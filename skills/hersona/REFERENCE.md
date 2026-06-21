# hersona SKILL リファレンス (詳細)

> このファイルは `SKILL.md` 本体から分離した詳細リファレンス。会話 (ペルソナ適用) には
> 不要な、CLI フラグ詳細 / レシピ集 / 検証チェックリスト / バージョン履歴をまとめている。
> 必要になったときだけ参照する (本体を毎ターン軽量に保つための分割)。

## v1.4.0 追加フラグ詳細

```bash
# measure: 期待バンド外で自己チェックプロンプトを生成
hersona measure personality/tsundere speech/keigo --weight strong --text "..." --strict
# → score 76/100, status=pass ✓
# → もし under/over なら pasteable な self-audit prompt を stderr に出力

# measure: プロンプトのみ表示 (LLM に貼り付けて再採点する用)
hersona measure personality/tsundere speech/keigo --weight strong --text "..." --check-prompt
# → レポート抑制、生成プロンプトのみ表示

# soul / persistent: ## Recent Context を SOUL.md 末尾に追加
hersona soul personality/tsundere --memory '{"recent_topic":"ReAct パターンの話","mood":"やや真剣"}'
hersona soul personality/tsundere --memory-file /tmp/memory.json
# → dict[str, str] 形式、max 16 keys, 各 value max 512 chars
# → markdown 特殊文字 (## [, ], *, _, `) は safelist エスケープ

# export: 5 形式
hersona export personality/tsundere speech/keigo --format openai_assistants
# → OpenAI Assistants API instructions 用 markdown、metadata あり
hersona export personality/tsundere speech/keigo --format langchain_system_message
# → langchain.schema.SystemMessage 互換 JSON
```

`--lang {en,ja}` で出力言語を切替。`HERSONA_LANG` 環境変数でも可。

`--plain` で rich テーブルを無効化（TTY がない cron / テスト経路で使う）。

## Verification Checklist

### single / multi モード

- [ ] システムプロンプトの先頭に `core_traits` / `catchphrases` / `tone` が注入されている
- [ ] セッション状態が指定属性 (複数属性の場合は組合せ) に切り替わっている
- [ ] multi モード時、`conflicts_with` 警告が適切に表示される
- [ ] `/hersona default` でリブラ人格に復帰できる

### persistent モード

- [ ] `~/.hermes/config_backups/` に実行前バックアップが作成されている
- [ ] `~/.hermes/config.yaml` の `agent.personalities` に `<name>: |` エントリが追加されている
- [ ] 新規セッション (`/new`) で自動的に属性が適用される
- [ ] `hersona check` で `core_traits` / `catchphrases` / `tone` が反映されている
- [ ] **(v1.4.0)** `--memory` フラグ使用時、SOUL.md 末尾に `## Recent Context (as of <timestamp>)` セクションが verbatim に round-trip する
- [ ] **(v1.4.0)** `## Recent Context` ブロックに framing directive（背景情報・会話ターンではない旨）が blockquote で付与される
- [ ] **(v1.4.0)** markdown injection (`## evil` 等) が safelist エスケープされる

### reset モード

- [ ] `~/.hermes/config_backups/` に reset 前バックアップが作成されている
- [ ] config.yaml から persistent 登録が全削除されている
- [ ] 新セッションでリブラ人格 (デフォルト) に戻る

### v1.4.0 追加ゲート (measure / memory / formats)

- [ ] `hersona measure --strict` が同じ入力で同じ出力を返す (決定性)
- [ ] `hersona measure --check-prompt` がレポートを抑制しプロンプトのみ表示
- [ ] `hersona soul --memory '<json>'` で 16 keys / 512 chars を超えると `ValueError`
- [ ] `hersona export --format <5 形式>` がすべて valid parseable output を返す

### validate.py による静的検証

- [ ] `python scripts/validate.py` が 84 属性 / 0 エラーで exit 0
- [ ] `pytest` が全件パス (880+ tests)
- [ ] `hersona list` の出力件数 = `find attributes -name "*.yaml" | wc -l`

## One-Shot Recipes

### 4 つのモードを順番に試す

