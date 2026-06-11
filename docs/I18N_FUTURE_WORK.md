# i18n 今後の任意作業 計画 (Phase 6+)

> ステータス: **全ワークストリーム完了** ／ 前提: Phase 0–5 は main にマージ済み (#28 / #41 / #43)。
> 本書は [`I18N_DESIGN.md`](./I18N_DESIGN.md) の「今後 (任意・スコープ外)」を実装可能な
> タスクに展開したもの。W1 Step 1 = #49、W1 Step 2 = #50、W2/W3 = 本書更新と同一 PR。

## 最終サマリ (W1–W3 完了時点)

| レイヤ | 英語対応 | 補足 |
|---|---|---|
| UI 文言 / メタデータ / 診断クイズ表示 | ✅ | `--lang en` (既定) / `--lang ja` |
| speech (口調) コンテンツ | ✅ | `content_lang: en` の 5 種 (formal/casual/blunt/southern_us/british) |
| personality / archetype 等のコンテンツ | ✅ (W1) | `content_i18n.en` に英語版 catchphrases/tone/core_traits (23 属性) |
| 診断クイズの推薦対象 | ✅ (W2) | en 表示言語では `recommend_quiz.en.yaml` が英語 speech へ導線 |
| ja データの配布分離 (W3) | 評価済 | 同梱維持で確定 (削減 ~10% で分離に値しない) |

### 中核的な不整合 (W1 の動機)

`content_language(attributes)` は **speech 属性の `content_lang` のみ**を見る
([`hersona/core/intensity.py`](../hersona/core/intensity.py))。そのため:

```
$ hersona blend southern_us_en tsundere
… Respond in English (this persona's content language is 'en').   ← 応答は英語指示
…
catchphrases:
- べ、別に……                                                      ← だが性格の口癖は日本語
```

応答言語指示は英語なのに、注入される `tsundere` の口癖・トーンが日本語のまま注入される。
LLM は概ね英語に従うが、**コンテンツの一貫性が崩れる**。これが最大の残課題。

---

## W1: personality / archetype コンテンツの言語認識化 ★最優先

英語ペルソナの**全コンテンツ**(性格の口癖・トーン含む)を英語で一貫させる。

### 対象
personality 20 + archetype 9 = **29 属性**の `catchphrases` / `tone` / `core_traits`
(visual / hobby は発話コンテンツをほぼ持たないため対象外、要確認)。

### 設計判断
- 性格の口癖は**翻訳ではなくネイティブに作り直す**。
  例: tsundere の英語口癖 = "It's not like I like you or anything!" / "D-don't get the wrong idea."
- メタデータの `i18n.<lang>` (表示名・説明) とは**別軸**。あちらは「同一内容の翻訳」、
  こちらは「言語ごとに別個に書き起こすコンテンツ」。混同しないこと。

### アプローチ (推奨: 段階導入)

**Step 1 — 暫定: 言語不一致コンテンツの抑制 (低コスト・即効) ✅ 実装済**
`render_blend` で、ペルソナの実効 `content_lang` (= speech 由来) と異なる言語の
personality/archetype の `catchphrases` を**注入から除外**し、
代わりに「Express those traits through catchphrases generated natively in {lang}」の
指示行 (`_native_catchphrase_directive`) に置き換える。
- 既存データ不変で不整合を解消。英語口癖は LLM 生成に委ねる。
- 実装: `hersona/core/attach.py` の `_render_prompt`。`_attr_content_lang()` で各属性の
  言語を判定し、人格言語に一致する属性の catchphrases のみ採用。
- tone / core_traits は解釈ガイダンスのため Step 1 では除外せず保持 (Step 2 で en 化)。
- テスト: `tests/test_attach.py` (英語ペルソナで ja 口癖除外 + 指示行 / 純 ja は不変)。

**Step 2 — 本格: 多言語コンテンツの保持 ✅ 実装済**
schema に `content_i18n.<lang>.{catchphrases,tone,core_traits}` を新設 (メタ用 `i18n.<lang>`
とは別キーで衝突回避)。BASE (トップレベル) は属性の `content_lang` (既定 ja)、英語版を
`content_i18n.en` に保持する。
- `resolve_content_field(attr, key, lang)` (intensity.py) が、要求 lang と属性の BASE 言語を
  比較し、一致なら BASE を、異なれば `content_i18n.<lang>` を返す (無ければ非ネイティブ印)。
- `render_blend` は core_traits / catchphrases / tone を解決後コンテンツで組み立てる
  (`_resolve_merge` / `_resolve_tones`)。ネイティブ版が無い属性のみ除外 + 生成指示。
- **言語拘束コンテンツを持つ 23 属性**に英語版を投入: personality 11 / archetype 2 /
  hobby 5 / visual 5 (`scripts/_oneoff/add_en_content.py`)。
- 注: intensity は従来どおり speech カテゴリのみ採点 (en speech の口癖は元から `catchphrases`
  に格納されネイティブ判定。personality 口癖は採点対象外という既存方針を維持)。サマリは
  表示名 (`resolve_meta`) ベースのため変更不要。

### 影響範囲 (実績)
- `schema/attribute.schema.json` (`content_i18n` 定義)
- `hersona/core/intensity.py` (`resolve_content_field`)
- `hersona/core/attach.py` (`render_blend` のコンテンツ解決)
- `hersona/core/authoring.py` / `scripts/migrate_i18n.py` (FIELD_ORDER に `content_i18n`)
- 23 属性 YAML への `content_i18n.en` 追記
- `site/data.json` は不変 (build_site の出力フィールドに content_i18n を含めず)

### 受け入れ条件 (達成)
- `hersona blend <en_speech> tsundere` の注入ブロックに**日本語の口癖が現れず**、英語の
  core_traits / catchphrases / tone が出る。除外が無いため生成指示も出ない。
- en コンテンツを持たない属性 (将来/ユーザー属性) では従来どおり除外 + 生成指示。
- ja ペルソナは完全不変 (後方互換)。

### 工数: 大 (Step 1 小 / Step 2 大、データ作業中心)。**完了**。

---

## W2: 診断クイズへの英語 speech 導線 ✅ 実装済

`hersona recommend` で英語ペルソナを提案できるようにする。

### 実装 (ロケール別クイズ)
設計書のロケール分離方針 (§2.2) と整合する **(b) 言語別クイズ**を採用:
- **`recommend_quiz.en.yaml`** を `scripts/_oneoff/gen_quiz_en.py` で BASE クイズから導出
  (ベース変更時は再生成)。差分:
  - 全設問から **ja speech への weight を除去** (en ペルソナに ja 話法を混ぜない)
  - `speech` 設問の選択肢を英語 speech 5 種 (formal/casual/blunt/southern_us/british) に差替
  - 除去で空になる選択肢を補填: interaction「Old-fashioned and formal」→ `formal_en`、
    cultural「Rooted in Kyoto culture」→「Rooted in British tradition」(`british_en`)
  - **質問 ID はベースと同一** (`--answers` キー互換)
- `recommend.quiz_path_for(lang)` / `quiz_for_lang(lang)` を新設。CLI (`_cmd_recommend` /
  対話クイズ) が表示言語のクイズを使う。**core の `recommend()` の既定 (`DEFAULT_QUIZ` = ja)
  は不変** — ライブラリ利用は後方互換。
  - 代替案 (a): 既存クイズに言語選択設問を 1 問足す方式は、加算 top-1 モデルでは
    言語フィルタを表現しにくい (en/ja speech が同時加算されうる) ため不採用。

### 受け入れ条件 (達成)
- `hersona recommend --answers speech=4` (en 既定) が `british_en` を含む人格を提案。
  `--apply` で英語の口癖が注入される (W1 と合わせ英語で一貫)。
- `--lang ja` は従来の ja クイズのまま。既存 `--answers` キーの互換は維持。

### 工数: 中。**完了**。

---

## W3: ja データの optional extra 分離 (残課題 6) ✅ 評価完了 — 同梱維持で確定

`pip install hersona[ja]` で日本語ロケール/コンテンツを任意依存にする案。

### 計測結果 (2026-06-11)

| 資産 | サイズ |
|---|---|
| `locales/ja.yaml` | 4.5 KB |
| 属性 YAML 内 `i18n.ja` ブロック (64 files) | 11.0 KB |
| quiz 内 `i18n.ja` | 4.3 KB |
| **分離可能な ja 資産合計** | **19.9 KB** |
| パッケージ総計 (attributes + quiz + locales + code) | 203.3 KB |
| 分離による削減率 | **9.8%** |

注: BASE の ja コンテンツ (catchphrases / tone 等) は ja ペルソナの本体データであり
分離対象外 (分離すると ja ペルソナ自体が成立しない)。上記は純粋に切り出せる資産のみ。

### 決定
- **同梱のまま維持で確定**。約 20 KB / 10% の削減のために optional extra・配布マトリクス・
  フォールバック分岐を増やす価値はない (設計書 §6 残課題 6 を解決)。
- **再検討トリガー**: 分離可能な ja 資産が 1 MB を超える、もしくは配布パッケージが
  10 MB を超えてサイズ起因の問題が報告された場合。

### 工数: 評価のみ (実装なし)。**クローズ**。

---

## 横断的な留意点

- **後方互換が最優先**: ja ペルソナ・既存 `--answers` キー・`site/data.json` の
  既存属性表現を壊さない。新フィールドはすべて任意・未指定時 ja フォールバック。
- **検証の定石** (各 PR 共通):
  - `python -m pytest -q` 全パス
  - `ruff check hersona/ tests/`
  - `python scripts/validate.py` (エラー 0)
  - `python scripts/build_site.py --check` (data.json 整合)
- **ドキュメント同期**: 着手・完了時に [`I18N_DESIGN.md`](./I18N_DESIGN.md) のチェックリストと
  `CHANGELOG.md`、README (en/ja) の件数・フィールド表を更新する。
- **推奨着手順**: W1 Step 1 → W2 → W1 Step 2 → (必要なら) W3。
  W1 Step 1 で不整合を解消してから W2 を入れると、推薦された英語ペルソナが
  最初から一貫した英語コンテンツになる。
