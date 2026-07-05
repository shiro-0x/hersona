"""hersona bench — ペルソナ維持ベンチマークハーネス。

外部レビュー(2026-07-04)が指摘した「人格維持・token量の定量比較がない」への
対応。`docs/reviews/2026-07-04-external-review-response.md` §P1-1 参照。

設計方針:
- **LLM を呼び出さない。** hersona は PyPI 配布ライブラリであり、特定 LLM
  SDK / API キーへの依存を持たない (既存の `hersona.core` 全体の方針と同じ)。
  本モジュールは「あなたが実際に生成したトランスクリプト (応答文字列のリスト)」
  を受け取って採点するだけ。「hersona あり/なし」の比較自体はユーザーが
  自分の環境で 2 回モデルを呼んで得た 2 本のトランスクリプトを、それぞれ
  ``score_transcript`` に通すことで行う (recipe は docs/BENCHMARKS.md)。
- **採点は `hersona.core.intensity.verify` を再利用する** (表層指標、決定的、
  再現可能)。LLM-judge のような品質評価は行わない — それは主張しない。
- ``demo_transcript`` は `sample_dialogue.generate_samples` (catchphrases から
  直接導出されるテンプレ文) を使った自己完結スモークテスト用。catchphrases
  そのものを採点するため常に高スコアになりがちな tautological な性質を持つ。
  ハーネスが正しく動くことの確認用であり、実際の品質比較の代用にはしない。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from hersona.core.attach import load_attribute, render_blend
from hersona.core.compatibility import CompatibilityMatrix
from hersona.core.i18n import tr
from hersona.core.intensity import IntensityReport, verify
from hersona.core.weight import WeightLevel, coerce_level

# CC0 サンプルシナリオは repo 直下 benchmarks/scenarios/ に同梱 (属性同様 CC0)
REPO_SCENARIOS_ROOT = Path(__file__).resolve().parent.parent.parent / "benchmarks" / "scenarios"


@dataclass(frozen=True)
class BenchScenario:
    """会話シナリオ (ユーザー発話列)。応答は含まない — ユーザーが自分の LLM で生成する。"""

    id: str
    turns: list[str]
    description: str = ""


def load_scenario(path: Path) -> BenchScenario:
    """YAML からシナリオをロードする (``id`` / ``turns`` 必須、``description`` 任意)。"""
    src = Path(path)
    if not src.exists():
        raise FileNotFoundError(tr("bench.scenario_not_found", path=src))
    data = yaml.safe_load(src.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "id" not in data or "turns" not in data:
        raise ValueError(tr("bench.scenario_bad_format", path=src))
    turns = [str(t) for t in data["turns"]]
    if not turns:
        raise ValueError(tr("bench.scenario_empty_turns", path=src))
    return BenchScenario(id=str(data["id"]), turns=turns, description=str(data.get("description", "")))


def available_scenarios(root: Path | None = None) -> dict[str, Path]:
    """同梱シナリオ (``benchmarks/scenarios/*.yaml``) を ``{id: path}`` で返す。"""
    src_root = root or REPO_SCENARIOS_ROOT
    out: dict[str, Path] = {}
    if not src_root.exists():
        return out
    for yml in sorted(src_root.glob("*.yaml")):
        try:
            scenario = load_scenario(yml)
        except (ValueError, FileNotFoundError):
            continue
        out[scenario.id] = yml
    return out


@dataclass
class TurnScore:
    """トランスクリプト中 1 ターンの採点結果。"""

    turn_index: int
    text: str
    report: IntensityReport | None  # None = 採点不能 (speech 属性未到達など)


@dataclass
class BenchResult:
    """``score_transcript`` の結果。"""

    blend: list[str]
    weight: WeightLevel
    turn_scores: list[TurnScore] = field(default_factory=list)
    scenario_id: str | None = None

    @property
    def scored_turns(self) -> list[TurnScore]:
        """採点できたターンのみ (report is not None)。"""
        return [t for t in self.turn_scores if t.report is not None]

    @property
    def maintenance_rate(self) -> float | None:
        """期待バンド内 (status == "pass") だったターンの比率。採点対象 0 件なら None。"""
        scored = self.scored_turns
        if not scored:
            return None
        passed = sum(1 for t in scored if t.report.status == "pass")
        return passed / len(scored)

    @property
    def mean_score(self) -> float | None:
        """採点対象ターンの平均スコア (0-100)。採点対象 0 件なら None。"""
        scored = self.scored_turns
        if not scored:
            return None
        return sum(t.report.score for t in scored) / len(scored)

    @property
    def decay(self) -> list[float]:
        """ターン順のスコア列 (減衰曲線の生データ)。採点不能ターンは除く。"""
        return [t.report.score for t in self.scored_turns]

    def to_dict(self) -> dict:
        return {
            "blend": self.blend,
            "weight": self.weight.value,
            "scenario_id": self.scenario_id,
            "maintenance_rate": self.maintenance_rate,
            "mean_score": self.mean_score,
            "decay": self.decay,
            "turns": [
                {
                    "turn_index": t.turn_index,
                    "score": t.report.score if t.report else None,
                    "status": t.report.status if t.report else "skipped",
                }
                for t in self.turn_scores
            ],
        }


def score_transcript(
    names: list[str],
    transcript: list[str],
    *,
    weight: str | WeightLevel = WeightLevel.MODERATE,
    matrix: CompatibilityMatrix | None = None,
    public_root: Path | None = None,
    user_root: Path | None = None,
    scenario_id: str | None = None,
) -> BenchResult:
    """トランスクリプト (応答文字列のリスト) を ``verify`` でターンごとに採点する。

    Args:
        names: ブレンドする属性名
        transcript: 応答文字列のリスト (1 ターン = 1 応答)。生成元は問わない
            (実 LLM 出力 / 手書き / ``demo_transcript`` のいずれでも可)
        weight: 期待強度 (バンド判定に使用)
        scenario_id: 結果に添えるシナリオ ID (任意、レポート表示用)

    Returns:
        BenchResult (維持率 / 平均スコア / 減衰曲線を含む)
    """
    if not names:
        raise ValueError(tr("core.blend_empty"))
    level = coerce_level(weight)
    attrs = [load_attribute(n, public_root=public_root, user_root=user_root) for n in names]

    turn_scores: list[TurnScore] = []
    for i, text in enumerate(transcript):
        report = verify(text, attrs, level)
        turn_scores.append(TurnScore(turn_index=i, text=text, report=report))

    return BenchResult(
        blend=list(names), weight=level, turn_scores=turn_scores, scenario_id=scenario_id
    )


@dataclass(frozen=True)
class TokenCostEstimate:
    """注入ブロックの token コスト見積り。"""

    names: list[str]
    weight: WeightLevel
    chars: int
    approx_tokens: int  # chars // 4 の粗い見積り (実トークナイザ非依存)。厳密値ではない

    def to_dict(self) -> dict:
        return {
            "names": self.names,
            "weight": self.weight.value,
            "chars": self.chars,
            "approx_tokens": self.approx_tokens,
        }


def estimate_token_cost(
    names: list[str],
    *,
    weight: str | WeightLevel = WeightLevel.MODERATE,
    matrix: CompatibilityMatrix | None = None,
    public_root: Path | None = None,
    user_root: Path | None = None,
) -> TokenCostEstimate:
    """注入ブロック (``render_blend(...).prompt``) の文字数 / 概算 token 数を返す。

    ``approx_tokens`` は 4 文字 ≈ 1 token という粗い経験則であり、実際の
    トークナイザ(モデル依存)の値とは異なる。相対比較 (属性追加でどれだけ
    増えるか) の目安として使うこと。
    """
    result = render_blend(
        names, matrix=matrix, public_root=public_root, user_root=user_root, weight=weight
    )
    level = coerce_level(weight)
    chars = len(result.prompt)
    return TokenCostEstimate(
        names=list(names), weight=level, chars=chars, approx_tokens=chars // 4
    )


def demo_transcript(
    names: list[str],
    *,
    count: int = 6,
    lang: str | None = None,
    matrix: CompatibilityMatrix | None = None,
) -> list[str]:
    """LLM 不要の自己完結デモ用トランスクリプトを生成する (ハーネスの動作確認用)。

    ``sample_dialogue.generate_samples`` (catchphrases から直接導出) を使うため、
    常に高スコアになりやすい tautological な性質を持つ。**実際の「hersona
    あり/なし」品質比較の代用にはしない** — それには自分の LLM 出力を
    ``score_transcript`` に渡すこと (docs/BENCHMARKS.md 参照)。
    """
    from hersona.core.sample_dialogue import generate_samples

    return generate_samples(names, count=count, lang=lang, matrix=matrix)
