# ペルソナパック & use_case 拡張 — 設計書・開発指示書(2026-07-05)

> 目的: 利用者獲得のための機能追加。参考: 数百のエージェント定義 Markdown を
> 「ツールの標準機構にファイルを置くだけ」で配布し、大規模な採用を得ている
> 先行のエージェント定義カタログ OSS(以下「先行カタログ」)。
> 方針: **Hermes 特化**。Claude Code の `.claude/agents/` ではなく、Hermes の
> `agent.personalities.<name>` レジストリ + `agent.personality` 切替を配布先とする。
> 位置づけ: `docs/reviews/2026-07-04-external-review-response.md`(品質・信頼性)完了後の
> 成長フェーズ第1弾。`docs/IMPROVEMENT_PLAN.md` §「体験までの距離」とも合流する。

---

## 0. 背景 — 先行カタログから借りるもの・借りないもの

先行カタログが採用を得ている本質は中身(数百のエージェント定義)ではなく**配布形態**:

1. ユーザーが既に使うツールの標準機構にファイルを置くだけ(インストール摩擦ゼロ)
2. 出来合いカタログから「選んで入れる」だけで動く(構成作業ゼロ)
3. 名前で呼ぶだけで切り替わる

hersona は (1) の配管を既に持つ(`hersona persistent --auto-config` が
`agent.personalities.<name>` への安全書込と `--apply` 切替を実装済み。
`hersona/core/persistent.py`)。欠けているのは (2) **出来合いカタログ**と、
それを一括で扱う (3) **一覧・導入・切替の UX** である。

**借りないもの**: 多ツール変換の全面展開(Cursor/Copilot/…)。既存 `targets.py` の
4 ターゲットで当面十分であり、本計画は Hermes 動線に集中する。

**差別化**(そのまま README / 宣伝文になる):

| 汎用エージェント定義カタログ | hersona ペルソナパック |
|---|---|
| 役割のみ、人格制御なし | ペルソナ × 役割(use_case)× **強度ダイヤル** |
| 静的テンプレ | conflict 検査済みブレンド + `hersona bench` で維持率を**測定可能** |
| 汎用ツール向け | **Hermes の複数 personality 登録・即切替**にネイティブ対応 |

## 1. スコープ

- **W1: ペルソナパック** — `personas/*.yaml`(レシピカタログ)+ `hersona personas` CLI
- **W2: use_case 拡張** — 現行 8 → 20(+12)。スキーマ変更なし
- W1×W2 の掛け算で初期パック 14 本を同梱

**非スコープ**(将来課題として明記のみ):

- `hersona update` の配布対象に `personas/` / `use_cases/` を加える変更
  (`DATA_DIRS` / `checksums.json` / `gen_checksums.py` の契約変更を伴うため別 PR)
- デモサイトへのパックギャラリー掲載(`build_site.py` 拡張)
- Claude Code サブエージェント形式(`.claude/agents/`)への書き出し
- パックへの `--memory` 同梱(memory はユーザー文脈であり、カタログに焼くべきでない)

---

# W1: Hermes ペルソナパック

## 2. データ設計

### 2.1 `personas/<persona_name>.yaml`(新規ディレクトリ、リポジトリ直下)

```yaml
persona_name: keigo_support          # ^[a-z][a-z0-9_]*$ (config.yaml キーになる)
display_name: Courteous Support      # BASE=en (属性 YAML と同じ i18n 方針)
description: A precise, courteous customer-support persona in polite keigo Japanese.
blend:                               # 実在属性のみ。conflict フリーであること (CI で担保)
  - personality/diligent
  - speech/keigo
weight: moderate                     # none/mild/moderate/strong
use_case: customer_support           # 任意。use_cases/ に実在すること
tags: [support, keigo, polite]       # 任意
i18n:
  ja:
    display_name: 敬語カスタマーサポート
    description: 折り目正しい敬語で応対するカスタマーサポート担当。
```

設計判断:

- **レシピであって成果物ではない**。注入ブロック本文は焼かず、install 時に
  `render_blend`/`run_persistent` で生成する(属性 YAML 更新が自動で反映され、
  `build_site.py` 型のドリフトゲートが不要になる)。
- persona content(catchphrases 等)を持たない — 人格は blend 先の属性が正。
  CLAUDE.md の「persona content 非翻訳」規則の対象物をパック側に増やさない。
