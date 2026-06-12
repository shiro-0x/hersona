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


# weight_for_score のレベル順 (昇格/降格の判定に使用)。
_LEVEL_ORDER: list[WeightLevel] = [
    WeightLevel.NONE,
    WeightLevel.MILD,
    WeightLevel.MODERATE,
    WeightLevel.STRONG,
]


def weight_for_score(
    score: float,
    *,
    previous: WeightLevel | None = None,
    thresholds: tuple[float, float, float] = (25.0, 55.0, 85.0),
    hysteresis: float = 5.0,
) -> WeightLevel:
    """0-100 の連続値スコアを WeightLevel に写像する (duet の感情温度ダイヤル用)。

    - score < t1 → NONE / < t2 → MILD / < t3 → MODERATE / それ以上 → STRONG
    - ``previous`` を渡すと、レベルが「変わる」には境界を ``hysteresis`` 分
      超える必要がある (シーンを跨いだ再評価で境界付近の振動を防ぐ)。
      例: previous=MILD, t2=55 のとき MODERATE 昇格は score >= 60、
      NONE 降格は score < 20。
    - score は 0-100 にクランプする。thresholds は狭義の昇順でなければ ValueError。

    recommend の適合度スコア (0〜3+) 用の :func:`suggest_weight` とは別物。
    """
    t1, t2, t3 = thresholds
    if not (t1 < t2 < t3):
        raise ValueError(f"thresholds must be strictly ascending: {thresholds}")
    score = max(0.0, min(100.0, score))

    def base_level(s: float) -> WeightLevel:
        if s < t1:
            return WeightLevel.NONE
        if s < t2:
            return WeightLevel.MILD
        if s < t3:
            return WeightLevel.MODERATE
        return WeightLevel.STRONG

    target = base_level(score)
    if previous is None or target == previous:
        return target

    prev_idx = _LEVEL_ORDER.index(previous)
    # 昇格: previous の上側境界を hysteresis 分超えたレベルまで上げる
    if _LEVEL_ORDER.index(target) > prev_idx:
        level = previous
        for idx in range(prev_idx, len(_LEVEL_ORDER) - 1):
            boundary = thresholds[idx]
            if score >= boundary + hysteresis:
                level = _LEVEL_ORDER[idx + 1]
            else:
                break
        return level
    # 降格: previous の下側境界を hysteresis 分下回ったレベルまで下げる
    level = previous
    for idx in range(prev_idx - 1, -1, -1):
        boundary = thresholds[idx]
        if score < boundary - hysteresis:
            level = _LEVEL_ORDER[idx]
        else:
            break
    return level
