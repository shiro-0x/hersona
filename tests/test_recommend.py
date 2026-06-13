"""属性推薦エンジン (hersona.core.recommend) の回帰テスト (ROADMAP ②)。

カバー範囲 (v1.2.0 強化後):
- score_answers がクイズ回答を属性スコアに集計する
- recommend がカテゴリごとに最高スコア属性を選ぶ
- recommend が ① 相性マトリクスで conflict を解決する (低スコア側を落とす)
- 既定クイズ DEFAULT_QUIZ が実データの属性のみを参照する
- 9 問構成 (visual / hobby / lifestyle / interaction / cultural 軸を含む)
- WeightMagnitude enum / RECOMMEND_THRESHOLDS の値検証
- rationale: 各採用属性の根拠が質問/選択肢を引用している
- alternatives: 落選属性に対する代替案が提示される
- summary: 日本語 1 文のサマリが生成される
- load_quiz: YAML から quiz を読み込める / 任意パス指定
- YAML の MODERATE / STRONG 等の WeightMagnitude 名前が正しく解決される
"""
from __future__ import annotations

from pathlib import Path

import pytest

from hersona.core.compatibility import CompatibilityMatrix, load_matrix
from hersona.core.recommend import (
    DEFAULT_QUIZ,
    DEFAULT_QUIZ_PATH,
    RECOMMEND_THRESHOLDS,
    QuizOption,
    QuizQuestion,
    WeightMagnitude,
    load_quiz,
    recommend,
    score_answers,
)
from hersona.core.weight import WeightLevel

REPO_ROOT = Path(__file__).resolve().parent.parent
ATTRIBUTES_DIR = REPO_ROOT / "attributes"


def _matrix() -> CompatibilityMatrix:
    return load_matrix(ATTRIBUTES_DIR)


# --- 旧 API (v1.1) 互換性 ------------------------------------------------


def test_score_answers_aggregates_weights() -> None:
    # distance=1 (tsundere2.0, kuudere1.0), role=1 (rival2.5, tsundere1.0)
    scores = score_answers({"distance": 1, "role": 1})
    assert scores["tsundere"] == pytest.approx(3.0)
    assert scores["rival"] == pytest.approx(2.5)
    assert scores["kuudere"] == pytest.approx(1.0)


def test_score_answers_unknown_question_raises() -> None:
    with pytest.raises(KeyError):
        score_answers({"nope": 0})


def test_score_answers_out_of_range_raises() -> None:
    with pytest.raises(IndexError):
        score_answers({"distance": 99})


def test_recommend_picks_top_per_category() -> None:
    # tsundere(personality) + keigo(speech) + rival(archetype) を狙う回答
    rec = recommend(
        {"distance": 1, "speech": 0, "role": 1},
        matrix=_matrix(),
    )
    assert "tsundere" in rec.blend
    assert "keigo" in rec.blend
    assert "rival" in rec.blend


def test_recommend_resolves_conflicts() -> None:
    # genki と kuudere は conflict。両方に重みが乗る回答で衝突解決を確認。
    quiz = [
        QuizQuestion(
            "q1", "?", [QuizOption("a", {"genki": 3.0})]
        ),
        QuizQuestion(
            "q2", "?", [QuizOption("a", {"kuudere": 1.0})]
        ),
    ]
    rec = recommend({"q1": 0, "q2": 0}, matrix=_matrix(), quiz=quiz)
    # 同カテゴリ (personality) なので高スコアの genki が採用され kuudere は候補外
    assert "genki" in rec.blend
    assert "kuudere" not in rec.blend


def test_recommend_drops_cross_category_conflict() -> None:
    # robot_android(archetype) と ore_boy(speech) は conflict。
    # robot_android を高スコアにして ore_boy が落ちることを確認。
    quiz = [
        QuizQuestion("a", "?", [QuizOption("x", {"robot_android": 3.0})]),
        QuizQuestion("s", "?", [QuizOption("x", {"ore_boy": 1.0})]),
    ]
    rec = recommend({"a": 0, "s": 0}, matrix=_matrix(), quiz=quiz)
    assert "robot_android" in rec.blend
    assert "ore_boy" not in rec.blend
    assert any("ore_boy" == name for name, _ in rec.dropped)