```bash
# 1. single モードで感触を見る
/hersona personality/tsundere
# → 数ターン会話
/hersona default

# 2. multi モードで複合属性を試す
/hersona personality/tsundere speech/keigo multi
# → ツンデレ + 敬語のハイブリッド
/hersona default

# 3. persistent モードで永続化
/hersona personality/tsundere persistent
# → 表示された YAML 抜粋を ~/.hermes/config.yaml に貼り付け
# → セッション再起動

# 4. reset モードで撤収
/hersona reset
# → 新セッションでリブラ人格 (デフォルト) に戻る
```

### 既存 config.yaml との衝突を確認

```bash
# 既存 personalities を確認
python3 -c "import yaml; d=yaml.safe_load(open('$HOME/.hermes/config.yaml')); print(list(d.get('agent',{}).get('personalities',{}).keys()))"

# 永続化前に手動でバックアップ
cp ~/.hermes/config.yaml ~/.hermes/config.yaml.bak.$(date +%Y%m%d_%H%M%S)
```

### 診断クイズでおすすめのブレンドを得る

```bash
# CLI 1 行で全自動 (TTY 不要)
hersona recommend --answers distance=1,speech=0,role=1 --apply --explain --json
# --apply で注入ブロックも表示 / --json で機械可読出力
# --explain で各採用属性の根拠 (rationale) + 落選の代替案 + サマリを表示
# v1.4.0 から --apply 時に intensity_baseline が記録される
```

### 人格を他フレームワークへエクスポート (v1.4.0 で 5 形式)

```bash
# LangGraph / LangChain / OpenAI / Anthropic 向け
hersona export personality/tsundere speech/keigo --format messages > tsundere_keigo.json
# → [{"role": "system", "content": "..."}] 形式

# Markdown (注入ブロックの素文)
hersona export personality/tsundere --format markdown

# 構造化 (メタデータ + システムプロンプト + 競合情報)
hersona export personality/tsundere --format json

# OpenAI Assistants API (v1.4.0)
hersona export personality/tsundere speech/keigo --format openai_assistants
# → Assistants instructions 用 markdown、metadata あり

# LangChain SystemMessage (v1.4.0)
hersona export personality/tsundere speech/keigo --format langchain_system_message
# → langchain.schema.SystemMessage 互換 JSON
```

### 強度指標を採点 + 期待バンド外なら自己チェックプロンプト (v1.4.0)

```bash
# 通常の採点
hersona measure personality/tsundere speech/keigo --weight strong --text "べ、別に...あんたのためじゃないんだからね！"
# → score 76/100, status=pass ✓

# 期待バンド外を警告 + 自己チェックプロンプト
hersona measure personality/tsundere speech/keigo --weight strong --text "了解しました。" --strict
# → score 12/100, status=under ⚠ + self-audit prompt を stderr

# プロンプトのみ表示 (LLM に貼り付けて再採点)
hersona measure personality/tsundere speech/keigo --weight strong --check-prompt
# → レポート抑制、生成プロンプトのみ
```

### SOUL.md に ## Recent Context を注入 (v1.4.0)

```bash
# インライン JSON
hersona soul personality/tsundere --memory '{"recent_topic":"ReAct パターンの話","mood":"やや真剣"}'
# → SOUL.md 末尾に `## Recent Context` セクション追加

# ファイルから読み込み
cat > /tmp/memory.json <<EOF
{
  "recent_topic": "openai_assistants format の export 議論",
  "mood": "やや真剣",
  "last_event": "v1.4.0 リリース"
}
EOF
hersona soul personality/tsundere --memory-file /tmp/memory.json

# persistent モードでも使える
hersona personality/tsundere speech/keigo persistent --memory "$(cat /tmp/memory.json)"
```

### ブレンドをプリセット保存して再利用する

```bash
# 保存
hersona save my_tsundere personality/tsundere speech/keigo --weight moderate --note "硬めツンデレ"
# 一覧
hersona presets
# 呼び出し
hersona load my_tsundere
# 強度上書き
hersona load my_tsundere --weight strong
```

### 新しい属性テンプレートを追加する

```bash
# 1. attributes/<category>/<name>.yaml を schema/attribute.schema.json に準拠して作成
# 2. scripts/_oneoff/gen_v1_attributes.py を使うか、手書きで配置
# 3. 検証
cd ~/projects/hersona
python scripts/validate.py
pytest

