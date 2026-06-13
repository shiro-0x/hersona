# Phase 1 実装ハンドオフ — hersona-studio (別セッション実行用)

> 目的: 新リポジトリ **`shiro-0x/hersona-studio`** で Phase 1 (orchestrator CLI) を
> 実装するための引き継ぎ資料。権威ある詳細設計は [`PHASE1_ORCHESTRATOR.md`](./PHASE1_ORCHESTRATOR.md)、
> プロダクト定義は [`../DUET_PLAN.md`](../DUET_PLAN.md)。本書はそれを前提に、
> **実装中に確定した具体決定（仕様の差分・命名・契約の細部）** と **検証手順**、
> 末尾に **別セッションへ貼るキックオフ・プロンプト** をまとめる。
>
> 背景: 本セッションは `shiro-0x/hersona` のみスコープされており hersona-studio へ
> push できないため、設計と決定をここに保存して別セッションに引き継ぐ。

## 0. 前提の現状 (2026-06-13 時点)

- **hersona 側 Phase 0 は完了済み**。`v0.0.1` リリース済み。duet が依存する公開 API
  (`hersona.core.__all__`) は揃っており、`docs/PUBLIC_API.md` が semver 対象を明記。
  - 利用可能な公開シンボル（抜粋・duet が使うもの）:
    `render_blend`, `available_attributes`, `load_attribute`, `BlendResult`,
    `coerce_level`, `WeightLevel`, `verify_intensity`, `IntensityReport`,
    `CompatibilityMatrix`, `load_matrix`。**`_` 接頭辞の私的関数は使用禁止**。
- **hersona の実バージョンは `0.0.1`**（設計書の `>=1.2,<2` は旧前提）。PyPI 公開前は
  git 依存で入れる: `uv add "git+https://github.com/shiro-0x/hersona"` あるいは
  `pip install "hersona @ git+https://github.com/shiro-0x/hersona"`。
  pyproject の依存指定は **`hersona>=0.0.1,<1`** とする。

## 1. リポジトリ事実

| 項目 | 値 |
|---|---|
| リポジトリ | `shiro-0x/hersona-studio`（新規・MIT） |
| Python パッケージ | `duet`（設計書の契約・CLI `duet ...` に合わせる。リポジトリ名と異なってよい） |
| CLI エントリ | `[project.scripts] duet = "duet.cli:main"` |
| Python | 3.11+ / ruff / pytest（hersona と同一スタイル） |

## 2. ディレクトリ構成（確定）

```
hersona-studio/
├── duet/
│   ├── __init__.py          # 公開: Project, Scene, load_project/scene, run_scene, SceneScript, Beat, Utterance
│   ├── providers.py         # LLM 抽象 + FakeProvider（§5 の決定参照）
│   ├── script.py            # データモデル + 出力（screenplay/novel/json, save/load）
│   ├── config.py            # project.yaml / scene.yaml ロード+検証（hersona 公開 API で検証）
│   ├── casting.py           # build_cast: render_blend で注入ブロック生成
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base.py          # TurnContext, format_context, LLMAgent
│   │   ├── writer.py        # build_beatsheet(JSON契約) / judge_beat_done / DuetWriterError / BeatSheet
│   │   ├── narrator.py      # narrate + narration_instruction + 文字数クリップ
│   │   └── actor.py         # act + build_actor_system(順序固定) + 自己ラベル strip
│   ├── orchestrator.py      # run_scene, select_speaker(純粋関数), DuetBudgetError, NARRATOR_INTERVAL
│   ├── quality.py           # annotate: verify_intensity を meta["intensity"] に
│   └── cli.py               # duet scene run / validate / cast
├── prompts/                 # writer_ja/en.md, narrator_ja/en.md（同梱職能プロンプト）
├── packs/examples/cafe/     # project.yaml + scenes/shopping.yaml（§4）
├── tests/                   # §6 のテスト
├── pyproject.toml
└── README.md
```

## 3. 実装中に確定した決定（仕様への差分・細部）

