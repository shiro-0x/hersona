# 最新コミットレビューと改善案 (2026-07-02)

対象: 直近のコミット群 — #122 (自己紹介 lint / ガイド)、#117・#118 (ユースケース
Operating Mode)、および関連する core / docs。

検証状況: `pytest` 1451 件全て成功、`scripts/validate.py` 通過。
疑わしい箇所は実際にコードを実行して確認済み。

---

## 優先度: 高(実挙動のバグ・ドリフト)

### 1. `self_intro.py` の誤検知(実行して確認済み)

- **メールアドレスが `third_party_handle` 扱い**
  `連絡は info@example.com まで` が `@example` として違反になる。
  `_HANDLE_RE` (`hersona/core/self_intro.py:62`) に負の後読み
  `(?<![A-Za-z0-9.])@` を追加するのが手軽。
- **`メタバース` が `meta_personality_label` 扱い**
  裸の `メタ` がサブストリングマッチするため。
  `メタ(?:発言|的な?説明)` のように文脈を要求すべき。
- **ローマ字 `ai` が `ai_self_label` 扱い**
  `(?i)\bAI\b` が小文字にも当たる。`(?i)` をパターン全体でなく
  必要な選択肢に限定し、AI は大文字固定にするのが安全。
- **職業としての「エージェント」も違反**
  `不動産エージェントとして働いています` が引っかかる。
  自己ラベル文脈(`エージェント(?:です|だ|として)` 等)を要求するか、
  意図的な仕様ならガイドにその旨を明記する。

### 2. `meta_rule_sermon` がほぼ機能していない(検知漏れ、実行して確認済み)

`しません(?:。|$).{0,40}しません` は「しません」が 2 回必要だが、日本語の
規則口上は「〜つきません。〜もしません。」のように動詞が変わるのが普通で、

- `嘘をつきません。誇張もしません。`
- `私は嘘をつきません。\nまた、誇張もしません。`

のいずれも検知されない。`ません(?:。|$)` ベースに広げ、複数行対応のため
`re.M | re.S` を付ける (`hersona/core/self_intro.py:58`)。

### 3. SKILL.md のバージョン不整合

front-matter とタイトルは **v0.5.5** (`skills/hersona/SKILL.md:4, 20`) なのに、
末尾の Versioning 節は「The current SKILL is **v0.5.4**」
(`skills/hersona/SKILL.md:394`) のまま。修正に加え、`test_skill_versions.py` に
「本文中のバージョン表記が front-matter と一致する」チェックを足すと再発防止になる。

### 4. `lint-intro --input` で存在しないパスを渡すとトレースバック

`main()` が捕捉するのは `AuthoringError / PresetError / KeyError / ValueError`
(`hersona/cli/app.py:98`) のみで、`Path(args.input).read_text()` の
`FileNotFoundError` (OSError 系) は素通りする。`_cmd_lint_intro` 内で捕捉して
`error.prefix` 付きメッセージ + exit 1 にするのが他コマンドと整合的。

---

## 優先度: 中(設計・整合性)

### 5. `use_cases.py`: 重複 `use_case_id` の解決が関数間で逆

`load_use_case` はソート順で**最初**にマッチしたファイルを返し
(`hersona/core/use_cases.py:53`)、`available_use_cases` は dict 上書きで
**最後**が勝つ (同 `:38`)。同じ ID が 2 ファイルにあると `use-case list` の
表示と `use-case show` の中身が食い違う。重複検出時にエラーにするか、
first-wins に統一する。

### 6. `validate_use_case` が毎回スキーマをディスクから再読込

`render_use_case_block` → `validate_use_case` のたびに JSON 読込 +
`Draft202012Validator` 再構築が走る (`hersona/core/use_cases.py:61-65`)。
`functools.lru_cache` でバリデータをキャッシュすれば済む。

### 7. `soul.py` の Name セクションが一人称「私」固定

`_DEFAULT_FIRST_PERSON = "私"` (`hersona/core/soul.py:40`) のため、俺様系
speech や英語ブレンドでも SOUL.md に「一人称: 私」が書かれ、本文の Tone と
矛盾する。`measure` が first_person を採点に使っているくらいなので、speech
属性から一人称を導出する(なければ既定)方が SOUL の正本性に合う。

### 8. `soul.py` の細かな重複・非効率

- personality 節の採番に `personality_attrs.index(attr)`
  (`hersona/core/soul.py:425`) を使っていて O(n²)、かつ同一属性が並ぶと
  採番が壊れる。speech 節 (同 `:469`) は既に `enumerate` なので揃える。
- `write_soul` は `render_soul` 内で lang を算出済みなのに、戻り値用に
  `_detect_lang_from_names` で **blend をもう一度フルレンダリング**している
  (同 `:268`)。`render_soul` が lang も返す形にすれば半分の仕事で済む。

---

## 優先度: 低(提案)

### 9. canonical ルールの拡張性

`--canonical` の禁止語が `マスター` ハードコード 1 語のみ
(`hersona/core/self_intro.py:125`)。ガイドは「inner-circle nicknames」一般を
謳っているので、`ご主人様` 等も含む設定可能なリストにするとガイドと実装が揃う。

### 10. lint と SOUL の統合

`persistent --memory` で `self_intro_canonical` キーを書き込む際に
`lint_self_intro(canonical=True)` を自動実行して警告する導線があると、
ガイドのチェックリスト(手動実行前提)が仕組みで担保される。

### 11. SKILL.md の Command Syntax に `hersona lint-intro` が未掲載

When to Use には自己紹介の項があるが、CLI 一覧
(`skills/hersona/SKILL.md:133-153`) に lint-intro がない。1 行追加で十分
(README には掲載済み)。

---

## まとめ

**1・2 (lint の精度)、3 (バージョン表記)、4 (CLI エラー処理)** が実害のある
修正候補で、いずれも小さな diff で直せる(全部まとめて 1 コミットで対応可能な規模)。

補足: レビュー中に `uv sync` の副産物として `uv.lock` の hersona バージョン
(0.0.1 → 1.6.0) の stale 修正をコミット済み (#119 のバンプ時の取り残し)。
