"""wheel パッケージングの回帰テスト (P0-1)。

attributes/ と schema/ が wheel に同梱され、開発用 scripts/ が漏れていないことを
ビルド成果物の中身で検証する。hersona.core.paths の二段解決も確認する。
"""
from __future__ import annotations

import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def wheel_path(tmp_path_factory: pytest.TempPathFactory) -> Path:
    out = tmp_path_factory.mktemp("dist")
    proc = subprocess.run(
        ["uv", "build", "--wheel", "--out-dir", str(out)],
        capture_output=True, text=True, cwd=REPO_ROOT,
    )
    if proc.returncode != 0:  # uv が無い環境では hatchling 直叩きにフォールバック
        proc = subprocess.run(
            [sys.executable, "-m", "hatchling", "build", "-t", "wheel", "-d", str(out)],
            capture_output=True, text=True, cwd=REPO_ROOT,
        )
    assert proc.returncode == 0, f"wheel build failed:\n{proc.stdout}\n{proc.stderr}"
    wheels = list(out.glob("hersona-*.whl"))
    assert wheels, f"wheel が生成されていない: {list(out.iterdir())}"
    return wheels[0]


def test_wheel_contains_attributes_and_schema(wheel_path: Path) -> None:
    names = zipfile.ZipFile(wheel_path).namelist()
    yaml_count = sum(
        1 for n in names if n.startswith("hersona/data/attributes/") and n.endswith(".yaml")
    )
    assert yaml_count >= 64, f"attributes YAML が不足: {yaml_count} 件"
    assert "hersona/data/attributes/personality/tsundere.yaml" in names
    assert "hersona/data/schema/attribute.schema.json" in names


def test_wheel_does_not_leak_dev_scripts(wheel_path: Path) -> None:
    leaked = [n for n in zipfile.ZipFile(wheel_path).namelist() if n.startswith("scripts/")]
    assert not leaked, f"開発用 scripts/ が wheel に混入: {leaked[:5]}"


def test_paths_resolve_in_repo_layout() -> None:
    """リポジトリ直置きでは repo 直下を解決する (wheel 側は publish.yml の smoke test で担保)。"""
    from hersona.core.paths import attribute_schema_path, public_attributes_root

    assert public_attributes_root() == REPO_ROOT / "attributes"
    assert attribute_schema_path() == REPO_ROOT / "schema" / "attribute.schema.json"


def test_version_matches_pyproject() -> None:
    """__init__.py の __version__ が pyproject.toml の version と一致すること。

    hersona/__init__.py は importlib.metadata から動的取得する設計 (軸A 統一, 2026-06-17)。
    pyproject.toml を唯一の真実とし、ハードコード値 ('0.0.1') の残存を検出する。
    """
    import tomllib

    import hersona

    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text("utf-8"))
    declared = pyproject["project"]["version"]
    # editable インストール下では importlib.metadata が拾えるはず。
    # 拾えない環境 (+dev) はスキップせず、最低限ハードコード値でないことを保証。
    assert hersona.__version__ != "0.0.1", "旧ハードコード値が残存している"
    if not hersona.__version__.endswith("+dev"):
        assert hersona.__version__ == declared, (
            f"version 不一致: __init__={hersona.__version__} pyproject={declared}"
        )
