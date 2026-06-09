# hersona 実装指示書（エージェント向けハンドオフ）

> このドキュメントは、文脈を持たないエージェント／開発者が **次に何を実装すべきか** を
> 単独で理解して着手できるようにするための指示書である。プロジェクト概要・規約・
> 現状・次タスクの具体手順・検証コマンドを自己完結的にまとめる。
>
> 設計合意の記録は [ROADMAP.md](./../ROADMAP.md)、属性追加規約は
> [CONTRIBUTING.md](./../CONTRIBUTING.md) を参照。

---

## 1. プロジェクト概要

hersona は、アニメ・ゲーム風キャラクターの **口調・性格・役割** を「作品に依存しない
汎用属性テンプレート」の組合せで構築するためのツール群。v1.0 で個別キャラ依存データ
(`data/`) を完全廃止し、`attributes/<category>/<name>.yaml` の汎用属性のみを提供する。

- **属性カテゴリ**: `personality` / `speech` / `archetype` の 3 種
- **属性数**: 52（personality 17 / speech 16 / archetype 9 / visual 5 / hobby 5）※変動するので下記「現状」で確認
- **大原則**: ローカル＝自由 / 公開・共有＝汎用属性のみ

### アーキテクチャ: core 共有

ロジックは `hersona/core/` に集約し、各インターフェース（Hermes スキル / CLI）は
薄い殻として同じ core を呼ぶ。

```
hersona/core/        # ロジック本体
  ├─ compatibility.py  # 相性マトリクス (conflict 対称閉包 / compatible 双方向和)
  ├─ authoring.py      # ローカル属性オーサリング (build/override/save + 検証ゲート + 共有ガード)
  ├─ recommend.py      # 診断クイズ → 適合度スコア → conflict 解決済み推薦ブレンド
  ├─ attach.py         # 属性ロード + ブレンド注入ブロック合成 (公開 + user 名前空間)
  └─ weight.py         # 強度 (none/mild/moderate/strong) ダイヤル
hersona/cli/         # argparse CLI (`hersona` / `python -m hersona.cli`)
  └─ app.py            # list / show / matrix / blend / recommend / create
attributes/          # 公開・汎用属性 (CC0)。SSOT は scripts/_oneoff/gen_v1_attributes.py
schema/attribute.schema.json   # 属性 YAML スキーマ
scripts/validate.py            # スキーマ + 相性整合の検証 CLI
tests/                         # pytest (test_<module>.py)
```

---

## 2. 必ず守る規約（重要）

1. **属性 YAML を手編集しない。** `attributes/**/*.yaml` は
   `scripts/_oneoff/gen_v1_attributes.py` 内の `ATTRIBUTES` リストを **Single Source of
   Truth** として生成される。属性の追加・変更は generator を編集して再生成する。
   - 再生成は既存ファイルと **byte 一致** で再現される（差分が出たら何か壊れている）。
2. **属性数を変える時は全カウント参照を更新する。** 後述「属性追加チェックリスト」参照。
3. **ブランチ運用**: `claude/hersona-<topic>` を切って作業 → `main` へ squash PR。
   1 PR = 1 論点（属性追加は 1 PR = 1 属性が基本）。
4. **検証ゲート 3 種を必ず通す**（コミット前）:
   ```bash
   python -m pytest -q              # 全テスト
   ruff check hersona/ tests/        # lint (新規・変更ファイル)
   python scripts/validate.py        # 属性スキーマ + 相性整合 (exit 0)
   ```
   - 注意: `tests/test_attributes.py` に既存の ruff UP015 指摘が残っているが、これは
     本作業外の既存事象。新規・変更ファイルがクリーンであればよい。
5. **DISCLAIMER 遵守**: 固有名詞・特定作品名を attributes / examples に入れない。
   ユーザー作成属性のローカル保存は自由だが、共有時は `authoring.assert_shareable()` で
   弾く設計。

### 環境セットアップ

```bash
pip install -e ".[dev]"   # pyyaml / jsonschema / pytest / ruff など
```

---

## 3. 現状（2026-06 時点）

