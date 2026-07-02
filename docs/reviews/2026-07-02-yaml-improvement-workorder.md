# 作業指示書: 注入トークン削減と個性強化 (2026-07-02)

元レビュー: [2026-07-02-yaml-token-review.md](./2026-07-02-yaml-token-review.md)

タスクは 6 件。**Task 1〜3 がコード変更(PR 1 本)、Task 4〜6 が YAML 整備
(PR 1〜2 本)** を想定。各タスクに変更内容・受け入れ基準・検証コマンドを示す。

## 共通ルール(全タスク)

- 変更後は必ず実行:

  ```bash
  uv run python scripts/validate.py
  uv run python -m pytest -q
  uv run ruff check hersona/ scripts/ tests/
  ```

- **属性 YAML を 1 つでも変更したら** `docs/app/data.json` の再生成が必要:

  ```bash
  uv run python scripts/build_site.py
  ```

- 各 PR に `CHANGELOG.md` の `## [Unreleased]` エントリを追加する。
- ペルソナコンテンツ (catchphrases / sentence_endings / tone / core_traits) は
  **日本語コンテンツ属性なら日本語で書く**(CLAUDE.md「Never translate persona
  content」)。ディレクティブ(LLM への指示文)は英語で書く。

---

## Task 1【バグ修正】mandarin_casual の tone からメンテナノートを除去

**ファイル**: `attributes/speech/mandarin_casual.yaml`

**現状**: `tone`(507 chars)の後半にスキーマ運用の説明が混入しており、
毎セッション persona tone として注入されている。

**変更**:

1. `tone` から次の文をまるごと削除する(`Note:` 以降すべて):

   > Note: BASE catchphrases are authored in zh (matching content_lang: zh).
   > The schema only requires display_name / description to match BASE=en;
   > catchphrases / tone / lexical_markers can be in any language consistent
   > with content_lang (Pitfall 27-A is about en attributes whose BASE drifted
   > away from en, not zh attributes).

2. 削除した文は `notes:` フィールドに移動する(既存 notes があれば追記)。

**受け入れ基準**:
- `render_blend(["mandarin_casual"]).prompt` に "Pitfall" / "schema" が含まれない。
- `tone` は言語レジスタの記述のみ(先頭〜 "Friendly rather than formal." まで)。
- `scripts/build_site.py` 再実行済み。

---

## Task 2【コード】固定ディレクティブの条件分岐・重複統合

**ファイル**: `hersona/core/attach.py`
(`response_style_directive` と呼び出し元 `_render_prompt`)

**現状の問題**(実測: keigo 単体で固定部 1,016/1,133 chars = 90%):
- 「When blending multiple attributes, adapt personality catchphrases …」
  (約 200 chars)が**単一属性でも**常に注入される。
- sentence_endings が無い属性でも "…and sentence endings as a repertoire /
  don't stamp the same ending on every sentence" が入る。
- 「use them only when they fit」と「Prioritize conversational sense; never
  break grammar to force a catchphrase in.」が意味重複。

**変更**:

1. シグネチャにキーワード専用引数を追加(既定値で後方互換維持):

   ```python
   def response_style_directive(
       lang: str,
       *,
       has_catchphrases: bool,
       has_sentence_endings: bool,
       is_blend: bool = True,
   ) -> str:
   ```

