"""Character Card V3 (`chara_card_v3`) エクスポートの検証。

SillyTavern / RisuAI / Agnai などが読む相互運用形式。hersona は汎用属性
ライブラリなのでキャラクター実体を捏造しない — 導出できるフィールドだけを埋め、
場面・挨拶は空のままにする、という方針を機械的に固定する。
"""
from __future__ import annotations

import json

import pytest

from hersona.core.export import (
    CHARACTER_CARD_SPEC,
    CHARACTER_CARD_SPEC_VERSION,
    EXPORT_FORMATS,
    export_blend,
    export_for_character_card_v3,
)

JA_BLEND = ["tsundere", "keigo"]
EN_BLEND = ["tsundere", "british_en"]


def _card(names: list[str], **kw) -> dict:
    """`export_for_character_card_v3` を直接呼ぶ (persona_lock は付かない)。

    persona_lock の付加は `export_blend` がディスパッチ前に行う既存の規約
    (openai_assistants / langchain も同じ)。lock 依存の検証は `_card_via_blend`。
    """
    return json.loads(export_for_character_card_v3(names, **kw))


def _card_via_blend(names: list[str], **kw) -> dict:
    """`export_blend` 経由 (persona_lock が既定で付く)。"""
    return json.loads(export_blend(names, fmt="character_card_v3", **kw))


# --- envelope ---------------------------------------------------------------


def test_format_is_registered() -> None:
    assert "character_card_v3" in EXPORT_FORMATS


def test_export_blend_routes_to_the_card_exporter() -> None:
    out = json.loads(export_blend(JA_BLEND, fmt="character_card_v3"))
    assert out["spec"] == CHARACTER_CARD_SPEC


def test_v3_envelope_shape() -> None:
    card = _card(JA_BLEND)
    assert card["spec"] == "chara_card_v3"
    assert card["spec_version"] == CHARACTER_CARD_SPEC_VERSION == "3.0"
    assert isinstance(card["data"], dict)


def test_all_v3_fields_are_present() -> None:
    data = _card(JA_BLEND)["data"]
    for field in (
        "name",
        "description",
        "personality",
        "scenario",
        "first_mes",
        "mes_example",
        "system_prompt",
        "post_history_instructions",
        "alternate_greetings",
        "tags",
        "creator",
        "character_version",
        "creator_notes",
        "extensions",
    ):
        assert field in data, f"V3 フィールド {field} が無い"


def test_output_is_valid_json_and_utf8_readable() -> None:
    raw = export_for_character_card_v3(JA_BLEND)
    assert "\\u" not in raw, "ensure_ascii が有効になっている (日本語が読めない)"
    json.loads(raw)


# --- derived fields ---------------------------------------------------------


def test_description_and_system_prompt_are_the_injection_block() -> None:
    from hersona.core.attach import render_blend

    data = _card_via_blend(JA_BLEND)["data"]
    expected = render_blend([*JA_BLEND, "persona_lock"]).prompt
    assert data["description"] == expected
    assert data["system_prompt"] == expected


def test_personality_lists_core_traits() -> None:
    data = _card(JA_BLEND)["data"]
    assert "素直になれない" in data["personality"]
    assert data["personality"].startswith("- ")


def test_mes_example_uses_sillytavern_conventions() -> None:
    data = _card(JA_BLEND)["data"]
    assert data["mes_example"].startswith("<START>")
    assert "{{char}}: " in data["mes_example"]


def test_mes_example_can_be_disabled() -> None:
    assert _card(JA_BLEND, example_count=0)["data"]["mes_example"] == ""


def test_tags_include_hersona_and_attribute_tags() -> None:
    tags = _card(JA_BLEND)["data"]["tags"]
    assert tags[0] == "hersona"
    assert len(tags) > 1


def test_extensions_carry_the_hersona_recipe() -> None:
    ext = _card_via_blend(JA_BLEND)["data"]["extensions"]["hersona"]
    assert ext["blend"] == [*JA_BLEND, "persona_lock"]
    assert ext["weight"] == "moderate"
    assert ext["content_lang"] == "ja"


def test_use_case_lands_in_extensions() -> None:
    ext = _card(JA_BLEND, use_case="tutor")["data"]["extensions"]["hersona"]
    assert ext["use_case"] == "tutor"


# --- the "do not invent a character" policy ---------------------------------


def test_scenario_and_first_mes_are_empty_by_default() -> None:
    """hersona に場面・挨拶の概念は無いので捏造しない。"""
    data = _card(JA_BLEND)["data"]
    assert data["scenario"] == ""
    assert data["first_mes"] == ""
    assert data["alternate_greetings"] == []


def test_scenario_and_first_mes_can_be_supplied() -> None:
    data = _card(JA_BLEND, first_mes="……何よ。", scenario="放課後の教室")["data"]
    assert data["first_mes"] == "……何よ。"
    assert data["scenario"] == "放課後の教室"


def test_creator_notes_explain_what_is_empty_and_why() -> None:
    notes = _card(EN_BLEND)["data"]["creator_notes"]
    assert "first_mes" in notes
    assert "scenario" in notes


def test_card_name_defaults_to_the_blend_without_persona_lock() -> None:
    """persona_lock は維持用の内部属性なのでカード名に出さない。"""
    assert _card(JA_BLEND)["data"]["name"] == "tsundere + keigo"


def test_card_name_can_be_overridden() -> None:
    assert _card(JA_BLEND, card_name="Aoi")["data"]["name"] == "Aoi"


# --- post_history_instructions ---------------------------------------------


def test_post_history_holds_the_persona_lock_intent() -> None:
    data = _card_via_blend(JA_BLEND)["data"]
    assert data["post_history_instructions"]
    assert "口調" in data["post_history_instructions"]


def test_post_history_does_not_leak_hersona_internals() -> None:
    """SOUL.md / `hersona soul` はカードの外の世界。カード内で参照してはいけない。"""
    for blend in (JA_BLEND, EN_BLEND):
        text = _card_via_blend(blend)["data"]["post_history_instructions"]
        for leak in ("SOUL", "hersona", "/new", "--no-persona-lock"):
            assert leak not in text, f"{blend}: post_history に {leak} が漏れている"


def test_post_history_is_empty_without_persona_lock() -> None:
    raw = export_blend(JA_BLEND, fmt="character_card_v3", persona_lock=False)
    assert json.loads(raw)["data"]["post_history_instructions"] == ""


def test_direct_exporter_does_not_apply_persona_lock() -> None:
    """既存エクスポータと同じ規約: lock の付加は `export_blend` の責務。"""
    assert _card(JA_BLEND)["data"]["post_history_instructions"] == ""
    assert _card(JA_BLEND)["data"]["extensions"]["hersona"]["blend"] == JA_BLEND


# --- language ---------------------------------------------------------------


def test_en_blend_card_is_english() -> None:
    data = _card_via_blend(EN_BLEND)["data"]
    assert "Stay in this persona's voice" in data["post_history_instructions"]
    assert "generic attribute library" in data["creator_notes"]


def test_ja_blend_card_is_japanese() -> None:
    data = _card(JA_BLEND)["data"]
    assert "汎用属性ライブラリ" in data["creator_notes"]


# --- errors -----------------------------------------------------------------


def test_unknown_attribute_raises() -> None:
    with pytest.raises(KeyError):
        export_for_character_card_v3(["definitely_not_an_attribute"])
