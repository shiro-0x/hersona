---
name: hersona
description: "Use when attaching a hersona character profile to the active session's persona via /hersona <title> <character> [mode]. Loads the persona_attach_prompt from data/<title>/<character>.yaml and applies it as the system prompt. Supports three modes: test (session-only), persistent (config.yaml registered), and reset. Also supports /hersona list, /hersona show, /hersona check."
version: 2.0.0
author: Hermes Agent + hersona project
license: MIT
metadata:
  hermes:
    tags: [persona, character, roleplay, attachment, hersona, session-modes]
    related_skills: [hermes-agent, persona-attach]
---

# hersona — Character Persona Attachment

## Overview

hersona（~/projects/hersona）に登録されているアニメ・ゲームキャラ人格を、**現在のセッションのシステムプロンプトに厳格アタッチ**するスキル。

キャラクターになりきった状態で会話・執筆・分析を行い、状況に応じて三つのモード（test / persistent / reset）を使い分ける。

## When to Use

- 「[title] の [character] として話したい」「[character] の口調でレビューして」と頼まれた
- `/hersona [title] [character]` と依頼された
- 既存キャラ人格の一覧を確認したい（`/hersona list`）
- アタッチ中の人格を解除したい（`/hersona default` または `/hersona reset`）
- テキストが指定キャラ人格として成立するか採点したい（`/hersona check <call>`）
- 人格を新しいセッションでも維持したい（persistent モード）
- 永続化した人格を取り消したい（reset モード）

**Don't use for:**
- キャラ人格を一時的にブレンドしたい場合（`scripts/persona_attach.py` の `attach_style: overlay` を別途実装する）
- 新しいキャラを作る場合（`hermes kanban` で `hersona-collector` / `hersona-writer` に投げる）

## Command Syntax

```
/hersona                              # 一覧 + 使い方ヘルプ
/hersona list                         # 利用可能な人格プリセット一覧
/hersona show <call>                  # 指定人格の詳細
/hersona [title] [character] [mode]   # 人格アタッチ
/hersona check <call> --input <file>  # テキストが人格アタッチ条件を満たすか採点
/hersona default                      # リブラ人格に復帰（test モード解除）
/hersona reset                        # persistent モードの全解除
```

`[title]` と `[character]` の組は人格 YAML ファイルの解決に使い、内部的に
`register_call`（`melina` / `toh` 等）に変換される。`data/fate/tohsaka.yaml`
のようにファイル名と `register_call` が一致しないケースでも `toh` 入力で動く。

### CLI からの persistent モード

```bash
# 使い方（v2.1.0 以降）: 第1引数にフラグが来る
./scripts/run_hersona.sh --persist <作品> <キャラ>
```

旧版（v2.0.x）は `./scripts/run_hersona.sh <作品> <キャラ> --persist` 順
だったが、case 文の構造上フラグ先頭しか受け付けない。`--persist` は必ず
先頭に置く。

### Arguments

- `[title]`: 作品ID（例: `elden-ring`、`fate`、`re-zero`、英数字ハイフン区切り）
- `[character]`: キャラID（例: `melina`、スネークケース小文字）
- `[mode]`: 適用モード。**省略可**。詳細は「## Three Modes」参照
  - 省略時: デフォルトは `test`（そのセッションだけ）
  - `test` / `persistent` / `overlay`（将来用）のいずれかを明示可能

## Three Modes

`/hersona [title] [character] [mode]` の `[mode]` で挙動を切り替え。

| モード | 効果 | 永続性 | 解除方法 | 推奨用途 |
|---|---|---|---|---|
| **test**（デフォルト） | アクティブセッションのシステムプロンプトに `attach_prompt` を注入 | そのセッションだけ | `/hersona default` または `/new` | 人格の感触を試す、短期ロールプレイ |
| **persistent** | `~/.hermes/config.yaml` の `agent.personalities.<call>` に登録 | 新規セッションで自動適用 | `/hersona reset` または `scripts/run_hersona.sh --reset` | 普段の作業人格として常用したい |
| **reset** | persistent モードの取り消し | persistent 登録を全削除 | （解除コマンド自体） | 永続人格の撤収、config.yaml クリーンアップ |

### モード詳細

#### test モード

```bash
/hersona <title> <character>
# または明示的に
/hersona <title> <character> test
```

- システムプロンプトに `persona_attach_prompt.attach_prompt` を注入
- `~/.hermes/config.yaml` には**触らない**
- セッション終了で自動的に元に戻る
- **CLI からの実行**: `hermes` 起動後 `/hersona` で適用 → `/new` でリセット

