# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added (Batch 4: speech / personality 拡張)
- 属性 7 種を追加。属性数 52 → **59** (personality 17→20 / speech 16→20)
  - speech: `seductive`(誘惑・色気)/ `stutter`(吃り・言い淀み)/ `blunt`(ぶっきらぼう)/ `theatrical`(芝居がかり)
  - personality: `chuunibyou`(中二病)/ `narcissist`(ナルシスト)/ `optimist`(楽観的)
  - 新カテゴリは作らず既存 speech / personality に純加算 (schema / core 不変)
  - 手書き YAML で追加(凍結生成物 `scripts/_oneoff/gen_v1_attributes.py` は Batch 3 完結スナップショットのため不変)
- `docs/BATCH4_DECISIONS.md` — Batch 4 の設計合意の記録(積み残し判断 + 新規 5 種の方向性)
- テストの数量アサーションを 52 → 59(personality 20 / speech 20)に更新
- `hersona recommend` 診断クイズに Batch 4 の 7 属性への到達経路を追加
  - 新設 2 問: `tone`(声や口調 → seductive / stutter / blunt / theatrical)/ `selfview`(自分の捉え方 → chuunibyou / narcissist / optimist)
  - `test_recommend.py` に到達経路テスト 7 件を追加

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
