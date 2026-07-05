"""hersona bench (hersona.core.bench) の回帰テスト。

外部レビュー対応 (docs/reviews/2026-07-04-external-review-response.md §P1-1):
人格維持率・token コストの決定的採点ハーネス。LLM 呼び出しは行わない。
"""
from __future__ import annotations

from pathlib import Path

import pytest

from hersona.core.bench import (
    BenchResult,
    BenchScenario,
    available_scenarios,
    demo_transcript,
    estimate_token_cost,
    load_scenario,
    score_transcript,
)


def test_score_transcript_basic() -> None:
    transcript = ["こんにちは、失礼します。", "承知いたしました、ようございます。"]
    result = score_transcript(["tsundere", "keigo"], transcript, weight="moderate")
    assert isinstance(result, BenchResult)
    assert result.blend == ["tsundere", "keigo"]
    assert len(result.turn_scores) == 2
    assert result.maintenance_rate is not None
    assert 0.0 <= result.maintenance_rate <= 1.0
    assert result.mean_score is not None
    assert len(result.decay) == len(result.scored_turns)


def test_score_transcript_empty_names_raises() -> None:
    with pytest.raises(ValueError):
        score_transcript([], ["hi"], weight="moderate")


def test_score_transcript_no_speech_attribute_all_skipped() -> None:
    # archetype 単体 (speech 属性なし) は measure_intensity が None を返す想定。
    result = score_transcript(["heroine"], ["some text", "more text"], weight="moderate")
    assert result.maintenance_rate is None
    assert result.mean_score is None
    assert result.decay == []


def test_bench_result_to_dict_shape() -> None:
    result = score_transcript(["tsundere", "keigo"], ["こんにちは。"], weight="strong")
    d = result.to_dict()
    assert set(d.keys()) >= {
        "blend", "weight", "scenario_id", "maintenance_rate", "mean_score", "decay", "turns",
    }
    assert d["weight"] == "strong"
    assert len(d["turns"]) == 1


def test_estimate_token_cost_increases_with_more_attributes() -> None:
    small = estimate_token_cost(["tsundere"], weight="moderate")
    large = estimate_token_cost(["tsundere", "keigo"], weight="moderate")
    assert large.chars > small.chars
    assert large.approx_tokens > small.approx_tokens


def test_estimate_token_cost_dict_shape() -> None:
    cost = estimate_token_cost(["tsundere"], weight="strong")
    d = cost.to_dict()
    assert d["weight"] == "strong"
    assert d["chars"] > 0
    assert d["approx_tokens"] == d["chars"] // 4


def test_demo_transcript_uses_content_language() -> None:
    ja_samples = demo_transcript(["tsundere", "keigo"], count=3, lang="ja")
    assert ja_samples  # tsundere/keigo have ja catchphrases
    assert all(isinstance(s, str) for s in ja_samples)


def test_demo_transcript_empty_for_unknown_lang_without_catchphrases() -> None:
    # 存在しない lang を渡すと content_i18n も base catchphrases も見つからずゼロ件になりうる。
    # (この属性ペアには en の content_i18n が無い前提)
    samples = demo_transcript(["tsundere", "keigo"], count=3, lang="fr")
    assert isinstance(samples, list)  # 空でもエラーにならない


def test_demo_transcript_then_score_roundtrip() -> None:
    names = ["tsundere", "keigo"]
    transcript = demo_transcript(names, count=4, lang="ja")
    assert transcript
    result = score_transcript(names, transcript, weight="moderate")
    assert result.maintenance_rate is not None


def test_load_scenario_roundtrip(tmp_path: Path) -> None:
    p = tmp_path / "s.yaml"
    p.write_text(
        "id: my_scenario\ndescription: test\nturns:\n  - hi\n  - bye\n", encoding="utf-8"
    )
    scenario = load_scenario(p)
    assert isinstance(scenario, BenchScenario)
    assert scenario.id == "my_scenario"
    assert scenario.turns == ["hi", "bye"]


def test_load_scenario_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_scenario(tmp_path / "nope.yaml")


def test_load_scenario_bad_format_raises(tmp_path: Path) -> None:
    p = tmp_path / "bad.yaml"
    p.write_text("not_id: x\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_scenario(p)


def test_load_scenario_empty_turns_raises(tmp_path: Path) -> None:
    p = tmp_path / "empty.yaml"
    p.write_text("id: x\nturns: []\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_scenario(p)


def test_available_scenarios_finds_repo_bundled_scenarios() -> None:
    scenarios = available_scenarios()
    assert "casual_greeting_ja" in scenarios
    assert "casual_greeting_en" in scenarios
    assert "long_form_topic_switch_ja" in scenarios
    assert "long_form_topic_switch_en" in scenarios
    assert "roleplay_scene_ja" in scenarios
    assert "technical_distraction_en" in scenarios
    for path in scenarios.values():
        assert path.exists()


def test_available_scenarios_missing_root_returns_empty(tmp_path: Path) -> None:
    assert available_scenarios(tmp_path / "does_not_exist") == {}
