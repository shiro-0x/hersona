"""Operating Mode / use-case prompt pack tests."""
from __future__ import annotations

from pathlib import Path

import pytest

from hersona.core.attach import render_blend
from hersona.core.use_cases import (
    UseCaseError,
    available_use_cases,
    load_use_case,
    render_use_case_block,
    validate_use_case,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
USE_CASES_DIR = REPO_ROOT / "use_cases"
ATTRIBUTES_DIR = REPO_ROOT / "attributes"
_NO_USER = Path("/nonexistent")


PUBLIC_CATALOG = {
    "programmer",
    "planner",
    "research",
    "marketing",
    "product_manager",
    "qa_reviewer",
    "data_analyst",
    "customer_support",
    "tutor",
    "creative_writer",
    "brainstorm_facilitator",
    "technical_writer",
    "sre_devops",
    "translator",
    "legal_info",
}


def test_available_use_cases_includes_public_catalog() -> None:
    cases = available_use_cases(root=USE_CASES_DIR, user_root=_NO_USER)

    assert set(cases) == PUBLIC_CATALOG
    assert all(meta["source"] == "public" for meta in cases.values())


def test_load_and_validate_programmer_use_case_is_english_control_plane() -> None:
    data = load_use_case("programmer", root=USE_CASES_DIR)

    validate_use_case(data)
    assert data["use_case_id"] == "programmer"
    assert data["display_name"] == "Programmer"
    # 注入ブロックは英語コントロールプレーンのまま (i18n はメタデータラベルのみ)。
    assert "プログラマー" not in render_use_case_block(data)
    assert data["i18n"]["ja"]["display_name"] == "プログラマー"
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
    for case_id in available_use_cases(root=USE_CASES_DIR, user_root=_NO_USER):
        data = load_use_case(case_id, root=USE_CASES_DIR, user_root=_NO_USER)
        validate_use_case(data)
        block = render_use_case_block(data)
        assert block.startswith("## Operating Mode:")
        assert "### Role" in block
        assert "### Quality Gate" in block


def test_all_public_use_cases_have_japanese_i18n() -> None:
    for case_id, meta in available_use_cases(root=USE_CASES_DIR, user_root=_NO_USER).items():
        ja = (meta.get("i18n") or {}).get("ja") or {}
        assert ja.get("display_name"), f"{case_id}: missing i18n.ja.display_name"
        assert ja.get("description"), f"{case_id}: missing i18n.ja.description"


def test_professional_use_cases_include_expected_controls() -> None:
    product = load_use_case("product_manager", root=USE_CASES_DIR)
    assert "impact, confidence, effort, and risk" in "\n".join(product["workflow"])

    qa = load_use_case("qa_reviewer", root=USE_CASES_DIR)
    assert "Acceptance criteria" in qa["output_contract"]

    data = load_use_case("data_analyst", root=USE_CASES_DIR)
    assert "Do not invent data, rows, schemas, or computed results." in data["role"]["boundaries"]

    support = load_use_case("customer_support", root=USE_CASES_DIR)
    assert "Never request passwords, recovery codes, private keys, or full payment details." in support["safety"]


def test_unknown_use_case_raises_key_error() -> None:
    with pytest.raises(KeyError):
        load_use_case("not_a_mode", root=USE_CASES_DIR, user_root=_NO_USER)


def test_medium_or_high_risk_requires_safety() -> None:
    data = load_use_case("sre_devops", root=USE_CASES_DIR, user_root=_NO_USER)
    assert data["risk_level"] == "medium"

    stripped = {k: v for k, v in data.items() if k != "safety"}
    with pytest.raises(UseCaseError, match="safety"):
        validate_use_case(stripped)


def test_regulated_pilot_legal_info_is_high_risk_with_guardrails() -> None:
    data = load_use_case("legal_info", root=USE_CASES_DIR, user_root=_NO_USER)

    assert data["category"] == "regulated"
    assert data["risk_level"] == "high"
    block = render_use_case_block(data)
    assert "not legal advice" in block
    assert "### Safety" in block


def _write_pack(path: Path, use_case_id: str, *, marker: str = "x") -> None:
    path.write_text(
        f"""use_case_id: {use_case_id}
display_name: Test {use_case_id}
description: Test pack {marker}.
category: technical
risk_level: low
role:
  domain: testing
  seniority: senior
  primary_responsibility: Exercise the loader.
principles:
  - Test principle.
workflow:
  - Test step.
output_contract:
  - Test output.
quality_gate:
  - Test gate.
""",
        encoding="utf-8",
    )


def test_duplicate_use_case_id_in_same_root_raises(tmp_path: Path) -> None:
    _write_pack(tmp_path / "a.yaml", "dup")
    _write_pack(tmp_path / "b.yaml", "dup")

    with pytest.raises(UseCaseError, match="Duplicate use_case_id"):
        available_use_cases(root=tmp_path, user_root=_NO_USER)
    with pytest.raises(UseCaseError, match="Duplicate use_case_id"):
        load_use_case("dup", root=tmp_path, user_root=_NO_USER)


def test_user_root_pack_is_discovered_and_overrides_public(tmp_path: Path) -> None:
    _write_pack(tmp_path / "my_mode.yaml", "my_mode", marker="mine")
    _write_pack(tmp_path / "programmer.yaml", "programmer", marker="override")

    cases = available_use_cases(root=USE_CASES_DIR, user_root=tmp_path)
    assert cases["my_mode"]["source"] == "user"
    assert cases["programmer"]["source"] == "user"

    data = load_use_case("programmer", root=USE_CASES_DIR, user_root=tmp_path)
    assert data["description"] == "Test pack override."
