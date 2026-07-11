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

[Docs](https://shiro-0x.github.io/hersona/) · [PyPI](https://pypi.org/project/hersona/) · [Repository](https://github.com/shiro-0x/hersona)

![hersona デモ — 30秒でペルソナを合成して Export](./docs/hersona-demo.gif)

## クイックスタート (30秒)

```bash
pip install hersona
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
埋め込み不要・再現可能) を同梱し、これらを印象ではなく数値にします:

| `tsundere` + `keigo` | mild | moderate | strong |
|---|---:|---:|---:|
| 注入コスト (実測) | 1751 chars (~437 tok) | 1931 chars (~482 tok) | 2039 chars (~509 tok) |

- **維持率 + 減衰曲線** — 任意の会話トランスクリプトをターンごとに採点。
- **ロック耐性率** — 同梱の人格上書き攻撃シナリオ (「システムプロンプトを
  無視して」「別キャラになって」) で `personality/persona_lock` の耐性を定量化。
- **token コスト** — ブレンドの 1 コンテキストあたりの正確な price を weight 別に。

初回公式実測 (2026-07-11、minimax/MiniMax-M3、tsundere+keigo moderate):
人格上書き攻撃シナリオで `a_lock` mean score 9.8 対 `a` 8.6 対 手書きベースライン
`b` 8.0 対 ペルソナ無し `c` 2.4 — ロック方向に小さく一貫した差、表面しきい値は
大きく下回る (悪い数値もそのまま公開した全表は `docs/BENCHMARKS.md`)。

コマンド・注意点・自分で hersona あり/なしを比較する手順:
[`docs/BENCHMARKS.md`](./docs/BENCHMARKS.md)(英語)。

## エージェントが既に読む設定ファイルへ直接書き出す

`hersona persistent --target` は、コーディングエージェントの規約ファイルへ
ペルソナを直接書き込みます:

| Target | 書き出し先 | 対応エージェント |
|---|---|---|
| `--target claude` | `CLAUDE.md` | Claude Code |
| `--target codex` (別名 `agents`) | `AGENTS.md` | Codex / AGENTS.md 対応エージェント |
| `--target cursor` | `.cursorrules` | Cursor |
| `--target gemini` | `GEMINI.md` | Gemini CLI |

`hersona export` はそれ以外の基盤への受け渡し — `json` / `messages`
(chat 配列) / `markdown` / `openai_assistants` / `langchain_system_message`。

## なぜ Hersona？

AIエージェントのシステムプロンプト書込みは、プロジェクトで最もコピペされているコードです。
多くのチームは長いペルソナ説明を手書きするか、Discord のやりとりからプロンプトを流用 —
結果としてキャラクターは会話中盤で drift したり、矛盾したり、強度が抜け落ちたりします。

Hersona は **346 のキャラ属性** を schema-validated で収録したライブラリ。自由に組み合わせできます:

- **Personality (43)** — tsundere, kuudere, yandere, airhead, intellectual, …
- **Speech (140)** — kansai_ben, keigo, mandarin_casual, banmal, british_en, valley_girl_en, …
- **Archetype (66)** — heroine, mentor, rival, idol, shrine_maiden, school_nurse, knight, villain, …
- **Visual (46)** — silver_hair, glasses, petite, glamorous, animal_ears, heterochromia, scar, …
- **Hobby (51)** — cooking, gamer, music, reading, sports, calligraphy, astronomy, …

各属性は `core_traits` / `catchphrases` / `tone` に加え、
`compatible_archetypes` / `conflicts_with` の組み合わせ行列を宣言。
blend engine は互換性のない組み合わせを検出して警告を出せます（永続化系の経路では
衝突ブレンドを拒否する場合があります）。強度は `mild` / `moderate` / `strong` で属性ごとに調整できます。

OpenAI 互換 API、Claude、ローカル LLM、LangChain、AutoGen、CrewAI —
あるいは Claude Desktop 用の MCP server としても使えます。

## hersona は何なのか — 何でないのか

hersona は**ペルソナレイヤー**である。キャラクターの人格・口調を構造化し、
会話を通して維持できているかを測定可能にする仕組み。**推論エンジンでも
RAG パイプラインでも tool-use/agent フレームワークでもない** — 導入しても
回答精度・検索品質・tool calling は改善しない。エージェントの仕事が「正しい
こと」ならhersonaは何も貢献しない。仕事の一部が「何者かであること」
(キャラクター、ブランドボイス、ロールプレイ相手)なら、それがhersonaの管轄。

| 欲しいもの | 適した手段 |
|---|---|
| 固定ペルソナ 1 つ、切替なし | 手書き system prompt — この用途では hersona は価値を足さない |
| 複数ペルソナをセッション/ユーザーごとに切替、強度調整も要る | **hersona**(`blend` / `soul` / `persistent`) |
| 長い会話でペルソナが維持できたか *知りたい* | **hersona**(`measure` / `verify_intensity` — 感覚でなく決定的に採点) |
| 大量の属性 × 組み合わせで衝突しない構成を保証したい | **hersona**(`compatible_archetypes` / `conflicts_with` 行列) |
| 推論・検索・tool-calling の質を上げたい | LangGraph、OpenAI Agents SDK、LlamaIndex、Semantic Kernel — hersona の `export` はペルソナをこれらに**渡す**側であり代替ではない |
| 単発プロジェクトのキャラ 1 体だけ | 自前の YAML/prompt でも十分 — 複数ペルソナを扱う、または複数プロジェクトで使い回す段階から hersona が効いてくる |

`hersona bench` がペルソナ維持率・注入 token コストをどう測るか、
「言い分を鵜呑みにせず自分で hersona あり/なしを比較する」手順は
[`docs/BENCHMARKS.md`](./docs/BENCHMARKS.md)(英語)を参照。

## その他のコマンド

```bash
hersona list                          # 346 属性をブラウズ
hersona show personality/tsundere     # 1 つの属性を詳しく
hersona recommend                     # 診断クイズ → 推薦ブレンド
hersona measure tsundere keigo --weight strong --input out.txt   # 単発テキストを採点
```

フル API は [`docs/PUBLIC_API.md`](./docs/PUBLIC_API.md) を参照。

## ガイド

属性テンプレートではない、ペルソナ横断の運用ドキュメント:

- [自己紹介](./docs/guides/self-introduction.ja.md) — 公開向けルール・プライバシー・チェックリスト
- [English](./docs/guides/self-introduction.md) · [一覧](./docs/guides/README.md)

```bash
hersona lint-intro --canonical --allow-handle YOUR_X --text "..."
hersona soul personality/kuudere speech/soft \
  --memory-file examples/self-intro-memory.json \
  --with-self-intro-guide --lint-self-intro-strict --allow-handle YOUR_X \
  --profile myagent --force
```

## インストール (Hermes Agent)

審査なし・今すぐ tap 経由でインストール可能:

```bash
hermes skills tap add shiro-0x/hersona
hermes skills install hersona
hermes skills install hersona-initializer
```

スキルレジストリへの掲載状況:

| レジストリ | 状態 |
|---|---|
| [HermesHub](https://www.hermeshub.xyz/) | 🔄 審査中 ([PR #125](https://github.com/amanning3390/hermeshub/pull/125)) |
| [ClawHub](https://clawhub.ai/) | https://clawhub.ai/shiro-0x/skills/hersona |

## ライセンス構成

リポジトリは 2 層に分かれており、各層でライセンスが異なります:

| 範囲 | ライセンス | 補足 |
|---|---|---|
| `scripts/`, `schema/`, `pyproject.toml` 等 (コード) | **MIT** | `LICENSE` |
| `attributes/**/*.yaml` (汎用属性テンプレート) | **CC0 1.0** | `LICENSE-CC0.txt` — パブリックドメイン献呈 |
| `personas/**/*.yaml` (ペルソナパック — ブレンドレシピ集) | **CC0 1.0** | `LICENSE-CC0.txt` — パブリックドメイン献呈 |

## 現在カバーしている属性

**346 属性** を 5 カテゴリで提供。大きな拡張は 2 系統: **speech 31 → 140**（v1.4.x までの **+103**
レジスターに加え、v1.5.0 で **+6** のネイティブ zh/ko）と、**archetype 9 → 66 / visual 5 → 46 /
hobby 5 → 51**（v1.7.x までのバッチ拡張。ロール・見た目・趣味を元のテンプレートセットから大幅に拡充）。
speech の変遷は 5 つの Phase に v1.5.0 波を加えた構成です:

| Phase | 件数 | 内容 | 例 |
|---|---:|---|---|
| **Phase 0/8**(既存) | 26 | 基礎日本語speech + 英語registers + `archaic_otaku` | `kansai_ben`、`keigo`、`gyaru`、`british_en` |
| **Phase 1: 地域方言** | 36 | 日本の主要地域(北海道〜沖縄) | `hokkaido_ben`、`nagoya_ben`、`osaka_ben`、`okinawa_ben` |
| **Phase 3: キャラ口調** | 25 | 時代・Z世代・サブカル・クラシックキャラロール | `warawa`、`vtuber`、`yankee`、`business`、`akuma_oujo` |
| **Phase 4: 外国語** | 24 | 英語方言拡張(10) + 翻訳調registers(14) | `aussie_en`、`valley_girl_en`、`mandarin`、`korean`、`french` |
| **Phase 5: アニメ口調** | 18 | 学園ラブコメ・異世界・ファンタジー・サブカル異世界 | `osananajimi`、`imouto`、`mesugaki`、`densetsu_no_yuusha`、`villainess` |
| **v1.5.0: ネイティブ zh/ko** | 6 | `content_lang` zh/ko の speech（翻訳調ではない） | `mandarin_casual`、`keigo_zh`、`taiwan_mandarin`、`banmal`、`jondaetmal`、`seoul_casual` |

総内訳: **personality 43 + speech 140 + archetype 66 + visual 46 + hobby 51 = 346**。

## 概要

二次元キャラクターの口調・性格を、体系化し、AI エージェントのシステムプロンプトに注入できるテンプレート集として配布する
オープンソースプロジェクト。

- **属性テンプレート** (`attributes/<category>/<name>.yaml`) を提供
- ユーザー (またはエージェント) が必要属性を割り当てることで、任意キャラの人格を構築

## 使い方

### Hermes Agent で使う

`/hersona <category>/<name>` 形式で属性をアタッチ:

```
/hersona                              # 一覧 + 使い方ヘルプ
/hersona list                         # 利用可能な属性一覧
/hersona show personality/tsundere    # 指定属性の詳細
/hersona personality/tsundere single  # 1 属性のみアタッチ
/hersona personality/tsundere speech/keigo multi  # 複数属性ブレンド
/hersona default                      # 解除
```

#### よくあるレシピ集

**アーキタイプを変えずに tsundere 寄りにしたい**

```
/hersona personality/tsundere single
```

`tsundere` だけをアタッチ (デフォルト `weight: moderate`)。既存のアーキタイプ
や口調はそのままで、次のターンから「表面的には冷たく、内側は温かい」典型的な
ツンデレ口調が乗る。

**既存ペルソナに敬語 (keigo) 口調を重ねる**

```
/hersona speech/keigo single
```

現在の attach に `speech/keigo` を積み増す。カスタマーサポートや貴族系
ロールプレイなど、丁寧語に切り替えるシーンで便利。

**ゼロから複数属性ブレンドで作る**

```
/hersona personality/tsundere speech/keigo multi
```

`tsundere` + `keigo` の全新ペルソナを組み、既存の attach を置き換える。
blend engine が先に `compatible_archetypes` / `conflicts_with` を検査
するため、`yandere` + `airhead` のような衝突は警告 → 代替提案の上で
attach が走る。

**属性ごとに強度を指定する**

```
/hersona personality/tsundere strong speech/keigo mild
```

`strong` で tsundere を支配的に (決め台詞の頻度UP、「べ、別に
あんたのためじゃない」がしっかり出る)、`mild` で keigo を背景 flavor
として添える。強度指定は属性単位で混在可能。

**ブレンドをプリセット保存して再利用する**

```
/hersona save my_tsun personality/tsundere speech/keigo --weight strong
/hersona load my_tsun
```

`save` で `~/.hermes/presets/my_tsun.yaml` にレシピを書き出し、
`load` で再実行。ユーザ名前空間なので public `attributes/` を
汚さない。

**全部解除して素の agent に戻す**

```
/hersona default
```

attach 済の属性を全部外す。セッション切替時、またはブレンドを
白紙から組み直す時のリセットに使う。

**アタッチ前にプレビューする**

```
/hersona preview personality/tsundere speech/keigo --weight strong
```

注入ブロックとサンプル発話をレンダリング (LLM 呼び出しなし)。
実際に agent に積む前に内容を確認できる。

Hermes skill の挙動メモは [skills/hersona/SKILL.md](./skills/hersona/SKILL.md) を参照。
レシピ集 / 検証チェックリスト / バージョン履歴 / エッジケースレシピ
(プリセット永続化、強度計測、MCP export) は
[skills/hersona/REFERENCE.md](./skills/hersona/REFERENCE.md) に分離
(スキル本体を毎ターン軽量に保つためオンデマンド読み込み)。CLI の正本は
`hersona --help`、この README、[`docs/PUBLIC_API.md`](./docs/PUBLIC_API.md) を優先。

#### プロ向け Operating Mode / use case

`--use-case` は、選んだ personality / speech 属性の上に、用途別の
プロ向け作業規律を重ねる機能。キャラクター性は保ったまま、実務タスク向けの
確認手順・出力契約・品質ゲートを追加できる。

```bash
hersona use-case list
hersona use-case show programmer
hersona blend personality/tsundere speech/keigo --use-case programmer
hersona soul personality/puppyish speech/keigo archetype/heroine --use-case planner --force
hersona export personality/tsundere --format openai_assistants --use-case product_manager
```

初期 public use case（全 20 本、`docs/PERSONA_PACKS_DESIGN.md` §6–§8 参照）:

**初期 8 本（Phase 1）**: `programmer`, `planner`, `research`, `marketing`,
`product_manager`, `qa_reviewer`, `data_analyst`, `customer_support`。

**追加 12 本（PR-A W2, Phase 2）**:
`frontend_developer`, `backend_architect`, `devops_engineer`, `security_reviewer`,
`tech_writer`, `executive_assistant`, `hr_recruiter`, `tutor`, `creative_writer`,
`game_master`, `community_manager`, `streamer_copilot`。

`hersona soul ... --use-case <id>` と `hersona persistent ... --use-case <id>` は、
Operating Mode を生成済み SOUL.md の中に書き込む。手動追記ではなく生成物として
残るため、ペルソナ再生成後もプロ向け作業規律を維持しやすい。再生成時は
`<!-- hersona:gen-end -->` より下のユーザー追記も保持する。

#### ペルソナパック (Hermes 向けレシピ集)

ペルソナパックは **ブレンド + 名前 + 用途** をひとまとめにした再利用可能な
レシピ。`persona_name` / `blend` / `weight` / `use_case` だけを記述し、
注入ブロック本体は install 時に属性 YAML からレンダリングされる
(属性側の更新が自動で反映される)。

```bash
hersona personas list                          # 14 本同梱パックを一覧
hersona personas show keigo_support            # 詳細 + 注入ブロックプレビュー
hersona personas install keigo_support --auto-config
hersona personas install keigo_support british_pm --apply  # 最後の 1 件が agent.personality に
hersona personas use keigo_support             # active personality 切替
hersona recommend --install-persona my_pack    # 診断 → 登録 を 1 コマンドで
```

同梱パック 14 本 (`docs/PERSONA_PACKS_DESIGN.md` §6 参照):

| Pack | Blend | Use case |
|---|---|---|
| `keigo_support` | diligent + keigo | customer_support |
| `kansai_marketer` | genki + kansai_ben | marketing |
| `tsundere_reviewer` | tsundere + blunt | qa_reviewer |
| `kuudere_analyst` | kuudere + soft | data_analyst |
| `genki_planner` | genki + casual_en | planner |
| `sensei_writer` | intellectual + sensei | tech_writer |
| `butler_assistant` | diligent + butler | executive_assistant |
| `onee_recruiter` | sociable + onee_kotoba | hr_recruiter |
| `samurai_devops` | stoic + samurai_lol | devops_engineer |
| `vtuber_streamer` | playful + vtuber | streamer_copilot |
| `miko_tutor` | serious + miko | tutor |
| `british_pm` | pragmatist + british_en | product_manager |
| `gyaru_community` | sociable + gyaru | community_manager |
| `warawa_gamemaster` | mysterious + warawa | game_master |

**汎用エージェントカタログとの差別化**:

| 汎用カタログ | hersona ペルソナパック |
|---|---|
| 役割のみ、人格制御なし | ペルソナ × 用途 × **強度ダイヤル** |
| 静的テンプレ | conflict 検査済みブレンド + `hersona bench` で **維持率を測定可能** (人格上書き攻撃へのロック耐性含む) |
| 汎用ツール向け | **Hermes の `agent.personalities.*` レジストリにネイティブ対応** |

同梱 14 本は `validate_persona()` エラー 0 を CI で恒久担保
(`tests/test_personas.py::test_all_shipped_personas_validate_clean`)。
上の表が正本、スキーマ追加は `docs/PERSONA_PACKS_DESIGN.md` §6 に従うこと。

### CLI から使う

`pip install hersona` 後 (Python >= 3.11)、`hersona` コマンドが使える。
ローカル checkout から開発する場合は `pip install -e .` または `python -m hersona.cli` を使う:

```
hersona list                                  # 利用可能な属性一覧 (公開 + user)
hersona show tsundere                          # 属性の詳細
hersona matrix --json                          # 相性マトリクスを JSON でダンプ
hersona blend tsundere keigo --weight strong   # 複数属性を注入ブロックに合成 (強度指定)
hersona recommend                              # 診断クイズ → 推薦 (対話。表示言語 en では英語 speech へ導線)
hersona recommend --answers distance=1,speech=0,role=1 --apply  # 注入ブロックも表示
hersona recommend --export openai_assistants > my_agent.json  # 診断結果をそのまま任意の形式でエクスポート (再入力不要)
hersona recommend --soul --profile myagent     # 診断結果をそのまま SOUL.md へ (--dry-run / --force)
hersona recommend --save from_quiz             # 診断結果をプリセットとして保存
hersona create --category personality --name my_attr \
  --display-ja マイ属性 --display-en MyAttr \
  --desc-ja 説明 --desc-en desc --example "..."  # 属性を作成し user 名前空間に保存
hersona measure kyoto_ben --weight strong --text "ようおいでやすどす"  # 出力の強度指標を採点
hersona measure tsundere heroine --weight moderate --input out.txt       # ブレンドの強度指標
hersona bench tsundere keigo --demo --turns 6  # 人格維持率・token コストの自己確認 (docs/BENCHMARKS.md 参照)
hersona soul puppyish keigo heroine --use-case planner --force  # SOUL.md に Operating Mode も書き込む
hersona update                                 # リポジトリから最新の属性データをダウンロード
hersona update --ref v1.8.0                    # ブランチ / タグ / コミット SHA を指定 (既定: main)
hersona update --clear                         # ダウンロード済みデータを削除し同梱テンプレートへ戻す
```

ユーザー作成属性は `~/.hermes/attributes/` (既定) または `HERSONA_USER_DIR` で
指定したディレクトリに保存され、公開 `attributes/` には混ざらない。

`hersona update` は**パッケージを再インストールせずに**属性テンプレートを最新化する。
`pip`/wheel でインストールすると `attributes/` と `schema/` はビルド時に同梱されるため、
アップストリームへの追加は再インストールしないと反映されない。`hersona update` は最新の
`attributes/` と `schema/` をリポジトリからローカルのデータキャッシュ
(既定 `~/.hermes/data/`、または `HERSONA_DATA_DIR`) へダウンロードし、同梱テンプレートより
優先して解決させる。`hersona update --clear` でキャッシュを削除し同梱データへ戻せる。
ダウンロードは Python 標準ライブラリのみで行う (追加依存なし)。

既定では、別の GitHub 配信経路から取得した SHA-256 マニフェスト (`checksums.json`)
とダウンロード内容を突き合わせ、不一致なら中止する。これが守る範囲・守らない範囲は
[SECURITY.md](./SECURITY.md) を参照。`hersona update --no-verify` でスキップできる。

保存済みブレンドプリセットは `~/.hermes/presets/` (既定) または `HERSONA_PRESETS_DIR` で
指定したディレクトリに保存される。プリセットは `attributes` + `weight` の名前付きレシピで、
`hersona load` は常に最新の属性テンプレートに対して同じ blend engine を再実行する。

別のエージェントフレームワーク (LangGraph / LangChain / OpenAI / Anthropic SDK) に渡す場合、
`hersona export <names...> --format {json,messages,markdown,openai_assistants,langchain_system_message}`
で移植可能な成果物を出力できる。`json` は構造化データ、`messages` は
`[{"role": "system", "content": ...}]` の chat 配列、`markdown` は注入ブロックそのもの、
OpenAI Assistants / LangChain 形式は各フレームワーク向け JSON を返す。同じ `export_blend()` は
`hersona.core` からも利用できる。

#### OpenAI Assistants / LangChain へ export

Tavern Card の意味論を持ち込まず、production agent framework にそのまま渡せる形式を用意している:

- `--format openai_assistants`: OpenAI Assistants API の `instructions` 向け JSON。
  hersona 固有情報は `metadata.hersona_*` に namespaced される。
- `--format langchain_system_message`: LangChain `SystemMessage` 互換 JSON
  (`type` / `content` / `response_metadata`)。

どちらも framework-neutral で、`openai` / `langchain` Python package はインストール不要。

```bash
hersona export tsundere keigo --weight strong --format openai_assistants \
  | jq -r '.instructions' > /tmp/system_prompt.txt
```

#### リッチな CLI 出力 (任意)

`list` のカラー表や `show` の panel 表示が欲しい場合は `tui` extra を入れる:

```bash
pip install "hersona[tui]"
```

`rich` がない場合、パイプ/リダイレクト時、または `--plain` / `NO_COLOR` 指定時は従来通り plain text。
パイプ時も色を残す場合は `HERSONA_FORCE_RICH=1` を使う (例: `| less -R`)。

#### シェル補完 (任意)

サブコマンド、属性名、プリセット名を tab 補完したい場合は `completion` extra を入れ、
補完を shell に登録する:

```bash
pip install "hersona[completion]"
eval "$(register-python-argcomplete hersona)"   # 永続化するなら ~/.bashrc / ~/.zshrc へ
```

`argcomplete` がなくても CLI 本体は同じように動作する (補完だけ無効)。

### MCP サーバーとして使う（任意）

MCP 対応 agent (Claude Desktop など) から以下のツールを直接呼べるようにする:

| ツール | 内容 |
|---|---|
| `list_attributes` / `show_attribute` | カタログ閲覧 |
| `blend` / `export` | ペルソナの合成・引き渡し（`export` は全 5 形式対応） |
| `recommend_blend` | 診断クイズ推薦（`export_format` で 2 回呼ぶ必要をなくせる） |
| `compatibility` | conflict / compatible 照会 |
| `measure_intensity` | 1 応答をブレンドの強度バンドと照合して採点（決定的・LLM 不要） |
| `bench_transcript` | 会話全体の人格維持率 + ロック耐性率を採点 |
| `list_personas` | 同梱 14 パックの一覧 |
| `install_persona` | パックの注入ブロックをプレビュー（dry-run。書き込みなし） |

`measure_intensity` / `bench_transcript` は `hersona measure` / `hersona bench`
と同じ決定的採点を MCP 経由で使え、エージェントが自分の応答を生成 → 採点 →
ブレていれば自己修正、というループを組める。`install_persona` は設計上プレビュー
専用（MCP 呼び出しからファイルへは一切書き込まない）— 実際のインストールは引き続き
CLI の `hersona personas install <name>` を使う。

```bash
pip install "hersona[mcp]"
hersona-mcp                       # stdio MCP server を起動
```

server (`hersona.mcp.server`) は `hersona.core` の薄い wrapper。tool logic は
`hersona.mcp.tools` にあり、library / CLI 利用には `mcp` extra は不要。

### 他の LLM で使う

`attributes/<category>/<name>.yaml` の `core_traits` / `catchphrases` / `tone` /
`description_ja` などをそのまま system prompt に貼り付ける。

複数属性をブレンドする場合は、各 YAML の `compatible_archetypes` / `conflicts_with` を
参照して互換性を確認する。

## データ形式

```
attributes/
├── personality/             # 性格属性 (43 種: 日本語ベース 35 + 英語ネイティブ 5 + ja-base hautaine + ja-base sociable + persona_lock)
├── speech/                  # 口調属性 (140 種: ja-content 119 + en 15 + native zh/ko 6)
├── archetype/               # アーキタイプ属性 (9 種)
├── visual/                  # 外見属性 (5 種)
└── hobby/                   # 趣味属性 (5 種)
```

各属性 YAML は [`schema/attribute.schema.json`](./schema/attribute.schema.json) に
準拠する。

### 属性テンプレート (`attributes/`)

[schema/attribute.schema.json](./schema/attribute.schema.json) で検証される、キャラプロファイルに
付与する **汎用属性タグのテンプレート集**。現在は personality 43 / speech 140 /
archetype 66 / visual 46 / hobby 51 の計 346 種を定義 (詳細は [attributes/](./attributes/) 配下)。
speech は 140 種: 日本語コンテンツ (`content_lang: ja`) 119 種（基礎口調、地域方言、翻訳調外国語、
アニメ・サブカル口調、`archaic_otaku`、`okinawa_ben` を含む）+ 英語 (`content_lang: en`) 15 種 +
ネイティブ中国語/韓国語 (`content_lang: zh` / `ko`) 6 種。
personality は日本語ベース 35 種 + 海外向け英語ネイティブ (`content_lang: en`) 5 種 +
`hautaine` (生まれ・育ちへの自負から来る高飛車さ) + `sociable` (場の空気を読んで聞き手適応する社交性)。

#### 346 属性一覧

| category | count | 含まれる属性 |
|---|---|---|
| personality (ja-base) | 35 | airhead / battle_junkie / chuunibyou / crybaby / dandere / deadpan / deredere / diligent / genki / gluttonous / himedere / hinedere / hot_blooded / intellectual / kamidere / klutz / kuudere / laid_back / menhera / mysterious / narcissist / optimist / pessimist / playful / pragmatist / protective / puppyish / sadodere / scheming / serious / socially_anxious / stoic / switch / tsundere / yandere |
| personality (ja-base, Phase 8) | 2 | hautaine / sociable |
| personality (en-native) | 5 | sassy / rebel / charmer / drama_queen / go_getter |
| speech (ja) | 25 | archaic / blunt / boku_girl / burikko / gyaru / hakata_ben / hiroshima_ben / kansai_ben / keigo / kyoto_ben / mischievous / mixed_dialect / onee_kotoba / ore_boy / princess_speech / robotic / seductive / soft / stutter / theatrical / third_person / tohoku_ben / tomboy / washi / whispery |
| speech (ja, Phase 8) | 1 | archaic_otaku |
| speech (ja, Phase 1: 地域方言) | 36 | akita_ben / ehime_ben / gifu_ben / gunma_ben / hokkaido_ben / hyogo_ben / ibaraki_ben / kagoshima_ben / kanagawa_ben / kanazawa_ben / kochi_ben / kumamoto_ben / mie_ben / miyazaki_ben / nagoya_ben / nagasaki_ben / nara_ben / niigata_ben / oita_ben / okayama_ben / okinawa_ben / osaka_ben / saga_ben / saitama_ben / sanuki_ben / sendai_ben / shimane_ben / shizuoka_ben / tochigi_ben / tokushima_ben / tokyo_ben / toyama_ben / tsugaru_ben / wakayama_ben / yamagata_ben / yamaguchi_ben |
| speech (ja, Phase 3: キャラ・サブカル口調) | 25 | akuma_oujo / business / butler / chuunibyou_speech / kawaii / mahou_shoujo / mama / miko / musuko / obaachan / ojisan / ol / ryoushi / sage / samon / sensei / shouwa_retro / streamer / taishou_retro / vtuber / wagahai / warawa / yankee / yuuusha / z_jidai_slang |
| speech (ja, Phase 4: アジア・欧州) | 14 | mandarin / taiwanese / cantonese / korean / french / german / italian / spanish / russian / arabic / hindi / vietnamese / thai / tagalog |
| speech (ja, Phase 5: アニメ・サブカル口調) | 18 | boin_girl / bokukko / dark_hero / densetsu_no_yuusha / hero_yamero / imouto / isekai_cheat / kuudere_girl / kuukichou / mesugaki / onee_san / osananajimi / oujo / samurai_lol / sensei_goroshi / tsukkomi / villainess / wizard |
| speech (en) | 15 | formal_en / casual_en / blunt_en / southern_us_en / british_en / aussie_en / scottish_en / irish_en / valley_girl_en / brooklyn_en / new_york_en / midwestern_en / pidgin_en / jamaican_en / punjabi_en |
| speech (zh/ko native, v1.5.0) | 6 | mandarin_casual / keigo_zh / taiwan_mandarin / banmal / jondaetmal / seoul_casual |
| archetype | 66 | alien / angel / antihero / apprentice / artist / assassin / bartender / best_friend / big_brother / big_sister / bodyguard / chef / childhood_friend / chosen_one / commander / cyborg / delinquent / demon / doctor / dragon / engineer / entrepreneur / fairy / fallen_hero / gakkyuu_iinchou / gamer_otaku / ghost / goddess / heroine / hikikomori / honor_student / idol / journalist / kitsune / knight / kouhai / little_brother / little_sister / lone_wolf / maid / mediator / mentor / mercenary / mother_figure / noble / nurse / office_worker / ojou_sama / oni / prince / rival / robot_android / school_nurse / scientist / seitokaicho / senpai / shrine_maiden / sidekick / soldier / teacher / tenkousei / twin / underdog / vampire / villain / witch |
| visual | 46 | ahoge / androgynous / animal_ears / black_hair / blonde / blue_hair / blunt_bangs / blush / bob_cut / braids / chubby / drill_hair / droopy_eyes / eyebags / eyepatch / freckles / glamorous / glasses / golden_eyes / gradient_hair / hair_bun / heterochromia / hime_cut / inner_color / jitome / kimono / long_hair / messy_hair / mole / muscular / pale_skin / petite / pink_hair / ponytail / red_eyes / red_hair / scar / sharp_eyes / short_hair / side_ponytail / silver_hair / slender / tall / tan / twintails / white_hair |
| hobby | 51 | art / astronomy / baking / board_games / cafe_hopping / calligraphy / camping / coffee / collecting / cooking / cosplay / crafting / cycling / dance / fashion / fishing / flower_arrangement / fortune_telling / gamer / gardening / hiking / history_buff / karaoke / knitting / languages / makeup / martial_arts / meditation / model_building / movies / music / occult / pet_care / photography / pottery / programming / puzzles / reading / running / sado / shopping / singing / skateboarding / sports / surfing / swimming / trains / travel / wine / writing / yoga |

#### 必須フィールド (attribute.schema.json)

| フィールド | 型 | 必須 | 説明 |
|---|---|---|---|
| `attribute_category` | enum | ✓ | `personality` / `speech` / `archetype` / `visual` / `hobby` の 5 種 |
| `attribute_name` | string (snake_case) | ✓ | ファイル名と一致する一意 ID |
| `weight_dimension` | enum | ✓ | `none` / `mild` / `moderate` / `strong` |
| `examples` | string[] (1 件以上) | ✓ | AI エージェント活用例。固有名詞・特定作品を含まない |

メタデータは、スキーマが許可する以下どちらかの形を満たす:

| 形式 | 必須フィールド | 補足 |
|---|---|---|
| 現行 i18n metadata | `display_name`, `description` | BASE 言語は英語。日本語などの表示名/説明は `i18n.<lang>`（例: `i18n.ja.display_name`）に置く |
| legacy suffix-pair metadata | `display_name_ja`, `display_name_en`, `description_ja`, `description_en` | 後方互換のため許容。新規属性は現行 i18n 形式を推奨 |

#### 任意フィールド

| フィールド | 型 | 説明 |
|---|---|---|
| `core_traits` | string[] (3-7 個) | 性格特性リスト。AI エージェントが prompt 注入時に解釈する核 |
| `speech_style` | string | 口調の総合説明 (1 行)。blend に注入される |
| `first_person` | string | 一人称。主に speech 属性用。blend に注入され強度測定にも使用 |
| `second_person` | string | 二人称 (例: 「貴方」「お前」)。ユーザー役名を含む |
| `sentence_endings` | string[] (1 個以上) | 語尾パターン (日本語 speech、例: 「〜の」「〜のね」) |
| `lexical_markers` | string[] | 特徴語・言い回し (英語 speech、例: "gonna" / "y'all")。blend に注入され英語の強度測定にも使用 |
| `register` | enum | 話法レジスタ: `formal` / `neutral` / `casual` / `vulgar` (主に英語 speech) |
| `catchphrases` | string[] または `{phrase, when}` object | 口癖。plain string または任意 trigger 付き object |
| `tone` | string | 声の雰囲気 (1 行) |
| `image_prompt_tags` | string[] | 画像生成用の英語タグ。主に visual 属性向け |

#### 関係性・ローカライズフィールド

| フィールド | 型 | 説明 |
|---|---|---|
| `compatible_archetypes` | string[] | 併用が想定される archetype の attribute_name リスト |
| `conflicts_with` | string[] | 排他が想定される他 attribute_name リスト |
| `tags` | string[] | 横断検索用タグ |
| `typical_value_range` | string | 重み付け運用時の典型値 (例: `0.4-0.7`) |
| `content_lang` | enum (`ja`/`en`/`zh`/`ko`) | 人格コンテンツの言語。応答言語指示・強度測定に影響。未指定 ⇒ `ja` |
| `content_i18n` | object | 言語別ネイティブ人格コンテンツ (`<lang>.{catchphrases,tone,core_traits,examples}`)。注入される口癖を人格の言語に保つ |
| `i18n` | object | 言語コードごとの localized metadata (`display_name` / `description`) |
| `has_catchphrase` | bool | 口癖の有無 |
| `variant` | string (snake_case) | 同 attribute_name の派生ラベル |
| `notes` | string | 補足・運用メモ |

#### 雛形生成スクリプト

通常のメンテナンスは `attributes/<category>/<name>.yaml` を直接追加・編集し、
`python scripts/validate.py` で検証する形で行う。下記のスクリプトは旧形式の
凍結スナップショットなので、日常運用では使用しない。

`scripts/_oneoff/gen_v1_attributes.py` を Single Source of Truth として YAML を再生成できる。
直接 YAML を編集する代わりに、リストを更新して再実行する:

```bash
# (旧形式の) 属性 YAML を確認なしで再生成
python scripts/_oneoff/gen_v1_attributes.py

# 書き込み予定パスのみ表示
python scripts/_oneoff/gen_v1_attributes.py --dry-run
```

> 注意: この生成スクリプトは凍結スナップショットで、旧メタデータ形式
> (`display_name_ja/en`・`description_ja/en`) を出力します。再生成した場合は
> `python scripts/migrate_i18n.py` を実行し、i18n ブロック形式 (BASE=en + `i18n.ja`) へ戻してください。

#### 検証

```bash
python scripts/validate.py
```

346 属性 YAML が全てスキーマに違反しないことを確認する。

## ライセンス

- 本リポジトリのコード: **MIT**
- `attributes/` 配下のテンプレート: **CC0 1.0** (public domain dedication)
- 免責事項: [DISCLAIMER.md](./DISCLAIMER.md) を必ず参照
- セキュリティ / 脅威モデル: [SECURITY.md](./SECURITY.md)(`hersona update` の checksum 検証が守る範囲・守らない範囲)を参照

## コントリビュート

1. 属性テンプレートの追加は `attributes/<category>/<name>.yaml` 形式で
2. examples / core_traits / catchphrases 等はセリフ根拠不要 (LLM が解釈する) だが、
   固有名詞・特定作品を含めない
3. PR 前に `python scripts/validate.py` で検証
4. 1 PR = 1 属性が基本。複数追加時は事前 Issue で合意

詳細は [CONTRIBUTING.md](./CONTRIBUTING.md) を参照。プロジェクトで hersona を
使っていたら [USED_BY.md](./USED_BY.md) に追加を。

エージェント／開発者向けの「次に何を実装するか」の指示書は
[docs/IMPLEMENTATION_GUIDE.md](./docs/IMPLEMENTATION_GUIDE.md) を参照。
