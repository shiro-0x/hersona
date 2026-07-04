# ユーザーフィードバック改善計画（2026-07-04）

> 対象: 初の外部ユーザーフィードバック 2 件への対応計画
> 位置づけ: `ROADMAP.md`（機能）・`docs/IMPROVEMENT_PLAN.md`（成長）・
> `docs/IMPROVEMENT_DISCUSSION_2026-06-15.md`（基盤）を補完する、**フィードバック起点の実装計画**。

---

## 0. 受領した要望

**要望 A（recommend → 成果物への直結）:**
> "I found that the hersona recommend command and the quiz to be really nice. I think it
> would be awesome if you had the option to immediately turn the result into a prompt
> injection block or SOUL.md without needing to manually re-enter the options into
> hersona blend."

**要望 B（英語ドキュメント・直感性）:**
> "I can't read japanese so I couldn't understand half the documentation. I think some
> more english docs would be quite nice especially on your website. It would also help
> if this were more intuitive to use."
> （blend 機能は「他のプロジェクトで見たことがない」と高評価）

**読み取れるシグナル:**

- recommend / quiz / blend は刺さっている。摩擦は「結果を成果物に変える最後の一歩」と「言語」。
- 「more intuitive」= 機能が無いのではなく**見つからない**（`recommend --apply` は既存だが
  ユーザーは blend への手入力に戻っている）。発見性の問題として扱う。

---

## 1. 現状ギャップ分析

### 1.1 要望 A: recommend 結果の出口

| 出口 | 現状 | ギャップ |
|---|---|---|
| 注入ブロック | `recommend --apply` が stdout に出力済み（`hersona/cli/app.py:862`） | **機能はあるが発見されていない**。README quickstart に導線なし |
| export 5 形式 | なし。`hersona export` へ属性名を手入力し直す必要 | `--export FORMAT` フラグ未実装 |
| SOUL.md | なし。`hersona soul` へ手入力し直す必要 | `--soul` 系フラグ未実装 |
| プリセット保存 | なし（`hersona save` へ手入力） | `--save NAME` 未実装 |
| MCP | `recommend_blend`（`hersona/mcp/tools.py:75`）は blend 返却のみ | export/soul への直結パラメータなし |
| Web サイト | クイズ結果 →「このブレンドを生成 →」で 1 クリック連携済み（`docs/app/app.js:514`） | 結果カードから直接コピーできる注入ブロックはない |

**好条件:** `recommend.py` の docstring に明記済みのフロー
（診断 → 推薦 → 適用 → 保存）の設計どおり、`Recommendation.blend` +
`weight_suggestion` は conflict 解決済みで、`export_blend` / `write_soul` /
`save_preset` の入力にそのまま渡せる。**core 側の新規ロジックは不要、CLI の配線のみ。**

### 1.2 要望 B: 英語対応

| 対象 | 現状 | ギャップ |
|---|---|---|
| 属性カタログ（`docs/app/data.json`） | `display_name_en` / `description_en` とも 213/213 で 100% | なし ✓ |
| **サイトの診断クイズ** | **日本語のみ**。`scripts/build_site.py:145` の `quiz_payload()` が `localized_prompt("ja")` 固定（コメントにも「en/ja 切替は将来作業」と明記） | **最大のギャップ**。EN ユーザーは目玉機能の診断が読めない |
| サイトの既定言語 | 「併記」固定。ブラウザ言語の自動判定なし。`<html lang="ja">`、title も JA 先行 | EN ユーザーの初見が JA 混在になる |
| サイトの記述ドリフト | Benefits に「5問の診断」→ 実際は 9 問 | 軽微だが信頼を損なう |
| README | EN 版あり（`README.md` が EN 正） ✓ | なし |
| `docs/PUBLIC_API.md` | 日本語のみ | 公開 API 契約文書なので EN 需要が高い |
| `docs/guides/`、`docs/app/README.md`、skill `REFERENCE.md` | ほぼ日本語のみ | 優先度は中〜低（オンデマンド文書） |

**設計上の注意（クイズ英語化）:** EN 対応は「JA クイズの英語ラベル表示」では不十分。
`recommend_quiz.en.yaml` は**英語 speech 属性へ導線する別の重み付け**を持つロケール別クイズ
（W2 設計、質問 ID は互換）。サイトも同様に **lang=en では EN クイズの重みで推薦**すべき。
data.json に両クイズを埋め込み、`state.lang` で切り替えるのが CLI と整合する。

---

## 2. 改善計画

### Phase 1 — recommend の出口直結（要望 A 本命）

**A1. `hersona recommend --export FORMAT [--output FILE]`**

- `EXPORT_FORMATS`（`hersona/core/export.py:27`）の 5 形式をそのまま choices に。
- weight は `--weight` 指定 > `rec.weight_suggestion` の順で解決（`--apply` と同じ規則）。
- `--output` 省略時は stdout（既存 `export` サブコマンドと同じ UX）。
- `--json` との併用は排他（エラー）。

**A2. `hersona recommend --soul [--profile NAME] [--force] [--dry-run] [--soul-output FILE]`**

- `write_soul`（`hersona/core/soul.py:180`）へ直結。上書き保護・dry-run は
  `soul` サブコマンドと同じ安全フラグ体系を踏襲（既定は上書き拒否）。
