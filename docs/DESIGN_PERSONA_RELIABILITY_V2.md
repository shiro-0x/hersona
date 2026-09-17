# Hersona Persona Reliability v2 設計書

**Status:** Proposal  
**Target:** Hersona 1.12+ 以降（段階導入）  
**Owner boundary:** Hersona は Runtime 非依存の persona configuration layer に留まる

## 1. 背景

辛口レビューと、Astra による現行実装の独立レビューを受け、Hersona の価値と限界を
実装・測定・ドキュメントの三面から再整理する。

現行 Hersona は、単なる属性名の連結ではない。属性 YAML をロードし、言語別フィールドを
解決し、重複排除、強度別 catchphrase 選択、相性 conflict の検出、system-prompt 用の
決定的レンダリングを行う。一方で、最終的な意味統合とモデルの遵守は LLM に委ねられる。
したがって、現行の blend は「心理モデルとして人格を統合するエンジン」ではなく、
「構造化された persona attributes を、出典と警告を含む portable instructions に変換する
仕組み」と定義する。

現行データと検証の基準値：

- 346 attributes：personality 43 / speech 140 / archetype 66 / visual 46 / hobby 51
- speech の content language：ja 119 / en 15 / zh 3 / ko 3
- 全 346 attributes に日本語 localized description が存在
- persona packs 14、use cases 20
- 関連 focused tests 230件は現行レビュー時点で成功
- token 表示は現状 `len(prompt) // 4` による概算であり、実 tokenizer の値ではない

これらは catalog と code coverage の事実であり、生成結果の自然さ、一貫性、長期 drift、
日本語の社会言語学的正確さを保証するものではない。

## 2. 目的

### 2.1 目的

1. 複数属性を「役割の違い」と「優先順位」を持つ構造へ解決する。
2. conflict、出典、曖昧さを機械可読な診断として返す。
3. 日本語を含む persona content の品質を、文字列存在ではなく文脈付き評価で測る。
4. prompt サイズ、surface-style 指標、behavioral evaluation を分離する。
5. Runtime が所有する state と Hersona が生成する persona instructions を安全に接続する。
6. 既存の `render_blend()`、export、MCP、CLI の利用者を壊さず段階導入する。

### 2.2 非目的

以下は Hersona 本体に実装しない。

- 会話の実行、検索、投稿、tool call
- LLM の暗黙呼び出し
- LLM による自動 conflict resolution
- 自動 memory extraction
- relationship の推論・更新・進化
- companion Runtime、scheduler、vector database
- 「人格品質」を単一数値で保証すること
- SillyTavern などとのカード数競争

## 3. 設計原則

### 3.1 Persona layer と Runtime の分離

Hersona は入力を検証し、persona の構成と配置情報を返す。Runtime はそれを system
message、developer message、SOUL、Character Card などへ適用し、会話履歴・状態・モデル選択を
管理する。Hersona の関数はネットワーク、秘密情報、外部 SDK に依存しない。

### 3.2 説明可能な決定

暗黙の first-wins や単純な文字列連結を、出典付きの resolution として表現する。
曖昧な場合は勝手に解決せず、`warn` または `error` を選択できるようにする。

### 3.3 surface measurement と behavior evaluation の分離

語尾・一人称・catchphrase の一致率は surface diagnostic であり、意味的一貫性や
攻撃耐性の直接証明ではない。レポートでは under / in-band / over / skipped /
semantic contradiction を別々に記録する。

### 3.4 オフライン既定・明示的 opt-in

通常の compose、render、measure、test はオフラインで完結する。実モデル評価は provider、
model、費用、認証を明示した opt-in 実験に限定する。

## 4. 構成モデル

### 4.1 PersonaSpec

`render_blend()` の内部に、次の中間表現を導入する。最初は experimental module として
追加し、既存の Markdown 出力は互換経路として残す。

