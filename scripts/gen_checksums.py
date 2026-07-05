#!/usr/bin/env python3
"""``checksums.json`` (attributes/ + schema/ の SHA-256 マニフェスト) を生成する。

外部レビュー対応 (docs/reviews/2026-07-04-external-review-response.md §P2-1):
`hersona update` はダウンロードしたアーカイブの内容を、この manifest を
GitHub の別配信経路 (raw.githubusercontent.com; codeload とは別の CDN パス)
から取得して検証する。本スクリプトはその manifest 自体を生成する側。

**このチェックサムが守るもの / 守らないもの (誇張しないための明記)**:
- 守る: 転送経路上の改ざん・破損 (単一の CDN エッジ/中間者攻撃で archive の
  みが改ざんされ、checksums.json が無傷なケースを検知できる)。
- 守らない: リポジトリ / GitHub アカウント自体が侵害された場合。archive と
  checksums.json は同じコミットツリーに由来するため、両方を書き換えられる
  攻撃者からは保護しない。署名 (Sigstore/SLSA provenance) ではない。

使い方::

    python scripts/gen_checksums.py            # checksums.json を生成
    python scripts/gen_checksums.py --check     # 既存と差分がないか検証 (CI 用)
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "checksums.json"

# hersona.core.update.DATA_DIRS と同じ対象 (循環 import を避けるため直接定義)
DATA_DIRS: tuple[str, ...] = ("attributes", "schema")
ALGORITHM = "sha256"


def _hash_file(path: Path) -> str:
    h = hashlib.new(ALGORITHM)
    h.update(path.read_bytes())
    return h.hexdigest()


def build_manifest() -> dict:
    files: dict[str, str] = {}
    for data_dir in DATA_DIRS:
        root = ROOT / data_dir
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(ROOT).as_posix()
            files[rel] = _hash_file(path)
    return {
        "algorithm": ALGORITHM,
        "count": len(files),
        "files": files,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="生成結果が既存 checksums.json と一致するか検証 (書き込まない)",
    )
    args = parser.parse_args()

    manifest = build_manifest()
    rendered = json.dumps(manifest, indent=2, sort_keys=True) + "\n"

    if args.check:
        if not OUT.exists():
            print(f"NG: {OUT} が存在しません。`python scripts/gen_checksums.py` を実行してください。")
            return 1
        current = OUT.read_text(encoding="utf-8")
        if current != rendered:
            print(f"NG: {OUT} が最新ではありません。`python scripts/gen_checksums.py` で再生成してください。")
            return 1
        print(f"OK: {OUT} は最新です ({manifest['count']} ファイル)。")
        return 0

    OUT.write_text(rendered, encoding="utf-8")
    print(f"書き出しました: {OUT} ({manifest['count']} ファイル)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
