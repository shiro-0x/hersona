# 口癖トリガ注記 (catchphrase trigger annotation) — 設計書

> ステータス: ドラフト (未実装)
> 対象バージョン: hersona v0.1.0+
> 関連: [`attributes/personality/tsundere.yaml`](../attributes/personality/tsundere.yaml) /
> [`hersona/core/attach.py`](../hersona/core/attach.py) /
> [`schema/attribute.schema.json`](../schema/attribute.schema.json)
> 前段の対策 A (整合性優先ルールのプロンプト注入) は実装済み。本書はその次段 **B**。

---

## 1. 概要

各 catchphrase（口癖）に **発動条件（トリガ／使用文脈）** を任意で併記できるようにする。

現状、口癖は文字列の平坦なリストとして注入され、「いつ使うか」の情報が剥がれている。
そのため「べ、別に……」（本来は *好意・感謝を向けられた照れ隠し* 専用）のような
状況依存フレーズが、文脈の合わない場面（例: 単なるタスク指示への応答）にも貼り付き、
`べ、別に…、すぐ修正する。` のような**意味的に破綻した文**を生む。

対策 B では、口癖に「どんな場面で出るか」を付与し、注入プロンプトに
`口癖 — 発動条件` の形で渡すことで、モデルが文脈に合うときだけ自然に使えるようにする。

```yaml
catchphrases:
  - phrase: べ、別に……
    when: 好意・感謝・心配を向けられ、それを認めるのが照れくさいとき
  - phrase: 勘違いしないでよね
    when: 親切にした直後、その意図を悟られたくないとき
```

---

## 2. 背景と問題

### 2.1 現状の注入経路

- `hersona/core/attach.py` `_render_prompt` が `## catchphrases` として
  `- {文字列}` を列挙する（対策 A で整合性優先の注記を併記済み）。
- `hersona/core/soul.py` `_render_soul_body` が SOUL.md の Tone セクションに同様に列挙。
- `hersona/core/intensity.py` `_collect_speech_signals` が speech 属性の
  catchphrases を採点用に集約（**文字列前提**）。
- `hersona/core/export.py` `_attribute_summary` が `catchphrases` を list として書き出し。
- スキーマ `schema/attribute.schema.json` は `catchphrases` を
  `array<string>`（1–15 件）と定義。`content_i18n.<lang>.catchphrases` も同型。

### 2.2 問題の本質

口癖は本来「文脈 → 言い回し」の対応だが、現データは**言い回しだけ**を持つ。
A（整合性優先のメタ指示）は「合わなければ使うな」と促すが、**何が「合う」かの
判断材料はモデル任せ**のままで、属性ごとに正解が違う照れ隠し系・強がり系の口癖では
誤適用が残る。B は判断材料（トリガ）をデータとして与え、A の指示を実効化する。

---

## 3. スコープ

### 3.1 In scope

- catchphrases の各要素に**任意のトリガ注記**を持たせるデータモデル拡張。
- スキーマ更新（後方互換を保つ polymorphic 定義）。
- 注入プロンプト / SOUL.md レンダラーがトリガを `口癖 — 発動条件` 形式で出力。
- `content_i18n.<lang>.catchphrases` も同じ拡張を適用。
- 強度指標 (`intensity.py`) がトリガ付き要素から**口癖文字列を正しく抽出**できる。
- 既存 export / 各 core ヘルパーの後方互換維持。
- 代表属性（tsundere / yandere / kuudere / dandere など状況依存が強いもの）への
  トリガ付与の**初期適用**。

### 3.2 Out of scope

- 全 65 属性へのトリガ全面付与（段階適用。本書は仕組みと初期分のみ）。
- トリガに基づくランタイムの自動発動制御（あくまでプロンプト内の自然言語ヒント）。
- 強度指標の採点式そのものの変更（口癖の抽出経路のみ修正、密度の重み調整は A/C 側課題）。

---

## 4. データモデル

### 4.1 要素の多態化（string | object）

後方互換のため、catchphrases の各要素は **文字列** か **オブジェクト** のいずれも許可する。

| 形 | 意味 |
| --- | --- |
| `"べ、別に……"` | 従来どおり。トリガなし（任意の場面で使える汎用口癖） |
| `{phrase: "べ、別に……", when: "…"}` | `when` の場面でのみ使う口癖 |

- `phrase` (必須, string): 口癖本体。
- `when` (任意, string): 発動条件・使用文脈の 1 行記述。日本語 BASE は日本語、
  `content_i18n.<lang>` 配下は当該言語で記述する。

### 4.2 内部正規化

ロード直後に各要素を `{"phrase": str, "when": str|None}` へ正規化する小ヘルパー
（`hersona/core/attach.py` に `_normalize_catchphrase(item) -> dict` を新設）を通し、
以降の処理は常に dict を扱う。これにより string/object の分岐を 1 箇所に閉じ込める。

```python
def _normalize_catchphrase(item: str | dict) -> dict:
    if isinstance(item, str):
        return {"phrase": item, "when": None}
    return {"phrase": item.get("phrase", ""), "when": item.get("when") or None}
```

---

## 5. スキーマ変更

`schema/attribute.schema.json` の `catchphrases.items` を polymorphic にする
（`content_i18n.<lang>.catchphrases` も同様）。

