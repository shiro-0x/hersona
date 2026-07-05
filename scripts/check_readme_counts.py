#!/usr/bin/env python3
"""README.md / README.ja.md の属性数表記が最新かを検証する (CI 用)。

外部レビューで指摘された「README は 208 属性、実体は 345、GitHub About は 89」
という3つの数字の併存を再発させないためのゲート。`tests/catalog_counts.py`
(= `PUBLIC_CATEGORY_COUNTS` / `TOTAL_PUBLIC_ATTRIBUTES`) を単一ソースとし、
両 README 内に「現在の総属性数」と「現在の各カテゴリ件数」への言及が
存在するかだけを検証する (ポジティブな存在チェックのみ)。

意図的に「古い数値が残っていないか」は検出しない — フェーズ別内訳
(例: 「Phase 3: 25件」) など、属性総数と無関係な数字が本文に多数存在し、
数値ベースの stale 検出は誤検知が避けられないため。属性を増減させたら
その都度 README の総数・カテゴリ件数を新しい値に書き換える運用とし、
本スクリプトは「書き換え忘れ」だけを機械的に捕捉する。

使い方::

    python scripts/check_readme_counts.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tests"))
from catalog_counts import PUBLIC_CATEGORY_COUNTS, TOTAL_PUBLIC_ATTRIBUTES  # noqa: E402

README_EN = ROOT / "README.md"
README_JA = ROOT / "README.ja.md"


def check_file(path: Path) -> list[str]:
    errors: list[str] = []
    if not path.exists():
        return [f"{path} が存在しません"]
    text = path.read_text(encoding="utf-8")

    if str(TOTAL_PUBLIC_ATTRIBUTES) not in text:
        errors.append(
            f"{path.name}: 現在の総属性数 {TOTAL_PUBLIC_ATTRIBUTES} への言及が見つかりません"
        )

    for cat, count in PUBLIC_CATEGORY_COUNTS.items():
        # "archetype 66" / "archetype (66)" / "archetype | 66" のような近接表記を許容する。
        pattern = rf"{cat}[^\d]{{0,3}}{count}\b"
        if not re.search(pattern, text):
            errors.append(
                f"{path.name}: カテゴリ '{cat}' の件数 {count} への言及が見つかりません "
                f"(パターン: {pattern!r})"
            )
    return errors


def main() -> int:
    all_errors: list[str] = []
    for path in (README_EN, README_JA):
        all_errors.extend(check_file(path))

    if all_errors:
        print("NG: README の属性数表記にドリフトがあります:")
        for e in all_errors:
            print(f"  - {e}")
        print(
            "\n`tests/catalog_counts.py` (PUBLIC_CATEGORY_COUNTS / TOTAL_PUBLIC_ATTRIBUTES) "
            "を正として README.md / README.ja.md の数値を更新してください。"
        )
        return 1

    print(
        f"OK: README.md / README.ja.md は現在の属性数 "
        f"({TOTAL_PUBLIC_ATTRIBUTES}; {PUBLIC_CATEGORY_COUNTS}) と一致しています。"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
