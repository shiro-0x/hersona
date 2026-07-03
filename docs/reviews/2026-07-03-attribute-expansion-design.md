# 詳細設計書: archetype / visual / hobby 属性拡張

- 版: 2026-07-03 draft
- 対象カテゴリ: archetype (9) / visual (5) / hobby (5)
- 候補カタログ: [expansion-backlog](./2026-07-03-attribute-expansion-backlog.md)(約170候補)
- 位置づけ: 「進め方」の実装設計。**本書合意後に着手**。CONTRIBUTING「PR 1件=1属性が
  基本、複数追加は事前合意」の *事前合意* を本書が兼ねる。

---

## 1. 目的とゴール

- 手薄な 3 カテゴリ(archetype/visual/hobby)を拡充し、ブレンドの表現力を上げる。
- 品質を落とさず(既存フォーマット・検証ゲート・ドキュメント同期を厳守)、
  **反復可能な手順**でバッチ投入する。
- 非目標: personality/speech の拡張、schema 変更、既存属性の意味変更。

### 完了条件(全体)
- [ ] 採用候補すべてが `attributes/<cat>/<name>.yaml` として存在し `validate.py` 緑。
- [ ] `tests/catalog_counts.py` と全ドキュメントの件数が一致、`pytest` 緑。
- [ ] `docs/app/data.json` 再生成済み(`build_site.py --check` 緑)。
- [ ] README EN/JA・SKILL.md・CHANGELOG 同期済み。

---

## 2. スコープ確定(要決定 → 本書で確定させる)

| 決定事項 | 選択肢 | 既定(推奨) |
|---|---|---|
| 採用範囲 | ◎のみ / ◎+○ / ◎+○+△ | **◎+○**(定番+有力、△は第3弾で精査) |
| カテゴリ配分 | 均等 / archetype 厚め | archetype 厚め(役割の需要が高い) |
| 投入単位 | 一括 / バッチ | **バッチ(1 PR = 1カテゴリ×1弾)** |
| 命名 | 正式 / 短縮 | §4 の命名規則に従う |

> **確定値はレビューで埋める**。以下の設計は「◎+○ をバッチ投入」を前提に記述。

### バッチ分割(既定案)

| Batch | カテゴリ | 内容 | 追加数(概算) | 到達合計 |
|---|---|---|---|---|
| B1 | archetype | ◎5 (senpai, kouhai, ojou_sama, student_council_president, detective) | +5 | 206 |
| B2 | visual | ◎5 (twintails, ponytail, heterochromia, tall, kimono) | +5 | 211 |
| B3 | hobby | ◎5 (art, photography, dance, gardening, fortune_telling) | +5 | 216 |
| B4 | archetype | ○ 群 | +~20 | ~236 |
| B5 | visual | ○ 群 | +~25 | ~261 |
| B6 | hobby | ○ 群 | +~20 | ~281 |
| B7+ | 全 | △ 精査投入 | 残り | ~370 |

各 Batch は独立 PR。**1 PR で件数契約を 1 回だけ更新**するのでバッチ境界=件数更新点。

---

## 3. 属性 YAML オーサリング仕様

### 3.1 共通ルール
- `attribute_category` はディレクトリと一致(`test_path_category_matches_attribute_category` が強制)。
- `attribute_name` == ファイル名(拡張子除く)、snake_case `^[a-z][a-z0-9_]*$`。
- **固有名詞・特定作品名を含めない**(examples/catchphrases 含む)。
- BASE(トップレベル)は日本語コンテンツ、`content_i18n.en` に英語ネイティブ版を必ず用意
  (既存 archetype/visual/hobby は全て en を持つ。注入言語切替のため)。
- `examples` は会話形式 2–3 個(`[user]` / `[assistant]`)。catchphrases の丸写し禁止
  (直近の dedup 方針と整合)。
- ペルソナコンテンツ(core_traits/catchphrases/tone)は**翻訳しない**。ja と en を
  それぞれネイティブに書く。

### 3.2 カテゴリ別 必須/推奨フィールド

