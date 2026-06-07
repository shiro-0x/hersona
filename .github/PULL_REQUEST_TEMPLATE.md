## 変更内容

- [ ] 新規キャラ追加 (data/<作品>/<キャラ>.{yaml,md})
- [ ] 既存プロフィール更新（修正内容: ____）
- [ ] スクリプト修正 (scripts/____.py)
- [ ] ドキュメント修正 (docs/____.md / CONTRIBUTING.md / README.md)
- [ ] スキーマ変更 (schema/____.json)
- [ ] その他（詳細: ____）

## キャラ追加時のチェックリスト（新規キャラの場合のみ）

- [ ] data/<作品>/_index.md のテーブルに新キャラ行を追加
- [ ] セリフ 30-50 本収集、うち 10-20 本を .md で引用
- [ ] 引用元 URL がすべて license_source に列挙されている
- [ ] セリフ本文は原文ママ（翻訳・改変なし）
- [ ] character_id が ^[a-z0-9-]+$ パターンに一致
- [ ] license: CC-BY-SA-4.0（固定）
- [ ] personality.first_person / second_person / sentence_endings / catchphrases の 4 鉄則すべてにセリフ根拠
- [ ] core_traits は 3-7 個
- [ ] python scripts/validate.py がエラーなしで完走
- [ ] python scripts/persona_validate.py <作品> <キャラ> で persona_attach 検証
- [ ] 該当キャラの persona_attach_prompt を新規追加した場合、register_call / detach_command / forbidden_words / required_words が schema v1.1.0 準拠
- [ ] 1 コミット = 1 キャラ（コミットメッセージ: add: <キャラ名> (<作品名>) character profile）

## セリフ誤り修正の場合

- [ ] 該当行番号（data/<作品>/<キャラ>.md:NN）
- [ ] 修正前 → 修正後
- [ ] 出典（公式 / Wiki 改訂 / 単行本●巻●ページ）
- [ ] 関連 Issue 番号（line_correction テンプレートで作成した issue）

## 検証

- [ ] python scripts/validate.py 出力: ____
- [ ] git diff --stat の要約: ____
- [ ] pre-commit run --all-files が緑（Wave 2 で pre-commit 設定後）

## 関連 Issue

Closes #____ / refs #____
