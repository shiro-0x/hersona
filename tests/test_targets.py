"""hersona.core.targets の回帰テスト (Claude Code / Codex / Cursor / Gemini 連携)。"""
from __future__ import annotations

from pathlib import Path

import pytest

from hersona.core.targets import (
    TARGETS,
    available_targets,
    render_for_target,
    resolve_target,
    write_target,
)


@pytest.fixture(autouse=True)
def _isolate_user_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("HERSONA_USER_DIR", str(tmp_path / "userattrs"))


# --- レジストリ -------------------------------------------------------------


def test_available_targets_covers_expected() -> None:
    targets = set(available_targets())
    assert {"claude", "codex", "cursor", "gemini"} <= targets


def test_resolve_target_alias_agents() -> None:
    spec = resolve_target("agents")
    assert spec.name == "codex"
    assert spec.filename == "AGENTS.md"


def test_resolve_target_unknown_raises() -> None:
    with pytest.raises(KeyError):
        resolve_target("no_such_target")


@pytest.mark.parametrize(
    "target,filename",
    [
        ("claude", "CLAUDE.md"),
        ("codex", "AGENTS.md"),
        ("cursor", ".cursorrules"),
        ("gemini", "GEMINI.md"),
    ],
)
def test_target_filenames(target, filename) -> None:
    assert TARGETS[target].filename == filename


# --- パス解決 ---------------------------------------------------------------


def test_resolve_path_project(tmp_path) -> None:
    spec = TARGETS["claude"]
    p = spec.resolve_path(global_=False, cwd=tmp_path)
    assert p == tmp_path / "CLAUDE.md"


def test_resolve_path_global() -> None:
    spec = TARGETS["claude"]
    p = spec.resolve_path(global_=True)
    assert p == Path.home() / ".claude" / "CLAUDE.md"


def test_resolve_path_global_without_home_subdir_uses_home() -> None:
    # cursor は home_subdir=None なのでホーム直下に置く
    spec = TARGETS["cursor"]
    p = spec.resolve_path(global_=True)
    assert p == Path.home() / ".cursorrules"


# --- レンダリング -----------------------------------------------------------


def test_render_for_target_uses_target_title() -> None:
    out = render_for_target("claude", ["tsundere", "keigo"], weight="strong")
    assert "# Persona (hersona)" in out
    # Hermes 専用の見出しは出さない
    assert "Hermes Agent ペルソナ定義" not in out
    # 4 要素は維持
    assert "Personality" in out
    assert "Tone" in out
    assert "Behavioral Guidelines" in out


def test_render_for_target_conflict_raises() -> None:
    with pytest.raises(ValueError):
        render_for_target("claude", ["airhead", "intellectual"])


# --- 書き出し ---------------------------------------------------------------


def test_write_target_creates_file(tmp_path) -> None:
    out = tmp_path / "CLAUDE.md"
    result = write_target("claude", ["tsundere"], weight="mild", path=out)
    assert out.exists()
    assert result.created is True
    assert result.target == "claude"
    assert "# Persona (hersona)" in out.read_text(encoding="utf-8")


def test_write_target_existing_raises_without_force(tmp_path) -> None:
    out = tmp_path / "AGENTS.md"
    write_target("codex", ["tsundere"], path=out)
    with pytest.raises(FileExistsError):
        write_target("codex", ["tsundere"], path=out)


def test_write_target_force_overwrites(tmp_path) -> None:
    out = tmp_path / "AGENTS.md"
    write_target("codex", ["tsundere"], path=out)
    result = write_target("codex", ["kuudere"], path=out, force=True)
    assert result.created is False
    assert "kuudere" in out.read_text(encoding="utf-8")


def test_write_target_creates_parent_dirs(tmp_path) -> None:
    out = tmp_path / "nested" / "dir" / "CLAUDE.md"
    write_target("claude", ["tsundere"], path=out)
    assert out.exists()


def test_write_target_alias_agents(tmp_path) -> None:
    out = tmp_path / "AGENTS.md"
    result = write_target("agents", ["tsundere"], path=out)
    assert result.target == "codex"
    assert out.exists()
