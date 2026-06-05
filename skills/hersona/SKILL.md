---
name: hersona
description: "Use when attaching a hersona character profile to the active session's persona via /hersona <作品> <キャラ> [設定]. Loads the YAML/MD profile from ~/projects/hersona/data/<作品>/<キャラ>.{yaml,md} and applies its persona_attach_prompt as the system prompt. Supports /hersona list, /hersona show, /hersona check <call>, /hersona default (detach)."
version: 1.0.0
author: Hermes Agent + hersona project
license: MIT
metadata:
  hermes:
    tags: [persona, character, roleplay, attachment, hersona, elden-ring]
    related_skills: [hermes-agent, persona-attach]
---

# hersona — Character Persona Attachment

## Overview

hersona（~/projects/hersona）に登録されているアニメ・ゲームキャラ人格を、**現在のセッションのシステムプロンプトに厳格アタッチ**するスキル。
メリーナ（エルデンリング）を最初の実装例とし、同じ構造で他キャラにも展開可能。

キャラクターになりきった状態で会話・執筆・分析を行い、`/hersona default` でリブラ人格に完全復帰する。

## When to Use

- 「メリーナとして話したい」「メリーナの口調でレビューして」と頼まれた
- 「hersona メリーナ 設定して」「/hersona エルデンリング メリナ」と依頼された
- 既存キャラ人格の一覧を確認したい（`/hersona list`）
- アタッチ中の人格を解除したい（`/hersona default`）
- テキストが指定キャラ人格として成立するか採点したい（`/hersona check <call>`）

**Don't use for:**
- キャラ人格を一時的にブレンドしたい場合（`scripts/persona_attach.py` の `attach_style: overlay` を別途実装する）
- 新しいキャラを作る場合（`hermes kanban` で `hersona-collector` / `hersona-writer` に投げる）

## Command Syntax

```
/hersona                              # 一覧 + 使い方ヘルプ
/hersona list                         # 利用可能な人格プリセット一覧
/hersona show <call>                  # 指定人格の詳細（attach_prompt, forbidden/required 等）
/hersona <作品> <キャラ> [設定]       # 人格アタッチ（厳格適用・完全置換）
/hersona check <call> --input <file>  # テキストが人格アタッチ条件を満たすか採点
/hersona default                      # リブラ人格に復帰
```

### Arguments

- `<作品>`: `elden-ring` / `fate` / `re-zero` 等の英数字ハイフン区切り
- `<キャラ>`: `melina` / `melina` 等のキャラ名（スネークケース）
- `[設定]`: 任意の追加指示（`strict` / `overlay` / `口調ゆるめ` 等）。省略時は `strict`（厳格適用）

## Workflow

### 1. `/hersona` 単体実行（ヘルプ）

```
/hersona
```

→ 利用可能な人格プリセット一覧 + 使い方を表示。

### 2. `/hersona <作品> <キャラ>` で人格アタッチ

```
/hersona elden-ring melina
```

実行内容：
1. `~/projects/hersona/data/elden-ring/melina.yaml` を読み込む
2. `persona_attach_prompt` フィールドを抽出
3. システムプロンプトの先頭に `attach_prompt` を注入
4. セッション状態を `persona=melina` に切り替え
5. リブラ人格ペルソナ（`~/.hermes/config.yaml` の `persona`）を一時退避
6. 以下の通知を返す：

```
人格アタッチ完了: メリーナ (elden-ring-melina) v1.0
スタイル: strict
強度: 8/10
解除: /hersona default

・・・貴方。今より私はメリーナとして振る舞います。
...
```

### 3. `/hersona show <call>` で詳細確認

```
/hersona show melina
```

→ `scripts/persona_attach.py --show melina` の出力を表示。

### 4. `/hersona check` でテキスト採点

```
echo "・・・貴方。おはようございます" > /tmp/test.txt
/hersona check melina --input /tmp/test.txt
```

