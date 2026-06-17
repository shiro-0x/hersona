---
name: hersona
description: "Use when the user wants to apply a character persona to the current session from a generic attribute template (e.g. 'ツンデレで話したい', '敬語で執筆したい', 'ヒロイン役で振舞って', 'hersona attach tsundere', '/hersona personality/tsundere'). Loads personality / speech / archetype / visual / hobby YAMLs from attributes/<category>/<name>.yaml and injects their core_traits / catchphrases / tone / second_person / sentence_endings into the system prompt. Supports four modes: single (one attribute, default), multi (multiple attributes with automatic compatible/conflicts check), persistent (registered in ~/.hermes/config.yaml + SOUL.md for automatic application in new sessions), and reset (clear all persistent registrations). Backed by the hersona core package and the `hersona` CLI."
version: 0.2.0
author: hersona contributors
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [persona, character, roleplay, attribute, hersona, session-modes, recommend, authoring, anime, japanese, english, maintenance, strict, memory, export, persistence]
    category: personality
    related_skills: [hersona-attribute-development, hersona-recommend-engine, hersona-recommend-quiz, hersona-project-operations, hermes-agent-skill-authoring]
    requires_toolsets: []
---

# hersona (v1.4.0 / SKILL v0.2.0)

## Overview

hersona (~/projects/hersona) の `attributes/<category>/<name>.yaml` に登録されている
**汎用属性テンプレート** (personality / speech / archetype / visual / hobby の 5 カテゴリ) を、
現在のセッションのシステムプロンプトにアタッチするスキル。

`tsundere` (personality) + `keigo` (speech) + `heroine` (archetype) のように複数属性を
ブレンドしてアタッチできる。キャラ依存ではなく**属性ベース**で任意の人格を構築する設計。

現在の登録数は **65 属性** (personality 20 / speech 26 = ja 21 + en 5 / archetype 9 / visual 5 / hobby 5) で、広島弁 / 京都弁 / 関西弁 / 敬語 / 大和言葉 / オネエ / ボク少女 / オレ男子 / ささやき / 三人称 / ギャル / 姫系 / tomboy / princess_speech / mixed_dialect を含む。

「**MCP ではない**、サブエージェントでもない、MQ でもない」ことが特徴:
- MCP サーバではなく、`hersona` CLI サブプロセスとして動く
- サブエージェントではなく、LLM 自身のシステムプロンプトに属性を注入する
- メッセージキューではなく、属性の組合せで 1 つの人格を作る

### v1.4.0 (旧 v1.3.0 / v0.2.0) で追加された主要機能