**archetype**(`weight_dimension: none` / `typical_value_range: 0.0-0.0` が既存慣例):
```yaml
attribute_category: archetype
attribute_name: <name>
display_name: <English display>
weight_dimension: none
typical_value_range: 0.0-0.0
description: <English 1-2 sentences, role/relationship>
examples:            # 会話形式 2-3
- |-
  [user] ...
  [assistant] ...
compatible_archetypes: [<names>]   # 実在属性のみ
conflicts_with: [<names>]          # 実在属性のみ
has_catchphrase: true
variant: ''
tags: [<ja tags>]
core_traits: [<ja 3-7>]
catchphrases: [<ja 1-15, {phrase, when} 可>]
tone: <ja 1 行>
content_i18n:
  en:
    core_traits: [<en 3-7>]
    catchphrases: [<en>]
    tone: <en 1 行>
i18n:
  ja:
    display_name: <日本語表示名>
    description: <日本語説明>
```

**visual**(`weight_dimension: mild` 目安、`image_prompt_tags` 必須):
- archetype と同形 + `image_prompt_tags: [<en tags>]`(画像生成用、language-neutral)。
- visual の core_traits は「見た目が与える印象+仕草」を書く(既存 glasses/petite に倣う)。

**hobby**(`weight_dimension: moderate` 目安):
- archetype と同形。core_traits は「その趣味に伴う気質・振る舞い」。

### 3.3 命名規則(§2 の確定用)
- 冗長名は短縮を許容。確定案:
  - `student_council_president` → **`seitokaicho`**(既存 speech の日本語ローマ字命名
    `kansai_ben`/`onee_kotoba` と整合)。
  - `flower_arrangement` → **`kado`**、`tea_ceremony` → **`sado`**、`martial_arts` → **`budo`**。
  - それ以外は英語一般名(`detective`, `twintails`, `photography`)。
- 判断基準: 日本文化固有語はローマ字、汎用概念は英語。

---

## 4. 関係性(compatible/conflicts)の配線ルール

`scripts/validate.py::_report_relationship_consistency` の挙動:
- **conflict は core 側で対称化済み**。片側宣言でも動くが、**両側に書くのを推奨**
  (`b9603cf` の zh/ko バックフィル前例と整合)。
- **compatible の非対称は設計上許容**(警告のみ、エラーにならない)。
- 参照先は**実在する attribute_name のみ**(存在しない名を書くと後続の破綻源)。

配線方針:
- 新規 archetype は既存 personality/speech/archetype と相性を張る(例: `senpai`↔`kouhai`
  を相互 compatible、`ojou_sama`↔`delinquent` を相互 conflict)。
- 同一バッチ内で相互参照する属性は**同じ PR で追加**(参照切れ回避)。
- 迷ったら空配列可(`conflicts_with: []`)。過剰結線より安全。

---

## 5. 件数契約(count contract)の更新手順

**単一の真実源**は `tests/catalog_counts.py`。ここを起点に同期する。

### 5.1 必須更新(コード)
1. `tests/catalog_counts.py`
   - `TOTAL_PUBLIC_ATTRIBUTES`(現 201)
   - `PUBLIC_CATEGORY_COUNTS`(該当カテゴリの数)
   - → `test_attributes.py` / `test_catalog_counts.py` / `test_cli.py` /
     `test_compatibility.py` / `test_attach.py` / `test_mcp.py` は本モジュール参照なので
     **手修正不要**(自動追随)。

### 5.2 必須更新(ドキュメント、数値がハードコード)
2. `README.md`
   - L5 冒頭サマリ "**201 reusable...**"
   - L25-32 カテゴリ別内訳(`Archetype (9)` 等)
   - L102-115 "What it covers now" テーブル + "Total breakdown: personality 42 + speech 140 + archetype 9 + visual 5 + hobby 5 = 201"
   - L368 付近 ディレクトリツリー `archetype/ (9)`
3. `README.ja.md` — 同箇所の日本語版(L5, L24-30, L106-117, ツリー)
4. `skills/hersona/SKILL.md`
   - L33-37 "There are currently **201 attributes**" ブロック
   - L137 "full 201-attribute tree"
   - L250 "Attribute Taxonomy (201 attrs)" 見出し + L259-261 カテゴリ表
   - L394 版フッタ "201-attribute / speech-140 catalog state"
   - front-matter `version:` を SemVer で上げる(データ拡張は minor 相当)
