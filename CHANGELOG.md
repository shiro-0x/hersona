# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added (i18n Phase 5: 英語ペルソナ拡充)
- **英語で喋る speech 属性 5 種を新設** (`content_lang: en`): `formal_en` / `casual_en` /
  `blunt_en` / `southern_us_en` / `british_en`。属性数 59 → **64** (speech 20 → 25)
- schema に **`lexical_markers`** (string[]) と **`register`** (enum formal/neutral/casual/vulgar)
  を追加。英語 speech は語尾活用が無いため `sentence_endings` の代わりにこれらで特徴づける
- **intensity に英語採点パスを実装**: `content_lang: en` のブレンドは lexical_markers の
  出現率 + catchphrase 密度で採点 (`unsupported_lang` skip は ja/en 以外のみ)
- **言語をまたぐ speech は構造的に conflict**: `content_lang` の異なる speech 同士を
  `CompatibilityMatrix.conflicts` で排他に (1 人格に ja/en の話法を混在させない)。
  英語 speech 5 種は互いにも相互排他 (`conflicts_with`)
- `render_blend` は英語ペルソナに `Respond in English …` の指示行を付与
- `build_site` / `site/data.json` に `content_lang` / `lexical_markers` / `register` を反映 (64 属性)
- README (en/ja) の属性表・件数・任意フィールドを更新
- テスト: 英語 speech 検証 / en intensity 採点 / 言語跨ぎ conflict を追加 (全 427 件)

### Changed (i18n Phase 4: コンテンツの言語認識化)
- **`content_lang` フィールドを新設** (schema, enum `ja`/`en`)。人格コンテンツ
  (sentence_endings / catchphrases / tone / examples / core_traits) の言語を明示。
  未指定は後方互換で `ja` 扱い
- 全 20 `speech/*` 属性に `content_lang: ja` を付与
- **intensity を言語認識化**: `IntensityReport.lang` を追加、`content_language()` /
  `skip_reason()` を新設。ja 人格に非日本語テキストを与えた場合は `lang_mismatch` で
  skip、ja 以外コンテンツは `unsupported_lang` で skip (現行採点は ja 専用)
- `hersona measure` が言語不一致/未対応言語を区別したメッセージで skip
- **`render_blend` に応答言語の指示行を追加** (設計書 §3.4)。コンテンツ言語に応じて
  「応答は日本語で行う…」/ `Respond in English…` を注入ブロック冒頭に付与
- **推薦サマリ (`Recommendation.summary`) を表示言語に追従**。文型・区切り・表示名を
  カタログ (`summary.*`) 経由で en/ja 切替 (en: "a Tsundere Rival who speaks with Keigo")
- 推薦の代替案/サマリの「該当なし」も `common.none` でロケール化
- テスト: content_lang / intensity 言語認識 / 言語指示 / サマリ en・ja を追加 (全 401 件)

### Changed (i18n Phase 3: Quiz のロケール分離)
- **診断クイズ (`recommend_quiz.yaml`) の prompt / label を BASE=en + `i18n.ja` ブロック化**。
  全 9 問 + 全選択肢を英語ベースに翻訳し、日本語は `i18n: {ja: {prompt|label}}` へ
- `QuizQuestion.localized_prompt(lang)` / `QuizOption.localized_label(lang)` を追加
  (フォールバック: `<lang>` → BASE)。`load_quiz` が `i18n` を読み込む
- 推薦の rationale (`question "..." -> "..."`) と conflict 落選理由を表示言語に追従
  (`recommend.rationale_item` / `recommend.conflict_reason` をカタログ化)
- 対話クイズ (`hersona recommend`) のプロンプト/選択肢を表示言語で出力
- `build_site.py` は quiz を ja 解決して `site/data.json` を生成 (JSON 形状・サイトは不変)
- 質問 ID (`distance` / `speech` 等 = `--answers` のキー) は不変 — API 後方互換
- skill (`hersona-recommend-quiz`) に i18n 構造の注記を追加
- 注記: 推薦サマリ (日本語文法で構成される人格コンテンツ) は引き続き Phase 4〜5 対象
- テスト: quiz i18n / localized_* / rationale の en・ja を追加 (全 392 件)

### Changed (i18n Phase 2: メタデータ英語ベース化 + i18n ブロック) — データ形式移行
- **属性メタデータを BASE=en + `i18n.<lang>` ブロック形式へ移行** (設計書 §2.2)。
  `display_name_en`→`display_name` / `description_en`→`description` (BASE)、
  `display_name_ja`/`description_ja`→`i18n.ja.*`。旧 4 キーは削除
