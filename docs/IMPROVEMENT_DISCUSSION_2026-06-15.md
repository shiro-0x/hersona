# hersona 改善議論ログ（2026-06-15）

> 形態: Claude Code + 外部AI（Grok）レビューの統合 / 対象: shiro-0x/hersona
> 目的: 既存 `ROADMAP.md`・`docs/IMPROVEMENT_PLAN.md`（成長・マーケ視点）と重複しない、
> **実装・運用基盤と製品の具体的な改善案**を優先度順に整理し、着手する。

## 0. 前提と現状認識

- 製品は個人OSSとして異例に成熟（64属性・相性マトリクス・診断クイズ・強度測定・i18n・テスト180件）。
- 既存ドキュメントの役割分担:
  - `ROADMAP.md` = 製品機能視点
  - `docs/IMPROVEMENT_PLAN.md` = 成長・マーケ視点（認知がボトルネックと診断）
  - 本ログ = 開発・品質基盤＋製品コアの具体改善

### 調査で判明した具体的な穴

1. **CIが存在しない** — `.github/workflows/` は `publish.yml`（PyPI公開）のみ。
   テスト180件・`ruff`・`scripts/validate.py` という揃った品質ゲートが PR で自動実行されていない。
   証拠: `hersona/core/recommend.py:343` に `ruff` エラー（B007 未使用ループ変数 `opt`）が残ったまま main にある。
2. **`site/` と `docs/app/` が完全重複** — `data.json` / `app.js` 等がバイト単位で同一。
   SSoT 違反で、片方だけ更新されて静かにズレる事故が起きる。
3. **バージョン番号の不整合** — `pyproject.toml` は `0.0.1`、ROADMAP は「初回 `v1.3.0` タグ」と矛盾。
   （→ 2026-06-15 に `0.0.1` へ統一して解消。§4 A3 参照）
4. **GitHub上の説明文が旧仕様**（旧25属性のまま。IMPROVEMENT_PLAN でも未対応）。

## 1. 統合改善提案（優先度順）

> 注: 検討初期に挙がった「agmsg 連携アダプター」案は誤りと判断し、完全に撤回した。

### 優先度 S（即日〜1週間）

| ID | 提案 | 根拠 / メモ |
|---|---|---|
| **S1** | **CIワークフロー追加** | `push`/`PR` で `ruff check` + `python scripts/validate.py` + `pytest` を Python 3.11/3.12/3.13 マトリクス実行。互換性マトリクス差分の PR コメント Action も将来同梱可 |
| **S2** | **`site/` と `docs/app/` の重複解消** | `docs/app/` を正に SSoT 化 |
| **S3** | **`ruff` エラー1件修正**（`recommend.py:343`） | `for opt` → `for _opt`。S1 を入れれば自動で弾ける |

### 優先度 A（1〜4週間）

| ID | 提案 | 根拠 / メモ |
|---|---|---|
| **A1** | **`hersona preview` コマンド** | core の `sample_dialogue.py` 既存・`recommend --generate-samples` 実装済み。ラップするだけで「人格がどう喋るか即確認」。LLM不要 |
| **A2** | **`rich` 導入（optional dep）** | `pip install hersona[tui]` で分離。`list` テーブル化、`blend` の conflict=赤/compatible=緑、`show` パネル |
| **A3** | **バージョニング整合・初回リリース** | `0.1.0` でリリースし Trusted Publishing 有効化（P0実装済み） |

### 優先度 B（1〜3ヶ月）

| ID | 提案 | 根拠 / メモ |
|---|---|---|
| **B1** | **`hersona diff` コマンド** | 2属性の core_traits 差分・共通フィールド・conflicts/compatible を並列表示。`load_attribute` 2回 + dict比較 |
| **B2** | **compatibility / blending エンジン強化** | 衝突時の代替案提案（例: `tsundere + playful` → `mischievous` 推奨）を `blend --strict` に展開。trait 重複排除・優先度解決・intensity 合成ルールの明文化 |
| **B3** | **visual 属性に画像生成プロンプト追加** | `image_prompt_tags`（英語タグ列、SD/Flux向け）をスキーマ追加。i18n 不要で軽量 |
| **B4** | **`first_person` フィールドをスキーマ追加** | `second_person` は既存だが `first_person` が欠落。`ore_boy`/`boku_girl`/`washi` の一人称軸が持つべきフィールドで、intensity「一人称は測れない」割り切りの根本原因。測定軸が3本目に |

### 優先度 C（3ヶ月〜、既存 ROADMAP と整合）

