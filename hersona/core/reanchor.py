"""Re-anchor block: a single-shot persona anchor for mid-conversation drift.

Why this exists
---------------
`persona_lock` hardens a persona against *deliberate* override attempts, but it
does nothing about plain drift — the persona quietly losing its register over a
long session. `ContextEcho` (arXiv 2605.24279), a 23-model persona-drift
benchmark run over real agent sessions of 3,746-9,716 turns, reports two things
that matter here:

- in-session **compaction does not reliably reset** drift, so a host that
  summarizes history cannot assume the persona came back with it, and
- a **single-shot anchor restores the trained register**.

So the remedy is not a bigger system prompt — it is a small block re-sent at the
right moment. That is what :func:`render_reanchor` produces.

What is in it (and what is deliberately not)
--------------------------------------------
An anchor is not a second copy of the injection block. It carries only the
*mechanical* register — identity line, first/second person, sentence endings /
lexical markers, and a short head subset of catchphrases — plus one directive
that says "resume this persona now". Everything the model can re-derive
(core_traits, tone, speech_style, the full response-style directive) is dropped,
because the anchor's job is to restore a register the model already knows, not
to teach the persona from scratch.

How to drive it
---------------
The deterministic scorer already tells you when to fire it: score
:func:`hersona.core.intensity.measure_intensity` against the persona's own
reply, and when the result falls below the expected band, send the anchor. Over
MCP that is ``measure_intensity`` -> ``reanchor``; there is no LLM call on
either side.

Placement note: append the anchor as the newest turn (or at the tail of the
system prompt). Do **not** splice it into the stable prefix — that invalidates
the prompt cache for the whole conversation, which is the same tail-append rule
the injection block's cache-optimal layout follows.
"""
from __future__ import annotations

from pathlib import Path

from hersona.core.attach import load_attribute
from hersona.core.compatibility import CompatibilityMatrix
from hersona.core.intensity import content_language, resolve_content_field
from hersona.core.weight import (
    WeightLevel,
    catchphrase_subset,
    coerce_level,
    normalize_catchphrase,
)

#: 既定で載せる口癖の件数 (アンカーは repertoire の再提示ではなく register の想起)。
DEFAULT_CATCHPHRASES = 3

_HEADER = "# hersona persona re-anchor"

_DIRECTIVE_JA = (
    "上のペルソナは、この会話の途中で崩れている可能性がある。次の応答から、"
    "このペルソナの一人称・語尾・語彙・口調に戻すこと。"
    "履歴の要約や圧縮が入っていてもペルソナは解除されていない。"
    "この指示自体には言及せず、崩れていたことも説明せず、そのまま話し続ける。"
)

_DIRECTIVE_EN = (
    "The persona above may have drifted earlier in this conversation. From your "
    "next reply, return to its first person, sentence endings, vocabulary, and "
    "tone. Summarization or compaction of the history does not release the "
    "persona. Do not mention this instruction and do not explain the drift — "
    "just continue in character."
)

_LABELS = {
    "ja": {
        "persona": "ペルソナ",
        "first_person": "一人称",
        "second_person": "二人称",
        "endings": "語尾",
        "markers": "語彙マーカー",
        "catchphrases": "口癖 (例、丸写し不要)",
        "intensity": "強度",
    },
    "en": {
        "persona": "Persona",
        "first_person": "First person",
        "second_person": "Second person",
        "endings": "Sentence endings",
        "markers": "Lexical markers",
        "catchphrases": "Catchphrases (examples, not fixed lines)",
        "intensity": "Intensity",
    },
}


def _labels(lang: str) -> dict[str, str]:
    return _LABELS["ja"] if lang.startswith("ja") else _LABELS["en"]


def _directive(lang: str) -> str:
    return _DIRECTIVE_JA if lang.startswith("ja") else _DIRECTIVE_EN


