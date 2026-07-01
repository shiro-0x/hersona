"""テスト共通フィクスチャ。

i18n の「現在の表示言語」はプロセス全体で共有されるグローバル状態のため、
テスト間でリークしないよう各テスト前に既定 (en) へリセットする。CLI 経路は
``main()`` が起動時に ``set_active_lang`` で再確定するので影響しない。
"""
from __future__ import annotations

import os
from pathlib import Path

# Core modules resolve public data roots at import time. Keep tests independent
# from a developer's downloaded ~/.hermes/data cache.
os.environ.setdefault("HERSONA_DATA_DIR", str(Path(__file__).resolve().parent / ".empty-data"))

import pytest

from hersona.core import i18n


@pytest.fixture(autouse=True)
def _reset_active_lang():
    i18n.set_active_lang("en")
    yield
    i18n.set_active_lang("en")
