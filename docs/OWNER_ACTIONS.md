# オーナー手作業チェックリスト（B-1 店構え / B-2 レジストリ登録）

> コード変更ゼロ・リポジトリオーナーの手作業だけで完了する項目の実行手順。
> 出典: [`IMPROVEMENT_PLAN_2026-07-10_sharpen-and-grow.md`](./IMPROVEMENT_PLAN_2026-07-10_sharpen-and-grow.md)
> B-1 / B-2 / B-5、および [`ROADMAP_V2.md`](./ROADMAP_V2.md) §7。
> 完了したらチェックを入れてコミットする（実施状況もこのファイルで追跡する）。

## B-1: GitHub 店構え（完了 — 2026-07-11）

Settings → General / 右上の ⚙（About 欄）から:

- [x] **About 欄の更新** — 「346 reusable character attributes... Build once.
  Keep personality everywhere.」へ差し替え済み（GitHub API で確認済み）
- [x] **topics の追加** — `mcp` `mcp-server` `ai-agent` `persona` `character-ai`
  `aituber` `character` `claude` `cursor` `llm` `system-prompt` 等、17個に拡充済み
- [x] **Discussions を有効化** — `has_discussions: true` 確認済み。
  最初の Show and tell 投稿も完了
- [ ] **Social Preview 画像** — Settings → General → Social preview に
  `docs/hersona-logo.png` をアップロード（API からは状態確認不可。未対応なら実施）
- [ ] リリースごとの About 同期は `docs/RELEASE_CHECKLIST.md` §4 の手動項目として確認
  （次回リリース時に再確認）

## B-2 前半: MCP レジストリ登録（メタデータは使い回し）

共通メタデータ（コピペ用）:

| 項目 | 値 |
|---|---|
| 名前 | `hersona-mcp` |
| 一行説明 (EN) | Composable personality layer for AI agents — 346 CC0 character attributes to blend, measure, and export personas (MCP server included) |
| インストール | `pip install "hersona[mcp]"` → コマンド `hersona-mcp` |
| リポジトリ | `https://github.com/shiro-0x/hersona` |
| カテゴリ | AI / Agents / Prompts / Roleplay |
| ツール一覧 | list_attributes / show_attribute / blend / export / recommend_blend / compatibility / **measure_intensity** / **bench_transcript** / **list_personas** / **install_persona** (2026-07-11 実装完了、計 10 種) |

登録先（2026 年時点の主要 4 箇所）:

- [ ] **mcp.so** — サイトの Submit フォームから登録
- [ ] **Smithery** (smithery.ai) — GitHub 連携で登録（ページビュー計測が可能）
- [ ] **Glama** (glama.ai/mcp/servers) — Submit から登録
- [ ] **awesome-mcp-servers** (`punkpeye/awesome-mcp-servers`) — カテゴリ節に 1 行追加の PR

> B-2 後半（MCP ツール拡張: measure / bench / personas）は **完了**
> （`hersona/mcp/tools.py` / `server.py`、2026-07-11）。「自分の人格維持率を
> 自己採点できる MCP サーバー」がレジストリ掲載文の売り文句として使える状態。
> 登録時の説明文にこの 4 ツールも触れると良い。

## B-5 残: awesome リスト PR / USED_BY

- [ ] awesome-ai-agents 系リストへ PR（1 行 + 一行説明）
- [x] `USED_BY.md` の器を用意（2026-07-10 実施。`reviews/2026-07-04` P3-2）
  — 利用例が来たら随時追記
- [x] `pyproject.toml` keywords 拡充（2026-07-10 実施: mcp / character-card /
  chatbot / aituber / langchain / character / roleplay 系を追加）

## 計測の開始（North Star 代理指標）

- [ ] **GitHub Traffic の週次記録を開始**（Insights → Traffic。14 日で消えるため
  週 1 回スプレッドシート等へ転記。`IMPROVEMENT_PLAN.md` S1 と同枠）
- [ ] pypistats.org で `hersona` の月次 DL を同じシートに記録
- [ ] Smithery 登録後はページビューも同枠で記録

> WPE（週次 Export 実行数）はテレメトリを入れず、上記の代理指標で観測する
> （2026-07-10 決定、`ROADMAP_V2.md` §1）。
