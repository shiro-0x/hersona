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
from hersona.core.export import (
    EXPORT_FORMATS,
    export_blend,
    export_for_langchain_system_message,
    export_for_openai_assistants,
)


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


def test_export_markdown_with_use_case() -> None:
    md = export_blend(["tsundere"], fmt="markdown", use_case="programmer")
    assert "## Operating Mode: Programmer" in md
    assert "Inspect relevant files before editing." in md


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
    assert EXPORT_FORMATS == (
        "json",
        "messages",
        "markdown",
        "openai_assistants",
        "langchain_system_message",
    )


def _all_keys(obj: object) -> set[str]:
    """Recursively collect all dict keys in a JSON-like structure."""
    keys: set[str] = set()
    if isinstance(obj, dict):
        keys.update(obj.keys())
        for value in obj.values():
            keys.update(_all_keys(value))
    elif isinstance(obj, list):
        for item in obj:
            keys.update(_all_keys(item))
    return keys


def test_export_openai_assistants_structure() -> None:
    raw = export_for_openai_assistants(["tsundere", "keigo"], weight="strong")
    data = json.loads(raw)
    assert data["model"] == "gpt-4o"
    assert data["name"] == "hersona-blend"
    assert data["instructions"]
    meta = data["metadata"]
    # OpenAI Assistants API の metadata は string → string (v1.4.1 fix)。
    # hersona_blend / hersona_conflicts は JSON 文字列化されてる。
    assert json.loads(meta["hersona_blend"]) == ["tsundere", "keigo"]
    assert meta["hersona_weight"] == "strong"
    assert meta["hersona_content_lang"] == "ja"
    assert meta["hersona_version"]
    assert json.loads(meta["hersona_conflicts"]) == []


def test_export_openai_assistants_metadata_is_string_dict() -> None:
    """OpenAI Assistants API 互換性ガード (v1.4.1 regression)。

    metadata の値はすべて string 必須。list / dict / number があると
    実 API への POST で 400 エラーになる。
    """
    raw = export_for_openai_assistants(
        ["tsundere", "keigo", "heroine"], weight="moderate"
    )
    data = json.loads(raw)
    meta = data["metadata"]
    for key, value in meta.items():
        assert isinstance(value, str), (
            f"metadata.{key} must be str, got {type(value).__name__}: {value!r}"
        )
    # 実 API 制約: 16 keys max, value 512 chars max
    assert len(meta) <= 16
    for key, value in meta.items():
        assert len(value) <= 512, f"metadata.{key} exceeds 512 chars"


def test_export_openai_assistants_via_dispatch() -> None:
    direct = export_for_openai_assistants(["tsundere", "keigo"], weight="strong")
    via_blend = export_blend(["tsundere", "keigo"], weight="strong", fmt="openai_assistants")
    assert json.loads(direct) == json.loads(via_blend)


def test_export_openai_assistants_no_character_fields() -> None:
    raw = export_for_openai_assistants(["tsundere", "keigo"], weight="strong")
    data = json.loads(raw)
    forbidden = {"first_mes", "scenario", "character_book", "greeting", "description"}
    assert not (_all_keys(data) & forbidden)
    assert set(data["metadata"].keys()) == {
        "hersona_version",
        "hersona_blend",
        "hersona_weight",
        "hersona_content_lang",
        "hersona_conflicts",
    }


def test_export_langchain_system_message_structure() -> None:
    raw = export_for_langchain_system_message(["tsundere", "keigo"], weight="strong")
    data = json.loads(raw)
    assert data["type"] == "system"
    assert data["content"]
    assert data["additional_kwargs"] == {}
    meta = data["response_metadata"]
    assert meta["hersona_blend"] == ["tsundere", "keigo"]
    assert meta["hersona_weight"] == "strong"
    assert meta["hersona_content_lang"] == "ja"
    assert meta["hersona_version"]


def test_export_langchain_system_message_via_dispatch() -> None:
    direct = export_for_langchain_system_message(["tsundere", "keigo"], weight="strong")
    via_blend = export_blend(
        ["tsundere", "keigo"], weight="strong", fmt="langchain_system_message"
    )
    assert json.loads(direct) == json.loads(via_blend)


def test_export_formats_tuple_includes_new_formats() -> None:
    assert len(EXPORT_FORMATS) == 5
    assert EXPORT_FORMATS[-2:] == ("openai_assistants", "langchain_system_message")
