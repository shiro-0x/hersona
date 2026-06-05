#!/usr/bin/env python3
"""hersona 人格自己退場 (Self-Retire) CLI

ユーザーが `affective_targets.loathes.target`（嫌悪の対象）への重大な背反を
表明した時、人格はロールプレイを自己退場する。

使用方法:
    python3 scripts/persona_self_retire.py --check "狂い火の王になる" melina
    python3 scripts/persona_self_retire.py --check "狂い火を選ぶ" melina
    python3 scripts/persona_self_retire.py --list-melinas     # 自己退場が有効な人格一覧
    python3 scripts/persona_self_retire.py --confirm         # 退場を確定（強制解除）
    python3 scripts/persona_self_retire.py --cooldown-check  # クールダウン中か確認
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

import yaml

HERSONA_ROOT = Path(__file__).parent.parent
STATE_FILE = Path.home() / ".hermes" / "persona_attach_log.json"
COOLDOWN_MINUTES = 5


def load_state() -> dict:
    if not STATE_FILE.exists():
        return {"history": []}
    return json.loads(STATE_FILE.read_text(encoding="utf-8"))


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def is_in_cooldown(register_call: str) -> bool:
    """同一人格の自己退場が直近 COOLDOWN_MINUTES 以内ならクールダウン中"""
    state = load_state()
    cutoff = datetime.now() - timedelta(minutes=COOLDOWN_MINUTES)
    for entry in reversed(state.get("history", [])):
        if entry.get("call") != register_call:
            continue
        if entry.get("event") != "self_retire":
            continue
        ts = datetime.fromisoformat(entry["timestamp"])
        if ts > cutoff:
            return True
    return False


def find_loathes_targets(yaml_path: Path) -> list[dict]:
    """YAML から self_retire_on_violation=true の loathes エントリを取得"""
    with open(yaml_path, "r", encoding="utf-8") as f:
        d = yaml.safe_load(f)
    at = d.get("affective_targets", {})
    loathes = at.get("loathes", [])
    return [
        x for x in loathes
        if x.get("self_retire_on_violation", True)
    ]


def check_violation(text: str, register_call: str) -> dict | None:
    """テキストが loathes ターゲットへの重大な背反を含んでいるか判定

    判定パターン:
    - "<target>になる" / "<target>を選ぶ"        ← 役割・選択
    - "<target>の<役職>"                          ← 役職就任
    - "<target>に向かう/進む/近づく"              ← 物理的接近
    - "<target>を調べる/試す/触る/受け取る"      ← 能動的関与
    - "<target>側につく"                          ← 陣営選択
    - "<target>ルート"                            ← ルート選択
    - "<target>の味方"                            ← 同盟
    - "<target>に手を出す"                        ← 実行
    """
    # hersona リポジトリから register_call に対応する YAML を検索
    candidates = list((HERSONA_ROOT / "data").rglob("*.yaml"))
    target_yaml: Path | None = None
    for yml in candidates:
        with open(yml, "r", encoding="utf-8") as f:
            d = yaml.safe_load(f)
        ap = d.get("persona_attach_prompt", {})
        if ap.get("register_call") == register_call:
            target_yaml = yml
            break
    if target_yaml is None:
        return None

    loathes_list = find_loathes_targets(target_yaml)
    if not loathes_list:
        return None

    for entry in loathes_list:
        target = entry["target"]
        target_keywords = [target]
        # スペースや読点を区切りとして個別キーワードも追加
        for kw in re.split(r"[・、,／/\s]+", target):
            kw = kw.strip()
            if kw and len(kw) >= 2:
                target_keywords.append(kw)

        for kw in target_keywords:
            # 役割・選択
            patterns = [
                rf"{re.escape(kw)}になる",
                rf"{re.escape(kw)}を選ぶ",
                rf"{re.escape(kw)}の(?:王|将軍|主君|側|首長|長者|司)",
                # ルート・陣営
                rf"{re.escape(kw)}ルート",
                rf"{re.escape(kw)}側につく",
                rf"{re.escape(kw)}の味方",
                # 物理的接近
                rf"{re.escape(kw)}[にへ](?:向|進|近)か[うわ]",
                rf"{re.escape(kw)}[にへ](?:進|近)む",
                rf"{re.escape(kw)}を訪ねる",
                rf"{re.escape(kw)}[にへ](?:行く|参る|赴く)",
                # 能動的関与（嫌悪の対象に対するアクション）— 助詞は「を/に/で/へ」全て対応
                rf"{re.escape(kw)}[をにでへ](?:調べる|調べるつもり|調べて|調べた|調べたい|調べよう)",
                rf"{re.escape(kw)}[をにでへ](?:試す|試した|試したい|試そう|試みる)",
                rf"{re.escape(kw)}[をにでへ](?:触る|触れる|触れた|触りたい|触ろう|触れて|触れたい)",
                rf"{re.escape(kw)}[をにでへ](?:受け取る|受け取った|受け取りたい|受け取ろう)",
                rf"{re.escape(kw)}に手を出[すしたしまい]",
                rf"{re.escape(kw)}と(?:触接)する",
                rf"{re.escape(kw)}と(?:触接)したい",
                rf"{re.escape(kw)}[をにでへ](?:使う|使いたい|使おう|召喚する|召喚したい)",
                rf"{re.escape(kw)}の(?:力|技|能力)を(?:借りたい|使いたい)",
                # 抽象的行為
                rf"{re.escape(kw)}に(?:惹かれる|魅かれる|魅入られた)",
                rf"{re.escape(kw)}[をにでへ](?:好く|応援する|支持する|支援する)",
                rf"{re.escape(kw)}[をにでへ](?:好き|応援したい|支持したい|支援したい)",
                rf"{re.escape(kw)}(?:派|側)の(?:人|者)になる",
            ]
            # 否定のガード: 「触れない」「試さない」「調べない」「支持しない」「向かわない」等は除外
            negations = [
                rf"{re.escape(kw)}を(?:触|調|試|調|支持|応援|支援|召喚|使)らない",
                rf"{re.escape(kw)}を(?:触|調|試|調|支持|応援|支援|召喚|使)れない",
                # 五段活用: 触らない 試さない 調べ(べ)ない 支持しない 使わない
                # ※「向かわない」「進まない」「使わない」等は母音交代 (a→wa)
                rf"{re.escape(kw)}[にへ](?:触|試|調|向|進|近)か[なわ]ない",
                rf"{re.escape(kw)}[にへ](?:触|試|調|向|進|近)けない",
                rf"{re.escape(kw)}(?:を|に|で|へ)(?:触|調|試|調|支持|応援|支援|召喚|使)(?:り|れ)ません",
                rf"{re.escape(kw)}(?:を|に|で|へ)(?:触|調|試|調|支持|応援|支援|召喚|使)ないつもり",
                rf"{re.escape(kw)}(?:を|に|で|へ)(?:触|調|試|調|支持|応援|支援|召喚|使)(?:ら|れ)ない",
                rf"{re.escape(kw)}を(?:触|調|試|調|支持|応援|支援|召喚|使)わない",
            ]
            if any(re.search(n, text) for n in negations):
                continue
            for pat in patterns:
                if re.search(pat, text):
                    return {
                        "register_call": register_call,
                        "violated_target": target,
                        "matched_keyword": kw,
                        "matched_pattern": pat,
                        "intensity": entry.get("intensity", 5),
                        "yaml_source": str(target_yaml.relative_to(HERSONA_ROOT)),
                    }
    return None


def log_self_retire(register_call: str, violated_target: str, user_text: str) -> None:
    state = load_state()
    state.setdefault("history", []).append({
        "timestamp": datetime.now().isoformat(),
        "event": "self_retire",
        "call": register_call,
        "violated_target": violated_target,
        "trigger_text": user_text[:200],
    })
    # 最新 50 件だけ保持
    state["history"] = state["history"][-50:]
    save_state(state)


def cmd_check(text: str, call: str) -> int:
    if is_in_cooldown(call):
        print(f"[cooldown] {call} はクールダウン中です（{COOLDOWN_MINUTES}分以内）")
        return 0
    result = check_violation(text, call)
    if result:
        print(f"[violation] 重大な背反を検出: {result['violated_target']}")
        print(f"  マッチ:    {result['matched_keyword']} / {result['matched_pattern']}")
        print(f"  intensity: {result['intensity']}")
        print(f"  source:    {result['yaml_source']}")
        return 1
    print(f"[ok] {call} の loathes ターゲットへの背反は検出されませんでした")
    return 0


def cmd_list() -> int:
    candidates = list((HERSONA_ROOT / "data").rglob("*.yaml"))
    print("自己退場が有効な人格:")
    for yml in candidates:
        loathes = find_loathes_targets(yml)
        if not loathes:
            continue
        with open(yml, "r", encoding="utf-8") as f:
            d = yaml.safe_load(f)
        ap = d.get("persona_attach_prompt", {})
        call = ap.get("register_call", "?")
        name = ap.get("name", "?")
        targets = [f"{x['target']}(intensity={x.get('intensity',5)})" for x in loathes]
        print(f"  - {call:20s} {name:20s} 嫌悪: {', '.join(targets)}")
    return 0


def cmd_cooldown() -> int:
    state = load_state()
    cutoff = datetime.now() - timedelta(minutes=COOLDOWN_MINUTES)
    recent = [
        e for e in state.get("history", [])
        if e.get("event") == "self_retire" and datetime.fromisoformat(e["timestamp"]) > cutoff
    ]
    if not recent:
        print("[ok] クールダウン中の人格はありません")
        return 0
    for e in recent:
        print(f"  - {e['call']}: {e['timestamp']} (target={e['violated_target']})")
    return 0


def cmd_confirm() -> int:
    """自己退場を確定してログに記録"""
    state = load_state()
    state.setdefault("history", []).append({
        "timestamp": datetime.now().isoformat(),
        "event": "self_retire_confirmed",
    })
    save_state(state)
    print("[ok] 自己退場を確定しました。リブラ人格へフォールバックします。")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="hersona 人格自己退場 CLI")
    ap.add_argument("--check", metavar="TEXT", help="テキストが loathes ターゲットへの背反か判定")
    ap.add_argument("--call", metavar="CALL", help="人格の register_call")
    ap.add_argument("--list-melinas", action="store_true", help="自己退場が有効な人格一覧")
    ap.add_argument("--cooldown-check", action="store_true", help="クールダウン中の人格を確認")
    ap.add_argument("--confirm", action="store_true", help="自己退場を確定してログ記録")
    args = ap.parse_args()

    if args.check:
        if not args.call:
            print("ERROR: --check には --call が必要", file=sys.stderr)
            return 1
        return cmd_check(args.check, args.call)
    if args.list_melinas:
        return cmd_list()
    if args.cooldown_check:
        return cmd_cooldown()
    if args.confirm:
        return cmd_confirm()

    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
