#!/usr/bin/env python3
"""hersona 属性テンプレート YAML 検証スクリプト

使用方法:
    python scripts/validate.py
    python scripts/validate.py attributes/
    python scripts/validate.py attributes/personality/tsundere.yaml

検証対象:
- attributes/**/*.yaml  ← attribute.schema.json で検証 (T1 / v1.0)

T2 (2026-06-09) で data/ 配下のキャラプロファイル (character.schema.json) と
persona_attach_prompt (persona_attach.schema.json) の検証は廃止。fanwork
由来キャラクターの完全廃止に伴い、attributes/ テンプレート検証のみを行う。
"""
import sys
import json
from pathlib import Path

import yaml
import jsonschema


ATTRIBUTE_SCHEMA_PATH = Path(__file__).parent.parent / "schema" / "attribute.schema.json"


def load_attribute_schema() -> dict:
    with open(ATTRIBUTE_SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_attribute_file(yaml_path: Path, attribute_schema: dict) -> list[str]:
    """属性 YAML を検証し、エラーメッセージのリストを返す。"""
    errors: list[str] = []
    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        return [f"YAML構文エラー: {e}"]

    if data is None:
        return ["空ファイル"]

    try:
        jsonschema.validate(data, attribute_schema)
    except jsonschema.ValidationError as e:
        path = "/".join(str(p) for p in e.absolute_path) or "(root)"
        errors.append(f"スキーマ違反 @ {path}: {e.message}")

    # 整合性チェック: compatible_archetypes / conflicts_with の参照先
    known: set[str] = set()
    attrs_root = Path(__file__).parent.parent / "attributes"
    if attrs_root.exists():
        for yml in sorted(attrs_root.rglob("*.yaml")):
            try:
                with open(yml, "r", encoding="utf-8") as f:
                    d = yaml.safe_load(f)
                if isinstance(d, dict) and "attribute_name" in d:
                    known.add(d["attribute_name"])
            except yaml.YAMLError:
                continue

    for ref in data.get("compatible_archetypes", []) or []:
        if ref not in known:
            errors.append(
                f"compatible_archetypes 参照エラー: '{ref}' "
                f"(attributes/ 配下に存在しない attribute_name)"
            )
    for ref in data.get("conflicts_with", []) or []:
        if ref not in known:
            errors.append(
                f"conflicts_with 参照エラー: '{ref}' "
                f"(attributes/ 配下に存在しない attribute_name)"
            )

    return errors


def find_all_yaml(root: Path) -> list[Path]:
    return sorted(root.rglob("*.yaml"))


def main() -> int:
    attribute_schema = load_attribute_schema()
    repo_root = Path(__file__).parent.parent

    if len(sys.argv) > 1:
        targets = [Path(arg) for arg in sys.argv[1:]]
    else:
        targets = []
        attrs_root = repo_root / "attributes"
        if attrs_root.exists():
            targets.extend(find_all_yaml(attrs_root))
        if not targets:
            print("検証対象ファイルがありません (attributes/ が空です)")
            return 1

    if not targets:
        print("検証対象ファイルがありません")
        return 1

    total_errors = 0
    for path in targets:
        if not path.exists():
            print(f"❌ {path}: ファイルなし")
            total_errors += 1
            continue
        if path.is_dir():
            for sub in find_all_yaml(path):
                errors = validate_attribute_file(sub, attribute_schema)
                _report(sub, errors, total_errors_ref=[0])
                total_errors += len(errors)
        else:
            errors = validate_attribute_file(path, attribute_schema)
            _report(path, errors, total_errors_ref=[0])
            total_errors += len(errors)

    print(f"\n検証完了: {len(targets)}ファイル, エラー {total_errors}件")
    return 0 if total_errors == 0 else 1


def _report(path: Path, errors: list[str], total_errors_ref: list[int]) -> None:
    if errors:
        print(f"❌ {path}")
        for e in errors:
            print(f"   - {e}")
    else:
        print(f"✓ {path}")


if __name__ == "__main__":
    sys.exit(main())
