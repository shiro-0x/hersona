---
name: hersona
description: "Use when attaching a hersona attribute template to the active session's system prompt via /hersona <category>/<name> [mode]. Loads the attribute YAML from attributes/<category>/<name>.yaml and injects its core_traits / catchphrases / tone / second_person / sentence_endings into the prompt. Supports four modes: single (one attribute, default), multi (multiple attributes with automatic compatible/conflicts check), persistent (registered in ~/.hermes/config.yaml for automatic application in new sessions), and reset (clear all persistent registrations). Also supports /hersona list, /hersona show, /hersona check, /hersona recommend (diagnostic quiz -> recommended blend -> apply), and /hersona create (author a local attribute into the user namespace). Backed by the hersona core package (compatibility / authoring / recommend / attach) and the `hersona` CLI."
version: 3.2.0
author: Hermes Agent + hersona project
license: MIT
metadata:
  hermes:
    tags: [persona, character, roleplay, attribute, hersona, session-modes, recommend, authoring, v1.0]
    related_skills: [hermes-agent]
---

# hersona — Attribute Template Attachment (v3.1.0)

## Overview

hersona (~/projects/hersona) の `attributes/<category>/<name>.yaml` に登録されている
**汎用属性テンプレート** (personality / speech / archetype / visual / hobby の 50 種) を、
現在のセッションのシステムプロンプトにアタッチするスキル。

v1.0 では v0.x の data/<title>/<character>.yaml 方式 (個別キャラ依存) を完全廃止し、
**作品に依存しない属性の組合せ**で任意キャラの人格を構築する設計に移行。
`tsundere` (personality) + `keigo` (speech) + `heroine` (archetype) のように複数属性を
ブレンドしてアタッチできる。

## When to Use

- 「ツンデレで話したい」「大和言葉の語尾で執筆したい」「 heroine 役として振舞って」
  のように、キャラではなく **属性で** 人格を指定したい
- `/hersona personality/tsundere` のように slash command で依頼された
- 利用可能な 50 属性を確認したい (`/hersona list`)
- 指定属性の詳細 (core_traits / catchphrases / tone 等) を見たい (`/hersona show`)
- テキストが指定属性の条件下にあるか採点したい (`/hersona check`)
- どの属性が好みか分からないので診断して推薦してほしい (`/hersona recommend`)
- 自分専用の属性をローカルで作りたい (`/hersona create`)
- 出力テキストが指定の強度 (weight) に達したか採点したい (`/hersona measure`)
- よく使う属性組合せを新セッションでも維持したい (`persistent` モード)
- persistent 登録を取り消したい (`reset` モード)

**Don't use for:**
- 特定作品キャラのセリフ再現 (DISCLAIMER.md 参照、原作品側ガイドラインを尊重)
- 個別キャラの YAML/MD 追加 (v0.x 形式は廃止済み。属性テンプレートの追加は `CONTRIBUTING.md` 参照)

## Command Syntax

```
/hersona                                     # 一覧 + 使い方ヘルプ
/hersona list                                # 利用可能な属性ツリー表示 (公開 + user)
/hersona show <category>/<name>              # 指定属性の詳細
/hersona <category>/<name> [mode]            # 属性アタッチ
/hersona check <category>/<name> --input <file>  # テキストが属性条件を満たすか採点
/hersona recommend                           # 診断クイズ → 推薦ブレンド → 適用 (→ 任意で保存)
/hersona create                              # 属性をローカル作成し user 名前空間に保存
/hersona measure <cat>/<name>... --weight <level> --input <file>|--text "..."  # 強度指標を採点
/hersona default                             # 解除 (test/single/multi モードの取り消し)
/hersona reset                               # persistent モードの全解除
```

`<category>` は `personality` / `speech` / `archetype` の 3 種。
`<name>` は attributes/ 配下のファイル名 stem (snake_case)。

`recommend` / `create` / `list` / `show` / `matrix` / `blend` は `hersona` CLI
(`python -m hersona.cli`) としても同じ core を介して実行できる。スキルと CLI は
`hersona/core/` (compatibility / authoring / recommend / attach) を共有する。

