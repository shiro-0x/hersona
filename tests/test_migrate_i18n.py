"""scripts/migrate_i18n (Phase 2 メタデータ移行) のテスト。"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent

# scripts/ はパッケージではないのでファイルパスから直接ロードする。
_spec = importlib.util.spec_from_file_location(
    "migrate_i18n", REPO_ROOT / "scripts" / "migrate_i18n.py"
)
migrate_i18n = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(migrate_i18n)


_LEGACY = {
    "attribute_category": "speech",
    "attribute_name": "keigo",
    "display_name_ja": "敬語",
    "display_name_en": "Keigo",
    "weight_dimension": "strong",
    "description_ja": "尊敬語を使う。",
    "description_en": "Uses honorifics.",
    "examples": ["お越しいただき、ありがとうございます"],
}


def test_migrate_data_maps_legacy_to_i18n() -> None:
    out = migrate_i18n.migrate_data(_LEGACY)
    assert out is not None
    assert out["display_name"] == "Keigo"
    assert out["description"] == "Uses honorifics."
    assert out["i18n"]["ja"]["display_name"] == "敬語"
    assert out["i18n"]["ja"]["description"] == "尊敬語を使う。"
    for legacy in ("display_name_ja", "display_name_en", "description_ja", "description_en"):
        assert legacy not in out


def test_migrate_data_orders_base_before_i18n() -> None:
    out = migrate_i18n.migrate_data(_LEGACY)
    keys = list(out)
    assert keys.index("display_name") < keys.index("i18n")
    assert keys.index("description") < keys.index("i18n")
    # attribute_name は先頭付近、i18n は末尾
    assert keys[-1] == "i18n"


def test_migrate_data_skips_new_format() -> None:
    new = {"attribute_name": "x", "display_name": "X", "description": "d"}
    assert migrate_i18n.migrate_data(new) is None


def test_migrate_data_skips_when_no_metadata() -> None:
    assert migrate_i18n.migrate_data({"attribute_name": "x"}) is None


def test_migrate_file_dry_run_does_not_write(tmp_path: Path) -> None:
    f = tmp_path / "a.yaml"
    f.write_text(yaml.safe_dump(_LEGACY, allow_unicode=True), encoding="utf-8")
    before = f.read_text(encoding="utf-8")
    changed = migrate_i18n.migrate_file(f, dry_run=True)
    assert changed is True
    assert f.read_text(encoding="utf-8") == before  # 書き込まれていない


def test_migrate_file_writes_new_format(tmp_path: Path) -> None:
    f = tmp_path / "a.yaml"
    f.write_text(yaml.safe_dump(_LEGACY, allow_unicode=True), encoding="utf-8")
    changed = migrate_i18n.migrate_file(f, dry_run=False)
    assert changed is True
    reloaded = yaml.safe_load(f.read_text(encoding="utf-8"))
    assert reloaded["display_name"] == "Keigo"
    assert reloaded["i18n"]["ja"]["display_name"] == "敬語"
    assert "display_name_ja" not in reloaded
    # 再実行は冪等 (既に新形式なので変換なし)
    assert migrate_i18n.migrate_file(f, dry_run=False) is False