#### persistent モード

```bash
/hersona <title> <character> persistent
# または
./scripts/run_hersona.sh <title> <character> --persist
```

- **実行前に** `~/.hermes/config.yaml` の自動バックアップを作成
  - バックアップ先: `~/.hermes/config_backups/config.yaml.bak.<timestamp>`
- `agent.personalities.<call>` に `attach_prompt` を追記する手順を表示
- ユーザーが config.yaml に**手動で**貼り付け
- 次のセッション開始時からその人格がデフォルトで適用
- **CLI からの実行**: `scripts/run_hersona.sh` を使う方が安全（自動バックアップ込み）

#### reset モード

```bash
/hersona reset
# または
./scripts/run_hersona.sh --reset
```

- persistent モードで登録した人格を config.yaml から全削除
- **実行前に**自動バックアップ（reset 後も config.yaml 自体は保持、編集済みバックアップが `~/.hermes/config_backups/` に残る）
- 削除後、新セッション開始時からリブラ人格（デフォルト）に戻る

## Available Personas (current)

`/hersona list` で実行時に確認できる。データソースは `~/projects/hersona/data/<title>/<character>.yaml` の `persona_attach_prompt` フィールド。

## Workflow

### 1. 人格を test モードで試す

```bash
# セッション中にコマンドを打つ
/hersona <title> <character>

# → システムプロンプトに attach_prompt が注入される
# → 応答がキャラ人格に切り替わる

# 解除
/hersona default
```

### 2. 人格を persistent モードで永続化する

```bash
# CLI 経由（推奨・自動バックアップあり）
cd ~/projects/hersona
./scripts/run_hersona.sh <title> <character> --persist

# → ~/.hermes/config.yaml のバックアップが作成される
# → config.yaml に貼り付けるべき YAML 抜粋が表示される
# → 表示された内容を config.yaml の agent.personalities セクションへ手動で貼り付け
# → 次のセッション開始時から人格がデフォルトで適用される
```

### 3. persistent モードを解除する

```bash
cd ~/projects/hersona
./scripts/run_hersona.sh --reset

# → バックアップが作成される
# → cleaned config が別名で保存される
# → diff で確認後、元の config.yaml と差し替え
```

### 4. テキストが人格アタッチ条件を満たすか採点

```bash
# 採点対象のテキストをファイルに保存
echo "..." > /tmp/test.txt

# 採点実行
/hersona check <call> --input /tmp/test.txt
# または
python3 scripts/persona_attach.py --check <call> --input /tmp/test.txt --repo-root ~/projects/hersona
```

→ 100点満点 + 指摘事項 + 判定（pass/marginal/retry/fail）を表示。

## Common Pitfalls

1. **persistent モードで config.yaml を壊してしまう** — 必ず `scripts/run_hersona.sh --persist` を使うこと。手動編集前は `cp ~/.hermes/config.yaml ~/.hermes/config.yaml.bak.<timestamp>` でバックアップ。

2. **test モードと persistent モードが混在する** — 同じ人格を test モードで使いながら config.yaml に persistent 登録すると、挙動が競合する。**どちらかに統一**すること。

3. **reset モードが反映されない** — `scripts/run_hersona.sh --reset` は cleaned config を別名で保存するのみ。`diff` で確認後、手動で `~/.hermes/config.yaml` と差し替える必要がある。**自動上書きはしない**（安全のため）。

4. **人格アタッチ中にリブラ人格の口調が出てしまう** — 4鉄則違反（`です・ます` / `あなた` 等の混入）。`/hersona show <call>` で forbidden/required を確認、テキストは `scripts/persona_attach.py --check` で採点。

5. **新セッションで人格が適用されない** — persistent モードで config.yaml を更新したのに反映されない場合、config.yaml の YAML 構文エラーが原因の可能性。`python3 -c "import yaml; yaml.safe_load(open('$HOME/.hermes/config.yaml'))"` でパース確認。

6. **persistent モードで登録した人格の強制解除** — セッションを `/new` でリセット、または `~/.hermes/config.yaml` の `agent.personalities.<call>` エントリを削除。

## Verification Checklist

### test モード

- [ ] システムプロンプトの先頭に `attach_prompt` が注入されている
- [ ] セッション状態がキャラ人格に切り替わっている
- [ ] `/hersona default` でリブラ人格に復帰できる

### persistent モード

