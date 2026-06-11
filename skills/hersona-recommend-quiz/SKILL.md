---
name: hersona-recommend-quiz
description: "Use when the user wants to take the hersona diagnostic quiz interactively (e.g. 'hersona で recommend して', '診断クイズやりたい', 'キャラ診断して', '属性推薦して'). Walks the user through all 9 questions in hersona/data/quiz/recommend_quiz.yaml, collects answer indices, builds the --answers string, runs `hersona recommend --explain --json`, and renders a Markdown-friendly result (blend / rationale / alternatives / summary / weight_suggestion). Also exposes scripts/run_quiz.py for non-interactive / TTY-less contexts (cron, batch, automated test). Trigger on any request to run the recommend flow as a user-facing experience, not as engine development (engine work uses hersona-recommend-engine)."
version: 1.0.0
author: Hermes Agent + hersona project
license: MIT
metadata:
  hermes:
    tags: [hersona, recommend, quiz, interactive, markdown, tty-less, v1.2]
    related_skills: [hersona, hersona-recommend-engine, hersona-attribute-development, hermes-agent-skill-authoring]
---

# hersona-recommend-quiz (v1.0.0)

## Overview

hersona 診断クイズを **ユーザーとして体験する側** のスキル。`hersona-recommend-engine`（engine 開発側）の対となる skill。

やることは単純:

1. `hersona/data/quiz/recommend_quiz.yaml` から 9 問を読む
2. 1 問ずつ番号付き選択肢を提示し、番号を集める
3. `key=index` 形式の文字列を組み立てて `hersona recommend --answers "..." --explain --json` を実行
4. 結果 JSON を **Markdown 整形**（Telegram / Discord / ターミナル全対応）で返す

LLM 主軸: 通常のチャットセッションでは、エージェントが SKILL.md を読んで Q1〜Q9 を表示し、ユーザーの番号を `--answers` に変換して CLI を叩く。

ヘルパー同梱: `scripts/run_quiz.py` を同梱し、TTY がない環境（cron / バッチ / CI / 自動テスト）ではこっちで stdin 経由に 9 問進行 → `--answers` 生成 → 結果整形まで一括実行できる。

## When to Use

- 「hersona で recommend して」「診断クイズやりたい」「キャラ診断して」「属性推薦して」など、ユーザーがクイズを **プレイしたい** とき
- 結果（採用された属性 blend / 根拠 / 代替案 / サマリ / 推奨強度）を **Markdown で見やすく** 受け取りたいとき
- TTY がない自動化経路（cron / テスト）で recommend を使いたいとき → `scripts/run_quiz.py`

**Don't use for:**

- クイズ YAML / WeightMagnitude / 閾値 / テストの **追加・編集**（→ `hersona-recommend-engine`）
- 新しい属性 YAML の **追加**（→ `hersona-attribute-development`）
- ペルソナをセッションにアタッチする作業（→ `hersona` の `attach` / `recommend` セクション）
- hersona リポジトリの戦略的・複数 PR 横断の作業（→ `hersona-project-operations`）

## The 9 Questions (固定 ID)

クイズの本体は `hersona/data/quiz/recommend_quiz.yaml` にあり、9 問。各質問は次の ID で固定（= CLI `--answers` のキー）。ID を変えるとユーザーの既存スクリプトが壊れるので SKILL.md / YAML をまたいで常に同期すること。

| ID | 軸 | 質問 |
|---|---|---|
| `distance` | personality | 相手との距離感は？ |
| `emotion` | personality | 感情の出し方は？ |
| `speech` | speech | どんな話し方が好み？ |
| `role` | archetype | 物語での立ち位置は？ |
| `hobby` | hobby | 趣味・ライフスタイルで近いのは？ |
| `appearance` | visual | 外見・雰囲気で近いのは？ |
| `lifestyle` | lifestyle | 日常の過ごし方は？ |
| `interaction` | interaction | 人と接するときは？ |
| `cultural` | cultural | 文化的・知的なバックグラウンドは？ |

選択肢の最新版は必ず YAML から読む（= 同梱禁止、コードと YAML の二重管理を避ける）。LLM フローの冒頭で `read_file` で YAML を読み込み、表示用テキストを生成する。

> i18n (Phase 3〜): `prompt` / `label` は **BASE=en**。日本語は各質問・各選択肢の
> `i18n: {ja: {prompt|label: "..."}}` に入る（上表は日本語版 = `i18n.ja.prompt`）。
> 表示言語に合わせて `i18n.<lang>` を優先し、無ければ BASE(en) にフォールバックして出すこと。

