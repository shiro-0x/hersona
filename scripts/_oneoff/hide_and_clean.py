#!/usr/bin/env python3
"""
hide_and_clean.py — hersona リポジトリ非公開化 + 関連リンク削除

スコープ（C 確定）:
  1. README.md の「## 関連リンク」セクションまるごと削除
  2. skills/hersona/SKILL.md の hersona-collector / hersona-writer 言及削除
  3. data/chainsaw-man/power.yaml.orig 削除 + .gitignore に *.orig 追加
  4. gh repo edit --visibility private
  5. 既存 open issue/PR があればクローズ（なければログのみ）
  6. コミット + push
  7. 出典URL（キャラ MD 内の Wiki URL）は触らない
  8. X は触らない

使用法:
  python3 hide_and_clean.py --dry-run        # ファイル変更の diff + gh コマンド echo のみ
  python3 hide_and_clean.py --apply          # 実実行
  python3 hide_and_clean.py --report-now "メッセージ"  # 手動で Telegram 報告
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

REPO = Path("/Users/sekihiroyuki/projects/hersona")
JST = timezone(timedelta(hours=9))
TG_CHAT_ID = "6167812250"  # home channel

# 10分タイマー（秒）
REPORT_INTERVAL = 600

# Telegram 報告用：hermes .env から BOT_TOKEN を読む
HERMES_ENV = Path.home() / ".hermes" / ".env"


def now_jst() -> str:
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST")


def get_bot_token() -> str | None:
    if not HERMES_ENV.exists():
        return None
    for line in HERMES_ENV.read_text().splitlines():
        prefix = "TELEGRAM_BOT_TOKEN"
        if line.startswith(prefix + "=") or line.startswith(prefix + " "):
            val = line.split("=", 1)[1].strip().strip('"').strip("'")
            if val and val != "***":
                return val
    return None


def send_telegram(text: str) -> bool:
    """Telegram ホームチャンネルに送る。失敗しても処理は止めない。"""
    import json
    import urllib.parse
    import urllib.request

    token = get_bot_token()
    if not token:
        print(f"[TG] BOT_TOKEN 未設定、スキップ: {text[:60]}...")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": TG_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": "true",
    }).encode()
    try:
        with urllib.request.urlopen(url, data=data, timeout=15) as r:
            body = json.loads(r.read().decode())
            if not body.get("ok"):
                print(f"[TG] 送信失敗: {body}")
                return False
            return True
    except Exception as e:
        print(f"[TG] 例外: {e}")
        return False


def run(cmd, *, check: bool = True, cwd: Path | None = None,
        capture: bool = True) -> subprocess.CompletedProcess:
    if isinstance(cmd, str):
        shell = True
    else:
        shell = False
    return subprocess.run(
        cmd, shell=shell, check=check, cwd=cwd or REPO,
        capture_output=capture, text=True,
    )


# --- ファイル変更 ---

def edit_readme(dry_run: bool) -> str:
    """README.md の「## 関連リンク」セクションを削除。"""
    p = REPO / "README.md"
    text = p.read_text()
    needle = "\n## 関連リンク\n\n- リポジトリ: https://github.com/shiro-0x/hersona\n- 関連スキル: hersona-collector / hersona-writer / hersona-publisher\n"
    if needle not in text:
        return "SKIP: README.md にセクション見つからず（既に削除済？）"
    new_text = text.replace(needle, "")
    diff = _diff(text, new_text, p.name)
    if not dry_run:
        p.write_text(new_text)
    return diff


def edit_skill_md(dry_run: bool) -> str:
    """skills/hersona/SKILL.md の collector/writer 言及を削除。"""
    p = REPO / "skills" / "hersona" / "SKILL.md"
    text = p.read_text()
    diffs = []

    # 1) Don't use for の行
    needle1 = (
        "- 新しいキャラを作る場合（`hermes kanban` で `hersona-collector` / `hersona-writer` に投げる）\n"
    )
    repl1 = "- 新しいキャラを作る場合（運用は `CONTRIBUTING.md` を参照）\n"
    if needle1 in text:
        text = text.replace(needle1, repl1)
        diffs.append("L33: collector/writer 言及 → CONTRIBUTING.md 参照に置換")
    else:
        diffs.append("L33: 既に置換済 / パターン不一致（スキップ）")

    # 2) 別キャラ追加レシピのコードブロック
    needle2 = (
        "# 1. セリフ収集（hersona-collector ワーカー）\n"
        "hermes kanban --board hersona create \"<キャラ> セリフ調査\" \\\n"
        "  --assignee hersona-collector\n"
        "\n"
        "# 2. YAML+MD生成（hersona-writer ワーカー）\n"
        "# → data/<title>/<character>.yaml の persona_attach_prompt を定義\n"
    )
    repl2 = (
        "# 1. セリフ収集\n"
        "# → data/<title>/<character>.yaml / .md のセリフ引用に Wiki URL 必須\n"
        "#\n"
        "# 2. YAML+MD生成\n"
        "# → data/<title>/<character>.yaml の persona_attach_prompt を定義\n"
    )
    if needle2 in text:
        text = text.replace(needle2, repl2)
        diffs.append("L241-246: kanban ワーカー → シンプルな手順に置換")
    else:
        diffs.append("L241-246: 既に置換済 / パターン不一致（スキップ）")

    if not dry_run:
        p.write_text(text)
    return "\n".join(diffs)


