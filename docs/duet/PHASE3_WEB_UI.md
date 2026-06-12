# Phase 3 詳細設計: Web UI (4 画面)

> 実装先: hersona-duet。依存: Phase 2。
> ゴール: `duet ui` でローカル Web アプリが立ち上がり、設定〜シーン実行〜
> レビュー〜出力までを人間が GUI で完結できる。

## 0. 方針の確定 (v2 計画からの精緻化)

- **ローカルファースト**: `duet ui` が FastAPI サーバ (localhost) + 静的フロントを起動。
  API キーはローカルの設定ファイルに保存され、外部送信されない。
  ※「GitHub Pages 配信」は orchestrator が Python である以上ブラウザ単体では動かないため、
  **Pages は読み取り専用ギャラリー (完成台本の公開) に限定** (Phase 4)。ここを混同しない
- フロントは Vite + React + TypeScript (実装エージェントの裁量で Svelte 等に変更可。
  ただし「ビルド成果物を `duet/ui/dist` に同梱し、Python サーバが配信する」契約は固定)

## 1. 構成

```
duet/
├── server/
│   ├── app.py            # FastAPI: REST + WebSocket + 静的配信
│   ├── runs.py           # 実行ジョブ管理 (1 プロセス内・同時 1 シーン)
│   └── settings.py       # ~/.duet/config.toml (APIキー等) の読み書き
└── ui/                   # フロント (ソース) → dist を同梱
    └── src/
        ├── pages/Basic.tsx Agents.tsx Scenes.tsx Output.tsx
        ├── components/ChatView.tsx BeatTimeline.tsx IntensityBadge.tsx CastEditor.tsx
        └── lib/api.ts ws.ts
```

## 2. REST / WebSocket API 契約

ベース: `http://127.0.0.1:7860` (ポートは `--port`)。全て JSON。

| メソッド | パス | 内容 |
|---|---|---|
| GET/PUT | `/api/project` | project.yaml の読み書き (PUT は §2.3 検証を通す) |
| GET | `/api/hersona/attributes` | 属性一覧 (`available_attributes` + 表示名/カテゴリ) — 配役ピッカー用 |
| POST | `/api/hersona/blend/preview` | `{names, weight}` → 注入ブロック + conflicts (配役プレビュー) |
| GET/POST/PUT/DELETE | `/api/scenes`, `/api/scenes/{id}` | シーン CRUD |
| POST | `/api/scenes/{id}/run` | 実行開始 `{mode: "auto"|"join", measure: bool}` → `{run_id}` |
| WS | `/ws/runs/{run_id}` | 進行イベントの購読 + 参加モードの発話送信 (§2.2) |
| POST | `/api/runs/{run_id}/review` | `{action: "approve"} \| {action: "retake", scope, beat_index, note}` |
| GET | `/api/runs/{run_id}/export?format=screenplay\|novel\|json` | 出力取得 |
| GET/PUT | `/api/settings` | プロバイダ別 API キー (マスク表示)・既定 LLM |

### 2.2 WebSocket イベント (server→client / client→server)

```jsonc
// server → client
{"type": "beat_sheet", "beats": [...]}
{"type": "beat_start", "index": 1, "phase": "sho", "goal": "..."}
{"type": "utterance", "kind": "line", "speaker": "rinka", "text": "...",
 "beat_index": 1, "intensity": {"score": 76, "status": "pass"} }
{"type": "awaiting_human", "actor_id": "player", "timeout_sec": null}
{"type": "scene_done", "run_id": "...", "status": "draft"}
{"type": "error", "code": "provider", "message": "..."}

// client → server (参加モードのみ)
{"type": "human_utterance", "text": "..."}   // 空文字 = パス
{"type": "command", "value": "skip" | "quit"}
```

実装: `QueueInputSource` (Phase 2) を WebSocket 受信で埋める。サーバ側は
シーン実行を `asyncio.to_thread` で回し、`on_event` コールバックを WS に中継する。

### 2.3 設定の検証

