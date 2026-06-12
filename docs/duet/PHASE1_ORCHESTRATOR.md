# Phase 1 詳細設計: orchestrator CLI — 完全自動で 1 シーン

> 実装先: **hersona-duet リポジトリ (新規作成)**。依存: Phase 0 完了
> (`hersona>=1.2,<2`。PyPI 未公開の間は `uv add git+https://github.com/shiro-0x/hersona`)。
> ゴール: `duet scene run scene.yaml --project project.yaml` で「買い物のシーン」が
> 台本 Markdown として出力される。

## 1. リポジトリ初期化

```
hersona-duet/
├── duet/
│   ├── __init__.py
│   ├── providers.py      # §3
│   ├── script.py         # §2 データモデル + 出力
│   ├── casting.py        # §4
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base.py       # §5
│   │   ├── writer.py     # §5.2
│   │   ├── narrator.py   # §5.3
│   │   └── actor.py      # §5.4
│   ├── orchestrator.py   # §6
│   ├── quality.py        # §6.4
│   ├── config.py         # §2.1 YAML ロード/検証
│   └── cli.py            # §8
├── prompts/              # 同梱スタッフプロンプト (writer_ja.md, narrator_ja.md, en 版)
├── packs/examples/cafe/  # サンプル: project.yaml + scenes/shopping.yaml
├── tests/
├── pyproject.toml        # deps: hersona, pyyaml / extras: anthropic, openai
└── README.md
```

`pyproject.toml`: `[project.scripts] duet = "duet.cli:main"`。
SDK (anthropic/openai) は optional-dependencies (`duet[anthropic]` 等)。ollama は HTTP 直叩きで依存なし。

## 2. 設定ファイル仕様 (config.py)

### 2.1 project.yaml

```yaml
title: 放課後カフェ物語
language: ja                      # ja | en (シーンで上書き可)
world: |
  現代日本の小さな商店街。高校生たちの日常。
story: |
  幼なじみ二人の、すれ違いと和解の物語。
defaults:
  llm: { provider: anthropic, model: claude-haiku-x, temperature: 0.8, max_tokens: 1024 }
staff:
  writer:
    prompt: prompts/writer_ja.md   # 職能プロンプト (hersona 不使用)
    llm: { provider: anthropic, model: claude-opus-x }   # 省略時 defaults.llm
  narrator:
    prompt: prompts/narrator_ja.md
actors:
  - id: rinka
    name: 凛花
    role: 主人公の幼なじみ。商店街の和菓子屋の娘
    hersona: [tsundere, kyoto_ben]   # hersona 属性ブレンド
    weight: moderate                  # none/mild/moderate/strong
    relationships: { kenta: 幼なじみ。素直になれない }
  - id: kenta
    name: 健太
    role: 主人公
    hersona: [optimist]
    weight: mild
```

### 2.2 scene.yaml

```yaml
id: shopping_01
title: 買い物のシーン
location: 商店街の雑貨屋
time: 放課後
goal: 凛花が素直になれないまま、健太への誕生日プレゼントを選ぶ
participants: [rinka, kenta]      # actors の id。ナレーターは常に暗黙参加
notes: 凛花は店員に話しかけられると標準語になってしまう   # 任意の演出メモ
max_turns: 24                      # アクター発話の総予算 (既定 24)
language: ja                       # 省略時 project.language
```

### 2.3 検証規則 (config.load_project / load_scene)

- `actors[].id` は一意・snake_case。`participants` は actors に存在する id のみ
- `hersona` の各属性名は `hersona.core.available_attributes()` に存在すること
  (存在しない場合は候補をエラーに含める)
- `weight` は `hersona.core.coerce_level` で検証
- 検証エラーは `DuetConfigError(messages: list[str])` に集約して一括報告

## 3. providers.py — LLM プロバイダ抽象

```python
@dataclass(frozen=True)
class LLMConfig:
    provider: str            # "anthropic" | "openai" | "ollama" | "fake"
    model: str
    temperature: float = 0.8
    max_tokens: int = 1024
    api_key_env: str | None = None   # 既定: ANTHROPIC_API_KEY / OPENAI_API_KEY

class Provider(Protocol):
    def complete(self, *, system: str, user: str, cfg: LLMConfig) -> str: ...

def get_provider(cfg: LLMConfig) -> Provider:
    """provider 名で実装を解決。SDK 未インストールなら導入方法を含む DuetProviderError。"""
```

- 入力は **system + 単一 user メッセージ**に正規化する (マルチパーティ会話を
  role 交互形式に無理に写像しない。文脈は user 文字列に整形して渡す — §5.1)
- リトライ: 429/5xx は指数バックオフで 3 回。それ以外は即時 `DuetProviderError`
- `FakeProvider`: コンストラクタに `responses: list[str]` を取り FIFO で返す (テスト用)

## 4. casting.py — 配役解決

