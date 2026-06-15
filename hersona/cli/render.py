"""CLI の見た目を担うレンダリング層 (rich は任意依存)。

`rich` が入っていない / 出力が端末でない / ``--plain`` / ``NO_COLOR`` のいずれかなら
**必ずプレーン出力にフォールバック**する。これにより:

- `pip install hersona` (rich 無し) でも全コマンドが動く
- パイプ・リダイレクト時は機械可読なプレーン出力になる (テストの capsys も同様)
- ``hersona[tui]`` を入れて端末で実行したときだけ色付きテーブル/パネルになる

テストやページャ (`| less -R`) 向けに ``HERSONA_FORCE_RICH=1`` で TTY 判定を上書きできる。
"""
from __future__ import annotations

import os
import sys

# CATEGORY_ORDER と対応する rich スタイル (端末配色)。
CATEGORY_STYLE: dict[str, str] = {
    "personality": "magenta",
    "speech": "cyan",
    "archetype": "yellow",
    "visual": "green",
    "hobby": "blue",
}

_plain_override = False


def set_plain(value: bool) -> None:
    """``--plain`` 指定を記録する (True なら以降は常にプレーン)。"""
    global _plain_override
    _plain_override = value


def rich_enabled() -> bool:
    """rich レンダリングを使うべきか判定する。"""
    if _plain_override:
        return False
    if os.environ.get("NO_COLOR"):
        return False
    if not (os.environ.get("HERSONA_FORCE_RICH") or sys.stdout.isatty()):
        return False
    try:
        import rich  # noqa: F401
    except ImportError:
        return False
    return True


def console():
    """stdout 用の rich Console を返す (rich_enabled() 確認後に呼ぶこと)。"""
    from rich.console import Console

    return Console()


def err_console():
    """stderr 用の rich Console を返す。"""
    from rich.console import Console

    return Console(stderr=True)


def warn(message: str) -> None:
    """警告を stderr に出す。rich 有効なら赤、無効ならプレーン。"""
    if rich_enabled():
        err_console().print(message, style="bold red")
    else:
        print(message, file=sys.stderr)