def remove_orig(dry_run: bool) -> str:
    p = REPO / "data" / "chainsaw-man" / "power.yaml.orig"
    if not p.exists():
        return "SKIP: power.yaml.orig 存在せず"
    if dry_run:
        return f"DRY-RUN: rm {p}"
    p.unlink()
    return f"DELETED: {p}"


def add_gitignore(dry_run: bool) -> str:
    p = REPO / ".gitignore"
    text = p.read_text()
    line = "*.orig"
    if any(line in ln for ln in text.splitlines()):
        return "SKIP: .gitignore に *.orig 既存"
    new_text = text.rstrip("\n") + "\n\n# Backup files (e.g. power.yaml.orig)\n" + line + "\n"
    if dry_run:
        return f"DRY-RUN: append '*.orig' to {p}"
    p.write_text(new_text)
    return f"APPENDED: *.orig to {p}"


def _diff(old: str, new: str, label: str) -> str:
    """簡易 diff 表示。"""
    import difflib
    diff = list(difflib.unified_diff(
        old.splitlines(keepends=True),
        new.splitlines(keepends=True),
        fromfile=f"a/{label}",
        tofile=f"b/{label}",
        n=2,
    ))
    if not diff:
        return f"NO-CHANGE: {label}"
    return "".join(diff)


# --- gh コマンド ---

def list_open_issues_prs() -> dict:
    out = {"issues": [], "prs": []}
    for kind, cmd in [
        ("issues", ["gh", "issue", "list", "--state", "open",
                    "--json", "number,title,url", "--limit", "100"]),
        ("prs", ["gh", "pr", "list", "--state", "open",
                 "--json", "number,title,url", "--limit", "100"]),
    ]:
        try:
            r = run(cmd, check=False)
            if r.returncode == 0 and r.stdout.strip():
                import json
                out[kind] = json.loads(r.stdout)
        except Exception as e:
            print(f"[gh {kind} list] {e}")
    return out


def close_issues_prs(issues, prs, dry_run: bool) -> str:
    actions = []
    for issue in issues:
        n = issue["number"]
        cmd = ["gh", "issue", "close", str(n), "--comment",
               "hersona リポジトリを private 化するため自動クローズ。"]
        if dry_run:
            actions.append(f"DRY-RUN: {' '.join(cmd)}")
        else:
            r = run(cmd, check=False)
            actions.append(f"CLOSE issue #{n}: rc={r.returncode}")
    for pr in prs:
        n = pr["number"]
        cmd = ["gh", "pr", "close", str(n), "--comment",
               "hersona リポジトリを private 化するため自動クローズ。", "--delete-branch"]
        if dry_run:
            actions.append(f"DRY-RUN: {' '.join(cmd)}")
        else:
            r = run(cmd, check=False)
            actions.append(f"CLOSE pr #{n}: rc={r.returncode}")
    return "\n".join(actions) if actions else "対象 issue/PR なし"


def make_repo_private(dry_run: bool) -> str:
    cmd = ["gh", "repo", "edit", "shiro-0x/hersona", "--visibility", "private",
           "--accept-visibility-change-consequences"]
    if dry_run:
        return f"DRY-RUN: {' '.join(cmd)}"
    r = run(cmd, check=False)
    out = f"gh repo edit rc={r.returncode}\nstdout: {r.stdout.strip()}\nstderr: {r.stderr.strip()}"
    return out


# --- 進捗報告 ---

REPORT_FILE = Path("/tmp/hersona_hide_report.log")


def log(msg: str) -> None:
    line = f"[{now_jst()}] {msg}"
    print(line, flush=True)
    with REPORT_FILE.open("a") as f:
        f.write(line + "\n")


# --- 10分タイマー（進捗報告） ---

class ProgressTicker:
    """バックグラウンドで 10分ごとに Telegram へ進捗を送る。"""

    def __init__(self, phase_fn, interval: int = REPORT_INTERVAL):
        self.phase_fn = phase_fn
        self.interval = interval
        self._stop = threading.Event()
        self._t: threading.Thread | None = None

    def start(self):
        self._t = threading.Thread(target=self._run, daemon=True)
        self._t.start()

    def stop(self):
        self._stop.set()

    def _run(self):
        while not self._stop.wait(self.interval):
            phase = self.phase_fn()
            send_telegram(
                f"⏳ [hersona] 進捗報告\n"
                f"経過: {phase.get('elapsed', '?')}\n"
                f"現在: {phase.get('current', '?')}\n"
                f"残り: {phase.get('remaining', '?')}\n"
                f"更新: {now_jst()}"
            )


