# hersona 国際化 (i18n) 設計書 — 英語ベース化 / 日本語の拡張言語化

> Status: **DRAFT (合意済みスコープ: Phase 0〜5 / 英語ペルソナまで)**
> 目的: 既定言語を **英語 (en)** に切り替え、日本語 (ja) を拡張ロケールとして
> 同居させる。**英語で喋るペルソナの生成 (B 層) までを最終ゴールとする**ことが合意済み。
> 本書は移行方針・スキーマ変更・段階計画・リポジトリ構成の設計を定義する。

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

- **Phase 1〜3 で「英語ベース・日本語拡張」という UI/メタデータ要件を達成**
  (見える情報がすべて英語起点、`--lang ja` で日本語に戻せる)。
- **Phase 4〜5 で「英語で喋るペルソナも作れる」最終ゴールに到達** (合意済みスコープ)。

### マイルストーン (合意済み: Phase 0〜5 完走)
- **M1 = Phase 0〜2** (UI + メタデータが英語起点)。早期に出荷可能な区切り。
- **M2 = Phase 3〜4** (Quiz 英語化 + コンテンツ言語認識化)。
- **M3 = Phase 5** (英語ペルソナ拡充)。§4.1 の英語 speech 設計が中核。

### 4.1 英語版 speech 属性の設計 (Phase 5 の中核)

日本語 speech (keigo / kansai_ben / washi / ...) は **言語固有**なので翻訳しない。
英語側は**英語の話法レジスタ**として**別属性セットを新設**する。命名は
衝突回避のため接尾辞でロケールを明示する (`<name>_en`) か、`variant`/`lang` で区別:

| 日本語 speech (既存・lang: ja) | 英語側の対応 (新設・lang: en) | 関係 |
|---|---|---|
| keigo (敬語) | `formal_en` (formal/polite register) | 概念的に近い別属性 |
| blunt (ぶっきらぼう) | `blunt_en` | 翻訳可能 (言語非依存度が高い) |
| kansai_ben / kyoto_ben (方言) | `southern_us_en` / `british_en` 等 | **対応せず英語独自の方言を新設** |
| washi / ore_boy / boku_girl (一人称) | (英語に一人称区別なし) | **非対応。tone/語彙で代替** |
| seductive / theatrical | `seductive_en` / `theatrical_en` | 翻訳可能 |

設計原則:
- **1:1 翻訳を強制しない。** 言語ごとに「その言語で自然な話法」を独立に定義する。
- 英語 speech は `sentence_endings` ではなく **語彙・文体・縮約 (contraction) ・
  間投詞**で特徴づける (英語は語尾活用が無いため)。schema の `sentence_endings` は
  `lang: en` では任意とし、代わりに `lexical_markers` / `register` を使う (§4.2 参照)。
- 日本語 speech と英語 speech は **`conflicts_with` で相互排他**にする
  (1 ペルソナに ja/en speech を混在させない)。

### 4.2 schema 追補 (Phase 5)
- `content[].lang` を必須化 (`en` / `ja`)。
- speech 用に言語非依存フィールド `lexical_markers` (string[], 例: "gonna", "y'all",
  "indeed") と `register` (enum: formal/neutral/casual/vulgar) を追加。
- `sentence_endings` は `lang: ja` でのみ必須、`lang: en` では任意に緩和。

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

## 6. 決定事項 / 残課題

### 決定済み
1. **B 層スコープ**: **英語ペルソナ (Phase 4〜5) まで実施**で確定。
2. **リポジトリ**: **同一リポジトリ + ロケール層**で確定 (§5)。
3. **英語版 speech**: 1:1 翻訳せず、英語独自の話法レジスタを**別属性セットで新設**
   (§4.1)。日本語 speech とは `conflicts_with` で相互排他。

### 残課題 (実装着手前に詰める)
4. **README の運用**: `README.md` を en 化し `README.ja.md` を別立て (推奨) か、1 ファイル併記か。
5. **locale 形式**: per-field の `i18n.<lang>` ブロック (推奨・YAML 内同居) か、
   `locales/<lang>/` 外部ファイルか。属性 59 規模なら前者が編集しやすい。
6. **ja の分離度**: ja を別 extra (`pip install hersona[ja]`) にするか同梱のままか
   (推奨: 当面同梱。データ量が問題化したら分離)。
7. **英語 speech の初期セット**: どのレジスタ/方言を最初に作るか
   (例: formal / casual / blunt / southern_us / british の 5 種から)。

---

## 7. 次アクション