- 全 59 公開属性 YAML を新形式へ一括移行 (`scripts/migrate_i18n.py`)
- `scripts/migrate_i18n.py` を追加 — 旧→新の一括変換 (`--dry-run` 対応、冪等)
- `schema/attribute.schema.json` を **oneOf で新旧両形式を受理** (移行期の後方互換)。
  `i18n` プロパティ・BASE `display_name`/`description` を追加、必須は共通 4 項目に緩和
- `authoring.build_attribute` が新形式を出力 (CLI の二言語入力 `--display-ja/en` 等は維持)
- `hersona show` を `i18n.resolve_meta` でロケール解決 (display_name / description を表示言語で)
- `recommend` サマリの表示名解決を `resolve_meta(..., "ja")` に変更 (日本語サマリを維持)
- `scripts/build_site.py` は i18n 形式から `display_name_{ja,en}`/`description_{ja,en}` を
  解決して `site/data.json` を生成 (JSON 形状・サイトは不変)
- 注記: 凍結生成物 `scripts/_oneoff/gen_v1_attributes.py` は旧形式を出力する。再実行後は
  `python scripts/migrate_i18n.py` で再移行すること
- テスト: 公開属性の新形式ロック (`test_attributes`) + `tests/test_migrate_i18n.py` 追加 (全 389 件)

### Changed (i18n Phase 1: UI 英語ベース化) — BREAKING (既定言語)
- **CLI の既定表示言語を英語 (en) に変更。** `--lang ja` / `HERSONA_LANG=ja` で従来の
  日本語 UI に戻せる(往復可能・後方互換)
- CLI 文言を全面カタログ化(`hersona/locales/{en,ja}.yaml`)。`app.py` の help/description・
  各種 print/input・エラー文言を `i18n.tr()` 経由に置換
- CLI が surface する core 例外メッセージ(属性が見つかりません 等)もロケール追従
  — `attach` / `authoring` / `compatibility` / `recommend` / `intensity.format_report`
- `--help` / `description` も表示言語でローカライズ(パーサ構築前に言語を確定)
- `schema/attribute.schema.json` の `description` を英語ベースに変更(開発者向けメタ)
- `README.md` を英語化し、日本語版を `README.ja.md` に分離(相互リンク付き)
- `i18n` にプロセス共通の表示言語 (`set_active_lang`/`active_lang`) を追加。
  `tr()`/`resolve_meta()` は lang 省略時に現在の表示言語を使用
- 注記: 注入ブロック (`render_blend` 出力) と推薦サマリ等の**人格コンテンツ本文**は
  言語束縛のため本フェーズ対象外(Phase 3〜5 で対応)。`compatibility._main` /
  `scripts/validate.py` 等の開発診断出力も対象外
- テスト: `tests/test_cli.py` を en 既定に更新 + `--lang ja` 往復テスト追加、
  `tests/conftest.py` で表示言語をテスト間リセット(全 324 件パス)

### Added (i18n Phase 0: 言語プラミング)
- `hersona/core/i18n.py` — 言語選択とロケール解決の基盤。既定言語を **英語 (en)** とし、
  `--lang {en,ja}` フラグ / `HERSONA_LANG` 環境変数で切替 (優先順: フラグ > 環境変数 > en)
  - `resolve_lang()` / `normalize_lang()`(`en-US` 等の地域サブタグを基底言語へ丸め)
  - `tr()` 文言カタログ参照(フォールバック: `<lang>` → en → キー文字列)
  - `resolve_meta()` 属性メタデータのロケール解決(新 `i18n.<lang>` と旧 `*_ja`/`*_en` を両受理)
- `hersona/locales/{en,ja}.yaml` — CLI 文言カタログの初版(Phase 0 は最小セット)
- CLI に `--lang` を配線(トップレベル/各サブコマンド双方で前置・後置を受理)
- `tests/test_i18n.py` — 言語決定・カタログ・メタ解決・CLI 配線の 21 テスト
- `docs/I18N_DESIGN.md` — i18n 設計書(スコープ Phase 0〜5・英語ペルソナまで)
- 後方互換: 既存の日本語 CLI 出力・`*_ja`/`*_en` フィールドは不変。`--lang ja` で従来表示

### Added (Batch 4: speech / personality 拡張)
- 属性 7 種を追加。属性数 52 → **59** (personality 17→20 / speech 16→20)
  - speech: `seductive`(誘惑・色気)/ `stutter`(吃り・言い淀み)/ `blunt`(ぶっきらぼう)/ `theatrical`(芝居がかり)
  - personality: `chuunibyou`(中二病)/ `narcissist`(ナルシスト)/ `optimist`(楽観的)
  - 新カテゴリは作らず既存 speech / personality に純加算 (schema / core 不変)
  - 手書き YAML で追加(凍結生成物 `scripts/_oneoff/gen_v1_attributes.py` は Batch 3 完結スナップショットのため不変)