# --- メインフロー ---

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--report-now", type=str, default=None,
                    help="任意の進捗を手動で Telegram 送信して終了")
    ap.add_argument("--ticker-interval", type=int, default=REPORT_INTERVAL,
                    help="進捗報告の間隔（秒）、デフォルト 600 = 10分")
    args = ap.parse_args()

    if args.report_now is not None:
        send_telegram(args.report_now)
        return 0

    dry_run = args.dry_run
    apply_mode = args.apply

    if not dry_run and not apply_mode:
        print("ERROR: --dry-run か --apply のどちらかを指定してください。")
        return 2

    mode = "DRY-RUN" if dry_run else "APPLY"
    log(f"=== {mode} 開始 ===")

    # 進捗追跡（ticker から参照）
    started_at = time.time()
    current_phase = "init"

    def phase_state():
        elapsed = int(time.time() - started_at)
        m, s = divmod(elapsed, 60)
        return {
            "elapsed": f"{m}分{s}秒",
            "current": current_phase,
            "remaining": "処理中（フェーズ完了で停止）",
        }

    ticker = ProgressTicker(phase_state, interval=args.ticker_interval)
    if apply_mode:
        ticker.start()
        log(f"進捗 ticker 起動（{args.ticker_interval}秒ごと）")

    send_telegram(
        f"🟡 [hersona] 着手\n"
        f"モード: {mode}\n"
        f"スコープ: 関連リンク削除 + .orig 削除 + .gitignore 追加 + リポ private 化\n"
        f"X: ノータッチ / 出典URL: 保持\n"
        f"開始: {now_jst()}"
    )

    results = []

    # Phase 1: ファイル変更
    log("--- Phase 1: ファイル変更 ---")
    current_phase = "1/4 ファイル変更"
    results.append(("README.md 関連リンク削除", edit_readme(dry_run)))
    results.append(("SKILL.md collector/writer 削除", edit_skill_md(dry_run)))
    results.append((".orig 削除", remove_orig(dry_run)))
    results.append((".gitignore *.orig 追加", add_gitignore(dry_run)))

    # Phase 2: 既存 issue/PR 確認 + クローズ
    log("--- Phase 2: 既存 issue/PR ---")
    current_phase = "2/4 issue/PR 確認"
    open_items = list_open_issues_prs()
    n_issues = len(open_items["issues"])
    n_prs = len(open_items["prs"])
    log(f"open issues: {n_issues}, open prs: {n_prs}")
    if n_issues or n_prs:
        current_phase = f"2/4 issue/PR クローズ中 ({n_issues} issues / {n_prs} prs)"
        results.append((f"issue/PR クローズ ({n_issues} issues / {n_prs} prs)",
                        close_issues_prs(open_items["issues"], open_items["prs"], dry_run)))
    else:
        results.append(("issue/PR クローズ", "対象なし、スキップ"))

    # Phase 3: リポ private 化
    log("--- Phase 3: リポ private 化 ---")
    current_phase = "3/4 gh repo edit private"
    results.append(("gh repo edit --visibility private", make_repo_private(dry_run)))

    # Phase 4: コミット + push（apply のみ）
    if apply_mode:
        log("--- Phase 4: git commit + push ---")
        current_phase = "4/4 git commit + push"
        r = run(["git", "add", "-A"], check=False)
        log(f"git add -A rc={r.returncode}")
        r = run(["git", "status", "--short"], check=False)
        staged = r.stdout.strip()
        if staged:
            log(f"staged:\n{staged}")
            msg = (
                "chore: 関連リンク削除 + クリーンアップ + リポ private 化\n\n"
                "- README.md: 「関連リンク」セクション削除\n"
                "- skills/hersona/SKILL.md: hersona-collector / hersona-writer 言及削除\n"
                "- data/chainsaw-man/power.yaml.orig 削除\n"
                "- .gitignore: *.orig 追加\n"
                "- リポ visibility: public → private\n"
            )
            r = run(["git", "commit", "-m", msg], check=False)
            log(f"git commit rc={r.returncode}\n{r.stdout}\n{r.stderr}")
            r = run(["git", "push", "origin", "main"], check=False)
            log(f"git push rc={r.returncode}\n{r.stdout}\n{r.stderr}")
            results.append(("git commit + push", f"commit rc={r.returncode}, push rc={r.returncode}"))
        else:
            results.append(("git commit + push", "staged なし、スキップ"))

    # ticker 停止
    ticker.stop()
    current_phase = "完了"

    # 結果サマリ
    log("=== 結果サマリ ===")
    for name, detail in results:
        first_line = (detail.splitlines()[0] if detail else "(空)")
        log(f"  - {name}: {first_line[:120]}")

    summary_lines = "\n".join(f"• {n}: {d.splitlines()[0][:100] if d else '(空)'}"
                              for n, d in results)
    send_telegram(
        f"🟢 [hersona] {mode} 完了\n"
        f"```\n{summary_lines}\n```\n"
        f"終了: {now_jst()}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
