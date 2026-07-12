"""Naturalness scorer (§2 / §3 P1 of IMPROVEMENT_PLAN_2026-07-11_humanize).

`measure_naturalness(text, *, lang="ja") -> NaturalnessReport`

100 点満点からの減点式 (0-100, 100 = natural). Detects surface-level
"AI-sounding" features across 4 catalogs (§2.A-D) using deterministic
regex / string matching. No morphological analysis, no LLM calls, no
embeddings — stdlib only, matching the intensity.py discipline.

**What this is** (per §4 honesty):
- A surface proxy for "AI-sound". Gaming-able by design (rewrite to avoid
  the catalogs and you score 100). The metric measures AI-flavor symptoms,
  not "human-ness" in any deep sense.

**What this is not**:
- Not an LLM judge. Not a perplexity score. Not an AI detector.
- Not tuned for English-syntax residual (no morphological analysis).
  See §4-3.

Catalogs (per §2):
- A. 手癖語彙・定型句 (dictionary match)
- B. 構文・リズム癖 (regex pattern + frequency threshold)
- C. 翻訳調・読みにくさ (syntactic proxy)
- D. 構造・応答様式 (conversation-context)

Thresholds are placeholders (per §4-4) and will be re-calibrated against
representative persona conversation transcripts in P3.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# --- §2.A: 手癖語彙・定型句 (dictionary match) ---------------------------

# Each entry: (phrase, penalty_points, language)
# Penalties are per-match; sentence_count normalization lives in measure().
_DICTIONARY: list[tuple[str, int, str]] = [
    # 定型接客句
    ("かしこまりました", 6, "ja"),
    ("承知いたしました", 5, "ja"),
    ("承知しました", 4, "ja"),
    ("Certainly!", 6, "en"),
    ("I'd be happy to", 6, "en"),
    ("Great question", 6, "en"),
    # メタ前置き
    ("重要なのは", 5, "ja"),
    ("結論から言うと", 7, "ja"),
    ("It's important to note", 6, "en"),
    ("In summary,", 5, "en"),
    # 締めの定型
    ("参考になれば幸いです", 7, "ja"),
    ("他にご質問があれば", 6, "ja"),
    ("I hope this helps", 6, "en"),
    ("Let me know if", 5, "en"),
    # 逃げの定型
    ("ケースバイケース", 5, "ja"),
    ("It depends", 4, "en"),
    ("generally speaking", 4, "en"),
    # 反論の先取り
    ("と思われるかもしれません", 5, "ja"),
    ("You might be wondering", 5, "en"),
    # AI 自己言及
    ("AI として", 12, "ja"),
    ("私は AI", 12, "ja"),
    ("as an AI", 12, "en"),
    ("as a language model", 12, "en"),
    # AI 頻出語・死んだ比喩
    ("羅針盤", 6, "ja"),
    ("種をまく", 4, "ja"),
    ("器", 2, "ja"),  # short, weak match — used heavily as both noun and metaphor
    ("受け皿", 6, "ja"),
    ("delve", 6, "en"),
    ("tapestry", 6, "en"),
    ("navigate the landscape", 8, "en"),
]

# --- §2.B: 構文・リズム癖 (regex pattern + frequency threshold) ----------

# (compiled regex, penalty, language, friendly label, threshold_count, threshold_per_chars)
# threshold_count = N occurrences before penalty kicks in
# threshold_per_chars = normalize by text length (None = absolute count)
_B_PATTERN_THRESHOLDS: list[tuple[re.Pattern[str], int, str, str, int, int | None]] = [
    # 否定→肯定の対比 (3回以上で減点)
    (re.compile(r"([^。]*)ではなく、?([^。]*)だ"), 4, "ja", "negation-then-affirmation", 3, None),
    # 三拍子の連打
    (re.compile(r"([^、。]+)、([^、。]+)、([^、。]+)(?:、|。)"), 6, "ja", "triplet-staccato", 1, None),
    # 短い問いの連打 (3連続で減点) - 「〜か。」で終わる文の連続
    # Detected by sentence splitter below; pattern is the per-sentence terminator.
    # 三拍子 / 短問い連打は measure() で文分割後に評価する。
    # 助詞止め・省略の畳みかけ
    (re.compile(r"(?:^|[。\n])([^。\n]{0,40}?(?:も|から|ね|よ|な|さ)[。！？\n]|$)"), 2, "ja", "particle-staccato", 3, None),
    # 「という」の密度 (千字あたり4回以上で減点)
    (re.compile("という"), 3, "ja", "toiu-density", 4, 1000),
    # ダッシュの多用
    (re.compile(r"——|—|--"), 2, "ja", "dash-multiple", 4, None),
    # ヘッジの一律付与 (文末が全部「〜かもしれません」)
    # measure() で文末評価
]


# --- §2.C: 翻訳調・読みにくさ (syntactic proxy) ---------------------------

_C_PATTERN_THRESHOLDS: list[tuple[re.Pattern[str], int, str, str, int, float]] = [
    # 100字を超える一文 (40% 以上の文が該当で減点。1 文だけ 100 字超えは「普通」)
    (re.compile(r"[^。]+。"), 8, "ja", "long-sentence-ratio", 1, 0.4),
    # 漢字7字以上の連続 (漢語の積み上げ) — 2 箇所以上で減点
    (re.compile(r"[一-鿿]{7,}"), 5, "ja", "kanji-run", 2, 0.0),
    # 一文に読点4つ以上 (2 文以上で減点。1 文の長い列挙は普通のケース)
    (re.compile(r"[^。\n]+、[^。\n]+、[^。\n]+、[^。\n]+"), 6, "ja", "comma-overload", 2, 0.0),
]


# --- §2.D: 構造・応答様式 (conversation-context) --------------------------

_DISCLAIMER_PHRASES_JA = [
    "ご注意ください",
    "ご注意ください。",
    "専門家にご相談ください",
    "専門医にご相談ください",
    "自己責任でお願いします",
    "責任を負いかねます",
]

_DISCLAIMER_PHRASES_EN = [
    "Please consult",
    "Please note that",
    "Disclaimer:",
    "I am not a",
    "I'm not a",
]


# --- §4-3: §2.C 英語統語の残存は対象外 ---------------------------------
# Documented in §4-3 as a known limitation. The P1 scorer intentionally
# leaves en-syntax residuals (passive voice, pronoun overuse) un-scored.


@dataclass
class CatalogHits:
    """Hits and penalty per catalog (§2.A-D)."""

    matches: list[str] = field(default_factory=list)
    penalty: float = 0.0

    def add(self, match: str, penalty: float) -> None:
        self.matches.append(match)
        self.penalty += penalty


@dataclass
class NaturalnessReport:
    """`measure_naturalness` の結果。

    - score: 0-100, 100 = natural. 0 = fully saturated with AI-flavor symptoms.
    - a_hits / b_hits / c_hits / d_hits: per-catalog hit detail (penalties + sample matches).
    - sentence_count: 文数 (C-100字ルール等の正規化で使用)
    - lang: 採点対象言語 (ja / en / mixed)
    """

    score: float  # 0-100
    a_hits: CatalogHits
    b_hits: CatalogHits
    c_hits: CatalogHits
    d_hits: CatalogHits
    sentence_count: int
    lang: str = "ja"


def _split_sentences(text: str, lang: str) -> list[str]:
    """naive 文分割。形態素解析なし。

    - ja: 。！？ で分割 (読点も考慮)
    - en: . ! ? で分割
    - 末尾の空要素を捨てる
    """
    if lang == "ja":
        # 改行 + 。！？ 全てで分割
        parts = re.split(r"[。！？\n]+", text)
    else:
        parts = re.split(r"[.!?\n]+", text)
    return [p.strip() for p in parts if p.strip()]


def _count_kanji_run(text: str) -> int:
    """漢字 7+ 連続の個数。"""
    return len(re.findall(r"[一-鿿]{7,}", text))


def _has_bullet_or_header(text: str, lang: str) -> bool:
    """D: 会話への箇条書き・見出し回答の検出。"""
    if lang == "ja":
        # 「・」「-」「*」「#」など。1 つでも見出し (# で始まる行) があれば強いシグナル。
        if re.search(r"^#+\s", text, re.MULTILINE):
            return True
        if re.search(r"^[-*・]\s", text, re.MULTILINE):
            return True
    else:
        if re.search(r"^#+\s", text, re.MULTILINE):
            return True
        if re.search(r"^[-*]\s", text, re.MULTILINE):
            return True
    return False


def _has_disclaimer(text: str, lang: str) -> bool:
    """D: 免責・注意書きの辞書照合。"""
    phrases = _DISCLAIMER_PHRASES_JA if lang == "ja" else _DISCLAIMER_PHRASES_EN
    return any(p in text for p in phrases)


def _sentence_length_cv(sentences: list[str]) -> float | None:
    """文長の変動係数 (standard deviation / mean)。None は 1 文以下。"""
    if len(sentences) < 2:
        return None
    lens = [len(s) for s in sentences]
    mean = sum(lens) / len(lens)
    if mean == 0:
        return None
    var = sum((x - mean) ** 2 for x in lens) / len(lens)
    std = var ** 0.5
    return std / mean


def _has_uniform_sentence_length(sentences: list[str], cv_threshold: float = 0.20) -> bool:
    """D: 文長の均質さ。CV が小さい(均質)と検出。"""
    cv = _sentence_length_cv(sentences)
    if cv is None:
        return False
    return cv < cv_threshold


def measure_naturalness(text: str, *, lang: str = "ja") -> NaturalnessReport:
    """`text` の naturalness スコアを返す。

    Args:
        text: 採点対象テキスト
        lang: "ja" or "en"。zh/ko は §2 範囲外 (§1)。

    Returns:
        NaturalnessReport (score 0-100, hits by catalog, sentence_count)
    """
    a_hits = CatalogHits()
    b_hits = CatalogHits()
    c_hits = CatalogHits()
    d_hits = CatalogHits()

    if not text or not text.strip():
        return NaturalnessReport(
            score=100.0,  # vacuous natural
            a_hits=a_hits,
            b_hits=b_hits,
            c_hits=c_hits,
            d_hits=d_hits,
            sentence_count=0,
            lang=lang,
        )

    sentences = _split_sentences(text, lang)
    sentence_count = len(sentences)
    char_count = len(text)

    # §2.A: 辞書照合 (case-insensitive for English; LLM outputs vary in casing)
    for phrase, penalty, phrase_lang in _DICTIONARY:
        if phrase_lang != lang:
            continue
        if lang == "en":
            count = text.lower().count(phrase.lower())
        else:
            count = text.count(phrase)
        for _ in range(count):
            a_hits.add(phrase, penalty)

    # §2.B: パターン + 頻度閾値
    for pattern, penalty, pat_lang, label, threshold, per_chars in _B_PATTERN_THRESHOLDS:
        if pat_lang != lang:
            continue
        if per_chars is not None and per_chars > 0:
            # density-based: normalize by char count
            matches = pattern.findall(text)
            expected_max = (char_count // per_chars) * threshold
            if len(matches) > expected_max:
                # penalty only on excess
                excess = len(matches) - expected_max
                for _ in range(excess):
                    b_hits.add(label, penalty)
        else:
            matches = pattern.findall(text)
            if len(matches) >= threshold:
                b_hits.add(label, penalty)

    # §2.B 追加: 否定→肯定の対比 と 三拍子 と 助詞止め は上で処理済み
    # §2.B 追加: ヘッジの一律付与 — 文末が全部「〜かもしれません」を検出
    if sentences and lang == "ja":
        hedge_count = sum(1 for s in sentences if s.endswith("かもしれません"))
        if hedge_count >= max(3, sentence_count // 2):  # 半分以上、または 3 文以上
            b_hits.add("hedge-uniformity", 5)

    # §2.B 追加: 短い問いの連打 — 3 文以上連続して「〜か。」で終わる
    if sentences and lang == "ja":
        consecutive_questions = 0
        max_consecutive = 0
        for s in sentences:
            if s.endswith("か") or s.endswith("か。") or s.endswith("か?"):
                consecutive_questions += 1
                max_consecutive = max(max_consecutive, consecutive_questions)
            else:
                consecutive_questions = 0
        if max_consecutive >= 3:
            b_hits.add("question-staccato", 4)

    # §2.C: 翻訳調
    for pattern, penalty, pat_lang, label, threshold, ratio in _C_PATTERN_THRESHOLDS:
        if pat_lang != lang:
            continue
        if ratio > 0:
            # ratio-based: long-sentence if >=40% of sentences exceed 100 chars
            if lang == "ja" and label == "long-sentence-ratio":
                long_count = sum(1 for s in sentences if len(s) > 100)
                if sentence_count > 0 and long_count / sentence_count >= ratio:
                    c_hits.add(label, penalty)
            else:
                matches = pattern.findall(text)
                if len(matches) >= threshold:
                    c_hits.add(label, penalty)
        else:
            matches = pattern.findall(text)
            if len(matches) >= threshold:
                c_hits.add(label, penalty)

    # §2.D: 構造・応答様式
    if _has_bullet_or_header(text, lang):
        d_hits.add("bullet-or-header", 8)
    if _has_disclaimer(text, lang):
        d_hits.add("disclaimer", 6)
    if _has_uniform_sentence_length(sentences):
        d_hits.add("uniform-sentence-length", 4)

    # スコア計算: 100 から減点
    total_penalty = (
        a_hits.penalty + b_hits.penalty + c_hits.penalty + d_hits.penalty
    )
    score = max(0.0, 100.0 - total_penalty)

    return NaturalnessReport(
        score=score,
        a_hits=a_hits,
        b_hits=b_hits,
        c_hits=c_hits,
        d_hits=d_hits,
        sentence_count=sentence_count,
        lang=lang,
    )


__all__ = [
    "CatalogHits",
    "NaturalnessReport",
    "measure_naturalness",
]