- 適用前に conflict 済み blend しか渡らないため、persistence 経路の拒否条件とも整合。

**A3. `hersona recommend --save PRESET_NAME`（任意・小）**

- 推薦結果をプリセット保存し、後日 `hersona load` で再利用できる導線。

**A4. MCP / スキル追随**

- `recommend_blend` MCP ツールに `export_format` パラメータ追加（戻り値に `export` キー）。
- `skills/hersona/SKILL.md` は 1 行追記に留め、フラグ詳細は `REFERENCE.md` 側へ
  （SKILL.md authoring rules: 毎ターンロードされる本体のトークン費用を増やさない）。

**A5. 発見性（実装ゼロで効く対策）**

- README（EN/JA）quickstart に `hersona recommend` →「そのまま `--export` / `--soul`」の
  ワンライナーを追記。既存の `--apply` もここで初めて見えるようにする。

実装ポイント: `_cmd_recommend`（`hersona/cli/app.py:792`）の末尾分岐に追加。
テストは `tests/test_cli.py` / `tests/test_recommend.py` に追加。

### Phase 2 — サイト英語化（要望 B 本命）

**B1. クイズの i18n 埋め込み（最優先）**

- `quiz_payload()` を BASE（prompt/label は EN、`i18n.ja` 併載）+ EN クイズ
  （`recommend_quiz.en.yaml`、英語 speech 導線の重み）両方を出力する形に変更。
- `app.js` は `state.lang === "en"` なら EN クイズで推薦、それ以外は JA 表示の BASE クイズ。
- `python scripts/build_site.py` で `data.json` 再生成（CI の `--check` ゲート対象）。

**B2. 初回訪問時の言語自動判定**

- `localStorage` 未設定時のみ `navigator.language` を判定: `ja*` → `both`（現行既定）、
  それ以外 → `en`。保存済み設定は常に尊重。
- `setLang()` で `<html lang>` も動的に切替。

**B3. 記述ドリフト修正**

- 「5問の診断」→ 9 問（`docs/app/index.html` の Benefits / Quiz セクション）。

**B4. クイズ結果カードの直接出口（要望 A×B の交点）**

- 結果カードに「注入ブロックをコピー」ボタンを追加（blend 生成器への遷移を挟まず即コピー）。
- 余力があれば SOUL.md 形式のダウンロードも（`render_soul` 相当の JS 移植は
  やり過ぎなので、注入ブロック + フロントマターの簡易版に留める判断も可）。

### Phase 3 — ドキュメント英語化・直感性の底上げ

| ID | 内容 | 優先度 |
|---|---|---|
| C1 | `docs/PUBLIC_API.md` の EN 版（`docs/PUBLIC_API.en.md`）。公開 API 契約なので最優先 | 高 |
| C2 | `docs/guides/README.md`・`docs/app/README.md` の EN 併記 | 中 |
| C3 | README に「30 秒で体験」導線（サイト → クイズ → コピー）を明示。IMPROVEMENT_PLAN の「体験までの距離」課題とも合流 | 中 |
| C4 | skill `REFERENCE.md` の EN 化は保留可（オンデマンド文書でトークン制約が緩く、JA 利用者が主。persona content は翻訳禁止ルールの対象外に注意） | 低 |

---

## 3. 実施順序と工数目安

| 順 | 項目 | 工数 | 効果 |
|---|---|---|---|
| 1 | A1 + A2（--export / --soul） | 半日 | 要望 A を直接解決。core 再利用のみ |
| 2 | A5（README 導線） | 30 分 | 「intuitive でない」の即効薬 |
| 3 | B1 + B2 + B3（サイトクイズ EN + 自動判定） | 1 日 | 要望 B の最大ギャップ解消 |
| 4 | A3 + A4（--save / MCP / スキル） | 半日 | 導線の完成 |
| 5 | B4（結果カード直接コピー） | 半日 | Web 側の要望 A |
| 6 | C1〜C3 | 1〜2 日 | 継続的な英語化 |

---

## 4. 各変更で守ること（CLAUDE.md 更新規則）

- CLI フラグ追加（A1〜A3）: `README.md` / `README.ja.md` 両方更新、
  `CHANGELOG.md` に `## [Unreleased]`、`python scripts/validate.py` + `pytest`。
- クイズ payload 変更（B1）: `python scripts/build_site.py` で `data.json` 再生成
  （validate/pytest ではカバーされない）。
- SKILL.md 追記（A4）: 本体は最小限、詳細は `REFERENCE.md`。`version:` の SemVer 更新。
- persona content（catchphrases / sentence_endings / tone / core_traits）は翻訳しない。

## 5. リスク・判断メモ

- `recommend --soul` は書き込みを伴うため、`soul` と同じ既定拒否 + `--force` を踏襲
  （うっかり上書きを防ぐ。安全側の一貫性が informal な信頼につながる）。
- B1 で data.json のサイズが増える（クイズ 2 本分）。属性 213 件に対しクイズは小さく、
  実測で問題になる規模ではない見込みだが、build 時に差分サイズを確認する。
- EN クイズと BASE クイズは質問 ID 互換（W2 設計）なので、サイトの回答状態は
  言語切替をまたいで引き継げる。ただし途中切替時は重みが変わるため「再診断を促す」が安全。