- ライセンスは `attributes/` と同じ **CC0**(README のライセンス表に行を追加)。

### 2.2 `schema/persona_pack.schema.json`(新規)

`use_case.schema.json` と同型の Draft 2020-12。required:
`persona_name` / `display_name` / `description` / `blend` / `weight`。
`additionalProperties: false`。`blend` は `minItems: 1`、
`weight` は enum `[none, mild, moderate, strong]`。`i18n` は use_case と同形式。

### 2.3 パッケージング

- `pyproject.toml` の force-include に `"personas" = "hersona/data/personas"` を追加
  (`use_cases` と同じ行のパターン)。
- `hersona/core/paths.py` に `personas_root()` / `persona_pack_schema_path()` を追加
  (`use_cases_root()` の実装をコピーして名前だけ変える)。

## 3. コア設計 — `hersona/core/personas.py`(新規)

`use_cases.py` を範として、殻に徹する(合成は既存 core へ委譲):

| シンボル | 内容 |
|---|---|
| `PersonaPackError(ValueError)` | 例外 |
| `available_personas(*, root=None) -> dict[str, dict]` | `{persona_name: {display_name, description, use_case, weight, path}}`。`available_use_cases` と同じ走査・防御 |
| `load_persona(name, *, root=None) -> dict` | YAML ロード + スキーマ検証。無ければ `KeyError` |
| `validate_persona(data, *, matrix=None) -> list[str]` | スキーマ検証 + **意味検証**: blend の属性が実在するか(`load_attribute`)、`check_blend` で conflict がないか、`use_case` が実在するか。エラー文字列のリストを返す(`authoring.validate_attribute` と同じ流儀) |
| `install_persona(name, *, auto_config=False, apply=False, ...) -> PersistentResult` | `run_persistent(blend, weight=…, use_case=…, profile=…, without_soul=True, auto_config=…, apply=…)` への薄い委譲。**`without_soul=True` が既定**(SOUL.md は 1 プロファイル 1 枚であり、複数パックの一括導入先は `agent.personalities` レジストリ。SOUL も欲しい場合は `--with-soul`) |

注意: `run_persistent` の `persona_name` が blend から自動導出される場合、
パックの `persona_name` で上書きできるかを確認し、できなければ
`run_persistent` に keyword 引数 `persona_name=None`(既定 None = 従来挙動)を
**追加**する(後方互換のある追加なので minor。`docs/PUBLIC_API.md` / `.en.md` を同時更新)。

## 4. CLI 設計 — `hersona personas <verb>`

`use-case` サブコマンドの `list|show` サブサブコマンド構造を踏襲:

```
hersona personas list [--json]
    同梱パック一覧: persona_name / 表示名 (i18n) / blend / weight / use_case
hersona personas show <name> [--json]
    詳細 + 注入ブロックプレビュー (render_blend で生成して表示)
hersona personas install <name...> [--auto-config] [--apply] [--profile P]
                         [--with-soul] [--force] [--dry-run]
    複数一括導入。--dry-run は config.yaml ブロックの表示のみ (書き込みなし)。
    --apply は最後に指定した 1 件に対してのみ実行 (agent.personality は単一値)
hersona personas use <name>
    hermes config set agent.personality <name> (persistent._apply_personality 再利用)。
    未 install の名前は警告 (レジストリ照会はできないため「install 済みか確認せよ」の注意文言)
```

- 文言は `locales/en.yaml` / `ja.yaml` に `personas.*` / `help.personas*` を新設
  (既存の `bench:` 追加と同じ手順)。
- エラー体系: 不明パック → `KeyError`(main() が exit 1 に変換)。
  validate エラー → メッセージ列挙して exit 1。

## 5. recommend ブリッジ

`hersona recommend --install-persona NAME [--auto-config] [--apply]`:
診断結果 blend + `weight_suggestion` を、その場で `agent.personalities.NAME` に登録する。
実装は `_cmd_recommend` の既存ブリッジ分岐(`--export`/`--soul`/`--save`)に 1 分岐追加し、
`run_persistent(..., without_soul=True)` へ委譲。`--json` との排他は既存と同じ扱い。

## 6. 初期パックセット(14 本)

blend は必ず `check_blend` conflict フリーであること(T6 の受け入れ基準)。
表示名 i18n.ja 必須。★ = W2 の新 use_case に依存(T5 完了後に執筆)。