```json
"catchphrases": {
  "type": "array",
  "minItems": 1,
  "maxItems": 15,
  "items": {
    "oneOf": [
      { "type": "string", "minLength": 1 },
      {
        "type": "object",
        "required": ["phrase"],
        "additionalProperties": false,
        "properties": {
          "phrase": { "type": "string", "minLength": 1 },
          "when":   { "type": "string", "minLength": 1 }
        }
      }
    ]
  }
}
```

既存の `array<string>` データはすべて `oneOf` の第 1 枝に適合するため**破壊変更なし**。

---

## 6. レンダリング変更

### 6.1 注入プロンプト (`attach._render_prompt`)

`## catchphrases` の各行を、トリガがあれば併記する形に変更する。

現状:

```
## catchphrases
- べ、別に……
- 勘違いしないでよね
```

変更後（ja）:

```
## catchphrases
- べ、別に…… — 好意・感謝・心配を向けられ、認めるのが照れくさいとき
- 勘違いしないでよね — 親切にした直後、意図を悟られたくないとき
```

- トリガなしの要素は従来どおり `- {phrase}` のまま。
- 区切りは ja: ` — `、en: ` — `（em dash + 半角スペース）で統一。
- 既存の整合性優先注記（A）は引き続き末尾に出す。トリガはその判断材料になる。

`_resolve_merge` / `catchphrase_subset` はトリガ付き要素を扱うため、
**正規化後の dict のリスト**を通すよう内部を調整する（重複排除は `phrase` で行う）。
`catchphrase_subset` の比率サブセット選択は `phrase` 数を基準に維持する。

### 6.2 SOUL.md (`soul._render_soul_body`)

Tone セクションの catchphrases 列挙を同形式（`- {phrase} — {when}`）に更新。
`_resolve_lang_field(attr, "catchphrases", lang)` の戻りを正規化して整形する。

### 6.3 export (`export._attribute_summary`)

`catchphrases` は構造化データとして**原形（string | object 混在）を維持**して書き出す。
`messages` / `markdown` 形式は `render_blend(...).prompt` 経由なので 6.1 の変更が自動反映。

---

## 7. 強度指標への影響 (`intensity.py`)

`_collect_speech_signals` は現在 `c` が `str` 前提で `seen_c` 判定している。
正規化を挟み、**`phrase` 文字列だけを採点対象**に集約する。

```python
for c in a.get("catchphrases", []) or []:
    phrase = _normalize_catchphrase(c)["phrase"]
    if phrase and phrase not in seen_c:
        seen_c.add(phrase); catchphrases.append(phrase)
```

`measure_intensity` の `text.count(c)` は `phrase` を数えるため挙動不変。
→ **採点結果は後方互換**（既存テストのスコアは変わらない）。

---

## 8. 後方互換とマイグレーション

- 既存の `array<string>` データはそのまま有効（正規化で `when=None`）。
- 段階適用: まず仕組み（4–7 章）を入れ、データは状況依存の強い属性から順次付与。
- マイグレーションスクリプトは**不要**（任意フィールド追加のため）。
  既存属性に手で `when` を足すだけで段階的に効果が出る。
- `content_i18n.<lang>.catchphrases` を object 化する場合、BASE と同数・同順を推奨
  （対応関係を保つ）。en 等のネイティブ記述は当該言語でトリガを書く。

---

## 9. バリデーション

- `scripts/validate.py`（または既存 check 経路）で次を確認:
  - object 形のとき `phrase` 必須・`when` は任意。
  - `phrase` 重複の検出（同一属性内）。
  - `when` の長さ目安（例: 60 字以内を warning）。
- スキーマ `oneOf` で構造は JSON Schema 検証に乗る。

---

## 10. テスト計画

| 対象 | 観点 |
| --- | --- |
| `_normalize_catchphrase` | string / object / 欠損 phrase / 空 when の正規化 |
| `attach._render_prompt` | トリガ付きは `phrase — when`、なしは `phrase` のみ |
| `attach` 後方互換 | 既存 `array<string>` 属性のプロンプトが従来文字列を含む |
| `soul._render_soul_body` | SOUL.md Tone にトリガ併記される |
| `intensity._collect_speech_signals` | object 要素から phrase を抽出、採点スコア不変 |
| `export` | json 形式が原形を保持、markdown 形式にトリガが乗る |
| schema | object / string 双方が `oneOf` を通過、`when` 余剰キーは reject |

回帰の要: 既存 `tests/test_intensity.py` のスコア期待値が**変わらない**こと。

---

## 11. ロールアウト

1. `_normalize_catchphrase` 追加 + 各 core 経路を正規化対応（無挙動変化を確認）。
2. スキーマ `oneOf` 化 + バリデーション。
3. レンダラー（attach / soul）にトリガ併記。
4. 状況依存の強い属性へトリガ初期付与（tsundere / yandere / kuudere / dandere / chuunibyou 等）。
5. ドキュメント（SKILL.md / hermes-agent.md）に記法を追記。

---

## 12. 未決事項

- 区切り記号は ` — ` で確定か（`：` や括弧 `(…)` 案もある）。
- トリガ未付与の汎用口癖と、付与済み口癖が混在する属性の**プロンプト見え方**を
  統一すべきか（混在を許すか、属性単位で全付与を推奨するか）。
- A の整合性注記と B のトリガ併記で**文量が増える**ため、weight=mild 以下では
  トリガ併記を間引く（先頭 N 件のみ）案の要否。
