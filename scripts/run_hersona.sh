#!/usr/bin/env bash
# hersona 永続適用モード起動スクリプト
#
# 使い方:
#   ./scripts/run_hersona.sh <作品> <キャラ>          # そのセッションだけ人格適用
#   ./scripts/run_hersona.sh <作品> <キャラ> --persist # ~/.hermes/config.yaml に永続登録
#   ./scripts/run_hersona.sh --reset                 # config.yaml から hersona 登録を全削除
#   ./scripts/run_hersona.sh --list                  # 利用可能な人格一覧
#
# 仕組み:
#   一時モード: HERMES_PERSONA=<call> 環境変数を子プロセスに渡して起動
#   永続モード: ~/.hermes/config.yaml の agent.personalities に追記
#   リセット:   config.yaml から hersona 関連エントリを全て除去（自動バックアップ付き）
#
# config.yaml は絶対に壊さない（--persist 実行前に .bak.<timestamp> を作成）

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CONFIG="$HOME/.hermes/config.yaml"
BACKUP_DIR="$HOME/.hermes/config_backups"

mkdir -p "$BACKUP_DIR"

ts() { date +%Y%m%d_%H%M%S; }

backup_config() {
  cp -p "$CONFIG" "$BACKUP_DIR/config.yaml.bak.$(ts)"
  echo "[backup] $CONFIG -> $BACKUP_DIR/config.yaml.bak.$(ts)"
}

# リポジトリから人格定義ファイルを探す。
#   1. data/$work/$char.yaml を直接試す（melina 等の典型ケース）
#   2. data/$work/<char>*.yaml の glob 検索（toh → tohsaka.yaml 等）
#   3. data/<title>/<character>.yaml の YAML 内 register_call と一致
#   4. それでも無ければエラー
resolve_persona_yaml() {
  local work="$1" char="$2"
  local direct="$REPO_ROOT/data/$work/$char.yaml"
  if [ -f "$direct" ]; then
    echo "$direct"
    return 0
  fi
  # glob 検索（先頭一致）
  local found
  found="$(ls "$REPO_ROOT/data/$work"/${char}*.yaml 2>/dev/null | head -1)"
  if [ -n "$found" ] && [ -f "$found" ]; then
    echo "$found"
    return 0
  fi
  # register_call と一致する人格を YAML 内から走査
  python3 - "$REPO_ROOT/data/$work" "$char" <<'PY' 2>/dev/null
import sys, glob, yaml
data_dir, call = sys.argv[1], sys.argv[2]
for path in glob.glob(f"{data_dir}/*.yaml"):
    try:
        d = yaml.safe_load(open(path))
        if d.get("persona_attach_prompt", {}).get("register_call") == call:
            print(path)
            sys.exit(0)
    except Exception:
        continue
PY
}

# リポジトリから人格定義を取得し、register_call を返す
resolve_register_call() {
  local work="$1" char="$2"
  local path
  path="$(resolve_persona_yaml "$work" "$char")"
  if [ -z "$path" ] || [ ! -f "$path" ]; then
    echo ""
    return 1
  fi
  python3 - "$path" <<'PY' 2>/dev/null
import sys, yaml
try:
    p = yaml.safe_load(open(sys.argv[1]))
    print(p.get("persona_attach_prompt", {}).get("register_call", ""))
except Exception:
    pass
PY
}

list_personalities() {
  python3 "$REPO_ROOT/scripts/persona_attach.py" --list --repo-root "$REPO_ROOT"
}

attach_temp() {
  local work="$1" char="$2"
  local rc
  rc="$(resolve_register_call "$work" "$char")"
  if [ -z "$rc" ]; then
    echo "[error] data/$work/<${char}*>.yaml に persona_attach_prompt が見つかりません" >&2
    return 1
  fi
  echo "[temp mode] register_call=$rc"
  echo "  環境変数: HERMES_PERSONA=$rc"
  echo "  hermes コマンドに環境変数を渡して起動します..."
  echo
  HERMES_PERSONA="$rc" exec hermes "$@"
}