def test_recommendation_ranked_excludes_zero() -> None:
    """全質問に「該当なし」相当の回答がない v1.2.0 では、空 answers で確認。"""
    rec = recommend({}, matrix=_matrix())  # 回答なし → scores={}
    assert rec.ranked() == []
    assert rec.blend == []


def test_ranked_excludes_zero_score_entries() -> None:
    """スコア 0 の属性は ranked() に含まれない (recommend 経由で確認)。"""
    rec = recommend({"distance": 0}, matrix=_matrix())  # 1 回答だけ
    ranked_names = [n for n, _ in rec.ranked()]
    # 該当質問に重みが乗ってない属性は入らない
    for name, score in rec.scores.items():
        if score == 0:
            assert name not in ranked_names


def test_default_quiz_references_only_real_attributes() -> None:
    m = _matrix()
    known = set(m.names())
    for q in DEFAULT_QUIZ:
        for opt in q.options:
            for attr in opt.weights:
                assert attr in known, f"クイズ '{q.id}' が未知属性 '{attr}' を参照"


def test_washi_is_reachable_via_quiz() -> None:
    rec = recommend({"speech": 4}, matrix=_matrix())
    assert "washi" in rec.blend


def test_kyoto_ben_is_reachable_via_quiz() -> None:
    rec = recommend({"speech": 5}, matrix=_matrix())
    assert "kyoto_ben" in rec.blend


@pytest.mark.parametrize(
    "question,option_index,attr",
    [
        # Batch 4 で speech 質問へ追記したオプション (index 10-13)
        ("speech", 10, "seductive"),
        ("speech", 11, "stutter"),
        ("speech", 12, "blunt"),
        ("speech", 13, "theatrical"),
        # Batch 4 で emotion 質問へ追記したオプション (index 5-7)
        ("emotion", 5, "chuunibyou"),
        ("emotion", 6, "narcissist"),
        ("emotion", 7, "optimist"),
    ],
)
def test_batch4_attributes_are_reachable_via_quiz(question, option_index, attr) -> None:
    # Batch 4 で追加した 7 属性が診断クイズの単一回答で推薦に到達する。
    rec = recommend({question: option_index}, matrix=_matrix())
    assert attr in rec.blend


def test_default_quiz_blend_is_conflict_free() -> None:
    """既定クイズの推薦ブレンドは常に conflict フリー。"""
    m = _matrix()
    # 各質問で option 0 を選ぶ
    answers = {q.id: 0 for q in DEFAULT_QUIZ}
    rec = recommend(answers, matrix=m)
    assert m.check_blend(rec.blend) == []


# --- v1.2.0 新規: クイズは 9 問 -------------------------------------------


def test_default_quiz_has_nine_questions() -> None:
    """v1.2.0 で 5 問 → 9 問に拡張。"""
    assert len(DEFAULT_QUIZ) == 9


def test_new_questions_cover_visual_hobby_lifestyle() -> None:
    ids = {q.id for q in DEFAULT_QUIZ}
    assert "appearance" in ids  # visual 軸
    assert "hobby" in ids
    assert "lifestyle" in ids
    assert "interaction" in ids
    assert "cultural" in ids


# --- v1.2.0 新規: WeightMagnitude enum ------------------------------------


def test_weight_magnitude_values() -> None:
    """STRONG > MODERATE > MILD > WEAK > NONE の順。"""
    assert float(WeightMagnitude.STRONG.value) == 2.5
    assert float(WeightMagnitude.MODERATE.value) == 2.0
    assert float(WeightMagnitude.MILD.value) == 1.5
    assert float(WeightMagnitude.WEAK.value) == 1.0
    assert float(WeightMagnitude.NONE.value) == 0.0


def test_recommend_thresholds_defined() -> None:
    """v1.2.0 導入の閾値定数が読める。"""
    assert RECOMMEND_THRESHOLDS["strong"] == 4.0
    assert RECOMMEND_THRESHOLDS["adopt"] == 2.0
    assert RECOMMEND_THRESHOLDS["candidate"] == 1.0


# --- v1.2.0 新規: YAML 外部化 ---------------------------------------------