- [ ] `~/.hermes/config_backups/` に実行前バックアップが作成されている
- [ ] `~/.hermes/config.yaml` の `agent.personalities` に `<call>: |` エントリが追加されている
- [ ] 新規セッション（`/new`）で自動的に人格が適用される
- [ ] `/hersona check` で forbidden/required 違反が0件

### reset モード

- [ ] `~/.hermes/config_backups/` に reset 前バックアップが作成されている
- [ ] cleaned config に `personalities` セクションの人格エントリがコメントアウトされている
- [ ] diff で削除内容を確認できる
- [ ] cleaned config を `~/.hermes/config.yaml` と差し替え後、新セッションでリブラ人格に戻る

## One-Shot Recipes

### 3つのモードを順番に試す

```bash
# 1. test モードで感触を見る
/hermes の新しいセッションを開く
/hersona <title> <character>
# → 数ターン会話
/hersona default

# 2. persistent モードで永続化
cd ~/projects/hersona
./scripts/run_hersona.sh <title> <character> --persist
# → 表示された YAML 抜粋を ~/.hermes/config.yaml に貼り付け
# → セッション再起動

# 3. reset モードで撤収
./scripts/run_hersona.sh --reset
# → diff 確認
# → cleaned config を config.yaml と差し替え
```

### 別キャラを人格アタッチ対応にする

```bash
# 1. セリフ収集（hersona-collector ワーカー）
hermes kanban --board hersona create "<キャラ> セリフ調査" \
  --assignee hersona-collector

# 2. YAML+MD生成（hersona-writer ワーカー）
# → data/<title>/<character>.yaml の persona_attach_prompt を定義

# 3. 検証
cd ~/projects/hersona
python3 scripts/validate.py
python3 scripts/persona_attach.py --list
python3 scripts/persona_attach.py --show <register_call>

# 4. コミット + push
git add data/<title>/<character>.{yaml,md} scripts/run_hersona.sh
git commit -m "feat: <character> persona_attach_prompt 追加"
git push origin main
```

## Reference Files

- スキーマ: `~/projects/hersona/schema/persona_attach.schema.json`
- 人格アタッチ CLI: `~/projects/hersona/scripts/persona_attach.py`
- 永続化スクリプト: `~/projects/hersona/scripts/run_hersona.sh`
- 壊れた personalities 修復: `~/projects/hersona/scripts/fix_persona_block.py <call>`
  （`hermes config set` 経由の書き込みで `agent.personalities.<call>` が
  YAML ブロック記法ごと文字列として壊れた場合に使用）
- 公式 README: `~/projects/hersona/README.md` の「人格アタッチメント」セクション
- hermes-agent-skill-authoring 規約: `~/.hermes/skills/software-development/hermes-agent-skill-authoring/SKILL.md`

## Common Pitfalls（追加）

6. **persistent モード適用後に人格が読み込まれない** — 最も多い原因は
   `hermes config set agent.personalities.<call> "<値>"` 経由の書き込みで、
   値が YAML ブロック記法ごと文字列として格納されるバグ。`fix_persona_block.py
   <call>` で修復可能（`data/<title>/<character>.yaml` の `attach_prompt` を
   真値として config.yaml に書き直す）。
   必ず `./scripts/run_hersona.sh --persist <作品> <キャラ>` 経由を使うこと
   （内部で `fix_persona_block.py` を呼び、壊れない YAML を出力）。

7. **ファイル名と register_call が一致しない** — `data/fate/tohsaka.yaml` の
   `register_call: toh` のように、ファイル名 ≠ 登録名の場合がある。
   `run_hersona.sh` は v2.1.0 以降 glob 検索 + YAML 内 `register_call`
   逆引きで対応。CLI 引数は `<作品> <キャラ>` の `キャラ` 部分に `toh` を
   指定すれば OK。

## Versioning

- **v1.x** (2026-06-05 以前): 単一モードの簡易実装
- **v2.0.0** (2026-06-05): **3 つのモード（test / persistent / reset）に再設計**、CLI スクリプト `run_hersona.sh` 追加、config.yaml 自動バックアップ機構追加
- **v2.1.0** (2026-06-06): **persistent モード YAML 破壊バグ修正** — `fix_persona_block.py` 追加、`run_hersona.sh` の glob 検索 + register_call 逆引き対応

破壊的変更：
- `/hersona` の引数体系に `[mode]` 追加（省略可のため既存ユーザー影響なし）
- 永続化フローが `persona_attach.py --register` から `run_hersona.sh --persist` に変更

