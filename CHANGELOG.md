# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-06-07

### Added
- メリーナ（ELDEN RING）/ 遠坂凛（Fate/stay night）/ パワー（CHAINSAW MAN）の persona_attach_prompt v1.1.0
- `scripts/persona_attach.py` CLI 5 サブコマンド（--list / --show / --check / --register / --detach）
- `scripts/validate.py` 自動スキーマ検証 + 4鉄則チェック
- `scripts/persona_validate.py` 10問シナリオ採点 + Markdown レポート
- `scripts/reviewer_cli.py` heuristic + LLM 採点（v0.1.0 リリース時点のものは melina 専用ハードコードあり、T-fix にて修正予定）
- `scripts/persona_self_retire.py` 人格自己退場（affective_targets ベース）
- `scripts/run_hersona.sh` 3モード (test/persistent/reset) 対応
- `scripts/apply_persona_to_config.py` config.yaml 自動マージ
- `scripts/fix_persona_block.py` 汎用 YAML 修復（v0.1.0 リリース時点では melina/toh 個別 fix も併存）
- `skills/hersona/SKILL.md` v2.0.0 3モード対応
- `prompts/generate_character.md` キャラ生成プロンプト
- `.github/ISSUE_TEMPLATE/character_request.md` キャラ追加 Issue テンプレート
- `LICENSE` (CC BY-SA 4.0)
- `CONTRIBUTING.md` 1.9KB
- `.env.example`（ダミー値）
- `.gitignore` 補強（.env / .venv / キャッシュ系）

### Changed
- README.md をメリーナ専用説明から汎用サンプル形式に書き換え (#1)
- character.schema.json / persona_attach.schema.json 拡張
- persona_attach_prompt に 4鉄則（first_person / second_person / sentence_endings / catchphrases）追加
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
- 2026-05-XX: メリーナ用 4鉄則（first_person / second_person / sentence_endings）追加
- 2026-05-XX: メリーナ用 catchphrases / core_traits フィールド追加
- 2026-05-XX: メリーナ口語版人格 / persona_attach 標準仕様
- 2026-05-XX: 4つの鉄則 - first_person, second_person, sentence_endings フィールド追加
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
- 2026-06-XX: パワー (CHAINSAW MAN) character profile
- 2026-06-XX: パワー few-shot 人手レビュー指摘反映
- 2026-06-XX: 関連リンク削除 + リポ private 化
- 2026-06-XX: .gitignore 補強 + .env.example 新設

[0.1.0]: https://github.com/shiro-0x/hersona/releases/tag/v0.1.0