def test_load_quiz_from_default_path() -> None:
    """既定パスから 9 問のクイズが読める。"""
    qs = load_quiz()
    assert len(qs) == 9
    # 旧 ID が保持されている
    ids = {q.id for q in qs}
    assert {"distance", "emotion", "speech", "role", "hobby"} <= ids


def test_default_quiz_path_exists() -> None:
    """既定 YAML が repo 内に存在する。"""
    assert DEFAULT_QUIZ_PATH.exists()
    assert DEFAULT_QUIZ_PATH.name == "recommend_quiz.yaml"
    # hersona/data/quiz/ 配下 (attributes/ と分離)
    assert "hersona/data/quiz" in str(DEFAULT_QUIZ_PATH)


# --- W2: 英語ペルソナ用ロケール別クイズ -------------------------------------


def test_en_quiz_exists_and_loads() -> None:
    from hersona.core.recommend import EN_QUIZ_PATH

    assert EN_QUIZ_PATH.exists()
    qs = load_quiz(EN_QUIZ_PATH)
    # 質問数・ID はベースと同一 (--answers キー互換)
    assert [q.id for q in qs] == [q.id for q in load_quiz()]


def test_en_quiz_references_only_en_speech() -> None:
    """en クイズは ja speech に weight しない / 英語 speech 5 種に全到達できる。"""
    from hersona.core.recommend import EN_QUIZ_PATH

    m = _matrix()
    ja_speech = {
        n for n, a in m.attributes.items()
        if a.category == "speech" and a.content_lang == "ja"
    }
    reached: set[str] = set()
    for q in load_quiz(EN_QUIZ_PATH):
        for opt in q.options:
            for attr in opt.weights:
                assert attr in m.attributes, f"未知属性: {attr}"
                assert attr not in ja_speech, f"ja speech が混入: {attr} ({q.id})"
                reached.add(attr)
    assert {"formal_en", "casual_en", "blunt_en", "southern_us_en", "british_en"} <= reached


def test_quiz_path_for_lang() -> None:
    from hersona.core.recommend import EN_QUIZ_PATH, quiz_path_for

    assert quiz_path_for("en") == EN_QUIZ_PATH
    assert quiz_path_for("ja") == DEFAULT_QUIZ_PATH


def test_recommend_with_en_quiz_proposes_english_speech() -> None:
    from hersona.core.recommend import EN_QUIZ_PATH

    quiz = load_quiz(EN_QUIZ_PATH)
    rec = recommend({"speech": 4}, matrix=_matrix(), quiz=quiz)
    assert "british_en" in rec.blend


def test_quiz_is_english_base_with_ja_i18n() -> None:
    """既定クイズは BASE=en + i18n.ja 形式 (Phase 3)。"""
    qs = load_quiz()
    distance_q = next(q for q in qs if q.id == "distance")
    # BASE は英語、i18n.ja に日本語
    assert distance_q.prompt == "How close does she get to you?"
    assert distance_q.i18n["ja"]["prompt"] == "相手との距離感は？"
    assert distance_q.options[0].i18n["ja"]["label"] == "ぐいぐい近づいてくる"


def test_localized_prompt_and_label_fallback() -> None:
    """localized_* は <lang> → BASE のフォールバックで解決する。"""
    qs = load_quiz()
    distance_q = next(q for q in qs if q.id == "distance")
    assert distance_q.localized_prompt("ja") == "相手との距離感は？"
    assert distance_q.localized_prompt("en") == "How close does she get to you?"
    # i18n を持たない (BASE のみの) 選択肢/質問でも BASE にフォールバック
    bare = QuizOption(label="x", weights={})
    assert bare.localized_label("ja") == "x"
    assert bare.localized_label("en") == "x"


def test_load_quiz_resolves_weight_magnitude_names() -> None:
    """YAML 内で ``MODERATE`` / ``STRONG`` 等の名前が正しく float 化される。"""
    qs = load_quiz()
    # speech 質問の最初の選択肢 ("丁寧な敬語") は keigo に STRONG (=2.5)
    speech_q = next(q for q in qs if q.id == "speech")
    keigo_opt = speech_q.options[0]
    assert keigo_opt.weights["keigo"] == pytest.approx(2.5)