## LLM Flow (manual / interactive)

### Step 1: YAML 読み込み

```
read_file path=hersona/data/quiz/recommend_quiz.yaml
```

これで 9 問の ID / prompt / options / weights を取得する。LLM は表示用テキストを組み立てる（= 質問文をそのまま出す + 選択肢番号 + 該当属性を hint 表示）。

### Step 2: 1 問目から順に提示

各 Q で次のフォーマットを使う:

```
Q<n>. <prompt>

1. <option[0].label>（<option[0].weights のキー>）
2. <option[1].label>（<option[1].weights のキー>）
...
n. <option[n].label>（<option[n].weights のキー>）
```

**全選択肢を必ず表示する**（YAML の順序を維持）。`distance` は 4、`emotion` は 8、`speech` は 14、`role` は 6、`hobby` は 6、`appearance` は 5、`lifestyle` は 5、`interaction` は 5、`cultural` は 5 個。

**途中で「キャンセル」「やめ」「stop」と書かれたら即終了。** 部分保存はしない（全 9 問揃ってから CLI を叩く前提）。

### Step 3: 回答を蓄積

内部状態として `answers: dict[str, int] = {}` を持つ。`1` 始まりなので内部表現は **0 始まりに直す**（CLI も 0 始まり）:

```python
answers = {qid: idx - 1 for qid, idx in user_responses.items()}
```

例: `distance=1,emotion=2,speech=3,role=0,hobby=4,appearance=2,lifestyle=1,interaction=3,cultural=4`

### Step 4: CLI 実行

全 9 問揃ったら組み立てる:

```bash
hersona recommend \
  --answers "distance=1,emotion=2,speech=3,role=0,hobby=4,appearance=2,lifestyle=1,interaction=3,cultural=4" \
  --explain --json
```

cwd は `~/projects/hersona`（hersona CLI はインストール済み前提。`which hersona` で確認可）。

### Step 5: 結果整形（Markdown）

JSON のうち **ユーザー向けに必要なキーだけ** を抜き出して整形する。`--json` キーは契約（`hersona-recommend-engine` Pitfall 参照）:

```markdown
## 推薦結果

**採用された属性 blend**:
- <blend[i]>（スコア <scores[i]>）

**各属性の根拠（rationale）**:
- <adopted> を選んだ理由:
  - 質問「<prompt>」→「<option.label>」（該当: <keys>）
  - ...

**落選した属性の代替案（alternatives）**:
- <dropped> の代わりに → <alternative>（スコア <score>）
- ...

**1 行サマリ**:
> <summary>

**推奨強度**: <weight_suggestion>（= none / mild / moderate / strong のいずれか）
```

`special_case` として `blend` が空配列のときは「マッチする属性が見つかりませんでした。回答を変えて再挑戦してください」と返す。

### Step 6: --apply オプション提案

整形結果を出した直後に、**追加で** 次を提示する:

```
この blend をセッションにアタッチしますか？
- はい（hersona recommend --apply で注入ブロックも出す）
- いいえ（診断だけして終わる）
```

「はい」なら `--answers "..." --apply` を再実行して注入ブロックを提示。

## Helper Script: `scripts/run_quiz.py`

TTY がない経路（cron / batch / CI / 自動テスト）用。stdin 経由で `qid=index` を 1 行ずつ受け取って `--answers` を組み立て、CLI を叩いて JSON を整形出力する。

### Usage

```bash
# 1) 引数モード（事前回答がある場合）
python3 scripts/run_quiz.py \
  --answers "distance=1,emotion=2,speech=3,role=0,hobby=4,appearance=2,lifestyle=1,interaction=3,cultural=4"

# 2) stdin モード（行ごとに qid=index）
echo "distance=1"   | python3 scripts/run_quiz.py
echo "emotion=2"    | python3 scripts/run_quiz.py
echo "speech=3"     | python3 scripts/run_quiz.py
echo "role=0"       | python3 scripts/run_quiz.py
echo "hobby=4"      | python3 scripts/run_quiz.py
echo "appearance=2" | python3 scripts/run_quiz.py
echo "lifestyle=1"  | python3 scripts/run_quiz.py
echo "interaction=3"| python3 scripts/run_quiz.py
echo "cultural=4"   | python3 scripts/run_quiz.py
echo ""             | python3 scripts/run_quiz.py   # 空行で finish

# 3) --apply 付きで注入ブロックも出す
python3 scripts/run_quiz.py --answers "distance=1,emotion=2,..." --apply

# 4) --json で raw JSON
python3 scripts/run_quiz.py --answers "..." --json
```