- `docs/BATCH4_DECISIONS.md` — Batch 4 の設計合意の記録(積み残し判断 + 新規 5 種の方向性)
- テストの数量アサーションを 52 → 59(personality 20 / speech 20)に更新
- `hersona/data/quiz/recommend_quiz.yaml` に Batch 4 の 7 属性への到達経路を追加(v1.2.0 の YAML 外部化に追随)
  - `speech` 質問へ 4 オプション(seductive / stutter / blunt / theatrical)、`emotion` 質問へ 3 オプション(chuunibyou / narcissist / optimist)を追記。質問数は 9 のまま
  - `test_recommend.py` に 7 属性の到達経路テストを追加

### Fixed (visual / hobby カテゴリの取りこぼし)
- `hersona list` がヘッダーで「59 件」と表示しながら `visual` / `hobby` の 10 件を
  一覧に出していなかった問題を修復(`_cmd_list` がカテゴリを 3 種ハードコードしていた)
- `hersona create` が `visual` / `hobby` 属性を作成できなかった問題を修復
  (schema の enum は 5 種だが `--category` choices と対話ウィザードが 3 種固定だった)
- カテゴリの正準順序を `hersona.core.constants.CATEGORY_ORDER` に集約し、
  list / create / recommend が同一ソースを参照するよう統一(新カテゴリ追加時の再発防止)
- `test_cli.test_list` に visual / hobby 属性の表示アサーションを追加(回帰防止)

### Changed (ドキュメント / バージョン整合)
- `pyproject.toml` の `version` を 0.2.0 → 1.2.0 に修正(CHANGELOG の最新リリースと一致)
- `README.md` の属性数・カテゴリ表を実体に同期(52 種 3 カテゴリ → 59 種 5 カテゴリ、
  enum 説明「3 種」→「5 種」、personality 17→20 / speech 16→20 の名称も補正)

### Fixed (CLI ランチャ修復)
- `hersona` CLI ランチャ (`~/.hermes/hermes-agent/venv/bin/hersona`) が
  `ModuleNotFoundError: No module named 'hersona'` で死亡していた問題を修復
- 原因: ランチャの shebang が venv の python を指しているのに、
  venv の `site-packages` に hersona パッケージが登録されていなかった
- 対処: `~/.hermes/hermes-agent/venv/bin/pip install -e ~/projects/hersona`
  (editable install) を実行。`hersona --help` が subcommand 一覧を返すことを確認
- 再発防止: 新規マシン/venv セットアップ時は
  `pip install -e ~/projects/hersona` を必ず走らせること

## [1.2.0] - 2026-06-09

### Added (recommend 強化)
- `hersona/data/quiz/recommend_quiz.yaml` — 診断クイズを Python コードから分離して YAML 外部化
  - 9 問構成 (旧 5 問 → +appearance / +hobby / +lifestyle / +interaction / +cultural 軸)
  - 52 属性 (personality 17 / speech 16 / archetype 9 / visual 5 / hobby 5) フル活用
  - weight は WeightMagnitude 名前空間 (`STRONG=2.5` / `MODERATE=2.0` / `MILD=1.5` / `WEAK=1.0`) で記述
  - 質問 ID の安定性保証 (CLI `--answers` API 互換)
- `WeightMagnitude` enum (`hersona/core/recommend.py`) — クイズ用重みスケール
- `RECOMMEND_THRESHOLDS` 定数 — 強採用 (4.0+) / 採用 (2.0+) / 補欠 (1.0+) の境界
- `load_quiz(path=None)` — YAML から `QuizQuestion` リストを組み立てる (任意パス対応)
- `Recommendation.rationale` — 各採用属性の根拠 (どの質問/選択肢から) を dict で保持
- `Recommendation.alternatives` — conflict で落ちた属性に対する推奨代替
- `Recommendation.summary(matrix=None)` — 1 文の日本語サマリ (例: 「京都弁 で話す リアリスト な 幼馴染。料理好き・眼鏡・知的に」)
- `Recommendation.weight_suggestion` — トップスコアからの推奨強度 (none / mild / moderate / strong)
- CLI: `hersona recommend --explain` — 各属性の根拠 + 落選の代替案 + サマリを表示
- CLI: `--json` に `rationale` / `alternatives` / `summary` / `weight_suggestion` を含める
- `tests/test_recommend.py` (29 件 / 旧 12 件から +17 件)
>>>>>>> origin/main

## [1.1.0] - 2026-06-09

### Added (強度指標 / intensity metric)
- `hersona/core/intensity.py` — 出力テキストの強度指標 (ROADMAP ★計画 → 実装済み)
  - `IntensityReport` / `measure_intensity()` / `verify()` / `expected_band()` / `format_report()`
  - 採点軸: 語尾一致率 60% + 口癖密度 40% (決定的・LLM 不使用)
  - speech 属性が無いブレンドは skip (None)。`/hersona check` とは別経路
