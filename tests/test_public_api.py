"""公開 API (docs/PUBLIC_API.md) と hersona.core.__all__ の整合テスト (P0-2)。

- __all__ の全シンボルが実際に import 可能であること
- __all__ の全シンボルが docs/PUBLIC_API.md に記載されていること
  (文書の更新漏れ / シンボルの削除漏れを双方向に検出する)
"""
from __future__ import annotations

from pathlib import Path

import pytest

import hersona.core as core

REPO_ROOT = Path(__file__).resolve().parent.parent
PUBLIC_API_DOC = REPO_ROOT / "docs" / "PUBLIC_API.md"


def test_public_api_doc_exists() -> None:
    assert PUBLIC_API_DOC.exists(), f"{PUBLIC_API_DOC} がありません"


@pytest.mark.parametrize("symbol", sorted(core.__all__))
def test_all_symbols_importable(symbol: str) -> None:
    assert hasattr(core, symbol), f"hersona.core.{symbol} が __all__ にあるが import できない"


@pytest.mark.parametrize("symbol", sorted(core.__all__))
def test_all_symbols_documented(symbol: str) -> None:
    doc = PUBLIC_API_DOC.read_text(encoding="utf-8")
    assert symbol in doc, (
        f"公開シンボル {symbol} が docs/PUBLIC_API.md に記載されていません "
        "(公開 API を変更したら文書も更新すること)"
    )


def test_no_underscore_in_public_api() -> None:
    leaked = [s for s in core.__all__ if s.startswith("_")]
    assert not leaked, f"内部シンボルが公開されています: {leaked}"
