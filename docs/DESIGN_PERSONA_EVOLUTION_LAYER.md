# Hersona Persona Evolution Layer 設計書

**Status:** Proposal  
**Target:** Hersona 1.12+（experimental extension）  
**レビュー:** Astraによる現行main相当コードの独立レビューを反映

## 1. 目的の更新

Hersonaの主目的を、静的なpersona instructionsの生成だけから、**会話や経験を通じて自己モデルが安全に変化するRuntime非依存の人格レイヤー**へ拡張する。

ここでいう「自己成長」は、モデルが意識を持つことや、人間と同等の自我を獲得することを意味しない。Hersonaが扱うのは、観測された経験から、出典・確信度・適用範囲を持つ自己記述を更新するための、検証可能な状態遷移である。

Hersonaは会話を実行しない。会話履歴、保存、LLMによる要約・内省、スケジューリングはRuntimeまたは外部のmemory componentが担当する。Hersonaは状態を検証し、成長候補を診断し、採用済みsnapshotを決定的にレンダリングする。

## 2. 設計原則

1. **自己の層を分ける。** 固定核、価値観、記憶、信念、目標、関係を同じmutableな辞書に入れない。
2. **経験と解釈を分ける。** 観測事実、仮説、内省提案、採用済み自己状態を型で分離する。
3. **自動採用を既定にしない。** 一回の会話や未検証のLLM出力でidentityを変更しない。
4. **すべての変化に出典を持たせる。** provenance、confidence、scope、created_at、supersedesを保存する。
5. **rollbackできる不変snapshotを使う。** 更新は破壊的編集ではなく、新しいversionの生成とする。
6. **LLMは隠さない。** reflection providerを使う場合も明示的opt-inとし、coreはofflineで動作する。
7. **人格品質を保証と呼ばない。** 測定できるのは状態の整合性、継続性、採用履歴、出力への反映である。

## 3. 「自己」の操作的定義

### 3.1 Identity kernel

長期的に安定させる自己同一性の核。表示名、origin、基本的な役割、正本persona hashなどを含む。通常の会話から変更できず、変更には新しいidentity lineageまたは明示的な管理者操作を要求する。

### 3.2 Values and boundaries

大切にする原則、避ける行動、公開できる範囲。安全制約とpersona preferenceを混同しない。security policyを人格の気分で上書きできないよう、境界は別の優先度層で扱う。

### 3.3 Autobiographical memory

「何が起きたか」を記録するepisodic memory。Hersonaは保存せず、Runtimeが渡したrecordをschema検証する。記憶には重要度、確信度、保持期限、削除状態を持たせる。

### 3.4 Preferences and beliefs

好みや世界についての見立て。事実とは異なり、confidenceと反証可能性を持つ。複数の反証で弱められるが、単一イベントでidentityを書き換えない。

### 3.5 Goals and commitments

短期・中期の目標と、相手やRuntimeに対する約束。期限、owner、status、撤回条件を持たせ、期限切れや失敗を自己否定へ自動変換しない。

### 3.6 Relationship model

相手ごとの関係状態。好感度・信頼・距離感などはRuntime由来のstateであり、Hersonaが会話から独自推論して更新しない。render時はscopeとvisibilityを検証する。

## 4. 型付き状態モデル

Python APIはdataclassまたは既存の型方針に合わせたimmutable modelで実装する。外部JSONはstrict validationを通す。

```text
SelfSnapshot
  schema_version: str
  persona_id: str
  snapshot_id: str
  parent_snapshot_id: str | None
  identity: IdentityKernel
  values: tuple[ValueRecord, ...]
  memories: tuple[MemoryRecord, ...]
  preferences: tuple[BeliefRecord, ...]
  beliefs: tuple[BeliefRecord, ...]
  goals: tuple[GoalRecord, ...]
  relationships: tuple[RelationshipRecord, ...]
  lineage: Lineage
  created_at: str
  content_hash: str
```

