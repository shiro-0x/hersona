"""属性ロード・ブレンド合成 (hersona.core.attach) の回帰テスト。

- load_attribute が公開属性を解決する
- ユーザー名前空間が公開属性を上書きする
- render_blend が core_traits / catchphrases を順序保持で統合する
- render_blend が conflict を検出してブロックに併記する
"""
from __future__ import annotations

from pathlib import Path

import pytest

from hersona.core.attach import available_attributes, load_attribute, render_blend
from hersona.core.authoring import build_attribute, save_attribute

REPO_ROOT = Path(__file__).resolve().parent.parent
ATTRIBUTES_DIR = REPO_ROOT / "attributes"


def test_load_public_attribute() -> None:
    data = load_attribute("tsundere", public_root=ATTRIBUTES_DIR, user_root=Path("/nonexistent"))
    assert data["attribute_name"] == "tsundere"
    assert data["attribute_category"] == "personality"


def test_load_unknown_raises() -> None:
    with pytest.raises(KeyError):
        load_attribute("nope", public_root=ATTRIBUTES_DIR, user_root=Path("/nonexistent"))


def test_user_namespace_overrides_public(tmp_path: Path) -> None:
    # tsundere を user 名前空間で上書き保存
    override = build_attribute(
        attribute_category="personality",
        attribute_name="tsundere",
        display_name_ja="独自ツンデレ",
        display_name_en="My Tsundere",
        weight_dimension="strong",
        description_ja="上書き版",
        description_en="overridden",
        examples=["ex"],
    )
    save_attribute(override, user_root=tmp_path)
    data = load_attribute("tsundere", public_root=ATTRIBUTES_DIR, user_root=tmp_path)
    assert data["display_name_ja"] == "独自ツンデレ"  # user 優先


def test_available_attributes_counts_public() -> None:
    attrs = available_attributes(public_root=ATTRIBUTES_DIR, user_root=Path("/nonexistent"))
    assert len(attrs) == 26
    assert attrs["tsundere"]["source"] == "public"


def test_render_blend_merges_fields() -> None:
    result = render_blend(
        ["tsundere", "keigo"],
        public_root=ATTRIBUTES_DIR,
        user_root=Path("/nonexistent"),
    )
    assert result.names == ["tsundere", "keigo"]
    assert "core_traits" in result.prompt
    assert "べ、別に……" in result.prompt  # tsundere の catchphrase
    assert result.conflicts == []


def test_render_blend_detects_conflict() -> None:
    result = render_blend(
        ["genki", "kuudere"],
        public_root=ATTRIBUTES_DIR,
        user_root=Path("/nonexistent"),
    )
    assert ("genki", "kuudere") in result.conflicts
    assert "conflict" in result.prompt.lower()


def test_render_blend_empty_raises() -> None:
    with pytest.raises(ValueError):
        render_blend([], public_root=ATTRIBUTES_DIR, user_root=Path("/nonexistent"))
