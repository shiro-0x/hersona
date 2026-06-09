#!/usr/bin/env python3
"""hersona キャラプロファイル / 属性テンプレート YAML 検証スクリプト

使用方法:
    python scripts/validate.py
    python scripts/validate.py data/elden-ring/melina.yaml
    python scripts/validate.py attributes/

検証対象:
- data/**/*.yaml        ← character.schema.json で検証
- attributes/**/*.yaml  ← attribute.schema.json で検証 (T1 / v1.0)
"""
import sys
import json
from pathlib import Path
import yaml
import jsonschema

# 直叩き / `python -m` 双方で動くよう親ディレクトリ (scripts/) を sys.path に追加
sys.path.insert(0, str(Path(__file__).resolve().parent))
from pap_utils import pap_get, pap_get_list  # noqa: E402


SCHEMA_PATH = Path(__file__).parent.parent / "schema" / "character.schema.json"
PERSONA_ATTACH_SCHEMA_PATH = Path(__file__).parent.parent / "schema" / "persona_attach.schema.json"
ATTRIBUTE_SCHEMA_PATH = Path(__file__).parent.parent / "schema" / "attribute.schema.json"


def load_schema() -> dict:
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_persona_attach_schema() -> dict | None:
    if not PERSONA_ATTACH_SCHEMA_PATH.exists():
        return None
    with open(PERSONA_ATTACH_SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_attribute_schema() -> dict | None:
    """T1 / v1.0 で追加。存在しない場合 (v0.x) は None。"""
    if not ATTRIBUTE_SCHEMA_PATH.exists():
        return None
    with open(ATTRIBUTE_SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_file(yaml_path: Path, schema: dict, attribute_schema: dict | None = None) -> list[str]:
    """YAMLファイルを検証し、エラーメッセージのリストを返す

    yaml_path が attributes/ 配下の場合は attribute_schema を使う (T1 / v1.0)。
    """
    errors = []
    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        return [f"YAML構文エラー: {e}"]

    if data is None:
        return [f"空ファイル"]

    # パスに応じて schema を選択 (attributes/ は attribute_schema を使用)
    if attribute_schema is not None and "attributes" in yaml_path.parts:
        used_schema = attribute_schema
        is_attribute = True
    else:
        used_schema = schema
        is_attribute = False

    try:
        jsonschema.validate(data, used_schema)
    except jsonschema.ValidationError as e:
        path = "/".join(str(p) for p in e.absolute_path) or "(root)"
        errors.append(f"スキーマ違反 @ {path}: {e.message}")

    # 追加の推奨チェック
    if is_attribute:
        # T1: attribute 固有の整合性チェック
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
    else:
        if "license_source" not in data or not data["license_source"]:
            errors.append("推奨: license_source（セリフ引用元）を最低1件記載してください")

        if "personality" in data:
            p = data["personality"]
            if "catchphrases" not in p or len(p.get("catchphrases", [])) < 3:
                errors.append("推奨: catchphrases（口癖）は3件以上記載してください")
            if "core_traits" in p and len(p["core_traits"]) < 3:
                errors.append("推奨: core_traits（性格特性）は3件以上記載してください")
            if "first_person" not in p or not p.get("first_person"):
                errors.append("推奨: first_person（一人称）を記載してください（セリフ根拠必須）")
            if "second_person" not in p or not p.get("second_person"):
                errors.append("推奨: second_person（二人称）を記載してください（セリフ根拠必須）")
            if "sentence_endings" not in p or len(p.get("sentence_endings", [])) < 3:
                errors.append("推奨: sentence_endings（語尾）は3件以上記載してください")

        # persona_attach_prompt 検証
        if "persona_attach_prompt" in data and data["persona_attach_prompt"]:
            pa_schema = load_persona_attach_schema()
            if pa_schema is None:
                errors.append("persona_attach_prompt がありますが schema/persona_attach.schema.json が見つかりません")
            else:
                try:
                    jsonschema.validate(data["persona_attach_prompt"], pa_schema)
                except jsonschema.ValidationError as e:
                    path = "/".join(str(p) for p in e.absolute_path) or "(root)"
                    errors.append(f"persona_attach_prompt スキーマ違反 @ {path}: {e.message}")
                # 追加チェック: required_words が attach_prompt 内に存在するか
                ap = data["persona_attach_prompt"]
                attach_text = pap_get(ap, "attach_prompt", default="")
                for w in pap_get_list(ap, "required_words"):
                    if w and w not in attach_text:
                        errors.append(
                            f"persona_attach_prompt: required_word「{w}」が attach_prompt 内に1回も出現しません"
                        )

    return errors


def find_all_yaml(root: Path) -> list[Path]:
    return sorted(root.rglob("*.yaml"))


def main() -> int:
    schema = load_schema()
    attribute_schema = load_attribute_schema()
    repo_root = Path(__file__).parent.parent

    if len(sys.argv) > 1:
        targets = [Path(arg) for arg in sys.argv[1:]]
    else:
        targets = []
        data_root = repo_root / "data"
        if data_root.exists():
            targets.extend(find_all_yaml(data_root))
        attrs_root = repo_root / "attributes"
        if attrs_root.exists() and attribute_schema is not None:
            targets.extend(find_all_yaml(attrs_root))
        if not targets:
            print("検証対象ファイルがありません (data/ も attributes/ も空です)")
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

        errors = validate_file(path, schema, attribute_schema=attribute_schema)
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
