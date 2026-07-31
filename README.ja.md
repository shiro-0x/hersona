# hersona

**日本語** · [English](./README.md)

> **Build once. Keep personality everywhere.**
> *Composable personalities for every LLM.*

AIエージェント向けペルソナの **346 の再利用可能キャラ属性** —
personality / speech / archetype / visual / hobby のテンプレートからペルソナを合成し、
会話で実際に維持できているかを**計測**し、あらゆる LLM・エージェント基盤へ移植する。
**MIT** (コード) + **CC0** (テンプレート)。CLI / MCP server / Hermes Agent skill 同梱。

[![PyPI](https://img.shields.io/pypi/v/hersona.svg)](https://pypi.org/project/hersona/)
[![Downloads](https://pepy.tech/badge/hersona)](https://pepy.tech/project/hersona)
[![License: MIT (code)](https://img.shields.io/badge/License-MIT-lightgrey.svg)](./LICENSE)
[![Templates: CC0 1.0](https://img.shields.io/badge/Templates-CC0_1.0-lightgrey.svg)](./LICENSE-CC0.txt)
[![MCP Server](https://img.shields.io/badge/MCP-Server-blue.svg)](#mcp-サーバーとして使う任意)
[![Docs](https://img.shields.io/badge/Docs-shiro--0x.github.io-9cf)](https://shiro-0x.github.io/hersona/)

[Docs](https://shiro-0x.github.io/hersona/) · [PyPI](https://pypi.org/project/hersona/) · [フルリファレンス](./docs/REFERENCE.md)

![hersona デモ — 30秒でペルソナを合成して Export](./docs/hersona-demo.gif)

## クイックスタート (30秒)

```bash
pip install hersona          # Python >= 3.11
hersona blend personality/tsundere speech/keigo --weight strong   # 注入ブロック → stdout
hersona export personality/tsundere speech/keigo --format openai_assistants > persona.json
hersona persistent personality/tsundere speech/keigo --target claude   # CLAUDE.md に書き出し
hersona bench tsundere keigo --cost-only                          # 注入コストを実測
```

インストール不要なら **[デモサイト](https://shiro-0x.github.io/hersona/app/)** へ:
属性カタログ・ブレンド・9 問の診断クイズがブラウザで動きます (EN/JA 自動判定)。

## 感覚ではなく、計測

ペルソナは崩れます: 会話中盤で口調が抜け、説得されてキャラを降り、毎ターン
token を消費する。hersona は決定的ベンチマーク (`hersona bench` — LLM 不要・
埋め込み不要・再現可能) を同梱し、維持率・減衰曲線・人格上書き攻撃への
ロック耐性・weight 別 token コストを数値化します。その効果の実測
(2026-07-12、minimax/MiniMax-M3、`tsundere + keigo` を `--weight strong` で、
人格上書き攻撃シナリオ):

| 条件 | 維持率 | 平均スコア | ロック耐性 |
|---|---:|---:|---:|
| hersona ブレンド + `persona_lock` | **92%** | **86.1** | **100%** |
| hersona ブレンド | 58% | 66.5 | 67% |
| 手書き 41 token ベースライン | 8% | 55.4 | 0% |
| ペルソナ無し | 0% | 10.8 | 0% |

手書きプロンプトは書いた時点の 1 つの声に固定される — `strong` を求めても
追従できませんが、hersona は同じ属性を新しい weight で再レンダリングするだけ。
正直な注意点: これは 1 モデル・1 シナリオ対の結果で、再実行では数値が振れる
ため、単発の順位は信用しないこと。全表・全注意点・自分で hersona あり/なしを
比較する手順は [`docs/BENCHMARKS.md`](./docs/BENCHMARKS.md)(英語)。

## エージェントが既に読む設定ファイルへ直接書き出す

`hersona persistent --target` は、コーディングエージェントの規約ファイルへ
ペルソナを直接書き込みます:

| Target | 書き出し先 | 対応エージェント |
|---|---|---|
| `--target codex` (別名 `agents`) | `AGENTS.md` | 事実上の標準 — Codex / Cursor / Copilot / Windsurf / Aider / Gemini CLI / Zed が native に読む |
| `--target claude` | `CLAUDE.md` | Claude Code |
| `--target cursor_mdc` (別名 `cursor-rules`) | `.cursor/rules/hersona-persona.mdc` | Cursor（現行形式、`alwaysApply: true`） |
| `--target copilot` | `.github/copilot-instructions.md` | GitHub Copilot |
| `--target gemini` | `GEMINI.md` | Gemini CLI |
| `--target cursor` | `.cursorrules` | Cursor — **旧単一ファイル形式・非推奨**（警告を表示） |

4 つのコピーを持つより**正本 1 つ**が良い: `AGENTS.md` は Agentic AI Foundation
(Linux Foundation) が stewardship を持ち多くのエージェントが native に読みますが、
Claude Code は `CLAUDE.md` を読みます。そこで `AGENTS.md` を書き、それを import
する薄い `CLAUDE.md` を併置します:

```bash
hersona persistent tsundere keigo --target agents --with-claude-import
```

ペルソナ本文は `AGENTS.md` に 1 回だけ書かれ、`CLAUDE.md` は `@AGENTS.md` を
含む 2 行になります — ドリフトする余地がありません。

`hersona export` はそれ以外の基盤への受け渡し — `json` / `messages`
(chat 配列) / `markdown` / `openai_assistants` / `langchain_system_message`。

## 中身

schema-validated な **346 属性** のライブラリ
（personality 43 / speech 140 / archetype 66 / visual 46 / hobby 51）:

- **Personality** — tsundere, kuudere, yandere, airhead, intellectual, …
- **Speech** — kansai_ben, keigo, mandarin_casual, banmal, british_en, valley_girl_en, …
- **Archetype** — heroine, mentor, rival, idol, knight, villain, …
- **Visual** — silver_hair, glasses, petite, animal_ears, heterochromia, …
- **Hobby** — cooking, gamer, music, reading, astronomy, …

各属性は `core_traits` / `catchphrases` / `tone` に加え、
`compatible_archetypes` / `conflicts_with` の組み合わせ行列を宣言。
blend engine が互換性のない組み合わせを警告し、強度は属性ごとに調整できます
（`mild` / `moderate` / `strong`、または `tsundere:strong keigo:mild` のインライン指定）。

hersona は**ペルソナレイヤー**であり、agent フレームワークではありません —
キャラクター・ブランドボイス・ロールプレイ相手を一貫させる仕組みで、推論・
検索・tool-calling は改善しません。固定ペルソナ 1 つなら手書きプロンプトで
十分。切替・ブレンド・測定・使い回しを始めた時に hersona が効いてきます
（[使いどころの判断](./docs/REFERENCE.md#hersona-の使いどころと使わないところ)）。

## Hermes Agent で使う

審査なし・今すぐ tap 経由でインストール可能:

```bash
hermes skills tap add shiro-0x/hersona
hermes skills install hersona
hermes skills install hersona-initializer
```

会話の中で属性をアタッチ:

```
/hersona list                         # 利用可能な属性一覧
/hersona personality/tsundere single  # 1 属性のみアタッチ
/hersona personality/tsundere speech/keigo multi  # 複数属性ブレンド
/hersona personality/tsundere strong speech/keigo mild  # 属性ごとの強度指定
/hersona default                      # 解除
```

レシピ集（プリセット保存、プレビュー、口調の積み増しなど）は
[docs/REFERENCE.md](./docs/REFERENCE.md#hermes-agent-skill--レシピ集)、
skill の挙動メモは [skills/hersona/SKILL.md](./skills/hersona/SKILL.md) を参照。

## MCP サーバーとして使う（任意）

カタログ・ブレンド・export に加え、決定的ペルソナスコアラー
（`measure_intensity` / `bench_transcript` — エージェントが自分の応答を採点して
自己修正できる）を Claude Desktop などの MCP 対応 agent に公開します:

```bash
pip install "hersona[mcp]"
hersona-mcp        # stdio MCP server
```

ツール一覧表は [docs/REFERENCE.md](./docs/REFERENCE.md#mcp-サーバー詳細) を参照。

## ブレンドの先へ

- **その他の CLI** — `reanchor`（会話途中でペルソナが崩れたとき送り直す短い
  アンカー）、`recommend`（診断クイズ）、`measure`（任意テキストの採点）、
  `diff`、`save`/`load` プリセット、`create`(自作属性)、
  `update`（再インストールせずテンプレート最新化）: すべて
  [CLI リファレンス](./docs/REFERENCE.md#cli-リファレンス)に。
- **Use case（20 本）** — `--use-case programmer` でペルソナの上にプロ向け
  作業規律を重ねる（`hersona use-case list`）。
- **ペルソナパック（14 本）** — Hermes のマルチ personality レジストリ向けの、
  conflict 検査済み名前付きレシピ（`hersona personas list`）。
- **ガイド** — [自己紹介](./docs/guides/self-introduction.ja.md) などの
  ペルソナ横断プレイブック。
- **オプション extras** — `pip install "hersona[tui]"` でリッチ CLI 出力、
  `"hersona[completion]"` でシェル tab 補完。

いずれも詳細は [docs/REFERENCE.md](./docs/REFERENCE.md) にまとめています。

## データ形式

各属性は `attributes/<category>/<name>.yaml` の YAML ファイルで、
[`schema/attribute.schema.json`](./schema/attribute.schema.json) に準拠
（`python scripts/validate.py` で検証）。346 属性の全カタログと
フィールドごとのスキーマ解説は
[docs/REFERENCE.md](./docs/REFERENCE.md#データ形式) を参照。

## ライセンス

| 範囲 | ライセンス |
|---|---|
| コード (`hersona/`, `scripts/`, `schema/` など) | **MIT** ([LICENSE](./LICENSE)) |
| テンプレート (`attributes/`, `personas/`) | **CC0 1.0** ([LICENSE-CC0.txt](./LICENSE-CC0.txt)) |

あわせて [DISCLAIMER.md](./DISCLAIMER.md) と [SECURITY.md](./SECURITY.md)
（`hersona update` の checksum 検証が守る範囲・守らない範囲）も参照。

## コントリビュート

1. 属性テンプレートの追加は `attributes/<category>/<name>.yaml` 形式で —
   `examples` / `core_traits` / `catchphrases` 等に固有名詞・特定作品を含めない
2. PR 前に `python scripts/validate.py` で検証
3. 1 PR = 1 属性が基本。複数追加時は事前 Issue で合意

詳細は [CONTRIBUTING.md](./CONTRIBUTING.md) を参照。hersona をプロジェクトで
使っていたら [USED_BY.md](./USED_BY.md) へ。エージェント／開発者向けの
実装指示書は [docs/IMPLEMENTATION_GUIDE.md](./docs/IMPLEMENTATION_GUIDE.md)。