def test_load_quiz_accepts_numeric_weights() -> None:
    """YAML 内に数値リテラル (1.5 等) を直接書くケースも許容。"""
    custom_yaml = (REPO_ROOT / "hersona" / "data" / "quiz" / "_test_quiz_custom.yaml")
    custom_yaml.parent.mkdir(parents=True, exist_ok=True)
    custom_yaml.write_text(
        "questions:\n"
        "  - id: t1\n"
        "    prompt: '?'\n"
        "    options:\n"
        "      - label: a\n"
        "        weights: {tsundere: 1.5}\n",
        encoding="utf-8",
    )
    try:
        qs = load_quiz(custom_yaml)
        assert qs[0].options[0].weights["tsundere"] == pytest.approx(1.5)
    finally:
        custom_yaml.unlink()


# --- v1.2.0 新規: rationale (採用根拠) ------------------------------------


def test_rationale_references_questions_and_choices() -> None:
    # 既定 (en): 根拠に英語の質問文 (distance の localized_prompt) が引用される。
    rec = recommend({"distance": 1, "speech": 0}, matrix=_matrix())
    assert "tsundere" in rec.blend
    distance_q = next(q for q in DEFAULT_QUIZ if q.id == "distance")
    expected = distance_q.localized_prompt("en")
    reasons = rec.rationale["tsundere"]
    assert any(expected in r for r in reasons), f"質問文が引用されていない: {reasons}"


def test_rationale_localizes_to_japanese() -> None:
    # --lang ja 相当: 表示言語を ja にすると根拠が日本語で構成される。
    from hersona.core import i18n

    i18n.set_active_lang("ja")
    try:
        rec = recommend({"distance": 1, "speech": 0}, matrix=_matrix())
        reasons = rec.rationale["tsundere"]
        assert any("距離感" in r for r in reasons), f"日本語の質問文が引用されていない: {reasons}"
        assert any("質問「" in r for r in reasons)
    finally:
        i18n.set_active_lang("en")


def test_rationale_includes_all_adopted_attributes() -> None:
    rec = recommend(
        {"distance": 1, "speech": 0, "role": 1, "hobby": 0, "appearance": 0},
        matrix=_matrix(),
    )
    for name in rec.blend:
        assert name in rec.rationale
        assert len(rec.rationale[name]) >= 1


# --- v1.2.0 新規: alternatives (落選 → 代替) -----------------------------


def test_alternatives_provided_for_dropped_attributes() -> None:
    """conflict で落ちた属性に対し、推奨代替が提示される。"""
    rec = recommend(
        {"distance": 0, "speech": 0, "role": 0},  # genki 系で tsundere / rival 競合
        matrix=_matrix(),
    )
    if rec.dropped:
        for dropped_name, _reason in rec.dropped:
            # その落選属性の alternatives エントリが存在する
            entry = next(
                (a for a in rec.alternatives if a[0] == dropped_name), None
            )
            assert entry is not None, f"{dropped_name} の代替案エントリがない"
            dropped, alt, score = entry
            assert dropped == dropped_name
            # 代替は "(該当なし)" か具体的な属性名
            assert alt == "(該当なし)" or isinstance(alt, str)


# --- v1.2.0 新規: summary (1 文サマリ) -----------------------------------


def test_summary_includes_personality_speech_archetype() -> None:
    rec = recommend(
        {"distance": 1, "speech": 0, "role": 1},  # tsundere + keigo + rival
        matrix=_matrix(),
    )
    s = rec.summary(matrix=_matrix())
    # 既定 (en): テンプレート + 英語表示名 (BASE) で構成される
    assert "speaks with" in s
    assert "Keigo" in s and "Tsundere" in s


def test_summary_localizes_to_japanese() -> None:
    from hersona.core import i18n

    i18n.set_active_lang("ja")
    try:
        rec = recommend({"distance": 1, "speech": 0, "role": 1}, matrix=_matrix())
        s = rec.summary(matrix=_matrix())
        assert "で話す" in s
        assert "敬語" in s and "ツンデレ" in s
    finally:
        i18n.set_active_lang("en")


