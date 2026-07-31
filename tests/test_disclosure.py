"""AI 開示ディレクティブ (`hersona.core.disclosure`) の検証。

`persona_lock` は「ペルソナを維持せよ」と指示するため、「あなたは AI ですか」に
素直に答えない方向にも効きうる。2026 年の companion chatbot 規制 (California
SB 243 等) はその答えを要求するので、ペルソナの声を保ったまま正直な答えを残す
opt-in ディレクティブを用意した。**opt-in であること**と**lock より優先する旨が
明記されること**を機械的に固定する。
"""
from __future__ import annotations

import json
import re

from hersona.core.attach import render_blend
from hersona.core.disclosure import (
    disclosure_directive,
    disclosure_meta_comment,
    render_disclosure_guidelines,
)
from hersona.core.export import export_blend
from hersona.core.soul import render_soul
from hersona.core.targets import render_for_target, write_target

JA_BLEND = ["tsundere", "keigo"]
EN_BLEND = ["tsundere", "british_en"]
KANA = re.compile(r"[ぁ-んァ-ヶ]")


# --- the directive itself ---------------------------------------------------


def test_directive_says_to_admit_being_an_ai() -> None:
    assert "AI であることをはっきり述べる" in disclosure_directive("ja")
    assert "say plainly that you are an AI" in disclosure_directive("en")


def test_directive_states_it_overrides_persona_lock() -> None:
    """これが無いと persona_lock と矛盾したまま両方注入されることになる。"""
    assert "persona lock" in disclosure_directive("ja")
    assert "優先する" in disclosure_directive("ja")
    assert "overrides" in disclosure_directive("en")
    assert "persona lock" in disclosure_directive("en")


def test_directive_forbids_claiming_human_attributes() -> None:
    assert "肉体" in disclosure_directive("ja")
    assert "physical body" in disclosure_directive("en")


def test_directive_has_a_crisis_carve_out() -> None:
    """SB 243 の自傷防止・クライシス紹介に対応する最小の逃げ道。"""
    assert "自傷" in disclosure_directive("ja")
    assert "crisis" in disclosure_directive("en")


def test_non_ja_languages_fall_back_to_english() -> None:
    for lang in ("en", "zh", "ko", ""):
        assert disclosure_directive(lang) == disclosure_directive("en")


def test_guidelines_are_bullets_for_the_soul_body() -> None:
    for lang in ("ja", "en"):
        bullets = render_disclosure_guidelines(lang)
        assert bullets
        assert all(b.startswith("- ") for b in bullets)


def test_meta_comment_reflects_state() -> None:
    assert disclosure_meta_comment(enabled=True).strip() == "<!-- ai_disclosure: on -->"
    assert disclosure_meta_comment(enabled=False).strip() == "<!-- ai_disclosure: off -->"


# --- opt-in across every path ----------------------------------------------


def test_blend_is_off_by_default() -> None:
    assert "AI 開示" not in render_blend(JA_BLEND).prompt


def test_blend_includes_it_when_requested() -> None:
    assert "AI 開示" in render_blend(JA_BLEND, disclosure=True).prompt


def test_soul_is_off_by_default() -> None:
    out = render_soul(JA_BLEND)
    assert "### 4.4" not in out
    assert "ai_disclosure: off" in out


def test_soul_adds_section_4_4_after_persona_lock() -> None:
    out = render_soul(JA_BLEND, disclosure=True)
    assert "### 4.3" in out and "### 4.4" in out
    assert out.index("### 4.3") < out.index("### 4.4"), (
        "「維持より優先」と書いてある節が lock より前にあると順序の意味が壊れる"
    )
    assert "ai_disclosure: on" in out


def test_target_files_are_off_by_default() -> None:
    assert "### 4.4" not in render_for_target("claude", JA_BLEND)


def test_target_files_include_it_when_requested() -> None:
    assert "### 4.4" in render_for_target("claude", JA_BLEND, disclosure=True)


def test_write_target_forwards_the_flag(tmp_path) -> None:
    result = write_target(
        "claude", JA_BLEND, path=tmp_path / "CLAUDE.md", disclosure=True
    )
    assert "### 4.4" in result.output_path.read_text("utf-8")


def test_every_export_format_carries_it() -> None:
    for fmt in (
        "markdown",
        "json",
        "messages",
        "openai_assistants",
        "langchain_system_message",
        "character_card_v3",
    ):
        out = export_blend(JA_BLEND, fmt=fmt, disclosure=True)
        assert "AI 開示" in out, f"{fmt} に開示ディレクティブが載っていない"


def test_export_formats_are_off_by_default() -> None:
    for fmt in ("markdown", "json", "character_card_v3"):
        assert "AI 開示" not in export_blend(JA_BLEND, fmt=fmt)


def test_character_card_carries_it_in_the_system_prompt() -> None:
    data = json.loads(export_blend(JA_BLEND, fmt="character_card_v3", disclosure=True))
    assert "AI 開示" in data["data"]["system_prompt"]


# --- language separation ----------------------------------------------------


def test_en_blend_gets_the_english_directive_only() -> None:
    prompt = render_blend(EN_BLEND, disclosure=True).prompt
    assert "AI disclosure" in prompt
    directive = prompt.split("## AI disclosure")[1]
    assert not KANA.search(directive), "英語ブレンドの開示節に日本語が混入"


def test_en_soul_gets_the_english_section_heading() -> None:
    out = render_soul(EN_BLEND, disclosure=True)
    assert "### 4.4 AI disclosure (overrides persona maintenance)" in out


# --- coexistence with persona_lock -----------------------------------------


def test_disclosure_and_persona_lock_coexist_in_soul() -> None:
    """両方が載ること自体が意図 — 矛盾は「優先する」の一文で解消する設計。"""
    out = render_soul(JA_BLEND, disclosure=True, persona_lock=True)
    assert "persona lock" in out.lower()
    assert "ペルソナ維持 (persona lock を含む) より優先する" in out


def test_disclosure_works_without_persona_lock() -> None:
    out = render_soul(JA_BLEND, disclosure=True, persona_lock=False)
    assert "### 4.3" not in out
    assert "AI 開示" in out