| ワークストリーム | 状態 | 主モジュール |
|---|---|---|
| ① 相性マトリクス | ✅ 実装済み | `core/compatibility.py` |
| ③ ローカルオーサリング | ✅ 実装済み | `core/authoring.py` |
| ② 評価・推薦 | ✅ 実装済み | `core/recommend.py` |
| CLI 殻 | ✅ 実装済み | `cli/app.py` |
| attach/blend | ✅ 実装済み | `core/attach.py` |
| weight 較正 | ✅ 実装済み | `core/weight.py` |
| SKILL.md v3.1.0 | ✅ 反映済み | `skills/hersona/SKILL.md` |
| **強度指標 (intensity)** | ✅ **実装済み** | `core/intensity.py` |
| 本格 TUI (textual) | ❌ 未着手（任意） | — |
| recommend (b) サンプル評価 / (c) 会話解析 | ❌ 未着手（後段） | — |

テストは現状 154 件パス。

---

## 4. 次にやること: 強度指標（intensity metric）の実装 ★最優先

weight は現状「指示＋口癖露出量の調整」までで、**出力が実際にその強度になったかを
測っていない**（開ループ）。出力テキストを決定的に採点する強度指標を入れて閉ループ化する。

### 4.1 確定仕様（変更不可・対話で合意済み）

| 論点 | 決定 |
|---|---|
| 測定方式 | **表層のみ・決定的**（regex / 文字列、LLM 不要。再現性優先、gaming 可は許容） |
| 未達 (under) 時 | **警告のみ**（スコア表示 + 未達明示。自動リトライはしない） |
| マーカー無し属性 | **speech 属性が無いブレンドは測定 skip**（語尾軸が無いと測れない） |
| 表示場所 | **専用コマンド `hersona measure`（オンデマンド）**。毎ターンバッジは付けない |
| 指標の軸 | **語尾一致率 + 口癖密度の 2 軸のみ**。一人称は schema に専用フィールドが無いため除外 |

### 4.2 実装ステップ

#### Step 1: `hersona/core/intensity.py` を新規作成

```python
from dataclasses import dataclass
from hersona.core.weight import WeightLevel, coerce_level

@dataclass
class IntensityReport:
    score: float              # 0-100
    endings_rate: float       # 0-1: 文末が sentence_endings に一致した割合
    catchphrase_hits: int     # catchphrases 出現回数
    sentence_count: int
    band: tuple[int, int]     # 期待バンド (lo, hi)
    status: str               # "pass" / "under" / "over"

def measure_intensity(text: str, attributes: list[dict]) -> IntensityReport | None:
    """speech 属性を含むブレンドの出力テキストを採点。speech が無ければ None (skip)。

    - sentence_endings / catchphrases は attributes 各 dict の同名フィールドを和集合で集約
    - speech 属性 (attribute_category == "speech") が 1 つも無ければ None
    - score = 100 * (0.6 * endings_rate + 0.4 * catchphrase_density)
      - catchphrase_density = min(1.0, catchphrase_hits / max(1, sentence_count))
    - band / status は verify() 側で埋める or measure 内で level を受けて埋める
    """

def expected_band(level: str | WeightLevel) -> tuple[int, int]:
    """none (0,20) / mild (20,45) / moderate (45,70) / strong (70,100)。"""

def verify(text: str, attributes: list[dict], level: str | WeightLevel) -> IntensityReport | None:
    """measure_intensity + expected_band を突き合わせ status を決める。
    score < lo → "under" / score > hi → "over" / それ以外 → "pass"。
    speech 無しなら None。"""
```

**実装上の既定（実装者が決めてよい細部、推奨値を記載）:**
- 文分割: `。！？!?\n` で分割し、空要素を除く。
- 文末一致判定: 各文の末尾（句読点・記号を strip 後）が、speech 属性の
  `sentence_endings` のいずれかで終わるか。語尾は「〜どす」のような波ダッシュ接頭を
  含むので、比較時は先頭の `〜` / `~` を除去して `text.rstrip(句読点).endswith(ending)` で判定。
- 口癖カウント: 各 catchphrase の出現回数を `text.count()` で合算。
- catchphrase が空（speech にも無い）の場合は density=0 として score は語尾のみで決まる。

#### Step 2: `hersona/core/__init__.py` にエクスポート追加