| persona_name | blend | weight | use_case |
|---|---|---|---|
| keigo_support | diligent + keigo | moderate | customer_support |
| kansai_marketer | genki + kansai_ben | moderate | marketing |
| tsundere_reviewer | tsundere + blunt | moderate | qa_reviewer |
| kuudere_analyst | kuudere + soft | mild | data_analyst |
| genki_planner | genki + casual_en | moderate | planner |
| sensei_writer | intellectual + sensei | moderate | tech_writer ★ |
| butler_assistant | diligent + butler | strong | executive_assistant ★ |
| onee_recruiter | sociable + onee_kotoba | moderate | hr_recruiter ★ |
| samurai_devops | stoic + samurai_lol | mild | devops_engineer ★ |
| vtuber_streamer | playful + vtuber | strong | streamer_copilot ★ |
| miko_tutor | serious + miko | moderate | tutor ★ |
| british_pm | pragmatist + british_en | moderate | product_manager |
| gyaru_community | genki + gyaru | strong | community_manager ★ |
| warawa_gamemaster | mysterious + warawa | strong | game_master ★ |

(組み合わせは草案。T6 で conflict / compatible_archetypes を確認しながら確定する。
確定表がこの表と食い違ったら**本ドキュメントを更新**すること。)

---

# W2: use_case 拡張(8 → 20)

## 7. 拡張方針

- **スキーマ変更なし**。`category` enum(technical/business/analysis/education/
  creative/conversation/regulated/lifestyle)は未使用値を含めて既設。
- ゴールデンサンプルは `use_cases/programmer.yaml`。全項目(role/principles/
  workflow/grounding_policy/output_contract/quality_gate/safety)を同じ粒度で書く。
- 本文は **English**(トークン効率と指示追従の既定方針)。`i18n.ja` の
  display_name/description は必須とする。
- **規制領域の規律**: 医療・法務・投資の「助言」を行う use_case は追加しない
  (`DISCLAIMER.md` の範囲を超える)。金融は "analysis"(データ読解)に留め、
  `risk_level: medium` + boundaries で「専門家の代替をしない」を必須にする。

## 8. 追加 12 本の選定

| use_case_id | category | risk | 概要 |
|---|---|---|---|
| frontend_developer | technical | low | UI 実装・アクセシビリティ・状態管理の規律 |
| backend_architect | technical | low | API 設計・データモデル・信頼性の規律 |
| devops_engineer | technical | medium | CI/CD・IaC・運用。destructive 操作の safety 必須 |
| security_reviewer | technical | medium | 脆弱性レビュー。悪用手順は出さない boundaries 必須 |
| tech_writer | technical | low | ドキュメント執筆。正確性 > 網羅性の規律 |
| executive_assistant | business | low | スケジュール・要約・調整。機密の扱いを safety に |
| hr_recruiter | business | medium | 求人・スクリーニング補助。差別回避を boundaries に |
| tutor | education | low | 段階的説明・答えを先に言わない workflow |
| creative_writer | creative | low | 小説・脚本補助。既存 IP の複製回避を boundaries に |
| game_master | creative | low | TRPG/ロールプレイ進行。セーフティツール(X カード等)を safety に |
| community_manager | conversation | medium | モデレーション・アナウンス。炎上時のエスカレーション規律 |
| streamer_copilot | creative | low | 配信企画・チャット対応台本。hersona の主客層向け |

(12 本確定。§8 起草時は 13 本候補 (sales を含む) だったが、business カテゴリで
product_manager / marketing / planner と役割が近接するため sales を除外した。
§6 の依存パック (14 本) はいずれも本表 12 本で成立するため、§6 テーブルの更新は不要。)

---

# 開発指示書(Work Order)

## 9. タスク分割

実装は 2 PR に分ける: **PR-A = W2(use_case 12 本)**、**PR-B = W1(パック一式)**。
W1 のパックが W2 の use_case に依存するため、この順で進める。

### PR-A: use_case 拡張

- **T5-1**: `use_cases/*.yaml` を 12 本執筆(§8 の表)。`programmer.yaml` の構造・
  粒度に合わせる。`validate_use_case` を通ることを 1 本ずつ確認。
- **T5-2**: `tests/test_use_cases.py` — カタログ件数・新 ID の存在・全ファイルが
  スキーマを通る回帰を追加(件数ハードコードは 1 箇所に)。
  `scripts/validate.py` は use_cases を対象にしていない(確認済み)ため、
  **validate.py に use_cases 検証を追加する**(スキーマ検証のみ、属性ほど重くない)。