| 項目 | 根拠 |
|---|---|
| `hersona save <name>` でブレンドをローカル保存 | authoring.py 既存。薄い殻のみ |
| 方言追加（hiroshima_ben 等） | 1PR=1属性 規約に従い順次 |
| MCP サーバー化 | IMPROVEMENT_PLAN M3。core共有のため殻のみ |
| Shell補完（`argcomplete`） | entry_point にフック |
| 他エージェント対応（LangGraph 等エクスポート） | core を再利用 |

## 2. やらない（スコープ外）と判断したもの

- **`textual` 本格TUI化**: argparse + rich で十分。開発コスト大。
- **LLMアシストオーサリング（`--ai`）**: API費・依存増で「軽量」ポジションを毀損。静的 preview で代替。
- **Semantic Recommend（埋め込み）**: numpy/torch が入り軽量性が壊れる。クイズ推薦で十分。
- **agmsg 連携**: 誤った提案として撤回。

## 3. 着手順（合意）

```
即日:    S1(CI) + S3(lint fix)
今週:    S2(site重複) + A3(0.1.0 リリース)
今月:    A1(preview) + A2(rich optional)
来月:    B1(diff) + B2(blend強化) + B3,B4(schema拡張)
```

特に **S1（CI）・A1（preview）・B2（blend強化）** が揃うと、品質の自動担保・体験の wow・core 完成度が同時に上がる。

## 4. 進行ログ

- 2026-06-15: 本議事録を記録。S1 + S3 + S2 から着手開始。
- 2026-06-15: **S3 完了** — `recommend.py:343` の未使用ループ変数 `opt` → `_opt`。`ruff check` クリーン。
- 2026-06-15: **S1 完了** — `.github/workflows/ci.yml` を追加。`push(main)`/`pull_request` で
  Python 3.11/3.12/3.13 マトリクスにて `ruff check` + `scripts/validate.py` +
  `build_site.py --check` + `pytest` を自動実行。
- 2026-06-15: **S2 完了** — `site/` と `docs/app/` のバイト単位重複を解消。
  - GitHub Pages は `/docs` フォルダを配信（`docs/index.html` が `app/` をリンク、`pages.yml` は不在）と判明。
    `docs/app/` を正規・配信ディレクトリとし、旧ビルド先 `site/` を削除。
  - `scripts/build_site.py` の出力先を `site/data.json` → `docs/app/data.json` に変更。
  - 副次発見: 配信中の `data.json` は最近の属性更新（catchphrases 追加）後に再生成されておらず古かった。
    `build_site.py` で再生成し、`catchphrases` を含む最新状態にリフレッシュ。
  - `build_site.py --check` を CI に追加し、今後のデータドリフトを自動検出。
  - 検証: `ruff` クリーン / `validate.py` exit 0 / `build_site --check` OK / `pytest` 553 passed。

- 2026-06-15: **A3 完了（バージョンは `0.0.1` に統一）** — 初回リリース番号を `0.0.1` に確定。
  - `CHANGELOG.md`: `[Unreleased]` を `[0.0.1] - 2026-06-15` に統合（タグ未発行・PyPI未公開のため、
    現リポジトリ内容すべてが初回 v0.0.1 として公開される）。
  - `ROADMAP.md` / `.github/workflows/publish.yml` の `v1.3.0` 表記を `v0.0.1` に修正。
  - 検証: `uv build` で `hersona-0.0.1` の sdist/wheel 生成 → クリーン venv に install →
    publish.yml 相当のスモークテスト合格（64 属性 / `tsundere` ブレンド / `__version__ == 0.0.1`）。
  - 残り（オーナー手作業）: PyPI 側の Trusted Publisher 登録 → `git tag v0.0.1 && git push --tags` で公開。

- 2026-06-15: **A1 完了** — `hersona preview` コマンドを実装。
  - `hersona/core/sample_dialogue.py`（既存）の `generate_samples` をラップし、LLM不要で
    「注入ブロック + catchphrases ベースのサンプルフレーズ」を即表示。
  - フラグ: `--weight`（既定 moderate）/ `--count`（既定 3）/ `--lang` 全サブコマンド共通。
  - ロケール: `preview.*` キーを `en.yaml` / `ja.yaml` 両方に追加。
  - テスト: `test_cli.py` に 6 件追加（559 passed）。ruff クリーン。
  - 使用例: `hersona preview tsundere kyoto_ben --weight strong`