# 4. コミット + push (wt/<branch> 上で)
git add attributes/<category>/<name>.yaml
git commit -m "feat(attributes): add <category>/<name>"
git push origin wt/<branch>
```

### シェル補完を有効にする

```bash
pip install "hersona[completion]"
# bash
eval "$(register-python-argcomplete hersona)"
# zsh
eval "$(register-python-argcomplete hersona)"
# fish
register-python-argcomplete --shell fish hersona | source

# 補完される対象: サブコマンド / 属性名 (show/blend/diff/preview/measure/save) / プリセット名 (load)
```

## Versioning

### hersona バージョン履歴

- **v0.0.1** (2026-06-13): 64 属性初版リリース（広島弁追加前）。PyPI Trusted Publishing 経路確立。
- **v1.0.0** (2026-06-15): v1.0 pivot — `data/<キャラ>` 廃止、属性テンプレート単体フロー化。
- **v1.1.0** (2026-06-??): 8 PR 累計 / 52 属性 / intensity metric 追加。
- **v1.2.0** (2026-06-??): 65 属性化、SOUL.md 永続化、multi-tool ターゲット対応。
- **v1.3.0** (2026-06-17): measure --strict + intensity baseline + SOUL.md memory + export 拡張。PR-1/2/3 マージ。
- **v0.2.0** (2026-06-17): ユーザー指示で v1.3.0 をリネーム (= ロールバック)。**PyPI に残存**。
- **v1.4.0** (2026-06-17): ロールバック撤回、v1.3.0 の機能セットを v1.4.0 として再 publish。
  PyPI 履歴は `0.0.1 → 1.0.0 → 1.1.0 → 1.2.0 → 1.3.0 → 0.2.0 → 1.4.0` という
  ロールバック履歴を含む。**機能的には v1.3.0 と同じ** (version bump + tag 置換のみ)。

### 廃止済みデータ形式

- `data/<title>/<character>.yaml` 形式の個別キャラ依存 YAML は v1.0 で完全廃止。
  キャラに依存しない **属性の組合せ** で任意の人格を構築する設計に移行。

### 破壊的変更

- v0.0.1 → v0.0.2: コマンド引数 `<title> <character>` → `<category>/<name>` (v3.0.0 で完了)
- v0.0.2 → v0.1.0: 広島弁追加 (PR #77)。`speech` カテゴリが 25 → 26 件。
- v0.0.x → v0.1.0: `hersona` CLI に `preview` / `diff` / `save` / `presets` / `load` / `export` サブコマンド追加 (PR #67-#75)。
- v1.2.0 → v1.3.0 / v1.4.0: `measure --strict` / `soul --memory` / `export` 5 形式追加。
  `Recommendation.intensity_baseline` / `Preset.intensity_baseline` フィールド追加。
  公開 API への追加のみ（semver additive）。

### SKILL.md バージョン履歴

- **v0.0.1** (2026-06-13): 64 属性初版。PyPI Trusted Publishing 経路確立。
- **v0.0.2** (SKILL.md): 旧バージョン。1,382 バイトの stub で Overview/When to Use/Common Pitfalls/Verification Checklist が欠落しており peer 品質未満。
- **v0.1.0** (2026-06-15): 65 属性に拡張 (PR #77 広島弁追加)。CLI サブコマンド `preview` / `diff` / `save` / `presets` / `load` / `export` を反映。PR #74-#77 (argcomplete / export / MCP / hiroshima_ben) を全て反映。peer 構造 (Overview / When to Use / Common Pitfalls / Verification Checklist / One-Shot Recipes) に準拠。元ファイルの誤字 (「砮」を「砕」、「続続」を「継続」) を修正。
- **v0.2.0** (2026-06-17): v1.4.0 リリースに合わせて SKILL.md を v0.2.0 へ bump。v1.4.0 の新機能 (measure --strict / --check-prompt / intensity_baseline / soul --memory / export 5 形式) を Command Syntax / Common Pitfalls / Verification Checklist / One-Shot Recipes に反映。Pitfall 10-12 (memory injection / strict プロンプトの誤用 / export 5 形式の注意) 追加。
- **v0.3.0** (2026-06-20): 詳細リファレンス (フラグ詳細 / Verification Checklist / One-Shot Recipes / Versioning) を本ファイル (REFERENCE.md) に分離し、SKILL.md 本体を会話に必要な分へスリム化 (毎ターンのコンテキスト軽量化)。注入ブロックの反復防止ディレクティブ 3 種を 1 つ (`response_style_directive`) に統合。
