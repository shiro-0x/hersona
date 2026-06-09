## 変更内容

- [ ] 新規属性追加 (`attributes/<category>/<name>.yaml` を `gen_v1_attributes.py` に追記)
- [ ] 既存属性更新 (修正内容: ____)
- [ ] schema 拡張 (`schema/attribute.schema.json`)
- [ ] スクリプト修正 (`scripts/____.py`)
- [ ] ドキュメント修正 (`README.md` / `CONTRIBUTING.md` / `CHANGELOG.md` / `skills/hersona/SKILL.md`)
- [ ] テスト追加・修正 (`tests/test_attributes.py`)
- [ ] その他（詳細: ____）

## 属性追加時のチェックリスト（`gen_v1_attributes.py` に追記する場合のみ）

- [ ] `attribute_name` が `^[a-z][a-z0-9_]*$` パターンに一致
- [ ] ファイル名と `attribute_name` が完全一致
- [ ] カテゴリ別数量制約 (personality 10 / speech 8 / archetype 7) 維持 (Round 1 確定 25 属性)
  - 増減させる場合は別 Issue で議論 (本 PR では 25 属性の維持を期待)
- [ ] `attribute_category` が `personality` / `speech` / `archetype` のいずれか
- [ ] `display_name_ja` / `display_name_en` 両方記載
- [ ] `weight_dimension` が `none` / `mild` / `moderate` / `strong` のいずれか
- [ ] `description_ja` / `description_en` 両方記載
- [ ] `examples` が 1 件以上 (5 件推奨: 注入 / 強度調整 x2 / 互換性 / NG)
- [ ] `compatible_archetypes` / `conflicts_with` の参照先属性が `attributes/` 配下に実在
- [ ] 固有名詞・特定作品を含まない (Round 1 仕様遵守)
- [ ] `_check_uniqueness` (attribute_name 重複) / `_check_category_counts` (数量制約) / `_check_compat_refs` (参照整合) を `gen_v1_attributes.py` 起動時チェックで担保
- [ ] 任意 6 フィールド (`core_traits` / `speech_style` / `second_person` / `sentence_endings` / `catchphrases` / `tone`) のうち、属性カテゴリに応じて必要なものを投入
  - personality: `core_traits` (3-7 個) + `catchphrases` (1-15 個) + `tone` (1 行)
  - speech: `speech_style` + `second_person` + `sentence_endings` + `catchphrases` + `tone`
  - archetype: `catchphrases` + `tone`
- [ ] 1 コミット = 1 属性（コミットメッセージ: `feat: <attribute_name> <category> attribute (T3 / Round N)`）

## 既存属性更新の場合

- [ ] 更新ファイル: `attributes/<category>/<name>.yaml`
- [ ] 更新内容（修正前 → 修正後）: ____
- [ ] `gen_v1_attributes.py` の ATTRIBUTES リスト修正が伴っている
- [ ] 24 残属性の量産は含まない (Round 3 でユーザー承認後に別途着手)

## 検証

- [ ] `python scripts/validate.py` 出力: 25 ファイル、エラー 0
- [ ] `pytest` 出力: 80+ ケース PASS
- [ ] `git diff --stat` の要約: ____
- [ ] `gen_v1_attributes.py` 起動時チェック (`_check_uniqueness` / `_check_category_counts` / `_check_compat_refs`) が緑

## 関連 Issue

Closes #____ / refs #____
