# hersona 国際化 (i18n) 設計書 — 英語ベース化 / 日本語の拡張言語化

> Status: **DRAFT (提案・未実装)**
> 目的: 既定言語を **英語 (en)** に切り替え、日本語 (ja) を拡張ロケールとして
> 同居させる。本書は移行方針・スキーマ変更・段階計画・リポジトリ構成の合意を取るための叩き台。

---

## 0. TL;DR (結論)

- **別リポジトリにしない。同一リポジトリ内でロケール層を足す**ことを推奨する。
  理由は §5。
- 「英語ベース化」は 2 層に分けて考える必要がある:
  - **A 層 = ツール / メタデータ** (CLI 文言・README・schema description・`display_name`・`description`・quiz)
    → **完全に英語ベース化できる。** ここが本タスクの主戦場。
  - **B 層 = 人格コンテンツ本体** (`catchphrases` / `sentence_endings` / `second_person` /
    `tone` / `examples` / `core_traits`)
    → **言語に束縛される。** とくに `speech/` の多く (keigo, kansai_ben, washi,
    boku_girl, ore_boy, kyoto_ben) は **日本語そのものが属性の中身**であり、
    「英語ベースに翻訳」は意味をなさない。B 層は「翻訳」ではなく
    **`lang` タグ付け + 言語別コンテンツの追加**として扱う。
- 後方互換を保つ段階移行 (Phase 0〜5)。既存の `*_ja` / `*_en` は当面フォールバックとして残す。

---

## 1. 現状の言語依存マップ

