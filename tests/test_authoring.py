"""ローカル属性オーサリング (hersona.core.authoring) の回帰テスト (ROADMAP ③)。

- build_attribute が任意フィールドの空値を除外し、スキーマ整合な dict を作る
- 検証ゲート: save_attribute がスキーマ違反を拒否する
- override_attribute が既存属性を土台に上書きする
- 保存先がユーザー名前空間に分離される (HERSONA_USER_DIR / 既定 ~/.hermes)
- 共有ガード: 既定では空ブロックリスト (find_proper_noun_risks が何も返さない)
"""
from __future__ import annotations

from pathlib import Path

import pytest

from hersona.core.authoring import (
    AuthoringError,
    ValidationGateError,
    build_attribute,
    find_proper_noun_risks,
    list_user_attributes,
    override_attribute,
    save_attribute,
    user_attributes_root,
    validate_attribute,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
ATTRIBUTES_DIR = REPO_ROOT / "attributes"


def _minimal_valid() -> dict:
    return build_attribute(
        attribute_category="personality",
        attribute_name="my_custom",
        display_name_ja="マイカスタム",
        display_name_en="My Custom",
        weight_dimension="moderate",
        description_ja="テスト用のローカル属性。",
        description_en="A local attribute for testing.",
        examples=["[user] hi\n[assistant] ...べ、別に"],
        core_traits=["a", "b", "c"],
        catchphrases=["x"],
    )


def test_build_attribute_drops_empty_optionals() -> None:
    data = build_attribute(
        attribute_category="speech",
        attribute_name="foo",
        display_name_ja="フー",
        display_name_en="Foo",
        weight_dimension="none",
        description_ja="説明",
        description_en="desc",
        examples=["ex"],
        notes="",  # 空文字は除外される
        tags=[],  # 空リストは除外される
        variant=None,  # None は除外される
        second_person="きみ",  # 値ありは残る
    )
    assert "notes" not in data
    assert "tags" not in data
    assert "variant" not in data
    assert data["second_person"] == "きみ"


def test_build_attribute_passes_schema() -> None:
    data = _minimal_valid()
    assert validate_attribute(data) == []


def test_validate_attribute_catches_schema_violation() -> None:
    bad = _minimal_valid()
    bad["weight_dimension"] = "extreme"  # enum 外
    errors = validate_attribute(bad)
    assert errors
    assert any("weight_dimension" in e for e in errors)


def test_validate_attribute_name_category_mismatch() -> None:
    data = _minimal_valid()
    errors = validate_attribute(data, expect_name="other", expect_category="speech")
    assert any("attribute_name" in e for e in errors)
    assert any("attribute_category" in e for e in errors)


def test_save_attribute_writes_to_user_namespace(tmp_path: Path) -> None:
    data = _minimal_valid()
    dest = save_attribute(data, user_root=tmp_path)
    assert dest == tmp_path / "personality" / "my_custom.yaml"
    assert dest.exists()
    # 公開 attributes/ には書かれていない
    assert not (ATTRIBUTES_DIR / "personality" / "my_custom.yaml").exists()


def test_save_attribute_validation_gate_rejects(tmp_path: Path) -> None:
    bad = _minimal_valid()
    del bad["examples"]  # 必須欠落
    with pytest.raises(ValidationGateError):
        save_attribute(bad, user_root=tmp_path)
    assert list_user_attributes(tmp_path) == []  # 何も書かれない


def test_save_attribute_no_overwrite_by_default(tmp_path: Path) -> None:
    data = _minimal_valid()
    save_attribute(data, user_root=tmp_path)
    with pytest.raises(AuthoringError):
        save_attribute(data, user_root=tmp_path)
    # overwrite=True なら成功
    save_attribute(data, user_root=tmp_path, overwrite=True)


def test_list_user_attributes(tmp_path: Path) -> None:
    save_attribute(_minimal_valid(), user_root=tmp_path)
    found = list_user_attributes(tmp_path)
    assert len(found) == 1


def test_user_attributes_root_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HERSONA_USER_DIR", "/tmp/hersona_test_dir")
    assert user_attributes_root() == Path("/tmp/hersona_test_dir")


def test_user_attributes_root_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HERSONA_USER_DIR", raising=False)
    assert user_attributes_root() == Path.home() / ".hermes" / "attributes"


def test_override_attribute_from_real_base() -> None:
    data = override_attribute(
        "tsundere",
        new_name="my_tsundere",
        overrides={"catchphrases": ["独自の口癖"]},
        attributes_root=ATTRIBUTES_DIR,
    )
    assert data["attribute_name"] == "my_tsundere"
    assert data["attribute_category"] == "personality"  # 土台を継承
    assert data["catchphrases"] == ["独自の口癖"]
    assert data["variant"] == "custom"
    assert validate_attribute(data) == []  # 上書き後もスキーマ整合


def test_override_attribute_rejects_same_name() -> None:
    with pytest.raises(AuthoringError):
        override_attribute(
            "tsundere",
            new_name="tsundere",
            overrides={},
            attributes_root=ATTRIBUTES_DIR,
        )


def test_override_attribute_unknown_base() -> None:
    with pytest.raises(AuthoringError):
        override_attribute(
            "nonexistent_base",
            new_name="x",
            overrides={},
            attributes_root=ATTRIBUTES_DIR,
        )


# --- 共有ガード ---------------------------------------------------------


def test_clean_attribute_has_no_risks() -> None:
    assert find_proper_noun_risks(_minimal_valid()) == []