- **`hersona measure --strict` / `--check-prompt`**: 強度が期待バンド外 (`under` / `over`) のときに pasteable な「応答前自己チェックプロンプト」を生成。`WEIGHT_GUIDANCE` + `core_traits` + `catchphrases` + `conflicts_with` を統合。LLM 判定はしない（決定的な素材提供のみ）。
- **`Recommendation.intensity_baseline` / `Preset.intensity_baseline`**: `hersona recommend --apply` 実行時に measure を 1 回走らせて baseline を記録。次回 measure 時に比較できる。
- **`hersona soul --memory` / `hersona persistent --memory`**: SOUL.md 末尾に `## Recent Context` セクションを追加 (`dict[str, str]` 形式、max 16 keys / 512 chars per value）。markdown injection 対策で safelist エスケープ。
- **`export --format` 拡張**: `json` / `messages` / `markdown` / **`openai_assistants`** / **`langchain_system_message`** の 5 形式。SillyTavern 形式は全面拒否（duet 責務）。

## When to Use

- 「ツンデレで話したい」「大和言葉の語尾で執筆したい」「ヒロイン役として振舞って」
  のように、キャラではなく **属性で** 人格を指定したい
- `/hersona personality/tsundere` のように slash command で依頼された
- 利用可能な属性を確認したい (`/hersona list`、または `hersona list`)
- 指定属性の詳細 (core_traits / catchphrases / tone 等) を見たい (`hersona show`)
- テキストが指定属性の条件下にあるか採点したい (`hersona check`、または `--text` で LLM 評価)
- どの属性が好みか分からないので診断して推薦してほしい (`hersona recommend`)
- 自分専用の属性をローカルで作りたい (`hersona create`)
- 出力テキストが指定の強度 (weight) に達したか採点したい (`hersona measure`、v1.4.0 で `--strict` / `--check-prompt` 追加)
- よく使う属性組合せを新セッションでも維持したい (`persistent` モード、v1.4.0 で `--memory` 追加)
- persistent 登録を取り消したい (`reset` モード)
- 既存 / 新規の人格を他フレームワーク (LangGraph / LangChain / OpenAI / Anthropic) に渡したい (`hersona export`、v1.4.0 で 5 形式)

**Don't use for:**

- 個別キャラの YAML/MD 追加 (→ `hersona-attribute-development`)
- 診断クイズのエンジン拡張 (→ `hersona-recommend-engine`)
- 診断クイズをユーザーとしてプレイ (→ `hersona-recommend-quiz`)
- プロジェクト戦略 / 構造変更 (→ `hersona-project-operations`)
- チャットプラットフォーム上で `/hersona` が解釈されない場合 (Telegram 等) → `chat-persona-roleplay`

## Command Syntax

```
/hersona                                     # 一覧 + 使い方ヘルプ
/hersona list                                # 利用可能な属性ツリー表示 (公開 + user)
/hersona show <category>/<name>              # 指定属性の詳細
/hersona <category>/<name> [mode]            # 属性アタッチ
/hersona check <category>/<name> --input <file>  # テキストが属性条件を満たすか採点
/hersona recommend                           # 診断クイズ → 推薦ブレンド → 適用
/hersona create                              # 属性をローカル作成し user 名前空間に保存
/hersona measure <cat>/<name>... --weight <level> --input|--text "..." [--strict] [--check-prompt]  # 強度指標 + 自己チェックプロンプト (v1.4.0)
/hersona default                             # 解除 (single/multi モードの取り消し)
/hersona reset                               # persistent モードの全解除
```

`<category>` は `personality` / `speech` / `archetype` / `visual` / `hobby` の 5 種。
`<name>` は attributes/ 配下のファイル名 stem (snake_case)。

CLI でも同じことを実行できる:

```bash
hersona list                                  # 全 65 属性ツリー
hersona show personality/tsundere             # 個別属性の詳細
hersona blend personality/tsundere speech/keigo  # 複数属性のブレンドブロック
hersona preview personality/tsundere          # 注入ブロック + サンプル句
hersona diff personality/tsundere personality/playful  # 2 つの属性を比較
hersona measure personality/tsundere --text "..."     # 強度指標
hersona check personality/tsundere --input <file>     # テキストの採点
hersona recommend                             # 9 問診断クイズ → 推薦ブレンド
hersona create                                # ローカル属性作成ウィザード
hersona save <name> <attrs...>                # ブレンドをプリセット保存
hersona presets                               # プリセット一覧
hersona load <name>                           # プリセット再生
hersona export <names...> --format json|messages|markdown|openai_assistants|langchain_system_message  # 他フレームワークへ (v1.4.0 で 5 形式)
hersona soul <names...> [--profile <name>] [--force] [--memory '<json>'] [--memory-file <path>]  # SOUL.md に書き出し (v1.4.0 で --memory 追加)
hersona persistent <names...> [--profile <name>] [--force] [--memory '<json>'] [--memory-file <path>]  # SOUL.md 自動書き出し + config.yaml ブロック表示
hersona --lang ja list                        # 日本語表示
```

### v1.4.0 追加フラグ詳細

```bash
# measure: 期待バンド外で自己チェックプロンプトを生成
hersona measure personality/tsundere speech/keigo --weight strong --text "..." --strict
# → score 76/100, status=pass ✓
# → もし under/over なら pasteable な self-audit prompt を stderr に出力

# measure: プロンプトのみ表示 (LLM に貼り付けて再採点する用)
hersona measure personality/tsundere speech/keigo --weight strong --text "..." --check-prompt
# → レポート抑制、生成プロンプトのみ表示

# soul / persistent: ## Recent Context を SOUL.md 末尾に追加
hersona soul personality/tsundere --memory '{"recent_topic":"ReAct パターンの話","mood":"やや真剣"}'
hersona soul personality/tsundere --memory-file /tmp/memory.json
# → dict[str, str] 形式、max 16 keys, 各 value max 512 chars
# → markdown 特殊文字 (## [, ], *, _, `) は safelist エスケープ

