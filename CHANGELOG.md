# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