設計書 `PHASE1_ORCHESTRATOR.md` を基準に、以下を確定済みとして実装すること。

### 3.1 providers.py — fake の解決方式
- `Provider` は `complete(*, system, user, cfg) -> str` の Protocol。
- `LLMConfig(provider, model, temperature=0.8, max_tokens=1024, api_key_env=None)` に
  `from_dict(data, *, fallback)` を持たせ、YAML 欠損を fallback で補完。
- 実装: `AnthropicProvider` / `OpenAIProvider` / `OllamaProvider`(HTTP 直叩き・依存なし) /
  `FakeProvider(responses: list[str])`（FIFO、**使い切ったら最後を繰り返す**、`.calls` 記録）。
- `FakeProvider` は responses 注入が必要なため registry に入れず、
  **モジュール関数 `set_fake_provider(fp)` で差し込み** → `get_provider(cfg)` が
  `provider=="fake"` のとき返す。未注入なら `DuetProviderError`。
- `_retry`: 例外時に指数バックオフ 3 回、最後は `DuetProviderError` に包む
  （SDK の例外型に依存しない `except Exception`）。

### 3.2 select_speaker — 最終シグネチャ（純粋関数・最重要テスト対象）
```python
def select_speaker(beat, transcript, state, names=None) -> str
# state: _SpeakerState(last_actor: str|None, actor_turns_since_narration: int)
# 優先順位: 参加者外除外 → (複数人かつ間隔到達で)NARRATOR → 直前発話の id/name 言及 →
#           ラウンドロビン(直前話者の次) → 参加者1人は連続可
```
- `names`（id→表示名）を**引数で明示的に渡す**（state に詰めない）。
- `NARRATOR_INTERVAL = 4`。`NARRATOR = "narrator"`。
- 「同一話者連続禁止」は参加者2人以上のとき。1人ビートは連続可。

### 3.3 actor.build_actor_system — 順序固定（テスト対象）
1. `member.persona_prompt`（空なら省略） 2. キャラクターシート(名前/role/関係)
3. 共通演技規則（言語で ja/en 切替）。
- `act()` 後に **自己ラベル strip**: 先頭の `名前「…」` は中身を取り、`名前:` `名前：` は除去
  （`member.name` と `member.id` 両方を対象に正規表現）。

### 3.4 writer — JSON 契約
- `build_beatsheet` は ```json フェンス/前後地の文を許容して最初の `{...}` を抽出 →
  検証（beats 3〜8 / phase は ki→sho→ten→ketsu 昇順 / participants ⊆ scene）。
  失敗時はエラー文を添えて**最大 2 回リトライ（計 3 回）**、なお失敗で `DuetWriterError`。
- `judge_beat_done` は YES/NO 回答で **YES 以外 False（保守的）**。

### 3.5 orchestrator — 停止保証
- 二重予算: `beat.max_turns`（既定6）+ `scene.max_turns`（既定24）。
- LLM 呼び出し総数上限 = `scene.max_turns * 3`。超過で `DuetBudgetError(message, script)`
  （現在までの script を保持。CLI は `--out` 指定時に部分保存して exit 3）。
- アクター発話 2 回ごとに `judge_beat_done` でビート消化判定。
- `on_event(kind, data)` コールバックで `beat_sheet/beat_start/narration/line/beat_end` を発火
  （CLI `--verbose` がこれを表示）。

### 3.6 quality
- `annotate(utt, member)`: `verify_intensity(utt.text, member.attributes, member.weight)`。
  `None`（speech 属性なし＝測定不能）は何もしない。非 None は
  `utt.meta["intensity"] = {"score": round(.,1), "status": "pass|under|over"}`。

### 3.7 config 検証（hersona 公開 API のみ）
- `actors[].id` は一意・snake_case。`participants ⊆ actors`。
- `hersona` 各属性は `available_attributes()` に存在（無ければ `difflib` で候補サジェスト）。
- `weight` は `coerce_level` で検証。エラーは `DuetConfigError(messages: list[str])` に集約。
- スタッフ prompt は project.yaml 相対で解決（`read_prompt`）。

### 3.8 CLI 終了コード
`0` 成功 / `1` 設定エラー(DuetConfigError) / `2` プロバイダ(DuetProviderError) /
`3` 予算超過(DuetBudgetError)。

## 4. 同梱データ（確定内容）

### prompts/（4 ファイル）
- `writer_ja.md` / `writer_en.md`: 「プロの脚本家。台詞は書かない。各ビートは目的/対立の種/
  出口条件のみ。phase 昇順。対立を必ず一つ。JSON のみ出力」。
- `narrator_ja.md` / `narrator_en.md`: 「台詞を書かない。心理を断定しない。ja 120字 / en 60語、
  五感の具体を一つ」。

### packs/examples/cafe/project.yaml
```yaml
title: 放課後カフェ物語
language: ja
world: |
  現代日本の小さな商店街。古い喫茶店と和菓子屋が並ぶ、夕暮れの似合う一角。
