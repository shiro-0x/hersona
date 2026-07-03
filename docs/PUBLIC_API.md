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
| `render_blend(names, *, matrix=None, public_root=None, user_root=None, weight=WeightLevel.MODERATE, use_case=None, use_case_root=None) -> BlendResult` | 複数属性をシステムプロンプト注入ブロックへ合成。conflict は警告として併記。`use_case` 指定時は英語 Operating Mode ブロックを末尾に追加 |
| `BlendResult` | `.names: list[str]` / `.attributes: list[dict]` / `.conflicts: list[tuple[str, str]]` / `.prompt: str` |

## use cases / Operating Modes — 用途別プロンプト規律

| シンボル | 説明 |
|---|---|
| `available_use_cases(*, root=None, user_root=None) -> dict[str, dict]` | 利用可能な use-case / Operating Mode prompt pack の `{use_case_id: metadata}` を返す。metadata は `display_name` / `description` / `category` / `risk_level` / `tags` / `i18n` / `source` (`public` or `user`) / `path`。user パックは同 ID の public パックを上書きし、同一ルート内の重複 ID は `UseCaseError` |
| `load_use_case(name, *, root=None, user_root=None) -> dict` | use-case prompt pack を ID でロードし、`schema/use_case.schema.json` で検証する (user root が public より優先)。見つからなければ `KeyError` |
| `validate_use_case(data) -> None` | use-case prompt pack dict を検証。schema 違反なら `UseCaseError`。`risk_level` が `medium` / `high` のパックは `safety` セクション必須 |
| `render_use_case_block(data) -> str` | use-case prompt pack を英語の `## Operating Mode: ...` 注入ブロックへレンダリングする |
| `user_use_cases_root() -> Path` | ユーザー作成 use-case のルート。`HERSONA_USER_USE_CASES_DIR` 環境変数、無ければ `~/.hermes/use_cases` |
| `UseCaseError` | use-case prompt pack の不正 (schema 違反 / 重複 ID) を表す `ValueError` 派生例外 |

## export — 他フレームワーク向けエクスポート

| シンボル | 説明 |
|---|---|
| `export_blend(names, *, weight=WeightLevel.MODERATE, fmt="json", matrix=None, public_root=None, user_root=None) -> str` | ブレンドを `json` (構造化) / `messages` (`[{role:system,content}]`) / `markdown` (注入ブロック素文) / `openai_assistants` / `langchain_system_message` へ変換。`render_blend` を再利用 |
| `EXPORT_FORMATS` | 対応フォーマットのタプル (`("json", "messages", "markdown", "openai_assistants", "langchain_system_message")`) |
| `export_for_openai_assistants(names, *, weight=WeightLevel.MODERATE, matrix=None, public_root=None, user_root=None) -> str` | OpenAI Assistants API の `instructions` フィールド用 JSON (`{"model": "gpt-4o", "instructions": ..., "metadata": {"hersona_*": ...}}`)。キャラ固定フィールド (`first_mes` / `scenario`) は生成しない |
| `export_for_langchain_system_message(names, *, weight=WeightLevel.MODERATE, matrix=None, public_root=None, user_root=None) -> str` | LangChain `SystemMessage` 互換 JSON (`{"type": "system", "content": ..., "response_metadata": {"hersona_*": ...}}`) |

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
| `normalize_catchphrase(item) -> dict` | 口癖要素 (str or `{phrase, when}` dict) を `{phrase, when}` dict に正規化 (B: トリガ注記対応) |
| `catchphrase_subset(catchphrases, level) -> list[dict]` | 強度に応じた口癖の露出サブセット。各要素は `normalize_catchphrase` で `{phrase, when}` に正規化済み |
| `suggest_weight(score: float) -> WeightLevel` | **recommend の適合度スコア (0〜3+)** から推奨強度を推定 |
| `weight_for_score(score, *, previous=None, thresholds=(25, 55, 85), hysteresis=5.0) -> WeightLevel` | **0-100 の連続値スコア**を強度へ写像。`previous` 指定時はヒステリシス付き (境界 ± hysteresis を超えるまでレベル維持)。duet の感情温度/好感度ダイヤル用 |

## intensity — 出力強度の決定的採点

| シンボル | 説明 |
|---|---|
| `measure_intensity(text, attributes) -> IntensityReport \| None` | 表層指標 (語尾一致 60% + 口癖密度 40%) で 0-100 採点。speech 属性が無ければ `None` |
| `verify_intensity(text, attributes, level) -> IntensityReport \| None` | 採点 + 期待バンド比較。`report.status` は `"pass" / "under" / "over"` |
| `expected_band(level) -> tuple[int, int]` | 強度ごとの期待スコア帯 |
| `format_report(report, level) -> str` | 人間可読の 1 行レポート |
| `pre_response_check_prompt(names, weight_level, last_response=None, lang="en") -> str` | 強度レベル別の自己監査プロンプトを返す。`measure --strict` / `--check-prompt` で使用 |
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

