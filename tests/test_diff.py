"""属性差分比較 (hersona.core.diff) の回帰テスト (B1)。"""
from __future__ import annotations

import pytest

from hersona.core.compatibility import Relation
from hersona.core.diff import diff_attributes


def test_diff_returns_relation_for_public_pair() -> None:
    d = diff_attributes("yandere", "dandere")
    assert d.relation == Relation.CONFLICT


def test_diff_neutral_pair() -> None:
    d = diff_attributes("tsundere", "dandere")
    assert d.relation == Relation.NEUTRAL


def test_diff_cross_lang_speech_conflict() -> None:
    d = diff_attributes("keigo", "casual_en")
    assert d.relation == Relation.CONFLICT


def test_diff_list_field_split_is_order_preserving() -> None:
    d = diff_attributes("tsundere", "kuudere")
    traits = next(f for f in d.lists if f.field == "core_traits")
    # 共通項が common に入り、only_a / only_b には現れない。
    assert "素直になれない" in traits.common
    assert "素直になれない" not in traits.only_a
    assert "素直になれない" not in traits.only_b
    # 片側のみは相手側に存在しない。
    for x in traits.only_a:
        assert x not in traits.only_b


def test_diff_scalars_include_display_name() -> None:
    d = diff_attributes("tsundere", "dandere")
    fields = {s.field for s in d.scalars}
    assert "display_name" in fields
    assert "weight_dimension" in fields


def test_diff_unknown_attribute_raises() -> None:
    with pytest.raises(KeyError):
        diff_attributes("tsundere", "nonexistent_xyz")


def test_diff_categories_reported() -> None:
    d = diff_attributes("tsundere", "keigo")
    assert d.category_a == "personality"
    assert d.category_b == "speech"
