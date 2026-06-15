"""ブレンドエクスポート (hersona.core.export) の回帰テスト (ROADMAP C)。

- json: メタ情報 + system_prompt + 属性要約 + conflicts を構造化
- messages: role=system のチャットメッセージ列
- markdown: 注入ブロック素文 (render_blend と一致)
- 未知フォーマットは ValueError
"""
from __future__ import annotations

import json

import pytest

from hersona.core.attach import render_blend
from hersona.core.export import EXPORT_FORMATS, export_blend


def test_export_json_structure() -> None:
    raw = export_blend(["tsundere", "keigo"], weight="strong", fmt="json")
    data = json.loads(raw)
    assert data["hersona"]["names"] == ["tsundere", "keigo"]
    assert data["hersona"]["weight"] == "strong"
    assert data["hersona"]["content_lang"] == "ja"
    assert data["hersona"]["version"]
    assert "system_prompt" in data and data["system_prompt"]
    assert data["conflicts"] == []
    names = [a["name"] for a in data["attributes"]]
    assert names == ["tsundere", "keigo"]
    # 属性要約に core_traits / catchphrases が含まれる
    tsun = next(a for a in data["attributes"] if a["name"] == "tsundere")
    assert tsun["category"] == "personality"
    assert tsun["core_traits"]
    assert tsun["catchphrases"]


def test_export_json_includes_conflicts() -> None:
    data = json.loads(export_blend(["airhead", "intellectual"], fmt="json"))
    assert ["airhead", "intellectual"] in data["conflicts"]


def test_export_messages_format() -> None:
    raw = export_blend(["tsundere"], fmt="messages")
    msgs = json.loads(raw)
    assert isinstance(msgs, list) and len(msgs) == 1
    assert msgs[0]["role"] == "system"
    assert "tsundere" in msgs[0]["content"]


def test_export_markdown_matches_render_blend() -> None:
    md = export_blend(["tsundere", "keigo"], weight="mild", fmt="markdown")
    expected = render_blend(["tsundere", "keigo"], weight="mild").prompt
    assert md == expected


def test_export_default_format_is_json() -> None:
    raw = export_blend(["tsundere"])
    json.loads(raw)  # parses as JSON


def test_export_unknown_format_raises() -> None:
    with pytest.raises(ValueError):
        export_blend(["tsundere"], fmt="xml")


def test_export_first_person_surfaced() -> None:
    """speech 属性の first_person フィールドが要約に含まれる (B4 連携)。"""
    data = json.loads(export_blend(["ore_boy"], fmt="json"))
    ore = next(a for a in data["attributes"] if a["name"] == "ore_boy")
    assert ore.get("first_person")


def test_export_formats_constant() -> None:
    assert EXPORT_FORMATS == ("json", "messages", "markdown")
