# hersona

> アニメ・ゲーム・漫画キャラの **口調・性格・語彙** 属性テンプレート集
> AI エージェント (Hermes Agent 等) で `/hersona` プリセットとして使える

[![License: MIT (code)](https://img.shields.io/badge/License-MIT-lightgrey.svg)](./LICENSE)
[![Templates: CC0 1.0](https://img.shields.io/badge/Templates-CC0_1.0-lightgrey.svg)](./LICENSE-CC0.txt)

## ライセンス構成 (v1.0)

リポジトリは 2 層に分かれており、各層でライセンスが異なります:

| 範囲 | ライセンス | 補足 |
|---|---|---|
| `scripts/`, `schema/`, `pyproject.toml` 等 (コード) | **MIT** | `LICENSE` |
| `attributes/**/*.yaml` (汎用属性テンプレート) | **CC0 1.0** | `LICENSE-CC0.txt` — パブリックドメイン献呈 |

> v0.x 時代は 3 層構成 (code MIT / attributes CC0 / character data CC BY-SA 4.0) でしたが、
> v1.0 で data/ 配下のキャラ依存 YAML を完全廃止し、**汎用属性のみ**を提供する設計に移行しました。

## 概要

アニメ・ゲーム・漫画キャラクターの口調・性格を、**作品に依存しない属性の組合せ**で
体系化し、AI エージェントのシステムプロンプトに注入できるテンプレート集として配布する
オープンソースプロジェクト。

v0.x までは「メリーナ」「遠坂凛」「パワー」など個別キャラの YAML/MD を提供していましたが、
v1.0 では

- 個別キャラ依存データを完全廃止
- 代わりに `tsundere` / `keigo` / `heroine` などの **属性テンプレート** (`attributes/<category>/<name>.yaml`) を提供
- ユーザー (またはエージェント) が必要属性を割り当てることで、任意キャラの人格を構築

というアーキテクチャに移行しています。

## 使い方

### Hermes Agent で使う

`/hersona <category>/<name>` 形式で属性をアタッチ:

```
/hersona                              # 一覧 + 使い方ヘルプ
/hersona list                         # 利用可能な属性一覧
/hersona show personality/tsundere    # 指定属性の詳細
/hersona personality/tsundere single  # 1 属性のみアタッチ
/hersona personality/tsundere speech/keigo multi  # 複数属性ブレンド
/hersona default                      # 解除
```

詳細は [skills/hersona/SKILL.md](./skills/hersona/SKILL.md) を参照。

### 他の LLM で使う

`attributes/<category>/<name>.yaml` の `core_traits` / `catchphrases` / `tone` /
`description_ja` などをそのまま system prompt に貼り付ける。

複数属性をブレンドする場合は、各 YAML の `compatible_archetypes` / `conflicts_with` を
参照して互換性を確認する。

## データ形式

```
attributes/
├── personality/             # 性格属性 (10 種)
├── speech/                  # 口調属性 (8 種)
└── archetype/               # アーキタイプ属性 (7 種)
```

各属性 YAML は [`schema/attribute.schema.json`](./schema/attribute.schema.json) に
準拠する。

### 属性テンプレート (`attributes/`, v1.0〜)

[schema/attribute.schema.json](./schema/attribute.schema.json) で検証される、キャラプロファイルに
付与する **汎用属性タグのテンプレート集**。v1.0 では personality 10 / speech 8 /
archetype 7 の計 25 種を定義 (詳細は [attributes/](./attributes/) 配下)。

#### 25 属性一覧

| category | count | 含まれる属性 (例) |
|---|---|---|
| personality | 10 | tsundere / kuudere / dandere / genki / serious / stoic / yandere / playful / pessimist / switch |
| speech | 8 | keigo / archaic / kansai_ben / onee_kotoba / boku_girl / ore_boy / third_person / whispery |
| archetype | 7 | heroine / mentor / rival / childhood_friend / gamer_otaku / robot_android / shrine_maiden |

#### 必須フィールド (attribute.schema.json)

| フィールド | 型 | 必須 | 説明 |
|---|---|---|---|
| `attribute_category` | enum | ✓ | `personality` / `speech` / `archetype` の 3 種 |
| `attribute_name` | string (snake_case) | ✓ | ファイル名と一致する一意 ID |
| `display_name_ja` / `display_name_en` | string | ✓ | 日本語 / 英語表示名 |
| `weight_dimension` | enum | ✓ | `none` / `mild` / `moderate` / `strong` |
| `description_ja` / `description_en` | string | ✓ | 属性の説明 |
| `examples` | string[] (1 件以上) | ✓ | AI エージェント活用例 (5 パターン推奨: 注入 / 強度調整 / 互換性 / NG)。固有名詞・特定作品を含まない |

#### 任意フィールド (Round 3 雛形 6 フィールド)

| フィールド | 型 | 説明 |
|---|---|---|
| `core_traits` | string[] (3-7 個) | 性格特性リスト。AI エージェントが prompt 注入時に解釈する核 |
| `speech_style` | string | 口調の総合説明 (1 行) |
| `second_person` | string | 二人称 (例: 「貴方」「お前」)。ユーザー役名を含む |
| `sentence_endings` | string[] (3 個以上) | 語尾パターン (例: 「〜の」「〜のね」) |
| `catchphrases` | string[] (任意) | 口癖 (3 個以上推奨) |
| `tone` | string | 声の雰囲気 (1 行) |

#### 関係性フィールド

| フィールド | 型 | 説明 |
|---|---|---|
| `compatible_archetypes` | string[] | 併用が想定される archetype の attribute_name リスト |
| `conflicts_with` | string[] | 排他が想定される他 attribute_name リスト |
| `tags` | string[] | 横断検索用タグ |
| `typical_value_range` | string | 重み付け運用時の典型値 (例: `0.4-0.7`) |
| `has_catchphrase` | bool | 口癖の有無 |
| `variant` | string (snake_case) | 同 attribute_name の派生ラベル |
| `notes` | string | 補足・運用メモ |

#### 雛形生成スクリプト

`scripts/_oneoff/gen_v1_attributes.py` を Single Source of Truth として YAML を再生成できる。
直接 YAML を編集する代わりに、リストを更新して再実行する:

```bash
# 25 属性 YAML を確認なしで再生成
python scripts/_oneoff/gen_v1_attributes.py

# 書き込み予定パスのみ表示
python scripts/_oneoff/gen_v1_attributes.py --dry-run
```

#### 検証

```bash
python scripts/validate.py
```

25 属性 YAML が全てスキーマに違反しないことを確認する。

## ライセンス

- 本リポジトリのコード: **MIT**
- `attributes/` 配下のテンプレート: **CC0 1.0** (public domain dedication)
- キャラクター権利・二次創作・商用利用の免責: [DISCLAIMER.md](./DISCLAIMER.md) を必ず参照

## コントリビュート

1. 属性テンプレートの追加は `attributes/<category>/<name>.yaml` 形式で
2. examples / core_traits / catchphrases 等はセリフ根拠不要 (LLM が解釈する) だが、
   固有名詞・特定作品を含めない
3. PR 前に `python scripts/validate.py` で検証
4. 1 PR = 1 属性が基本。複数追加時は事前 Issue で合意

詳細は [CONTRIBUTING.md](./CONTRIBUTING.md) を参照。
