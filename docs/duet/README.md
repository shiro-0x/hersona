# hersona-duet 詳細設計書 (実装エージェント向け)

> 親文書: [`docs/DUET_PLAN.md`](../DUET_PLAN.md) (プロダクト定義・競合調査・フェーズ概要)
> 本ディレクトリは各フェーズを**他の開発エージェント / 開発者が単独で実装に着手できる粒度**
> に落とした詳細設計。実装前に親文書 → 該当フェーズの順で読むこと。

## フェーズ一覧と依存関係

| 文書 | 実装先リポジトリ | 依存 |
|---|---|---|
| [PHASE0_HERSONA_PREP.md](./PHASE0_HERSONA_PREP.md) | **hersona (本リポジトリ)** | なし。最初に着手 |
| [PHASE1_ORCHESTRATOR.md](./PHASE1_ORCHESTRATOR.md) | hersona-studio (新規) | Phase 0 |
| [PHASE1_HANDOFF.md](./PHASE1_HANDOFF.md) | hersona-studio (新規) | 別セッション実行用の引き継ぎ + キックオフ・プロンプト (実装着手はここから) |
| [PHASE2_DIRECTOR_AND_PARTICIPATION.md](./PHASE2_DIRECTOR_AND_PARTICIPATION.md) | hersona-studio | Phase 1 |
| [PHASE3_WEB_UI.md](./PHASE3_WEB_UI.md) | hersona-duet | Phase 2 |
| [PHASE4_ECOSYSTEM.md](./PHASE4_ECOSYSTEM.md) | hersona-duet (+hersona) | Phase 2 (UI 不要のものあり) |

## 共通規約 (全フェーズ)

- **言語/ツール**: Python 3.11+ / uv / ruff / pytest。hersona 本体と同一スタイル
- **hersona への依存**: `hersona.core` の公開エクスポート (`hersona/core/__init__.py` の
  `__all__`) のみ import 可。私的関数 (`_` 接頭辞) の利用禁止
- **LLM 呼び出し**: 必ず `duet/providers.py` の抽象を経由。エージェント実装内で
  SDK を直接 import しない (テスト容易性・エージェント別 LLM 設定のため)
- **テスト**: LLM 依存箇所は `FakeProvider` (PHASE1 §7) で決定的にテストする。
  実 API を叩くテストは `@pytest.mark.live` でマークし CI から除外
- **i18n**: ユーザー向け文字列は ja/en 両対応を前提にキーで管理 (hersona の
  `locales/*.yaml` 方式を踏襲)。コンテンツ言語はシーン設定の `language` に従う
- **コンテンツ方針**: 全年齢。固有名詞 (実在作品・キャラ名) をパックに含めない。
  共有機能では hersona の `assert_shareable` / `find_proper_noun_risks` を再利用

## 各フェーズ共通の Definition of Done

1. 該当文書の「受け入れ基準」を全て満たす
2. `ruff check` クリーン / `pytest -q` 全パス (live マーク除く)
3. 文書に列挙されたテストケースが実装されている
4. README / CHANGELOG 更新 (ユーザー可視の変更がある場合)
