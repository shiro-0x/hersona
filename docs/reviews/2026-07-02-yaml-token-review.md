# YAML レビュー: トークン削減・無駄の排除・個性の強化 (2026-07-02)

対象: `attributes/` 201 ファイル + `use_cases/` 8 ファイル。
観点はユーザー指定の 3 点 — **トークン量の削減 / 無駄を省く / きちんと個性が出る**。

検証方法: 全 YAML を横断集計し、`render_blend` の実出力・`measure_intensity` の
実挙動をコードを動かして確認した(推測ではなく実測)。

## 前提: 注入されるフィールドと、されないフィールド

`attach.py::_render_prompt` が毎セッションのシステムプロンプトに注入するのは
**core_traits / catchphrases (+when) / tone / sentence_endings / second_person** のみ。

**注入されない**: `description` / `examples` / `first_person` / `speech_style` /
`lexical_markers` / `register` / `compatible_archetypes` / `notes` / `tags`
(show / export / measure / SOUL 等でのみ使用、または未使用)。

→ トークン削減の主戦場は「注入されるフィールド + 固定ディレクティブ」、
個性強化の主戦場は「注入されて**いない**が個性を担うフィールド」になる。

---

## A. 個性が出るように(注入内容の欠落)

### A-1. `first_person` / `lexical_markers` が注入されず、measure とは不整合【最重要】

- `first_person` は 105/140 の speech 属性が持ち、`measure_intensity` では採点 3 軸の
  1 つ(重み 25〜60%)。しかし **`_render_prompt` は一切注入しない**。
  つまり「オレ / 俺」で話すよう一度も指示していない LLM を、一人称の出現率で採点している。
