# hersona ROADMAP

> v1.0 (attributes-only) 以降の開発方針。本ドキュメントは設計合意の記録であり、
> 実装の進捗に合わせて更新する。

## 0. 全体方針

| 項目 | 確定内容 |
|---|---|
| **アプリ形態** | 対話 CLI/TUI（ローカル完結）。ホスト型 Web は設計上の余地として残すのみ |
| **優先順位** | ① 相性マトリクス → ③ オーサリング基盤 → ② 評価・推薦 → ① speech/weight 拡張 |
| **大原則** | **ローカル＝自由 / 公開・共有＝汎用属性のみ** |
| **土台** | 既存 Python (pyproject/uv) + `schema/` + `scripts/validate.py` + `skills/hersona/` の延長 |

### 設計の核: core 共有

ロジックを `hersona/core/` に集約し、各インターフェースは薄い殻にする。
これにより Hermes スキル・CLI/TUI・将来の Web 殻が同一ロジックを共有する。

```
hersona/core/      # attach / blend / check / recommend / authoring（ロジック本体）
  ├── hersona/cli/      # 対話 CLI/TUI の殻 (textual 等)
  ├── skills/hersona/   # Hermes スキルの殻 (/hersona コマンド)
  └── (将来) web/       # Web 殻
attributes/        # 公開・汎用属性のみ (CC0)
~/.hermes/, attributes/user/   # ユーザー作成データ (gitignore)
```

### 利用形態

- **Hermes スキルとして**: `/hersona <category>/<name> [mode]`（既存）
- **CLI/TUI アプリとして**: 上記コマンド群をローカルで対話実行
- **データ提供として**: 他 LLM で `attributes/*.yaml` を直接 system prompt に貼付

---

## ワークストリーム

### ① 相性マトリクス整備 ★着手済み (core)

`conflicts_with` / `compatible_archetypes` を **データとして引ける形** に整備する。
②推薦エンジンの燃料であり、③/multi の conflict 自動チェックの基盤。

- [x] 全 25 属性の相性関係を機械可読なマトリクスとして集約 (`hersona/core/compatibility.py`, `--json` ダンプ対応)
- [x] conflict / compatible の双方向整合を `validate.py` で検証 (conflict 非対称を警告)
- [x] core から `is_compatible(a, b)` / `conflicts(a, b)` を引ける API (+ `relation` / `check_blend`)

### ③ ローカルオーサリング基盤 ★着手済み (core)

ユーザーがローカルで自分の属性/人格を作り、適用できる機能。core ロジックは
`hersona/core/authoring.py` に実装。

- [x] 属性組み立て API（`build_attribute` / `override_attribute`、手書き YAML 不要）
- [x] 既存属性のフィールド上書き（`override_attribute`: tsundere を土台に catchphrases だけ差し替え 等）
- [x] 保存先の分離: 既定 `~/.hermes/attributes/`（または `HERSONA_USER_DIR`）/ `attributes/user/` は **gitignore**。公開 `attributes/` には混ざらない
- [x] スキーマ検証ゲート: `save_attribute` が `schema/attribute.schema.json` 違反を拒否
- [x] **固有名詞ガードは「共有時のみ」発動**（`assert_shareable` / `find_proper_noun_risks`。ローカル保存は自由）
- [ ] ガイド付き対話ウィザード（CLI/TUI 殻。上記 core API の上に乗せる）

### ② 評価・推薦システム ★既存の仕組みを再利用

新規エンジンを作らず、`/hersona check` の 5 項目 100 点採点ロジックを
「適合度スコア」に転用する。

#### フロー: 診断 → 推薦 → 適用（→ 任意で保存）

```
/hersona recommend
  → ① 診断クイズ（数問）
  → ② 適合度スコアリング（既存 check ロジック転用）
  → ③ 推薦ブレンド提示（属性 + weight + 相性チェック済み）
  → ④ そのまま適用（内部で multi モードのアタッチを呼ぶ）
```

推薦結果＝属性ベクトルは `multi` モードの入力そのもの。新規実装ではなく
既存 attach 機構へ流す（①の相性マトリクスで conflict 自動チェック）。

#### コマンド体系

| コマンド | 挙動 |
|---|---|
| `/hersona recommend` | 診断 → 推薦提示 → 「適用する？ [Y/n]」（デフォルト適用） |
| `/hersona recommend --apply` | 確認スキップで即適用 |
| `/hersona recommend --dry-run` | 推薦のみ表示、適用しない |
| `/hersona recommend --save <name>` | 推薦ブレンドをローカル属性として保存（③と接続） |

#### 要点

1. 適用は必ず①の相性マトリクスを通す（conflict 含む可能性 → 適用前に警告。multi と挙動共用）
2. `--save` で③と接続 — 診断結果を再利用可能な資産にする
3. 適用後の解除は既存 `/hersona default` で統一（新解除コマンドは作らない）

入力方式は (a) 診断クイズ → 属性ベクトル を起点。(b) サンプル応答評価は次段、
(c) 過去会話解析は重いため後回し。

### ① speech 拡張 / weight 較正（基盤後に薄く）

「数より軸」。定番アーキタイプの量産はしない。

- [ ] speech 拡張: 方言・語尾・一人称（アンカー効果が大きく、プリセットが実際に効く軸）
- [ ] weight 較正: mild / moderate / strong の実例整備

---

## スキル (SKILL.md) の追従

CLI/TUI アプリ化と②③に合わせ、`skills/hersona/SKILL.md` のコマンド体系も拡張する。

- [ ] `/hersona recommend`（診断 → 推薦 → 適用 → 任意で保存）を追記
- [ ] `/hersona create`（ローカルオーサリング）を追記
- [ ] 次バージョン（v3.0.0 → v3.1.0 以降）で反映

---

## 横断リスクと原則

1. **DISCLAIMER 問題の再燃防止** — v1.0 で `data/<キャラ>` を廃止した意図を尊重。
   ローカル作成は自由だが、公開 repo への commit / 共有機能での配信は「汎用属性のみ」。
   保存先分離（gitignore）と共有時の固有名詞ガードで担保する。
2. **品質の希薄化防止** — カタログ拡大に伴い `validate.py` + `check` ベースの品質ゲートを維持。
3. **スコープ固定** — コア＝ロジック、各殻＝薄く。ホスト型 Web へ進む場合も core を再利用する。

---

## 依存関係（推奨着手順）

```
① 相性マトリクスをデータ化      ← ②の前提。最初に着手
   ↓
③ ローカルオーサリング基盤       ← ①の YAML 追加コストも下げる
   ↓
② 評価・推薦（check 転用 + 診断クイズ + recommend→apply）
   ↓
① speech 拡張 / weight 較正      ← 基盤が固まってから薄く足す
```
