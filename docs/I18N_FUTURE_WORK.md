# i18n 今後の任意作業 計画 (Phase 6+)

> ステータス: **計画 (未着手)** ／ 前提: Phase 0–5 は main にマージ済み (#28 / #41 / #43)。
> 本書は [`I18N_DESIGN.md`](./I18N_DESIGN.md) の「今後 (任意・スコープ外)」を実装可能な
> タスクに展開したもの。各ワークストリームは独立しており、優先度順に着手してよい。

## 現状サマリ (Phase 5 完了時点)

英語ペルソナは **speech レイヤのみ**英語化されている。

| レイヤ | 英語対応 | 補足 |
|---|---|---|
| UI 文言 / メタデータ / 診断クイズ表示 | ✅ | `--lang en` (既定) / `--lang ja` |
| speech (口調) コンテンツ | ✅ | `content_lang: en` の 5 種 (formal/casual/blunt/southern_us/british) |
| personality / archetype コンテンツ | ❌ | `catchphrases` / `tone` / `core_traits` が**日本語固定**、`content_lang` 無し |
| 診断クイズの推薦対象 | ❌ (ja のみ) | 英語 speech に weight する設問が無い |

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

**Step 1 — 暫定: 言語不一致コンテンツの抑制 (低コスト・即効)**
`render_blend` で、ペルソナの実効 `content_lang` (= speech 由来) と異なる言語の
personality/archetype コンテンツ (`catchphrases` 等) を**注入から除外**し、
代わりに「Generate catchphrases natively in {lang}」の指示に置き換える。
- 既存データ不変で不整合を解消できる。英語口癖は LLM 生成に委ねる。
- `content_language` を speech だけでなく全 speech-bearing 属性に拡張する判定も検討。

**Step 2 — 本格: 多言語コンテンツの保持**
schema に言語別コンテンツ構造を導入する。`i18n.<lang>` はメタ専用なので衝突を避け、
別キー (案: `content_i18n.<lang>.{catchphrases,tone,core_traits}`) を新設。
- BASE は現状の `ja` コンテンツ、`content_i18n.en` に英語版を追加。
- `content_language(attrs)` が解決した lang に応じて catchphrases/tone/core_traits を選択。
- 注入・intensity・サマリすべてが選択後コンテンツを使う。

### 影響範囲
- `schema/attribute.schema.json` (新キー定義)
- `hersona/core/attach.py` (`render_blend` のコンテンツ選択)
- `hersona/core/intensity.py` (`_collect_speech_signals` 相当を personality 口癖にも適用?)
- `scripts/build_site.py` / `site/data.json` (新フィールド反映)
- 29 属性 YAML への英語コンテンツ追記 (Step 2、データ作業が大半)

### 受け入れ条件
- `hersona blend <en_speech> tsundere` の注入ブロックに**日本語の口癖が現れない**。
- 英語ペルソナの intensity が personality 由来の英語口癖も拾う (Step 2)。
- ja ペルソナは完全不変 (後方互換)。

### 工数: 大 (Step 1 小 / Step 2 大、データ作業中心)。Step 1 を先行リリース推奨。

---

## W2: 診断クイズへの英語 speech 導線

`hersona recommend` で英語ペルソナを提案できるようにする。

### 現状
クイズ ([`hersona/data/quiz/recommend_quiz.yaml`](../hersona/data/quiz/recommend_quiz.yaml))
の `weights` は日本語 speech のみを参照。`--lang en` でも UI が英語になるだけで、
推薦される speech は ja 5 種に到達できない。

### アプローチ (推奨: ロケール別クイズ)
設計書のロケール分離方針 (§2.2) と整合する **(b) 言語別クイズ**を採用:
- `recommend_quiz.en.yaml` を新設し、英語 speech 5 種に weight する設問を含める。
  英語 speech は 5 種のみなので **register/dialect 選択 1 問**で十分:
  - "How should she sound?" → Formal / Casual / Blunt / Southern / British
- `--lang en` 時は en クイズ、`--lang ja` 時は現行 ja クイズをロード。
  - 代替案 (a): 既存クイズに言語選択設問を 1 問足す方式は、加算 top-1 モデルでは
    言語フィルタを表現しにくい (en/ja speech が同時加算されうる) ため非推奨。

### 影響範囲
- `hersona/data/quiz/recommend_quiz.en.yaml` (新規)
- `hersona/core/recommend.py` (lang に応じたクイズファイル選択)
- テスト (en クイズが英語 speech を推薦に出すこと、全 weight キーが実在属性であること)

### 受け入れ条件
- `hersona recommend --lang en --answers sound=4` 等が `british_en` 等を含む人格を提案。
- 既存 `--answers` キー (`distance` 等) の互換は維持 (ja クイズは不変)。

### 工数: 中。W1 Step 1 の後に着手すると、提案された英語ペルソナの口癖も英語で一貫する。

---

## W3: ja データの optional extra 分離 (残課題 6)

`pip install hersona[ja]` で日本語ロケール/コンテンツを任意依存にする案。

### 方針
- **当面は同梱のまま**。データ量が配布上問題化した時点で着手 (設計書 §6 残課題 6 の確認事項)。
- 着手前に計測: `locales/ja.*` + 各 YAML の `i18n.ja` + ja コンテンツの総バイト数を出し、
  分離の損益分岐 (パッケージサイズ削減量 vs ビルド/配布の複雑化) を評価する。
- 分離する場合: ja を `[project.optional-dependencies]` の extra データとして切り出し、
  未インストール時は en へフォールバック (既存のフォールバック機構を流用)。

### 工数: 小〜中 / 優先度: 低 (トリガー待ち)。

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