story: |
  幼なじみ二人の、すれ違いと和解の物語。素直になれない少女と、鈍感だが優しい少年。
defaults:
  llm: { provider: anthropic, model: claude-haiku-4-5-20251001, temperature: 0.8, max_tokens: 1024 }
staff:
  writer:
    prompt: ../../../prompts/writer_ja.md
    llm: { provider: anthropic, model: claude-opus-4-8 }
  narrator:
    prompt: ../../../prompts/narrator_ja.md
actors:
  - id: rinka
    name: 凛花
    role: 主人公の幼なじみ。商店街の和菓子屋の娘
    hersona: [tsundere, kyoto_ben]
    weight: moderate
    relationships: { kenta: 幼なじみ。素直になれない }
  - id: kenta
    name: 健太
    role: 主人公。鈍感だが面倒見が良い
    hersona: [optimist]
    weight: mild
    relationships: { rinka: 幼なじみ。気になっている }
```

### packs/examples/cafe/scenes/shopping.yaml
```yaml
id: shopping_01
title: 買い物のシーン
location: 商店街の雑貨屋
time: 放課後
goal: 凛花が素直になれないまま、健太への誕生日プレゼントを選ぶ
participants: [rinka, kenta]
notes: 凛花は照れると京言葉が強くなる
max_turns: 16
language: ja
```

## 5. テスト計画（FakeProvider で決定的に）

| ファイル | 内容 | 対応 |
|---|---|---|
| `tests/conftest.py` | cafe pack のパス fixture | — |
| `tests/test_config.py` | 正常系 / 未知属性+候補 / 重複id+不正weight集約 / participant不在 | T1 |
| `tests/test_providers.py` | FakeProvider FIFO / 未知 provider / fake 未注入 / from_dict | T2 |
| `tests/test_casting.py` | render_blend 連携(実hersona) / hersona無しで空 prompt | T3 |
| `tests/test_writer.py` | JSON 契約: 正常 / フェンス付き / 不正→リトライ→DuetWriterError / beats制約 | T4 |
| `tests/test_select_speaker.py` | 言及優先 / ラウンドロビン / 連続禁止 / 1人 / ナレーター間隔 | T5 |
| `tests/test_actor.py` | system 組み立て順 / 自己ラベル strip(「」と:両方) | T6 |
| `tests/test_orchestrator.py` | Fake 台本 E2E / ビート消化 / 二重予算で停止 / DuetBudgetError | T7 |
| `tests/test_script.py` | 3 形式出力スナップショット / save→load 往復 | T8 |
| `tests/test_quality.py` | speech あり(annotate付与) / なし(何もしない) | T9 |
| (live) `tests/test_live.py` | `@pytest.mark.live` 実 API 1 シーン（CI 除外） | T10 |

## 6. Definition of Done（受け入れ基準）

- [ ] `duet validate packs/examples/cafe/project.yaml` が exit 0
- [ ] `duet cast packs/examples/cafe/project.yaml` が配役 + conflict 警告を表示
- [ ] `duet scene run .../shopping.yaml --project .../project.yaml --measure --out out.md`
      が台本 Markdown を出力（live 環境で各アクター発話に intensity バッジ）
- [ ] FakeProvider のみで T1〜T9 が CI でパス
- [ ] 1 シーンの LLM 呼び出し回数が `max_turns*3` を超えない
- [ ] `ruff check duet/ tests/` クリーン / `pytest -q` 全パス（live 除く）

### 検証コマンド
```bash
uv venv && uv pip install -e ".[dev]" "git+https://github.com/shiro-0x/hersona"
ruff check duet/ tests/
pytest -q                      # live 除外（-m "not live"）
duet validate packs/examples/cafe/project.yaml
```

## 7. 別セッション用キックオフ・プロンプト

> 新セッションを **`shiro-0x/hersona-studio` をスコープに含めて**開始し、以下を貼る。
> （hersona の設計docを参照するため hersona も読めると望ましい。少なくとも
> `docs/duet/PHASE1_ORCHESTRATOR.md` と本書をクローン/参照できる状態にする。）

```text
あなたは hersona-studio (リポジトリ shiro-0x/hersona-studio) で Phase 1 を実装します。