`IntensityReport` / `measure_intensity` / `expected_band` / `verify` を import & `__all__` に追加。

#### Step 3: CLI に `measure` サブコマンドを追加（`hersona/cli/app.py`）

```
hersona measure <name> [<name>...] --weight <level> --input <file>
hersona measure <name> [<name>...] --weight <level> --text "応答テキスト"
```

- `_build_parser()` に `p_measure` を追加（`names` nargs="+", `--weight`
  choices=`_WEIGHT_CHOICES` 既定 moderate, `--input` ファイルパス, `--text` インライン）。
- ハンドラ `_cmd_measure`:
  - `names` を `load_attribute()` で dict 群に解決（`attach.load_attribute` 流用）。
  - text を `--input`（読み込み）か `--text` から取得。両方無ければ ValueError。
  - `verify(text, attrs, weight)` を呼ぶ。`None` なら「speech 属性が無いため強度測定を skip」
    と表示して return 0。
  - レポートを表示。`status == "under"` のとき **警告を stderr に出す**（exit code は 0 のまま）。

表示例:
```
強度 76/100 (語尾一致 80% / 口癖 3件)  band=strong(70-100)  status=pass ✓
```

#### Step 4: テスト `tests/test_intensity.py` を新規作成

最低限カバーすべきケース:
- `measure_intensity` が **speech 属性無しのブレンド（例: ["tsundere"]）で None** を返す
  （注: tsundere は personality。speech が無いので skip）。
- speech 属性ありで、語尾を多用したテキストの `endings_rate` が高い。
- 作為テキストで `score` が strong バンドに入る / 平淡テキストで under になる。
- `verify` の status が `pass` / `under` / `over` を正しく返す。
- `expected_band` の各レベルの境界。
- CLI: `main(["measure", "kyoto_ben", "--weight", "strong", "--input", str(tmp)])` が 0 を返し、
  期待文言を stdout に出す。speech 無しブレンドで skip メッセージ。
- 実データ参照テストは `public_root` / `user_root` を渡せるよう `load_attribute` の
  引数を活用（`tests/test_attach.py` のパターンに倣う。`user_root=Path("/nonexistent")`）。

> CLI テストは `tests/test_cli.py` の `_isolate_user_dir` フィクスチャ（`HERSONA_USER_DIR` を
> tmp に向ける）と `capsys` のパターンを踏襲すること。

#### Step 5: ドキュメント更新

- `CHANGELOG.md` の `## [Unreleased]` に Added エントリ。
- `ROADMAP.md` の「## 強度指標（intensity metric）」を ★計画 → ★実装済みに更新し
  チェックを入れる（PR #9 でこのセクションが追加されている。未マージなら順序に注意）。
- `README.md` の CLI セクションに `hersona measure` を追記。
- `skills/hersona/SKILL.md` に `/hersona measure`（または check との関係）を追記。
  必要なら version 3.1.0 → 3.2.0。

### 4.3 完了の定義（DoD） — intensity metric（実装済み）

- [x] `hersona/core/intensity.py` 実装、`core/__init__.py` でエクスポート
- [x] `hersona measure` サブコマンド動作（`--input` / `--text`、speech 無しで skip、under で警告）
- [x] `tests/test_intensity.py` 26 件 追加、`python -m pytest -q` 180 件全件パス
- [x] `ruff check hersona/ tests/test_intensity.py` クリーン
- [x] `python scripts/validate.py` exit 0
- [x] CHANGELOG / ROADMAP / README / SKILL.md 更新
- [ ] `claude/hersona-intensity` ブランチで PR 作成 ← 進行中

### 4.4 次の次タスク案（backlog へ移動済み）

下記は §5 に集約（PR #10 §5 を参照）。

---

## 5. その他の未着手バックログ（優先度順・参考）

1. **recommend `--save`（ブレンドのプリセット保存）** — 診断結果のブレンドを再利用可能な
   資産として保存。属性は単一カテゴリなので「ブレンド = 属性名リスト」を別形式
   （プリセット）で持つ設計が要る。`authoring` と接続。
2. **recommend (b) サンプル応答評価入力** — 「どの応答が好み？」で重みを推定する入力方式。
   `recommend.py` に評価入力経路を追加。
