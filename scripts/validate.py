#!/usr/bin/env python3
"""hersona 属性テンプレート YAML 検証スクリプト

使用方法:
    python scripts/validate.py
    python scripts/validate.py attributes/
    python scripts/validate.py attributes/personality/tsundere.yaml

検証対象:
- attributes/**/*.yaml  ← attribute.schema.json で検証 (T1 / v1.0)

attributes/ テンプレートのスキーマ検証のみを行います。
"""
import json
import sys
from pathlib import Path

import jsonschema
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from hersona.core.compatibility import load_matrix  # noqa: E402

ATTRIBUTE_SCHEMA_PATH = Path(__file__).parent.parent / "schema" / "attribute.schema.json"


def load_attribute_schema() -> dict:
    with open(ATTRIBUTE_SCHEMA_PATH, encoding="utf-8") as f:
        return json.load(f)


def validate_attribute_file(yaml_path: Path, attribute_schema: dict) -> list[str]:
    """属性 YAML を検証し、エラーメッセージのリストを返す。"""
    errors: list[str] = []
    try:
        with open(yaml_path, encoding="utf-8") as f:
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
                with open(yml, encoding="utf-8") as f:
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

    full_run = len(sys.argv) <= 1
    if len(sys.argv) > 1:
        targets = [Path(arg) for arg in sys.argv[1:]]
        full_run = any(Path(arg).is_dir() for arg in sys.argv[1:])
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

    # 相性マトリクスの双方向整合チェック (ROADMAP ①)。
    # conflict は対称関係なので非対称宣言は警告 (core 側で対称閉包するため exit は失敗させない)。
    # compatible は提案ベースで片側宣言が設計上許容されるため件数のみ報告。
    if full_run:
        _report_relationship_consistency()

    return 0 if total_errors == 0 else 1


def _report_relationship_consistency() -> None:
    """全属性の相性関係の双方向整合を報告する (警告のみ、exit には影響しない)。"""
    attrs_root = REPO_ROOT / "attributes"
    if not attrs_root.exists():
        return
    matrix = load_matrix(attrs_root)
    asym = matrix.asymmetries()

    conflicts = asym["conflicts"]
    compatible = asym["compatible"]
    if not conflicts and not compatible:
        print("相性整合: 双方向の非対称なし ✓")
        return

    if conflicts:
        print(f"\n⚠ conflict 非対称 {len(conflicts)}件 (core で対称化済み / 片側宣言):")
        for a, b in conflicts:
            print(f"   - {a} → {b}")
    if compatible:
        print(f"⚠ compatible 非対称 {len(compatible)}件 (提案ベース、設計上許容)")


def _report(path: Path, errors: list[str], total_errors_ref: list[int]) -> None:
    if errors:
        print(f"❌ {path}")
        for e in errors:
            print(f"   - {e}")
    else:
        print(f"✓ {path}")


if __name__ == "__main__":
    sys.exit(main())