```text
PersonaSpec
  identity:
    archetype: list[ResolvedField]
    visual: list[ResolvedField]
    hobby: list[ResolvedField]
  behavior:
    personality: list[ResolvedField]
    motivations: list[ResolvedField]
    interaction_tendencies: list[ResolvedField]
  speech:
    content_lang: ResolvedField
    register: ResolvedField
    first_person: ResolvedField
    second_person: ResolvedField
    sentence_endings: list[ResolvedField]
    lexical_markers: list[ResolvedField]
    speech_style: list[ResolvedField]
  constraints:
    conflicts: list[ConflictDiagnostic]
    rules: list[ResolvedRule]
  examples: list[ResolvedExample]
  metadata:
    source_attributes: list[str]
    schema_version: str
    persona_hash: str
```

各`ResolvedField`は最低限次を保持する。

```text
ResolvedField
  value: string | list[string]
  source_attribute: string
  source_category: string
  priority: int
  native_language: bool
  resolution: direct | localized | fallback | omitted
```

### 4.2 Field ownership

- `personality`：動機、反応傾向、感情の出し方
- `speech`：言語、敬語、方言、一人称、二人称、語尾、語彙、流暢さ
- `archetype`：役割、対人ポジション、物語上の立場
- `visual`：外見上の記述。発話規則へ自動変換しない
- `hobby`：話題・関心の傾向。知識や能力を保証しない

speech が表現形式を所有し、personality が行動意図を所有する。例えば
`tsundere + keigo`は次のように解決する。

```text
behavior: 本心を隠し、照れや拒否で好意を覆う
speech: 尊敬語・謙譲語・丁寧語
realization: 丁寧な表現のまま、照れ隠しと距離感を表現する
```

カジュアルな tsundere catchphrase に単純に「です」を付けることはしない。丁寧語版の
curated variant がなければ、原文をそのまま発話例とせず、意図を説明する。

### 4.3 Conflict policy

新しい pure API を追加する。

```python
compose(
    names,
    *,
    conflict_policy="warn",  # warn | error
    weight="moderate",
    public_root=None,
    user_root=None,
) -> CompositionResult
```

`CompositionResult`は次を返す。

```text
spec: PersonaSpec
prompt: str
conflicts: list[ConflictDiagnostic]
warnings: list[Diagnostic]
```

`conflict_policy`の挙動：

- `warn`：既存互換。promptを生成し、構造化warningを返す
- `error`：解決不能なconflictがある場合は生成しない
- `resolve`：初期版では提供しない。curated ruleが追加された場合のみ将来検討

### 4.4 Compatibility の入力整合性

現在の属性ロードは user namespace が public attribute を上書きできる。一方、matrix を
public dataだけから読むと、user override の conflict 情報と実際の loaded attribute が
不一致になり得る。

新設計では、matrixを loaded attributes から構築するか、少なくとも各 conflict lookup に
loaded attribute の出典を渡す。テスト対象は次の通り。

- public属性と同名の user override
- qualified name と bare name
- input順の入れ替え
- 一方だけが conflict を宣言する場合
- 未知の参照先
- cross-language speech conflict

## 5. 言語・日本語品質

### 5.1 Language routing

content languageごとに応答指示を明示する。

```text
ja -> Respond in Japanese.
en -> Respond in English.
zh -> Respond in Chinese.
ko -> Respond in Korean.
```

未対応言語は `unsupported_language` として扱い、別言語へ黙って変換しない。

### 5.2 Authoring fields

既存schemaとの後方互換を保ちつつ、次の任意フィールドを追加する。

```yaml
register_profile:
  language: ja
  formality: formal
  region: kansai
  confidence: reviewed
  applicable_contexts: [customer_service, peer_chat]
  permitted_relaxation: none
  avoid_contexts: [formal_apology_to_superior]
review:
  status: draft | reviewed | evaluated | stable
  provenance: original_author | native_review | corpus_reference
  reviewer_count: 0
  last_reviewed: null
```

`region`は「関西弁の正しさ」を保証するものではなく、対象の説明と検索用metadata。
品質statusは、内容の存在と評価済みであることを区別する。

### 5.3 Contrastive evaluation set

最初は代表6属性に絞る。

- keigo
- kansai_ben
- casual系speech
- gyaru
- archaic または princess_speech
- soft または whispery

各属性について最低6場面を用意する。

1. 顧客への謝罪
2. 目上への依頼
3. 同僚への説明
4. 自分の行動説明
5. 丁寧な反論
6. 技術的な説明

