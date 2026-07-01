"""Regression tests for tests/catalog_counts.py."""

from tests.catalog_counts import (
    PUBLIC_CATEGORY_COUNTS,
    TOTAL_PUBLIC_ATTRIBUTES,
    assert_category_totals_match,
    cli_list_banner_en,
    cli_list_banner_ja_count_fragment,
)


def test_public_category_counts_sum_to_total() -> None:
    assert_category_totals_match()


def test_cli_banner_helpers_use_total() -> None:
    assert cli_list_banner_en() == f"Available attributes ({TOTAL_PUBLIC_ATTRIBUTES})"
    assert cli_list_banner_ja_count_fragment() == f"{TOTAL_PUBLIC_ATTRIBUTES} 件"
    assert sum(PUBLIC_CATEGORY_COUNTS.values()) == TOTAL_PUBLIC_ATTRIBUTES
