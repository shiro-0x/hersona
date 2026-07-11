# Hersona v2.0 ロードマップ & OSS成長戦略（改訂版）

> **Build once. Keep personality everywhere.**
> *Composable personalities for every LLM.*

現行バージョン: **v1.8.0**（PyPI）
コンセプト: あらゆるLLM・AIエージェントに一貫した人格を与える標準基盤（The Personality Layer for AI Agents）

---

## 0. リポジトリ実態との突き合わせ（2026-07-10 取り込み時点）

本ドキュメントは戦略（North Star・差別化・Phase 構成）の記録であり、戦術レベルの
実行計画は [`IMPROVEMENT_PLAN_2026-07-10_sharpen-and-grow.md`](./IMPROVEMENT_PLAN_2026-07-10_sharpen-and-grow.md)
（以下 sharpen-and-grow）が担う。取り込みにあたり、下記の通り実態と対応付けた。

| 本ドキュメントの項目 | リポジトリ実態 / 対応 |
|---|---|
| Phase 1「Export 3本」（AGENTS.md / CLAUDE.md / Cursor Rules） | **実装済み**（v1.4.0、`hersona persistent --target claude\|codex\|cursor\|gemini` = CLAUDE.md / AGENTS.md / .cursorrules / GEMINI.md の4形式、`tests/test_targets.py` でテスト済み）。残タスクは README での明示（= Phase 1 の README 刷新に統合） |
| Phase 1「Benchmark 最小版」の Style Retention | **実質実装済み**（`hersona bench` = 決定的採点による維持率・減衰曲線・注入トークンコスト。LLM 不要）。深掘りは sharpen-and-grow **A-1**（persona_lock 耐性ベンチ）/ **A-2**（公式 vs-baseline 実測）として実行 |
| Phase 1「Benchmark 最小版」の Cross-model Drift（埋め込みコサイン距離） | **見送り（2026-07-10 決定）**。埋め込み依存は「軽量・決定的」ポジションに反するとして過去2回却下済み（`IMPROVEMENT_DISCUSSION_2026-06-15.md` / sharpen-and-grow §6）。モデル間比較は A-2 の決定的採点（同一シナリオ × 複数モデルの維持率比較）で代替し、埋め込み版は要望が来たら Backlog から昇格 |
| §3.3 の「N=20 応答生成（GPT/Claude/Gemini に投げる）」 | `benchmarks/run_comparison.py`（A-2）が担う。**core は LLM 依存ゼロを維持**し、スクリプトは stdlib のみで API を叩く開発用ツールとして package 外に置く |
| North Star「週次 Export 実行数（WPE）」の計測 | **テレメトリは実装しない（2026-07-10 決定）**。パッケージに計測コードは入れず、代理指標（PyPI DL / デモサイト計測 / レジストリ流入。`IMPROVEMENT_PLAN.md` §2.2「週間人格注入数」と同枠）で観測する |
| Phase 1「README 刷新」 | 2026-07-10 実施（タグライン・デモ・Quick Start・実測ベンチ表・Export 先の明示。EN/JA 同期） |
| §5「Integrations 3本に集中」 | 展開先は実装済み4形式で充足。フレームワーク統合の実例（LangChain / CrewAI / AutoGen / AITuberKit）は sharpen-and-grow **B-3** が担う |
| §7 GitHub 成長戦略（店構え / レジストリ / SNS） | sharpen-and-grow **B-1 / B-2 / B-5** と `IMPROVEMENT_PLAN.md`（SNS・記事・シェアカード）が担う。オーナー手作業分は [`OWNER_ACTIONS.md`](./OWNER_ACTIONS.md) にチェックリスト化 |

---

## 0.1 この改訂版で変えた3つの前提

初版からの最大の変更点。ここだけ読めば方針は掴めます。

1. **North Star を1つに絞った** — 6つ並んでいた指標を「週次Export実行数」1本に統一。Star数やContributor数は結果指標に降格。
2. **Benchmarkを最優先に前倒し** — 「人格が崩れない」ことを証明する手段がHersona唯一の堀。Phase 3→Phase 1へ移動し、最小版から出す。
3. **Marketplaceを後ろに回した** — ユーザーとPackが育つ前に市場を作ると空き家になる。人格が溜まってから開く。

