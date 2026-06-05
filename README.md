# hersona

> アニメ・ゲーム・漫画キャラの口調・性格プロファイル集
> AIエージェント（Hermes Agent 等）で `/personality` プリセットとして使える

[![License: CC BY-SA 4.0](https://img.shields.io/badge/License-CC_BY--SA_4.0-lightgrey.svg)](https://creativecommons.org/licenses/by-sa/4.0/)

## 概要

アニメ・ゲーム・漫画キャラクターの **口調・性格・語彙** を体系的にデータベース化し、AIエージェントの system prompt に注入できるプロファイルとして配布するオープンソースプロジェクト。

各キャラは構造化データ（YAML）と人間可読ドキュメント（Markdown）の両形式で提供され、Hermes Agent の `/personality` 機能、または他のLLMベースのチャットエージェントで利用できる。

## 使い方

### Hermes Agent で使う

`~/.hermes/config.yaml` の `agent.personalities` に追加：

```yaml
agent:
  personalities:
    melina: |
      あなたはエルデンリングのメリーナです。
      [data/elden-ring/melina.md の中身を貼り付け]
```

または `/personality` コマンドで一時切り替え。

### 他の LLM で使う

`data/<作品>/<キャラ>.md` の内容を system prompt にそのまま入れる。YAML は機械可読・解析用。

## 収録作品

- [エルデンリング (ELDEN RING)](./data/elden-ring/)

## データ形式

```
data/
└── <作品名>/
    ├── _index.md            # 作品紹介・キャラ一覧
    ├── <キャラ名>.yaml      # 構造化プロファイル（機械可読）
    └── <キャラ名>.md        # 人間可読プロファイル（引用付き）
```

### YAML スキーマ

[schema/character.schema.json](./schema/character.schema.json) を参照。

### YAML 必須フィールド（character.schema.json）

- `character_id`: 一意ID（小文字英数字ハイフン）
- `name`: 表示名
- `source`: 作品名
- `license`: 必ず `CC-BY-SA-4.0`
- `personality.core_traits`: 性格特性タグ（3-7個）
- `personality.speech_style`: 口調の全体説明
- `personality.tone`: 声の雰囲気

### YAML 推奨フィールド（4鉄則）

- `personality.first_person`: 一人称（セリフ根拠必須）
- `personality.second_person`: 二人称（セリフ根拠必須）
- `personality.sentence_endings`: 語尾パターン（3個以上）
- `personality.catchphrases`: 口癖（3個以上）

### 人格アタッチメント（persona_attach_prompt）

YAML の `persona_attach_prompt` フィールドに、AIエージェントのシステムプロンプトへ注入する **厳格なキャラ人格プロンプト** を定義できる（オプション）。

スキーマは [schema/persona_attach.schema.json](./schema/persona_attach.schema.json) を参照。

#### メリーナ人格アタッチ例

`data/elden-ring/melina.yaml` の `persona_attach_prompt` には **口語版・厳格メリーナ人格** が定義されている：

- 一人称: **「私」** のみ
- 二人称: **「貴方」** のみ（マスター = 褪せ人 = 契約の盟友 として扱う）
- 語尾: **「～の」「～のね」「～わ」「～ほしい」「～だろう」「～ね」** を多用
- 口癖: **冒頭の「・・・」** を必ず置く
- 文体: 古語・文語の語彙を残しつつ口語で話す
- 適用強度 (intensity): 8/10
- 解除コマンド: `/personality default`

#### 使い方

```bash
# 人格プリセット一覧
python scripts/persona_attach.py --list

# メリーナ人格の詳細（attach_prompt, forbidden/required_words 等）
python scripts/persona_attach.py --show melina

# テキストがメリーナ人格アタッチ条件を満たすか採点
python scripts/persona_attach.py --check melina --input sample.txt

# ~/.hermes/config.yaml への登録手順を表示（自動編集はしない）
python scripts/persona_attach.py --register melina

# 解除手順の表示
python scripts/persona_attach.py --detach melina
```

#### 他キャラへの展開

新しいキャラを追加するときは、以下の手順で他キャラと同じ構造で人格アタッチメントを展開可能：

1. `data/<作品>/<キャラ>.yaml` の `personality` 配下に 4鉄則・口調・性格を定義
2. 同じ YAML の `persona_attach_prompt` フィールドに [schema/persona_attach.schema.json](./schema/persona_attach.schema.json) 準拠の構造でアタッチプロンプトを定義
3. `python scripts/validate.py` で YAML 全体 + persona_attach_prompt を検証
4. `python scripts/persona_attach.py --register <register_call>` で config.yaml 登録手順を確認
5. 任意: `data/<作品>/<キャラ>.md` に人間可読の説明セクションを追加

これにより、複数ユーザーが同じキャラを同じルールでセットアップでき、出力が安定する。

## ライセンス

- 本リポジトリのコード: CC BY-SA 4.0
- 各キャラプロファイル: CC BY-SA 4.0
- セリフ引用: 各 Wiki のライセンス方針に従う（`license_source` 参照）

## コントリビュート

1. データ追加は `data/<作品名>/<キャラ名>.{yaml,md}` 形式で
2. セリフ引用は出典URL必須（Wiki記事ライセンス継承）
3. PR前に `python scripts/validate.py` で検証

詳細は [CONTRIBUTING.md](./CONTRIBUTING.md) を参照。

## 関連リンク

- リポジトリ: https://github.com/shiro-0x/hersona
- 関連スキル: hersona-collector / hersona-writer / hersona-publisher