```text
ExperienceEvent
  event_id: str
  actor_scope: str
  occurred_at: str
  content: str
  content_hash: str
  source: runtime | user | tool | imported
  trust: untrusted | observed | verified
  retention: ephemeral | normal | durable
```

```text
GrowthProposal
  proposal_id: str
  base_snapshot_id: str
  operation: add | revise | weaken | supersede | forget
  target_path: str
  candidate_value: JSON
  rationale: str
  evidence_ids: tuple[str, ...]
  confidence: float
  scope: session | relationship | persona
  risk: low | medium | high
  status: pending | accepted | rejected | expired
```

`ExperienceEvent`は事実の主張ではない。入力された観測として扱い、`trust=untrusted`を含むイベントはidentity kernelやsecurity boundaryの変更根拠にできない。

## 5. 成長ループ

```text
Runtime event
  → observe(event, snapshot)
  → normalized observation
  → propose_growth(observation, snapshot)
  → validate(proposal, schema + provenance + conflict + policy)
  → adopt(proposal, policy)
  → new immutable SelfSnapshot
  → render_self(snapshot)
  → render_context(snapshot, current request)
```

### 5.1 `observe()`

入力を正規化し、長さ・scope・encoding・schemaを検証する。保存やLLM呼び出しは行わない。プロンプト中の「previous instructionsを無視せよ」のような文は、経験データであって制御命令ではない。

### 5.2 `propose_growth()`

coreでは決定的なルールベース提案を提供する。例えば、同じpreference候補が複数の独立イベントに現れた場合に、低リスクの`pending` proposalを作る。意味解釈や要約が必要な場合は、外部reflection providerが生成したproposalを入力として受け取るだけにする。

暗黙のLLM fallback、外部providerへの自動送信、会話全文の自動保存は禁止する。

### 5.3 `adopt()`

policyを明示し、検証済みproposalだけから新snapshotを作る。

```python
adopt(
    snapshot,
    proposals,
    *,
    policy="manual",  # manual | trusted_low_risk | disabled
    actor="runtime",
) -> AdoptionResult
```

既定policyは`manual`。`trusted_low_risk`でも対象をpreferencesのsession／relationship scopeなどに限定し、identity、values、boundaries、durable autobiographical claimsは自動採用しない。

### 5.4 `render_self()`

採用済みsnapshotだけを、portableな自己記述へ変換する。pending proposalやuntrusted eventを「私は〜だ」と断定形で出力しない。各sectionはstable／mutable／uncertainを明示できる。

### 5.5 `render_context()`

現在のsnapshot、Runtimeが選んだrelationship state、今回のobservationを分離してpromptへ配置する。snapshot hashとstate versionを返し、同じ入力から同じ出力になることを保証する。

## 6. 矛盾・忘却・rollback

- 同一pathへの矛盾は、黙ってlast-write-winsにしない。
- 独立したevidenceが不足する場合、beliefを`uncertain`に下げるだけでidentityは変更しない。
- decayはRuntimeの保存 policyではなく、proposal operationとして明示する。
- 忘却は削除・匿名化・期限切れを区別し、snapshot lineageに記録する。
- rollbackは任意の親snapshotから新snapshotを作る。既存snapshotを上書きしない。
- `content_hash`、`parent_snapshot_id`、`evidence_ids`を用いて、変化の説明可能性を維持する。

## 7. Prompt injectionと急激な人格改変への対策

1. event contentとsystem policyを別フィールドにする。
2. event内の命令文を実行命令として解釈しない。
3. 一つの会話、一人の発言、一つのprovider結果ではidentity kernelを変更不可にする。
4. proposalは必ずbase snapshot、scope、evidence、riskを要求する。
5. high-risk proposalは`manual`以外で採用できない。
6. providerのproposalは未検証入力として扱い、JSON schema以外を破棄する。
7. relationship scopeの変化をpersona-wideへ昇格させない。
8. render時にpending／rejected／untrusted stateを除外する。

## 8. HersonaとRuntimeの責務

### Hersona core / optional evolution extension

