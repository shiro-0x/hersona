# Phase 0 詳細設計: hersona 側の前提整備

> 実装先: **hersona リポジトリ (本リポジトリ)**。duet 着手前に完了させる。
> 4 タスクは独立しており並行実装可。

---

## P0-1: PyPI 公開

### 作業内容

1. `pyproject.toml` メタデータ整備:
   - `project.name = "hersona"` (PyPI で名前確保。取得不可なら `hersona-attributes` にフォールバックし、P0-2 の文書に正式パッケージ名を記載)
   - `description` / `readme = "README.md"` / `license` / `keywords` /
     `classifiers` (Python :: 3.11+, License :: OSI Approved :: MIT License) /
     `urls` (Homepage, Repository, Changelog)
   - `attributes/` データの同梱確認: wheel に `attributes/**/*.yaml` と
     `schema/attribute.schema.json` が含まれること (`[tool.hatch.build]` 等で明示)。
     **重要**: `hersona.core.attach.PUBLIC_ATTRIBUTES_ROOT` がインストール環境でも
     解決できることを確認し、必要なら `importlib.resources` ベースに修正する
2. GitHub Actions による Trusted Publishing:
   - `.github/workflows/publish.yml`: `v*` タグ push で `uv build` → `pypa/gh-action-pypi-publish`
   - PyPI 側で Trusted Publisher (GitHub OIDC) を登録 (手作業、オーナーが実施)
3. バージョン方針: 現行 `1.2.0` から semver。公開 API (P0-2) の破壊的変更は major

### 受け入れ基準

- [ ] クリーンな venv で `pip install hersona` → `hersona list` が 64 属性を表示
- [ ] `python -c "from hersona.core import render_blend; print(render_blend(['tsundere']).prompt[:80])"` が動く
- [ ] タグ push で自動公開される (初回は手動 `uv publish` でも可)

### テスト

- `tests/test_packaging.py`: wheel ビルド後、zip 内に `attributes/personality/tsundere.yaml` が存在することを検証

---

## P0-2: 公開 API の明文化

### 作業内容

`docs/PUBLIC_API.md` を新設し、以下を「公開 API (semver 対象)」と宣言。
README の Contributing 節からリンクする。

```
hersona.core (公開エクスポート = __init__.__all__ 全体):
  attach:        BlendResult, available_attributes, load_attribute, render_blend
  compatibility: Attribute, CompatibilityMatrix, Relation, load_matrix
  weight:        WeightLevel, WEIGHT_GUIDANCE, catchphrase_subset, coerce_level,
                 suggest_weight, weight_for_score (P0-3 で追加)
  intensity:     IntensityReport, expected_band, format_report, measure_intensity,
                 verify_intensity
  recommend:     DEFAULT_QUIZ, QuizQuestion, QuizOption, Recommendation,
                 load_quiz, score_answers, recommend
  authoring:     build_attribute, override_attribute, validate_attribute,
                 save_attribute, list_user_attributes, user_attributes_root,
                 find_proper_noun_risks, assert_shareable,
                 AuthoringError, ValidationGateError, ShareGuardError
```

各シンボルに 1 行説明と、duet が依存する主要シグネチャを明記:

```python
render_blend(names: list[str], *, matrix=None, public_root=None, user_root=None,
             weight: str | WeightLevel = WeightLevel.MODERATE) -> BlendResult
# BlendResult: .names .attributes(list[dict]) .conflicts(list[tuple[str,str]]) .prompt(str)

verify_intensity(text: str, attributes: list[dict],
                 level: str | WeightLevel) -> IntensityReport | None
# None = speech 属性なしで測定スキップ。.score .band .status("pass"|"under"|"over")

CompatibilityMatrix.check_blend(names: list[str]) -> list[tuple[str, str]]
```

### 受け入れ基準

- [ ] `docs/PUBLIC_API.md` が存在し、`__all__` と過不足なく一致 (テストで担保)
- [ ] `tests/test_public_api.py`: `__all__` の全シンボルが import 可能かつ文書に記載されている

---

## P0-3: 連続値スコア → weight 写像 API

### 背景

既存 `suggest_weight(score)` は recommend の適合度スコア (0〜3+) 用。duet の
「感情温度ダイヤル」(ギャルゲーパックでは好感度) は **0-100 の連続値**で、
シーンを跨いで頻繁に再評価されるため、**閾値境界での振動を防ぐヒステリシス**が必要。

### 仕様 (`hersona/core/weight.py` に追加)

```python
def weight_for_score(
    score: float,
    *,
    previous: WeightLevel | None = None,
    thresholds: tuple[float, float, float] = (25.0, 55.0, 85.0),
    hysteresis: float = 5.0,
) -> WeightLevel:
    """0-100 の連続値スコアを WeightLevel に写像する。

    - score < t1 → NONE / < t2 → MILD / < t3 → MODERATE / それ以上 → STRONG
    - previous を渡すと、レベルが「変わる」には境界を hysteresis 分超える必要がある
      (例: previous=MILD, t2=55 のとき、MODERATE 昇格は score >= 60、
       NONE 降格は score < 20)
    - score は 0-100 にクランプ。thresholds は昇順でなければ ValueError
    """
```

`__init__.py` の re-export と `__all__` に追加。`WEIGHT_GUIDANCE` は変更しない。

### テスト (`tests/test_weight.py` に追加)

1. 境界値: 24.9→NONE / 25→MILD / 55→MODERATE / 85→STRONG
2. クランプ: -10→NONE / 150→STRONG
3. ヒステリシス昇格: previous=MILD, score=57 → MILD のまま / score=60 → MODERATE
4. ヒステリシス降格: previous=MODERATE, score=52 → MODERATE のまま / score=49 → MILD
5. previous=None は素の閾値判定
6. thresholds 非昇順で ValueError

### 受け入れ基準

- [ ] 上記 6 ケースを含むテストが追加されパス
- [ ] `docs/PUBLIC_API.md` に追記

---

## P0-4: ROADMAP 追記

`ROADMAP.md` のワークストリーム節に以下を追加するだけの小タスク:

```markdown
### ④ duet — エージェント協働の自動制作スタジオ (別リポジトリ)

監督(ユーザー)/シナリオライター/ナレーター/アクター構成のシーン制作システム。
hersona はライブラリとして依存される (公開 API は docs/PUBLIC_API.md)。
計画: docs/DUET_PLAN.md / 詳細設計: docs/duet/
hersona 側の前提タスク: P0-1〜P0-3 (docs/duet/PHASE0_HERSONA_PREP.md)
```