### 動作

1. `hersona/data/quiz/recommend_quiz.yaml` を読み込み 9 問 ID を取得
2. 引数または stdin から `qid=index` を受信
3. **9 個揃ったら** `hersona recommend --answers "..." --explain --json` を `subprocess.run` で実行
4. JSON を stdout に **Markdown 整形**して出力（終了コード 0）
5. 9 個揃う前に EOF → 終了コード 2 + stderr に「不足 ID 一覧」

### 検証

```bash
# 正常系
python3 scripts/run_quiz.py --answers "distance=1,emotion=2,speech=3,role=0,hobby=4,appearance=2,lifestyle=1,interaction=3,cultural=4" | head -30

# --json で構造確認
python3 scripts/run_quiz.py --answers "distance=1,emotion=2,speech=3,role=0,hobby=4,appearance=2,lifestyle=1,interaction=3,cultural=4" --json | python3 -m json.tool | head -40
```

## Common Pitfalls

### Pitfall Q1: YAML を読まずに選択肢をハードコードしない

YAML の選択肢が変わるたびに追従が要る。「Q3 には 14 個あります」のように件数を動的に数える。LLM フローの Step 1 で必ず `read_file` する。

### Pitfall Q2: 1 始まりの番号を 0 始まりに直すのを忘れる

ユーザーは「1, 2, 3...」で答えるが、CLI は 0 始まり。`idx - 1` を必ず噛ませる。

### Pitfall Q3: 全 9 問揃う前に CLI を叩く

`--answers` に欠損があると hersona CLI はエラー。LLM は「あと n 問」と表示し、揃ってから初めて実行する。

### Pitfall Q4: 採用属性が空 (`blend: []`) のときに rationale 表示で KeyError

JSON 整形時に `blend` が空配列だと rationale も空。Pitfall Q5 の special_case 処理で先に分岐する。

### Pitfall Q5: `summary` が `null` のケース

`Recommendation.summary()` は lazy import 失敗などで稀に `None` を返すことがある。`null` なら「（サマリ生成に失敗）」とフォールバック。

### Pitfall Q6: alternatives のタプル形式

`--json` では `alternatives: list[{dropped, alternative, score}]` で降ってくる（オブジェクト形式）。LLM 整形時に `.get("dropped", "?")` / `.get("alternative", "?")` / `.get("score", 0.0)` で安全アクセス。

### Pitfall Q7: 作業ディレクトリ

`hersona` CLI は `~/projects/hersona` から叩く前提。`workdir` を明示しないと YAML が見つからず `FileNotFoundError` になる。

```python
# scripts/run_quiz.py 内部
subprocess.run(
    ["hersona", "recommend", "--answers", answers_str, "--explain", "--json"],
    cwd=PROJECT_ROOT,   # = pathlib.Path(__file__).resolve().parents[1]
    check=True, capture_output=True, text=True,
)
```

### Pitfall Q8: `python -m hersona` 不可（hersona-recommend-engine Pitfall 19 参照）

`hersona` コマンドを使う。`python -m hersona` は失敗する。

## Verification Checklist

- [ ] YAML を `read_file` で読み込み、9 問全てから選択肢を動的に組み立てた
- [ ] ユーザー回答は 1 始まり、内部表現は 0 始まりに変換した
- [ ] 全 9 問揃ってから CLI を実行した（途中で叩いていない）
- [ ] `cwd` を `~/projects/hersona` に設定した
- [ ] `hersona recommend --answers "..." --explain --json` の `--json` キーは契約通り保持
- [ ] Markdown 整形は **ラベル + 値** の箇条書き（Telegram 表崩れ回避）
- [ ] `blend` 空 / `summary=null` / `alternatives` 空 をフォールバック処理した
- [ ] --apply オプションを最後に確認した
- [ ] LLM フロー失敗時の代替としてヘルパースクリプトの動作も確認した
- [ ] ヘルパースクリプトの stdin / 引数 / --apply / --json の 4 経路すべて検証した

## Cross-Reference

- **クイズ YAML / WeightMagnitude / 閾値 / テスト** → `hersona-recommend-engine`（engine 開発側、v1.2.0 契約保持）
- **属性 YAML 追加** → `hersona-attribute-development`
- **セッションへのペルソナ attach** → `hersona`（`/hersona personality/tsundere` 等）
- **hersona 戦略・複数 PR 横断** → `hersona-project-operations`
- **SKILL.md 記法・frontmatter** → `hermes-agent-skill-authoring`
