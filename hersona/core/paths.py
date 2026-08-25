"""パッケージデータの解決 (ダウンロードキャッシュ / リポジトリ直置き / wheel 同梱)。

`attributes/` と `schema/` はリポジトリではトップレベルに置かれるが、
wheel では `hersona/data/` 配下に同梱される (pyproject の force-include)。
editable インストール・リポジトリ直実行・wheel インストールのいずれでも
同じ API でパスを解決できるようにする。

さらに `hersona update` が GitHub から最新データを取得した場合は
データキャッシュ (`data_cache_root`) へ展開され、同梱データより優先して
解決される。これにより再インストールせずに属性データを更新できる。
"""
from __future__ import annotations

import os
from pathlib import Path

_PKG_ROOT = Path(__file__).resolve().parent.parent          # hersona/
_REPO_ROOT = _PKG_ROOT.parent                                # リポジトリ直置き時のみ有効
_PKG_DATA = _PKG_ROOT / "data"                               # wheel 同梱データ

#: ダウンロード済み公開データの保存先を上書きする環境変数。
_DATA_DIR_ENV = "HERSONA_DATA_DIR"


def data_cache_root() -> Path:
    """`hersona update` がダウンロードした公開データの保存ルート。

    環境変数 ``HERSONA_DATA_DIR`` があればそれを、無ければ ``~/.hermes/data``。
    (ユーザー作成属性 ``~/.hermes/attributes`` とは分離する。)
    """
    env = os.environ.get(_DATA_DIR_ENV)
    if env:
        return Path(env).expanduser()
    return Path.home() / ".hermes" / "data"


def _resolve(rel: str) -> Path:
    """ダウンロードキャッシュ → リポジトリ直下 → wheel 同梱 の順で解決する。"""
    cached = data_cache_root() / rel
    if cached.exists():
        return cached
    repo = _REPO_ROOT / rel
    if repo.exists():
        return repo
    return _PKG_DATA / rel


def public_attributes_root() -> Path:
    """公開属性 (`attributes/`) のルートディレクトリ。"""
    return _resolve("attributes")


def attribute_schema_path() -> Path:
    """`schema/attribute.schema.json` のパス。"""
    return _resolve("schema/attribute.schema.json")


def use_cases_root() -> Path:
    """Public Operating Mode / use-case prompt pack root (`use_cases/`)."""
    return _resolve("use_cases")


def use_case_schema_path() -> Path:
    """`schema/use_case.schema.json` path."""
    return _resolve("schema/use_case.schema.json")


def personas_root() -> Path:
    """Public persona-pack recipe root (`personas/`).

    Each ``<persona_name>.yaml`` is a *recipe*: it names a blend of real
    attributes and a weight. The actual injection block is rendered at
    install time, so attribute updates propagate automatically and
    ``build_site.py``-style drift gates are unnecessary for packs.
    """
    return _resolve("personas")


def persona_pack_schema_path() -> Path:
    """`schema/persona_pack.schema.json` path."""
    return _resolve("schema/persona_pack.schema.json")


def registry_path() -> Path:
    """Repository component registry path (`docs/REGISTRY.yaml`).

    The registry is a repository governance artifact rather than packaged
    runtime data, so missing it is reported by ``hersona.core.registry``
    instead of silently falling back to a generated or cached copy.
    """
    return _REPO_ROOT / "docs" / "REGISTRY.yaml"