```python
@dataclass
class CastMember:
    id: str
    name: str
    role: str
    persona_prompt: str            # hersona render_blend(...).prompt ("" if hersona なし)
    attributes: list[dict]         # BlendResult.attributes (intensity 測定に使用)
    weight: WeightLevel
    conflicts: list[tuple[str, str]]
    llm: LLMConfig
    human: bool = False            # Phase 2 で使用

def build_cast(project: Project) -> dict[str, CastMember]
```

- `render_blend(actor.hersona, weight=actor.weight)` で注入ブロック生成
- `conflicts` が非空なら警告ログ (中断はしない — 配役のドラマとして意図的な場合がある)

## 5. エージェント

### 5.1 base.py

```python
@dataclass
class TurnContext:
    project: Project
    scene: Scene
    beat: Beat
    transcript_tail: list[Utterance]   # 直近 N=12 発話
    instruction: str                   # このターンへの指示 (orchestrator が組み立て)

class LLMAgent:
    def __init__(self, *, agent_id: str, system_prompt: str, llm: LLMConfig): ...
    def respond(self, ctx: TurnContext) -> str:
        """system=system_prompt, user=format_context(ctx) で provider を呼ぶ。"""
```

`format_context(ctx)` の整形 (全エージェント共通・テスト対象):

```
# 作品設定
{world / story の要約}
# 現在のシーン
{title / location / time / goal / notes}
# 現在のビート
{phase}: {goal} (対立の種: {conflict_seed})
# 直近のやりとり
凛花「……べ、別に、あんたのために選んでるんと違うし」
（ナレーション）夕暮れの店内に、オルゴールの音が流れる。
# あなたへの指示
{instruction}
```

### 5.2 writer.py — シナリオライター

```python
def build_beatsheet(project: Project, scene: Scene, *, agent: LLMAgent) -> BeatSheet
def judge_beat_done(beat: Beat, transcript_tail: list[Utterance], *, agent: LLMAgent) -> bool
```

- system prompt = `staff.writer.prompt` のファイル内容 (職能プロンプト。同梱版は
  「プロの脚本家。台詞は書かない。各ビートは目的と出口条件を持つ」を明記)
- `build_beatsheet` は **JSON 出力契約**: 次の形を強制し、parse 失敗時は
  エラーメッセージを添えて最大 2 回リトライ。それでも失敗なら `DuetWriterError`

```json
{"logline": "...", "beats": [
  {"phase": "ki",    "goal": "...", "conflict_seed": "...", "exit_condition": "...",
   "participants": ["rinka", "kenta"], "max_turns": 6},
  {"phase": "sho", ...}, {"phase": "ten", ...}, {"phase": "ketsu", ...}]}
```

- 制約: beats は 3〜8 個。phase は ki/sho/ten/ketsu の昇順 (同 phase 複数可)。
  participants ⊆ scene.participants。**台詞・固有の言い回しを goal に書かない**
- `judge_beat_done`: 「このビートの exit_condition は満たされたか」を YES/NO で
  回答させ、YES 以外は False (保守的)

### 5.3 narrator.py — ナレーター

```python
def narrate(ctx: TurnContext, *, agent: LLMAgent) -> str
```

- ビート開始時と、orchestrator が要求した時 (§6.2) に 1〜3 文の情景描写を返す
- system prompt = `staff.narrator.prompt`。制約: 台詞を書かない・心理の断定をしない
  (描写から滲ませる)・1 回 120 文字以内 (ja) / 60 words (en)

### 5.4 actor.py — アクター

```python
def act(ctx: TurnContext, member: CastMember, *, agent: LLMAgent) -> Utterance
```

- system prompt の組み立て順 (この順序は固定・テスト対象):
  1. `member.persona_prompt` (hersona 注入ブロック。空なら省略)
  2. キャラクターシート: 名前 / role / relationships
  3. 共通演技規則: 「1 発話 1〜3 文。地の文を書かない。ト書きは（）で 1 つまで。
     他人の台詞を書かない。シーン言語 ({language}) で話す」
- instruction には「あなたは {name}。直近のやりとりに続けて、ビートの目的に沿い
  人格を保って発言せよ」+ ビートの conflict_seed を含める
- 出力後処理: 先頭の「{name}:」「{name}「」等の自己ラベルを strip (正規表現、テスト対象)

## 6. orchestrator.py — シーン進行ループ

### 6.1 メインループ (擬似コード)

```
run_scene(project, scene, *, measure=False, on_event=None) -> SceneScript:
  cast = build_cast(project); agents = init_agents(project, cast)
  beats = writer.build_beatsheet(project, scene)
  emit(beat_sheet)
  total = 0
  for beat in beats.beats:
    emit(beat_start); turns = 0
    add(narrator.narrate(...))                       # ビート冒頭の情景
    while turns < beat.max_turns and total < scene.max_turns:
      speaker = select_speaker(beat, transcript)     # §6.2
      if speaker == NARRATOR: add(narrator.narrate(...)); continue  # ターン消費しない
      utt = actor.act(...); add(utt); turns += 1; total += 1
      if measure: quality.annotate(utt, cast[speaker])
      if turns % 2 == 0 and writer.judge_beat_done(beat, tail): break
    emit(beat_end)
  return SceneScript(status="draft", ...)
```