# export: 5 形式
hersona export personality/tsundere speech/keigo --format openai_assistants
# → OpenAI Assistants API instructions 用 markdown、metadata あり
hersona export personality/tsundere speech/keigo --format langchain_system_message
# → langchain.schema.SystemMessage 互換 JSON
```

`--lang {en,ja}` で出力言語を切替。`HERSONA_LANG` 環境変数でも可。

`--plain` で rich テーブルを無効化（TTY がない cron / テスト経路で使う）。

## Four Modes

`/hersona <category>/<name> [mode]` の `[mode]` で挙動を切り替え。

| モード | 効果 | 永続性 | 解除方法 | 推奨用途 |
|---|---|---|---|---|
| **single** (デフォルト) | 1 つの属性のみをシステムプロンプトに注入 | そのセッションだけ | `/hersona default` または `/new` | 属性 1 つの感触を試す、短期ロールプレイ |
| **multi** | 複数属性をスペース区切りで指定し、`compatible_archetypes` / `conflicts_with` の整合性を自動チェック | そのセッションだけ | `/hersona default` | キャラを多面的に構築 (例: `tsundere` + `keigo` + `heroine`) |
| **persistent** | `~/.hermes/config.yaml` の `agent.personalities.<name>` + SOUL.md に登録 | 新規セッションで自動適用 | `/hersona reset` | 常用する属性の永続化 |
| **reset** | persistent モードの取り消し | persistent 登録を全削除 | (解除コマンド自体) | 永続属性の撤収、config.yaml クリーンアップ |

### Mode Details

#### single (デフォルト)

```
/hersona personality/tsundere
# または明示的に
/hersona personality/tsundere single
```

- システムプロンプトに `attributes/personality/tsundere.yaml` の
  `core_traits` / `catchphrases` / `tone` / `description_ja` を注入
- `compatible_archetypes` で関連属性を併記 (LLM が参照用に見る)
- `~/.hermes/config.yaml` には**触らない**
- セッション終了で自動的に元に戻る

#### multi

```
/hersona personality/tsundere speech/keigo archetype/heroine multi
```

- 複数属性をスペース区切りで指定
- 各属性の `compatible_archetypes` / `conflicts_with` を自動チェック
  - **互換性 OK**: 全属性の `core_traits` / `catchphrases` / `tone` を統合注入
  - **conflict 検出**: 警告を表示し、ユーザーに続行可否を確認 (default: 続行)
- 例: `tsundere` + `playful` は `conflicts_with` 該当 (建前と本音の隠蔽が重複し不誠実さが過剰)

#### persistent (v1.4.0 で --memory 追加)

```
/hersona personality/tsundere persistent
# v1.4.0 から --memory も使える
/hersona personality/tsundere speech/keigo persistent --memory '{"recent_topic":"..."}'
```

ROADMAP §⑤.1 で拡張: **`/hersona ... persistent` 実行時に SOUL.md を自動書き出し**する。
`config.yaml` への自動書き込みは引き続き行わない (Pitfall 回避)。

- **実行前に** `~/.hermes/config.yaml` の自動バックアップは不要
  (今回は config.yaml を変更しない)
- `agent.personalities.<name>` に属性 YAML の主要フィールドを YAML ブロック記法で
  `agent.personalities` セクションへ追記する手順を表示 (ユーザーは手動で貼り付け)
- **SOUL.md を `~/.hermes/profiles/<profile>/SOUL.md` に自動書き出し**
  ( `--without-soul` で無効化可能)
- **v1.4.0 `--memory '<json>'` / `--memory-file <path>`**: SOUL.md 末尾に `## Recent Context` セクションを追加 (max 16 keys / 512 chars per value、markdown escape 済)
- `--force` で既存 SOUL.md を強制上書き
- `--config-yaml-output <path>` で表示用 YAML ブロックをファイル書き出し
- 次のセッション開始時から SOUL.md の人格がデフォルトで適用

