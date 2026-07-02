"""Deterministic lint for public self-introduction copy (docs/guides/self-introduction.*).

No LLM calls — regex / substring rules only.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class IntroViolation:
    rule: str
    message: str
    excerpt: str = ""


@dataclass
class IntroLintResult:
    ok: bool
    violations: list[IntroViolation] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "violations": [
                {"rule": v.rule, "message": v.message, "excerpt": v.excerpt}
                for v in self.violations
            ],
        }


# Self-label (public intro): AI / agent / bot / LLM
_AI_SELF_LABEL = re.compile(
    r"(?i)"
    r"(?:\bAI\b|AI(?:です|だ|である|として|エージェント)|"
    r"人工知能|エージェント|ボット|\bLLM\b|大規模言語|language\s+model|"
    r"\bartificial\s+intelligence\b|\bchatbot\b)",
)

# Meta / implementation exposure
_META_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "meta_personality_label",
        re.compile(r"(クーデレ|ツンデレ|ヤンデレ|デレデレ|メタ|キャラ(?:クター)?(?:です|だよ)|〜系です)"),
    ),
    (
        "meta_implementation",
        re.compile(
            r"(SOUL\.md|SKILL\.md|システムプロンプト|プロンプト注入|hersona\s+blend|"
            r"Recent\s+Context|self_intro_canonical)",
            re.I,
        ),
    ),
    (
        "meta_rule_sermon",
        re.compile(r"(?:禁止(?:です|します)|しません(?:。|$).{0,40}しません)"),
    ),
]

_HANDLE_RE = re.compile(r"@([A-Za-z0-9_]{1,50})")


def _excerpt(text: str, start: int, end: int, *, radius: int = 24) -> str:
    lo = max(0, start - radius)
    hi = min(len(text), end + radius)
    snippet = text[lo:hi].replace("\n", " ")
    return snippet.strip()


def lint_self_intro(
    text: str,
    *,
    allow_handles: frozenset[str] | None = None,
    canonical: bool = False,
) -> IntroLintResult:
    """Lint *text* against cross-persona self-introduction rules.

    Args:
        text: Intro body to check.
        allow_handles: Twitter/X handles allowed without leading @ (e.g. ``hersona_agent``).
        canonical: If True, also flag inner-circle nicknames like マスター (public canonical script).
    """
    allow = {h.lower().lstrip("@") for h in (allow_handles or frozenset())}
    violations: list[IntroViolation] = []
    body = text.strip()
    if not body:
        violations.append(
            IntroViolation("empty", "Intro text is empty", "")
        )
        return IntroLintResult(ok=False, violations=violations)

    for m in _AI_SELF_LABEL.finditer(body):
        violations.append(
            IntroViolation(
                "ai_self_label",
                "Do not use AI/agent/bot/LLM as a self-label in public intros",
                _excerpt(body, m.start(), m.end()),
            )
        )

    for rule_id, pat in _META_PATTERNS:
        for m in pat.finditer(body):
            violations.append(
                IntroViolation(
                    rule_id,
                    f"Meta or rule-sermon pattern ({rule_id})",
                    _excerpt(body, m.start(), m.end()),
                )
            )

    for m in _HANDLE_RE.finditer(body):
        handle = m.group(1).lower()
        if handle not in allow:
            violations.append(
                IntroViolation(
                    "third_party_handle",
                    f"Unexpected @handle (@{m.group(1)}); allow with --allow-handle",
                    _excerpt(body, m.start(), m.end()),
                )
            )

    if canonical:
        if re.search(r"マスター", body):
            violations.append(
                IntroViolation(
                    "inner_circle_nickname",
                    "Canonical public intro should not use マスター (inner-circle only)",
                    "マスター",
                )
            )

    # De-dupe identical rule+excerpt
    seen: set[tuple[str, str]] = set()
    unique: list[IntroViolation] = []
    for v in violations:
        key = (v.rule, v.excerpt)
        if key not in seen:
            seen.add(key)
            unique.append(v)

    return IntroLintResult(ok=len(unique) == 0, violations=unique)
