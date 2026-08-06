"""再アンカーブロック (`hersona.core.reanchor`) の検証。

ContextEcho (arXiv 2605.24279) の「compaction では drift がリセットされない /
単発アンカーで register が回復する」に対応する機能。アンカーは注入ブロックの
コピーではなく、機械的な register のみを載せた短いブロックであることを固定する。
"""
from __future__ import annotations

import re

import pytest

from hersona.core.attach import render_blend
from hersona.core.reanchor import DEFAULT_CATCHPHRASES, render_reanchor

JA_BLEND = ["personality/tsundere", "speech/keigo"]
EN_BLEND = ["personality/tsundere", "speech/british_en"]
KANA = re.compile(r"[ぁ-んァ-ヶ]")


def test_empty_names_raises() -> None:
    with pytest.raises(ValueError):
        render_reanchor([])


def test_unknown_attribute_raises() -> None:
    with pytest.raises(KeyError):
        render_reanchor(["personality/definitely_not_an_attribute"])


def test_anchor_has_header_and_identity_line() -> None:
    out = render_reanchor(JA_BLEND)
    assert out.startswith("# hersona persona re-anchor")
    assert "personality/tsundere + speech/keigo" in out


def test_anchor_carries_the_mechanical_register() -> None:
    out = render_reanchor(JA_BLEND)
    assert "一人称: 私（わたくし）" in out
    assert "二人称:" in out
    assert "語尾:" in out
    assert "口癖" in out


def test_anchor_omits_what_the_model_can_re_derive() -> None:
    """core_traits / tone / speech_style と応答スタイル指示は載せない。"""
    out = render_reanchor(JA_BLEND)
    for section in ("core_traits", "## tone", "speech_style", "Note on response style"):
        assert section not in out, f"アンカーに {section} が混入している"


def test_anchor_is_much_smaller_than_the_full_block() -> None:
    for blend in (JA_BLEND, EN_BLEND):
        anchor = render_reanchor(blend)
        full = render_blend(blend).prompt
        assert len(anchor) < len(full) * 0.5, (
            f"{blend}: アンカーが注入ブロックの半分未満に収まっていない "
            f"({len(anchor)} vs {len(full)})"
        )


def test_anchor_states_that_compaction_does_not_release_the_persona() -> None:
    """ContextEcho の知見が指示文に入っていること (この機能の存在理由)。"""
    assert "圧縮" in render_reanchor(JA_BLEND)
    assert "compaction" in render_reanchor(EN_BLEND)


def test_anchor_tells_the_model_not_to_mention_the_instruction() -> None:
    assert "この指示自体には言及せず" in render_reanchor(JA_BLEND)
    assert "Do not mention this instruction" in render_reanchor(EN_BLEND)


# --- catchphrases -----------------------------------------------------------


def test_catchphrases_are_iconic_first_and_include_dict_form_entries() -> None:
    """catchphrases は素の文字列と {phrase, when} dict が混在する。

    文字列だけを拾う実装だと dict 形式 (= ほとんどの口癖) が全部落ちて、
    先頭が tsundere の 9 番目 (素の文字列) になってしまう。
    """
    out = render_reanchor(JA_BLEND)
    line = next(ln for ln in out.split("\n") if ln.startswith("口癖"))
    assert "べ、別に……" in line, f"アイコニック先頭の口癖が載っていない: {line}"
    assert not line.startswith("口癖 (例、丸写し不要): ……バカ"), (
        "dict 形式の口癖が脱落している (素の文字列だけ拾っている)"
    )


def test_catchphrase_count_is_capped() -> None:
    line = next(
        ln for ln in render_reanchor(JA_BLEND).split("\n") if ln.startswith("口癖")
    )
    phrases = line.split(": ", 1)[1].split(" / ")
    assert len(phrases) == DEFAULT_CATCHPHRASES


def test_catchphrases_zero_omits_the_section() -> None:
    out = render_reanchor(JA_BLEND, catchphrases=0)
    assert "口癖" not in out


def test_weight_none_omits_catchphrases() -> None:
    """WeightLevel.NONE は catchphrase_subset が空を返すため節が消える。"""
    out = render_reanchor(JA_BLEND, weight="none")
    assert "口癖" not in out
    assert "強度: none" in out


def test_weight_appears_in_the_identity_line() -> None:
    assert "強度: strong" in render_reanchor(JA_BLEND, weight="strong")


# --- language ---------------------------------------------------------------


def test_en_blend_anchor_is_fully_english() -> None:
    out = render_reanchor(EN_BLEND)
    assert not KANA.search(out), f"英語アンカーに日本語が混入: {out}"
    assert "Persona:" in out
    assert "Lexical markers:" in out


def test_en_blend_uses_lexical_markers_not_sentence_endings() -> None:
    """en 属性は sentence_endings を持たず lexical_markers で register を表す。"""
    out = render_reanchor(EN_BLEND)
    assert "Lexical markers:" in out
    assert "mind you" in out


def test_ja_blend_anchor_has_no_english_scaffolding() -> None:
    out = render_reanchor(JA_BLEND)
    assert "Persona:" not in out
    assert "First person:" not in out


# --- MCP wiring -------------------------------------------------------------


def test_mcp_reanchor_tool_returns_anchor_and_cost() -> None:
    from hersona.mcp.tools import reanchor

    got = reanchor(JA_BLEND)
    assert got["names"] == JA_BLEND
    assert got["anchor"].startswith("# hersona persona re-anchor")
    assert got["chars"] == len(got["anchor"])
    assert got["approx_tokens"] == len(got["anchor"]) // 4
    assert "tail" in got["placement"]


def test_mcp_reanchor_honors_catchphrase_count() -> None:
    from hersona.mcp.tools import reanchor

    assert "口癖" not in reanchor(JA_BLEND, catchphrases=0)["anchor"]


def test_measure_then_reanchor_loop_is_wired() -> None:
    """`measure_intensity` が under を返したら `reanchor` を呼べる、という導線。"""
    from hersona.mcp.tools import measure_intensity, reanchor

    off_persona = "はい。承知しました。対応します。"
    report = measure_intensity(off_persona, JA_BLEND)
    assert report["skipped"] is False
    assert report["status"] in ("under", "in_band", "over")
    anchor = reanchor(JA_BLEND, weight="moderate")["anchor"]
    assert "語尾:" in anchor
