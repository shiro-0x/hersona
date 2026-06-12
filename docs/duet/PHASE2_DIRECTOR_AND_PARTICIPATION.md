# Phase 2 詳細設計: 監督ループ + ユーザー参加モード

> 実装先: hersona-duet。依存: Phase 1。
> ゴール: ユーザーが (a) シーン単位でレビュー/リテイクでき、(b) 登場人物として
> チャットでシーンに乱入できる。

## 1. 追加モジュール

```
duet/
├── review.py         # §2 監督レビューとリテイク
├── agents/human.py   # §3 人間アクター
├── session.py        # §4 実行状態の永続化・レジューム
└── cli.py            # §5 拡張 (scene join / scene review / scene retake)
```

## 2. review.py — 監督レビューとリテイク

### 2.1 データモデル

```python
@dataclass
class ReviewNote:
    scope: Literal["scene", "beat"]
    beat_index: int | None      # scope="beat" のとき必須
    note: str                   # 監督の注記 (自由文)
    created_at: str             # ISO8601

# SceneScript.meta["review_notes"]: list[ReviewNote] に蓄積
# SceneScript.status: "draft" → "approved" | "retake"
```

### 2.2 API

```python
def approve(script: SceneScript) -> SceneScript          # status="approved"
def request_retake(script: SceneScript, note: ReviewNote) -> SceneScript

def retake(project, scene, script, note, *, agents, on_event=None) -> SceneScript:
    """リテイク実行。
    - scope="scene": ビートシートから再生成。writer の system に監督ノートを追記
    - scope="beat":  beat_index 以降の発話を破棄し、該当ビートから再演。
      writer (judge) と全 actor の instruction に監督ノートを追記
    - 確定済み (beat_index より前) の発話は変更しない
    """
```

### 2.3 監督ノートの伝播 (仕様)

- ノートは `TurnContext.instruction` の末尾に定型で付加する:
  `「# 監督ノート (リテイク指示)\n{note}」`
- 同一シーンに対するノートは**累積**する (リテイク 2 回目は両方のノートが見える)。
  上限 5 件。超過時は古いものから要約せず単純に落とす (シンプルさ優先、文書化)
- ノートに固有名詞が含まれてもガードしない (ローカル自由の原則)

## 3. agents/human.py — 人間アクター

### 3.1 登場設定の必須化 (config.py 拡張)

```yaml
actors:
  - id: player
    human: true          # 人間アクター宣言
    name: あなた          # 必須
    role: 幼なじみの同級生  # 必須 — 「登場設定は必要」(オーナー要件)
    hersona: []          # 任意。指定時は persona ブロックを参考情報として表示する
```

検証規則: `human: true` の actor は `name` と `role` が必須。欠落は
`DuetConfigError`。`llm` 指定は無視 (警告ログ)。

### 3.2 インターフェース

```python
class HumanActor:
    """LLMAgent と同じ respond(ctx) -> str を持つが、入力ソースから発話を取得する。"""
    def __init__(self, member: CastMember, input_source: InputSource): ...

class InputSource(Protocol):
    def read_line(self, prompt_text: str, ctx: TurnContext) -> str: ...

class StdinInputSource:   # CLI 用。直近のやりとり + ビート目標を表示してから入力を促す
class QueueInputSource:   # UI/テスト用。asyncio.Queue から取得 (Phase 3 が利用)
```

- 入力コマンド (CLI):
  - 空行 = パス (発話せず次の話者へ。select_speaker は同一話者連続禁止を維持)
  - `/skip` = このビート中は自動進行 (人間をスキップ)
  - `/quit` = セッション保存して中断 (レジューム可)
- 人間の発話には intensity 測定を**適用しない** (utt.meta["human"]=True)

### 3.3 select_speaker の拡張

- 人間アクターも通常の参加者として選択候補に入る (言及されれば指名される)
- `--auto` フラグ実行時 (完全自動モード) は `human: true` の actor が participants に
  含まれていたら設定エラーにする (黙って AI 代演しない。明示性優先)

## 4. session.py — 永続化とレジューム

```python
# 保存先: ./runs/<scene_id>/<timestamp>/
#   ├── script.json      # SceneScript (発話 1 件ごとに追記保存 = クラッシュ耐性)
#   ├── beats.json
#   └── meta.json        # project/scene のハッシュ・モデル名・経過

def autosave(script: SceneScript, run_dir: Path) -> None
def load_run(run_dir: Path) -> tuple[SceneScript, RunMeta]
def resume(project, scene, run_dir, *, agents) -> SceneScript
    # 再開条件: project/scene のハッシュが一致。透明性のため不一致は明示エラー
```

## 5. CLI 拡張

```
duet scene run  ...                          # Phase 1 と同じ (完全自動 = --auto 既定)
duet scene join <scene.yaml> --project ...   # 参加モード: 人間アクターとして対話実行
duet scene review <run_dir>                  # 台本を表示 → approve / retake を対話選択
duet scene retake <run_dir> --beat N --note "もっと対立を強く"
duet scene resume <run_dir>
```

`scene join` の対話表示 (UX 仕様):

```
--- ビート 2/4 [承]: 凛花がプレゼント選びに迷い、本音を隠す ---
（ナレーション）店内の棚には、色とりどりの小物が並んでいる。
凛花「べ、別に、あんたのために来たんと違うし……これは、ついで」

[あなた / 幼なじみの同級生] 発言してください (空行=パス, /skip, /quit):
> 
```

## 6. テスト計画

| # | テスト | 種別 |
|---|---|---|
| T1 | human actor 検証: name/role 欠落で DuetConfigError / llm 指定の警告 | unit |
| T2 | QueueInputSource: 発話 / パス / skip / quit の各コマンド | unit |
| T3 | --auto と human 参加者の併用が設定エラー | unit |
| T4 | retake(scope=beat): beat_index 以前の発話が不変 / 以降が再生成される | integration (Fake) |
| T5 | 監督ノートの累積と上限 5 件 / instruction への付加形式 | unit |
| T6 | autosave: 発話ごとに script.json が更新 / resume で発話数が一致 | unit |
| T7 | resume: project 改変後のハッシュ不一致エラー | unit |
| T8 | E2E (Fake): join モードで人間発話 2 回を含むシーン完走 → review → retake → approve | integration |

## 7. 受け入れ基準

- [ ] ユーザーが幼なじみ役で乱入した買い物シーンを、リテイク 1 回を挟んで
      approve まで通せる (live 手動確認)
- [ ] `/quit` → `duet scene resume` で続きから再開できる
- [ ] T1〜T8 が CI でパス (Fake のみ)