→ 100点満点 + 指摘事項 + 判定（pass/marginal/retry/fail）を表示。

### 5. `/hersona default` でリブラ人格に復帰

```
/hersona default
```

→ 退避していたリブラ人格ペルソナを復元、メリーナ人格プロンプトを除去。

## Available Personas (hersona v1.0)

| register_call | name | source | intensity | style | 解除 |
|---|---|---|---|---|---|
| `melina` | メリーナ | エルデンリング | 8 | strict | `/hersona default` |

## Common Pitfalls

1. **人格アタッチ中にリブラ人格の口調が出てしまう** — 4鉄則違反（`です・ます` / `あなた` 等の混入）。`/hersona show melina` で forbidden/required を確認、テキストは `scripts/persona_attach.py --check` で採点。

2. **アタッチ解除が反映されない** — `/hersona default` の後に `/new` で新セッションを開始するのが確実。同一セッション内ではバックエンドの実装によっては完全リセットされないことがある。

3. **`persona_attach_prompt` 未定義のキャラを指定** — `scripts/validate.py` 警告が出る。先に `hermes kanban --board hersona create` で該当キャラの制作タスクを起票。

4. **メリーナ人格の強制解除が必要** — セッションを `/new` でリセット、または `~/.hermes/config.yaml` の `agent.personalities.melina` エントリを削除。

5. **人格間の会話テスト** — `scripts/melina_cli.py` / `scripts/reviewer_cli.py` を使うと、独立プロセスでメリーナ人格との対話と精度検証ができる。リブラ人格には影響しない。

## Verification Checklist

人格アタッチ直後に以下を確認：

- [ ] システムプロンプトの先頭にメリーナの `attach_prompt` が注入されている
- [ ] セッション状態が `persona=melina` になっている
- [ ] リブラ人格ペルソナが退避されている（`/hersona default` で復元できる状態）
- [ ] 解除コマンド `/hersona default` が応答する
- [ ] メリーナ人格の応答で 4鉄則（私/貴方/～の・～わ/・・・）が守られている

## One-Shot Recipes

### メリーナ人格で会話テスト

```bash
# 1. 利用可能な人格を確認
/hersona list

# 2. メリーナ人格に切り替え
/hersona elden-ring melina

# 3. メリーナ人格と会話（セッション内）
# ・・・貴方。おはようございます。

# 4. 解除
/hersona default
```

### CLI で独立テスト（人格アタッチとは別プロセス）

```bash
# メリーナ人格CLIを起動
cd ~/projects/hersona
python3 scripts/melina_cli.py

# 別ターミナルでレビュアーCLIを起動し、メリーナの応答をスコアリング
python3 scripts/reviewer_cli.py --input data/elden-ring/validation_report.md

# 自動10問検証
python3 scripts/persona_validate.py
```

### 新しいキャラを人格アタッチ対応にする

```bash
# 1. YAML に persona_attach_prompt フィールドを追加（schema 準拠）
# 2. MD に人格アタッチメントセクションを追加
# 3. 検証
cd ~/projects/hersona
python3 scripts/validate.py
python3 scripts/persona_attach.py --list
python3 scripts/persona_attach.py --show <register_call>
# 4. コミット + push
git add data/<作品>/<キャラ>.{yaml,md} schema/persona_attach.schema.json scripts/persona_attach.py
git commit -m "feat: <キャラ> persona_attach_prompt 追加"
git push origin main
```

## Reference Files

- スキーマ: `~/projects/hersona/schema/persona_attach.schema.json`
- CLI: `~/projects/hersona/scripts/persona_attach.py`
- メリーナ人格のソース: `~/projects/hersona/data/elden-ring/melina.yaml` の `persona_attach_prompt` フィールド
- 公式 README: `~/projects/hersona/README.md` の「人格アタッチメント」セクション
- hermes-agent-skill-authoring 規約: `~/.hermes/skills/software-development/hermes-agent-skill-authoring/SKILL.md`
