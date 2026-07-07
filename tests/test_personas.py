"""Persona-pack recipe tests (PR-B W1, docs/PERSONA_PACKS_DESIGN.md §9 T2)."""
from __future__ import annotations

from pathlib import Path

import pytest

from hersona.core.compatibility import load_matrix
from hersona.core.personas import (
    PersonaPackError,
    available_personas,
    load_persona,
    validate_persona,
)
from hersona.core.use_cases import load_use_case

REPO_ROOT = Path(__file__).resolve().parent.parent
PERSONAS_DIR = REPO_ROOT / "personas"


# --- スキーマ検証 (構造) -----------------------------------------------------


def test_schema_rejects_missing_required_field() -> None:
    """blend / weight / persona_name / display_name / description が必須。"""
    errors = validate_persona({})  # 全部欠け
    # 5 つの required が全部欠けると 5 件の schema エラーが出る
    assert any("schema" in e and "persona_name" in e for e in errors)


def test_schema_rejects_unknown_weight_value() -> None:
    """weight は enum [none / mild / moderate / strong] のみ。"""
    errors = validate_persona(
        {
            "persona_name": "x",
            "display_name": "X",
            "description": "d",
            "blend": ["personality/diligent"],
            "weight": "very_strong",  # ← invalid
        }
    )
    assert any("weight" in e for e in errors)


def test_schema_rejects_blend_with_empty_list() -> None:
    """blend は minItems: 1。"""
    errors = validate_persona(
        {
            "persona_name": "x",
            "display_name": "X",
            "description": "d",
            "blend": [],
            "weight": "moderate",
        }
    )
    assert any("blend" in e for e in errors)


def test_schema_rejects_blend_item_without_category_prefix() -> None:
    """blend item は ^<category>/<name>$ パターン必須。"""
    errors = validate_persona(
        {
            "persona_name": "x",
            "display_name": "X",
            "description": "d",
            "blend": ["bare_diligent"],  # ← invalid (no category/)
            "weight": "moderate",
        }
    )
    assert any("blend" in e for e in errors)


# --- 意味検証 (実在する属性 / conflict なし) ------------------------------


def test_semantic_rejects_unknown_attribute() -> None:
    """blend 内の <category>/<name> が実在しない属性ならエラー。"""
    errors = validate_persona(
        {
            "persona_name": "x",
            "display_name": "X",
            "description": "d",
            "blend": ["personality/this_attribute_does_not_exist"],
            "weight": "moderate",
        }
    )
    assert any("unknown attribute" in e for e in errors)


def test_semantic_rejects_conflict_pair() -> None:
    """実在属性でも conflict ペアを含む blend はエラー。

    ``intellectual`` ↔ ``airhead`` は実マトリクスで真の conflict。
    """
    # intellectual ↔ airhead は実マトリクスで真の conflict
    matrix = load_matrix()
    errors = validate_persona(
        {
            "persona_name": "x",
            "display_name": "X",
            "description": "d",
            "blend": ["personality/intellectual", "personality/airhead"],
            "weight": "moderate",
        },
        matrix=matrix,
    )
    assert any("conflict pair" in e for e in errors), errors


def test_semantic_rejects_unknown_use_case() -> None:
    """use_case が use_cases/ に実在しない ID ならエラー。"""
    errors = validate_persona(
        {
            "persona_name": "x",
            "display_name": "X",
            "description": "d",
            "blend": ["personality/diligent"],
            "weight": "moderate",
            "use_case": "this_use_case_does_not_exist",
        }
    )
    assert any("unknown use_case" in e for e in errors)


# --- available_personas / load_persona の動作 ------------------------------


def test_available_personas_returns_empty_when_dir_empty(tmp_path: Path) -> None:
    """空ディレクトリでは空 dict。"""
    assert available_personas(root=tmp_path) == {}


def test_load_persona_raises_keyerror_for_unknown() -> None:
    """未存在パックは KeyError。"""
    with pytest.raises(KeyError):
        load_persona("not_a_pack", root=PERSONAS_DIR)


def test_load_persona_raises_packerror_for_invalid_file(tmp_path: Path) -> None:
    """schema 不適合の YAML は load_persona() で PersonaPackError。"""
    (tmp_path / "bad.yaml").write_text(
        "persona_name: bad\n"
        "display_name: Bad\n"
        "description: d\n"
        "blend: []\n"  # ← invalid (empty)
        "weight: moderate\n",
        encoding="utf-8",
    )
    with pytest.raises(PersonaPackError):
        load_persona("bad", root=tmp_path)


# --- 同梱パックの回帰 (§9 T6 の受け入れ基準: 全 pack が validate_persona を 0 エラー) -


def test_all_shipped_personas_validate_clean() -> None:
    """All 14 shipped persona packs pass validate_persona() with zero errors.

    This is the §9 T6 acceptance criterion enforced as a permanent CI gate:
    a pack with an unknown attribute, a conflict pair, or a missing use_case
    will fail this test and block the PR.

    Guarded by a count check so that an empty personas/ directory fails
    loudly instead of silently passing the assertion.
    """
    catalog = available_personas(root=PERSONAS_DIR)
    assert len(catalog) >= 14, (
        f"personas/ has {len(catalog)} packs; PR-B W1 §9 T6 requires at least 14"
    )
    matrix = load_matrix()
    bad: dict[str, list[str]] = {}
    for name in catalog:
        pack = load_persona(name, root=PERSONAS_DIR)
        errs = validate_persona(pack, matrix=matrix)
        if errs:
            bad[name] = errs
    assert not bad, f"validation errors: {bad}"


# --- use_cases / attributes と同じファイルの "not found" 一貫性 ---------


def test_use_case_lookup_helper_is_reachable() -> None:
    """sanity check: validate_persona() が use_cases.load_use_case() と矛盾しない。

    load_use_case() は dict[str, Any] を返すのでキーを直接読む。
    """
    data = load_use_case("programmer")
    assert data["use_case_id"] == "programmer"
