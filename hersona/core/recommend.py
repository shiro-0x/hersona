"""属性推薦エンジン (ROADMAP ② 評価・推薦システム) v1.2.0。

診断クイズの回答を属性ベクトルにマッピングし (適合度スコア)、① 相性マトリクスを
使って conflict を解決した推薦ブレンドを返す。推薦結果はそのまま multi モードの
適用入力になり、`hersona.core.authoring` で保存もできる (recommend → apply → save)。

v1.2.0 での拡張:
- クイズを ``hersona/data/quiz/recommend_quiz.yaml`` に外部化 (Python コードからデータ分離)
- WeightMagnitude enum (STRONG=2.5 / MODERATE=2.0 / MILD=1.5 / WEAK=1.0 / NONE=0.0) を導入
- 9 問構成 (旧 5 問 → visual / hobby / lifestyle / interaction / cultural 軸を追加)
- ``Recommendation`` に rationale / alternatives / summary / weight_suggestion を追加
- 適合度スコアから強度 (none / mild / moderate / strong) を ``suggest_weight`` 経由で推定
- 閾値 ``RECOMMEND_THRESHOLDS`` で「強採用 / 採用 / 補欠 / 表示のみ」を区別

フロー (ROADMAP)::

    診断クイズ → 適合度スコアリング → 推薦ブレンド (相性チェック済み) → 適用 (→ 任意で保存)

設計方針:
- スコアリングは LLM 非依存の決定的マッピング (各回答が属性に重みを加算)。
- ブレンド選定はカテゴリごとに最高スコアの属性を採り、① マトリクスの
  ``check_blend`` で conflict を検出したら低スコア側を落とす (conflict-aware)。
- LLM によるテキスト採点 (``/hersona check``) は別経路であり、本モジュールは
  クイズ→ベクトルの推薦経路を担う。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

import yaml

from hersona.core.compatibility import CompatibilityMatrix, load_matrix
from hersona.core.constants import CATEGORY_ORDER
from hersona.core.i18n import active_lang, resolve_meta, tr
from hersona.core.weight import WeightLevel, suggest_weight


# ---------------------------------------------------------------------------
# 重みスケール (Quiz YAML で参照される名前空間)
# ---------------------------------------------------------------------------
class WeightMagnitude(StrEnum):
    """クイズ回答 1 つが加算する重みの強さ。

    YAML 側はこの名前で参照する (``weights: {genki: MODERATE}``)。
    Python 側では ``WeightMagnitude.MODERATE.value`` (= "2.0") がスコア加算値。
    """

    STRONG = "2.5"
    MODERATE = "2.0"
    MILD = "1.5"
    WEAK = "1.0"
    NONE = "0.0"


# スコアの閾値 (= 「強採用 / 採用 / 補欠 / 表示のみ」の判定境界)
RECOMMEND_THRESHOLDS = {
    "strong": 4.0,  # score >= 4.0 → 強採用
    "adopt": 2.0,   # score >= 2.0 → 採用
    "candidate": 1.0,  # score >= 1.0 → 補欠
    # score < 1.0 → 表示のみ
}


# ---------------------------------------------------------------------------
# データ型
# ---------------------------------------------------------------------------
def _localize(base: str, i18n: dict, field: str, lang: str | None) -> str:
    """BASE 値 + i18n ブロックから表示言語の文字列を解決する。

    ``resolve_meta`` と同じフォールバック (i18n.<lang>.<field> → BASE)。
    """
    return resolve_meta({"i18n": i18n, field: base}, field, lang)


@dataclass(frozen=True)
class QuizOption:
    """診断クイズの選択肢。選ぶと weights の属性スコアが加算される。"""

    label: str  # BASE (en)
    weights: dict[str, float]
    i18n: dict = field(default_factory=dict)  # {lang: {label: "..."}}

    def localized_label(self, lang: str | None = None) -> str:
        """表示言語のラベルを返す (フォールバック: <lang> → BASE)。"""
        return _localize(self.label, self.i18n, "label", lang)


@dataclass(frozen=True)
class QuizQuestion:
    """診断クイズの 1 問。"""

    id: str
    prompt: str  # BASE (en)
    options: list[QuizOption]
    i18n: dict = field(default_factory=dict)  # {lang: {prompt: "..."}}

    def localized_prompt(self, lang: str | None = None) -> str:
        """表示言語の質問文を返す (フォールバック: <lang> → BASE)。"""
        return _localize(self.prompt, self.i18n, "prompt", lang)


@dataclass
class Recommendation:
    """推薦結果。"""

    blend: list[str]  # 適用すべき属性名 (カテゴリ横断、相性チェック済み)
    scores: dict[str, float]  # 全属性の適合度スコア (降順で参照可)
    dropped: list[tuple[str, str]] = field(default_factory=list)  # (属性, 理由)
    rationale: dict[str, list[str]] = field(default_factory=dict)  # 属性 → 根拠のリスト
    alternatives: list[tuple[str, str, float]] = field(
        default_factory=list
    )  # (落選属性, 推奨代替, スコア) — conflict で落ちたもののみ
    weight_suggestion: WeightLevel = WeightLevel.MODERATE  # トップスコアからの推奨強度
    candidates: list[list[str]] = field(default_factory=list)  # 複数候補 (top>1 時)

    def ranked(self) -> list[tuple[str, float]]:
        """スコア降順の (属性, スコア) リスト (スコア 0 は除外)。"""
        return [
            (n, s)
            for n, s in sorted(self.scores.items(), key=lambda kv: (-kv[1], kv[0]))
            if s > 0
        ]

    def summary(self, matrix: CompatibilityMatrix | None = None) -> str:
        """推薦結果から 1 文のサマリを生成する (表示言語に追従)。

        speech/personality/archetype の有無に応じてテンプレートを選び、hobby/visual を
        末尾に結合する。表示名・文型・区切りはすべてカタログ (`summary.*`) 経由で
        現在の表示言語に合わせて解決する。

        Args:
            matrix: category 判定用。None なら ``load_matrix()`` でロード。
                    display_name は attach.load_attribute 経由で YAML から解決する。
        """
        m = matrix
        if m is None:
            m = load_matrix()

        # display_name を attach.load_attribute 経由で取得 (遅延 import で循環回避)
        from hersona.core.attach import load_attribute as _load_attr

        by_cat: dict[str, str] = {}
        for name in self.blend:
            if name not in m.attributes:
                continue
            cat = m.attributes[name].category
            if cat in by_cat:
                continue
            try:
                data = _load_attr(name)
                by_cat[cat] = resolve_meta(data, "display_name") or name
            except (KeyError, FileNotFoundError):
                by_cat[cat] = name

        parts: list[str] = []
        speech = by_cat.get("speech")
        personality = by_cat.get("personality")
        archetype = by_cat.get("archetype")

        if speech and personality and archetype:
            parts.append(
                tr(
                    "summary.speech_personality_archetype",
                    speech=speech,
                    personality=personality,
                    archetype=archetype,
                )
            )
        elif speech and personality:
            parts.append(tr("summary.speech_personality", speech=speech, personality=personality))
        elif speech and archetype:
            parts.append(tr("summary.speech_archetype", speech=speech, archetype=archetype))
        elif personality or archetype:
            parts.append(personality or archetype or "")

        tail = [by_cat[k] for k in ("hobby", "visual") if k in by_cat]
        if tail:
            parts.append(tr("summary.tail_join").join(tail))

        return tr("summary.sentence_join").join(parts) if parts else tr("common.none")


# ---------------------------------------------------------------------------
# YAML 読み込み
# ---------------------------------------------------------------------------
DEFAULT_QUIZ_PATH = (
    Path(__file__).resolve().parent.parent / "data" / "quiz" / "recommend_quiz.yaml"
)
# 英語ペルソナ用クイズ (W2: ロケール別クイズ)。gen_quiz_en.py で BASE から導出。
EN_QUIZ_PATH = DEFAULT_QUIZ_PATH.with_name("recommend_quiz.en.yaml")


def quiz_path_for(lang: str | None = None) -> Path:
    """表示言語に対応する既定クイズのパスを返す (W2)。

    en は英語 speech へ導線するロケール別クイズ、それ以外は BASE クイズ
    (ja ペルソナ構成)。質問 ID は両者で同一 (``--answers`` キー互換)。
    """
    resolved = lang or active_lang()
    if resolved == "en" and EN_QUIZ_PATH.exists():
        return EN_QUIZ_PATH
    return DEFAULT_QUIZ_PATH


def quiz_for_lang(lang: str | None = None) -> list[QuizQuestion]:
    """表示言語の既定クイズをロードする (lang 省略時は現在の表示言語)。"""
    return load_quiz(quiz_path_for(lang))


def _coerce_weight(value: str | float | int) -> float:
    """YAML の weight を float に正規化する。

    許容:
    - 数値 (1.0, 2, 0.5) → そのまま float 化
    - WeightMagnitude 名前 (``"STRONG"`` / ``"MODERATE"`` / ...) → 該当値に解決
    """
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        # まず WeightMagnitude 名前として解釈を試みる (大文字小文字を問わない)
        upper = value.strip().upper()
        if upper in WeightMagnitude.__members__:
            return float(WeightMagnitude[upper].value)
        # 数値文字列として解釈
        try:
            return float(value)
        except ValueError as e:
            raise ValueError(tr("core.weight_unparseable", value=value)) from e
    raise TypeError(tr("core.weight_bad_type", type=type(value).__name__))


def load_quiz(path: Path | None = None) -> list[QuizQuestion]:
    """``recommend_quiz.yaml`` から ``QuizQuestion`` のリストを組み立てる。

    Args:
        path: YAML ファイルパス。None なら ``DEFAULT_QUIZ_PATH`` (同梱) を使う。
    """
    src = path or DEFAULT_QUIZ_PATH
    if not src.exists():
        raise FileNotFoundError(tr("core.quiz_not_found", src=src))

    with src.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict) or "questions" not in data:
        raise ValueError(tr("core.quiz_bad_format", src=src))

    questions: list[QuizQuestion] = []
    for q in data["questions"]:
        options = []
        for opt in q.get("options", []):
            weights = {
                attr: _coerce_weight(w) for attr, w in opt.get("weights", {}).items()
            }
            options.append(
                QuizOption(
                    label=opt["label"],
                    weights=weights,
                    i18n=opt.get("i18n") or {},
                )
            )
        questions.append(
            QuizQuestion(
                id=q["id"],
                prompt=q["prompt"],
                options=options,
                i18n=q.get("i18n") or {},
            )
        )
    return questions


# 既定クイズ (= YAML ロードの薄いラッパ)
def _default_quiz() -> list[QuizQuestion]:
    return load_quiz(DEFAULT_QUIZ_PATH)


# --- 互換性: 旧 API (DEFAULT_QUIZ) -----------------------------------------
# 旧コードが ``from hersona.core.recommend import DEFAULT_QUIZ`` で参照していた
# 場合に壊れないよう、モジュールロード時に確定値をバインドする。
DEFAULT_QUIZ: list[QuizQuestion] = _default_quiz()


# ---------------------------------------------------------------------------
# スコアリング
# ---------------------------------------------------------------------------
def score_answers(
    answers: dict[str, int],
    *,
    quiz: list[QuizQuestion] | None = None,
) -> dict[str, float]:
    """クイズ回答 {question_id: option_index} を属性スコアに集計する。"""
    questions = quiz or DEFAULT_QUIZ
    by_id = {q.id: q for q in questions}
    scores: dict[str, float] = {}
    for qid, opt_index in answers.items():
        q = by_id.get(qid)
        if q is None:
            raise KeyError(tr("core.unknown_question_id", qid=qid))
        if not (0 <= opt_index < len(q.options)):
            raise IndexError(tr("core.option_out_of_range", qid=qid, index=opt_index))
        for attr, weight in q.options[opt_index].weights.items():
            scores[attr] = scores.get(attr, 0.0) + weight
    return scores


def _build_rationale(
    answers: dict[str, int],
    *,
    quiz: list[QuizQuestion] | None = None,
) -> dict[str, list[str]]:
    """各属性について「どの質問/選択肢から推されたか」の根拠文字列を生成する。"""
    questions = quiz or DEFAULT_QUIZ
    by_id = {q.id: q for q in questions}
    rationale: dict[str, list[str]] = {}
    for qid, opt_index in answers.items():
        q = by_id.get(qid)
        if q is None or not (0 <= opt_index < len(q.options)):
            continue
        opt = q.options[opt_index]
        reason = tr(
            "recommend.rationale_item",
            prompt=q.localized_prompt(),
            label=opt.localized_label(),
        )
        for attr in opt.weights:
            rationale.setdefault(attr, []).append(reason)
    return rationale


# ---------------------------------------------------------------------------
# 推薦本体
# ---------------------------------------------------------------------------
def _build_candidate_blend(
    name: str,
    score: float,
    by_category: dict[str, list[tuple[str, float]]],
    blend: list[str],
    m: CompatibilityMatrix,
) -> tuple[list[str], list[tuple[str, str]]]:
    """1 つの seed 属性から派生候補ブレンドを組み立てる。

    seed 属性のカテゴリ以外で最高スコアの属性を貪欲に追加する。
    カテゴリ top-1 候補 (blend) を「ベース」、他カテゴリの top-1 を 1 つずつ
    足していく形。conflict が出たら低スコア側を落とす。
    """
    seed_cat = m.attributes[name].category
    # seed の score 引数が 0.0 (= 後方互換計算用) の場合、by_category から実際の
    # スコアを引き直す。さもないとソート順が狂い、seed 以外の属性が seed を上書きする。
    actual_seed_score = score
    if actual_seed_score <= 0.0:
        for s_name, s_score in by_category.get(seed_cat, []):
            if s_name == name:
                actual_seed_score = s_score
                break
    parts: list[tuple[str, float, str]] = [(name, actual_seed_score, seed_cat)]
    for cat in CATEGORY_ORDER:
        if cat == seed_cat:
            continue
        ranked = by_category.get(cat, [])
        if not ranked:
            continue
        parts.append((ranked[0][0], ranked[0][1], cat))

    parts.sort(key=lambda x: (-x[1], x[0]))
    cand_blend: list[str] = []
    dropped: list[tuple[str, str]] = []
    for cand_name, _sc, _cat in parts:
        conflicting = [b for b in cand_blend if m.conflicts(cand_name, b)]
        if conflicting:
            dropped.append(
                (cand_name, tr("recommend.conflict_reason", names=", ".join(conflicting)))
            )
        else:
            cand_blend.append(cand_name)
    return cand_blend, dropped


def recommend(
    answers: dict[str, int],
    *,
    matrix: CompatibilityMatrix | None = None,
    quiz: list[QuizQuestion] | None = None,
    attributes_root: Path | None = None,
    top: int = 1,
) -> Recommendation:
    """診断回答から conflict 解決済みの推薦ブレンドを生成する。

    戻り値の ``Recommendation`` には以下を含む:
    - ``blend``: 採用属性 (カテゴリ top-1, conflict 解決済)。``top=1`` 時の単一候補
    - ``candidates``: ``top`` 件の派生候補ブレンド (新フィールド)。
      ``top=1`` なら ``[blend]`` と同等の 1 件。複数指定時は score 上位を seed に派生
    - ``scores``: 全属性の適合度スコア
    - ``dropped``: conflict で落ちた属性と理由
    - ``rationale``: 各採用属性の根拠 (どの質問/選択肢から)
    - ``alternatives``: 落選属性に対する推奨代替 (同カテゴリの次点スコア)
    - ``weight_suggestion``: トップスコアからの推奨強度

    Args:
        top: 返却する候補数 (既定 1)。``top>1`` で複数候補を返す。
    """
    if top < 1:
        raise ValueError(tr("core.recommend_top_invalid", top=top))

    m = matrix or load_matrix(attributes_root)
    questions = quiz or DEFAULT_QUIZ
    scores = score_answers(answers, quiz=questions)
    rationale = _build_rationale(answers, quiz=questions)

    # カテゴリごとにスコア付き属性を集める
    by_category: dict[str, list[tuple[str, float]]] = {}
    for name, score in scores.items():
        if score <= 0 or name not in m.attributes:
            continue
        cat = m.attributes[name].category
        by_category.setdefault(cat, []).append((name, score))

    # カテゴリごとに top-K (上位 2 件まで) を候補に保持 (= alternatives 用)
    top_k: dict[str, list[tuple[str, float]]] = {}
    for cat in CATEGORY_ORDER:
        ranked = sorted(by_category.get(cat, []), key=lambda kv: (-kv[1], kv[0]))
        top_k[cat] = ranked[:2]

    # 各カテゴリの最高スコア属性を seed 候補に
    seed_candidates: list[tuple[str, float]] = []
    for cat in CATEGORY_ORDER:
        ranked = top_k.get(cat, [])
        if ranked:
            seed_candidates.append(ranked[0])

    # スコア降順で seed を並べ、上位 ``top`` 件から派生候補を生成
    seed_candidates.sort(key=lambda kv: (-kv[1], kv[0]))
    selected_seeds = seed_candidates[:top]

    candidates: list[list[str]] = []
    seen_blends: set[tuple[str, ...]] = set()
    for seed_name, _seed_score in selected_seeds:
        cand_blend, _dropped = _build_candidate_blend(
            seed_name, _seed_score, by_category, [], m
        )
        key = tuple(cand_blend)
        if key in seen_blends:
            continue
        seen_blends.add(key)
        candidates.append(cand_blend)

    # 単一 seed で衝突し派生が空になった場合 (理論上ほぼ起こらない) のフォールバック
    if not candidates and seed_candidates:
        candidates.append([seed_candidates[0][0]])

    # 後方互換: blend は「カテゴリ top-1 を貪欲 + conflict 解決」の旧ロジック。
    # top=1 時の既存挙動を完全保持するため、candidates[0] ではなく従来の手順で再計算。
    # (candidates は _build_candidate_blend 経由のためドロップログが混在しない、
    #  旧 dropped を維持するには従来手順が必要)
    primary_seed = candidates[0][0] if candidates else None
    blend: list[str] = []
    primary_dropped: list[tuple[str, str]] = []
    if primary_seed is not None:
        _cand_for_blend, primary_dropped = _build_candidate_blend(
            primary_seed, 0.0, by_category, [], m
        )
        blend = _cand_for_blend

    # dropped: 旧仕様 (= 採用候補が conflict で落ちたもの) を維持。
    # _build_candidate_blend 内部で記録された dropped をマージする。
    # top>1 で増えた派生候補の dropped は除外 (= 派生候補は独立した blend なので混在不可)。
    dropped: list[tuple[str, str]] = list(primary_dropped)

    # alternatives: 落選した属性について、同カテゴリの次点を代替として提示
    alternatives: list[tuple[str, str, float]] = []
    for dropped_name, _reason in dropped:
        if dropped_name not in m.attributes:
            continue
        cat = m.attributes[dropped_name].category
        # 同カテゴリで top-1 (=採用済) と top-2 (= 落選属性) 以外の候補
        same_cat = top_k.get(cat, [])
        for cand_name, cand_score in same_cat:
            if cand_name == dropped_name:
                continue
            if cand_name in blend:
                continue
            # 採用済と conflict しないものだけ代替候補に
            if not any(m.conflicts(cand_name, b) for b in blend):
                alternatives.append((dropped_name, cand_name, cand_score))
                break
        else:
            # 代替が見つからない (= 同カテゴリに他に候補なし)
            alternatives.append((dropped_name, tr("common.none"), 0.0))

    # weight_suggestion: トップスコアから推定
    ranked_all = [(n, s) for n, s in scores.items() if s > 0]
    top_score = max((s for _, s in ranked_all), default=0.0)
    weight_suggestion = suggest_weight(top_score)

    return Recommendation(
        blend=blend,
        scores=scores,
        dropped=dropped,
        rationale={n: rationale.get(n, []) for n in blend},
        alternatives=alternatives,
        weight_suggestion=weight_suggestion,
        candidates=candidates,
    )
