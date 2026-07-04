"""Unit tests for hersona v1.0 attribute templates (T2).

v0.x 時代の data/<title>/<character>.yaml 統合テスト (test_legacy_score.py) は
v1.0 で data/ 形式が完全廃止されたことに伴い削除済み。

本ファイルは v1.0 の中核である attributes/ 配下のテンプレートが
- 206 属性 (personality 42 / speech 140 / archetype 9 / visual 5 / hobby 10) 揃っている
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

from tests.catalog_counts import PUBLIC_CATEGORY_COUNTS, TOTAL_PUBLIC_ATTRIBUTES

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


def test_all_attributes_present() -> None:
    """206 属性 (personality 42 / speech 140 / archetype 9 / visual 5 / hobby 10)。

    speech 140 = ja 25 + en 5 + archaic_otaku (Phase 8)
                  + 36 regional dialects (Phase 1)
                  + 25 character/subculture voices (Phase 3)
                  + 24 foreign-language registers (Phase 4)
                  + 18 anime-genre voices (Phase 5)
                  + mandarin_casual + keigo_zh + taiwan_mandarin (v1.5.0 multi-lang)
                  + banmal (Korean banmal / タメ口, v1.5.0 wave 2)
                  + jondaetmal (Korean jondaetmal / 敬語, v1.5.0 wave 2 PR-A5)
                  + seoul_casual (Korean Seoul casual / 서울말, v1.5.0 wave 2 PR-A6)。
    206 属性で v1.6.0 hobby expansion (B3) 完了。
    206 属性 (personality 42 / speech 140 / archetype 9 / visual 5 / hobby 10)。
    personality 42 = ja-base 35 + en-native 5 + hautaine + sociable (Phase 8)。
    """
    paths = _all_attribute_paths()
    names = [p.stem for p in paths]
    assert len(names) == TOTAL_PUBLIC_ATTRIBUTES, (
        f"{TOTAL_PUBLIC_ATTRIBUTES} 属性あるはずだが {len(names)} 件: {names}"
    )

    by_cat: dict[str, list[str]] = {
        "personality": [], "speech": [], "archetype": [], "visual": [], "hobby": []
    }
    for p in paths:
        rel = p.relative_to(ATTRIBUTES_DIR)
        if rel.parts[0] in by_cat:
            by_cat[rel.parts[0]].append(p.stem)

    assert len(by_cat["personality"]) == PUBLIC_CATEGORY_COUNTS["personality"], by_cat
    assert len(by_cat["speech"]) == PUBLIC_CATEGORY_COUNTS["speech"], by_cat
    assert len(by_cat["archetype"]) == PUBLIC_CATEGORY_COUNTS["archetype"], by_cat
    assert len(by_cat["visual"]) == PUBLIC_CATEGORY_COUNTS["visual"], by_cat
    assert len(by_cat["hobby"]) == PUBLIC_CATEGORY_COUNTS["hobby"], by_cat


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


# --- B3: visual image_prompt_tags -------------------------------------------

_VISUAL_NAMES = ["animal_ears", "glamorous", "glasses", "petite", "silver_hair"]


@pytest.mark.parametrize("name", _VISUAL_NAMES)
def test_visual_has_image_prompt_tags(name: str) -> None:
    """B3: visual 属性はすべて image_prompt_tags を持つ。"""
    path = ATTRIBUTES_DIR / "visual" / f"{name}.yaml"
    data = _load(path)
    tags = data.get("image_prompt_tags")
    assert isinstance(tags, list), f"{name}: image_prompt_tags がリストでない"
    assert len(tags) >= 1, f"{name}: image_prompt_tags が空"
    assert all(isinstance(t, str) and t for t in tags), f"{name}: image_prompt_tags に空文字が含まれる"


def test_image_prompt_tags_are_english(name: str = "animal_ears") -> None:
    """image_prompt_tags は英語タグ (ASCII 範囲) であること。"""
    path = ATTRIBUTES_DIR / "visual" / f"{name}.yaml"
    data = _load(path)
    for tag in data.get("image_prompt_tags", []):
        assert tag.isascii(), f"{name}: image_prompt_tags に非ASCII: {tag!r}"


# --- B4: speech first_person ------------------------------------------------

_FIRST_PERSON_ATTRS = {
    "ore_boy": ["オレ", "俺"],
    "boku_girl": ["ボク"],
    "washi": ["わし"],
    "gyaru": ["あたし", "うち"],
    "tomboy": ["あたし"],
    "princess_speech": ["わたくし", "私"],
    "archaic": ["我", "拙者"],
}


@pytest.mark.parametrize("name,expected_tokens", list(_FIRST_PERSON_ATTRS.items()))
def test_speech_has_first_person(name: str, expected_tokens: list[str]) -> None:
    """B4: 一人称軸を持つ speech 属性は first_person フィールドを持つ。"""
    path = ATTRIBUTES_DIR / "speech" / f"{name}.yaml"
    data = _load(path)
    fp = data.get("first_person", "")
    assert fp, f"{name}: first_person フィールドが空"
    tokens = [t.strip() for t in fp.split("/")]
    for expected in expected_tokens:
        assert any(expected in tok for tok in tokens), (
            f"{name}: first_person='{fp}' に '{expected}' が含まれない"
        )