PUT `/api/project` は `config.load_project` と同じ検証を通し、エラーは
`{errors: [{path: "actors[0].role", message: "..."}]}` 形式で返す (フォームに紐付け可能に)。

## 3. 画面仕様 (4 画面 — オーナー要件)

### 3.1 基本設定 (Basic)

- 作品タイトル / 言語 (ja/en) / 世界観 (textarea) / 物語 (textarea)
- 既定 LLM (プロバイダ・モデルのセレクト) — `/api/settings` のキー登録状況を表示

### 3.2 エージェント設定 (Agents)

- **スタッフ**: writer / narrator のプロンプト編集 (同梱テンプレを初期値に) + LLM 個別指定
- **アクター (配役)**: CastEditor
  - hersona 属性ピッカー: カテゴリ別一覧 (`/api/hersona/attributes`)、
    選択のたびに `/blend/preview` で注入ブロックと **conflict 警告**を即時表示
  - weight セレクト / name / role / relationships / LLM 個別指定
  - `human: true` 切替 — ON のとき name/role 必須のフォームバリデーション (登場設定)
- 監督席の説明文を常設表示: 「監督はあなたです。シーン完了後にレビューします」

### 3.3 シーン設定 (Scenes)

- シーン一覧 (作品 = シーンの束) + 追加/複製/削除
- シーン編集: title / location / time / goal / notes / participants (актер選択) / max_turns
- 実行ボタン: 「完全自動で実行」/「参加して実行」(human アクターがいる場合のみ活性)
- 実行ビュー: ChatView (発話ストリーム + IntensityBadge) + BeatTimeline (現在ビート強調)
  - 参加モード: `awaiting_human` で入力欄が活性化。パス / skip / quit ボタン
  - 完了時: レビューパネル (採用 / ビートを選んでリテイク + ノート入力)

### 3.4 テキスト出力 (Output)

- run 一覧 (シーン別・状態 draft/approved)
- プレビュー: 台本体 / 小説体 切替。Markdown / JSON ダウンロード
- 「承認済みのみ表示」フィルタ

## 4. settings.py — API キー管理

- 保存先: `~/.duet/config.toml`。`chmod 600`。リポジトリ/パックには絶対に書かない
- 形式: `[providers.anthropic] api_key = "..."` / 環境変数があれば env 優先
- GET `/api/settings` はキーを `sk-***abc` 形式にマスクして返す

## 5. 非機能

- 同時実行は 1 シーンのみ (runs.py がロック)。2 件目の run 要求は 409
- サーバは 127.0.0.1 バインド固定。`--host` での外部公開はドキュメントで非推奨明記
  (BYO キーが他者に使われるため)
- フロントのビルド成果物は wheel に同梱し、`duet ui` だけで動く (Node 不要)

## 6. テスト計画

| # | テスト | 種別 |
|---|---|---|
| T1 | REST: project の GET/PUT 検証エラー形式 / scenes CRUD | unit (TestClient) |
| T2 | blend/preview: conflicts が返る (hersona 実データ) | unit |
| T3 | WS: Fake provider で run → イベント列の順序 (beat_sheet→beat_start→utterance→scene_done) | integration |
| T4 | WS 参加モード: awaiting_human → human_utterance → 続行 / quit → セッション保存 | integration |
| T5 | review API: approve / retake が Phase 2 retake を呼ぶ | integration (Fake) |
| T6 | settings: マスク表示 / env 優先 / 600 パーミッション | unit |
| T7 | 同時実行ロック: 2 件目が 409 | unit |

## 7. 受け入れ基準

- [ ] `duet ui` → ブラウザで 4 画面を遷移し、設定〜自動実行〜レビュー〜エクスポートが
      GUI のみで完結する (live 手動確認)
- [ ] 参加モードで入力欄から発話してシーンを完走できる
- [ ] API キーが localhost の外に出ない (コード検査 + 設定ファイルのみ)
- [ ] T1〜T7 が CI でパス
