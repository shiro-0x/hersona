---
about: 新規属性テンプレート追加提案 (attributes/<category>/<name>.yaml)
title: '[ATTRIBUTE] '
labels: attribute, needs-triage
assignees: ''
---

## 提案属性

- 属性名 (snake_case): ___
- カテゴリ: personality / speech / archetype のいずれか
- display_name_ja:
- display_name_en:
- weight_dimension: none / mild / moderate / strong のいずれか
- typical_value_range: 例: `0.4-0.7`

## 属性の根拠

- 既存 25 属性で不足する理由: ___
- アニメ・ゲーム・漫画・クリーチャーで広く見られる特性か: yes / no (理由: ___)
- 固有名詞・特定作品への依存がないか: yes / no (理由: ___)

## 想定する core_traits / catchphrases / tone

v1.0 では 6 フィールド (core_traits / speech_style / second_person / sentence_endings / catchphrases / tone) が任意追加可能。`tsundere` を雛形として参考に。

- core_traits (3-7 個): ___
- speech_style (1 行散文、speech カテゴリのみ): ___
- second_person (1 行 / 区切り、speech カテゴリのみ): ___
- sentence_endings (3 個以上、speech カテゴリのみ): ___
- catchphrases (3-15 個、全カテゴリ): ___
- tone (1 行散文、全カテゴリ): ___

## 互換性

- compatible_archetypes (併用 OK な archetype 名リスト): ___
- conflicts_with (排他が想定される属性名リスト): ___
- tags (横断検索タグ): ___

## examples 案 (AI エージェント活用 5 パターン)

1. システムプロンプト注入: ___
2. 強度調整 (weight=mild): ___
3. 強度調整 (weight=strong): ___
4. 互換性チェック (compatible_archetypes との組み合わせ): ___
5. NG パターン (conflicts_with 該当との同時付与): ___

## 想定工数

- examples / core_traits 設計: N 時間
- gen_v1_attributes.py への追記: N 時間
- pytest 80 → 81+ への拡張: N 時間
- 検証 (validate.py + pytest): N 分

## 関連 Issue

Closes # / refs #