---

## 1. North Star Metric（唯一の指標）

> **週次 Export 実行数 — Weekly Persona Exports (WPE)**

作った人格が実際にLLMへ注入された回数。Hersonaの提供価値そのものの代理変数。

### なぜStar数ではないのか
Star・フォロワー・インストール数は「見た人の数」であって「使った人の数」ではない（vanity metric）。個人OSSでは、虚栄指標を追うと工数がSNS運用に溶ける。「実際に人格がExportされた」回数だけが、プロダクトが刺さっているかを正直に示す。

> **計測方法（2026-07-10 確定）**: パッケージ内テレメトリは採用しない。
> PyPI ダウンロード数（pypistats）・デモサイトの計測・レジストリ流入を
> 代理指標として週次で観測する（`IMPROVEMENT_PLAN.md` §2.2 と同じ枠組み）。

### 従属指標（North Starに連動して伸びるはずのもの）
以下は「目標」ではなく「WPEが健全に伸びていれば自然と付いてくる」健康診断値として観測する。

| 指標 | 12か月の目安 | 位置づけ |
|---|---|---|
| GitHub ⭐ | 3,000〜5,000 | 認知の代理値 |
| Contributors | 20〜30 | コミュニティ健全度 |
| Persona Packs | 100〜150 | 供給側の厚み |
| Framework Integrations | 5〜8 | 到達範囲 |
| Web Demo MAU | 3,000 | 入口の広さ |

> 初版の「⭐10,000 / Contributors 100 / Packs 500」は、個人運営の12か月としては非現実的。未達が続くとモチベーションを削るだけなので、到達可能で意味のある水準に修正した。背伸びした数字より、達成して積み上がる数字を選ぶ。

---

## 2. 差別化：唯一の技術的な堀は「一貫性の計測」

Hersonaの他OSSに対する優位は、機能の多さではなく**「人格が崩れないことを数値で証明できる」唯一のツールである**こと。

| OSS | 強み | Hersonaの立ち位置 |
|---|---|---|
| LangChain | 統合の豊富さ | 競合しない。Export先として乗る |
| CrewAI | 実例の豊富さ | 競合しない。人格レイヤとして差し込む |
| AutoGen | マルチエージェント | 各エージェントに人格を供給する側 |
| OpenAI Agents SDK | シンプルさ | Export先として乗る |

**結論**: フレームワークとは戦わない。全ての上に乗る「人格レイヤ」に徹する。そのために「人格の一貫性」という、他の誰も定量化していない軸を最初に押さえる。

---

## 3. Persona Benchmark 最小版（Phase 1で出す本命）

### 3.1 何を測るのか
> 同じペルソナ定義を複数のLLMに流したとき、**応答の「らしさ」がどれだけブレるか**を数値化する。

これができると、「Hersonaを使うと人格が安定する」という主張に**実データの裏付け**が付く。同時にHacker News記事「なぜ人格は崩れるのか」の材料にもなる。

### 3.2 最小スコープ

| 指標 | 定義 | 実装（2026-07-10 時点の対応） |
|---|---|---|
| **Style Retention** | 口調・一人称・語尾がどれだけ保たれるか | `hersona bench` の維持率（`hersona.core.intensity` の決定的採点: 語尾一致率 + 口癖密度）が既に担う |
| **Cross-model 比較** | モデルを変えたとき維持率がどれだけズレるか | `benchmarks/run_comparison.py`（A-2）で同一シナリオを複数モデルに流し、**決定的採点の維持率差**として計測（埋め込みコサイン距離は不採用 — §0 参照） |
| **Lock Resistance** | 人格上書き攻撃にどれだけ耐えるか | sharpen-and-grow A-1（攻撃シナリオ + lock resistance rate） |

残りの Stability / Token Cost / Latency のうち、**Token Cost は実装済み**（`bench --cost-only`、`docs/BENCHMARKS.md` に実測表）。Latency はログを取るだけなので run_comparison.py に記録欄を残す。

### 3.3 最小パイプライン

