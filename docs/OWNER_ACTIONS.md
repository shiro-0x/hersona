# オーナー手作業チェックリスト（B-1 店構え / B-2 レジストリ登録）

> コード変更ゼロ・リポジトリオーナーの手作業だけで完了する項目の実行手順。
> 出典: [`IMPROVEMENT_PLAN_2026-07-10_sharpen-and-grow.md`](./IMPROVEMENT_PLAN_2026-07-10_sharpen-and-grow.md)
> B-1 / B-2 / B-5、および [`ROADMAP_V2.md`](./ROADMAP_V2.md) §7。
> 完了したらチェックを入れてコミットする（実施状況もこのファイルで追跡する）。

## B-1: GitHub 店構え（最優先・約1時間）

Settings → General / 右上の ⚙（About 欄）から:

- [ ] **About 欄の更新** — 現在「89 reusable character attributes」のまま。以下に差し替え:
  ```
  Build once. Keep personality everywhere. 346 composable character
  attributes for AI agent personas — blend, measure, and export to
  CLAUDE.md / AGENTS.md / Cursor / any LLM. MIT + CC0.
  ```
  Website 欄: `https://shiro-0x.github.io/hersona/`
- [ ] **topics の追加** — 現状に加えて:
  `mcp` `mcp-server` `ai-agent` `persona` `character-ai` `aituber`
  `system-prompt` `prompt-engineering`
- [ ] **Discussions を有効化** — Settings → General → Features → Discussions
- [ ] **Social Preview 画像** — Settings → General → Social preview に
  `docs/hersona-logo.png` をアップロード
- [ ] リリースごとの About 同期は `docs/RELEASE_CHECKLIST.md` §4 の手動項目として確認

## B-2 前半: MCP レジストリ登録（メタデータは使い回し）

共通メタデータ（コピペ用）:

| 項目 | 値 |
|---|---|
| 名前 | `hersona-mcp` |
| 一行説明 (EN) | Composable personality layer for AI agents — 346 CC0 character attributes to blend, measure, and export personas (MCP server included) |
| インストール | `pip install "hersona[mcp]"` → コマンド `hersona-mcp` |
| リポジトリ | `https://github.com/shiro-0x/hersona` |
| カテゴリ | AI / Agents / Prompts / Roleplay |
| ツール一覧 | list_attributes / show_attribute / blend / export / recommend_blend / compatibility |

登録先（2026 年時点の主要 4 箇所）:

- [ ] **mcp.so** — サイトの Submit フォームから登録
- [ ] **Smithery** (smithery.ai) — GitHub 連携で登録（ページビュー計測が可能）
- [ ] **Glama** (glama.ai/mcp/servers) — Submit から登録
- [ ] **awesome-mcp-servers** (`punkpeye/awesome-mcp-servers`) — カテゴリ節に 1 行追加の PR

> B-2 後半（MCP ツール拡張: measure / bench / personas）はコード作業。
> sharpen-and-grow の 60 日枠で実施する。

## B-5 残: awesome リスト PR / USED_BY

- [ ] awesome-ai-agents 系リストへ PR（1 行 + 一行説明）
- [ ] `USED_BY.md` の器はリポジトリに用意済みになったら利用例を随時追記
  （`reviews/2026-07-04` P3-2）
- [x] `pyproject.toml` keywords 拡充（2026-07-10 実施: mcp / character-card /
  chatbot / aituber / langchain / character / roleplay 系を追加）

## 計測の開始（North Star 代理指標）

- [ ] **GitHub Traffic の週次記録を開始**（Insights → Traffic。14 日で消えるため
  週 1 回スプレッドシート等へ転記。`IMPROVEMENT_PLAN.md` S1 と同枠）
- [ ] pypistats.org で `hersona` の月次 DL を同じシートに記録
- [ ] Smithery 登録後はページビューも同枠で記録

> WPE（週次 Export 実行数）はテレメトリを入れず、上記の代理指標で観測する
> （2026-07-10 決定、`ROADMAP_V2.md` §1）。