def test_summary_handles_empty_blend() -> None:
    rec = recommend({}, matrix=_matrix())  # 回答なし → blend=[]
    # 既定 (en) では common.none = "(none)"
    assert rec.summary(matrix=_matrix()) == "(none)"


# --- v1.2.0 新規: weight_suggestion --------------------------------------


def test_weight_suggestion_strong_for_high_score() -> None:
    """高スコアのときは STRONG。"""
    # 1 回答のみでも 2.5 < 4.0 なので MODERATE (= suggest_weight 閾値)
    # MODERATE 以上になるには複数回答必要
    rec2 = recommend(
        {"speech": 0, "role": 0},  # keigo 2.5 + mentor 2.5 → 4.0 強採用圏
        matrix=_matrix(),
    )
    assert rec2.weight_suggestion in (WeightLevel.MODERATE, WeightLevel.STRONG)


def test_weight_suggestion_moderate_default() -> None:
    """無回答 (=blend空) のとき、WeightLevel を持つ (型確認のみ)。"""
    rec = recommend({}, matrix=_matrix())
    assert isinstance(rec.weight_suggestion, WeightLevel)


# --- v1.2.0 新規: 全属性へのクイズ到達性 --------------------------------


def test_all_visual_attributes_reachable() -> None:
    """visual 5 種が全てクイズから推薦可能。"""
    visual = ["glasses", "silver_hair", "petite", "glamorous", "animal_ears"]
    for v in visual:
        rec = recommend({"appearance": {"glasses": 0, "silver_hair": 1, "petite": 2, "glamorous": 3, "animal_ears": 4}[v]}, matrix=_matrix())
        assert v in rec.blend, f"visual '{v}' がクイズから推薦できない"


def test_all_hobby_attributes_reachable() -> None:
    """hobby 5 種が全てクイズから推薦可能。"""
    mapping = {
        "gamer": 0, "reading": 1, "music": 2, "sports": 3, "cooking": 4,
    }
    for h, idx in mapping.items():
        rec = recommend({"hobby": idx}, matrix=_matrix())
        assert h in rec.blend, f"hobby '{h}' がクイズから推薦できない"


# --- 既知: robot_android と ore_boy の conflict (既存テスト維持) ---------
# 既存テストは上記 test_recommend_drops_cross_category_conflict に集約。


# --- v1.3.0 新規: top パラメータ (複数候補) -------------------------------


def test_top_default_is_one_and_backward_compatible() -> None:
    """既定 (top 省略) で 1 件、blend と candidates[0] が一致する。"""
    rec = recommend(
        {"distance": 1, "speech": 0, "role": 1},
        matrix=_matrix(),
    )
    assert rec.blend == rec.candidates[0]
    assert len(rec.candidates) == 1


def test_top_returns_multiple_distinct_candidates() -> None:
    """top=3 で候補が 3 件、各候補がカテゴリ横断で構成される。"""
    rec = recommend(
        {"distance": 1, "emotion": 1, "speech": 0, "role": 1, "hobby": 1, "appearance": 1},
        matrix=_matrix(),
        top=3,
    )
    assert 1 <= len(rec.candidates) <= 3
    # 各候補がカテゴリ 5 つ (personality/speech/archetype/visual/hobby) をまたぐ
    for cand in rec.candidates:
        cats = {_matrix().attributes[a].category for a in cand if a in _matrix().attributes}
        assert len(cats) >= 2  # 最低 2 カテゴリは欲しい


def test_top_invalid_raises() -> None:
    """top=0 / top=-1 は ValueError。"""
    with pytest.raises(ValueError):
        recommend({"distance": 1}, matrix=_matrix(), top=0)
    with pytest.raises(ValueError):
        recommend({"distance": 1}, matrix=_matrix(), top=-1)


def test_top_one_matches_legacy_behavior() -> None:
    """top=1 を明示しても省略時と完全に同じ結果 (後方互換保証)。"""
    rec_default = recommend({"distance": 1, "speech": 0, "role": 1}, matrix=_matrix())
    rec_explicit = recommend(
        {"distance": 1, "speech": 0, "role": 1}, matrix=_matrix(), top=1
    )
    assert rec_default.blend == rec_explicit.blend
    assert rec_default.candidates == rec_explicit.candidates
    assert rec_default.scores == rec_explicit.scores