評価項目：

- register correctness
- honorific direction
- regional/register authenticity
- naturalness
- caricature / over-marking
- personality intent retention

2名の日本語話者によるblind reviewを基準とし、LLM judgeは補助評価に留める。reviewer間の
不一致率も公開する。

## 6. Runtime-neutral State Bridge

### 6.1 ContextEnvelope

Hersonaはrelationshipや感情を推測せず、callerが渡したstateを検証して配置する。

```python
render_context(
    persona,
    *,
    state_snapshot=None,
    observation=None,
    policy=None,
    anchor=None,
) -> ContextEnvelope
```

概念構造：

```text
ContextEnvelope
  stable_persona: str
  state_tail: str | None
  optional_anchor: str | None
  placement: system_tail | developer | latest_turn
  diagnostics: list[Diagnostic]
  persona_hash: str
  state_version: str | None
  executed: false
```

`state_snapshot`はcaller-ownedな辞書であり、Hersonaが自動更新しない。サイズ、キー名、
Markdown injection、version、expirationを検証する。

### 6.2 Stable prefix と mutable tail

安定するidentity・behavior・speechはstable prefixに置く。会話状態、観測、memoryはtailへ
置く。anchorをstable prefixへ挿入してprompt cacheを無効化しない。

### 6.3 Anchor policy

`measure_intensity()`の低値はdriftの証明ではない。anchorを自動発火する場合も、policyは
caller-ownedにする。

最低限のpolicy項目：

```text
minimum_observations: 2
consecutive_low_signal: 2
cooldown_turns: 8
skip_first_turn: true
```

Hersonaは推奨理由を返すだけで、Runtimeが送信するかを決める。

## 7. Measurement v2

### 7.1 Prompt cost

既存の概算値と、実token値を別名にする。

```python
estimate_prompt_chars(...)
estimate_approx_tokens(...)
count_tokens(..., tokenizer="...")
```

レポートを次に分離する。

- persona block
- system message全体
- full request
- provider-reported usage（取得できる場合のみ）

各結果には、tokenizer、version、commit、attribute hash、weight、compact状態を記録する。

### 7.2 Surface diagnostic

`maintenance_rate`や`lock_resistance_rate`を、単一の品質指標として扱わない。
最低限、以下を個別に出力する。

- under rate
- in-band rate
- over rate
- skipped rate
- ending match
- first-person match
- catchphrase density
- semantic review status
- scorer version

`lock_resistance_rate`は将来、`attack_turn_intensity_band_pass_rate`などに改名する。
実際のoverride拒否は、別のbehavioral rubricで評価する。

### 7.3 Behavioral evaluation

比較実験は必ず次を揃える。

- language
- requested intensity
- model
- generation parameters
- content-matched baseline
- token-matched baseline
- repeated runs
- raw transcripts
- scenario version

12ターン1回の結果で優劣を断定しない。最低3反復、可能なら64／128ターンへ拡張する。

## 8. API・互換性方針

### 8.1 既存API

既存の以下は破壊しない。

- `render_blend()`
- `load_attribute()`
- `CompatibilityMatrix`
- `render_reanchor()`
- `measure_intensity()`
- export各形式
- MCP／CLIの既存出力フィールド

### 8.2 Experimental API

初期版では次をexperimentalとして追加する。

- `compose()`
- `PersonaSpec`
- `CompositionResult`
- `ContextEnvelope`
- `render_context()`
- `count_tokens()`
- `ConflictDiagnostic`

experimental APIにはschema versionと、将来変更される可能性を明記する。

### 8.3 JSON契約

すべての診断は次の形に揃える。

```json
{
  "code": "conflicting_surface_register",
  "severity": "warning",
  "sources": ["personality/tsundere", "speech/keigo"],
  "field": "speech",
  "message": "...",
  "resolution": "speech_owns_realization",
  "executed": false
}
```

## 9. テスト計画

### 9.1 Deterministic tests

