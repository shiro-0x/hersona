#!/usr/bin/env python3
"""merina エントリを `melina: |` ブロックスタイルに強制修正する。

apply_persona_to_config.py v1 が `melina: "\n..."` インライン文字列として
書き込んでしまったバグの修正版。直接テキスト置換で config.yaml を書き直す。

使用方法:
    python3 scripts/fix_melina_block.py --dry-run
    python3 scripts/fix_melina_block.py
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
MELINA_YAML = HERSONA_ROOT / "data" / "elden-ring" / "melina.yaml"


def load_attach_prompt() -> str:
    """melina.yaml の persona_attach_prompt.attach_prompt を取得"""
    with open(MELINA_YAML, "r", encoding="utf-8") as f:
        d = yaml.safe_load(f)
    return d["persona_attach_prompt"]["attach_prompt"]


def backup_config() -> Path:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = BACKUP_DIR / f"config.yaml.bak.fix_melina.{ts}"
    if not dst.exists():
        shutil.copy2(CONFIG, dst)
    return dst


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not CONFIG.exists():
        print(f"ERROR: {CONFIG} が存在しません", file=sys.stderr)
        return 1

    body = load_attach_prompt()
    print(f"[load] melina.yaml から attach_prompt {len(body)} chars 取得")

    text = CONFIG.read_text(encoding="utf-8")
    lines = text.split("\n")

    # `    melina: "..."` または `    melina: '...'` の行を探す
    # （壊れたインライン文字列）
    melina_start = None
    for i, line in enumerate(lines):
        m = re.match(r"^(\s+)melina:\s*[\"']", line)
        if m:
            melina_start = i
            break

    if melina_start is None:
        # `melina: |` ブロックスタイルか、メリーナ未登録
        m2 = re.match(r"^(\s+)melina:\s*\|", "\n".join(lines))
        if m2:
            print("[ok] メリーナは既に `melina: |` ブロックスタイルで登録されています")
            return 0
        print("ERROR: `melina:` エントリが見つかりません", file=sys.stderr)
        return 1

    indent = re.match(r"^(\s+)", lines[melina_start]).group(1)
    # ブロックの終了を、インデント ≤ indent の非空行で判定
    end = melina_start + 1
    while end < len(lines):
        line = lines[end]
        if line == "":
            end += 1
            continue
        # インライン文字列の継続行: 次の行も同じか深いインデントで `\` 続き
        # ここでは「`      \\`」で始まる行 = インライン継続
        if re.match(r"^\s+\\$", line) or re.match(r"^\s+\\u", line):
            end += 1
            continue
        break

    print(f"[find] メリーナ壊れエントリ: 行 {melina_start+1}-{end}（{end - melina_start}行）")
    print(f"[find] indent: {len(indent)} spaces")

    if args.dry_run:
        print()
        print("=== 修正後のブロック（書き込み予定） ===")
        print(f"{indent}melina: |")
        for body_line in body.split("\n"):
            print(f"{indent}  {body_line}")
        return 0

    bak = backup_config()
    print(f"[backup] {bak}")

    # 壊れたブロックを削除し、新しいブロックに差し替え
    new_block = [f"{indent}melina: |"]
    for body_line in body.split("\n"):
        new_block.append(f"{indent}  {body_line}")

    lines = lines[:melina_start] + new_block + lines[end:]
    CONFIG.write_text("\n".join(lines), encoding="utf-8")
    print(f"[write] {CONFIG} に {len(new_block)}行で書き込み")

    # 検証
    with open(CONFIG, "r", encoding="utf-8") as f:
        parsed = yaml.safe_load(f)
    melina = parsed.get("agent", {}).get("personalities", {}).get("melina")
    if isinstance(melina, str) and not melina.startswith("\\"):
        print(f"[ok] メリーナエントリ修正完了（{len(melina)} chars、先頭: {repr(melina[:30])}）")
        return 0
    print(f"[error] 修正後のメリーナがまだ壊れている: {type(melina).__name__} {repr(melina)[:60]}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