`/hersona check` は LLM の応答テキストが `core_traits` / `catchphrases` / `tone` /
`second_person` / `sentence_endings` の各条件を満たすか 5 項目 / 100 点満点で採点する
(「5 項目 = 互換性 / 必須語 / 一人称 (personality のみ) / 語尾 (speech のみ) / 強度」)。

### Arguments

- `<category>`: 属性カテゴリ。`personality` / `speech` / `archetype` のいずれか
- `<name>`: 属性名。`attributes/<category>/<name>.yaml` の stem (例: `tsundere`, `keigo`, `heroine`)
- `[mode]`: 適用モード。**省略可**。詳細は「## Four Modes」参照
  - 省略時: デフォルトは `single` (1 属性のみ)
  - `single` / `multi` / `persistent` / `reset` のいずれかを明示可能
- `--input <file>`: `--check` 用のテキストファイルパス

## Four Modes

`/hersona <category>/<name> [mode]` の `[mode]` で挙動を切り替え。

| モード | 効果 | 永続性 | 解除方法 | 推奨用途 |
|---|---|---|---|---|
| **single** (デフォルト) | 1 つの属性のみをシステムプロンプトに注入 | そのセッションだけ | `/hersona default` または `/new` | 属性 1 つの感触を試す、短期ロールプレイ |
| **multi** | 複数属性をスペース区切りで指定し、`compatible_archetypes` / `conflicts_with` の整合性を自動チェック | そのセッションだけ | `/hersona default` | キャラを多面的に構築 (例: `tsundere` + `keigo` + `heroine`) |
| **persistent** | `~/.hermes/config.yaml` の `agent.personalities.<name>` に登録 | 新規セッションで自動適用 | `/hersona reset` | 常用する属性の永続化 |
| **reset** | persistent モードの取り消し | persistent 登録を全削除 | (解除コマンド自体) | 永続属性の撤収、config.yaml クリーンアップ |

### モード詳細

#### single モード (デフォルト)

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

#### multi モード

```
/hersona personality/tsundere speech/keigo archetype/heroine multi
```

- 複数属性をスペース区切りで指定
- 各属性の `compatible_archetypes` / `conflicts_with` を自動チェック
  - **互換性 OK**: 全属性の `core_traits` / `catchphrases` / `tone` を統合注入
  - **conflict 検出**: 警告を表示し、ユーザーに続行可否を確認 (default: 続行)
- 例: `tsundere` + `playful` は `conflicts_with` 該当 (建前と本音の隠蔽が重複し不誠実さが過剰)

#### persistent モード

```
/hersona personality/tsundere persistent
```

- **実行前に** `~/.hermes/config.yaml` の自動バックアップを作成
  - バックアップ先: `~/.hermes/config_backups/config.yaml.bak.<timestamp>`
- `agent.personalities.<name>` に属性 YAML の主要フィールドを YAML ブロック記法で
  `agent.personalities` セクションへ追記する手順を表示
- ユーザーが config.yaml に**手動で**貼り付け (自動書き込みは安全のため行わない)
- 次のセッション開始時からその属性がデフォルトで適用

#### reset モード

```
/hersona reset
```

- persistent モードで登録した属性を config.yaml から全削除
- **実行前に**自動バックアップ
- 削除後、新セッション開始時からリブラ人格 (デフォルト) に戻る

## Workflow

### 1. 属性を single モードで試す

```
# セッション中に slash command を打つ
/hersona personality/tsundere

# → システムプロンプトに tsundere の core_traits / catchphrases / tone が注入される
# → 応答がツンデレ傾向に切り替わる

# 解除
/hersona default
```

### 2. 複数属性を multi モードでブレンド

```
/hersona personality/tsundere speech/keigo multi

# → 互換性チェックが走り、tsundere + keigo の組み合わせは compatible_archetypes
#   該当のため警告なしで進む
# → 両属性の core_traits / catchphrases / tone が統合注入される
```

```
/hersona personality/tsundere personality/playful multi

# → conflicts_with 警告が表示される
# → 「tsundere (建前で本音を隠す) + playful (冗談で本音を隠す) は意味が重複し
#    不誠実さが過剰になる」と理由が表示される
# → 続行可否をユーザーに確認 (default: 続行)
```