- en speech 22 属性の `lexical_markers`(gonna / y'all 等)も同様: en の採点主軸なのに
  未注入。en 属性の注入は catchphrases + tone だけになる。
- `speech_style`(115/140 が保有。「口調・人称・語尾・口癖の連動」を 1 行で記した
  最も個性密度の高いフィールド)もどこにも注入されない。

**提案**: `_render_prompt` に 3 行追加する。

```
## First person: オレ / 俺
## Lexical markers: gonna / y'all / ...
(speech_style は tone セクションへ合流 or 1 行追加)
```

コストは 1 属性あたり +10〜30 トークン程度で、個性への効果と
measure との整合(注入した内容を採点する)が得られる。
`speech_style` は「注入する」か「フィールド廃止」かの方針決定を推奨
(現状はファイルにあるだけの死荷重)。

### A-2. 基幹 speech 8 属性が tone / sentence_endings / second_person 全欠落

`archaic / boku_girl / kansai_ben / keigo / onee_kotoba / ore_boy / third_person / whispery`
(最古参かつ最頻用と思われるレジスタ群)は上記 3 フィールドが**全て無い**。実測:

- `render_blend(["keigo"])` の注入ブロックは **catchphrase 5 行のみ**(118 chars)。
  「ですます / ございます統一」という keigo の本質は `notes:` にしか書かれておらず、
  notes は注入されない。
- `measure_intensity(text, [keigo])` は **None**(採点不能)を返す。
  語尾も一人称もシグナルが無いため。

**提案**: この 8 属性に `tone` / `sentence_endings` / `second_person` / `first_person`
(該当するもの)をバックフィルする。これはトークンを**増やす**変更だが、
「個性が出る」目的に直結し、measure 不能も解消する。1 属性 +50〜100 トークン程度。

### A-3. archetype は 9 属性中 7 つが core_traits / tone なし

`heroine` の注入ブロックを実測したところ catchphrase 5 行のみ。archetype は
「役割」を与えるカテゴリなのに、注入に役割の中身(core_traits / tone)が乗らない。
`mentor` / `rival` 等 7 属性へのバックフィルを推奨(A-2 と同じ性質の改善)。

---

## B. トークン削減(毎セッション注入されるもの)

### B-1. 固定ディレクティブが注入ブロックの 6〜7 割を占める

実測(moderate):

| blend | 全体 | 固定部 (header + Intensity 節) | 固定部比率 |
|---|---|---|---|
| keigo 単体 | 1,133 chars | 1,016 | 90% |
| tsundere + keigo | 1,681 chars | 1,039 | 62% |

削減余地(`attach.py::response_style_directive`):

1. **「When blending multiple attributes, adapt personality catchphrases …」
   (約 200 chars ≒ 40 tok)が単一属性でも常に注入される。**
   `len(attrs) > 1` のときだけ出すよう `is_blend` フラグを追加する。単一属性
   セッションで確実に 40 tok/ターン節約、挙動変化なし。
2. sentence_endings が無い属性でも「…and sentence endings as a repertoire /
   don't stamp the same ending…」が入る(keigo 単体で該当)。
   `has_sentence_endings` は既に引数にあるので文言を条件分岐すれば良い。
3. 「use them only when they fit」と末尾の「Prioritize conversational sense;
   never break grammar to force a catchphrase in.」は意味が重なる。
   1 文に統合して 15〜20 tok 削減可。

合計で固定部から **60〜80 tok/セッション** 程度削れる見込み。
CLAUDE.md の方針どおり、変更は `response_style_directive` に集約して行う
(SOUL.md 生成も同関数を使うため両方に効く)。

### B-2. `mandarin_casual` の tone にメンテナ向けノートが混入【バグ】

`attributes/speech/mandarin_casual.yaml` の `tone`(507 chars)の後半約 280 chars は
「Note: BASE catchphrases are authored in zh … (Pitfall 27-A is about …)」という
**スキーマ運用の説明文**で、ペルソナの口調ではない。これが毎セッション
persona tone としてそのまま注入されている。

**提案**: 該当部分を `notes:` フィールドへ移動する(純減 ~60 tok、個性ノイズも除去)。

### B-3. `when` トリガ注記は削らないことを推奨

catchphrase の `when`(158 個、平均 25 字)はトークンを食うが、
「口癖を状況に紐づける」= 個性が形骸化しない仕組みの中核なので維持が妥当。
露出量は既に `catchphrase_subset`(mild 5 / moderate 10 / strong 15)で制御されている。

---

## C. ファイルの無駄(注入されないがリポジトリ・コンテキストのコスト)

### C-1. `examples` が全体の 29%(135KB / 469KB)を占める

`examples` は attach / SOUL / export のどこにも使われない
(authoring の必須フィールドと show 表示のみ)。毎ターンのコストではないが、
エージェントが YAML を読む際・リポジトリの保守では最大の重量物。

- うち **16 ファイルは examples が catchphrases の完全コピー**(情報量ゼロ):
  archetype 7 (childhood_friend, gamer_otaku, heroine, mentor, rival,
  robot_android, shrine_maiden) + speech 9 (boku_girl, keigo, onee_kotoba,
  ore_boy, princess_speech, stutter, third_person, tomboy)。
- tsundere.yaml のような「7 パターンの会話例」は品質ドキュメントとして価値がある
  ので維持。一方、コピー 16 件は A-2 / A-3 のバックフィル時に
  「実際の会話例 2〜3 個」へ差し替えるのが一石二鳥。

### C-2. 該当なし: `use_cases/` は良好

8 パックの行単位重複を集計したところ余剰は **19 バイトのみ**
(共通ボイラープレートの複製なし)。レンダリング後 1.7〜2.1KB/パックで、
同時に 1 つしか適用されない設計のため現状維持で問題なし。

---

## 推奨実行順

| 順 | 項目 | 種別 | トークン | 個性 |
|---|---|---|---|---|
| 1 | B-2 mandarin_casual の tone からノート除去 | バグ修正 | −60 tok | ノイズ除去 |
| 2 | B-1 固定ディレクティブの条件分岐・統合 | コード | −60〜80 tok | 変化なし |
| 3 | A-1 first_person / lexical_markers の注入追加 | コード | +10〜30 tok | 大 + measure 整合 |
| 4 | A-2 基幹 speech 8 属性のバックフィル | YAML | +50〜100 tok/属性 | 大 + measure 不能解消 |
| 5 | A-3 archetype 7 属性のバックフィル | YAML | +微増 | 中 |
| 6 | C-1 examples コピー 16 件の差し替え | YAML | 0(注入外) | 保守性 |

ネットでは「無駄な固定費を削り、その分を個性を担うフィールドに再配分する」形になる。

**運用ノート**: 属性 YAML を編集した場合は `python scripts/build_site.py` で
`docs/app/data.json` の再生成が必要(CI の `--check` ゲート対象)。
`speech_style` を注入対象に変える場合は README EN/JA・`docs/PUBLIC_API.md`・
CHANGELOG の同期が CLAUDE.md ルールで必須。
