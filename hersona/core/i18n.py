"""hersona 言語プラミング (i18n) — Phase 0。

設計書 `docs/I18N_DESIGN.md` §3 に基づく、言語選択とロケール解決の最小基盤。
本モジュールは「配管 (plumbing)」のみを提供し、CLI 文言の全面カタログ化や
メタデータの BASE=en 化 (Phase 1〜2) は後続フェーズで段階的に積む。

公開 API:
    DEFAULT_LANG / SUPPORTED_LANGS  既定言語と対応言語
    resolve_lang(cli_lang)          言語決定: フラグ > 環境変数 > 既定 en
    tr(key, lang, **fmt)            CLI 文言カタログ参照 (フォールバック付き)
    resolve_meta(attr, field, lang) 属性メタデータのロケール解決

言語決定の優先順位 (設計書 §3.1):
    --lang フラグ > HERSONA_LANG 環境変数 > 既定 'en'
"""
from __future__ import annotations

import os
from functools import cache
from pathlib import Path
from typing import Any

import yaml

#: 既定言語。プロジェクト方針として英語ベース (en) を既定にする。
DEFAULT_LANG = "en"

#: 現状サポートする言語コード。新言語追加時はここと locales/<lang>.yaml を増やす。
SUPPORTED_LANGS: tuple[str, ...] = ("en", "ja")

#: 文言カタログの所在 (hersona/locales/<lang>.yaml)。
_LOCALES_DIR = Path(__file__).resolve().parent.parent / "locales"

#: 環境変数名。
_ENV_VAR = "HERSONA_LANG"


def normalize_lang(lang: str | None) -> str | None:
    """言語コードを正規化する。'en-US' → 'en' のように地域サブタグを落とす。

    未対応・空・None は None を返す (呼び出し側でフォールバックさせる)。
    """
    if not lang:
        return None
    base = lang.strip().lower().replace("_", "-").split("-", 1)[0]
    return base if base in SUPPORTED_LANGS else None


def resolve_lang(cli_lang: str | None = None) -> str:
    """有効な言語コードを決定する。

    優先順位: ``cli_lang`` (--lang) > ``HERSONA_LANG`` 環境変数 > ``DEFAULT_LANG``。
    いずれも未対応値なら次へフォールバックし、最終的に必ず対応言語を返す。
    """
    return (
        normalize_lang(cli_lang)
        or normalize_lang(os.environ.get(_ENV_VAR))
        or DEFAULT_LANG
    )


#: プロセス全体の「現在の表示言語」。CLI 起動時に ``set_active_lang`` で確定する。
#: core 層のエラーメッセージ等は引数で lang を受け取らずこの値を参照する。
_active_lang: str = resolve_lang()


def set_active_lang(cli_lang: str | None = None) -> str:
    """プロセスの現在表示言語を確定し、その値を返す。

    CLI の ``main`` が起動時に一度呼ぶ。以後 ``tr(key)`` / ``resolve_meta(...)`` を
    lang 引数なしで呼ぶと本値が使われる。
    """
    global _active_lang
    _active_lang = resolve_lang(cli_lang)
    return _active_lang


def active_lang() -> str:
    """現在の表示言語を返す。"""
    return _active_lang


def _effective(lang: str | None) -> str:
    """明示 lang があればそれを解決、無ければ現在の表示言語を使う。"""
    return resolve_lang(lang) if lang is not None else _active_lang


@cache
def _load_catalog(lang: str) -> dict[str, str]:
    """`locales/<lang>.yaml` を読み、ドット区切りキーの平坦な辞書にする。

    カタログが無い / 壊れている場合は空辞書 (呼び出し側でフォールバック)。
    """
    path = _LOCALES_DIR / f"{lang}.yaml"
    if not path.is_file():
        return {}
    try:
        with path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except (OSError, yaml.YAMLError):
        return {}
    return _flatten(data)


def _flatten(data: Any, prefix: str = "") -> dict[str, str]:
    """ネストした dict をドット区切りキーへ平坦化する。"""
    flat: dict[str, str] = {}
    if isinstance(data, dict):
        for key, value in data.items():
            child = f"{prefix}.{key}" if prefix else str(key)
            flat.update(_flatten(value, child))
    else:
        flat[prefix] = data
    return flat


def tr(key: str, lang: str | None = None, /, **fmt: Any) -> str:
    """文言カタログからローカライズ済み文字列を返す。

    ``lang`` 省略時は現在の表示言語 (``set_active_lang`` で設定) を使う。
    フォールバック順: ``<lang>`` カタログ > ``DEFAULT_LANG`` カタログ > ``key`` そのもの。
    ``**fmt`` を渡すと ``str.format`` で差し込む (差し込み失敗時はテンプレートをそのまま返す)。
    """
    resolved = _effective(lang)
    template = _load_catalog(resolved).get(key)
    if template is None and resolved != DEFAULT_LANG:
        template = _load_catalog(DEFAULT_LANG).get(key)
    if template is None:
        template = key
    if not fmt:
        return template
    try:
        return template.format(**fmt)
    except (KeyError, IndexError, ValueError):
        return template


def resolve_meta(attr: dict[str, Any], field: str, lang: str | None = None) -> str:
    """属性メタデータ (display_name / description 等) をロケール解決する。

    設計書 §2.2 / §3.2 のフォールバック順で最初に見つかった非空値を返す:
        1. ``i18n.<lang>.<field>``        (新形式・拡張ロケール)
        2. ``<field>_<lang>``             (旧形式 suffix ペア: 例 display_name_ja)
        3. ``<field>``                    (新形式 BASE=en、または言語中立)
        4. ``<field>_en`` → ``<field>_ja`` (旧形式の最終フォールバック)

    後方互換のため新旧両形式を受理する。該当が無ければ空文字。
    ``lang`` 省略時は現在の表示言語 (``set_active_lang`` で設定) を使う。
    """
    resolved = _effective(lang)

    i18n = attr.get("i18n")
    if isinstance(i18n, dict):
        block = i18n.get(resolved)
        if isinstance(block, dict) and block.get(field):
            return str(block[field])

    legacy = attr.get(f"{field}_{resolved}")
    if legacy:
        return str(legacy)

    base = attr.get(field)
    if base:
        return str(base)

    for fallback in (f"{field}_{DEFAULT_LANG}", f"{field}_ja"):
        value = attr.get(fallback)
        if value:
            return str(value)

    return ""
