"""パッケージデータの解決 (リポジトリ直置き / wheel 同梱の両対応)。

`attributes/` と `schema/` はリポジトリではトップレベルに置かれるが、
wheel では `hersona/data/` 配下に同梱される (pyproject の force-include)。
editable インストール・リポジトリ直実行・wheel インストールのいずれでも
同じ API でパスを解決できるようにする。
"""
from __future__ import annotations

from pathlib import Path

_PKG_ROOT = Path(__file__).resolve().parent.parent          # hersona/
_REPO_ROOT = _PKG_ROOT.parent                                # リポジトリ直置き時のみ有効
_PKG_DATA = _PKG_ROOT / "data"                               # wheel 同梱データ


def _resolve(rel: str) -> Path:
    """リポジトリ直下 → wheel 同梱 (hersona/data/) の順で解決する。"""
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
