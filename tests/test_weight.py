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