```
persona.yaml (attributes)
    │
    ▼
[1] 注入ブロック生成  … hersona blend / export（条件A）、手書き（条件B）、素（条件C）
    │
    ▼
[2] N ターン応答生成  … benchmarks/scenarios/ の固定質問セットを各モデルに投げる
    │                （benchmarks/run_comparison.py — anthropic / openai / gemini / ollama）
    ▼
[3] スコアリング      … hersona bench（決定的・再現可能）
    ├─ 維持率（Style Retention）
    ├─ 減衰曲線（decay）
    └─ lock resistance rate（攻撃シナリオ時）
    │
    ▼
comparison.md + comparison.json（表とスコア、日付・モデル・再現コマンド付き）
```

### 3.4 出力イメージ（README/Hacker Newsに貼れる形）

```
Persona: tsundere + keigo (weight: moderate)
Scenario: long_form_topic_switch_ja (12 turns)  |  Models: 2

                      model-a   model-b
Maintenance (hersona)   0.83      0.75
Maintenance (baseline)  0.42      0.33
Maintenance (none)      0.08      0.00
Lock resistance         0.90      0.70
```

この一枚が「Hersonaは人格の崩れを可視化できる」という主張の全証拠になる。**機能ではなく、この表を最初に世に出す。**

### 3.5 個人マシンでの現実的な運用
- 応答生成はAPI（またはローカル ollama）を叩くだけなのでメモリ負荷は低い。
- 採点は決定的（LLM・埋め込み不要）なのでゼロコストで再実行できる。
- CI化はPhase 3以降。まずは手元で1コマンド実行できれば十分。

---

## 4. 改訂ロードマップ

| Phase | 期間 | 主眼 | やること | 完了の判定 |
|---|---|---|---|---|
| **1** | 0〜2か月 | 堀とDX | README刷新 / 30秒Quick Start / GIF / **Benchmark最小版**（A-1 + A-2） / Export先の明示 | Benchmark表を1つ公開・WPE代理指標の観測開始 |
| **2** | 2〜4か月 | 到達範囲 | **Integrations 実例に集中**（B-3: LangChain / CrewAI / AutoGen / AITuberKit）/ Examples 10本 | 3フレームワークで動く実例 |
| **3** | 4〜6か月 | 自動化 | BenchmarkのCI化 / 指標追加（zh/ko = A-3 等） / Export拡充 | PR毎に人格スコアが自動表示 |
| **4** | 6〜8か月 | 市場 | Persona Gallery（軽量、B-4）/ タグ・検索 / 評価 | Pack投稿と閲覧の循環が回る |
| **5** | 8〜12か月 | 進化・生態系 | Personality Evolution / VSCode・Cursor拡張 / MCP Registry 拡充 | 履歴から人格を推薦・改善 |

### Phase 1 詳細（最初の60日）
README冒頭「3スクロール以内」に置くもの:
1. 一行で「何ができるか」
2. デモ（人格を定義→Exportまで30秒）
3. Quick Start（コピペで動く5行）
4. **Benchmark表**（Before/Afterではなく、実測のブレ数値）
5. Export先バッジ（AGENTS.md / CLAUDE.md / Cursor Rules / GEMINI.md）

---

## 5. Integrations：展開先は「今使われる」で選ぶ

初版のExport 10種は個人工数を溶かす。いま最も使われるエージェント基盤に絞る。

| 優先 | Export先 | 状態 |
|---|---|---|
| 1 | **`AGENTS.md`** | 実装済み（`persistent --target codex|agents`） |
| 2 | **`CLAUDE.md`** | 実装済み（`persistent --target claude`） |
| 3 | **Cursor Rules** | 実装済み（`persistent --target cursor` = `.cursorrules`。新形式 `.cursor/rules/*.mdc` は要望が来たら Backlog から昇格） |
| 4 | **`GEMINI.md`** | 実装済み（ボーナス） |

残りの JSON Schema / XML / REST API などは **Backlog（未着手プール）** に置き、要望が来てから着手。「作れる」ではなく「今使われる」で選ぶ。

---

## 6. Backlog（やることリストではなく、選択肢のプール）

> ⚠ これは実装予定リストではない。**同時に走らせられるのは常時1〜2個**。Phaseの実装項目と混同しないため、意図的に分離している。要望・自分の必要・PRのいずれかが来た項目だけをPhaseへ昇格させる。

<details>
<summary>Export（クリックで展開）</summary>

Cursor `.mdc` 形式 / JSON Schema / XML / PromptPack / REST API / GraphQL / Web Components
</details>

