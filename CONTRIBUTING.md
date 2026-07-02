# コントリビュートガイド

hersona プロジェクトへの貢献ありがとうございます。

## hersona v1.0 のアーキテクチャ要約

- セリフ集の事前収集は不要 (LLM が解釈段階で属性を発現)
- 属性テンプレートの追加・改善が本リポジトリの中心作業

## 開発フロー

```
属性テンプレート追加 (attribute author) → スキーマ検証 (validator) → PR レビュー
```

## 属性テンプレートの追加

### 1. 配置場所の決定

`attributes/<category>/<name>.yaml` に配置。`<category>` は以下 5 種:

- `personality` — 性格特性 (tsundere, kuudere 等)
- `speech` — 話し方 (keigo, archaic, kansai_ben, mandarin_casual 等)
- `archetype` — 役割 (heroine, mentor, rival 等)
- `visual` — 外見タグ (glasses, silver_hair 等)
- `hobby` — 趣味タグ (cooking, gaming 等)

`<name>` はスネークケース (例: `tsundere`, `boku_girl`)。

### 2. YAML 生成

`schema/attribute.schema.json` に準拠。通常は `attributes/<category>/<name>.yaml` を
直接追加・編集する。`scripts/_oneoff/gen_v1_attributes.py` は旧形式の凍結スナップショットなので、
日常運用の生成元にはしない。

各属性 YAML が持つ主要フィールド:

- `attribute_category` / `attribute_name` — 配置と一致
- `weight_dimension` — 強度軸 (mild / moderate / strong / none)
- `examples` — AI エージェント活用例。固有名詞・特定作品を含めない
- metadata は以下どちらか:
  - 現行形式: `display_name` / `description` + 必要に応じて `i18n.<lang>.display_name` / `description`
  - legacy 形式: `display_name_ja` / `display_name_en` / `description_ja` / `description_en`
- `content_lang` — 人格コンテンツの言語 (`ja` / `en` / `zh` / `ko`; 未指定は `ja`)
- `typical_value_range` — 典型的な強度レンジ
- `core_traits` — 性格特性リスト (3-7 個目安)
- `speech_style` / `first_person` / `second_person` / `sentence_endings` / `lexical_markers` — 口調属性の特徴
- `catchphrases` — 口癖リスト。plain string または `{phrase, when}` object
- `tone` — 1 行程度の口調説明 (任意)
- `image_prompt_tags` — 画像生成用タグ (主に visual)
- `compatible_archetypes` / `conflicts_with` — 他属性との関係
- `tags` — 検索用タグ

### 3. 検証

```bash
python scripts/validate.py
```

全 attributes/ YAML がスキーマと整合するか確認。エラーが出たら修正して再実行。
属性 YAML を追加・削除した場合は、サイトデータも同期するため `python scripts/build_site.py` を実行する。

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

## 更新ルール (ドキュメント同期)

**機能・契約に影響する変更を入れたら、必ず README を確認し、ずれていれば同じ PR で
更新する。** 「コードだけ直して README は後で」は不可 (ドキュメントの陳腐化を防ぐため)。

### README を確認・更新すべき変更

以下のいずれかを変更したら、`README.md` と `README.ja.md` の**両方**を確認する
(英日で内容を一致させる):

- CLI サブコマンド / フラグの追加・変更・削除
- `/hersona` スキルのコマンド構文・モード・挙動
- 属性スキーマ (`schema/attribute.schema.json`) のフィールド追加・変更
- 属性の件数・カテゴリ構成 (現在 201 / 5 カテゴリ)
- 公開 API (`hersona.core` / `docs/PUBLIC_API.md`)
- export 形式 / 連携フレームワーク
- ユーザー向けの新ファイル・新ドキュメント (例: `REFERENCE.md` を足したら README から導線を張る)
- `docs/guides/` 配下のガイド追加・変更 (例: 自己紹介) — README の **Guides / ガイド** 節と `docs/guides/README.md` を同期

### 更新時の手順

1. 変更を実装する
2. 上記に該当するか確認し、該当すれば `README.md` + `README.ja.md` を更新
3. `CHANGELOG.md` の `## [Unreleased]` に追記
4. スキルを触ったら下記「SKILL.md オーサリング規約」も確認
5. `python scripts/validate.py` と `pytest` を通す
6. 属性 YAML を追加・削除した場合は `python scripts/build_site.py` も実行する

> エージェント (Claude Code 等) で作業する場合は `CLAUDE.md` に同じルールの要約が
> あるので、それに従って毎回 README 同期を確認すること。

## SKILL.md オーサリング規約

`skills/hersona/SKILL.md` は **スキル有効時に毎ターン LLM のコンテキストへ載る**
ため、トークンコストを意識して書く。会話の体感速度に直結する。

- **本文は英語で書く。** 日英で意味が同じでも日本語の方がトークン数が多いため
  (実測: 同義ディレクティブで日本語 157 tok vs 英語 102 tok)。本文を英語にするだけで
  毎ロードのトークンを削減できる。
- **front-matter の `description` 内の日本語トリガ例は残す** (例: 'ツンデレで話したい')。
  これは日本語発話でスキルを起動させる機能的なマッチ用キーワードで、英訳すると
  日本語ユーザーでスキルが効かなくなる。
- **詳細リファレンスは `REFERENCE.md` に分離する。** フラグの具体例 / 検証チェックリスト /
  One-Shot レシピ / バージョン履歴など「会話には不要だが参照したい」内容は本体に置かず
  `REFERENCE.md` (オンデマンド読み込み) へ。本体は「いつ・どう使うか」の判断に必要な分だけ。
- **属性ブレンドの注入ブロック内のディレクティブは重複させない。** 反復防止 / 自然さ /
  口癖・語尾の使い方は `hersona.core.attach.response_style_directive` に 1 本化済み。
  新しい指示を足すときは個別ディレクティブを増やさず既存を拡張する (毎ターンのコスト増回避)。
- **ペルソナ内容 (catchphrases / sentence_endings / tone / core_traits) は翻訳しない。**
  言語拘束であり、人格の実体そのもの。注入ブロックの言語最適化はディレクティブ文のみ対象。
- `version:` は本体と独立した SemVer (下記「スキルのバージョン管理」を参照)。

## ライセンス方針

- `attributes/` 配下のテンプレートは CC0 (public domain dedication) — `LICENSE-CC0.txt` 参照
- 商用利用可否や LLM 出力の責任は `DISCLAIMER.md` を参照

## スキルのバージョン管理

`skills/*/SKILL.md` の front-matter `version:` は、パッケージ本体
(`pyproject.toml`) とは独立した SemVer (`MAJOR.MINOR.PATCH`) で管理する。
本体リリースに追従させない (スキルは個別成果物のため)。

- 後方互換のある変更: PATCH を上げる
- スキルの入出力契約が広がる変更: MINOR を上げる
- 破壊的変更: MAJOR を上げる
- LLM 固有の試験的スキルは `-<llm>` サフィックスを付けてよい (例: `1.0.0-grok`)
- `0.x.y` は草案・実験段階を示す (`hersona-initializer` 等)

形式検証は `tests/test_skill_versions.py` で CI 化 (SemVer 正規表現チェック)。

## 質問・相談

GitHub Issue で。ラベル `question` を付けてください。