5. `CLAUDE.md` — L19 "categories (currently 201 / 5 categories)"
6. `CONTRIBUTING.md` — L91 "現在 201 / 5 カテゴリ"
7. `CHANGELOG.md` — `## [Unreleased]` に Added エントリ

> 実装時は各弾で `grep -rn '\b<oldtotal>\b'` と各カテゴリ旧数を検索して漏れを潰す。

### 5.3 サイトデータ
8. `python scripts/build_site.py` で `docs/app/data.json` 再生成(CI `--check` ゲート対象)。

---

## 6. 検証ゲート(各 PR 必須)

```bash
uv run python scripts/validate.py          # スキーマ + 参照整合 (エラー0)
uv run python scripts/build_site.py --check # data.json 最新性
uv run python -m pytest -q                  # 件数契約含む全テスト
uv run ruff check hersona/ scripts/ tests/  # lint (今回コード変更なしでも走らせる)
```

- `validate.py` の "compatible 非対称 N件" は既存warning(設計上許容)なので無視可。
- 新規属性は原則コード変更を伴わないため、`pytest` の主眼は件数契約と
  スキーマ整合(`test_attributes.py` のカテゴリ別カウント)。

---

## 7. PR 構成・コミット規約

- ブランチ: `claude/latest-files-review-rhxd5g`(継続)。マージ済みなら
  最新 main から同名で切り直す(タスク規約)。
- 1 Batch = 1 PR。PR タイトル例: `feat(attributes): add 5 archetype roles (senpai, kouhai, ...)`。
- コミット粒度: **1 コミット = 1 カテゴリバッチ**(YAML群) + **1 コミット = ドキュメント/件数同期**。
  CONTRIBUTING の「1PR=1属性」は少数手動追加時の原則で、合意済みバッチは束ねてよい
  (本書が合意)。
- PR 本文はリポジトリの `.github/PULL_REQUEST_TEMPLATE.md` のセクション構成を流用。

---

## 8. Definition of Done(バッチ単位チェックリスト)

- [ ] 追加 YAML すべて schema 準拠(`validate.py` エラー0)
- [ ] `content_i18n.en` を全属性に用意
- [ ] examples は会話形式・catchphrase 丸写しなし・固有名詞なし
- [ ] compatible/conflicts の参照先が実在(バッチ内相互参照は同PR)
- [ ] `catalog_counts.py` 更新 → `pytest` 緑
- [ ] README EN/JA・SKILL.md(+version)・CLAUDE.md・CONTRIBUTING の件数同期
- [ ] `build_site.py` 再生成 → `--check` 緑
- [ ] CHANGELOG `[Unreleased]` に Added
- [ ] `ruff` 緑

---

## 9. リスクと対策

| リスク | 影響 | 対策 |
|---|---|---|
| 件数のドキュメント漏れ | pytest は緑でも README がずれる | §5.2 の grep 漏れ潰しを DoD に含める |
| 参照切れ(存在しない属性名) | 後続バッチで破綻 | バッチ内相互参照は同PR、迷えば空配列 |
| archetype と speech の意味衝突 | ユーザ混乱(butler など) | description で「役割 vs 口調」を明示、tags で区別 |
| en コンテンツの機械翻訳臭 | 個性の質低下 | en はネイティブ発想で起草(直訳しない) |
| 大量追加で注入が肥大 | ブレンド時のトークン増 | 1 属性 = 通常 1 カテゴリ 1 個の運用は不変(合算は利用者責任)。設計影響なし |
| SKILL.md 肥大 | 毎ターンコスト増 | 件数と代表例のみ更新、個別属性は列挙しない |

---

## 10. 次アクション

1. §2 の確定(採用範囲・配分・命名)をレビューで確定。
2. 確定後、B1(archetype ◎5)から着手。DoD を満たしたら PR。
3. 各バッチのレビュー通過を待って次バッチへ(またはまとめて連続投入)。

> 決定が出れば本書 §2 の「既定」を確定値に書き換え、B1 の YAML 起草に入る。