- `hersona measure <name>... --weight <level> --input <file>|--text "..."`
  - 期待バンド (none 0-20 / mild 20-45 / moderate 45-70 / strong 70-100) と比較して
    `pass` / `under` / `over` を判定。`under` のとき stderr に警告 (exit code は 0)
- `tests/test_intensity.py` (26 件)
- README / CHANGELOG / ROADMAP / SKILL.md を更新

### Added (speech 拡張: 京都弁)
- `attributes/speech/kyoto_ben.yaml` — 京都弁 (京言葉: わ、一人称「うち」/ 語尾「〜どす/〜え/〜はる」/ はんなり婉曲)。`kansai_ben` の京言葉派生 (variant=kyoto)。属性数 26 → **27** (speech 9 → 10)
  - generator SSOT 経由で追加、`_check_category_counts` を speech=10 に更新
  - `recommend` 診断クイズの speech 質問に到達経路を追加 (conflicts_with: genki / ore_boy)

### Added (ROADMAP ① speech 拡張 / weight 較正)
- `attributes/speech/washi.yaml` — 老人語 (一人称「わし」+ 語尾「〜じゃ/〜のう」軸)。属性数 25 → **26** (speech 8 → 9)
  - generator SSOT (`scripts/_oneoff/gen_v1_attributes.py`) 経由で追加、`_check_category_counts` を speech=9 に更新
  - `recommend` 診断クイズに到達経路を追加
- `hersona/core/weight.py` — weight 較正の core モジュール
  - `WeightLevel` / `WEIGHT_GUIDANCE` / `catchphrase_subset()` / `suggest_weight()`
  - `render_blend(weight=...)` が強度ガイダンスと catchphrases 露出量を調整
  - CLI: `blend --weight`、`recommend --apply` は適合度スコアから強度を自動推定
- `tests/test_weight.py` (7 件)。属性数の回帰アサーションを 26 に更新

### Changed (hersona skill v3.1.0)
- `skills/hersona/SKILL.md` を v3.0.0 → v3.1.0 に更新
  - `/hersona recommend`（診断クイズ → 推薦ブレンド → 適用 → 任意で保存）を追記
  - `/hersona create`（ローカル属性オーサリング、検証ゲート + 共有時のみ固有名詞ガード）を追記
  - スキルと `hersona` CLI が `hersona/core/` (compatibility / authoring / recommend / attach) を共有することを明記
  - 既存コマンドは不変（下位互換）

### Added (ROADMAP CLI/TUI 殻)
- `hersona/core/attach.py` — 属性ロード・ブレンド合成の core モジュール
  - `load_attribute()` / `available_attributes()` — 公開 + user 名前空間の属性解決 (user が公開を上書き)
  - `render_blend()` — 複数属性をシステムプロンプト注入ブロックに合成、① マトリクスで conflict を併記
- `hersona/cli/` — `hersona` コマンド (argparse CLI、`python -m hersona.cli`)
  - `list` / `show` / `matrix [--json]` / `blend <name>...`
  - `recommend [--answers ... | 対話] [--apply] [--json]` — 診断クイズ → 推薦 → 注入ブロック
  - `create [フラグ | 対話ウィザード]` — 検証ゲート付きでユーザー名前空間に保存
- `pyproject.toml`: `[project.scripts] hersona` エントリポイントを追加
- `tests/test_attach.py` (7 件) / `tests/test_cli.py` (12 件)

### Added (ROADMAP ① 相性マトリクス整備)
- `hersona/core/compatibility.py` — 全属性の相性マトリクスを集約する core モジュール
  - conflicts は対称閉包、compatible は双方向和集合として正規化 (片側宣言で成立)
  - API: `load_matrix()` / `conflicts(a, b)` / `is_compatible(a, b)` / `relation(a, b)` / `check_blend([...])` / `to_dict()`
  - `python -m hersona.core.compatibility [--json]` で機械可読マトリクスをダンプ
- `scripts/validate.py` に相性関係の双方向整合チェックを追加 (conflict 非対称を警告、exit には非影響)
- `tests/test_compatibility.py` — 対称閉包 / 優先順位 / blend チェック / 実データ整合の回帰テスト (14 件)

### Added (ROADMAP ③ ローカルオーサリング基盤)
- `hersona/core/authoring.py` — ローカル属性オーサリングの core モジュール
  - `build_attribute()` / `override_attribute()` — 手書き YAML 不要の属性組み立て・既存属性の上書き
  - `save_attribute()` — スキーマ検証ゲート付き保存。ユーザー名前空間 (既定 `~/.hermes/attributes/`、`HERSONA_USER_DIR` で変更可) に分離
  - `assert_shareable()` / `find_proper_noun_risks()` — 固有名詞ガード (共有時のみ発動、ローカル保存は自由)
