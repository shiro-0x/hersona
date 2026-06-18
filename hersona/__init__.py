"""hersona — 汎用属性テンプレート集のコアロジック。

ロードマップ (ROADMAP.md) の core 共有設計に基づき、attach / blend / check /
recommend / authoring のロジックを本パッケージに集約する。Hermes スキル・
CLI/TUI・将来の Web 殻はいずれも本パッケージの薄い殻となる。
"""
from __future__ import annotations

__all__ = ["__version__"]

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version

try:
    __version__ = _pkg_version("hersona")
except PackageNotFoundError:  # editable/未インストール時のフォールバック
    __version__ = "0.0.0+dev"