- 2026-06-15: **A2 完了** — `rich` を任意依存 (`hersona[tui]`) として導入し CLI を強化。
  - `hersona/cli/render.py` を新設。`rich` 未インストール / 非TTY / `--plain` / `NO_COLOR` の
    いずれかなら**必ずプレーン出力にフォールバック**（lazy import でベース install を汚さない）。
  - `list` → カテゴリ色分けテーブル、`show` → パネル（`conflicts_with`=赤 / `compatible_archetypes`=緑）。
  - `blend` / `preview` の conflict 警告を rich 有効時に赤表示。
  - グローバル `--plain` フラグ追加。`HERSONA_FORCE_RICH=1` でパイプ時も色維持（テスト用途も兼ねる）。
  - `pyproject`: `[tui]` extra (`rich>=13`) + dev に rich を追加（CI で rich パスを検証）。
  - 検証: クリーン wheel（rich 無し）で `list`/`show` がプレーン動作することを確認。ruff クリーン /
    pytest 564 passed（+5）。README / CHANGELOG 更新。

- 2026-06-15: **B1 完了** — `hersona diff <a> <b>` を実装。
  - core ロジックを `hersona/core/diff.py` に純粋関数 `diff_attributes()` として実装
    （「core=ロジック、殻=薄く」方針）。relation（conflict/compatible/neutral、
    言語跨ぎ speech の構造的 conflict 含む）+ scalar 並置 + list フィールドの
    共通/片側のみ分解を構造化して返す。
  - user 名前空間の属性はマトリクス未収録のため relation は None（"n/a"）にガード。
  - CLI: プレーン + rich テーブル（relation を conflict=赤/compatible=緑、共通項を緑）。
  - テスト: `test_diff.py` 7 件 + `test_cli.py` に 8 件（579 passed）。ruff クリーン。

- 2026-06-15: **B2 完了** — blend/compatibility 強化（衝突時の代替案提案）。
  - `CompatibilityMatrix.alternatives_for(name, keep)` — 同カテゴリ + keep と非衝突の
    代替候補を「compatible 数降順 → 名前昇順」で決定的に返す。
  - `CompatibilityMatrix.suggest_blend_fixes(names)` — conflict ペアごとに両側差し替え案を列挙。
  - CLI: `blend --suggest` / `preview --suggest`。助言は **stderr** に出し stdout の注入ブロックを汚さない。
  - 例: `airhead + intellectual`（衝突）→「airhead を外して chuunibyou/dandere/hot_blooded」。
    言語跨ぎ speech（`keigo + casual_en`）→ en speech 同士は相互衝突のため ja speech へ寄せる案。
  - テスト: `test_compatibility.py` +5 / `test_cli.py` +5（589 passed）。ruff クリーン。

- 2026-06-15: **B3 完了** — visual 属性に `image_prompt_tags` フィールドを追加。
  - `schema/attribute.schema.json` に任意フィールド `image_prompt_tags: string[]` を追加。
  - 全 5 visual 属性 (`animal_ears` / `glamorous` / `glasses` / `petite` / `silver_hair`) に
    SD/Flux 向け英語タグリストを設定。
  - テスト: `test_attributes.py` +6 件。validate.py / pytest クリーン。

- 2026-06-15: **B4 完了** — `first_person` スキーマ追加 + intensity 3 軸目実装。
  - `schema/attribute.schema.json` に任意フィールド `first_person: string` を追加
    (値例: `オレ / 俺`、`/` 区切りで複数記述可)。
  - 7 speech 属性に追加: `ore_boy` / `boku_girl` / `washi` / `gyaru` / `tomboy` /
    `princess_speech` / `archaic`。
  - `intensity.py` を 3 軸採点に拡張:
    - `sentence_endings` + `first_person` 両方あり: `0.45·endings + 0.30·catchphrase + 0.25·fp`
    - endings のみ: `0.60·endings + 0.40·catchphrase` (従来通り)
    - first_person のみ (ore_boy / boku_girl): `0.60·fp + 0.40·catchphrase` — **スキップ解消**。
  - `IntensityReport.first_person_hits` フィールド追加。`format_report` に一人称件数を表示。
  - テスト: +13 件 (608 passed)。ruff クリーン。

- 2026-06-15: **C (save) 完了** — ブレンドプリセットのローカル保存を実装。
  - ブレンドは「複数属性 + 強度」でありスキーマ (単一カテゴリ) に収まらないため、
    属性ではなく **プリセット (レシピ)** として保存する設計を採用。
  - `hersona/core/presets.py` を新設: `Preset` / `save_preset` / `load_preset` /
    `list_presets` / `delete_preset` / `presets_root` / `PresetError`。
    `hersona.core.__all__` に追加し `docs/PUBLIC_API.md` にも記載 (整合テスト維持)。
  - 保存先は `~/.hermes/presets/`（既定）。`HERSONA_PRESETS_DIR` で上書き可。未指定時は
    属性ルート (`HERSONA_USER_DIR`) の兄弟 `presets/` を使い、属性側の隔離設定を継承。
  - CLI 3 コマンド: `save <name> <attrs...> [--weight] [--note] [--overwrite]` /
    `presets`（一覧、rich テーブル対応）/ `load <name> [--weight]`（保存ブレンドを
    同じ blend エンジンで再生 → 常に最新属性を反映）。conflict は警告のみで保存は妨げない。
  - テスト: `test_presets.py` 15 件 + `test_cli.py` 12 件 (649 passed)。ruff クリーン。