## presets — ブレンドプリセットのローカル保存

| シンボル | 説明 |
|---|---|
| `Preset` | `.name` / `.attributes: list[str]` / `.weight` / `.note` / `.created` / `.tags` |
| `save_preset(name, attributes, *, weight="moderate", note="", tags=None, root=None, overwrite=False) -> Path` | ブレンド (属性名リスト + 強度) を `~/.hermes/presets/<name>.yaml` に保存 |
| `load_preset(name, *, root=None) -> Preset` | 名前からプリセットを読み込む。無ければ `PresetError` |
| `list_presets(root=None) -> list[Preset]` | 保存済みプリセットを名前昇順で列挙 |
| `delete_preset(name, *, root=None) -> Path` | プリセットを削除 |
| `presets_root() -> Path` | プリセット保存ルート (`HERSONA_PRESETS_DIR` か属性ルート兄弟の `presets/`) |
| `PresetError` | プリセット処理の例外 |

## soul — SOUL.md 永続化 (Hermes One 公式仕様への書き出し)

| シンボル | 説明 |
|---|---|
| `SoulRenderResult` | `.content` / `.output_path` / `.blend_names` / `.weight` / `.lang` / `.name` / `.memory` / `.use_case` |
| `render_soul(names, *, weight="moderate", name="Libra", matrix=None, public_root=None, user_root=None, memory=None, use_case=None, use_case_root=None) -> str` | blend を SOUL.md 形式 (公式 4 要素: name / personality / tone / behavioral guidelines) の markdown 文字列にレンダリングする。`use_case` 指定時は `## Operating Mode` も生成する。conflict 検出で `ValueError` |
| `write_soul(output, names, *, weight="moderate", name="Libra", append=False, overwrite=False, force=False, matrix=None, public_root=None, user_root=None, memory=None, use_case=None, use_case_root=None) -> SoulRenderResult` | SOUL.md を `output` に書き出す。既存ファイルがあれば既定で `FileExistsError` ( `overwrite` / `force` / `append` で制御)。`<!-- hersona:gen-end -->` より下のユーザー追記は `overwrite` / `force` 再生成時に保持する |
| `default_soul_path(profile="default") -> Path` | `~/.hermes/SOUL.md` を返す (`profile` は後方互換で受け取るが現在は無視) |

## persistent — SOUL.md 自動書き出し + config.yaml ブロック表示

| シンボル | 説明 |
|---|---|
| `PersistentResult` | `.persona_name` / `.config_yaml_block` / `.soul_result` / `.config_write_result` / `.apply_result` / `.skipped: dict` / `.memory` / `.use_case` |
| `run_persistent(names, *, weight="moderate", profile="default", without_soul=False, without_config=False, force=False, config_yaml_output=None, auto_config=False, config_path=None, apply=False, memory=None, memory_file=None, use_case=None) -> PersistentResult` | persistent モードを実行。SOUL.md 自動書き出し (既定 ON) + `config.yaml` 追記用 YAML ブロック生成。`use_case` 指定時は config ブロックと SOUL.md の両方に Operating Mode を含める |

## self_intro — 公開向け自己紹介の決定論 lint

| シンボル | 説明 |
|---|---|
| `IntroViolation` | `.rule` / `.message` / `.excerpt` |
| `IntroLintResult` | `.ok` / `.violations` — `.to_dict()` で JSON 化 |
| `lint_self_intro(text, *, allow_handles=None, canonical=False) -> IntroLintResult` | `docs/guides/self-introduction.*` の機械チェック (AI 自称・メタ・未許可 @ など)。CLI: `hersona lint-intro` |
| `merge_self_intro_guide(memory, *, lang="ja") -> dict[str, str] \| None` | 未設定の `self_intro_style` / `privacy_inner_circle` をガイドから補完 |
| `lint_memory_self_intro_canonical(memory, *, allow_handles=None, canonical=True)` | memory 内 `self_intro_canonical` の lint (`None` = キーなし) |
| `self_intro_guide_defaults(lang="ja") -> dict[str, str]` | ガイド由来の 2 キーだけのテンプレート |

`soul` / `persistent` CLI: `--with-self-intro-guide`, `--lint-self-intro`, `--lint-self-intro-strict`, `--allow-handle` (repeatable).

## データの所在 (参考)

インストール形態によらず、属性 (`attributes/`) とスキーマ (`schema/attribute.schema.json`)
はライブラリが内部で解決する (リポジトリ直置き → wheel 同梱 `hersona/data/` の順)。
外部プロジェクトがパスを直接組み立てる必要はない。

## 互換性ポリシー

- 公開シンボルの削除・シグネチャの非互換変更: **major** リリース
- 公開シンボルの追加・キーワード引数の追加 (既定値あり): **minor** リリース
- 属性データの追加・文言修正: **minor / patch** リリース
- `attributes/` の属性削除・`attribute_name` 変更はデータ互換性の破壊とみなし **major**
