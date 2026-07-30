"""skills/*/SKILL.md の front-matter を YAML として検証する。

version が SemVer であることに加え、front-matter が **YAML として実際に
パースできる** ことを検証する。行 grep だけだと front-matter が壊れていても
通ってしまう: 実際に `claude-hersona` / `gpt-hersona` の 2 本は
`description:` の行頭に半角スペース 1 つが入って `yaml.safe_load` が
ScannerError を投げる状態のまま、旧テスト (`^version:` の行 grep) を
6/6 pass で通過していた。Agent Skills 準拠のランタイムはこの 2 本を
ロードできない。
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_FILES = sorted((REPO_ROOT / "skills").glob("*/SKILL.md"))
SEMVER = re.compile(r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.]+)?$")


def _split_front_matter(path: Path) -> str:
    """先頭 `---` から次の `---` までを front-matter として切り出す。"""
    text = path.read_text("utf-8")
    assert text.startswith("---"), f"{path} が front-matter (---) で始まっていない"
    parts = text.split("---", 2)
    assert len(parts) >= 3, f"{path} の front-matter が閉じられていない"
    return parts[1]


def _load_front_matter(path: Path) -> dict:
    raw = _split_front_matter(path)
    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as exc:  # 行頭の余分な空白・タブなどはここで落ちる
        pytest.fail(f"{path} の front-matter が YAML として不正: {exc}")
    assert isinstance(data, dict), f"{path} の front-matter が mapping でない: {type(data)}"
    return data


@pytest.mark.parametrize("skill", SKILL_FILES, ids=lambda p: p.parent.name)
def test_front_matter_parses_as_yaml(skill: Path) -> None:
    """front-matter が YAML mapping としてロードできる (スキルが読み込める前提)。"""
    _load_front_matter(skill)


@pytest.mark.parametrize("skill", SKILL_FILES, ids=lambda p: p.parent.name)
def test_front_matter_has_name_and_description(skill: Path) -> None:
    """`name` / `description` はスキル検出に必須。"""
    data = _load_front_matter(skill)
    for key in ("name", "description"):
        assert data.get(key), f"{skill} の front-matter に {key} が無い / 空"
        assert isinstance(data[key], str), f"{skill} の {key} が文字列でない"


@pytest.mark.parametrize("skill", SKILL_FILES, ids=lambda p: p.parent.name)
def test_skill_version_is_semver(skill: Path) -> None:
    data = _load_front_matter(skill)
    v = data.get("version")
    assert v is not None, f"{skill} に version front-matter が無い"
    assert SEMVER.match(str(v)), f"{skill} の version が SemVer 形式でない: {v!r}"