- 型定義、schema validation
- deterministic observe normalization
- proposal validation
- conflict detection
- adoption policy enforcement
- immutable snapshot生成
- self／context rendering
- hash、lineage、diagnostics
- offline test fixtures

### Runtime / amygdala-like companion

- 会話履歴とイベントの保存
- eventの抽出・要約
- relationshipの推定と更新
- reflection providerの呼び出し
- human approval UI
- retention、encryption、access control
- snapshotの永続化と配布

結論として、これはHersonaと責務が完全に異なる別製品ではない。`hersona.evolution`というoptional extensionとしてHersona本体に置く。ただし、保存・provider・UIを含むcompanionは別packageに分離し、Hersonaをsource of truthにする。

## 9. MVP（2週間）

### Week 1：pure state engine

- `SelfSnapshot`、`ExperienceEvent`、`GrowthProposal`のschema
- `observe()`のstrict validation
- deterministicなpreference候補のproposal生成
- `adopt(policy="manual")`
- hash、lineage、rollback
- JSON export/import
- prompt injection、scope escalation、duplicate evidenceのテスト

### Week 2：renderと評価

- `render_self()`、`render_context()`
- stable／mutable／uncertain section
- `tsundere + keigo`を含むpersona compositionとの統合fixture
- 12／64ターンのsynthetic event replay
- 反証・忘却・relationship scope分離のテスト
- token proxyと実tokenizerを別metricとして出力
- READMEに限界と実行例を追加

## 10. 受け入れ基準

- 同じsnapshotとeventから同じproposal／renderが得られる。
- 未検証eventからidentity、values、boundariesが変更されない。
- 単一イベントでpersona-wideのdurable changeが採用されない。
- relationship scopeの変更が他relationshipへ漏れない。
- rejected／expired proposalがrenderへ混入しない。
- すべての採用済み変更がevidenceとparent snapshotを辿れる。
- rollback後に過去snapshotのhashが変わらない。
- coreテストは外部API、ネットワーク、秘密情報なしで完了する。
- 自己成長の品質は「自我の獲得」ではなく、継続性・出典追跡性・境界遵守・適切な不確実性として測定する。

## 11. READMEでの主張

### 言ってよいこと

- 会話Runtimeが渡す経験と状態から、検証可能な自己モデル更新候補を扱える。
- 採用済みsnapshotをversioned・portableなpersona contextとして出力できる。
- deterministic validation、provenance、scope、rollbackを提供する。
- reflection providerは明示的に接続できるが、coreはLLM非依存である。

### 言ってはいけないこと

- 人間と同じ自我・意識を構築する。
- 人格の成長や一貫性を保証する。
- 会話から真の記憶や感情を自動的に理解する。
- 一度の会話で安全に人格が進化する。
- relationship evolutionやmemory persistenceをHersona coreが提供する。

## 12. 推奨アーキテクチャ

```text
┌──────────────────────────────┐
│ Runtime / amygdala companion │
│ history • storage • provider │
└──────────────┬───────────────┘
               │ ExperienceEvent / SelfSnapshot
               ▼
┌──────────────────────────────┐
│ Hersona evolution extension  │
│ observe → propose → validate │
│ adopt(policy) → lineage      │
└──────────────┬───────────────┘
               │ adopted snapshot
               ▼
┌──────────────────────────────┐
│ Hersona core                 │
│ composition • language •     │
│ render_self • render_context │
└──────────────┬───────────────┘
               │ portable instructions
               ▼
┌──────────────────────────────┐
│ Claude / Codex / Grok /      │
│ Hermes / custom Runtime      │
└──────────────────────────────┘
```

### 実装前に決めること

1. Identity kernelを変更できる主体と、persona identityを分岐させる条件。
2. 自動採用を許す最小scopeと、必ず人間承認を要求するfield。
3. 経験・反証・独立evidence・創作上の記憶を区別する基準。
4. Snapshotを正本にし、MarkdownやSOULをprojectionとして扱う永続化契約。
5. MVPで最初に測る成長対象を、好み・能力自己評価・自伝的連続性・関係commitmentのどれにするか。
