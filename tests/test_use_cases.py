"""Operating Mode / use-case prompt pack tests."""
from __future__ import annotations

from pathlib import Path

import pytest

from hersona.core.attach import render_blend
from hersona.core.use_cases import (
    available_use_cases,
    load_use_case,
    render_use_case_block,
    validate_use_case,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
USE_CASES_DIR = REPO_ROOT / "use_cases"
ATTRIBUTES_DIR = REPO_ROOT / "attributes"
_NO_USER = Path("/nonexistent")


def test_available_use_cases_includes_initial_catalog() -> None:
    cases = available_use_cases(root=USE_CASES_DIR)

    assert set(cases) >= {
        "programmer",
        "planner",
        "research",
        "marketing",
        "product_manager",
        "qa_reviewer",
        "data_analyst",
        "customer_support",
    }


def test_load_and_validate_programmer_use_case_is_english_control_plane() -> None:
    data = load_use_case("programmer", root=USE_CASES_DIR)

    validate_use_case(data)
    assert data["use_case_id"] == "programmer"
    assert data["display_name"] == "Programmer"
    assert "プログラマー" not in str(data)
    assert data["risk_level"] == "low"
    assert "Do not claim success without observed command output." in data["principles"]


def test_render_use_case_block_has_operating_mode_and_contract() -> None:
    data = load_use_case("programmer", root=USE_CASES_DIR)

    block = render_use_case_block(data)

    assert block.startswith("## Operating Mode: Programmer")
    assert "You must keep the selected personality and speech style" in block
    assert "### Workflow" in block
    assert "Inspect relevant files before editing." in block
    assert "### Output Contract" in block
    assert "Files changed" in block


def test_render_blend_appends_use_case_operating_mode() -> None:
    result = render_blend(
        ["tsundere", "keigo"],
        public_root=ATTRIBUTES_DIR,
        user_root=_NO_USER,
        use_case="programmer",
        use_case_root=USE_CASES_DIR,
    )

    assert "# hersona attribute blend" in result.prompt
    assert "## Operating Mode: Programmer" in result.prompt
    assert "Inspect relevant files before editing." in result.prompt
    assert "べ、別に……" in result.prompt


def test_all_public_use_cases_validate_and_render() -> None:
    for case_id in available_use_cases(root=USE_CASES_DIR):
        data = load_use_case(case_id, root=USE_CASES_DIR)
        validate_use_case(data)
        block = render_use_case_block(data)
        assert block.startswith("## Operating Mode:")
        assert "### Role" in block
        assert "### Quality Gate" in block


def test_professional_use_cases_include_expected_controls() -> None:
    product = load_use_case("product_manager", root=USE_CASES_DIR)
    assert "impact, confidence, effort, and risk" in "\n".join(product["workflow"])

    qa = load_use_case("qa_reviewer", root=USE_CASES_DIR)
    assert "Acceptance criteria checked" in qa["output_contract"]

    data = load_use_case("data_analyst", root=USE_CASES_DIR)
    assert "Do not invent data, rows, schemas, or computed results." in data["role"]["boundaries"]

    support = load_use_case("customer_support", root=USE_CASES_DIR)
    assert "Never request passwords, recovery codes, private keys, or full payment details." in support["safety"]


def test_unknown_use_case_raises_key_error() -> None:
    with pytest.raises(KeyError):
        load_use_case("not_a_mode", root=USE_CASES_DIR)


# --- PR-A W2 / T5-2: use_case 拡張 (8 → 20) 回帰テスト ---------------------
#
# 件数ハードコードは ``tests/catalog_counts.py`` の ``TOTAL_USE_CASES`` 1 箇所に
# 集約する (PR-A §9 T5-2 仕様)。追加・削除時は ``catalog_counts.py`` を更新するだけで
# ここのテストはそのまま機能する。

from .catalog_counts import TOTAL_USE_CASES

REQUIRED_FIELDS = [
    "use_case_id", "display_name", "description", "category", "risk_level",
    "role", "principles", "workflow", "output_contract", "quality_gate",
]


def test_use_case_count_meets_minimum() -> None:
    """Catalog has at least TOTAL_USE_CASES entries (PR-A target: 20)."""
    assert len(available_use_cases()) >= TOTAL_USE_CASES


def test_all_use_case_ids_resolvable() -> None:
    """Every catalog ID loads via load_use_case() without exception."""
    for uid in available_use_cases().keys():
        data = load_use_case(uid)
        assert data["use_case_id"] == uid


def test_all_use_cases_pass_schema() -> None:
    """Every YAML file passes schema validation."""
    for uid in available_use_cases().keys():
        data = load_use_case(uid)  # load_use_case() validates internally
        for field in REQUIRED_FIELDS:
            assert field in data, f"{uid} missing {field}"


@pytest.mark.parametrize(
    "section",
    ["principles", "workflow", "grounding_policy", "output_contract", "quality_gate", "safety"],
)
def test_no_duplicate_section_lines(section: str) -> None:
    """No identical line appears in 2+ use_case files (designer §11 / §9 risk)."""
    seen: dict[str, list[str]] = {}
    for uid in available_use_cases().keys():
        data = load_use_case(uid)
        for line in data.get(section, []):
            seen.setdefault(line, []).append(uid)
    duplicates = {line: ids for line, ids in seen.items() if len(ids) > 1}
    assert not duplicates, f"{section}: duplicate lines found: {duplicates}"
