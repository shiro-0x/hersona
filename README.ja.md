# hersona

**日本語** · [English](./README.md)

> 二次元キャラの **口調・性格・語彙** 属性テンプレート集
> AI エージェント (Hermes Agent 等) で `/hersona` プリセットとして使えるようにすることを目的にしたプロジェクト

[![License: MIT (code)](https://img.shields.io/badge/License-MIT-lightgrey.svg)](./LICENSE)
[![Templates: CC0 1.0](https://img.shields.io/badge/Templates-CC0_1.0-lightgrey.svg)](./LICENSE-CC0.txt)

## インストール (Hermes Agent)

審査なし・今すぐ tap 経由でインストール可能:

```bash
hermes skills tap add shiro-0x/hersona
hermes skills install hersona
hermes skills install hersona-initializer
```

スキルレジストリへの掲載状況:

| レジストリ | 状態 |
|---|---|
| [HermesHub](https://www.hermeshub.xyz/) | 🔄 審査中 ([PR #125](https://github.com/amanning3390/hermeshub/pull/125)) |
| [ClawHub](https://clawhub.ai/) | 🔜 申請準備中 |

## ライセンス構成

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

詳細は [skills/hersona/SKILL.md](./skills/hersona/SKILL.md) を参照。レシピ集 /
検証チェックリスト / バージョン履歴は
[skills/hersona/REFERENCE.md](./skills/hersona/REFERENCE.md) に分離している
(スキル本体を毎ターン軽量に保つためオンデマンド読み込み)。

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
hersona update                                 # リポジトリから最新の属性データをダウンロード
hersona update --ref v1.4.1                    # ブランチ / タグ / コミット SHA を指定 (既定: main)
hersona update --clear                         # ダウンロード済みデータを削除し同梱テンプレートへ戻す
```

ユーザー作成属性は `~/.hermes/attributes/` (既定) または `HERSONA_USER_DIR` で
指定したディレクトリに保存され、公開 `attributes/` には混ざらない。

`hersona update` は**パッケージを再インストールせずに**属性テンプレートを最新化する。
`pip`/wheel でインストールすると `attributes/` と `schema/` はビルド時に同梱されるため、
アップストリームへの追加は再インストールしないと反映されない。`hersona update` は最新の
`attributes/` と `schema/` をリポジトリからローカルのデータキャッシュ
(既定 `~/.hermes/data/`、または `HERSONA_DATA_DIR`) へダウンロードし、同梱テンプレートより
優先して解決させる。`hersona update --clear` でキャッシュを削除し同梱データへ戻せる。
ダウンロードは Python 標準ライブラリのみで行う (追加依存なし)。

### 他の LLM で使う

`attributes/<category>/<name>.yaml` の `core_traits` / `catchphrases` / `tone` /
`description_ja` などをそのまま system prompt に貼り付ける。

複数属性をブレンドする場合は、各 YAML の `compatible_archetypes` / `conflicts_with` を
参照して互換性を確認する。

## データ形式

```
attributes/
├── personality/             # 性格属性 (42 種: 日本語ベース 35 + 英語ネイティブ 5 + 日本語ベース hautaine + 日本語ベース sociable)
├── speech/                  # 口調属性 (31 種: 日本語 25 + 英語 5 + archaic_otaku)
├── archetype/               # アーキタイプ属性 (9 種)
├── visual/                  # 外見属性 (5 種)
└── hobby/                   # 趣味属性 (5 種)
```

各属性 YAML は [`schema/attribute.schema.json`](./schema/attribute.schema.json) に
準拠する。

### 属性テンプレート (`attributes/`)

[schema/attribute.schema.json](./schema/attribute.schema.json) で検証される、キャラプロファイルに
付与する **汎用属性タグのテンプレート集**。現在は personality 42 / speech 67 /
archetype 9 / visual 5 / hobby 5 の計 128 種を定義 (詳細は [attributes/](./attributes/) 配下)。
speech は日本語 (`content_lang: ja`) 60 種 + 英語 (`content_lang: en`) 5 種 + `archaic_otaku`
(文語レジスタに推し活・作品引用を融合させた口調)。
personality は日本語ベース 35 種 + 海外向け英語ネイティブ (`content_lang: en`) 5 種 +
`hautaine` (生まれ・育ちへの自負から来る高飛車さ) + `sociable` (場の空気を読んで聞き手適応する社交性)。

#### 128 属性一覧

| category | count | 含まれる属性 |
|---|---|---|
| personality (ja-base) | 35 | airhead / battle_junkie / chuunibyou / crybaby / dandere / deadpan / deredere / diligent / genki / gluttonous / himedere / hinedere / hot_blooded / intellectual / kamidere / klutz / kuudere / laid_back / menhera / mysterious / narcissist / optimist / pessimist / playful / pragmatist / protective / puppyish / sadodere / scheming / serious / socially_anxious / stoic / switch / tsundere / yandere |
| personality (ja-base, Phase 8) | 2 | hautaine / sociable |
| personality (en-native) | 5 | sassy / rebel / charmer / drama_queen / go_getter |
| speech (ja) | 25 | archaic / blunt / boku_girl / burikko / gyaru / hakata_ben / hiroshima_ben / kansai_ben / keigo / kyoto_ben / mischievous / mixed_dialect / onee_kotoba / ore_boy / princess_speech / robotic / seductive / soft / stutter / theatrical / third_person / tohoku_ben / tomboy / washi / whispery |
| speech (ja, Phase 8) | 1 | archaic_otaku |
| speech (ja, Phase 1: 地域方言) | 36 | akita_ben / ehime_ben / gifu_ben / gunma_ben / hokkaido_ben / hyogo_ben / ibaraki_ben / kagoshima_ben / kanagawa_ben / kanazawa_ben / kochi_ben / kumamoto_ben / mie_ben / miyazaki_ben / nagoya_ben / nagasaki_ben / nara_ben / niigata_ben / oita_ben / okayama_ben / okinawa_ben / osaka_ben / saga_ben / saitama_ben / sanuki_ben / sendai_ben / shimane_ben / shizuoka_ben / tochigi_ben / tokushima_ben / tokyo_ben / toyama_ben / tsugaru_ben / wakayama_ben / yamagata_ben / yamaguchi_ben |
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

#### 任意フィールド

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

通常のメンテナンスは `attributes/<category>/<name>.yaml` を直接追加・編集し、
`python scripts/validate.py` で検証する形で行う。下記のスクリプトは旧形式の
凍結スナップショットなので、日常運用では使用しない。

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

128 属性 YAML が全てスキーマに違反しないことを確認する。

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
