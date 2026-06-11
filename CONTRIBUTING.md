# コントリビュートガイド

hersona プロジェクトへの貢献ありがとうございます。

## hersona v1.0 のアーキテクチャ要約

v1.0 では従来の「data/<作品>/<キャラ>.yaml 方式」は廃止し、
LLM のシステムプロンプトに「属性テンプレート (`attributes/<category>/<name>.yaml`)」
を直接アタッチする方式に移行しました。

- セリフ集の事前収集は不要 (LLM が解釈段階で属性を発現)
- キャラ別 YAML は不要 (ユーザーが必要属性を割り当てる)
- 属性テンプレートの追加・改善が本リポジトリの中心作業

## 開発フロー

```
属性テンプレート追加 (attribute author) → スキーマ検証 (validator) → PR レビュー
```

## 属性テンプレートの追加

### 1. 配置場所の決定

`attributes/<category>/<name>.yaml` に配置。`<category>` は以下 3 種:

- `personality` — 性格特性 (tsundere, kuudere 等)
- `speech` — 話し方 (keigo, archaic, kansai_ben 等)
- `archetype` — 役割 (heroine, mentor, rival 等)

`<name>` はスネークケース (例: `tsundere`, `boku_girl`)。

### 2. YAML 生成

`schema/attribute.schema.json` に準拠。`scripts/_oneoff/gen_v1_attributes.py`
が既存 25 属性の雛形なので、これを参考に手作業または LLM で生成可能。

各属性 YAML が持つ主要フィールド:

- `attribute_category` / `attribute_name` — 配置と一致
- `display_name_ja` / `display_name_en` — 表示名
- `weight_dimension` — 強度軸 (mild / moderate / strong / none)
- `typical_value_range` — 典型的な強度レンジ
- `description_ja` / `description_en` — 説明
- `core_traits` — 性格特性リスト (3-7 個目安)
- `catchphrases` — 口癖リスト (任意)
- `tone` — 1 行程度の口調説明 (任意)
- `examples` — AI エージェント活用例 (5 パターン推奨: 注入 / 強度調整 / 互換性 / NG)
- `compatible_archetypes` / `conflicts_with` — 他の archetype との関係
- `tags` — 検索用タグ

### 3. 検証

```bash
python scripts/validate.py
```

全 attributes/ YAML がスキーマと整合するか確認。エラーが出たら修正して再実行。

### 4. コミット・PR

```bash
git add attributes/<category>/<name>.yaml
git commit -m "feat(attributes): add <category>/<name>"
git push origin wt/<branch>
```

PR テンプレートに従って記載。リブラがレビューしてマージ。

## プルリクエスト

PR テンプレートに従って記載。review 待ち。リブラが承認したらマージ。
PR 1 件 = 1 属性追加が基本。複数追加時は事前 Issue で合意。

## ライセンス方針

- `attributes/` 配下のテンプレートは CC0 (public domain dedication) — `LICENSE-CC0.txt` 参照
- 商用利用可否や LLM 出力の責任は `DISCLAIMER.md` を参照

## 質問・相談

GitHub Issue で。ラベル `question` を付けてください。
