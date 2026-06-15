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

### 次の着手予定

- A3（バージョニング整合・`0.1.0` 初回リリース）→ A1（`hersona preview`）→ A2（`rich` optional）。
</content>
</invoke>
