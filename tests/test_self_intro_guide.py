"""Tests for self-intro guide merge and memory lint helpers."""

from __future__ import annotations

import json
from pathlib import Path

from hersona.core.self_intro import (
    lint_memory_self_intro_canonical,
    merge_self_intro_guide,
    self_intro_guide_defaults,
)


def test_guide_defaults_ja() -> None:
    d = self_intro_guide_defaults("ja")
    assert "self_intro_style" in d
    assert "privacy_inner_circle" in d
    assert "self-introduction.ja" in d["self_intro_style"]


def test_merge_guide_fills_missing_keys() -> None:
    merged = merge_self_intro_guide({"likes": "tea"}, lang="ja")
    assert merged is not None
    assert merged["likes"] == "tea"
    assert "self_intro_style" in merged
    assert "privacy_inner_circle" in merged


def test_merge_guide_none_returns_defaults_only() -> None:
    merged = merge_self_intro_guide(None, lang="en")
    assert merged is not None
    assert set(merged.keys()) == {"self_intro_style", "privacy_inner_circle"}
    assert "self-introduction.md" in merged["self_intro_style"]


def test_lint_memory_sona_example() -> None:
    repo = Path(__file__).resolve().parent.parent
    data = json.loads((repo / "examples" / "sona-self-intro-memory.json").read_text(encoding="utf-8"))
    r = lint_memory_self_intro_canonical(
        data, allow_handles=frozenset({"hersona_agent"}), canonical=True
    )
    assert r is not None
    assert r.ok


def test_lint_memory_missing_canonical_returns_none() -> None:
    assert lint_memory_self_intro_canonical({"likes": "x"}) is None