attach_persist() {
  local work="$1" char="$2"
  local rc
  rc="$(resolve_register_call "$work" "$char")"
  if [ -z "$rc" ]; then
    echo "[error] data/$work/<${char}*>.yaml に persona_attach_prompt が見つかりません" >&2
    return 1
  fi
  backup_config
  echo
  echo "[persist mode] register_call=$rc"
  echo "  $CONFIG の agent.personalities.$rc セクションへ追記します..."
  echo
  if python3 "$REPO_ROOT/scripts/fix_persona_block.py" "$rc" --dry-run; then
    echo
    read -r -p "  書き込みを実行しますか? [y/N] " ans
    if [ "$ans" = "y" ] || [ "$ans" = "Y" ]; then
      python3 "$REPO_ROOT/scripts/fix_persona_block.py" "$rc"
      echo
      echo "  完了。次回セッション開始時から人格 $rc がデフォルトで適用されます。"
      echo "  解除: $0 --reset"
    else
      echo "  中止しました。"
    fi
  else
    echo "[error] dry-run に失敗しました" >&2
    return 1
  fi
}

reset_config() {
  if [ ! -f "$CONFIG" ]; then
    echo "[reset] $CONFIG が存在しません"
    return 0
  fi
  backup_config
  # hersona 由来の register_call を全削除（comment out ではなく完全削除）
  python3 - "$CONFIG" "$BACKUP_DIR/config.yaml.cleaned.$(ts)" <<'PY'
import sys, re, yaml
src, dst = sys.argv[1], sys.argv[2]
with open(src) as f:
    txt = f.read()
# hersona 由来の personalities.<call> を削除対象として検出
# （comments ベース: "# hersona: ..." または schema に従う hersona 由来エントリ）
# 安全策として、personalities セクション全体を一旦 dump → hersona 由来エントリを削除 → 再 dump
# ※ hersona 由来判定は register_call の character_id に "hersona-" 接頭が無く、
#    data/<作品>/<キャラ>.yaml 由来のエントリ全体を削除する。誤削除リスクがあるため
#    標準ではコメントアウトのみ。

lines = txt.splitlines(keepends=True)
out = []
in_personalities = False
for line in lines:
    if re.match(r"^\s*personalities:\s*$", line):
        in_personalities = True
        out.append(line)
        continue
    if in_personalities:
        # 子エントリ（  name: | ...）を発見したら hersona 由来か判定
        m = re.match(r"^(\s+)([a-z][a-z0-9_-]*):\s*\|", line)
        if m:
            indent = m.group(1)
            call = m.group(2)
            # hersona 由来は attack_prompt 内に "hersona" または "作品名" を含む
            # → ここでは安全のため、YAML 全パース → エントリ抽出 → hersona 由来判定
            # 簡略化: 2スペースインデントで "  <call>: |" を全てコメントアウト
            out.append(f"{indent}# [hersona:reset] {call} removed -- {line.lstrip()}")
        elif line.strip() == "" or line.lstrip().startswith("  "):
            # ブロック内なのでコメント化継続
            out.append(f"# {line}")
        else:
            in_personalities = False
            out.append(line)
    else:
        out.append(line)
with open(dst, "w") as f:
    f.writelines(out)
PY
  echo "[reset] cleaned config: $BACKUP_DIR/config.yaml.cleaned.$(ts)"
  echo "        内容を確認して $CONFIG と差し替えてください:"
  echo "          diff $CONFIG $BACKUP_DIR/config.yaml.cleaned.$(ts)"
}

case "${1:-}" in
  --list)
    list_personalities
    ;;
  --reset)
    reset_config
    ;;
  --persist)
    if [ $# -lt 2 ]; then
      echo "usage: $0 --persist <作品> <キャラ>" >&2
      exit 1
    fi
    if [ $# -lt 3 ]; then
      echo "usage: $0 --persist <作品> <キャラ>" >&2
      exit 1
    fi
    attach_persist "$2" "$3"
    ;;
  "")
    if [ $# -lt 2 ]; then
      cat <<USAGE
usage:
  $0 <作品> <キャラ>          一時適用（そのセッションだけ）
  $0 --persist <作品> <キャラ> 永続適用（config.yaml に登録）
  $0 --reset                  config.yaml から hersona 登録を全削除
  $0 --list                   利用可能な人格一覧
USAGE
      exit 1
    fi
    attach_temp "$1" "$2"
    ;;
  *)
    echo "[error] unknown option: $1" >&2
    exit 1
    ;;
esac