### 3. 属性を persistent モードで永続化する

```
/hersona personality/tsundere persistent

# → ~/.hermes/config.yaml のバックアップが作成される
# → config.yaml に貼り付けるべき YAML 抜粋が表示される
# → 表示された内容を config.yaml の agent.personalities セクションへ手動で貼り付け
# → 次のセッション開始時から tsundere 属性がデフォルトで適用
```

### 4. persistent モードを解除する

```
/hersona reset

# → バックアップが作成される
# → persistent で登録した属性エントリが config.yaml から全削除される
# → 新セッションでリブラ人格 (デフォルト) に戻る
```

### 5. テキストが属性条件を満たすか採点

```bash
# 採点対象のテキストをファイルに保存
echo "べ、別に……用事がなければ、付き合ってもいいけど" > /tmp/test.txt

# 採点実行
/hersona check personality/tsundere --input /tmp/test.txt
# または
python3 scripts/validate.py  # 50 属性 YAML 自体のスキーマ整合確認
```

→ 5 項目 / 100 点満点 + 指摘事項 + 判定 (pass / marginal / retry / fail) を表示。

### 6. 診断クイズで好みの属性を推薦してもらう (recommend)

```
/hersona recommend
# → 数問の診断クイズ (距離感 / 感情 / 話し方 / 立ち位置 / 趣味)
# → 各回答を属性スコアに集計 (適合度スコア)
# → カテゴリごと最高スコアの属性を選び、① 相性マトリクスで conflict を解決した
#   推薦ブレンドを提示
# → 「適用する？ [Y/n]」(デフォルト適用) → multi 相当でアタッチ
```

CLI では非対話実行も可能:

```bash
hersona recommend --answers distance=1,speech=0,role=1 --apply
# --apply で注入ブロックも表示 / --json で機械可読出力
```

推薦ブレンドはそのまま `create` で保存して再利用できる (recommend → apply → save)。

### 7. 自分専用の属性をローカル作成する (create)

```
/hersona create
# → 対話ウィザード: category / attribute_name / 表示名 / weight / 説明 / examples
# → schema/attribute.schema.json の検証ゲートを通過したら user 名前空間に保存
```

CLI では既存属性を土台にした上書き作成や非対話作成も可能:

```bash
hersona create --category personality --name my_tsundere \
  --display-ja 俺ツンデレ --display-en My Tsundere \
  --desc-ja 説明 --desc-en desc --example "..."
```

- 保存先: `~/.hermes/attributes/`(既定) または `HERSONA_USER_DIR`。`attributes/user/` は gitignore
- **ローカル作成は自由** (既存キャラ設定 OK)。固有名詞ガードは**共有・エクスポート時のみ**発動
- 既存属性のフィールド上書き (例: tsundere を土台に catchphrases だけ差し替え) は core の
  `override_attribute()` を使う

## Example Dialogues

### ターン 1: single モード

```
user: /hersona personality/tsundere
assistant: personality/tsundere をアタッチしました。core_traits 7 件、catchphrases
          10 件、tone 説明をシステムプロンプトに注入しています。
          (例: 「べ、別に……」「……バカ」)
user: 一緒に帰らない？
assistant: べ、別に……用事がなければ、付き合ってもいいけど
user: /hersona default
assistant: tsundere テンプレートを解除しました。リブラ人格 (デフォルト) に復帰します。
```

### ターン 2: multi モード (互換性 OK)

```
user: /hersona personality/tsundere speech/keigo multi
assistant: 2 属性をブレンドします:
          - personality/tsundere (compatible with archetype/rival, archetype/childhood_friend)
          - speech/keigo
          → 互換性チェック OK。core_traits / catchphrases / tone / second_person /
            sentence_endings を統合注入しました。
user: お時間よろしいでしょうか
assistant: べ、別に……お時間構いませんわ。……って、なんで敬語とタメ口が混ざって
          しまうのかしら。バカ
```

### ターン 3: multi モード (conflicts_with 警告)

