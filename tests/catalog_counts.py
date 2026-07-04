"""Public attribute catalog counts for regression tests.

When adding or removing attributes under ``attributes/``, update this module
once instead of scattering hard-coded totals across multiple test files.
"""

from __future__ import annotations

TOTAL_PUBLIC_ATTRIBUTES = 206

PUBLIC_CATEGORY_COUNTS: dict[str, int] = {
    "personality": 42,
    "speech": 140,
    "archetype": 9,
    "visual": 5,
    "hobby": 10,
}


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
