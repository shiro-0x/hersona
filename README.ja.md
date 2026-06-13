# hersona

**日本語** · [English](./README.md)

> 二次元キャラの **口調・性格・語彙** 属性テンプレート集
> AI エージェント (Hermes Agent 等) で `/hersona` プリセットとして使えるようにすることを目的にしたプロジェクト

[![License: MIT (code)](https://img.shields.io/badge/License-MIT-lightgrey.svg)](./LICENSE)
[![Templates: CC0 1.0](https://img.shields.io/badge/Templates-CC0_1.0-lightgrey.svg)](./LICENSE-CC0.txt)

## ライセンス構成 (v0.0.1)

リポジトリは 2 層に分かれており、各層でライセンスが異なります:

| 範囲 | ライセンス | 補足 |
|---|---|---|
| `scripts/`, `schema/`, `pyproject.toml` 等 (コード) | **MIT** | `LICENSE` |
| `attributes/**/*.yaml` (汎用属性テンプレート) | **CC0 1.0** | `LICENSE-CC0.txt` — パブリックドメイン献呈 |

## 概要

二次元キャラクターの口調・性格を、体系化し、AI エージェントのシステムプロンプトに注入できるテンプレート集として配布する
オープンソースプロジェクト。

- **属性テンプレート** (`attributes/<category>/<name>.yaml`) を提供
- ユーザー (またはエージェント) が必要属性を割り当てることで、任意キャラの人格を構築

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

### CLI で使う

`pip install -e .` 後、`hersona` コマンド (または `python -m hersona.cli`) が使える:

```
hersona list                                  # 利用可能な属性一覧 (公開 + user)
hersona show tsundere                          # 属性の詳細
hersona matrix --json                          # 相性マトリクスを JSON でダンプ
hersona blend tsundere keigo --weight strong   # 複数属性を注入ブロックに合成 (強度指定)
hersona recommend                              # 診断クイズ → 推薦 (対話。表示言語 en では英語 speech へ導線)
hersona recommend --answers distance=1,speech=0,role=1 --apply
hersona create --category personality --name my_attr \
  --display-ja マイ属性 --display-en MyAttr \
  --desc-ja 説明 --desc-en desc --example "..."  # 属性を作成し user 名前空間に保存
hersona measure kyoto_ben --weight strong --text "ようおいでやすどす"  # 出力の強度指標を採点
hersona measure tsundere heroine --weight moderate --input out.txt       # ブレンドの強度指標
```

ユーザー作成属性は `~/.hermes/attributes/` (既定) または `HERSONA_USER_DIR` で
指定したディレクトリに保存され、公開 `attributes/` には混ざらない。

### 他の LLM で使う

`attributes/<category>/<name>.yaml` の `core_traits` / `catchphrases` / `tone` /
`description_ja` などをそのまま system prompt に貼り付ける。

複数属性をブレンドする場合は、各 YAML の `compatible_archetypes` / `conflicts_with` を
参照して互換性を確認する。

## データ形式

```
attributes/
├── personality/             # 性格属性 (20 種)
├── speech/                  # 口調属性 (25 種: 日本語 20 + 英語 5)
├── archetype/               # アーキタイプ属性 (9 種)
├── visual/                  # 外見属性 (5 種)
└── hobby/                   # 趣味属性 (5 種)
```

各属性 YAML は [`schema/attribute.schema.json`](./schema/attribute.schema.json) に
準拠する。

### 属性テンプレート (`attributes/`, v0.0.1〜)

[schema/attribute.schema.json](./schema/attribute.schema.json) で検証される、キャラプロファイルに
付与する **汎用属性タグのテンプレート集**。現在は personality 20 / speech 25 /
archetype 9 / visual 5 / hobby 5 の計 64 種を定義 (詳細は [attributes/](./attributes/) 配下)。
speech は日本語 (`content_lang: ja`) 20 種 + 英語 (`content_lang: en`) 5 種。

#### 64 属性一覧

| category | count | 含まれる属性 |
|---|---|---|
| personality | 20 | airhead / chuunibyou / dandere / genki / hot_blooded / intellectual / klutz / kuudere / mysterious / narcissist / optimist / pessimist / playful / pragmatist / protective / serious / stoic / switch / tsundere / yandere |
| speech (ja) | 20 | archaic / blunt / boku_girl / gyaru / kansai_ben / keigo / kyoto_ben / mischievous / mixed_dialect / onee_kotoba / ore_boy / princess_speech / seductive / soft / stutter / theatrical / third_person / tomboy / washi / whispery |
| speech (en) | 5 | formal_en / casual_en / blunt_en / southern_us_en / british_en |
| archetype | 9 | childhood_friend / gamer_otaku / heroine / hikikomori / idol / mentor / rival / robot_android / shrine_maiden |
| visual | 5 | animal_ears / glamorous / glasses / petite / silver_hair |
| hobby | 5 | cooking / gamer / music / reading / sports |

#### 必須フィールド (attribute.schema.json)

| フィールド | 型 | 必須 | 説明 |
|---|---|---|---|
| `attribute_category` | enum | ✓ | `personality` / `speech` / `archetype` / `visual` / `hobby` の 5 種 |
| `attribute_name` | string (snake_case) | ✓ | ファイル名と一致する一意 ID |
| `display_name_ja` / `display_name_en` | string | ✓ | 日本語 / 英語表示名 |
| `weight_dimension` | enum | ✓ | `none` / `mild` / `moderate` / `strong` |
| `description_ja` / `description_en` | string | ✓ | 属性の説明 |
| `examples` | string[] (1 件以上) | ✓ | AI エージェント活用例 (7 パターン推奨: 注入 / 強度調整 x2 / 互換性 / 複数ターン会話 / 英語応答 / NG)。固有名詞・特定作品を含まない |

#### 任意フィールド (Round 3 雛形 6 フィールド)

| フィールド | 型 | 説明 |
|---|---|---|
| `core_traits` | string[] (3-7 個) | 性格特性リスト。AI エージェントが prompt 注入時に解釈する核 |
| `speech_style` | string | 口調の総合説明 (1 行) |
| `second_person` | string | 二人称 (例: 「貴方」「お前」)。ユーザー役名を含む |
| `sentence_endings` | string[] (3 個以上) | 語尾パターン (日本語 speech、例: 「〜の」「〜のね」) |
| `lexical_markers` | string[] | 特徴語・言い回し (英語 speech、例: "gonna" / "y'all")。英語の強度測定に使用 |
| `register` | enum | 話法レジスタ: `formal` / `neutral` / `casual` / `vulgar` (主に英語 speech) |
| `catchphrases` | string[] (任意) | 口癖 (3 個以上推奨) |
| `tone` | string | 声の雰囲気 (1 行) |

#### 関係性フィールド

| フィールド | 型 | 説明 |
|---|---|---|
| `compatible_archetypes` | string[] | 併用が想定される archetype の attribute_name リスト |
| `conflicts_with` | string[] | 排他が想定される他 attribute_name リスト |
| `tags` | string[] | 横断検索用タグ |
| `typical_value_range` | string | 重み付け運用時の典型値 (例: `0.4-0.7`) |
| `content_lang` | enum (`ja`/`en`) | 人格コンテンツの言語。応答言語指示・強度測定に影響。未指定 ⇒ `ja` |
| `content_i18n` | object | 言語別ネイティブ・コンテンツ (`<lang>.{catchphrases,tone,core_traits,examples}`)。BASE (トップレベル) は `content_lang` の言語、`content_i18n.en` に英語版を追加。注入される口癖を人格の言語に保つ |
| `has_catchphrase` | bool | 口癖の有無 |
| `variant` | string (snake_case) | 同 attribute_name の派生ラベル |
| `notes` | string | 補足・運用メモ |

#### 雛形生成スクリプト

`scripts/_oneoff/gen_v1_attributes.py` を Single Source of Truth として YAML を再生成できる。
直接 YAML を編集する代わりに、リストを更新して再実行する:

```bash
# (旧形式の) 属性 YAML を確認なしで再生成
python scripts/_oneoff/gen_v1_attributes.py

# 書き込み予定パスのみ表示
python scripts/_oneoff/gen_v1_attributes.py --dry-run
```

> 注意: この生成スクリプトは凍結スナップショットで、旧メタデータ形式
> (`display_name_ja/en`・`description_ja/en`) を出力します。再生成した場合は
> `python scripts/migrate_i18n.py` を実行し、i18n ブロック形式 (BASE=en + `i18n.ja`) へ戻してください。

#### 検証

```bash
python scripts/validate.py
```

64 属性 YAML が全てスキーマに違反しないことを確認する。

## ライセンス

- 本リポジトリのコード: **MIT**
- `attributes/` 配下のテンプレート: **CC0 1.0** (public domain dedication)
- 免責事項: [DISCLAIMER.md](./DISCLAIMER.md) を必ず参照

## コントリビュート

1. 属性テンプレートの追加は `attributes/<category>/<name>.yaml` 形式で
2. examples / core_traits / catchphrases 等はセリフ根拠不要 (LLM が解釈する) だが、
   固有名詞・特定作品を含めない
3. PR 前に `python scripts/validate.py` で検証
4. 1 PR = 1 属性が基本。複数追加時は事前 Issue で合意

詳細は [CONTRIBUTING.md](./CONTRIBUTING.md) を参照。

エージェント／開発者向けの「次に何を実装するか」の指示書は
[docs/IMPLEMENTATION_GUIDE.md](./docs/IMPLEMENTATION_GUIDE.md) を参照。