```
user: /hersona personality/tsundere personality/playful multi
assistant: ⚠️ conflicts_with 警告:
          tsundere (建前で本心を隠す) と playful (冗談で本心を隠す) は意味が重複し、
          不誠実さが過剰になります。併用は推奨されません。
          続行しますか? [y/N]
user: y
assistant: 続行します。両属性を統合注入しました (注意: 不誠実さ過剰の可能性あり)。
```

### ターン 4: list / show

```
user: /hersona list
assistant: 利用可能な属性 (50 件):
          personality/ (10)
            - tsundere / kuudere / dandere / genki / serious / stoic /
              yandere / playful / pessimist / switch
          speech/ (10)
            - keigo / archaic / kansai_ben / onee_kotoba / boku_girl /
              ore_boy / third_person / whispery / washi / kyoto_ben
          archetype/ (7)
            - heroine / mentor / rival / childhood_friend / gamer_otaku /
              robot_android / shrine_maiden

user: /hersona show personality/tsundere
assistant: === personality/tsundere ===
          display_name_ja: ツンデレ
          display_name_en: Tsundere
          weight_dimension: moderate
          typical_value_range: 0.4-0.7
          core_traits: 7 件 (素直になれない / 照れ隠し / 本音と反対の口調 / ...)
          catchphrases: 10 件 (べ、別に…… / あんたなんか嫌いだからね！ / ...)
          compatible_archetypes: [rival, childhood_friend]
          conflicts_with: []
```

### ターン 5: check モード

```
user: /hersona check personality/tsundere --input /tmp/sample.txt
assistant: === 属性条件採点: personality/tsundere ===
          入力ファイル: /tmp/sample.txt
          テキスト長: 87 chars
          スコア: 92/100  判定: pass
          指摘:
            - catchphrases 「べ、別に……」が出現 (+20)
            - core_traits 「素直になれない」が発現 (+25)
            - tone「照れ隠しで本心を覆う」が反映 (+25)
            - 二周目以降も継続: 22点
```

## Common Pitfalls

1. **複数属性の `conflicts_with` を見落とす** — `multi` モードで組み合わせる前に
   `/hersona show <category>/<name>` で `conflicts_with` を確認する。
   警告を無視して続行しても、LLM の応答が不誠実さ過剰になる可能性がある。

2. **`compatible_archetypes` の意味を取り違える** — これは「併用想定」であり「必須」
   ではない。compatible_archetypes に無い属性と組み合わせても警告は出ないが、
   文脈的に整合しない場合がある (例: `genki` (personality) + `archaic` (speech) は
   口調の温度差が大きく、LLM が混乱する場合がある)。

3. **persistent モードで config.yaml を壊してしまう** — 必ず **自動バックアップ** が
   作成されるが、手動編集前は念のため `cp ~/.hermes/config.yaml ~/.hermes/config.yaml.bak.<timestamp>`
   で二重バックアップ推奨。

4. **test (single/multi) モードと persistent モードが混在する** — 同じ属性を
   single モードで使いながら config.yaml に persistent 登録すると、挙動が競合する。
   **どちらかに統一**すること。

5. **新セッションで属性が適用されない** — persistent モードで config.yaml を更新したのに
   反映されない場合、config.yaml の YAML 構文エラーが原因の可能性。
   `python3 -c "import yaml; yaml.safe_load(open('$HOME/.hermes/config.yaml'))"` でパース確認。

6. **属性アタッチ中にリブラ人格の口調が出てしまう** — 4 鉄則違反
   (`です・ます` / `あなた` 等の混入)。`/hersona show <category>/<name>` で
   `second_person` / `sentence_endings` を確認、テキストは `/hersona check` で採点。

7. **prompt 注入量の増大** — multi モードで 5 属性以上ブレンドすると、システムプロンプトが
   膨大になり LLM の応答が逆に不安定になる場合がある。3 属性程度が実用上の目安。

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
- [ ] `/hersona check` で `core_traits` / `catchphrases` / `tone` が反映されている

### reset モード

- [ ] `~/.hermes/config_backups/` に reset 前バックアップが作成されている
- [ ] config.yaml から persistent 登録が全削除されている
- [ ] 新セッションでリブラ人格 (デフォルト) に戻る

### validate.py による静的検証

