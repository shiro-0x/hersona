"""skills/*/SKILL.md の version front-matter が SemVer 形式であることを検証。"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_FILES = sorted((REPO_ROOT / "skills").glob("*/SKILL.md"))
SEMVER = re.compile(r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.]+)?$")


def _read_version(path: Path) -> str | None:
    for line in path.read_text("utf-8").splitlines():
        m = re.match(r"^version:\s*(.+?)\s*$", line)
        if m:
            return m.group(1)
    return None


@pytest.mark.parametrize("skill", SKILL_FILES, ids=lambda p: p.parent.name)
def test_skill_version_is_semver(skill: Path) -> None:
    v = _read_version(skill)
    assert v is not None, f"{skill} に version front-matter が無い"
    assert SEMVER.match(v), f"{skill} の version が SemVer 形式でない: {v!r}"
