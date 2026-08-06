"""2026 年時点のエージェント規約ファイル形式への追従を検証。

- `.cursorrules` は 2024 年末に非推奨。現行は `.cursor/rules/*.mdc`
  (`description` / `globs` / `alwaysApply` の front-matter)。
- `AGENTS.md` は Linux Foundation 傘下 Agentic AI Foundation が stewardship を
  持つ事実上の標準だが Claude Code は native に読まないため、コミュニティの定石は
  「AGENTS.md を正本にして薄い CLAUDE.md から `@AGENTS.md` で import」。
"""
from __future__ import annotations

import pytest

from hersona.core.targets import (
    TARGET_ALIASES,
    available_targets,
    render_for_target,
    resolve_target,
    write_claude_import,
    write_target,
)

BLEND = ["tsundere", "keigo"]


# --- registry ---------------------------------------------------------------


def test_modern_targets_are_registered() -> None:
    targets = available_targets()
    assert "cursor_mdc" in targets
    assert "copilot" in targets
    # 既存ターゲットは維持 (後方互換)
    for legacy in ("claude", "codex", "cursor", "gemini"):
        assert legacy in targets


def test_cursor_rules_alias_resolves_to_mdc() -> None:
    assert TARGET_ALIASES["cursor-rules"] == "cursor_mdc"
    assert resolve_target("cursor-rules").name == "cursor_mdc"


def test_legacy_cursor_is_flagged_deprecated_with_a_replacement() -> None:
    assert resolve_target("cursor").deprecated_for == "cursor_mdc"


def test_modern_targets_are_not_flagged_deprecated() -> None:
    for name in ("claude", "codex", "cursor_mdc", "copilot", "gemini"):
        assert resolve_target(name).deprecated_for == ""


# --- .mdc front-matter ------------------------------------------------------


def test_cursor_mdc_emits_yaml_front_matter_first() -> None:
    out = render_for_target("cursor_mdc", BLEND)
    lines = out.split("\n")
    assert lines[0] == "---"
    assert "alwaysApply: true" in lines[:6]
    # front-matter が閉じてから本文の見出しが来る
    assert lines.index("---", 1) < lines.index("# Persona (hersona)")


def test_cursor_mdc_front_matter_parses_as_yaml() -> None:
    import yaml

    out = render_for_target("cursor_mdc", BLEND)
    fm = out.split("---", 2)[1]
    data = yaml.safe_load(fm)
    assert data["alwaysApply"] is True
    assert isinstance(data["description"], str) and data["description"]


def test_legacy_cursor_has_no_front_matter() -> None:
    out = render_for_target("cursor", BLEND)
    assert out.startswith("# Persona (hersona)")


def test_copilot_has_no_front_matter() -> None:
    assert render_for_target("copilot", BLEND).startswith("# Persona (hersona)")


# --- nested output paths ----------------------------------------------------


def test_cursor_mdc_writes_into_nested_rules_directory(tmp_path) -> None:
    result = write_target(
        "cursor_mdc", BLEND, path=tmp_path / ".cursor" / "rules" / "hersona-persona.mdc"
    )
    assert result.output_path.exists()
    assert result.output_path.parts[-3:] == (".cursor", "rules", "hersona-persona.mdc")


def test_cursor_mdc_default_path_is_relative_to_cwd(tmp_path) -> None:
    spec = resolve_target("cursor_mdc")
    p = spec.resolve_path(cwd=tmp_path)
    assert p == tmp_path / ".cursor" / "rules" / "hersona-persona.mdc"


def test_copilot_default_path_is_in_dot_github(tmp_path) -> None:
    p = resolve_target("copilot").resolve_path(cwd=tmp_path)
    assert p == tmp_path / ".github" / "copilot-instructions.md"


def test_write_target_creates_missing_parent_directories(tmp_path) -> None:
    """`.cursor/rules/` や `.github/` が無い状態から書ける。"""
    out = tmp_path / "proj"
    out.mkdir()
    result = write_target("copilot", BLEND, path=out / ".github" / "copilot-instructions.md")
    assert result.created is True
    assert result.output_path.read_text("utf-8").startswith("# Persona (hersona)")


# --- thin CLAUDE.md importing AGENTS.md -------------------------------------


def test_claude_import_writes_the_import_directive(tmp_path) -> None:
    result = write_claude_import(path=tmp_path / "CLAUDE.md")
    assert result.target == "claude_import"
    body = result.output_path.read_text("utf-8")
    assert "@AGENTS.md" in body
    assert result.created is True


def test_claude_import_is_thin_not_a_second_copy_of_the_persona(tmp_path) -> None:
    """人格本文を重複させないのがこのモードの目的。"""
    body = write_claude_import(path=tmp_path / "CLAUDE.md").content
    for section in ("## 1. Name", "## 2. Personality", "core_traits", "catchphrases"):
        assert section not in body, f"薄い CLAUDE.md に {section} が入っている"
    assert len(body.split("\n")) < 12


def test_claude_import_refuses_to_clobber_without_force(tmp_path) -> None:
    target = tmp_path / "CLAUDE.md"
    target.write_text("hand-written project memory", encoding="utf-8")
    with pytest.raises(FileExistsError):
        write_claude_import(path=target)
    # 既存内容は保持されている
    assert target.read_text("utf-8") == "hand-written project memory"


def test_claude_import_force_overwrites_and_reports_not_created(tmp_path) -> None:
    target = tmp_path / "CLAUDE.md"
    target.write_text("old", encoding="utf-8")
    result = write_claude_import(path=target, force=True)
    assert result.created is False
    assert "@AGENTS.md" in target.read_text("utf-8")


def test_agents_plus_import_pair_keeps_one_source_of_truth(tmp_path) -> None:
    """AGENTS.md が本文を持ち、CLAUDE.md はそれを指すだけ。"""
    agents = write_target("agents", BLEND, path=tmp_path / "AGENTS.md")
    claude = write_claude_import(path=tmp_path / "CLAUDE.md")
    assert "## 2. Personality" in agents.content
    assert "## 2. Personality" not in claude.content
    assert "@AGENTS.md" in claude.content