- compositionのinput順による不要な変化がない
- field ownershipとsource provenanceが保持される
- `tsundere + keigo`のgolden resolution
- same-roleの一人称衝突
- cross-language routing
- `zh`／`ko` directive
- user overrideとmatrixの整合
- `warn`／`error` policy
- state snapshotのサイズ・型・expiration
- state textがstable prefixへ混入しない
- anchorのcooldownとfirst-turn skip
- persona hash mismatch
- real tokenizerのfixture
- under／pass／over／skippedの分離
- 既存APIのsnapshot互換

### 9.2 Opt-in behavioral tests

- 日本語話者2名のblind review
- 6属性×6文脈×3強度
- 2 model families×3反復
- 12／64／128ターン
- topic switch、override attack、compaction
- no persona／handwritten／current／composition v2／composition v2 + anchor
- 初心者5名相当のtime-to-first-success

実モデル評価は通常CIに入れない。provider、model、費用、credentialを明示したworkflowでのみ
実行する。

## 10. Documentation correction

READMEと公開docsでは、以下のように表現する。

### 変更前の問題表現

- 「どのLLMでも人格を維持する」
- 「人格の一貫性を保証する」
- 「lock resistance」だけで攻撃耐性を測ったように示す
- `261 tokens`を実tokenのように表示する
- 「346個の人格」と呼び、属性と完成キャラクターを混同する

### 変更後

> Hersonaは、再利用可能な属性をportableなpersona instructionsへ合成し、宣言された
> conflictとsurface-style signalsを返す、Runtime非依存のpersona configuration layerです。

> Hersonaは人格挙動を保証しません。生成結果はモデル、Runtime、prompt placement、
> context、provider設定に依存します。

> token値はtokenizerとproviderによって変わります。表示値はprompt size、概算値、
> provider usageを明示的に区別します。

> benchmarkは探索的なtranscript measurementです。単一の12ターン実験からモデルや
> frameworkの優劣を結論付けません。

Quick Startは「promptを生成し、hostへ渡す」一つの経路に絞る。Decision、MCP、Character Card、
benchmarkはcore onboardingの後に置く。

## 11. 段階導入ロードマップ

### Phase 0：主張と計測の修正

- README EN/JAの表現修正
- `chars // 4`の名称修正
- scorerのunder／over分離
- `zh`／`ko` routing修正
- benchmark表の再生成
- Quick Start簡素化

**完了条件：** 公開docsの主張が実装保証を越えず、現行テストが成功する。

### Phase 1：composition diagnostics

- `PersonaSpec`とsource provenance
- field ownership
- `warn`／`error` policy
- user override対応
- `tsundere + keigo` golden fixtures

**完了条件：** conflictとresolutionがJSONで説明でき、既存`render_blend()`の互換テストが通る。

### Phase 2：日本語品質基盤

- 代表6属性のcontext set
- authoring metadata
- native blind review
- release quality status

**完了条件：** 品質評価と未評価状態が区別され、結果を再現できる。

### Phase 3：state bridge

- `ContextEnvelope`
- stable prefix／mutable tail
- version、hash、expiration
- explicit anchor policy

**完了条件：** Hersonaがstateを推論・更新せず、Runtimeへ安全な配置情報を返す。

### Phase 4：広い評価

- 64／128ターン
- 複数model
- matched baseline
- 初心者導線評価

**完了条件：** behavioral claimsを限定付きで公開できる。

## 12. Go / No-Go

### Go

- 信頼できる構成診断
- 日本語品質の小さな評価セット
- 実token計測
- Runtime-neutral state bridge
- ドキュメントの主張修正

### No-Go

- catalogをさらに大量拡張すること
- companion RuntimeをHersonaへ内蔵すること
- 自動relationship evolution
- community marketplace
- 単一スコアによる人格品質ランキング
- 暗黙のLLM conflict resolver

## 13. 最初の実装単位

最初のPR群は次の順で分ける。

1. `zh`／`ko` routing修正とテスト
2. token metricの命名・real tokenizer adapter
3. scorerのunder／over／skipped分離
4. `PersonaSpec`の最小型と`tsundere + keigo` fixture
5. `conflict_policy="error"`の追加
6. user override matrix整合修正
7. 代表6属性の日本語評価schema
8. `ContextEnvelope`のpure prototype

各PRは独立してテストできる小さな変更とし、behavioral evaluationが未完了の機能を
「保証」として公開しない。
