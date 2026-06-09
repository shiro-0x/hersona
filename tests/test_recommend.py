"""属性推薦エンジン (hersona.core.recommend) の回帰テスト (ROADMAP ②)。

- score_answers がクイズ回答を属性スコアに集計する
- recommend がカテゴリごとに最高スコア属性を選ぶ
- recommend が ① 相性マトリクスで conflict を解決する (低スコア側を落とす)
- 既定クイズ DEFAULT_QUIZ が実データの属性のみを参照する
"""
from __future__ import annotations

from pathlib import Path

import pytest

from hersona.core.compatibility import CompatibilityMatrix, load_matrix
from hersona.core.recommend import (
    DEFAULT_QUIZ,
    QuizOption,
    QuizQuestion,
    recommend,
    score_answers,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
ATTRIBUTES_DIR = REPO_ROOT / "attributes"


def _matrix() -> CompatibilityMatrix:
    return load_matrix(ATTRIBUTES_DIR)


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
    rec = recommend({"hobby": 3}, matrix=_matrix())  # "特にこだわらない" = {}
    assert rec.ranked() == []
    assert rec.blend == []


def test_default_quiz_references_only_real_attributes() -> None:
    m = _matrix()
    known = set(m.names())
    for q in DEFAULT_QUIZ:
        for opt in q.options:
            for attr in opt.weights:
                assert attr in known, f"クイズ '{q.id}' が未知属性 '{attr}' を参照"


def test_washi_is_reachable_via_quiz() -> None:
    # speech 質問の「老成・含蓄ある語り」(index 4) で washi が推薦される
    rec = recommend({"speech": 4}, matrix=_matrix())
    assert "washi" in rec.blend


def test_kyoto_ben_is_reachable_via_quiz() -> None:
    # speech 質問の「はんなり上品な京言葉」(index 5) で kyoto_ben が推薦される
    rec = recommend({"speech": 5}, matrix=_matrix())
    assert "kyoto_ben" in rec.blend


@pytest.mark.parametrize(
    "question,option_index,attr",
    [
        ("tone", 0, "seductive"),
        ("tone", 1, "stutter"),
        ("tone", 2, "blunt"),
        ("tone", 3, "theatrical"),
        ("selfview", 0, "chuunibyou"),
        ("selfview", 1, "narcissist"),
        ("selfview", 2, "optimist"),
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
