#!/usr/bin/env python3
"""hersona persistent モード：config.yaml にメリーナ人格を実際に書き込む

scripts/run_hersona.sh --persist から呼ばれる、または直接実行可能。
自動バックアップは run_hersona.sh 側で取得済み。

動作:
  1. scripts/persona_attach.py --register <call> で YAML 抜粋を生成
  2. ~/.hermes/config.yaml の agent.personalities.<call> にマージ
  3. 既存エントリがあれば上書き
  4. YAML 構文を最後にパースチェック

使用法:
    python3 scripts/apply_persona_to_config.py melina --dry-run   # 書き込み内容を確認
    python3 scripts/apply_persona_to_config.py melina              # 実際に書き込み
    python3 scripts/apply_persona_to_config.py --list              # 登録されている人格を表示
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: pyyaml が必要です", file=sys.stderr)
    sys.exit(1)


HERSONA_ROOT = Path(__file__).parent.parent
CONFIG = Path.home() / ".hermes" / "config.yaml"
BACKUP_DIR = Path.home() / ".hermes" / "config_backups"


def extract_register_call(yaml_text: str) -> str:
    """persona_attach.py --register が出力する YAML から <call>: | ブロックを抽出"""
    # `  <call>: |\n` で始まり、`    `（4スペース）インデントの複数行
    # 簡易的に、`  melina: |\n` のあとの indent 4 スペースのブロックを抽出
    lines = yaml_text.split("\n")
    out: list[str] = []
    in_block = False
    block_indent = 0
    for line in lines:
        m = re.match(r"^  ([a-z][a-z0-9_-]*):\s*\|\s*$", line)
        if m:
            in_block = True
            block_indent = 2
            out.append(line)
            continue
        if in_block:
            if line == "" or line.startswith(" " * 4) or line.startswith(" " * (block_indent + 2)):
                out.append(line)
            else:
                in_block = False
                # 次の call ブロックに備えて継続
    return "\n".join(out).rstrip()


def backup_config() -> Path:
    """config.yaml のバックアップを作成（既にバックアップされていなければ）"""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = BACKUP_DIR / f"config.yaml.bak.{ts}"
    if not dst.exists():
        shutil.copy2(CONFIG, dst)
    return dst


def read_config() -> dict:
    with open(CONFIG, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def write_config(data: dict) -> None:
    with open(CONFIG, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def generate_register_yaml(call: str) -> str:
    """persona_attach.py --register を実行して YAML 抜粋を取得"""
    result = subprocess.run(
        [sys.executable, str(HERSONA_ROOT / "scripts" / "persona_attach.py"),
         "--register", call, "--repo-root", str(HERSONA_ROOT)],
        capture_output=True, text=True, check=True,
    )
    return result.stdout


def parse_attach_block(yaml_text: str) -> tuple[str, str]:
    """出力 YAML から (register_call, 4スペースインデントの本文) を抽出"""
    # `  <call>: |` を探す
    m = re.search(r"^  ([a-z][a-z0-9_-]*):\s*\|\s*$", yaml_text, re.MULTILINE)
    if not m:
        raise ValueError("登録用 YAML から `  <call>: |` ブロックが見つかりません")
    call = m.group(1)
    start = m.end()
    # ブロック本文: 4スペースインデントの連続行を、2スペースインデントに変換
    lines = yaml_text[start:].split("\n")
    body_lines: list[str] = []
    for line in lines:
        if line.startswith("    "):
            body_lines.append(line[2:])  # 4スペース → 2スペースに
        elif line == "":
            body_lines.append("")
        else:
            break
    body = "\n".join(body_lines).rstrip("\n")
    return call, body


def dump_with_block_style(call: str, body: str) -> None:
    """<call>: | ブロックスタイルで config.yaml に直接追記・上書き

    元の config.yaml の構造（順序・コメント）を保つため、
    該当キーの値だけ部分的に書き換える。
    """
    text = CONFIG.read_text(encoding="utf-8")
    lines = text.split("\n")

    # agent.personalities の開始・終了行を特定
    start_idx = None
    personalities_indent = 0
    for i, line in enumerate(lines):
        m = re.match(r"^(\s*)personalities:\s*$", line)
        if m:
            start_idx = i
            personalities_indent = len(m.group(1))
            break
    if start_idx is None:
        # personalities セクションが無い → 追加
        agent_idx = None
        for i, line in enumerate(lines):
            if line.startswith("agent:"):
                agent_idx = i
                break
        if agent_idx is None:
            print("ERROR: agent: セクションが見つかりません", file=sys.stderr)
            sys.exit(1)
        end_idx = agent_idx + 1
        while end_idx < len(lines) and (lines[end_idx].startswith(" ") or lines[end_idx] == ""):
            end_idx += 1
        new_section = [f"{' ' * (personalities_indent + 2)}personalities:",
                       f"{' ' * (personalities_indent + 4)}{call}: |"]
        for body_line in body.split("\n"):
            new_section.append(f"{' ' * (personalities_indent + 6)}{body_line}" if body_line else "")
        lines = lines[:end_idx] + new_section + lines[end_idx:]
        CONFIG.write_text("\n".join(lines), encoding="utf-8")
        return

    end_idx = start_idx + 1
    child_indent = personalities_indent + 2
    while end_idx < len(lines):
        line = lines[end_idx]
        if line == "":
            end_idx += 1
            continue
        if line.startswith(" " * child_indent):
            end_idx += 1
            continue
        break

    # 既存 <call> エントリがあれば削除
    call_pattern = re.compile(rf"^(\s*){re.escape(call)}:\s*\|")
    i = start_idx + 1
    while i < end_idx:
        m = call_pattern.match(lines[i])
        if m:
            del_start = i
            block_indent = len(m.group(1))
            i += 1
            while i < end_idx:
                line = lines[i]
                if line == "":
                    i += 1
                    continue
                if len(line) - len(line.lstrip(" ")) > block_indent:
                    i += 1
                    continue
                break
            del_end = i
            lines = lines[:del_start] + lines[del_end:]
            end_idx -= (del_end - del_start)
            break
        i += 1

    # 新エントリを挿入（end_idx の手前）
    new_block = [f"{' ' * child_indent}{call}: |"]
    for body_line in body.split("\n"):
        if body_line == "":
            new_block.append("")
        else:
            new_block.append(f"{' ' * (child_indent + 2)}{body_line}")
    lines = lines[:end_idx] + new_block + lines[end_idx:]

    CONFIG.write_text("\n".join(lines), encoding="utf-8")


def list_registered() -> list[str]:
    """config.yaml に現在登録されている人格名"""
    if not CONFIG.exists():
        return []
    data = read_config()
    return list(data.get("agent", {}).get("personalities", {}).keys())


def apply(call: str, dry_run: bool = False) -> int:
    if not CONFIG.exists():
        print(f"ERROR: {CONFIG} が存在しません", file=sys.stderr)
        return 1

    # 1. 登録用 YAML 抜粋を生成
    raw = generate_register_yaml(call)
    block_call, body = parse_attach_block(raw)
    if block_call != call:
        print(f"ERROR: 想定 call={call} に対し抽出 call={block_call}", file=sys.stderr)
        return 1

    # 2. 現在の config.yaml を読み込み
    data = read_config()
    agent = data.setdefault("agent", {})
    personalities = agent.setdefault("personalities", {})

    if call in personalities:
        print(f"[update] {CONFIG} の agent.personalities.{call} を上書きします")
    else:
        print(f"[add]    {CONFIG} の agent.personalities.{call} を新規追加します")

    # 3. dry-run
    if dry_run:
        print()
        print("--- 書き込み予定内容 ---")
        print(yaml.dump({"agent": {"personalities": {call: body}}},
                        allow_unicode=True, default_flow_style=False, sort_keys=False))
        return 0

    # 4. バックアップ
    if not dry_run:
        bak = backup_config()
        print(f"[backup] {bak}")

    # 5. 書き換え（テキスト直接編集でブロックスタイルを保持）
    if not dry_run:
        dump_with_block_style(call, body)

    # 6. パース確認
    try:
        with open(CONFIG, "r", encoding="utf-8") as f:
            parsed = yaml.safe_load(f)
        registered_call = parsed.get("agent", {}).get("personalities", {}).get(call)
        if not registered_call:
            print(f"[error]  書き込み後の config.yaml に {call} が見つかりません", file=sys.stderr)
            return 2
        print(f"[ok]     {CONFIG} の YAML パース確認 OK（{call} 登録確認）")
    except yaml.YAMLError as e:
        print(f"[error]  YAML パース失敗: {e}", file=sys.stderr)
        return 2

    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="hersona persistent モード: config.yaml への人格登録")
    ap.add_argument("call", nargs="?", help="register_call（例: melina）")
    ap.add_argument("--dry-run", action="store_true", help="書き込み内容を確認のみ")
    ap.add_argument("--list", action="store_true", help="登録済み人格一覧")
    args = ap.parse_args()

    if args.list:
        names = list_registered()
        print(f"~/.hermes/config.yaml の agent.personalities 登録: {len(names)}件")
        for n in names:
            print(f"  - {n}")
        return 0

    if not args.call:
        ap.print_help()
        return 1

    return apply(args.call, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