2. `_render_prompt` から `is_blend=len(attrs) > 1` を渡す。
3. 本文を次の条件構成にする:
   - ベース文(常時): "Embody personality and tone through word choice and
     attitude; never narrate your own traits or add preamble…"
   - `has_catchphrases or has_sentence_endings` のとき: repertoire 文。ただし
     文言を条件で出し分ける — 両方あるとき "catchphrases and sentence endings"、
     catchphrases のみ "catchphrases"、endings のみ "sentence endings"。
     "don't stamp the same ending on every sentence" は
     `has_sentence_endings` のときのみ。
   - `is_blend` のときのみ: "When blending multiple attributes, adapt
     personality catchphrases to the speech attribute's …" 文。
   - 反復防止文(常時): "Don't repeat the same opening…"
   - `has_catchphrases` のとき: 末尾文を **repertoire 文と統合**して 1 文に
     短縮する(例: repertoire 文の末尾に "; never break grammar or
     conversational sense to force one in" を付け、独立した最終文は削除)。

**テスト更新**: `tests/test_attach.py`
- `test_response_style_directive_languages` (L161): `is_blend` の
  True/False 両方を検証するケースを追加。単一属性で
  "When blending multiple attributes" が**出ない**ことを assert。
- `test_render_blend_emits_consolidated_response_style_directive` (L130):
  2 属性ブレンドなので blending 文が出ることは維持されるはず。文言統合に
  合わせて assert 文字列を調整。
- 新規: `render_blend(["keigo"])`(単一・endings なし)で blending 文と
  "stamp the same ending" が出ないことを検証。

**受け入れ基準**:
- `len(render_blend(["keigo"]).prompt)` が現状 1,133 chars から **≥150 chars 減**。
- 2 属性以上のブレンド出力には blending 文が引き続き含まれる。
- `docs/PUBLIC_API.md` は変更不要(response_style_directive は非公開 API)だが、
  シグネチャ拡張を CHANGELOG に記載。

---

## Task 3【コード】first_person / lexical_markers / speech_style の注入追加

**ファイル**: `hersona/core/attach.py::_render_prompt`

**現状の問題**: `measure_intensity` は first_person(重み 25〜60%)と
lexical_markers(en の主軸)で採点するのに、注入ブロックはどちらも含まない。
`speech_style`(115/140 属性が保有)は全く未使用。

**変更**: `## Second person:` ブロックの直後に以下を追加する。

```python
first_person = _first_str(attrs, "first_person")
lexical_markers = _merge_list(attrs, "lexical_markers")
speech_styles = [
    a["speech_style"] for a in attrs
    if isinstance(a.get("speech_style"), str) and a["speech_style"]
]
...
if first_person:
    lines.append("")
    lines.append(f"## First person: {first_person}")
if lexical_markers:
    lines.append("")
    lines.append("## Lexical markers: " + " / ".join(lexical_markers))
if speech_styles:
    lines.append("")
    lines.append("## speech_style")
    lines.extend(f"- {s}" for s in speech_styles)
```

設計判断のメモ:
- `first_person` は `second_person` と同じ **first-wins**(`_first_str`)。
  複数 speech 属性の一人称が混在すると人格が壊れるため。
- `speech_style` は `content_i18n` の対象外(スキーマ上 catchphrases / tone /
  core_traits / examples のみ)なので言語解決は不要。そのまま注入する。
- `register` は tone と重複度が高いので注入**しない**(現状維持)。

**テスト追加**: `tests/test_attach.py`
- ja: `render_blend(["ore_boy"])` に `## First person: オレ / 俺` が入る。
- en: `render_blend(["casual_en"])` に `## Lexical markers:` が入る。
- speech_style を持つ属性で `## speech_style` セクションが入る。
- 持たない属性(personality 単体等)でセクションが出ないこと。

**SOUL 連携(任意・推奨)**: `hersona/core/soul.py::_render_soul_body` の
Tone 節にも同 3 フィールドを出力すると SOUL.md と blend の個性が揃う。
また前回レビュー指摘 (#7) の「一人称『私』固定」は、この `first_person`
first-wins 値があれば `_DEFAULT_FIRST_PERSON` のフォールバック置き換えで解消できる。

**ドキュメント同期**: 注入ブロックの構成が変わるため、README EN/JA に注入
フィールドの記載があれば更新し、CHANGELOG に記載。SKILL.md は変更不要。

**受け入れ基準**:
- measure が採点する 3 シグナル(endings / first_person / lexical_markers)が
  すべて注入ブロックにも現れる(該当フィールドを持つ属性の場合)。
- 既存テストが文言調整以外の変更なしで通る。

---

## Task 4【YAML】基幹 speech 8 属性のバックフィル

**対象**: `attributes/speech/{archaic,boku_girl,kansai_ben,keigo,onee_kotoba,ore_boy,third_person,whispery}.yaml`

**現状**: 8 属性とも `tone` / `sentence_endings` / `second_person` が無く、
注入が catchphrases のみ。keigo / kansai_ben 等は `measure_intensity` が
**None(採点不能)** を返す。

**変更**: 各ファイルに以下を追加する。下記ドラフトは既存の catchphrases /
notes / description と整合するよう起草したもの — 実装時に文言を磨いてよいが、
**日本語コンテンツとして書くこと**(tone も日本語で可。既存 ja 属性の慣例に従う)。

| 属性 | first_person | second_person | sentence_endings | tone(要旨) |
|---|---|---|---|---|
| keigo | 私（わたくし） | あなた様 / お客様 / 〜様 | です / ます / ございます / でしょうか / いたします | 尊敬語・謙譲語・丁寧語を統一的に維持。崩れる瞬間に感情のピークを置く |
| kansai_ben | うち / わし | あんた / 自分 | や / やで / やん / ねん / へん / ほんま | 関西弁のテンポとツッコミ。距離の近さと軽妙さ、感情表現は率直 |
| archaic | (既存: 我 / 拙者) | そなた / 貴方（あなた） | ぞ / じゃ / でござる / 給え / ぬ | 古語・文語調で威厳と非日常性。現代語彙を混ぜない |
| boku_girl | (既存: ボク) | キミ | さ / よ / じゃん / もん / ぜ | ボーイッシュで軽快、活発。照れると勢いが増す |
| onee_kotoba | 私 | あなた | わ / わよ / わね / のよ / かしら / なさい | 品と包容力のある年長者の余裕。丁寧だが距離は近い |
| ore_boy | (既存: オレ / 俺) | お前 / テメェ | ぜ / ぞ / だろ / ねえ / かよ | 粗野で断定的、自信と喧嘩っ早さ。仲間には義理堅い |
| third_person | ※付与しない(下記) | あなた / 相手の名前呼び | の / だよ / ね(舌足らずな短文) | 自分を名前で呼ぶ。無邪気さと非人間性の両義。短い文節、間が多い |
| whispery | 私 | あなた | ……ね / ……の / ……から / ……かな | 常に声を潜めた低く柔らかいトーン。三点リーダと間で空気を作る |

**third_person の注意**: 一人称は「キャラ自身の名前」であり固定トークンが
存在しないため `first_person` は付与**しない**(プレースホルダを入れると
measure の一人称カウントが誤作動する)。tone に「一人称の代わりに自分の
名前を使う」ことを明記する。

**受け入れ基準**:
- 8 属性すべてで `render_blend([name]).prompt` に tone / sentence_endings /
  second_person が現れる(third_person の first_person 除く)。
- `measure_intensity("です・ます調のサンプル文…", [load_attribute("keigo")])`
  が None ではなく IntensityReport を返す。
- `conflicts_with` の対称性チェック(`validate.py`)が通る。
- `scripts/build_site.py` 再実行済み。

---

## Task 5【YAML】archetype 7 属性への core_traits / tone 追加

**対象**: `attributes/archetype/` のうち core_traits / tone を持たない 7 属性
(childhood_friend, gamer_otaku, heroine, mentor, rival, robot_android,
shrine_maiden)。

**変更**: 各属性に `core_traits`(3〜7 個、schema 準拠)と `tone`(1 行)を
追加する。archetype は「関係性・役割」のカテゴリなので、core_traits は
**行動・関係性の型**として書く。例(mentor):

```yaml
core_traits:
- 相手の成長を第一に置く
- 答えではなく問いを与える
- 失敗を許容し見守る
- 要所でのみ本気を見せる
tone: 落ち着いた説得力のある語り。教えるより導く。距離は保つが突き放さない。
```

heroine / rival 等も同じ型で起草する(既存 catchphrases のニュアンスと
整合させること)。

**受け入れ基準**:
- 7 属性すべてで `render_blend([name]).prompt` に `## core_traits` と
  `## tone` が現れる。
- `scripts/build_site.py` 再実行済み。

---

## Task 6【YAML・任意】examples が catchphrases の完全コピーの 16 件を差し替え

**対象**(16 ファイル):
- archetype: childhood_friend, gamer_otaku, heroine, mentor, rival,
  robot_android, shrine_maiden
- speech: boku_girl, keigo, onee_kotoba, ore_boy, princess_speech, stutter,
  third_person, tomboy

**変更**: `examples` を catchphrases のコピーから、`tsundere.yaml` の
簡易版フォーマット(`[user]` / `[assistant]` の 1〜2 往復 × 2〜3 個)へ
差し替える。examples は注入されないため優先度は低いが、**Task 4 / Task 5 で
同じファイルを触る際に同時に行うと二度手間がない**(16 件中 12 件が
Task 4・5 の対象と重複)。

**受け入れ基準**: 各ファイルの examples に会話形式の例が 2 個以上あり、
catchphrases との完全一致が無い。固有名詞・実在作品名を含まない。

---

## PR 分割と順序

| PR | 内容 | 依存 |
|---|---|---|
| PR-A | Task 1 + Task 2 + Task 3(コード + mandarin_casual 修正) | なし |
| PR-B | Task 4 + Task 6 の speech 分 | PR-A 推奨(注入確認のため) |
| PR-C | Task 5 + Task 6 の archetype 分 | PR-A 推奨 |

## 完了時の効果測定

PR-A マージ後に以下を before/after で記録する:

```bash
uv run python -c "
from hersona.core.attach import render_blend
for names in (['keigo'], ['tsundere','keigo'], ['casual_en']):
    print(names, len(render_blend(names, weight='moderate').prompt), 'chars')
"
```

目安: keigo 単体 1,133 → PR-A 後 ~950 以下(削減)、PR-B 後は
tone/endings 追加で増えるが、その分すべてが個性シグナル(意図した再配分)。