- [ ] `python scripts/validate.py` が 50 属性 / 0 エラーで exit 0
- [ ] `pytest` が全件パス (50 属性のスキーマ整合 / ファイル名一致 / カテゴリ一致)
- [ ] `ls data/` が「No such file or directory」になる
- [ ] `grep -r "elden-ring\|fate\|chainsaw-man" .` が 0 hit (working tree)

## One-Shot Recipes

### 4 つのモードを順番に試す

```
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

## Reference Files

- スキーマ: `~/projects/hersona/schema/attribute.schema.json`
- 50 属性テンプレート: `~/projects/hersona/attributes/`
- core ロジック: `~/projects/hersona/hersona/core/` (compatibility / authoring / recommend / attach)
- CLI 殻: `~/projects/hersona/hersona/cli/` (`hersona` / `python -m hersona.cli`)
- 検証 CLI: `~/projects/hersona/scripts/validate.py`
- 属性生成 Single Source of Truth: `~/projects/hersona/scripts/_oneoff/gen_v1_attributes.py`
- 壊れた personalities 修復: `hermes config set` 経由の書き込みで
  `agent.personalities.<name>` が YAML ブロック記法ごと文字列として壊れた場合は
  手動で config.yaml を編集
- 公式 README: `~/projects/hersona/README.md`
- コントリビュートガイド: `~/projects/hersona/CONTRIBUTING.md`
- 免責事項: `~/projects/hersona/DISCLAIMER.md`
- hermes-agent-skill-authoring 規約: `~/.hermes/skills/software-development/hermes-agent-skill-authoring/SKILL.md`

## Versioning

- **v1.x** (2026-06-05 以前): data/<title>/<character>.yaml 前提の単一モード実装
- **v2.0.0** (2026-06-05): 3 つのモード (test / persistent / reset) に再設計、
  CLI スクリプト `run_hersona.sh` 追加、config.yaml 自動バックアップ機構追加
- **v2.1.0** (2026-06-06): persistent モード YAML 破壊バグ修正 — `fix_persona_block.py`
  追加、`run_hersona.sh` の glob 検索 + register_call 逆引き対応
- **v3.0.0** (2026-06-09): **T1 + T2 統合リリース** — 個別キャラ data/ 形式完全廃止、
  `attributes/<category>/<name>.yaml` 単一テンプレート方式に統一、コマンド体系を
  `/hersona <category>/<name>` に刷新、4 モード (single / multi / persistent / reset) に再設計
- **v3.1.0** (2026-06-09): **core 共有 + CLI 殻リリース** — ロジックを `hersona/core/`
  (compatibility / authoring / recommend / attach) に集約。スキルと `hersona` CLI が
  同一 core を共有。新コマンド `/hersona recommend` (診断クイズ → 推薦ブレンド → 適用) と
  `/hersona create` (ローカル属性オーサリング、検証ゲート + 共有時のみ固有名詞ガード) を追加。
- **v3.2.0** (2026-06-09): `/hersona measure` (強度指標: 語尾一致率 + 口癖密度、決定的採点)
  を追加。`hersona/core/intensity.py` を core に追加し、speech 属性が無いブレンドは
  skip、under のとき stderr 警告。`/hersona check` (LLM 5 項目採点) とは別経路。
  相性マトリクスは conflict を対称閉包として扱う。下位互換 (既存コマンドは不変)。

### 破壊的変更 (v2.x → v3.0.0)

- コマンド引数: `/hersona <title> <character>` → `/hersona <category>/<name>`
- 永続化フロー: `run_hersona.sh --persist <作品> <キャラ>` → `/hersona <category>/<name> persistent`
- データ参照: `data/<title>/<character>.yaml` (キャラ依存) → `attributes/<category>/<name>.yaml` (汎用属性)
- CLI スクリプト: `persona_attach.py` / `run_hersona.sh` / `fix_persona_block.py` / `melina_cli.py` / `apply_persona_to_config.py` 等を全削除
  (これらは v1.0 データ形式に依存していたため)
- ライセンス: 3 層 (code MIT / attributes CC0 / data CC-BY-SA 4.0) → 2 層 (code MIT / attributes CC0)
- `prompts/generate_character.md` / `schema/character.schema.json` / `schema/persona_attach.schema.json` 削除
