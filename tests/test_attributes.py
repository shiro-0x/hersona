"""Unit tests for hersona v1.0 attribute templates (T2).

v0.x 時代の data/<title>/<character>.yaml 統合テスト (test_legacy_score.py) は
v1.0 で data/ 形式が完全廃止されたことに伴い削除済み。

本ファイルは v1.0 の中核である attributes/ 配下のテンプレートが
- 59 属性 (personality 20 / speech 20 / archetype 9 / visual 5 / hobby 5) 揃っている
- すべて attribute.schema.json に違反しない
- ファイル名と attribute_name が一致する
- カテゴリ別に分類されている
ことを確認する回帰テスト。

スコア検証 (_legacy_score / _weighted_score) は v0.x 機能であり v1.0 では
persona_attach.py ごと削除されたため、本ファイルには含めない。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import jsonschema
import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
ATTRIBUTES_DIR = REPO_ROOT / "attributes"
SCHEMA_PATH = REPO_ROOT / "schema" / "attribute.schema.json"


def _load_schema() -> dict:
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        return json.load(f)


def _all_attribute_paths() -> list[Path]:
    return sorted(ATTRIBUTES_DIR.rglob("*.yaml"))


def _load(p: Path) -> dict:
    with open(p, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def test_attributes_dir_exists() -> None:
    assert ATTRIBUTES_DIR.exists(), f"{ATTRIBUTES_DIR} が存在しません"
    assert ATTRIBUTES_DIR.is_dir(), f"{ATTRIBUTES_DIR} はディレクトリである必要があります"


def test_schema_exists() -> None:
    assert SCHEMA_PATH.exists(), f"{SCHEMA_PATH} が存在しません"


def test_all_52_attributes_present() -> None:
    """64 属性 (personality 20 / speech 25 / archetype 9 / visual 5 / hobby 5)。

    speech 25 = ja 20 + en 5 (Phase 5: formal/casual/blunt/southern_us/british _en)。
    """
    paths = _all_attribute_paths()
    names = [p.stem for p in paths]
    assert len(names) == 64, f"64 属性あるはずだが {len(names)} 件: {names}"

    by_cat: dict[str, list[str]] = {
        "personality": [], "speech": [], "archetype": [], "visual": [], "hobby": []
    }
    for p in paths:
        rel = p.relative_to(ATTRIBUTES_DIR)
        if rel.parts[0] in by_cat:
            by_cat[rel.parts[0]].append(p.stem)

    assert len(by_cat["personality"]) == 20, by_cat
    assert len(by_cat["speech"]) == 25, by_cat
    assert len(by_cat["archetype"]) == 9, by_cat
    assert len(by_cat["visual"]) == 5, by_cat
    assert len(by_cat["hobby"]) == 5, by_cat


@pytest.mark.parametrize("yaml_path", _all_attribute_paths(), ids=lambda p: str(p.relative_to(REPO_ROOT)))
def test_each_attribute_validates_against_schema(yaml_path: Path) -> None:
    schema = _load_schema()
    data = _load(yaml_path)
    try:
        jsonschema.validate(data, schema)
    except jsonschema.ValidationError as e:
        pytest.fail(f"{yaml_path.name}: スキーマ違反 @ {list(e.absolute_path)}: {e.message}")


@pytest.mark.parametrize("yaml_path", _all_attribute_paths(), ids=lambda p: str(p.relative_to(REPO_ROOT)))
def test_attribute_uses_i18n_format(yaml_path: Path) -> None:
    """公開属性は i18n ブロック形式 (BASE=en + i18n.ja) に移行済みであること。

    旧 suffix ペア (display_name_ja/en, description_ja/en) は残さない。
    """
    data = _load(yaml_path)
    assert "display_name" in data, f"{yaml_path.name}: BASE display_name が無い"
    assert "description" in data, f"{yaml_path.name}: BASE description が無い"
    legacy = [
        k
        for k in ("display_name_ja", "display_name_en", "description_ja", "description_en")
        if k in data
    ]
    assert not legacy, f"{yaml_path.name}: 旧形式キーが残存: {legacy}"
    assert data.get("i18n", {}).get("ja", {}).get("display_name"), (
        f"{yaml_path.name}: i18n.ja.display_name が無い"
    )


@pytest.mark.parametrize("yaml_path", _all_attribute_paths(), ids=lambda p: str(p.relative_to(REPO_ROOT)))
def test_filename_matches_attribute_name(yaml_path: Path) -> None:
    data = _load(yaml_path)
    assert data.get("attribute_name") == yaml_path.stem, (
        f"{yaml_path}: attribute_name '{data.get('attribute_name')}' が "
        f"ファイル名 '{yaml_path.stem}' と一致しない"
    )


@pytest.mark.parametrize("yaml_path", _all_attribute_paths(), ids=lambda p: str(p.relative_to(REPO_ROOT)))
def test_path_category_matches_attribute_category(yaml_path: Path) -> None:
    rel = yaml_path.relative_to(ATTRIBUTES_DIR)
    path_category = rel.parts[0]
    data = _load(yaml_path)
    assert data.get("attribute_category") == path_category, (
        f"{yaml_path}: パスカテゴリ '{path_category}' と "
        f"attribute_category '{data.get('attribute_category')}' が不一致"
    )


def test_no_data_directory() -> None:
    """v1.0 で data/ ディレクトリは完全廃止。"""
    data_root = REPO_ROOT / "data"
    assert not data_root.exists(), (
        f"{data_root} がまだ存在します。v1.0 で data/ 形式は完全廃止されました。"
    )


def test_validate_py_runs_clean() -> None:
    """scripts/validate.py を実走し、エラー 0 件で exit 0 を確認。"""
    import subprocess
    proc = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "validate.py")],
        capture_output=True, text=True, cwd=REPO_ROOT,
    )
    assert proc.returncode == 0, (
        f"validate.py exit {proc.returncode}\n"
        f"stdout: {proc.stdout}\nstderr: {proc.stderr}"
    )