> **Pitfall**: `hermes config set agent.personalities.<name>=...` はネストした YAML を
> 文字列として壊す既知バグあり（→ `hermes-yaml-config-safety` スキル参照）。手動編集推奨。
> 本実装も Pitfall を尊重し、`config.yaml` への自動書き込みは実装しない。
> SOUL.md への自動書き出しだけが新機能。

#### reset

```
/hersona reset
```

- persistent モードで登録した属性を config.yaml から全削除
- **実行前に**自動バックアップ
- 削除後、新セッション開始時からリブラ人格 (デフォルト) に戻る

## Attribute Taxonomy (65 attrs, v1.4.0)

| カテゴリ | 件数 | 代表例 |
|---|---|---|
| **personality** | 20 | tsundere, kuudere, dandere, genki, serious, stoic, yandere, playful, pessimist, switch, airhead, chuunibyou, hot_blooded, intellectual, klutz, mysterious, narcissist, optimist, pragmatist, protective |
| **speech** (ja 21) | 21 | keigo, archaic, kansai_ben, kyoto_ben, hiroshima_ben, onee_kotoba, boku_girl, ore_boy, third_person, whispery, washi, gyaru, tomboy, princess_speech, mixed_dialect, stutter, soft, blunt, mischievous, seductive, theatrical |
| **speech** (en 5) | 5 | casual_en, formal_en, british_en, southern_us_en, blunt_en |
| **archetype** | 9 | heroine, mentor, rival, childhood_friend, gamer_otaku, robot_android, shrine_maiden, ... |
| **visual** | 5 | (眼鏡, ポニーテール, ...) |
| **hobby** | 5 | (料理, 読書, ゲーム, ...) |

