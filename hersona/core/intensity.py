"""強度指標 (intensity metric)。

ROADMAP の「強度指標 (intensity metric) ★計画 (仕様確定済み・未実装)」を実装する
core ロジック。出力テキストの「形」(語尾一致率 + 口癖密度) を **表層のみ・決定的**
に採点し、期待バンドと比較して status (pass / under / over) を返す。

設計の割り切り (ROADMAP / IMPLEMENTATION_GUIDE §4.1 合意済み):
- LLM 不使用。再現性優先、gaming 可は許容。
- 一人称は指標から除外 (schema に専用フィールドが無いため)。
- speech 属性が 1 つも無いブレンドは測定 skip (語尾軸が無いため)。
"""
from __future__ import annotations

from dataclasses import dataclass

from hersona.core.weight import WeightLevel, coerce_level

# 文末判定時の句読点・記号 (半角全角両対応)
_PUNCT_STRIP = "。．.！!？? 　"


@dataclass
class IntensityReport:
    """強度指標の採点結果。"""

    score: float  # 0-100
    endings_rate: float  # 0-1: 文末が sentence_endings に一致した割合
    catchphrase_hits: int  # catchphrases 出現回数
    sentence_count: int  # 採点対象文数
    band: tuple[int, int]  # 期待バンド (lo, hi)
    status: str  # "pass" / "under" / "over"


def expected_band(level: str | WeightLevel) -> tuple[int, int]:
    """強度レベルから期待バンド (lo, hi) を返す。

    none (0, 20) / mild (20, 45) / moderate (45, 70) / strong (70, 100)。
    """
    bands: dict[WeightLevel, tuple[int, int]] = {
        WeightLevel.NONE: (0, 20),
        WeightLevel.MILD: (20, 45),
        WeightLevel.MODERATE: (45, 70),
        WeightLevel.STRONG: (70, 100),
    }
    return bands[coerce_level(level)]


def _split_sentences(text: str) -> list[str]:
    """文を句読点・改行で分割し、空要素を除いて返す。"""
    if not text:
        return []
    parts: list[str] = []
    buf: list[str] = []
    for ch in text:
        if ch in "。．.！!？?\n":
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    tail = "".join(buf)
    if tail:
        parts.append(tail)
    return [s for s in parts if s.strip()]


def _normalize_ending(ending: str) -> str:
    """語尾比較用に先頭の 〜 / ~ と末尾の句読点を除去する。"""
    e = ending.strip().rstrip(_PUNCT_STRIP)
    while e and e[0] in "〜~":
        e = e[1:]
    return e


def _ends_with_any(text: str, normalized_endings: list[str]) -> bool:
    """text の文末 (句読点 strip 後) が normalized_endings のいずれかに一致するか。

    ただし normalized_endings が空なら False。
    """
    if not normalized_endings:
        return False
    t = text.rstrip(_PUNCT_STRIP)
    return any(t.endswith(e) for e in normalized_endings if e)


def _collect_speech_signals(
    attributes: list[dict],
) -> tuple[list[str], list[str]]:
    """speech 属性から sentence_endings と catchphrases を和集合で集約する。

    personality / archetype は語尾・口癖を持っていても測定対象外 (signal に含めない)。
    """
    endings: list[str] = []
    catchphrases: list[str] = []
    seen_e: set[str] = set()
    seen_c: set[str] = set()
    for a in attributes:
        if a.get("attribute_category") != "speech":
            continue
        for e in a.get("sentence_endings", []) or []:
            if not isinstance(e, str):
                continue
            ne = _normalize_ending(e)
            if ne and ne not in seen_e:
                seen_e.add(ne)
                endings.append(ne)
        for c in a.get("catchphrases", []) or []:
            if not isinstance(c, str) or not c:
                continue
            if c not in seen_c:
                seen_c.add(c)
                catchphrases.append(c)
    return endings, catchphrases


def measure_intensity(text: str, attributes: list[dict]) -> IntensityReport | None:
    """出力テキストの強度指標を採点する。

    speech 属性が無いブレンドは None (skip)。採点軸は:
    - endings_rate: 文末が speech 属性の sentence_endings に一致する割合 (0-1)
    - catchphrase_density: catchphrases 出現数 / 文数 (0-1 にクリップ)

    score は 0-100 = 100 * (0.6 * endings_rate + 0.4 * catchphrase_density)。
    band / status は verify() 側で埋める想定だが、本関数も band=(0, 100) / status=""
    で初期化したレポートを返す (verify() を経由せず中間結果を使いたい場合用)。
    """
    endings, catchphrases = _collect_speech_signals(attributes)
    if not endings:
        # speech 属性が無い → 語尾軸が成立しないので skip
        return None

    sentences = _split_sentences(text)
    sentence_count = len(sentences)

    if sentence_count == 0:
        # 採点対象が無い
        return IntensityReport(
            score=0.0,
            endings_rate=0.0,
            catchphrase_hits=0,
            sentence_count=0,
            band=(0, 100),
            status="",
        )

    matching = sum(1 for s in sentences if _ends_with_any(s, endings))
    endings_rate = matching / sentence_count

    catchphrase_hits = sum(text.count(c) for c in catchphrases)
    density = min(1.0, catchphrase_hits / max(1, sentence_count))

    score = 100.0 * (0.6 * endings_rate + 0.4 * density)
    return IntensityReport(
        score=score,
        endings_rate=endings_rate,
        catchphrase_hits=catchphrase_hits,
        sentence_count=sentence_count,
        band=(0, 100),
        status="",
    )


def verify(
    text: str,
    attributes: list[dict],
    level: str | WeightLevel,
) -> IntensityReport | None:
    """measure_intensity にバンド比較を足し、status を確定する。

    - score < lo → "under" (警告対象。exit 0 のまま stderr に警告)
    - score > hi → "over"
    - それ以外 → "pass"

    speech 属性が無いブレンドは None。
    """
    report = measure_intensity(text, attributes)
    if report is None:
        return None
    lo, hi = expected_band(level)
    report.band = (lo, hi)
    if report.score < lo:
        report.status = "under"
    elif report.score > hi:
        report.status = "over"
    else:
        report.status = "pass"
    return report


def format_report(report: IntensityReport, level: str | WeightLevel) -> str:
    """採点結果を CLI 1 行表示用に整形する (verify() 後専用)。"""
    lvl = coerce_level(level).value
    lo, hi = report.band
    if report.status == "pass":
        mark = "✓"
    elif report.status == "under":
        mark = "⚠ under"
    else:
        mark = f"over ({report.status})"
    return (
        f"強度 {report.score:.0f}/100 "
        f"(語尾一致 {report.endings_rate:.0%} / "
        f"口癖 {report.catchphrase_hits}件) "
        f"band={lvl}({lo}-{hi}) "
        f"status={report.status} {mark}"
    )