- `.gitignore` に `attributes/user/` を追加 (ユーザー作成データは公開対象外)
- `tests/test_authoring.py` — 検証ゲート / 上書き / 保存先分離 / 共有ガードの回帰テスト (17 件)

### Added (ROADMAP ② 評価・推薦システム)
- `hersona/core/recommend.py` — 属性推薦エンジンの core モジュール
  - `DEFAULT_QUIZ` / `score_answers()` — 診断クイズ回答を属性スコアに集計 (LLM 非依存の決定的マッピング)
  - `recommend()` — カテゴリごと最高スコア属性を選び、① 相性マトリクスで conflict を解決した推薦ブレンドを返す
  - 推薦結果 (`Recommendation.blend`) はそのまま multi 適用入力になり、③ で保存可能
- `tests/test_recommend.py` — スコア集計 / カテゴリ選定 / conflict 解決 / 既定クイズ整合の回帰テスト (9 件)

### PR 一覧 (Batch 2)
- #12: feat(attributes) — personality 6 種 (airhead / intellectual / hot_blooded / pragmatist / klutz / protective)
- #13: feat(attributes) — speech 5 種 (tomboy / gyaru / soft / mixed_dialect / mischievous)
- #14: feat(attributes) — archetype 2 種 (hikikomori / idol)

### PR 一覧 (Batch 3)
- #15: feat(schema) — visual / hobby enum 追加
- #16: feat(attributes) — hobby 5 種 (gamer / cooking / reading / music / sports)
- #17: feat(attributes) — visual 5 種 (petite / glamorous / silver_hair / animal_ears / glasses)
- #18: feat(attributes) — mysterious (personality) + princess_speech (speech) + conflicts 復活

### 検証 (Batch 2 + 3 累計)
- pytest: **255 passed** (v1.0.0 の 154 から +101)
- ruff: All checks passed
- validate.py: exit 0 (compatible 非対称 133件 = 設計上許容)
- generator 再生成後 byte 一致性: OK

## [1.0.0] - 2026-06-09

### Added (T1 / v1.0 基盤)
- `attributes/personality/` (10 種) / `attributes/speech/` (8 種) / `attributes/archetype/` (7 種) の計 25 種 属性テンプレート
- `schema/attribute.schema.json` (必須 6 フィールド + 任意 6 フィールド: `core_traits` / `speech_style` / `second_person` / `sentence_endings` / `catchphrases` / `tone`)
- `LICENSE-CC0.txt` — `attributes/` 配下はパブリックドメイン献呈
- `scripts/_oneoff/gen_v1_attributes.py` — 25 属性を Single Source of Truth から再生成
- `tests/test_attributes.py` — 25 属性のスキーマ整合 / ファイル名一致 / カテゴリ一致 / `data/` 非存在 / `validate.py` 実走を回帰検出

### Changed (T2 / hersona skill v3.0.0)
- `skills/hersona/SKILL.md` を v2.1.0 → v3.0.0 に全面改訂
  - コマンド体系: `/hersona <title> <character>` → `/hersona <category>/<name>`
  - 永続化フロー: `run_hersona.sh --persist` → `/hersona <category>/<name> persistent`
  - モード: `single` / `multi` / `persistent` / `reset` の 4 種
- `README.md` を 3 層ライセンス (code MIT / attributes CC0 / data CC-BY-SA 4.0) → 2 層 (code MIT / attributes CC0) に再構成
- `DISCLAIMER.md` を v0.x の個別キャラ引用前提 → v1.0 の属性テンプレート合成研究用に再構成
- `CONTRIBUTING.md` を「セリフ収集 → YAML 生成」フロー → 「属性テンプレート追加」フローに再構成

### Removed (T2)
- `data/` ディレクトリ配下すべてのファンアート二次創作プロファイル
- `scripts/persona_attach.py` — data/ 形式専用 CLI
- `scripts/run_hersona.sh` — data/ 形式専用永続化スクリプト
- `scripts/fix_persona_block.py` — persona_attach.py / run_hersona.sh の修復用
- `scripts/fix_melina_block.py` / `scripts/fix_toh_block.py` — 個別キャラ fix
- `scripts/apply_persona_to_config.py` — data/ 形式 register_call 専用
- `scripts/melina_cli.py` / `scripts/review_fewshot.py` / `scripts/persona_self_retire.py` / `scripts/persona_validate.py` / `scripts/reviewer_cli.py` — 個別キャラ依存
- `scripts/_oneoff/hide_and_clean.py` — data/ クリーンアップ用 one-off
- `prompts/generate_character.md` — data/<title>/<character>.yaml 生成プロンプト
- `schema/character.schema.json` — 旧キャラプロファイル用
- `schema/persona_attach.schema.json` — 旧 persona_attach_prompt 用
- `tests/test_legacy_score.py` — 旧 3 キャラ yaml 統合テスト