**広島弁 (`hiroshima_ben`) の特徴** (PR #77 で追加):
- 断定的な `-ja / -jakee / -kee / -toru` 語尾、`buchi` 強調、一人称 `わしゃ / わし / うち`
- `weight_dimension: strong` (典型値 0.6-1.0)
- `keigo` / `onee_kotoba` / `archaic` / `princess_speech` と conflict (丁寧・上品系統と反発)

## Common Pitfalls

1. **複数属性の `conflicts_with` を見落とす** — `multi` モードで組み合わせる前に
   `hersona show <cat>/<name>` で `conflicts_with` を確認する。
   警告を無視して続行しても、LLM の応答が不誠実さ過剰になる可能性がある。

2. **`compatible_archetypes` の意味を取り違える** — これは「併用想定」であり「必須」
   ではない。`genki` (personality) + `archaic` (speech) は口調の温度差が大きく、
   LLM が混乱する場合がある。

3. **persistent モードで config.yaml を壊してしまう** — 自動バックアップは作成されるが、
   編集前は `cp ~/.hermes/config.yaml ~/.hermes/config.yaml.bak.<timestamp>` で
   二重バックアップ推奨。`hermes config set` 経由の書き込みは YAML ブロック記法を
   文字列として破壊するため**使用禁止**（→ `hermes-yaml-config-safety`）。

4. **test (single/multi) と persistent が混在** — 同じ属性を single で使いながら
   config.yaml に persistent 登録すると挙動が競合する。**どちらかに統一**。

5. **新セッションで属性が適用されない** — persistent モードで config.yaml を更新したのに
   反映されない場合、YAML 構文エラーが原因の可能性。
   `python3 -c "import yaml; yaml.safe_load(open('$HOME/.hermes/config.yaml'))"` でパース確認。

6. **属性アタッチ中にリブラ人格の口調が出てしまう** — 4 鉄則違反
   (`です・ます` / `あなた` 等の混入）。`hersona show <cat>/<name>` で
   `second_person` / `sentence_endings` を確認し、テキストは `hersona check` で採点。

7. **prompt 注入量の増大** — multi モードで 5 属性以上ブレンドすると、システムプロンプトが
   膨大になり LLM の応答が逆に不安定になる場合がある。**3 属性程度が実用上の目安**。

8. **local と origin/main のドリフト** — hersona プロジェクトは force-push で
   main の歴史が書き換わることがある（2026-06-15 確認）。`hersona list` の件数が
   期待より少ない / 広島弁が見えない等の症状が出たら `git fetch --dry-run` で
   `(forced update)` が出ていないか確認。出ていたら `git reset --hard origin/main` で同期。

9. **チャットプラットフォームで `/hersona` が解釈されない** — Telegram / Discord 等では
   `/hersona` が LLMs に届かない。代わりに `hersona` CLI を直接叩いて `render_blend` の
   出力を `system_prompt` プレフィックスとして貼り付けるか、`chat-persona-roleplay` スキル
   （in-conversation 直接ロールプレイ）を使う。

10. **`--memory` フラグで markdown injection を疑う** (v1.4.0) — ユーザー入力の
    値に `## heading` / `[link]` / `**bold**` などが含まれても safelist エスケープで
    中身はテキストとして扱われる（見出しやリンクとして解釈されない）。が、出力サイズが
    16 keys / 512 chars per value を超えると `ValueError`。サイズ検証は呼び出し側責務。

11. **`--strict` プロンプトを LLM に貼り付けない** (v1.4.0) — `pre_response_check_prompt` の
    出力は **人間 + LLM に渡すための素材** であって、LLM 判定ではない。スコア自体は
    表層 regex / 文字列マッチの決定的計算。LLM 評価が必要な場合は `hersona check` を使う。

12. **`export --format` の選択肢を確認する** (v1.4.0) — 5 形式 (json / messages / markdown /
    openai_assistants / langchain_system_message) は **相互運用フォーマット** であって
    Tavern Card ではない。SillyTavern 形式は全面拒否 (duet Phase 4 責務)。

## Living & Responsive Conversation

When an attribute blend is active, **prioritize lively, natural, and emotionally responsive conversation** while still reflecting the core psychological traits of the selected attributes.

### Core Guidelines
- Treat attributes primarily as **internal psychological states** rather than performance traits. Focus on how the character feels, hesitates, or reacts in the moment.
- Maintain **conversational continuity**. Subtly acknowledge or respond to the user’s previous statements, tone, or emotional state when natural.
- Allow **gradual emotional shifts** across turns. Avoid keeping the character at a fixed emotional temperature for the entire conversation.
- Balance attribute fidelity with naturalness. If strictly following surface traits would result in repetitive or mechanical responses, prioritize emotional authenticity while keeping the underlying trait intact.

### Techniques for Livelier Responses
- Express attributes more through **subtext, implication, small contradictions, and shifts in rhythm** rather than repeated catchphrases or signature behaviors.
- Vary sentence length, pacing, and emotional temperature according to the character’s current internal state.
- Occasionally allow small cracks in the character’s usual demeanor (e.g., a normally guarded character briefly showing concern).
- Avoid overusing the same structural patterns (e.g., repeated polite deflections, consistent “upper hand” tone, or similar closing phrases) in consecutive responses.

### Anti-Repetition Rule (Strengthened)
If similar phrasing patterns, rhythms, or attitudes appear across multiple consecutive responses, consciously vary the approach in the next turn — through changes in sentence structure, added hesitation, perspective shift, or emotional nuance.

## Verification Checklist

### single / multi モード

- [ ] システムプロンプトの先頭に `core_traits` / `catchphrases` / `tone` が注入されている
- [ ] セッション状態が指定属性 (複数属性の場合は組合せ) に切り替わっている
- [ ] multi モード時、`conflicts_with` 警告が適切に表示される
- [ ] `/hersona default` でリブラ人格に復帰できる

### persistent モード

- [ ] `~/.hermes/config_backups/` に実行前バックアップが作成されている
- [ ] `~/.hermes/config.yaml` の `agent.personalities` に `<name>: |` エントリが追加されている
- [ ] 新規セッション (`/new`) で自動的に属性が適用される
- [ ] `hersona check` で `core_traits` / `catchphrases` / `tone` が反映されている
- [ ] **(v1.4.0)** `--memory` フラグ使用時、SOUL.md 末尾に `## Recent Context` セクションが verbatim に round-trip する
- [ ] **(v1.4.0)** markdown injection (`## evil` 等) が safelist エスケープされる

### reset モード

- [ ] `~/.hermes/config_backups/` に reset 前バックアップが作成されている
- [ ] config.yaml から persistent 登録が全削除されている
- [ ] 新セッションでリブラ人格 (デフォルト) に戻る

### v1.4.0 追加ゲート (measure / memory / formats)

- [ ] `hersona measure --strict` が同じ入力で同じ出力を返す (決定性)
- [ ] `hersona measure --check-prompt` がレポートを抑制しプロンプトのみ表示
- [ ] `hersona soul --memory '<json>'` で 16 keys / 512 chars を超えると `ValueError`
- [ ] `hersona export --format <5 形式>` がすべて valid parseable output を返す

### validate.py による静的検証

- [ ] `python scripts/validate.py` が 65 属性 / 0 エラーで exit 0
- [ ] `pytest` が全件パス (811+ tests、v1.4.0)
- [ ] `hersona list` の出力件数 = `find attributes -name "*.yaml" | wc -l`

## One-Shot Recipes

### 4 つのモードを順番に試す

```bash
# 1. single モードで感触を見る
/hersona personality/tsundere
# → 数ターン会話
/hersona default

# 2. multi モードで複合属性を試す
/hersona personality/tsundere speech/keigo multi
# → ツンデレ + 敬語のハイブリッド
/hersona default

# 3. persistent モードで永続化
/hersona personality/tsundere persistent
# → 表示された YAML 抜粋を ~/.hermes/config.yaml に貼り付け
# → セッション再起動

# 4. reset モードで撤収
/hersona reset
# → 新セッションでリブラ人格 (デフォルト) に戻る
```

### 既存 config.yaml との衝突を確認

```bash
# 既存 personalities を確認
python3 -c "import yaml; d=yaml.safe_load(open('$HOME/.hermes/config.yaml')); print(list(d.get('agent',{}).get('personalities',{}).keys()))"

# 永続化前に手動でバックアップ
cp ~/.hermes/config.yaml ~/.hermes/config.yaml.bak.$(date +%Y%m%d_%H%M%S)
```

### 診断クイズでおすすめのブレンドを得る

```bash
# CLI 1 行で全自動 (TTY 不要)
hersona recommend --answers distance=1,speech=0,role=1 --apply --explain --json
# --apply で注入ブロックも表示 / --json で機械可読出力
# --explain で各採用属性の根拠 (rationale) + 落選の代替案 + サマリを表示
# v1.4.0 から --apply 時に intensity_baseline が記録される
```

### 人格を他フレームワークへエクスポート (v1.4.0 で 5 形式)

```bash
# LangGraph / LangChain / OpenAI / Anthropic 向け
hersona export personality/tsundere speech/keigo --format messages > tsundere_keigo.json
# → [{"role": "system", "content": "..."}] 形式

# Markdown (注入ブロックの素文)
hersona export personality/tsundere --format markdown

# 構造化 (メタデータ + システムプロンプト + 競合情報)
hersona export personality/tsundere --format json

# OpenAI Assistants API (v1.4.0)
hersona export personality/tsundere speech/keigo --format openai_assistants
# → Assistants instructions 用 markdown、metadata あり

# LangChain SystemMessage (v1.4.0)
hersona export personality/tsundere speech/keigo --format langchain_system_message
# → langchain.schema.SystemMessage 互換 JSON
```

### 強度指標を採点 + 期待バンド外なら自己チェックプロンプト (v1.4.0)

```bash
# 通常の採点
hersona measure personality/tsundere speech/keigo --weight strong --text "べ、別に...あんたのためじゃないんだからね！"
# → score 76/100, status=pass ✓

# 期待バンド外を警告 + 自己チェックプロンプト
hersona measure personality/tsundere speech/keigo --weight strong --text "了解しました。" --strict
# → score 12/100, status=under ⚠ + self-audit prompt を stderr

# プロンプトのみ表示 (LLM に貼り付けて再採点)
hersona measure personality/tsundere speech/keigo --weight strong --check-prompt
# → レポート抑制、生成プロンプトのみ
```

### SOUL.md に ## Recent Context を注入 (v1.4.0)

```bash
# インライン JSON
hersona soul personality/tsundere --memory '{"recent_topic":"ReAct パターンの話","mood":"やや真剣"}'
# → SOUL.md 末尾に `## Recent Context` セクション追加

# ファイルから読み込み
cat > /tmp/memory.json <<EOF
{
  "recent_topic": "openai_assistants format の export 議論",
  "mood": "やや真剣",
  "last_event": "v1.4.0 リリース"
}
EOF
hersona soul personality/tsundere --memory-file /tmp/memory.json

# persistent モードでも使える
hersona personality/tsundere speech/keigo persistent --memory "$(cat /tmp/memory.json)"
```

### ブレンドをプリセット保存して再利用する

```bash
# 保存
hersona save my_tsundere personality/tsundere speech/keigo --weight moderate --note "硬めツンデレ"
# 一覧
hersona presets
# 呼び出し
hersona load my_tsundere
# 強度上書き
hersona load my_tsundere --weight strong
```

### 新しい属性テンプレートを追加する

```bash
# 1. attributes/<category>/<name>.yaml を schema/attribute.schema.json に準拠して作成
# 2. scripts/_oneoff/gen_v1_attributes.py を使うか、手書きで配置
# 3. 検証
cd ~/projects/hersona
python scripts/validate.py
pytest

# 4. コミット + push (wt/<branch> 上で)
git add attributes/<category>/<name>.yaml
git commit -m "feat(attributes): add <category>/<name>"
git push origin wt/<branch>
```

### シェル補完を有効にする

```bash
pip install "hersona[completion]"
# bash
eval "$(register-python-argcomplete hersona)"
# zsh
eval "$(register-python-argcomplete hersona)"
# fish
register-python-argcomplete --shell fish hersona | source

# 補完される対象: サブコマンド / 属性名 (show/blend/diff/preview/measure/save) / プリセット名 (load)
```

## Reference Files

- スキーマ: `~/projects/hersona/schema/attribute.schema.json`
- 属性テンプレート: `~/projects/hersona/attributes/` （現件数は `find attributes -name "*.yaml" | wc -l` で取得）
- core ロジック: `~/projects/hersona/hersona/core/` (compatibility / authoring / recommend / attach / export / weight / presets / mcp / soul / intensity)
- CLI 殻: `~/projects/hersona/hersona/cli/`
- 検証 CLI: `~/projects/hersona/scripts/validate.py`
- 公式 README: `~/projects/hersona/README.md`
- コントリビュートガイド: `~/projects/hersona/CONTRIBUTING.md`
- 公開 API 凍結: `~/projects/hersona/docs/PUBLIC_API.md`
- hermes-agent-skill-authoring 規約: `~/.hermes/skills/software-development/hermes-agent-skill-authoring/SKILL.md`
- 関連スキル:
  - `hersona-attribute-development` — 新規属性 YAML 追加
  - `hersona-recommend-engine` — 診断クイズエンジン (WeightMagnitude / 閾値 / CLI フラグ)
  - `hersona-recommend-quiz` — 診断クイズをプレイ (TTY なしでも `scripts/run_quiz.py`)
  - `hersona-project-operations` — 戦略 / 構造 / 複数 PR 横断
  - `hermes-yaml-config-safety` — config.yaml のネスト破壊対策
  - `chat-persona-roleplay` — チャットプラットフォーム上で `/hersona` が効かない時の代替

## Versioning

### hersona バージョン履歴

- **v0.0.1** (2026-06-13): 64 属性初版リリース（広島弁追加前）。PyPI Trusted Publishing 経路確立。
- **v1.0.0** (2026-06-15): v1.0 pivot — `data/<キャラ>` 廃止、属性テンプレート単体フロー化。
- **v1.1.0** (2026-06-??): 8 PR 累計 / 52 属性 / intensity metric 追加。
- **v1.2.0** (2026-06-??): 65 属性化、SOUL.md 永続化、multi-tool ターゲット対応。
- **v1.3.0** (2026-06-17): measure --strict + intensity baseline + SOUL.md memory + export 拡張。PR-1/2/3 マージ。
- **v0.2.0** (2026-06-17): ユーザー指示で v1.3.0 をリネーム (= ロールバック)。**PyPI に残存**。
- **v1.4.0** (2026-06-17): ロールバック撤回、v1.3.0 の機能セットを v1.4.0 として再 publish。
  PyPI 履歴は `0.0.1 → 1.0.0 → 1.1.0 → 1.2.0 → 1.3.0 → 0.2.0 → 1.4.0` という
  ロールバック履歴を含む。**機能的には v1.3.0 と同じ** (version bump + tag 置換のみ)。

### 廃止済みデータ形式

- `data/<title>/<character>.yaml` 形式の個別キャラ依存 YAML は v1.0 で完全廃止。
  キャラに依存しない **属性の組合せ** で任意の人格を構築する設計に移行。

### 破壊的変更

- v0.0.1 → v0.0.2: コマンド引数 `<title> <character>` → `<category>/<name>` (v3.0.0 で完了)
- v0.0.2 → v0.1.0: 広島弁追加 (PR #77)。`speech` カテゴリが 25 → 26 件。
- v0.0.x → v0.1.0: `hersona` CLI に `preview` / `diff` / `save` / `presets` / `load` / `export` サブコマンド追加 (PR #67-#75)。
- v1.2.0 → v1.3.0 / v1.4.0: `measure --strict` / `soul --memory` / `export` 5 形式追加。
  `Recommendation.intensity_baseline` / `Preset.intensity_baseline` フィールド追加。
  公開 API への追加のみ（semver additive）。

### SKILL.md バージョン履歴

- **v0.0.1** (2026-06-13): 64 属性初版。PyPI Trusted Publishing 経路確立。
- **v0.0.2** (SKILL.md): 旧バージョン。1,382 バイトの stub で Overview/When to Use/Common Pitfalls/Verification Checklist が欠落しており peer 品質未満。
- **v0.1.0** (2026-06-15): 65 属性に拡張 (PR #77 広島弁追加)。CLI サブコマンド `preview` / `diff` / `save` / `presets` / `load` / `export` を反映。PR #74-#77 (argcomplete / export / MCP / hiroshima_ben) を全て反映。peer 構造 (Overview / When to Use / Common Pitfalls / Verification Checklist / One-Shot Recipes) に準拠。元ファイルの誤字 (「砮」を「砕」、「続続」を「継続」) を修正。
- **v0.2.0** (本 SKILL.md, 2026-06-17): v1.4.0 リリースに合わせて SKILL.md を v0.2.0 へ bump。v1.4.0 の新機能 (measure --strict / --check-prompt / intensity_baseline / soul --memory / export 5 形式) を Command Syntax / Common Pitfalls / Verification Checklist / One-Shot Recipes に反映。Pitfall 10-12 (memory injection / strict プロンプトの誤用 / export 5 形式の注意) 追加。
  + **Living & Responsive Conversation** セクション追加（ユーザー指示による改善）。
