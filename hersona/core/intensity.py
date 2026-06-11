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

from hersona.core.i18n import tr
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
    lang: str = "ja"  # 採点対象 (speech 属性) のコンテンツ言語


def _has_japanese(text: str) -> bool:
    """text に日本語 (ひらがな/カタカナ/漢字) が含まれるか。"""
    return any(
        "぀" <= ch <= "ヿ" or "一" <= ch <= "鿿" or ch == "ー"
        for ch in text
    )


def content_language(attributes: list[dict]) -> str:
    """ブレンドのコンテンツ言語を speech 属性の content_lang から決める。

    speech 属性の最初の ``content_lang`` を採用。未指定/speech 無しは既定 ``ja``。
    """
    for a in attributes:
        if a.get("attribute_category") == "speech" and a.get("content_lang"):
            return str(a["content_lang"])
    return "ja"


def resolve_content_field(attr: dict, key: str, lang: str) -> tuple[object, bool]:
    """言語拘束コンテンツ (catchphrases / tone / core_traits) を lang に解決する。

    BASE (トップレベルのキー) の言語は属性の ``content_lang`` (未指定は ``ja``)。
    要求 lang が属性の BASE 言語と一致すれば BASE を、異なれば
    ``content_i18n.<lang>.<key>`` を優先する。
    戻り値 ``(value, is_native)``:
    - ``is_native=True``  : value はその言語でネイティブ (BASE 一致 or 解決済み)
    - ``is_native=False`` : BASE 値しか無く lang と不一致 (呼び出し側で除外判断)
    """
    base = attr.get(key)
    attr_lang = str(attr.get("content_lang") or "ja")
    if not lang or attr_lang == lang:
        return base, True
    sub = (attr.get("content_i18n") or {}).get(lang) or {}
    if sub.get(key):
        return sub[key], True
    return base, False


def skip_reason(text: str, attributes: list[dict]) -> str | None:
    """強度測定を skip すべきか判定し、理由コードを返す (測定可なら None)。

    - ``"no_speech"``     : speech 属性のシグナル (語尾 / lexical_markers) が無い
    - ``"unsupported_lang"``: コンテンツ言語が ja / en 以外 (採点ロジック未対応)
    - ``"lang_mismatch"`` : コンテンツ言語と出力テキストの言語が食い違う
    """
    endings, markers, _ = _collect_speech_signals(attributes)
    lang = content_language(attributes)
    if lang == "ja":
        if not endings:
            return "no_speech"
        if text.strip() and not _has_japanese(text):
            return "lang_mismatch"
        return None
    if lang == "en":
        if not markers:
            return "no_speech"
        if text.strip() and _has_japanese(text):
            return "lang_mismatch"
        return None
    return "unsupported_lang"


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
) -> tuple[list[str], list[str], list[str]]:
    """speech 属性から sentence_endings / lexical_markers / catchphrases を集約する。

    personality / archetype は語尾・口癖を持っていても測定対象外 (signal に含めない)。
    戻り値: ``(endings, lexical_markers, catchphrases)``。
    ``endings`` は ja コンテンツ採点用、``lexical_markers`` は en コンテンツ採点用。
    """
    endings: list[str] = []
    markers: list[str] = []
    catchphrases: list[str] = []
    seen_e: set[str] = set()
    seen_m: set[str] = set()
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
        for mk in a.get("lexical_markers", []) or []:
            if not isinstance(mk, str) or not mk:
                continue
            low = mk.strip().lower()
            if low and low not in seen_m:
                seen_m.add(low)
                markers.append(low)
        for c in a.get("catchphrases", []) or []:
            if not isinstance(c, str) or not c:
                continue
            if c not in seen_c:
                seen_c.add(c)
                catchphrases.append(c)
    return endings, markers, catchphrases


def measure_intensity(text: str, attributes: list[dict]) -> IntensityReport | None:
    """出力テキストの強度指標を採点する。

    speech 属性が無いブレンドは None (skip)。採点軸は:
    - endings_rate: 文末が speech 属性の sentence_endings に一致する割合 (0-1)
    - catchphrase_density: catchphrases 出現数 / 文数 (0-1 にクリップ)

    score は 0-100 = 100 * (0.6 * endings_rate + 0.4 * catchphrase_density)。
    band / status は verify() 側で埋める想定だが、本関数も band=(0, 100) / status=""
    で初期化したレポートを返す (verify() を経由せず中間結果を使いたい場合用)。
    """
    endings, markers, catchphrases = _collect_speech_signals(attributes)
    lang = content_language(attributes)
    # 主シグナル: ja は語尾、en は lexical_markers。いずれも無ければ skip。
    primary = endings if lang == "ja" else markers if lang == "en" else []
    if not primary:
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
            lang=lang,
        )

    if lang == "en":
        # en: 語尾活用が無いため「マーカーを含む文の割合」を主軸にする (大小無視)。
        low_sentences = [s.lower() for s in sentences]
        matching = sum(1 for s in low_sentences if any(mk in s for mk in primary))
        low_text = text.lower()
        catchphrase_hits = sum(low_text.count(c.lower()) for c in catchphrases)
    else:
        matching = sum(1 for s in sentences if _ends_with_any(s, primary))
        catchphrase_hits = sum(text.count(c) for c in catchphrases)

    endings_rate = matching / sentence_count
    density = min(1.0, catchphrase_hits / max(1, sentence_count))

    score = 100.0 * (0.6 * endings_rate + 0.4 * density)
    return IntensityReport(
        score=score,
        endings_rate=endings_rate,
        catchphrase_hits=catchphrase_hits,
        sentence_count=sentence_count,
        band=(0, 100),
        status="",
        lang=lang,
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
        mark = tr("report.pass")
    elif report.status == "under":
        mark = tr("report.under")
    else:
        mark = tr("report.over", status=report.status)
    return tr(
        "report.line",
        score=f"{report.score:.0f}",
        endings=f"{report.endings_rate:.0%}",
        hits=report.catchphrase_hits,
        band=lvl,
        lo=lo,
        hi=hi,
        status=report.status,
        mark=mark,
    )
