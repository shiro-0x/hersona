#!/usr/bin/env python3
"""hersona キャラプロファイルYAML検証スクリプト

使用方法:
    python scripts/validate.py
    python scripts/validate.py data/elden-ring/melina.yaml
"""
import sys
import json
from pathlib import Path
import yaml
import jsonschema


SCHEMA_PATH = Path(__file__).parent.parent / "schema" / "character.schema.json"


def load_schema() -> dict:
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_file(yaml_path: Path, schema: dict) -> list[str]:
    """YAMLファイルを検証し、エラーメッセージのリストを返す"""
    errors = []
    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        return [f"YAML構文エラー: {e}"]

    if data is None:
        return [f"空ファイル"]

    try:
        jsonschema.validate(data, schema)
    except jsonschema.ValidationError as e:
        path = "/".join(str(p) for p in e.absolute_path) or "(root)"
        errors.append(f"スキーマ違反 @ {path}: {e.message}")

    # 追加の推奨チェック
    if "license_source" not in data or not data["license_source"]:
        errors.append("推奨: license_source（セリフ引用元）を最低1件記載してください")

    if "personality" in data:
        p = data["personality"]
        if "catchphrases" not in p or len(p.get("catchphrases", [])) < 3:
            errors.append("推奨: catchphrases（口癖）は3件以上記載してください")
        if "core_traits" in p and len(p["core_traits"]) < 3:
            errors.append("推奨: core_traits（性格特性）は3件以上記載してください")

    return errors


def find_all_yaml(root: Path) -> list[Path]:
    return sorted(root.rglob("*.yaml"))


def main() -> int:
    schema = load_schema()
    repo_root = Path(__file__).parent.parent

    if len(sys.argv) > 1:
        targets = [Path(arg) for arg in sys.argv[1:]]
    else:
        targets = find_all_yaml(repo_root / "data")

    if not targets:
        print("検証対象ファイルがありません")
        return 1

    total_errors = 0
    for path in targets:
        if not path.exists():
            print(f"❌ {path}: ファイルなし")
            total_errors += 1
            continue

        errors = validate_file(path, schema)
        if errors:
            print(f"❌ {path}")
            for e in errors:
                print(f"   - {e}")
            total_errors += len(errors)
        else:
            print(f"✓ {path}")

    print(f"\n検証完了: {len(targets)}ファイル, エラー {total_errors}件")
    return 0 if total_errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
