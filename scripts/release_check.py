#!/usr/bin/env python3
"""リリース前のドライラン: 既存の CI ゲートをローカルでまとめて実行する。

外部レビュー対応 (docs/reviews/2026-07-04-external-review-response.md §P3-1):
「リリース運用に粗さがある」(semver ロールバック等) への対処。個々のゲート
(validate.py / build_site.py --check / check_readme_counts.py /
gen_checksums.py --check / ruff / pytest) は CI (.github/workflows/ci.yml) に
既にあるが、タグを打つ前にローカルで同じチェックを一括実行し、CI で落ちて
から気付く手戻りを減らす。CI のジョブ定義を変更したらこのスクリプトの
_STEPS も合わせて更新すること (二重管理だが、依存関係インストール前提が
異なるため統合はしない — CI は `uv sync` 済み venv 前提、本スクリプトは
ローカルの `uv run` に委ねる)。

使い方::

    python scripts/release_check.py            # 全ゲートを順に実行
    python scripts/release_check.py --skip-pytest  # pytest (数分かかる) を除外
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

_STEPS: list[tuple[str, list[str]]] = [
    ("ruff check", ["uv", "run", "ruff", "check"]),
    ("attribute schema validation", ["uv", "run", "python", "scripts/validate.py"]),
    ("demo site data freshness", ["uv", "run", "python", "scripts/build_site.py", "--check"]),
    ("README attribute-count drift", ["uv", "run", "python", "scripts/check_readme_counts.py"]),
    ("checksums.json freshness", ["uv", "run", "python", "scripts/gen_checksums.py", "--check"]),
]

_PYTEST_STEP = ("pytest (full suite)", ["uv", "run", "pytest", "-q"])


def _run_step(name: str, cmd: list[str]) -> bool:
    print(f"\n=== {name} ===")
    start = time.monotonic()
    result = subprocess.run(cmd, cwd=ROOT)
    elapsed = time.monotonic() - start
    ok = result.returncode == 0
    status = "OK" if ok else "FAILED"
    print(f"--- {name}: {status} ({elapsed:.1f}s) ---")
    return ok


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-pytest",
        action="store_true",
        help="pytest フルスイート (数分かかる) をスキップし、他のゲートだけ素早く確認する",
    )
    args = parser.parse_args()

    steps = list(_STEPS)
    if not args.skip_pytest:
        steps.append(_PYTEST_STEP)

    results: list[tuple[str, bool]] = []
    for name, cmd in steps:
        results.append((name, _run_step(name, cmd)))

    print("\n=== Summary ===")
    failed = [name for name, ok in results if not ok]
    for name, ok in results:
        mark = "✓" if ok else "✗"
        print(f"  {mark} {name}")

    if failed:
        print(f"\nNG: {len(failed)} gate(s) failed: {', '.join(failed)}")
        print("Fix these before tagging a release (see docs/RELEASE_CHECKLIST.md).")
        return 1

    print("\nOK: all gates passed. Safe to proceed with the release checklist"
          " (docs/RELEASE_CHECKLIST.md) — this script does not cover the"
          " manual steps (CHANGELOG heading, version bump, tagging).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
