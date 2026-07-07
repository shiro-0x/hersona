"""Public catalog counts for regression tests.

When adding or removing attributes under ``attributes/`` or use cases under
``use_cases/``, update this module once instead of scattering hard-coded totals
across multiple test files.
"""

from __future__ import annotations

TOTAL_PUBLIC_ATTRIBUTES = 346

PUBLIC_CATEGORY_COUNTS: dict[str, int] = {
    "personality": 43,
    "speech": 140,
    "archetype": 66,
    "visual": 46,
    "hobby": 51,
}

#: Total number of public Operating Mode / use-case prompt packs in
#: ``use_cases/*.yaml``. Update when extending the catalog (see
#: ``docs/PERSONA_PACKS_DESIGN.md`` §9 T5-2: 1 箇所に集約).
TOTAL_USE_CASES = 20


def assert_category_totals_match() -> None:
    """Guard against typos: category buckets must sum to the public total."""
    total = sum(PUBLIC_CATEGORY_COUNTS.values())
    assert total == TOTAL_PUBLIC_ATTRIBUTES, (
        f"PUBLIC_CATEGORY_COUNTS sum to {total}, expected {TOTAL_PUBLIC_ATTRIBUTES}"
    )


def cli_list_banner_en() -> str:
    return f"Available attributes ({TOTAL_PUBLIC_ATTRIBUTES})"


def cli_list_banner_ja_count_fragment() -> str:
    """Substring expected in Japanese ``list`` output (利用可能な属性 (N 件))."""
    return f"{TOTAL_PUBLIC_ATTRIBUTES} 件"