- 2026-06-15: **C (Shell 補完) 完了** — `argcomplete` を任意依存として追加。
  - `main()` が `_try_argcomplete(parser)` 経由で補完フックを呼ぶ。未インストールは no-op。
  - 属性名 (`show`/`blend`/`diff`/`preview`/`measure`/`save`) とプリセット名 (`load`) を補完。
  - 任意 extra `[completion]` (`argcomplete>=3`)。`dev` にも入れ CI で経路検証。
  - テスト: `test_cli.py` +5 件 (654 passed)。ruff クリーン。

- 2026-06-15: **C (エクスポート) 完了** — 他フレームワーク向け `hersona export` を実装。
  - `hersona/core/export.py` に `export_blend(names, *, weight, fmt)` を新設 (`render_blend` 再利用)。
    `json` (メタ + system_prompt + 属性要約 + conflicts) / `messages` (`role=system` 列) /
    `markdown` (注入ブロック素文) の 3 形式。LangGraph / LangChain / OpenAI / Anthropic で利用可。
  - `hersona.core.__all__` に `export_blend` / `EXPORT_FORMATS` を追加、`PUBLIC_API.md` に記載。
  - テスト: `test_export.py` 8 件 + `test_cli.py` 4 件 (669 passed)。ruff クリーン。

- 2026-06-15: **C (MCP サーバー) 完了** — `hersona-mcp` を実装 (IMPROVEMENT_PLAN M3)。
  - `hersona/mcp/tools.py`: 純粋ロジック (mcp 非依存・全面テスト可)。`list_attributes` /
    `show_attribute` / `blend` / `export` / `recommend_blend` / `compatibility` を core 再利用で提供。
  - `hersona/mcp/server.py`: FastMCP への薄い配線。`mcp` を lazy import し、未インストール時は
    導入手順付き `RuntimeError`。`hersona-mcp` エントリ (`hersona.mcp.server:main`)。
  - 任意 extra `[mcp]` (`mcp>=1.0`)。CI には入れず、tools と「mcp 欠如パス」のみ検証。
  - テスト: `test_mcp.py` 12 件 (682 passed)。ruff クリーン。

- 2026-06-15: **C (方言追加) 完了** — `hiroshima_ben`（広島弁）を追加し計 65 属性に。
  - speech 26 種 = ja 21 + en 5。断定「〜じゃ/〜じゃけぇ/〜けぇ/〜とる」、強調「ぶち」、
    B4 で追加した `first_person`（わし/わしゃ/うち）を活用し intensity 3 軸採点が効く。
  - conflicts_with: keigo / onee_kotoba / archaic / princess_speech（丁寧・上品軸と衝突）。
  - 件数を全箇所で更新: tests（test_attach / test_compatibility / test_attributes /
    test_cli / test_mcp）、README / README.ja、`docs/app/data.json` 再生成。
  - テスト: 686 passed。ruff クリーン / validate 65ファイル / build_site --check OK。

- 2026-06-19: **Recent Context 強化（記事知見の反映）** — `## Recent Context` ブロックを改善。
  - 根拠: Qiita 記事（RAG実装ノウハウ）の「取り出した記憶を会話ターンと混同させない」「タイムスタンプで新旧区別」「否定・変化を消さず最新値を優先」という3原則に対応。
  - `## Recent Context (as of <timestamp>)` 形式に変更。SOUL.md 生成時刻をヘッダーで明示し、LLM が情報の新旧を判断できるようにした。
  - blockquote フレーミングディレクティブを追加: 「会話ターンではなく背景情報として参照」「最後に記録された値を現在の状態とする」。LLM が context を会話ターンとして誤解釈するリスクを軽減。
  - テスト: `test_soul.py` に 2 件追加（`test_render_soul_memory_header_includes_as_of_timestamp` / `test_render_soul_memory_has_framing_directive`）、決定性テストの `_strip_volatile` を `## Recent Context (as of` 行除外に更新。
  - SKILL.md: `--memory` 説明・Verification Checklist を新形式に同期。
  - 非採用: 埋め込み類似度検索・意味的dedup・RELEVANCE_THRESHOLD（numpy/torch を呼び込み「軽量・決定的」ポジションに反する。既に ROADMAP で却下済み）。

### まとめ

- ロードマップ B / C タスク（save / 補完 / export / MCP / 方言）をすべて完了。
  残るは ROADMAP の長期項目（さらなる方言・語尾の順次追加、Web 殻等）。