コンテキスト:
- hersona-studio は「監督(ユーザー)/シナリオライター/ナレーター/アクター」が協働して
  シーン単位で物語を作るスタジオ。アクターの人格は hersona 属性ブレンドで注入する。
- hersona 側 Phase 0 は完了済み (v0.0.1)。公開 API は hersona.core.__all__ / docs/PUBLIC_API.md。

権威ある設計を必ず読むこと（hersona リポジトリ内）:
- docs/duet/PHASE1_ORCHESTRATOR.md  ← 実装仕様（モジュール/シグネチャ/テスト/受け入れ基準）
- docs/duet/PHASE1_HANDOFF.md        ← 実装中に確定した決定・命名・同梱データ・DoD（本書）
- docs/DUET_PLAN.md                  ← プロダクト定義
（hersona がスコープに無ければ git clone https://github.com/shiro-0x/hersona して参照）

やること:
1. PHASE1_HANDOFF.md「2. ディレクトリ構成」「3. 確定した決定」「4. 同梱データ」の通りに
   hersona-studio を実装する（パッケージ名 duet / CLI duet）。
2. hersona は公開 API (hersona.core の __all__) のみ import。_ 接頭辞の私的関数は使わない。
   依存は pyproject に hersona>=0.0.1,<1。未公開のうちは
   `uv pip install "git+https://github.com/shiro-0x/hersona"` で入れる。
3. LLM 呼び出しは必ず duet/providers.py 経由。テストは FakeProvider で決定的に。
   実 API テストは @pytest.mark.live でマークし CI から除外。
4. PHASE1_HANDOFF.md「5. テスト計画」の T1〜T9 を実装し、ruff/pytest を通す。
5. DoD（同 §6）を満たすことを確認:
   duet validate / cast / scene run (FakeProvider/実API) が仕様通り動く。

進め方:
- ブランチ claude/phase1-orchestrator を切って実装。
- 1 まとまりごとにコミット。完了したら PR を main に作成（テスト緑・ruff クリーンを本文に明記）。
- 不明点は PHASE1_ORCHESTRATOR.md を一次情報とし、それでも曖昧なら質問する。

完了基準: FakeProvider で T1〜T9 がCIパス、duet scene run が台本Markdownを出力、
LLM 呼び出しが max_turns*3 を超えない。
```

## 8. 補足（このハンドオフ作成時の状況）

- 本セッション（hersona スコープ）でローカルに Phase 1 の下書きコードを作成したが、
  hersona-studio へ push できないため未保存。**新セッションは本書 + PHASE1_ORCHESTRATOR.md
  から実装すれば等価なものを再現できる**ように決定を固定済み。
- hersona のモデル ID（プロンプト例で使用）: Opus `claude-opus-4-8` /
  Haiku `claude-haiku-4-5-20251001`。実在の最新 ID に合わせて適宜更新してよい。
