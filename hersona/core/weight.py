"""weight 較正 (ROADMAP ① weight 較正: mild / moderate / strong)。

属性の「強度」を attach/blend の実ダイヤルとして扱う。weight_dimension
(none / mild / moderate / strong) ごとに、プロンプト注入時の強度ガイダンスと
catchphrases の露出量を調整する。recommend の適合度スコアから強度を推定する
ヘルパーも提供する。
"""
from __future__ import annotations

from enum import StrEnum


class WeightLevel(StrEnum):
    """属性の強度レベル (schema の weight_dimension と対応)。"""

    NONE = "none"
    MILD = "mild"
    MODERATE = "moderate"
    STRONG = "strong"


# 各強度のプロンプト注入時ガイダンス。
WEIGHT_GUIDANCE: dict[WeightLevel, str] = {
    WeightLevel.NONE: "特性として質的にのみ効かせる。口癖・語尾の顕在化は最小限に留める。",
    WeightLevel.MILD: "ほのかに滲ませる。catchphrases は時折、語尾は控えめに。",
    WeightLevel.MODERATE: "標準的な強度。catchphrases と語尾を自然な頻度で用いる。",
    WeightLevel.STRONG: "明確に顕在化させる。catchphrases を多用し、語尾・一人称を徹底する。",
}

# 強度ごとの catchphrases 露出比率 (0.0-1.0)。
_CATCHPHRASE_RATIO: dict[WeightLevel, float] = {
    WeightLevel.NONE: 0.0,
    WeightLevel.MILD: 0.34,
    WeightLevel.MODERATE: 0.67,
    WeightLevel.STRONG: 1.0,
}


def coerce_level(value: str | WeightLevel) -> WeightLevel:
    """文字列 / WeightLevel を WeightLevel に正規化する。"""
    if isinstance(value, WeightLevel):
        return value
    try:
        return WeightLevel(value)
    except ValueError as e:
        raise ValueError(
            f"未知の weight: '{value}' (none / mild / moderate / strong)"
        ) from e


def catchphrase_subset(catchphrases: list[str], level: str | WeightLevel) -> list[str]:
    """強度に応じて catchphrases の露出サブセットを返す。

    NONE は空、STRONG は全件。MILD/MODERATE は比率で先頭から採る (最低 1 件)。
    """
    lvl = coerce_level(level)
    ratio = _CATCHPHRASE_RATIO[lvl]
    if not catchphrases or ratio <= 0.0:
        return []
    if ratio >= 1.0:
        return list(catchphrases)
    k = max(1, round(len(catchphrases) * ratio))
    return catchphrases[:k]


def suggest_weight(score: float) -> WeightLevel:
    """recommend の適合度スコアから推奨強度を推定する。

    スコアが高いほど強く顕在化させる (0 → none, 大 → strong)。
    """
    if score <= 0:
        return WeightLevel.NONE
    if score < 1.5:
        return WeightLevel.MILD
    if score < 3.0:
        return WeightLevel.MODERATE
    return WeightLevel.STRONG