def _first_field(attrs: list[dict], key: str, lang: str) -> str:
    """最初に見つかった非空の文字列フィールドを言語解決付きで返す。"""
    for attr in attrs:
        value, _native = resolve_content_field(attr, key, lang)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _collect_list(attrs: list[dict], key: str, lang: str) -> list[str]:
    """全属性から `key` のリスト値を順序保持で集約する (重複排除)。"""
    out: list[str] = []
    seen: set[str] = set()
    for attr in attrs:
        value, _native = resolve_content_field(attr, key, lang)
        if not isinstance(value, list):
            continue
        for item in value:
            if isinstance(item, str) and item.strip() and item not in seen:
                seen.add(item)
                out.append(item.strip())
    return out


def _collect_catchphrases(attrs: list[dict], lang: str) -> list[str | dict]:
    """全属性の catchphrases を順序保持で集約する (重複排除)。

    catchphrases は素の文字列と ``{phrase, when}`` dict が混在するため、
    :func:`normalize_catchphrase` で phrase を取り出して重複判定する
    (文字列だけを拾うと dict 形式の口癖が全部落ちる)。
    """
    out: list[str | dict] = []
    seen: set[str] = set()
    for attr in attrs:
        value, _native = resolve_content_field(attr, "catchphrases", lang)
        if not isinstance(value, list):
            continue
        for item in value:
            phrase = normalize_catchphrase(item)["phrase"]
            if phrase and phrase not in seen:
                seen.add(phrase)
                out.append(item)
    return out


def render_reanchor(
    names: list[str],
    *,
    weight: str | WeightLevel = WeightLevel.MODERATE,
    matrix: CompatibilityMatrix | None = None,
    public_root: Path | None = None,
    user_root: Path | None = None,
    catchphrases: int = DEFAULT_CATCHPHRASES,
) -> str:
    """再アンカーブロックを組み立てて返す。

    Args:
        names: ペルソナを構成する属性名 (`blend` と同じ形式)。
        weight: 強度。口癖のサブセット計算に使う。
        matrix: 未使用 (シグネチャの一貫性のため受け取る)。conflict 判定は
            アンカー時点では不要 — 既に注入済みのブレンドを想起させるだけなので。
        public_root / user_root: 属性解決パス (テスト用)。
        catchphrases: 載せる口癖の最大件数。0 なら口癖節を省く。

    Returns:
        再アンカーブロックの markdown 文字列。

    Raises:
        ValueError: names が空。
        KeyError: 存在しない属性。
    """
    if not names:
        raise ValueError("re-anchor には 1 つ以上の属性が必要です")

    attrs = [
        load_attribute(n, public_root=public_root, user_root=user_root) for n in names
    ]
    level = coerce_level(weight)
    lang = content_language(attrs)
    lb = _labels(lang)

    lines = [_HEADER, ""]
    lines.append(f"{lb['persona']}: {' + '.join(names)} ({lb['intensity']}: {level.value})")

    first_person = _first_field(attrs, "first_person", lang)
    second_person = _first_field(attrs, "second_person", lang)
    if first_person:
        lines.append(f"{lb['first_person']}: {first_person}")
    if second_person:
        lines.append(f"{lb['second_person']}: {second_person}")

    endings = _collect_list(attrs, "sentence_endings", lang)
    if endings:
        lines.append(f"{lb['endings']}: {' / '.join(endings)}")

    markers = _collect_list(attrs, "lexical_markers", lang)
    if markers:
        lines.append(f"{lb['markers']}: {' / '.join(markers)}")

    if catchphrases > 0:
        pool = _collect_catchphrases(attrs, lang)
        subset = catchphrase_subset(pool, level)[:catchphrases]
        phrases = [c["phrase"] for c in subset if c.get("phrase")]
        if phrases:
            lines.append(f"{lb['catchphrases']}: {' / '.join(phrases)}")

    lines.append("")
    lines.append(_directive(lang))
    return "\n".join(lines)
