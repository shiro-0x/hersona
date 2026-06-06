#!/usr/bin/env python3
"""壊れた personalities.<key> インライン文字列エントリを `key: |` ブロックスタイルに修正する汎用スクリプト。

## 背景

`hermes config set agent.personalities.<key> "<値>"` 経由で config.yaml に
書き込むと、値が YAML ブロック記法ごと **文字列として** 格納されてしまう
バグがある（`hermes config set` はネスト構造に非対応、`<値>` 全体を plain
string として書く）。

例（壊れた状態）:
```yaml
personalities:
  toh: "  toh: |\n    あんた、今日より私は遠坂凛として..."
```

正しい状態:
```yaml
personalities:
  toh: |
    あんた、今日より私は遠坂凛として...
```

`data/<title>/<character>.yaml` の `persona_attach_prompt.attach_prompt` を
真の値として config.yaml に書き直す。

## 使用方法

```bash
# melina 用（既存の挙動を完全再現）
python3 scripts/fix_persona_block.py melina

# toh 用
python3 scripts/fix_persona_block.py toh

# 任意の register_call
python3 scripts/fix_persona_block.py <call>

# ドライラン
python3 scripts/fix_persona_block.py <call> --dry-run
```

## register_call → data ファイル解決

`data/<title>/<character>.yaml` のうち、register_call と一致する人格が
含まれるファイルを探す。`data/<title>/_index.md` のテーブル、
または `data/fate/_index.md` のような index ファイルから逆引きする。

見つからない場合、`data/fate/tohsaka.yaml` のようにファイル名と
register_call が違うケースに対応するため、register_call が `toh` なら
`data/**/to*.yaml` のような glob 候補も試す。
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
DATA_DIR = HERSONA_ROOT / "data"


def find_persona_yaml(call: str) -> Path | None:
    """register_call から対応する data/<title>/<character>.yaml を探す。

    1. まず全 data/**/*.yaml を走査し、persona_attach_prompt.register_call
       が一致するファイルを探す
    2. 見つからなければエラー
    """
    if not DATA_DIR.exists():
        return None
    for yaml_path in DATA_DIR.rglob("*.yaml"):
        try:
            d = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        pap = d.get("persona_attach_prompt", {}) if isinstance(d, dict) else {}
        if pap.get("register_call") == call:
            return yaml_path
    return None


def load_attach_prompt(yaml_path: Path) -> str:
    with open(yaml_path, "r", encoding="utf-8") as f:
        d = yaml.safe_load(f)
    return d["persona_attach_prompt"]["attach_prompt"]


def backup_config(suffix: str) -> Path:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = BACKUP_DIR / f"config.yaml.bak.fix_{suffix}.{ts}"
    if not dst.exists():
        shutil.copy2(CONFIG, dst)
    return dst


def find_broken_block(lines: list[str], key: str) -> tuple[int, int, str] | None:
    """`    <key>: "..."` または `'...'` インライン壊れエントリの行範囲を返す。"""
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
                if re.match(r"^\s+\\$", ln) or re.match(r"^\s+\\u", ln):
                    end += 1
                    continue
                break
            return (i, end, indent)
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("call", help="register_call（例: melina, toh）")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not CONFIG.exists():
        print(f"ERROR: {CONFIG} が存在しません", file=sys.stderr)
        return 1

    persona_yaml = find_persona_yaml(args.call)
    if persona_yaml is None:
        print(f"ERROR: register_call={args.call} に対応する data/**/*.yaml が見つかりません", file=sys.stderr)
        return 1
    print(f"[load] {persona_yaml.relative_to(HERSONA_ROOT)} から attach_prompt を取得")

    body = load_attach_prompt(persona_yaml)
    print(f"[load] {len(body)} chars 取得")

    text = CONFIG.read_text(encoding="utf-8")
    lines = text.split("\n")

    found = find_broken_block(lines, args.call)
    if found is None:
        # 既に `key: |` ブロックスタイルか、未登録
        if re.search(rf"^\s+{re.escape(args.call)}:\s*\|", text, re.MULTILINE):
            print(f"[ok] {args.call} は既に `{args.call}: |` ブロックスタイルで登録されています")
            return 0
        print(f"ERROR: `{args.call}:` エントリが config.yaml に見つかりません", file=sys.stderr)
        return 1

    start, end, indent = found
    print(f"[find] 壊れエントリ: 行 {start+1}-{end}（{end - start}行, indent: {len(indent)} spaces）")

    if args.dry_run:
        print()
        print(f"=== 修正後のブロック（書き込み予定） ===")
        print(f"{indent}{args.call}: |")
        for body_line in body.split("\n"):
            print(f"{indent}  {body_line}")
        return 0

    bak = backup_config(args.call)
    print(f"[backup] {bak}")

    new_block = [f"{indent}{args.call}: |"]
    for body_line in body.split("\n"):
        new_block.append(f"{indent}  {body_line}")

    lines = lines[:start] + new_block + lines[end:]
    CONFIG.write_text("\n".join(lines), encoding="utf-8")
    print(f"[write] {CONFIG} に {len(new_block)}行で書き込み")

    # 検証
    with open(CONFIG, "r", encoding="utf-8") as f:
        parsed = yaml.safe_load(f)
    val = parsed.get("agent", {}).get("personalities", {}).get(args.call)
    if isinstance(val, str) and not val.startswith("\\") and f"{args.call}: |" not in val[:20]:
        print(f"[ok] {args.call} エントリ修正完了（{len(val)} chars、先頭: {repr(val[:30])}）")
        return 0
    print(f"[error] 修正後の {args.call} がまだ壊れている: {type(val).__name__} {repr(val)[:60]}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
