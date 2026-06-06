#!/usr/bin/env python3
"""DEPRECATED: fix_persona_block.py を使用してください。

toh エントリを `toh: |` ブロックスタイルに強制修正する。

hermes config set agent.personalities.toh "<YAML>" 経由の書き込みは、
値を YAML ブロック記法ごと文字列として格納してしまうバグがある
（`  toh: |\\n    あんた...` のような壊れた状態）。

fix_melina_block.py の toh 版。dry-run で確認後に書き込む。

使用方法:
    python3 scripts/fix_toh_block.py --dry-run
    python3 scripts/fix_toh_block.py
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

import yaml

CONFIG = Path.home() / ".hermes" / "config.yaml"
BACKUP_DIR = Path.home() / ".hermes" / "config_backups"
HERSONA_ROOT = Path(__file__).parent.parent
TOH_YAML = HERSONA_ROOT / "data" / "fate" / "tohsaka.yaml"
PERSONA_KEY = "toh"


def load_attach_prompt() -> str:
    """tohsaka.yaml の persona_attach_prompt.attach_prompt を取得"""
    with open(TOH_YAML, "r", encoding="utf-8") as f:
        d = yaml.safe_load(f)
    return d["persona_attach_prompt"]["attach_prompt"]


def backup_config(suffix: str) -> Path:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = BACKUP_DIR / f"config.yaml.bak.{suffix}.{ts}"
    if not dst.exists():
        shutil.copy2(CONFIG, dst)
    return dst


def find_broken_block(lines: list[str], key: str) -> tuple[int, int, str] | None:
    """`    <key>: "..."` または `'...'` インライン壊れエントリの行範囲を返す。

    戻り値: (start_idx, end_idx_exclusive, indent_str)
    """
    for i, line in enumerate(lines):
        m = re.match(rf"^(\s+){re.escape(key)}:\s*[\"']", line)
        if m:
            indent = m.group(1)
            end = i + 1
            while end < len(lines):
                ln = lines[end]
                if ln == "":
                    end += 1
                    continue
                # インライン継続: 同じ/深いインデントで `\` または `\u` 始まりの行
                if re.match(r"^\s+\\$", ln) or re.match(r"^\s+\\u", ln):
                    end += 1
                    continue
                break
            return (i, end, indent)
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not CONFIG.exists():
        print(f"ERROR: {CONFIG} が存在しません", file=sys.stderr)
        return 1

    body = load_attach_prompt()
    print(f"[load] tohsaka.yaml から attach_prompt {len(body)} chars 取得")

    text = CONFIG.read_text(encoding="utf-8")
    lines = text.split("\n")

    found = find_broken_block(lines, PERSONA_KEY)
    if found is None:
        # 既に `toh: |` ブロックスタイルか、未登録
        if re.search(rf"^\s+{re.escape(PERSONA_KEY)}:\s*\|", text, re.MULTILINE):
            print(f"[ok] {PERSONA_KEY} は既に `{PERSONA_KEY}: |` ブロックスタイルで登録されています")
            return 0
        print(f"ERROR: `{PERSONA_KEY}:` エントリが見つかりません", file=sys.stderr)
        return 1

    start, end, indent = found
    print(f"[find] 壊れエントリ: 行 {start+1}-{end}（{end - start}行, indent: {len(indent)} spaces）")

    if args.dry_run:
        print()
        print(f"=== 修正後のブロック（書き込み予定） ===")
        print(f"{indent}{PERSONA_KEY}: |")
        for body_line in body.split("\n"):
            print(f"{indent}  {body_line}")
        return 0

    bak = backup_config("fix_toh")
    print(f"[backup] {bak}")

    new_block = [f"{indent}{PERSONA_KEY}: |"]
    for body_line in body.split("\n"):
        new_block.append(f"{indent}  {body_line}")

    lines = lines[:start] + new_block + lines[end:]
    CONFIG.write_text("\n".join(lines), encoding="utf-8")
    print(f"[write] {CONFIG} に {len(new_block)}行で書き込み")

    # 検証
    with open(CONFIG, "r", encoding="utf-8") as f:
        parsed = yaml.safe_load(f)
    toh = parsed.get("agent", {}).get("personalities", {}).get(PERSONA_KEY)
    if isinstance(toh, str) and not toh.startswith("\\") and "toh: |" not in toh[:20]:
        print(f"[ok] {PERSONA_KEY} エントリ修正完了（{len(toh)} chars、先頭: {repr(toh[:30])}）")
        return 0
    print(f"[error] 修正後の {PERSONA_KEY} がまだ壊れている: {type(toh).__name__} {repr(toh)[:60]}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