## [0.1.0] - 2026-06-07

### Added
- メリーナ / 遠坂凛 / パワー の persona_attach_prompt v1.1.0
- `scripts/persona_attach.py` CLI 5 サブコマンド（--list / --show / --check / --register / --detach）
- `scripts/validate.py` 自動スキーマ検証 + 4 鉄則チェック
- `scripts/persona_validate.py` 10 問シナリオ採点 + Markdown レポート
- `scripts/reviewer_cli.py` heuristic + LLM 採点
- `scripts/persona_self_retire.py` 人格自己退場（affective_targets ベース）
- `scripts/run_hersona.sh` 3 モード (test/persistent/reset) 対応
- `scripts/apply_persona_to_config.py` config.yaml 自動マージ
- `scripts/fix_persona_block.py` 汎用 YAML 修復
- `skills/hersona/SKILL.md` v2.0.0 3 モード対応
- `prompts/generate_character.md` キャラ生成プロンプト
- `.github/ISSUE_TEMPLATE/character_request.md` キャラ追加 Issue テンプレート
- `LICENSE` (CC BY-SA 4.0)
- `CONTRIBUTING.md` 1.9KB
- `.env.example`（ダミー値）
- `.gitignore` 補強（.env / .venv / キャッシュ系）

### Changed
- README.md をメリーナ専用説明から汎用サンプル形式に書き換え (#1)
- character.schema.json / persona_attach.schema.json 拡張
- persona_attach_prompt に 4 鉄則（first_person / second_person / sentence_endings / catchphrases）追加
- メリーナの attach_prompt 細部調整

### Fixed
- persistent モードの YAML 破壊バグ修正（汎用修復スクリプト fix_persona_block.py 追加）(#3)
- power persona_attach_prompt few-shot 人手レビュー指摘反映
- tohsaka persona_attach_prompt few-shot 人手レビュー指摘反映
- melina persona_attach_prompt few-shot 人手レビュー指摘反映
- 関連リンク削除 + クリーンアップ + リポ private 化（1b560c5）
- 実装不在スクリプトの言及を README から削除（2cc86c3）

### Deprecated
- persona_attach_prompt の `version` フィールド（schema_version への統合推奨、v2.0 で削除予定）

## Previous History

- 2026-05-XX: メリーナ initial commit
- 2026-05-XX: メリーナ用 4 鉄則（first_person / second_person / sentence_endings）追加
- 2026-05-XX: メリーナ用 catchphrases / core_traits フィールド追加
- 2026-05-XX: メリーナ口語版人格 / persona_attach 標準仕様
- 2026-05-XX: 4 つの鉄則 - first_person, second_person, sentence_endings フィールド追加
- 2026-06-XX: persistent モード用 config.yaml マージスクリプト
- 2026-06-XX: /hersona スキル追加（キャラ人格アタッチ）
- 2026-06-XX: メリーナ用 affective_targets 追加
- 2026-06-XX: 人格自己退場 (self-retire) 機能
- 2026-06-XX: fate tohsaka persona_attach_prompt 追加
- 2026-06-XX: persistent モード YAML 破壊バグ修正
- 2026-06-XX: persona_attach_prompt スキーマ v1.1.0 拡張と few-shot / check 評価改善
- 2026-06-XX: メリーナ few-shot 人手レビュー指摘反映
- 2026-06-XX: 遠坂凛 few-shot 人手レビュー指摘反映
- 2026-06-XX: 実装不在スクリプトの言及削除
- 2026-06-XX: persona_attach.py --register に --write を追加
- 2026-06-XX: パワー character profile
- 2026-06-XX: パワー few-shot 人手レビュー指摘反映
- 2026-06-XX: 関連リンク削除 + リポ private 化
- 2026-06-XX: .gitignore 補強 + .env.example 新設

[1.0.0]: https://github.com/shiro-0x/hersona/releases/tag/v1.0.0
[0.1.0]: https://github.com/shiro-0x/hersona/releases/tag/v0.1.0

### Added (Batch 2 / personality 6 種)
- `attributes/personality/airhead.yaml` — 天然 (状況把握遅・のんびりボケ)
  - core_traits 6 / catchphrases 5 / tone, weight=mild
  - conflicts_with: serious / intellectual / pragmatist
- `attributes/personality/intellectual.yaml` — インテリ (博識・分析的・脱線)
  - core_traits 6 / catchphrases 5 / tone, weight=moderate
  - conflicts_with: airhead / genki / playful
- `attributes/personality/hot_blooded.yaml` — 熱血 (正義感・大声・即行動)
  - core_traits 6 / catchphrases 5 / tone, weight=strong
  - conflicts_with: pragmatist / kuudere / stoic / pessimist
- `attributes/personality/pragmatist.yaml` — リアリスト (結果優先・効率・ドライ)
  - core_traits 6 / catchphrases 5 / tone, weight=moderate
  - conflicts_with: hot_blooded / genki / airhead / yandere
- `attributes/personality/klutz.yaml` — ドジっ子 (失敗多・愛嬌・立ち直り早い)
  - core_traits 6 / catchphrases 5 / tone, weight=mild
  - conflicts_with: pragmatist / intellectual
- `attributes/personality/protective.yaml` — 守護 (献身・世話焼き・過保護)
  - core_traits 6 / catchphrases 5 / tone, weight=moderate
  - conflicts_with: pragmatist / tsundere

合計: personality 10 → **16** (27 → **33** 属性)
generator SSOT 経由 (scripts/_oneoff/gen_v1_attributes.py) で追加。
generator docstring / `_check_category_counts()` / テスト (test_attributes / test_attach / test_cli / test_compatibility) / ドキュメント (README / SKILL.md / IMPLEMENTATION_GUIDE) の count 参照を同時更新。

### Added (Batch 2 / speech 5 種)
- `attributes/speech/tomboy.yaml` — ボーイッシュ (一人称「あたし」+ 荒っぽいタメ口 + 力強い語尾)
  - sentence_endings 5 / catchphrases 5 / tone, weight=moderate
  - conflicts_with: keigo / onee_kotoba / archaic / washi
- `attributes/speech/gyaru.yaml` — ギャル (テンション高 + 若者語 + 反復)
  - sentence_endings 5 / catchphrases 5 / tone, weight=moderate
  - conflicts_with: keigo / archaic / onee_kotoba / washi
- `attributes/speech/soft.yaml` — ソフト (甘え + 語尾伸ばし + 小声)
  - sentence_endings 5 / catchphrases 5 / tone, weight=moderate
  - conflicts_with: ore_boy / kansai_ben / keigo / gyaru
- `attributes/speech/mixed_dialect.yaml` — 方言ミックス (関西/東北/博多の散在)
  - sentence_endings 5 / catchphrases 5 / tone, weight=moderate
  - conflicts_with: keigo / archaic / washi
- `attributes/speech/mischievous.yaml` — 小悪魔 (からかい + 挑発 + 余裕)
  - sentence_endings 5 / catchphrases 5 / tone, weight=moderate
  - conflicts_with: airhead / serious / washi

### Changed (schema)
- `schema/attribute.schema.json` — `typical_value_range.pattern` を `^[0-9]\.[0-9]-[0-9]\.[0-9]$` から `^[0-1]\.[0-9]-[0-1]\.[0-9]$` に拡張
  (元は 0.X-0.Y のみ受理、tomboy の 0.4-0.8 を契機に全域カバーへ)。
  既存 27 属性の range (0.0-0.0 / 0.2-0.5 / 0.3-0.6 / 0.4-0.7 / 0.5-0.8 / 0.7-1.0) は全てマッチ継続。

合計: speech 10 → **15** (33 → **38** 属性)
generator SSOT 経由 (scripts/_oneoff/gen_v1_attributes.py) で追加。
generator docstring / `_check_category_counts()` / テスト 4 件 / ドキュメント 4 件
の count 参照 (33→38) を同時更新。

### Added (Batch 2 / archetype 2 種)
- `attributes/archetype/hikikomori.yaml` — 引きこもり (自宅中心・オンライン最大化)
  - core_traits 6 / catchphrases 5 / tone, weight=none
  - conflicts_with: genki / idol / hot_blooded
  - online/offline 二項対立を核、gamer_otaku との併用想定
- `attributes/archetype/idol.yaml` — アイドル (パフォーマー・公私ギャップ)
  - core_traits 6 / catchphrases 5 / tone, weight=none
  - conflicts_with: hikikomori / pessimist / stoic
  - 公私ギャップが核、switch との併用で on/off 切替トリガを明示

合計: archetype 7 → **9** (38 → **40** 属性)
generator SSOT 経由 (scripts/_oneoff/gen_v1_attributes.py) で追加。
generator docstring / `_check_category_counts()` / テスト 4 件 / ドキュメント 4 件
の count 参照 (38→40) を同時更新。

### Added (Batch 3 / hobby 5 種)
- `attributes/hobby/gamer.yaml` — ゲーム好き (実況・廃人)
  - core_traits 5 / catchphrases 3 / tone, weight=moderate
  - conflicts_with: [] (PR #18 で mysterious / kuudere を追加予定)
- `attributes/hobby/cooking.yaml` — 料理好き (家庭・世話焼き)
  - core_traits 5 / catchphrases 3 / tone, weight=moderate
  - conflicts_with: klutz / mischievous
- `attributes/hobby/reading.yaml` — 読書好き (本好き・想像力)
  - core_traits 5 / catchphrases 3 / tone, weight=mild
  - conflicts_with: genki / idol / hot_blooded
- `attributes/hobby/music.yaml` — 音楽好き (リズム・感情表現)
  - core_traits 5 / catchphrases 3 / tone, weight=moderate
  - conflicts_with: [] (PR #18 で mysterious / pessimist を追加予定)
- `attributes/hobby/sports.yaml` — スポーツ好き (運動・爽やか)
  - core_traits 5 / catchphrases 3 / tone, weight=moderate
  - conflicts_with: hikikomori / intellectual / klutz

合計: 40 → **45** 属性 (新カテゴリ `hobby` 5 種追加)
generator SSOT 経由 (scripts/_oneoff/gen_v1_attributes.py) で追加。
generator docstring / `_check_category_counts()` / テスト 4 件 / ドキュメント 4 件
の count 参照 (40→45) を同時更新。by_cat に visual=0, hobby=5 の assert 追加。

### Added (Batch 3 / visual 5 種)
- `attributes/visual/petite.yaml` — 小柄・可愛らしい (小柄・華奢・幼く見える)
  - core_traits 5 / catchphrases 3 / tone, weight=mild
  - conflicts_with: glamorous (PR #18 で神秘追加予定)
- `attributes/visual/glamorous.yaml` — グラマー・大人っぽい (存在感・色気)
  - core_traits 5 / catchphrases 3 / tone, weight=moderate
  - conflicts_with: petite (PR #18 で神秘追加予定)
- `attributes/visual/silver_hair.yaml` — 銀髪・神秘的 (幻想的・目立つ)
  - core_traits 5 / catchphrases 3 / tone, weight=mild
  - conflicts_with: genki / gyaru / idol (PR #18 で神秘追加予定)
- `attributes/visual/animal_ears.yaml` — 獣耳・尻尾 (身体性・非人間)
  - core_traits 5 / catchphrases 3 / tone, weight=moderate
  - conflicts_with: petite / glamorous (PR #18 で神秘追加予定)
- `attributes/visual/glasses.yaml` — 眼鏡・知的に (外すとギャップ)
  - core_traits 5 / catchphrases 3 / tone, weight=mild
  - conflicts_with: gyaru / idol (PR #18 で神秘追加予定)

### Added (Batch 3 新カテゴリ visual)
- `schema/attribute.schema.json` の `attribute_category.enum` に `visual` を追加
  (PR #15 で先行拡張済み、PR #16 で hobby と同時導入)
- 見た目カテゴリは personality とは独立した descriptor として運用
- 性格と「見た目」の二軸クロスで組み合わせの幅が一気に拡大

合計: 45 → **50** 属性 (新カテゴリ visual 5 種追加)
generator SSOT 経由 (scripts/_oneoff/gen_v1_attributes.py) で追加。
generator docstring / `_check_category_counts()` / テスト 4 件 / ドキュメント 4 件
の count 参照 (45→50) を同時更新。by_cat に visual=5 の assert 追加。

### Added (Batch 3 完結 / mysterious + princess_speech)
- `attributes/personality/mysterious.yaml` — ミステリアス (寡黙・含み・低く余韻)
  - core_traits 5 / catchphrases 3 / tone, weight=moderate
  - conflicts_with: genki / gyaru / idol / klutz
  - silver_hair (visual) との併用で神秘感の二重軸
- `attributes/speech/princess_speech.yaml` — 古風・お嬢様語 (ですわ / 候 / 上品)
  - sentence_endings 5 / catchphrases 5 / speech_style / second_person / tone, weight=moderate
  - conflicts_with: genki / ore_boy / kansai_ben / tomboy
  - Batch 2 の archaic (古風・文語) とは別属性: 「お嬢様」色濃い丁寧口調

### Changed (Batch 3 完結: conflicts 復活)
- PR #16 / #17 で一時的に空配列にしていた `conflicts_with` を `mysterious` 参照復活:
  - gamer (hobby) ↔ mysterious, kuudere
  - music (hobby) ↔ mysterious, pessimist
  - petite (visual) ↔ glamorous, mysterious
  - glamorous (visual) ↔ petite, mysterious
  - silver_hair (visual) ↔ genki, gyaru, idol, mysterious
  - animal_ears (visual) ↔ petite, glamorous, mysterious
  - glasses (visual) ↔ mysterious, gyaru, idol

合計: 50 → **52** 属性 (Batch 3 完結)
- personality 16 → 17 (+mysterious)
- speech 15 → 16 (+princess_speech)
- visual 5 (不変)
- hobby 5 (不変)
- archetype 9 (不変)

generator SSOT 経由 (scripts/_oneoff/gen_v1_attributes.py) で追加。
generator docstring / `_check_category_counts()` / テスト 4 件 / ドキュメント 4 件
の count 参照 (50→52) を同時更新。by_cat に personality=17, speech=16 assert 追加。