- **T5-3**: ドキュメント: README EN/JA の use-case 節(件数と代表例)、CHANGELOG。

受け入れ基準: `pytest tests/test_use_cases.py` 全パス /
`hersona use-case list` に 20 件 / README の件数表記が一致。

### PR-B: ペルソナパック

- **T1**: `schema/persona_pack.schema.json` + `personas/` + `paths.py`
  (`personas_root` / `persona_pack_schema_path`)+ `pyproject.toml` force-include。
- **T2**: `hersona/core/personas.py`(§3)+ `tests/test_personas.py`
  (スキーマ検証 / 意味検証 (存在しない属性・conflict ペア・存在しない use_case が
  エラーになる) / install が `PersistentResult` を返す / 同梱全パックが
  `validate_persona` を通る回帰)。`run_persistent` に `persona_name` 引数を
  追加した場合は `tests/test_persistent.py` 相当と `docs/PUBLIC_API.md`/`.en.md` も更新。
- **T3**: CLI(§4)+ `locales/en.yaml`/`ja.yaml` + `tests/test_cli.py`
  (list/show/install --dry-run/use の非対話経路。config.yaml 実書込は tmp 隔離)。
- **T4**: recommend ブリッジ(§5)+ テスト。
- **T6**: 初期パック 14 本執筆(§6)。**受け入れ基準: 全パックが
  `validate_persona` エラー 0(= conflict フリー・属性/use_case 実在)**。
  これをテスト化して CI で恒久担保する(`test_personas.py` に含める)。
- **T7**: ドキュメント一式:
  - README EN/JA: 「Persona packs for Hermes」節(§0 の比較表を流用)、
    ライセンス表に `personas/` = CC0 行を追加
  - `docs/hermes-agent.md`: 方法 D として `hersona personas install` を追記
  - `skills/hersona/SKILL.md`: コマンド一覧に 1 行(トークン規律に従い詳細は
    REFERENCE.md へ)。version minor バンプ
  - `CHANGELOG.md` `## [Unreleased]`
- **T8**: 検証: `python scripts/release_check.py`(全ゲート)。
  `gen_checksums.py` は Phase 1 では `personas/` を対象に**しない**
  (DATA_DIRS 契約と揃えるため。§1 非スコープ参照)。

受け入れ基準: `hersona personas install keigo_support --dry-run` が config.yaml
ブロックを表示 / `--auto-config` で tmp の config.yaml に 2 パック一括登録できる /
`hersona personas use` が `hermes` 不在環境で安全にエラーを返す /
release_check.py 全ゲート OK。

## 10. 共通規律(CLAUDE.md 準拠チェックリスト)

- README は **EN/JA 両方**を同一 PR で更新
- SKILL.md は本体最小・詳細 REFERENCE.md、`version:` を独立 SemVer でバンプ
- persona content(catchphrases 等)は翻訳しない(パックは持たない設計なので
  主に属性側を触らないことの確認)
- 各 PR で `CHANGELOG.md` `## [Unreleased]` に追記
- タグ前は `scripts/release_check.py`(`docs/RELEASE_CHECKLIST.md`)

## 11. リスクと判断メモ

- **config.yaml の肥大**: personalities 各エントリに注入ブロック全文が入るため、
  多数 install で config.yaml が肥大する。`install` に一括件数の上限は設けないが、
  5 件以上の一括指定時に合計サイズを表示して注意を促す(実装は print 1 行)。
- **`personas use` の限界**: hersona からは Hermes レジストリの照会 API を持たない
  (Pitfall 回避で読み取りも実装していない)ため、「未 install の名前への切替」は
  検出できない。文言で注意する以上のことはしない。
- **名前空間**: `persona_name` は preset 名・属性名と独立の名前空間。衝突検査は
  しない(config.yaml のキーとしてのみ意味を持つ)が、同梱パック同士の重複は
  スキーマ検証(available_personas の dict キー衝突検出)で CI に落とさせる。
- **W2 の品質**: use_case は「常に注入される英語プロンプト」であり、雑な 12 本は
  製品価値を直接毀損する。1 本あたり programmer.yaml と同等の推敲を行い、
  機械生成の言い回し重複(principles の使い回し)を T5-2 のテストで検査する
  (完全一致 principles が 2 ファイル以上に現れたら fail)。