### 6.2 発話者選択 `select_speaker` (純粋関数・最重要テスト対象)

優先順位:
1. ビート参加者 (`beat.participants`) 以外は候補にしない
2. 直前のアクター発話が他の参加者名 (name または id) を含む → その参加者
3. それ以外はラウンドロビン (参加者リスト順)
4. **同一話者の連続は禁止** (参加者が 1 人のビートを除く)
5. アクター発話 4 回ごとにナレーター挿入を 1 回許可 (場面転換の呼吸)

### 6.3 停止保証

- ビート単位 `beat.max_turns` (既定 6)、シーン単位 `scene.max_turns` (既定 24) の二重予算
- LLM 呼び出し総数の上限 = `scene.max_turns * 3` (writer/narrator 込みの安全弁)。
  超過時は `DuetBudgetError` で現在までの script を保存して終了

### 6.4 quality.py

```python
def annotate(utt: Utterance, member: CastMember) -> None:
    """verify_intensity(utt.text, member.attributes, member.weight) を呼び
    utt.meta["intensity"] = {"score": .., "status": "pass|under|over"} を付与。
    None (speech 属性なし) の場合は何もしない。"""
```

## 7. script.py — データモデルと出力

```python
@dataclass
class Utterance:
    kind: Literal["narration", "line"]
    speaker: str                  # actor id / "narrator"
    text: str
    beat_index: int
    meta: dict = field(default_factory=dict)

@dataclass
class Beat:        # writer の JSON と 1:1
    phase: Literal["ki", "sho", "ten", "ketsu"]
    goal: str
    conflict_seed: str = ""
    exit_condition: str = ""
    participants: list[str] = field(default_factory=list)
    max_turns: int = 6

@dataclass
class SceneScript:
    scene_id: str
    title: str
    beats: list[Beat]
    utterances: list[Utterance]
    status: Literal["draft", "approved"] = "draft"
    meta: dict = field(default_factory=dict)   # 生成時刻・モデル名・コスト概算

def to_screenplay_md(s: SceneScript) -> str   # 台本体: 「凛花「…」」+（ナレーション）
def to_novel_md(s: SceneScript) -> str        # 小説体: 地の文に台詞を織り込む整形のみ (LLM 不使用)
def to_json(s: SceneScript) -> str
def save(s: SceneScript, path: Path) -> None  # JSON 保存 (Phase 2 のレジューム素体)
```

## 8. cli.py

```
duet scene run <scene.yaml> --project <project.yaml>
     [--out out.md] [--format screenplay|novel|json] [--measure]
     [--max-turns N] [--verbose] [--lang ja|en]
duet validate <project.yaml>        # 設定検証のみ (LLM 呼び出しなし)
duet cast <project.yaml>            # 配役一覧 + conflict 警告表示
```

- `--verbose`: 発話をリアルタイムで stdout に流す (進行が見える)
- 終了コード: 0 成功 / 1 設定エラー / 2 プロバイダエラー / 3 予算超過

## 9. テスト計画

| # | テスト | 種別 |
|---|---|---|
| T1 | config: 正常系ロード / 未知属性 / 重複 id / 不正 weight の集約エラー | unit |
| T2 | providers: FakeProvider の FIFO / 未知 provider 名のエラー | unit |
| T3 | casting: render_blend 連携 (hersona 実データ) / conflict 警告 | unit |
| T4 | writer: JSON 契約 — 正常 parse / 不正 JSON →リトライ→DuetWriterError / beats 制約違反検出 | unit (Fake) |
| T5 | select_speaker: 言及優先 / ラウンドロビン / 連続禁止 / 参加者 1 人 / ナレーター挿入間隔 | unit |
| T6 | actor: system prompt 組み立て順 / 自己ラベル strip | unit (Fake) |
| T7 | orchestrator: Fake 台本での E2E — ビート消化 / 二重予算による停止 / DuetBudgetError | integration (Fake) |
| T8 | script: 3 形式の出力スナップショット / save→load 往復 | unit |
| T9 | quality: speech 属性あり/なしの annotate | unit |
| T10 | live: 実 API で shopping.yaml 1 シーン (手動・CI 除外) | live |

## 10. 受け入れ基準

- [ ] `duet validate packs/examples/cafe/project.yaml` が exit 0
- [ ] `duet scene run packs/examples/cafe/scenes/shopping.yaml --project ... --measure --out out.md`
      が台本 Markdown を出力し、各アクター発話に intensity バッジが付く (live 環境)
- [ ] FakeProvider のみで T1〜T9 が CI でパス
- [ ] 1 シーンの LLM 呼び出し回数が `max_turns*3` を超えない
