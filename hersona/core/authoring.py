"""ローカル属性オーサリング (ROADMAP ③ ローカルオーサリング基盤)。

ユーザーがローカルで自分の属性テンプレートを作成・上書きし、検証ゲートを通して
ユーザー名前空間に保存するための core ロジック。Hermes スキルの `/hersona create`
や CLI/TUI はいずれも本モジュールの薄い殻となる。

設計方針 (ROADMAP / DISCLAIMER との整合):
- **ローカル＝自由**: ローカル保存時は固有名詞ガードを発動しない (私的利用は自由)。
- **公開・共有＝汎用のみ**: 共有・エクスポート時のみ `assert_shareable()` で
  固有名詞リスクを検査する。
- **保存先の分離**: ユーザー作成データは `~/.hermes/attributes/` (既定) または
  環境変数 `HERSONA_USER_DIR` で指定したディレクトリに置き、公開 `attributes/`
  には混ざらない。リポジトリ内 `attributes/user/` も `.gitignore` 済み。
- **検証ゲート**: `save_attribute()` は `schema/attribute.schema.json` 違反があれば
  保存を拒否する。
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import jsonschema
import yaml

from hersona.core.i18n import tr
from hersona.core.paths import attribute_schema_path, public_attributes_root

SCHEMA_PATH = attribute_schema_path()
PUBLIC_ATTRIBUTES_ROOT = public_attributes_root()

# YAML 出力時のフィールド順 (人間可読性のため安定化)
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
    # 旧 suffix ペア形式 (移行期の後方互換)。新規生成では使わない。
    "display_name_ja",
    "display_name_en",
    "description_ja",
    "description_en",
]

# 共有時に弾く固有名詞リスク (best-effort のブロックリスト)。
# 既定は空。プロジェクト方針に応じて拡張可能。
DEFAULT_PROPER_NOUN_BLOCKLIST: frozenset[str] = frozenset()


class AuthoringError(Exception):
    """オーサリング処理の汎用エラー。"""


class ValidationGateError(AuthoringError):
    """検証ゲートでスキーマ違反を検出した。"""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("属性のスキーマ検証に失敗しました:\n  - " + "\n  - ".join(errors))


class ShareGuardError(AuthoringError):
    """共有ガードで固有名詞リスクを検出した。"""

    def __init__(self, hits: list[str]) -> None:
        self.hits = hits
        super().__init__(
            "固有名詞リスクを検出しました (共有には汎用属性のみ可):\n  - "
            + "\n  - ".join(hits)
        )


def load_schema() -> dict:
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        return json.load(f)


def validate_attribute(
    data: dict,
    *,
    expect_name: str | None = None,
    expect_category: str | None = None,
) -> list[str]:
    """属性 dict を検証し、エラーメッセージのリストを返す (空なら合格)。"""
    errors: list[str] = []
    try:
        jsonschema.validate(data, load_schema())
    except jsonschema.ValidationError as e:
        path = "/".join(str(p) for p in e.absolute_path) or "(root)"
        errors.append(f"スキーマ違反 @ {path}: {e.message}")

    if expect_name is not None and data.get("attribute_name") != expect_name:
        errors.append(
            f"attribute_name '{data.get('attribute_name')}' が期待値 '{expect_name}' と不一致"
        )
    if expect_category is not None and data.get("attribute_category") != expect_category:
        errors.append(
            f"attribute_category '{data.get('attribute_category')}' が "
            f"期待値 '{expect_category}' と不一致"
        )
    return errors


def build_attribute(
    *,
    attribute_category: str,
    attribute_name: str,
    display_name_ja: str,
    display_name_en: str,
    weight_dimension: str,
    description_ja: str,
    description_en: str,
    examples: list[str],
    **optional: Any,
) -> dict:
    """必須フィールド + 任意フィールドから属性 dict を組み立てる。

    メタデータは BASE=en (``display_name`` / ``description``) を基準とし、日本語は
    ``i18n.ja`` ブロックに格納する (設計書 §2.2)。引数は二言語ペアのまま受け取り、
    内部で新形式へ写像する (CLI のオーサリングは二言語入力を維持)。
    任意フィールドのうち None / 空文字 / 空リストは出力から除外する。
    フィールド順は FIELD_ORDER に従って安定化する。
    """
    data: dict[str, Any] = {
        "attribute_category": attribute_category,
        "attribute_name": attribute_name,
        "display_name": display_name_en,
        "weight_dimension": weight_dimension,
        "description": description_en,
        "examples": examples,
    }
    for key, value in optional.items():
        if value is None or value == "" or value == [] or value == {}:
            continue
        data[key] = value
    ja: dict[str, str] = {}
    if display_name_ja:
        ja["display_name"] = display_name_ja
    if description_ja:
        ja["description"] = description_ja
    if ja:
        data["i18n"] = {"ja": ja}
    return _ordered(data)


def load_base_attribute(name: str, *, attributes_root: Path | None = None) -> dict:
    """公開 attributes/ から既存属性を読み込む (上書きの土台)。"""
    root = attributes_root or PUBLIC_ATTRIBUTES_ROOT
    for yml in sorted(root.rglob("*.yaml")):
        with open(yml, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if isinstance(data, dict) and data.get("attribute_name") == name:
            return data
    raise AuthoringError(tr("core.authoring_not_found", name=name, root=root))


def override_attribute(
    base_name: str,
    *,
    new_name: str,
    overrides: dict[str, Any],
    attributes_root: Path | None = None,
) -> dict:
    """既存属性を土台に、指定フィールドを上書きした新属性 dict を作る。

    例: tsundere を土台に catchphrases だけ差し替えて my_tsundere を作る。
    attribute_category は土台を引き継ぐ (overrides で上書きも可)。
    """
    if new_name == base_name:
        raise AuthoringError(
            f"new_name は base_name と異なる必要があります (どちらも '{base_name}')"
        )
    base = load_base_attribute(base_name, attributes_root=attributes_root)
    merged: dict[str, Any] = dict(base)
    merged["attribute_name"] = new_name
    for key, value in overrides.items():
        merged[key] = value
    # 派生であることを変種ラベルで明示 (overrides 未指定かつ空/未設定の場合のみ)
    if "variant" not in overrides and not merged.get("variant"):
        merged["variant"] = "custom"
    return _ordered(merged)


def user_attributes_root() -> Path:
    """ユーザー作成属性の保存ルート。

    環境変数 HERSONA_USER_DIR があればそれを、なければ ~/.hermes/attributes。
    """
    env = os.environ.get("HERSONA_USER_DIR")
    if env:
        return Path(env).expanduser()
    return Path.home() / ".hermes" / "attributes"


def save_attribute(
    data: dict,
    *,
    user_root: Path | None = None,
    overwrite: bool = False,
) -> Path:
    """検証ゲートを通してユーザー名前空間に属性 YAML を保存する。

    保存先: <user_root>/<attribute_category>/<attribute_name>.yaml
    スキーマ違反があれば ValidationGateError を送出し、保存しない。
    固有名詞ガードはローカル保存では発動しない (ローカル＝自由)。
    """
    category = data.get("attribute_category")
    name = data.get("attribute_name")
    errors = validate_attribute(data, expect_name=name, expect_category=category)
    if errors:
        raise ValidationGateError(errors)

    root = user_root or user_attributes_root()
    dest_dir = root / str(category)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{name}.yaml"
    if dest.exists() and not overwrite:
        raise AuthoringError(
            f"既に存在します: {dest} (上書きするには overwrite=True)"
        )

    with open(dest, "w", encoding="utf-8") as f:
        yaml.safe_dump(
            _ordered(data),
            f,
            allow_unicode=True,
            sort_keys=False,
            default_flow_style=False,
        )
    return dest


def list_user_attributes(user_root: Path | None = None) -> list[Path]:
    """ユーザー名前空間に保存済みの属性 YAML を列挙する。"""
    root = user_root or user_attributes_root()
    if not root.exists():
        return []
    return sorted(root.rglob("*.yaml"))


# --- 共有ガード (共有・エクスポート時のみ発動) ---------------------------


def find_proper_noun_risks(
    data: dict,
    *,
    blocklist: frozenset[str] | None = None,
) -> list[str]:
    """属性のテキストフィールドから固有名詞リスク候補を検出する (best-effort)。

    共有時のみ呼ぶこと。ローカル保存では呼ばない (ローカル＝自由)。
    """
    block = blocklist if blocklist is not None else DEFAULT_PROPER_NOUN_BLOCKLIST
    hits: list[str] = []
    for token in block:
        needle = token.lower()
        for field, text in _iter_text_fields(data):
            if needle in text.lower():
                hits.append(f"'{token}' を {field} に検出")
                break
    return sorted(set(hits))


def assert_shareable(
    data: dict,
    *,
    blocklist: frozenset[str] | None = None,
) -> None:
    """共有可能か検査する。固有名詞リスクがあれば ShareGuardError を送出。"""
    hits = find_proper_noun_risks(data, blocklist=blocklist)
    if hits:
        raise ShareGuardError(hits)


# --- 内部 ---------------------------------------------------------------


def _ordered(data: dict) -> dict:
    """FIELD_ORDER に従ってフィールドを並べ替えた dict を返す。"""
    ordered = {k: data[k] for k in FIELD_ORDER if k in data}
    # FIELD_ORDER に無いキーは末尾に保持
    for k, v in data.items():
        if k not in ordered:
            ordered[k] = v
    return ordered


def _iter_text_fields(data: dict):
    """検査対象のテキスト (フィールド名, 文字列) を順に yield する。"""
    for key, value in data.items():
        if isinstance(value, str):
            yield key, value
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, str):
                    yield key, item
