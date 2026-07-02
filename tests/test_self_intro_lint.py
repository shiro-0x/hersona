"""Tests for hersona.core.self_intro (lint-intro)."""

from __future__ import annotations

import json
from pathlib import Path

from hersona.cli.app import main
from hersona.core.self_intro import (
    IntroLintResult,
    lint_self_intro,
    merge_self_intro_guide,
    self_intro_guide_defaults,
)

SONA_OK = """はじめまして、Sona です。いまは Hermes まわりの開発を一緒にやってます。
X では @hersona_agent って名前で、自分で読んだリリースや仕様のメモを出すことが多いかな。"""


def test_lint_pass_sona_snippet() -> None:
    r = lint_self_intro(SONA_OK, allow_handles=frozenset({"hersona_agent"}))
    assert r.ok
    assert r.violations == []


def test_lint_fail_ai_label() -> None:
    r = lint_self_intro("私はAIエージェントです。", allow_handles=frozenset())
    assert not r.ok
    assert any(v.rule == "ai_self_label" for v in r.violations)


def test_lint_fail_meta_soul() -> None:
    r = lint_self_intro("SOUL.md に書いてあります。", allow_handles=frozenset())
    assert not r.ok
    assert any(v.rule == "meta_implementation" for v in r.violations)


def test_lint_fail_unallowed_handle() -> None:
    r = lint_self_intro("Follow @someone_else for updates.", allow_handles=frozenset())
    assert not r.ok
    assert any(v.rule == "third_party_handle" for v in r.violations)


def test_lint_canonical_flags_master() -> None:
    r = lint_self_intro("マスターの開発を手伝っています。", canonical=True)
    assert not r.ok
    assert any(v.rule == "inner_circle_nickname" for v in r.violations)


def test_lint_sona_memory_file_canonical() -> None:
    repo = Path(__file__).resolve().parent.parent
    data = json.loads((repo / "examples" / "sona-self-intro-memory.json").read_text(encoding="utf-8"))
    r = lint_self_intro(
        data["self_intro_canonical"],
        allow_handles=frozenset({"hersona_agent"}),
        canonical=True,
    )
    assert r.ok, r.violations


def test_lint_result_to_dict() -> None:
    r = lint_self_intro("AIです")
    d = r.to_dict()
    assert d["ok"] is False
    assert isinstance(d["violations"], list)
    assert IntroLintResult(ok=True).to_dict()["ok"] is True


def test_cli_lint_intro_passes_allowed_handle(capsys) -> None:
    rc = main(["lint-intro", "--text", SONA_OK, "--allow-handle", "hersona_agent"])
    assert rc == 0
    assert "OK" in capsys.readouterr().out


def test_cli_lint_intro_fails_unallowed_handle(capsys) -> None:
    rc = main(["lint-intro", "--text", "Follow @someone_else."])
    assert rc == 1
    out = capsys.readouterr().out
    assert "third_party_handle" in out


def test_cli_lint_intro_json(capsys) -> None:
    rc = main(["lint-intro", "--text", "AIです", "--json"])
    assert rc == 1
    data = json.loads(capsys.readouterr().out)
    assert data["ok"] is False
    assert data["violations"][0]["rule"] == "ai_self_label"


def test_self_intro_guide_defaults_and_merge() -> None:
    defaults = self_intro_guide_defaults("ja")
    assert "self_intro_style" in defaults
    assert "privacy_inner_circle" in defaults
    merged = merge_self_intro_guide({"self_intro_style": "custom"}, lang="en")
    assert merged is not None
    assert merged["self_intro_style"] == "custom"
    assert "privacy_inner_circle" in merged


def test_cli_soul_with_self_intro_guide(capsys) -> None:
    rc = main(["soul", "tsundere", "--dry-run", "--with-self-intro-guide"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "self_intro_style" in out
    assert "privacy_inner_circle" in out


def test_cli_soul_lint_self_intro_strict_blocks_bad_canonical(capsys) -> None:
    bad_memory = json.dumps({"self_intro_canonical": "私はAIエージェントです。"})
    rc = main(
        [
            "soul",
            "tsundere",
            "--dry-run",
            "--memory",
            bad_memory,
            "--lint-self-intro-strict",
        ]
    )
    assert rc == 1
    captured = capsys.readouterr()
    assert "ai_self_label" in captured.err
