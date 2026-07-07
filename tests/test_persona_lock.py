"""Tests for default-on persona lock."""
from __future__ import annotations

from hersona.core.persona_lock import (
    apply_persona_lock,
    merge_memory_persona_lock,
    persona_lock_active,
)
from hersona.core.soul import render_soul


def test_apply_persona_lock_appends_once():
    out = apply_persona_lock(["tsundere"], enabled=True)
    assert "personality/persona_lock" in out
    assert apply_persona_lock(out, enabled=True) == out


def test_apply_persona_lock_disabled():
    assert apply_persona_lock(["tsundere"], enabled=False) == ["tsundere"]


def test_persona_lock_active():
    assert persona_lock_active(["personality/persona_lock"])
    assert not persona_lock_active(["tsundere"])


def test_render_soul_includes_persona_lock_by_default():
    text = render_soul(["tsundere"], weight="none", persona_lock=True)
    assert "persona_lock" in text
    assert "### 4.3 persona lock" in text
    assert "persona_lock: on" in text


def test_render_soul_no_lock_when_disabled():
    text = render_soul(["tsundere"], weight="none", persona_lock=False)
    assert "persona_lock: off" in text
    assert "### 4.3 persona lock" not in text


def test_merge_memory_persona_lock():
    merged = merge_memory_persona_lock({"likes": "tea"}, enabled=True, lang="ja")
    assert merged is not None
    assert "persona_lock" in merged
    assert merge_memory_persona_lock(None, enabled=True) is None
