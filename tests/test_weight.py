"""weight 較正 (hersona.core.weight) の回帰テスト (ROADMAP ① weight 較正)。

- catchphrase_subset が強度に応じて露出量を変える
- suggest_weight がスコアを強度に写像する
- render_blend(weight=...) が強度ガイダンスと catchphrase 量に反映する
"""
from __future__ import annotations

from pathlib import Path

import pytest

from hersona.core.attach import render_blend
from hersona.core.weight import (
    WeightLevel,
    catchphrase_subset,
    coerce_level,
    suggest_weight,
)

ATTRIBUTES_DIR = Path(__file__).resolve().parent.parent / "attributes"
_NO_USER = Path("/nonexistent")


def test_coerce_level_accepts_str_and_enum() -> None:
    assert coerce_level("strong") is WeightLevel.STRONG
    assert coerce_level(WeightLevel.MILD) is WeightLevel.MILD


def test_coerce_level_rejects_unknown() -> None:
    with pytest.raises(ValueError):
        coerce_level("extreme")


def test_catchphrase_subset_scales_with_level() -> None:
    cps = [f"c{i}" for i in range(10)]
    assert catchphrase_subset(cps, "none") == []
    assert len(catchphrase_subset(cps, "mild")) == 3  # round(10*0.34)
    assert len(catchphrase_subset(cps, "moderate")) == 7  # round(10*0.67)
    assert catchphrase_subset(cps, "strong") == cps


def test_catchphrase_subset_min_one_when_nonzero() -> None:
    assert catchphrase_subset(["a"], "mild") == ["a"]
    assert catchphrase_subset([], "strong") == []


def test_suggest_weight_thresholds() -> None:
    assert suggest_weight(0) is WeightLevel.NONE
    assert suggest_weight(1.0) is WeightLevel.MILD
    assert suggest_weight(2.0) is WeightLevel.MODERATE
    assert suggest_weight(5.0) is WeightLevel.STRONG


def test_render_blend_weight_affects_catchphrases() -> None:
    mild = render_blend(["tsundere"], public_root=ATTRIBUTES_DIR, user_root=_NO_USER, weight="mild")
    strong = render_blend(
        ["tsundere"], public_root=ATTRIBUTES_DIR, user_root=_NO_USER, weight="strong"
    )
    assert "## 強度: mild" in mild.prompt
    assert "## 強度: strong" in strong.prompt
    # strong の方が catchphrases を多く含む
    assert strong.prompt.count("- べ、別に") >= mild.prompt.count("- べ、別に")
    assert strong.prompt.count("\n- ") > mild.prompt.count("\n- ")


def test_render_blend_default_is_moderate() -> None:
    result = render_blend(["tsundere"], public_root=ATTRIBUTES_DIR, user_root=_NO_USER)
    assert "## 強度: moderate" in result.prompt


# ---- weight_for_score (P0-3: 連続値スコア → weight 写像、ヒステリシス付き) ----


def test_weight_for_score_boundaries() -> None:
    from hersona.core import weight_for_score

    assert weight_for_score(24.9) == WeightLevel.NONE
    assert weight_for_score(25) == WeightLevel.MILD
    assert weight_for_score(55) == WeightLevel.MODERATE
    assert weight_for_score(85) == WeightLevel.STRONG


def test_weight_for_score_clamps_out_of_range() -> None:
    from hersona.core import weight_for_score

    assert weight_for_score(-10) == WeightLevel.NONE
    assert weight_for_score(150) == WeightLevel.STRONG


def test_weight_for_score_hysteresis_promotion() -> None:
    from hersona.core import weight_for_score

    # MILD→MODERATE 昇格は t2(55) + hysteresis(5) = 60 から
    assert weight_for_score(57, previous=WeightLevel.MILD) == WeightLevel.MILD
    assert weight_for_score(60, previous=WeightLevel.MILD) == WeightLevel.MODERATE


def test_weight_for_score_hysteresis_demotion() -> None:
    from hersona.core import weight_for_score

    # MODERATE→MILD 降格は t2(55) - hysteresis(5) = 50 を下回ってから
    assert weight_for_score(52, previous=WeightLevel.MODERATE) == WeightLevel.MODERATE
    assert weight_for_score(49, previous=WeightLevel.MODERATE) == WeightLevel.MILD


def test_weight_for_score_without_previous_uses_raw_thresholds() -> None:
    from hersona.core import weight_for_score

    assert weight_for_score(57) == WeightLevel.MODERATE
    assert weight_for_score(52) == WeightLevel.MILD


def test_weight_for_score_multi_level_jump() -> None:
    from hersona.core import weight_for_score

    # 大きく跳ねた場合は複数レベルを一度に移動できる (各境界 + hysteresis を満たす限り)
    assert weight_for_score(95, previous=WeightLevel.NONE) == WeightLevel.STRONG
    assert weight_for_score(5, previous=WeightLevel.STRONG) == WeightLevel.NONE


def test_weight_for_score_invalid_thresholds() -> None:
    import pytest

    from hersona.core import weight_for_score

    with pytest.raises(ValueError):
        weight_for_score(50, thresholds=(55.0, 25.0, 85.0))