- [x] **Phase 0**: `core/i18n.py` + `--lang`/`HERSONA_LANG` プラミング (既定 en)。
      文言カタログ `hersona/locales/{en,ja}.yaml` の初版・`resolve_lang`/`tr`/
      `resolve_meta` 実装・CLI への `--lang` 配線・`tests/test_i18n.py` (済)。
- [x] **Phase 1**: CLI 文言を `tr()` へ全面カタログ化 (`locales/{en,ja}.yaml`)、
      CLI が surface する core 例外メッセージもロケール追従、`--help`/description も
      ローカライズ、schema description を en 化、`README.md`=en / `README.ja.md`=ja に分離 (済)。
      - 対象外 (後続): 注入ブロック本文 (`render_blend`) と推薦サマリ等の人格コンテンツ
        (言語束縛 → Phase 3〜5)、`compatibility._main` / `scripts/validate.py` の開発診断出力。
- [x] **Phase 2**: `display_name`/`description` を BASE=en 化 + `i18n.ja` へ移行 (全 59 属性)。
      `scripts/migrate_i18n.py` (一括変換・`--dry-run`・冪等) + schema を oneOf 後方互換化。
      `build_attribute`/`show`/`recommend`/`build_site` を新形式対応に更新 (済)。
      - locale 形式は **YAML 内 `i18n.<lang>` ブロック**で確定 (§6 残課題 5 を解決)。
      - 注意: 凍結生成物 `gen_v1_attributes.py` は旧形式出力 → 再実行後は `migrate_i18n.py` 必須。
- [x] **M1 (Phase 0〜2) 完了** — UI・CLI 文言・メタデータが英語起点、`--lang ja` で日本語へ往復可。
- [x] **Phase 3**: Quiz (prompt/label) を BASE=en + `i18n.ja` 化。`localized_prompt`/
      `localized_label` で解決、rationale/落選理由も表示言語追従。質問 ID は不変 (API 互換)。
      `build_site` は ja 解決で data.json 不変。skill にも i18n 注記 (済)。
- [x] **Phase 4**: コンテンツの言語タグ付け。`content_lang` (enum ja/en) を schema 新設し
      全 `speech/*` を `ja` 明示。intensity を言語認識化 (`content_language`/`skip_reason`/
      `IntensityReport.lang`、lang 不一致・未対応言語で skip)。`render_blend` に応答言語
      指示行を追加。推薦サマリ (B 層) を表示言語に追従 (`summary.*` カタログ)。(済)
      - 採用形式: 属性メタと揃え、コンテンツ言語は **属性単位の `content_lang`** で表現
        (将来 1 属性内に複数言語 payload を持つ場合は §2.2 の content 配列へ拡張)。
- [x] **Phase 5**: 英語ペルソナ拡充 (済)。`content_lang: en` の英語 speech 5 種
      (formal/casual/blunt/southern_us/british) を新設。schema に `lexical_markers`/`register`
      を追加。intensity に en 採点 (lexical_markers ベース) を実装。言語跨ぎ speech を
      `conflicts` で構造的に排他。`render_blend` が英語応答指示を付与。属性 59→64。
      - 残課題 7 (英語 speech 初期セット) = 上記 5 種で確定。
- [x] **全ゴール到達** — 英語 UI/メタデータ/クイズ + **英語で喋るペルソナ**まで実装完了。
      `--lang ja` で日本語 UI、ja/en 両方の人格を生成可能。

### 今後 (任意・スコープ外)
> 実装可能なタスクへの展開は [`I18N_FUTURE_WORK.md`](./I18N_FUTURE_WORK.md) を参照 (W1–W3)。

- **W1**: 英語 personality/archetype の en `content` 化 (現状 personality 等は ja コンテンツ固定 → 英語ペルソナで口癖が日本語になる不整合)。★最優先。
- **W2**: 診断クイズへの英語 speech 導線追加 (現状 en 人格は blend/create で opt-in)。
- **W3**: 残課題 6 (ja の extra 分離) はデータ量が問題化したら検討。

### Phase 0 実装メモ
- 言語決定は `resolve_lang()` に一元化 (フラグ > `HERSONA_LANG` > en)。`en-US` 等の
  地域サブタグは `normalize_lang()` で基底言語に丸める。未対応値は次段へフォールバック。
- `--lang` はトップレベルと全サブパーサ双方に付与し前置/後置どちらも受理
  (`default=argparse.SUPPRESS` で前置値の上書きを回避)。
- `tr()` のフォールバック: `<lang>` → `en` → キー文字列。差し込み失敗時もテンプレート返却。
- カタログは Phase 0 では `error.prefix` 等の最小セットのみ。全面化は Phase 1。
- `resolve_meta()` は新形式 (`i18n.<lang>`) と旧 suffix ペア (`*_ja`/`*_en`) を両受理。
