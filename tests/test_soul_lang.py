"""SOUL.md / ターゲットファイルの章枠組みがブレンドのコンテンツ言語に追従することを検証。

以前は本文 (core_traits / tone / catchphrases) だけが `content_i18n` で言語解決され、
章見出し・ラベル・一人称/二人称の既定値・強度ガイドライン・`notes` 由来の行動ルールは
日本語固定だった。その結果 `--lang en` + 英語 speech 属性でも、生成される
CLAUDE.md / AGENTS.md に「## 1. Name (エージェント名)」「**一人称**: 私」や
日本語の notes が混入していた。
"""
from __future__ import annotations

import re

from hersona.core.soul import render_soul
from hersona.core.targets import render_for_target

KANA = re.compile(r"[ぁ-んァ-ヶ]")

# 英語ペルソナ: 英語 speech 属性 + en 訳を持つ personality
EN_BLEND = ["personality/tsundere", "speech/british_en"]
JA_BLEND = ["personality/tsundere", "speech/keigo"]


def _en_target(target: str = "claude") -> str:
    return render_for_target(target, EN_BLEND, weight="moderate")


def test_en_blend_target_file_has_no_japanese_at_all() -> None:
    """英語ブレンドの出力に仮名が 1 文字も混入しない (回帰の総合ガード)。"""
    out = _en_target()
    offenders = [line for line in out.split("\n") if KANA.search(line)]
    assert offenders == [], f"英語出力に日本語が混入: {offenders[:5]}"


def test_en_blend_uses_english_section_headings() -> None:
    out = _en_target()
    assert "## 1. Name" in out
    assert "## 2. Personality" in out
    assert "## 3. Tone" in out
    assert "## 4. Behavioral Guidelines" in out
    assert "エージェント名" not in out


def test_en_blend_uses_english_pronoun_labels() -> None:
    out = _en_target()
    assert "**First person**:" in out
    assert "**Second person**:" in out
    assert "**一人称**" not in out


def test_en_blend_does_not_inject_japanese_default_first_person() -> None:
    """`british_en` は first_person を持たないので、既定値が英語であること。"""
    out = _en_target()
    assert "**First person**: I" in out
    assert "私" not in out


def test_en_blend_takes_second_person_from_the_speech_attribute() -> None:
    """属性が second_person を宣言していれば既定値ではなくそれを使う。"""
    out = _en_target()
    assert "**Second person**: you / mate" in out


def test_en_blend_weight_guidance_is_english() -> None:
    out = _en_target()
    assert "### 4.1 Core rule (intensity: moderate)" in out
    assert "Standard intensity" in out
    assert "鉄則" not in out


def test_en_blend_drops_unlocalized_japanese_notes() -> None:
    """`notes` に en 訳が無く属性言語も違う場合、行動ルールへ混入させない。"""
    out = _en_target()
    section = out.split("### 4.2")[1].split("###")[0]
    assert not KANA.search(section), f"4.2 に日本語が混入: {section[:200]}"


def test_en_blend_intro_blockquote_is_english() -> None:
    out = _en_target()
    assert "Persona definition loaded by Claude Code at startup" in out
    assert "起動時に読み込む人格定義" not in out


def test_en_intro_names_the_right_tool_per_target() -> None:
    assert "loaded by Cursor at startup" in _en_target("cursor")
    assert "loaded by Gemini CLI at startup" in _en_target("gemini")
    assert "loaded by AGENTS.md-compatible agents at startup" in _en_target("codex")


def test_ja_blend_keeps_japanese_scaffolding() -> None:
    """日本語ブレンドの出力は従来どおり日本語のまま (後方互換)。"""
    out = render_for_target("claude", JA_BLEND, weight="moderate")
    assert "## 1. Name (エージェント名)" in out
    assert "**一人称**:" in out
    assert "### 4.1 鉄則 (強度: moderate)" in out
    assert "Claude Code が起動時に読み込む人格定義" in out


def test_ja_blend_first_person_comes_from_keigo_attribute() -> None:
    out = render_for_target("claude", JA_BLEND, weight="moderate")
    assert "**一人称**: 私（わたくし）" in out


def test_ja_blend_keeps_japanese_notes_as_behavioral_rules() -> None:
    """属性言語と一致する場合は notes 由来のルールを従来どおり載せる。"""
    out = render_for_target("claude", JA_BLEND, weight="moderate")
    section = out.split("### 4.2")[1].split("###")[0]
    assert KANA.search(section), "ja ブレンドで notes 由来のルールが落ちている"


def test_render_soul_hermes_path_is_localized_too() -> None:
    """`hersona soul` (Hermes 経路) も同じラベル解決を通る。"""
    out = render_soul(EN_BLEND, weight="moderate")
    assert "## 1. Name" in out
    assert "**First person**: I" in out
    assert not KANA.search(out.split("## 1. Name")[1])


def test_en_footer_is_english() -> None:
    out = render_soul(EN_BLEND, weight="moderate")
    assert "_Generated " in out
    assert "作成:" not in out