| 区分 | 対象 | 現状 | 英語ベース化の難度 |
|---|---|---|---|
| A: UI | CLI 出力文字列 (`app.py` 等) | 日本語ハードコード | 低 (文言カタログ化) |
| A: Docs | README / ROADMAP / docs/* | 日本語 | 低〜中 |
| A: Schema | `schema/attribute.schema.json` の `description` | 日本語 | 低 |
| A: Meta | `display_name_ja/en`, `description_ja/en` | 二言語ペア (済) | 低 (基準を en に) |
| A: Quiz | `recommend_quiz.yaml` の `prompt` / `label` | 日本語 | 中 (ロケール分離) |
| B: Content | `core_traits` | 日本語 | 中 (personality は翻訳可) |
| B: Content | `catchphrases` / `sentence_endings` / `second_person` / `tone` / `examples` | 日本語 | **高 (言語束縛)** |
| B: Logic | `intensity.py` (語尾・句読点で採点) | 日本語前提 | **高 (言語認識化)** |
| B: Attr | `speech/*` の方言・敬語・一人称 | 日本語固有 | **本質的に ja 固有** |

**設計上の核心:** 注入プロンプト (`render_blend` の出力) は、AI が**応答する言語**と
一致していなければ機能しない。日本語の語尾・口癖を英語応答に混ぜても破綻する。
したがって B 層は「ベース言語を 1 つに固定」できず、**コンテンツに `lang` を持たせ、
出力言語に合わせて選択する**設計が必要。

---

## 2. ロケールモデル (スキーマ設計)

### 2.1 現状の弱点
`display_name_ja` / `display_name_en` のような **suffix ペア方式**は
2 言語固定で N 言語に伸びない。かつ 2 フィールドしかカバーしていない。

### 2.2 推奨: メタデータとコンテンツを分離し、メタデータは locale サブツリーへ

```yaml
# 言語中立 (不変) ----------------------------------------
attribute_name: keigo            # ASCII id。ロケール非依存。変更しない
attribute_category: speech
weight_dimension: strong
typical_value_range: 0.7-1.0
compatible_archetypes: [mentor, shrine_maiden, robot_android]
conflicts_with: [kansai_ben, ore_boy, boku_girl, genki]

# メタデータ: BASE = 英語 -------------------------------
display_name: Keigo              # 基準言語 (en)
description: Accurate, consistent use of sonkeigo, kenjogo, and teineigo...

# 人格コンテンツ: lang タグ付き --------------------------
content:
  lang: ja                       # この payload が書かれている言語
  sentence_endings: ["〜です", "〜ございます"]
  second_person: "..."
  catchphrases: ["..."]
  tone: "ですます/ございますで統一。崩れる瞬間に感情ピーク。"
  examples: ["お越しいただき、ありがとうございます", ...]

# 拡張ロケール: 翻訳されるのはメタデータのみ ---------------
i18n:
  ja:
    display_name: 敬語
    description: 尊敬語・謙譲語・丁寧語を正確・統一的に使用...
```

- **`attribute_name`** は ASCII の不変 ID。UI 言語に関わらずキーとして使う (既存の安定 API)。
- **メタデータ** (`display_name` / `description`) は BASE=en。`i18n.<lang>` で上書き翻訳。
- **`content`** は `lang` 付きの単一 payload。`speech/*` は `lang: ja` のまま。
- 将来、言語中立カテゴリ (personality / archetype / visual / hobby) は
  `content` を配列化して **言語別 payload** を持てる:
  ```yaml
  content:
    - lang: ja
      core_traits: [素直になれない, 照れ隠し, ...]
    - lang: en
      core_traits: [can't be honest, hides embarrassment, ...]
  ```

### 2.3 後方互換
- スキーマは移行期間中 **両形式を受理** (oneOf)。`display_name_ja/en` が在れば
  `display_name` + `i18n.ja.display_name` に自動マッピングして読む。
- `scripts/migrate_i18n.py` (新規) で全 YAML を新形式へ一括変換。`--dry-run` 対応。

---

## 3. ランタイム / API 設計

### 3.1 言語選択
優先順: `--lang <code>` フラグ > `HERSONA_LANG` 環境変数 > 既定 `en`。

```
hersona list --lang ja
HERSONA_LANG=ja hersona show keigo
```

### 3.2 ロケール解決 (`hersona/core/i18n.py` 新規)
- `resolve_meta(attr, field, lang)` : `i18n.<lang>.<field>` → BASE → 空、の順でフォールバック。
- `tr(key, lang)` : CLI / quiz 文言の翻訳カタログ参照。
- 文言カタログは `hersona/locales/<lang>.yaml` (例: `en.yaml`, `ja.yaml`)。

### 3.3 CLI 文言の外部化
`app.py` 等の日本語ハードコード文字列を `tr("cmd.list.header", lang)` 形式に置換。
カタログ初版は en / ja の 2 ファイル。

### 3.4 render_blend と出力言語
- `render_blend(..., lang="en")` : 注入ブロックの**見出し**を `lang` で出す。
- **payload は `content.lang` のものを使う** (見出し言語と payload 言語は独立)。
- payload 言語と要求言語が食い違う場合は注入ブロック冒頭に
  `Respond in Japanese (this persona's speech patterns are Japanese).` 等の
  **言語指示行**を自動付与する (英語 UI から日本語ペルソナを使う典型ケースを救済)。

### 3.5 intensity の言語認識化
- `IntensityReport` に `lang` を追加。
- 文分割・語尾照合は `content.lang` に応じて切替 (ja は現行ロジック、en は
  別トークナイザ or 当面 skip)。
- 出力テキストの言語と `content.lang` が不一致なら測定 skip + 警告。

---

## 4. 段階計画 (Phases)

各 Phase は独立 PR。後方互換を壊さない順に積む。

| Phase | 内容 | 範囲 | 規模 |
|---|---|---|---|
| **0** | 言語プラミング | `core/i18n.py`, `--lang`/`HERSONA_LANG`, 既定 en | S |
| **1** | A: UI 英語ベース化 | CLI 文言カタログ化 (`locales/en,ja`)、schema description を en 化、`README.md`=en / `README.ja.md`=ja に分離 | M |
| **2** | A: メタデータ英語ベース化 | `display_name`/`description` を BASE=en に、ja を `i18n.ja` へ。`migrate_i18n.py` + schema を oneOf 後方互換に | M |
| **3** | A: Quiz 英語ベース化 | quiz の prompt/label をロケール分離 (`recommend_quiz.<lang>.yaml` or i18n ブロック) | M |
| **4** | B: コンテンツの lang タグ付け | `content.lang` 導入、`speech/*` を ja 明示、intensity を言語認識化 | M〜L |
| **5** | B: 英語ペルソナ拡充 (任意・最大) | 言語中立カテゴリの en `content` 追加。英語版「話し方」属性 (formal/casual/southern_us 等) を**別属性セット**として新設 | L |

- **Phase 1〜3 で「英語ベース・日本語拡張」というユーザー要望はほぼ達成**できる
  (UI と見える情報がすべて英語起点、`--lang ja` で日本語に戻せる)。
- **Phase 4〜5 は「英語で喋るペルソナも作れる」段階**で、要件次第。
  speech の方言・敬語は日本語固有のため、英語側は別系統の属性として設計する。

### 推奨スコープ
まず **Phase 0〜2** を 1 マイルストーンとして実施 (UI + メタデータが英語起点になる)。
Phase 4〜5 は「英語出力ペルソナの需要」が確認できてから着手を推奨。

---

## 5. リポジトリ構成: 同一 vs 別

**結論: 同一リポジトリ + ロケール層。別リポジトリ / フォークは非推奨。**

| 観点 | 同一リポジトリ (推奨) | 別リポジトリ / フォーク |
|---|---|---|
| 属性データの単一ソース | ◎ 1 か所 | ✗ 二重管理・乖離不可避 |
| schema / CLI / tests の結合 | ◎ そのまま共有 | ✗ 全コピー、追従地獄 |
| Git 履歴・Issue | ◎ 連続 | △ 分断 |
| i18n は横断的関心事 | ◎ ロケール層で吸収 | ✗ 言語ごとに実装が分岐 |
| 配布 (PyPI 等) | ◎ 単一パッケージ + locale data | △ パッケージ名衝突 / 重複 |
| 別ブランディングしたい場合 | locale/サブパッケージで分離可 | 唯一の利点だが時期尚早 |

- hersona はデータ・スキーマ・CLI・テストが密結合。フォークは即日から
  二重メンテに陥る。
- i18n は「言語を増やす」横断機能であり、**コードとデータを 1 つに保ったまま
  ロケール層を足す**のが定石。
- 将来「英語圏向けに別名で出す」需要が出ても、まずは monorepo 内の
  サブパッケージ / 別 locale で分けるのが先。リポジトリ分割はその後でも遅くない。

---

## 6. 未決事項 (要合意)

1. **B 層のスコープ**: 今回は A 層 (UI/メタデータ) だけで止めるか、英語出力
   ペルソナ (Phase 4〜5) まで行くか。← 設計全体の規模を決める最大の分岐。
2. **英語版 speech 属性**を作るか (formal/casual/regional 等)。作るなら命名規約と
   日本語 speech との関係 (排他? 併存?) を定義する必要。
3. **README の運用**: `README.md` を en 化し `README.ja.md` を別立てにするか、
   1 ファイル併記か。
4. **locale 形式**: per-field の `i18n.<lang>` ブロックか、`locales/<lang>/` の
   外部ファイルか。属性数 59 規模なら前者 (YAML 内同居) が編集しやすい。
5. **ja を「拡張」にする度合い**: ja を別パッケージ extra (`pip install hersona[ja]`)
   にするほど分離するか、同梱のままにするか。

---

## 7. 次アクション

- [ ] §6 の 1 (B 層スコープ) と 5 (ja 分離度) を合意
- [ ] Phase 0 の `core/i18n.py` + `--lang` プラミングを PR 化
- [ ] schema を oneOf 後方互換化 + `migrate_i18n.py` の雛形作成
