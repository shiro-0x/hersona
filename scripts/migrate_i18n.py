#!/usr/bin/env python3
"""属性 YAML を旧 suffix ペア形式から i18n ブロック形式へ移行する (設計書 §2.2 / Phase 2)。

変換内容 (1 ファイルあたり):
    display_name_en  -> display_name        (BASE=en)
    description_en   -> description          (BASE=en)
    display_name_ja  -> i18n.ja.display_name
    description_ja   -> i18n.ja.description

旧 4 キーは削除し、フィールド順は authoring.FIELD_ORDER に揃える。既に新形式
(``display_name`` を持つ) のファイルはスキップする。後方互換のためスキーマは
両形式を受理する (oneOf) ので、未移行ファイルが残っても検証は通る。

使い方::

    python scripts/migrate_i18n.py              # attributes/ 配下を変換 (上書き)
    python scripts/migrate_i18n.py --dry-run    # 変換対象を表示するだけ (書き込まない)
    python scripts/migrate_i18n.py path/to/dir  # 対象ルートを指定
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TARGET = ROOT / "attributes"

# authoring.FIELD_ORDER と同じ並び (移行後の安定したフィールド順)。
FIELD_ORDER = [
    "attribute_category",
    "attribute_name",
    "display_name",
    "weight_dimension",
    "content_lang",
    "typical_value_range",
    "description",
    "examples",
    "compatible_archetypes",
    "conflicts_with",
    "has_catchphrase",
    "variant",
    "tags",
    "core_traits",
    "speech_style",
    "second_person",
    "sentence_endings",
    "lexical_markers",
    "register",
    "catchphrases",
    "tone",
    "content_i18n",
    "notes",
    "i18n",
]

_LEGACY_KEYS = ("display_name_ja", "display_name_en", "description_ja", "description_en")


def _reorder(data: dict) -> dict:
    ordered = {k: data[k] for k in FIELD_ORDER if k in data}
    for k, v in data.items():  # 未知キーは末尾に保持
        if k not in ordered:
            ordered[k] = v
    return ordered


def migrate_data(data: dict) -> dict | None:
    """旧形式 dict を新形式へ変換する。既に新形式なら None を返す。"""
    if "display_name" in data:
        return None  # 既に移行済み
    if "display_name_en" not in data and "display_name_ja" not in data:
        return None  # メタデータが無い (対象外)

    out = dict(data)
    if data.get("display_name_en"):
        out["display_name"] = data["display_name_en"]
    if data.get("description_en"):
        out["description"] = data["description_en"]

    ja: dict[str, str] = {}
    if data.get("display_name_ja"):
        ja["display_name"] = data["display_name_ja"]
    if data.get("description_ja"):
        ja["description"] = data["description_ja"]
    if ja:
        i18n = dict(out.get("i18n") or {})
        i18n["ja"] = {**ja, **(i18n.get("ja") or {})}
        out["i18n"] = i18n

    for key in _LEGACY_KEYS:
        out.pop(key, None)
    return _reorder(out)


def _dump(data: dict) -> str:
    return yaml.safe_dump(
        data,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
        width=1000,
    )


def migrate_file(path: Path, *, dry_run: bool) -> bool:
    """1 ファイルを変換する。変換した (またはする予定) なら True。"""
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        return False
    migrated = migrate_data(data)
    if migrated is None:
        return False
    if not dry_run:
        with path.open("w", encoding="utf-8") as f:
            f.write(_dump(migrated))
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "targets",
        nargs="*",
        type=Path,
        default=[DEFAULT_TARGET],
        help="変換対象のディレクトリ / ファイル (既定: attributes/)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="変換対象を表示するだけで書き込まない",
    )
    args = parser.parse_args(argv)

    files: list[Path] = []
    for target in args.targets:
        if target.is_dir():
            files.extend(sorted(target.rglob("*.yaml")))
        elif target.is_file():
            files.append(target)

    converted = 0
    for path in files:
        if migrate_file(path, dry_run=args.dry_run):
            converted += 1
            verb = "would migrate" if args.dry_run else "migrated"
            print(f"  {verb}: {path.relative_to(ROOT)}")

    action = "対象" if args.dry_run else "変換"
    print(f"{action}: {converted} / {len(files)} ファイル")
    return 0


if __name__ == "__main__":
    sys.exit(main())