<details>
<summary>Benchmark</summary>

埋め込みコサイン距離による Cross-model Drift（extras 隔離が条件） / Stability / Latency 集計 / CI 化
</details>

<details>
<summary>Persona管理</summary>

Import / Merge / History / Version / Tags / Search / Favorites / Sharing / Templates
（Diff / Save / Presets は実装済み）
</details>

<details>
<summary>Community</summary>

Rating / Comments / Weekly Ranking / Trending / Verified Creator / Featured / Collections / Following / Badges / Challenges
</details>

<details>
<summary>AI支援</summary>

Prompt Optimizer / Personality Repair / Conflict Detector / Persona Simulator / Multi-turn Test / Regression Test / Blend Suggestion / Auto Benchmark / Prompt Compression

（Tone Analyzer 系は 2026-07-11 にオーナー要望で昇格 →
[`IMPROVEMENT_PLAN_2026-07-11_humanize.md`](./IMPROVEMENT_PLAN_2026-07-11_humanize.md):
AI 臭の決定的測定 (naturalness スコア) + `--humanize` ディレクティブ + before/after 実測）
</details>

<details>
<summary>Developer</summary>

TypeScript SDK / REST API / GraphQL / Docker / GitHub Action / CI Integration / CLI Plugins / Web Components
（Python SDK = `hersona.core` 公開 API / MCP サーバーは実装済み）
</details>

---

## 7. GitHub成長戦略

### Issue戦略（Good First Issue）
新規貢献者が最初に触れる場所。難易度の低い順に用意:
- ドキュメント修正・翻訳
- Persona Pack 追加（1ファイル）
- Example 追加
- Export先の追加（テンプレート化しておく）

### SNS戦略（週1本・使い回し前提）
毎回ゼロから作らない。1つの素材を複数媒体に展開:
- 新Persona / Blend紹介
- **Benchmark比較**（数値付きが最も拡散する）
- Tips・落とし穴
- Community作品の紹介

### 大きな山（タイミングを合わせる）
- **Product Hunt**: v2公開日にローンチ
- **Hacker News**: 技術記事3本を弾に
  - なぜ人格は崩れるのか（Benchmark実データ）
  - Persona Benchmark とは何か
  - Prompt Engineering を超える人格設計

> HNは「主張＋実データ」でしか刺さらない。だからBenchmarkを先に作る順番になっている。

---

## 8. 将来像

```
Developer
    │
    ▼
Hersona ── 人格を定義・計測・共有・移植
    │
    ├── OpenAI
    ├── Claude
    ├── Gemini
    ├── Qwen
    ├── DeepSeek
    ├── Local LLM
    └── MCP
```

人格はHersonaが管理し、モデルは自由に差し替えられる世界。

---

## 9. ミッション / キャッチコピー

**Mission: Build once. Keep personality everywhere.**

メイン: `Build once. Keep personality everywhere.`
サブ: `Composable personalities for every LLM.`

> 抽象名詞句（"Personality Infrastructure…"）より、動詞で始まる命令形の方が記憶に残り、READMEトップで機能する。二段構成で固定する。

---

## 10. 最重要提案（変わらぬ核）

「人格を**作る**OSS」ではなく、
**人格を管理・評価・共有・移植するOSS** へ。

その中で、**「評価（Benchmark）」だけは他の誰もやっていない**。ここを最初に取ることで、Hersonaは単なるプロンプト集ではなく、AIエージェント時代の人格インフラとして独自のポジションを確立する。

**最初の一手は、機能追加ではなく「人格の崩れを数値で見せる一枚の表」。**

---

## 改訂履歴

- 2026-07-11: Backlog「AI支援」から Tone Analyzer 系をオーナー要望で昇格し、
  [`IMPROVEMENT_PLAN_2026-07-11_humanize.md`](./IMPROVEMENT_PLAN_2026-07-11_humanize.md)
  （AI 臭の抑制と測定）として計画化。
- 2026-07-10: リポジトリへ取り込み。§0（実態突き合わせ）を追加し、実装済み項目
  （Export 4形式 / bench / token cost）と決定事項（埋め込み Drift 見送り /
  テレメトリ不採用）を反映。実行計画は sharpen-and-grow に委譲。
