#!/usr/bin/env python3
"""デモサイト用データビルダー。

`attributes/**/*.yaml` と診断クイズ (hersona.core.recommend.DEFAULT_QUIZ)、
強度ガイダンス (hersona.core.weight) を読み取り、GitHub Pages 用の静的サイトが
そのまま読める JSON (`site/data.json`) に書き出す。

GitHub Pages は Python を実行しないため、このスクリプトはローカルで実行し、
生成された `site/data.json` をコミットする (CI でも再生成して差分検証できる)。

使い方::

    python scripts/build_site.py            # site/data.json を生成
    python scripts/build_site.py --check    # 既存と差分がないか検証 (CI 用)
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import types
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
ATTRIBUTES_ROOT = ROOT / "attributes"
CORE = ROOT / "hersona" / "core"
OUT = ROOT / "site" / "data.json"


def _load_core_module(name: str) -> types.ModuleType:
    """`hersona.core.<name>` をパッケージ __init__ を実行せず直接ロードする。

    `hersona/core/__init__.py` は authoring 経由で jsonschema を import するが、
    本ビルドに必要な recommend / weight / compatibility は yaml だけで動く。
    重い __init__ を回避するため namespace パッケージとして登録して読み込む。
    """
    for pkg, path in (("hersona", ROOT / "hersona"), ("hersona.core", CORE)):
        if pkg not in sys.modules:
            mod = types.ModuleType(pkg)
            mod.__path__ = [str(path)]  # namespace package
            sys.modules[pkg] = mod
    full = f"hersona.core.{name}"
    spec = importlib.util.spec_from_file_location(full, CORE / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[full] = module
    spec.loader.exec_module(module)
    return module


_recommend = _load_core_module("recommend")
_weight = _load_core_module("weight")
DEFAULT_QUIZ = _recommend.DEFAULT_QUIZ
WEIGHT_GUIDANCE = _weight.WEIGHT_GUIDANCE
_CATCHPHRASE_RATIO = _weight._CATCHPHRASE_RATIO

# data.json に載せる属性フィールド (schema 由来 + Round 3 雛形)。
_FIELDS = [
    "attribute_category",
    "attribute_name",
    "display_name_ja",
    "display_name_en",
    "weight_dimension",
    "content_lang",
    "typical_value_range",
    "description_ja",
    "description_en",
    "core_traits",
    "speech_style",
    "second_person",
    "sentence_endings",
    "lexical_markers",
    "register",
    "catchphrases",
    "tone",
    "compatible_archetypes",
    "conflicts_with",
    "tags",
    "has_catchphrase",
    "variant",
    "notes",
    "examples",
]


# i18n ブロック形式 (BASE=en + i18n.ja) と旧 suffix ペア形式の両方から、
# サイトが期待するロケール別キーを解決するためのマップ。
_DERIVED_META = {
    "display_name_ja": ("display_name", "ja"),
    "display_name_en": ("display_name", "en"),
    "description_ja": ("description", "ja"),
    "description_en": ("description", "en"),
}


def _resolve_meta(data: dict, field: str, lang: str) -> str:
    """属性メタを新旧両形式からロケール解決する (core/i18n.resolve_meta と同等)。"""
    block = (data.get("i18n") or {}).get(lang) or {}
    if block.get(field):
        return block[field]
    if data.get(f"{field}_{lang}"):
        return data[f"{field}_{lang}"]
    if data.get(field):
        return data[field]
    return data.get(f"{field}_en") or data.get(f"{field}_ja") or ""


def load_attributes() -> list[dict]:
    """全属性 YAML を読み取り、_FIELDS に絞った dict のリストを返す。

    サイト (site/app.js) は ``display_name_ja/en`` / ``description_ja/en`` を読むため、
    i18n ブロック形式の YAML からはこれらをロケール解決して埋める (JSON 形状は不変)。
    """
    out: list[dict] = []
    for yml in sorted(ATTRIBUTES_ROOT.rglob("*.yaml")):
        with open(yml, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not isinstance(data, dict) or "attribute_name" not in data:
            continue
        entry: dict = {}
        for k in _FIELDS:
            if k in _DERIVED_META:
                field, lang = _DERIVED_META[k]
                value = _resolve_meta(data, field, lang)
                if value:
                    entry[k] = value
            elif k in data:
                entry[k] = data[k]
        out.append(entry)
    return out


def quiz_payload() -> list[dict]:
    """DEFAULT_QUIZ をフロント用の素直な JSON に変換する。

    サイトは現状クイズを日本語で表示するため、prompt/label は ja を解決して出力する
    (JSON 形状は不変)。サイト側の en/ja 切替対応は将来作業。
    """
    return [
        {
            "id": q.id,
            "prompt": q.localized_prompt("ja"),
            "options": [
                {"label": o.localized_label("ja"), "weights": o.weights}
                for o in q.options
            ],
        }
        for q in DEFAULT_QUIZ
    ]


def build() -> dict:
    return {
        "attributes": load_attributes(),
        "quiz": quiz_payload(),
        "weight_guidance": {str(k): v for k, v in WEIGHT_GUIDANCE.items()},
        "catchphrase_ratio": {str(k): v for k, v in _CATCHPHRASE_RATIO.items()},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="生成結果が既存 site/data.json と一致するか検証 (書き込まない)",
    )
    args = parser.parse_args()

    payload = build()
    rendered = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"

    if args.check:
        if not OUT.exists():
            print(f"NG: {OUT} が存在しません。`python scripts/build_site.py` を実行してください。")
            return 1
        current = OUT.read_text(encoding="utf-8")
        if current != rendered:
            print(f"NG: {OUT} が最新ではありません。`python scripts/build_site.py` で再生成してください。")
            return 1
        print(f"OK: {OUT} は最新です ({len(payload['attributes'])} 属性)。")
        return 0

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(rendered, encoding="utf-8")
    print(f"書き出しました: {OUT} ({len(payload['attributes'])} 属性)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
