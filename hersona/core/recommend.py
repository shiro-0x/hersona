"""属性推薦エンジン (ROADMAP ② 評価・推薦システム)。

診断クイズの回答を属性ベクトルにマッピングし (適合度スコア)、① 相性マトリクスを
使って conflict を解決した推薦ブレンドを返す。推薦結果はそのまま multi モードの
適用入力になり、`hersona.core.authoring` で保存もできる (recommend → apply → save)。

フロー (ROADMAP)::

    診断クイズ → 適合度スコアリング → 推薦ブレンド (相性チェック済み) → 適用 (→ 任意で保存)

設計方針:
- スコアリングは LLM 非依存の決定的マッピング (各回答が属性に重みを加算)。
- ブレンド選定はカテゴリごとに最高スコアの属性を採り、① マトリクスの
  `check_blend` で conflict を検出したら低スコア側を落とす (conflict-aware)。
- LLM によるテキスト採点 (`/hersona check`) は別経路であり、本モジュールは
  クイズ→ベクトルの推薦経路を担う。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from hersona.core.compatibility import CompatibilityMatrix, load_matrix


@dataclass(frozen=True)
class QuizOption:
    """診断クイズの選択肢。選ぶと weights の属性スコアが加算される。"""

    label: str
    weights: dict[str, float]


@dataclass(frozen=True)
class QuizQuestion:
    """診断クイズの 1 問。"""

    id: str
    prompt: str
    options: list[QuizOption]


@dataclass
class Recommendation:
    """推薦結果。"""

    blend: list[str]  # 適用すべき属性名 (カテゴリ横断、相性チェック済み)
    scores: dict[str, float]  # 全属性の適合度スコア (降順で参照可)
    dropped: list[tuple[str, str]] = field(default_factory=list)  # (属性, 理由)

    def ranked(self) -> list[tuple[str, float]]:
        """スコア降順の (属性, スコア) リスト (スコア 0 は除外)。"""
        return [
            (n, s)
            for n, s in sorted(self.scores.items(), key=lambda kv: (-kv[1], kv[0]))
            if s > 0
        ]


# ---------------------------------------------------------------------------
# 既定の診断クイズ (LLM 非依存・決定的)。
# 各回答は personality / speech / archetype の属性に重みを加える。
# ---------------------------------------------------------------------------
DEFAULT_QUIZ: list[QuizQuestion] = [
    QuizQuestion(
        id="distance",
        prompt="相手との距離感は？",
        options=[
            QuizOption("ぐいぐい近い", {"genki": 2.0, "childhood_friend": 1.5, "playful": 1.0}),
            QuizOption("素っ気ないが本当は気にする", {"tsundere": 2.0, "kuudere": 1.0}),
            QuizOption("物静かで控えめ", {"dandere": 2.0, "whispery": 1.5, "stoic": 1.0}),
            QuizOption("一定の品を保つ", {"keigo": 2.0, "onee_kotoba": 1.0, "mentor": 1.0}),
        ],
    ),
    QuizQuestion(
        id="emotion",
        prompt="感情の出し方は？",
        options=[
            QuizOption("表情豊かでにぎやか", {"genki": 2.0, "playful": 1.5}),
            QuizOption("クールで動じない", {"kuudere": 2.0, "stoic": 1.5}),
            QuizOption("内に秘めて深く重い", {"yandere": 1.5, "pessimist": 1.5, "dandere": 1.0}),
            QuizOption("場面で切り替える", {"switch": 2.0, "serious": 1.0}),
        ],
    ),
    QuizQuestion(
        id="speech",
        prompt="どんな話し方が好み？",
        options=[
            QuizOption("丁寧な敬語", {"keigo": 2.5}),
            QuizOption("ボーイッシュなタメ口", {"boku_girl": 2.0, "ore_boy": 2.0}),
            QuizOption("方言まじりで親しみやすい", {"kansai_ben": 2.5, "genki": 0.5}),
            QuizOption("古風・荘厳", {"archaic": 2.5, "shrine_maiden": 1.0}),
            QuizOption("老成・含蓄ある語り", {"washi": 2.5, "archaic": 1.0}),
            QuizOption("はんなり上品な京言葉", {"kyoto_ben": 2.5, "onee_kotoba": 0.5}),
        ],
    ),
    QuizQuestion(
        id="tone",
        prompt="声や口調の色は？",
        options=[
            QuizOption("色気のある誘うような口調", {"seductive": 2.5}),
            QuizOption("緊張して言い淀みがち", {"stutter": 2.5, "dandere": 0.5}),
            QuizOption("素っ気なく言葉数が少ない", {"blunt": 2.5, "kuudere": 0.5}),
            QuizOption("大仰で芝居がかった", {"theatrical": 2.5}),
            QuizOption("特にこだわらない", {}),
        ],
    ),
    QuizQuestion(
        id="selfview",
        prompt="自分の捉え方は？",
        options=[
            QuizOption("特別な力や設定を信じている", {"chuunibyou": 2.5}),
            QuizOption("自分の魅力に自信がある", {"narcissist": 2.5}),
            QuizOption("何でも前向きに捉える", {"optimist": 2.5, "genki": 0.5}),
            QuizOption("特に意識しない", {}),
        ],
    ),
    QuizQuestion(
        id="role",
        prompt="物語での立ち位置は？",
        options=[
            QuizOption("導く先達", {"mentor": 2.5, "serious": 1.0}),
            QuizOption("ぶつかり合うライバル", {"rival": 2.5, "tsundere": 1.0}),
            QuizOption("そばにいる幼なじみ", {"childhood_friend": 2.5, "genki": 1.0}),
            QuizOption("ヒロイン", {"heroine": 2.5}),
        ],
    ),
    QuizQuestion(
        id="hobby",
        prompt="趣味・属性で近いのは？",
        options=[
            QuizOption("ゲーム・オタク気質", {"gamer_otaku": 2.5, "playful": 1.0}),
            QuizOption("精緻で機械的", {"robot_android": 2.5, "third_person": 1.5}),
            QuizOption("神聖・伝統的", {"shrine_maiden": 2.5, "archaic": 1.0}),
            QuizOption("特にこだわらない", {}),
        ],
    ),
]


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
            raise KeyError(f"未知の質問 id: '{qid}'")
        if not (0 <= opt_index < len(q.options)):
            raise IndexError(f"質問 '{qid}' の選択肢 index 範囲外: {opt_index}")
        for attr, weight in q.options[opt_index].weights.items():
            scores[attr] = scores.get(attr, 0.0) + weight
    return scores


def recommend(
    answers: dict[str, int],
    *,
    matrix: CompatibilityMatrix | None = None,
    quiz: list[QuizQuestion] | None = None,
    attributes_root: Path | None = None,
) -> Recommendation:
    """診断回答から conflict 解決済みの推薦ブレンドを生成する。

    カテゴリごとに最高スコアの属性を 1 つ選び、① 相性マトリクスで conflict を
    検出したら低スコア側を落とす。
    """
    m = matrix or load_matrix(attributes_root)
    scores = score_answers(answers, quiz=quiz)

    # カテゴリごとに最高スコア属性を選ぶ (スコア 0 は対象外)。
    by_category: dict[str, list[tuple[str, float]]] = {}
    for name, score in scores.items():
        if score <= 0 or name not in m.attributes:
            continue
        cat = m.attributes[name].category
        by_category.setdefault(cat, []).append((name, score))

    candidates: list[tuple[str, float]] = []
    for cat in ("personality", "speech", "archetype"):
        ranked = sorted(by_category.get(cat, []), key=lambda kv: (-kv[1], kv[0]))
        if ranked:
            candidates.append(ranked[0])

    # conflict-aware: スコア降順で採用し、既採用と conflict するものは落とす。
    candidates.sort(key=lambda kv: (-kv[1], kv[0]))
    blend: list[str] = []
    dropped: list[tuple[str, str]] = []
    for name, _score in candidates:
        conflicting = [b for b in blend if m.conflicts(name, b)]
        if conflicting:
            dropped.append((name, f"{', '.join(conflicting)} と conflict"))
        else:
            blend.append(name)

    return Recommendation(blend=blend, scores=scores, dropped=dropped)