3. **本格 TUI（textual）** — 現状 argparse CLI。対話 UI を厚くする場合。core は再利用。
4. **さらなる speech 属性** — 方言・語尾・一人称の軸（例: 博多弁、軍隊口調 等）。
   **1 PR = 1 属性**で generator 経由。下記チェックリスト必須。
5. **recommend (c) 過去会話解析** — 重いので後段。

---

## 6. 属性追加チェックリスト（speech/personality/archetype を 1 つ足す時）

属性数が変わると **複数箇所のカウント参照** を同時更新する必要がある。漏れるとテストが落ちる。

1. `scripts/_oneoff/gen_v1_attributes.py` の `ATTRIBUTES` に新エントリを追加
   （speech なら `sentence_endings` / `catchphrases` / `speech_style` / `second_person` /
   `tone` を入れると強度指標・blend で効く）。
2. 同ファイルの `_check_category_counts()` の `expected` 該当カテゴリ数を +1。
3. 同ファイル冒頭 docstring の属性数・カテゴリ別件数・属性名リストを更新。
4. 再生成: `python scripts/_oneoff/gen_v1_attributes.py`（既存は byte 一致のはず）。
5. カウント参照を更新（grep で `<旧総数>` / `speech.*<旧数>` を洗う）:
   - `tests/test_attributes.py`（docstring / 関数名 / `== N` / カテゴリ別 assert）
   - `tests/test_compatibility.py`（`== N`）
   - `tests/test_attach.py`（`available_attributes` の `== N`）
   - `tests/test_cli.py`（`"N 件"`）
   - `README.md`（データ形式の「(N 種)」/「計 N 種」/「N 属性一覧」表 / 再生成・検証コメント）
   - `skills/hersona/SKILL.md`（Overview / When to Use / list 例の件数とツリー / 検証チェックリスト / Reference Files）
6. conflict を宣言した場合、`validate.py` は対称閉包するので片側宣言で OK
   （非対称は警告表示されるが exit 0）。
7. recommend クイズを編集する場合は `hersona/data/quiz/recommend_quiz.yaml` を
   末尾追加で更新する (Python コードから分離済み)。既存 option index を
   ずらさないこと (テストの `speech=4` 等が壊れる)。新 WeightMagnitude 名前
   (`STRONG` / `MODERATE` / `MILD` / `WEAK` / `NONE`) と数値リテラルの混在 OK。

---

## 7. 主要コマンド早見表

```bash
# セットアップ
pip install -e ".[dev]"

# 検証ゲート
python -m pytest -q
ruff check hersona/ tests/
python scripts/validate.py

# 属性再生成 (SSOT)
python scripts/_oneoff/gen_v1_attributes.py [--dry-run]

# CLI 動作確認
python -m hersona.cli list
python -m hersona.cli show tsundere
python -m hersona.cli blend tsundere keigo --weight strong
python -m hersona.cli recommend --answers "distance=1,speech=0,role=1" --apply
python -m hersona.cli matrix --json

# 相性マトリクスのダンプ
python -m hersona.core.compatibility --json
```

---

## 8. ハマりどころ（このプロジェクト特有）

- **generator が SSOT**: 属性 YAML を直接書き換えても次の再生成で消える。必ず generator を直す。
- **DEFAULT_QUIZ は YAML 外部化済** (v1.2.0): `hersona/data/quiz/recommend_quiz.yaml`。
  拡張は YAML 末尾追加で OK。Python コード修正不要。weight は `STRONG/MODERATE/MILD/WEAK` 名前
  または数値リテラル (例: 1.5) で記述可。
- **weight の conflict**: 例えば `genki` と `kyoto_ben` / `washi` は conflict 宣言済み。
  ハイテンション × はんなり/老成は両立しない設計。blend に両方入れると警告が出る。
- **conflict は対称閉包**: 片側 YAML にしか書いてなくても core が両方向に効かせる。
  `validate.py` は非対称を警告するが落とさない（SSOT 直接編集を避ける方針のため）。
- **強度指標は「形」しか測れない**: 語尾・口癖の表層プロキシ。意味的な濃さ（felt intensity）は
  測れず gaming 可能。これは確定済みの割り切りであり「仕様」。
