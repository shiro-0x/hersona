# hersona 公開 API (semver 対象)

> 本文書に列挙するシンボルが hersona の**公開 API** であり、semver の対象である。
> 破壊的変更は major バージョンでのみ行う。`_` 接頭辞のモジュール・関数、および
> ここに記載のないシンボルは内部実装であり、予告なく変更されうる。
>
> 外部プロジェクト (hersona-duet 等) は `hersona.core` の公開エクスポートのみを
> import すること。整合性は `tests/test_public_api.py` で機械的に担保される。

## インポート元

すべて `hersona.core` から import する (`hersona/core/__init__.py` の `__all__` と一致):

```python
from hersona.core import render_blend, load_matrix, verify_intensity, weight_for_score
```

## attach / blend — 属性の解決と注入ブロック合成

| シンボル | 説明 |
|---|---|
| `available_attributes(*, public_root=None, user_root=None) -> dict[str, dict]` | 利用可能な属性の `{name: {category, source, path}}`。user 名前空間が公開属性と同名なら user 優先 |
| `load_attribute(name, *, public_root=None, user_root=None) -> dict` | 属性名から YAML を解決して dict を返す。見つからなければ `KeyError` |
| `render_blend(names, *, matrix=None, public_root=None, user_root=None, weight=WeightLevel.MODERATE) -> BlendResult` | 複数属性をシステムプロンプト注入ブロックへ合成。conflict は警告として併記 |
| `BlendResult` | `.names: list[str]` / `.attributes: list[dict]` / `.conflicts: list[tuple[str, str]]` / `.prompt: str` |

## compatibility — 相性マトリクス

| シンボル | 説明 |
|---|---|
| `load_matrix(attributes_root=None) -> CompatibilityMatrix` | 全属性の相性関係をロード |
| `CompatibilityMatrix` | `.attributes` / `.is_compatible(a, b)` / `.conflicts(a, b)` / `.relation(a, b)` / `.check_blend(names) -> list[tuple[str, str]]` |
| `Relation` | 関係の列挙 (compatible / conflict / neutral) |
| `Attribute` | マトリクス内の属性ビュー |

## weight — 強度ダイヤル

| シンボル | 説明 |
|---|---|
| `WeightLevel` | `NONE / MILD / MODERATE / STRONG` (StrEnum。schema の `weight_dimension` と対応) |
| `WEIGHT_GUIDANCE: dict[WeightLevel, str]` | 各強度のプロンプト注入ガイダンス文 |
| `coerce_level(value) -> WeightLevel` | 文字列 / WeightLevel を正規化 |
| `catchphrase_subset(catchphrases, level) -> list[str]` | 強度に応じた口癖の露出サブセット |
| `suggest_weight(score: float) -> WeightLevel` | **recommend の適合度スコア (0〜3+)** から推奨強度を推定 |
| `weight_for_score(score, *, previous=None, thresholds=(25, 55, 85), hysteresis=5.0) -> WeightLevel` | **0-100 の連続値スコア**を強度へ写像。`previous` 指定時はヒステリシス付き (境界 ± hysteresis を超えるまでレベル維持)。duet の感情温度/好感度ダイヤル用 |

## intensity — 出力強度の決定的採点

| シンボル | 説明 |
|---|---|
| `measure_intensity(text, attributes) -> IntensityReport \| None` | 表層指標 (語尾一致 60% + 口癖密度 40%) で 0-100 採点。speech 属性が無ければ `None` |
| `verify_intensity(text, attributes, level) -> IntensityReport \| None` | 採点 + 期待バンド比較。`report.status` は `"pass" / "under" / "over"` |
| `expected_band(level) -> tuple[int, int]` | 強度ごとの期待スコア帯 |
| `format_report(report, level) -> str` | 人間可読の 1 行レポート |
| `IntensityReport` | `.score` / `.endings_rate` / `.catchphrase_hits` / `.band` / `.status` |

## recommend — 診断クイズ → 推薦

| シンボル | 説明 |
|---|---|
| `DEFAULT_QUIZ` / `DEFAULT_QUIZ_PATH` / `RECOMMEND_THRESHOLDS` | 既定クイズ (ja) と閾値定数 |
| `QuizQuestion` / `QuizOption` / `WeightMagnitude` | クイズのデータ型 |
| `load_quiz(path=None) -> list[QuizQuestion]` | クイズのロード |
| `score_answers(answers, quiz=None) -> dict[str, float]` | 回答 → 属性スコア |
| `recommend(answers, ...) -> Recommendation` | conflict 解決済みの推薦ブレンド (`.blend` は `render_blend` 入力互換) |

## authoring — ローカル属性の作成 (検証ゲート付き)

| シンボル | 説明 |
|---|---|
| `build_attribute(...) -> dict` / `override_attribute(base, **fields) -> dict` | 属性 dict の組み立て / 既存属性の上書き派生 |
| `validate_attribute(data) -> list[str]` | スキーマ検証 (エラーメッセージのリスト) |
| `save_attribute(data, *, ...) -> Path` | ユーザー名前空間へ保存。スキーマ違反は `ValidationGateError` |
| `list_user_attributes()` / `user_attributes_root()` | ユーザー名前空間の列挙 / ルート |
| `find_proper_noun_risks(data) -> list[str]` / `assert_shareable(data)` | 固有名詞リスク検出 / **共有時のみ**のガード (`ShareGuardError`) |
| `AuthoringError` / `ValidationGateError` / `ShareGuardError` | 例外階層 |

## データの所在 (参考)

インストール形態によらず、属性 (`attributes/`) とスキーマ (`schema/attribute.schema.json`)
はライブラリが内部で解決する (リポジトリ直置き → wheel 同梱 `hersona/data/` の順)。
外部プロジェクトがパスを直接組み立てる必要はない。

## 互換性ポリシー

- 公開シンボルの削除・シグネチャの非互換変更: **major** リリース
- 公開シンボルの追加・キーワード引数の追加 (既定値あり): **minor** リリース
- 属性データの追加・文言修正: **minor / patch** リリース
- `attributes/` の属性削除・`attribute_name` 変更はデータ互換性の破壊とみなし **major**
