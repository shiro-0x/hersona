"""Read-only component registry tests."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from hersona.core.registry import (
    RegistryError,
    get_registry_entry,
    list_registry,
    load_registry,
    validate_registry,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = REPO_ROOT / "docs" / "REGISTRY.yaml"


def test_load_repository_registry_and_keep_entry_ids_unique() -> None:
    data = load_registry(path=REGISTRY_PATH)
    ids = [entry["id"] for entry in data["entries"]]
    assert len(ids) == 17
    assert len(ids) == len(set(ids))
    assert get_registry_entry("interface/hermes-skill", path=REGISTRY_PATH)["status"] == "active"


def test_list_registry_filters_without_mutating_loaded_data() -> None:
    before = load_registry(path=REGISTRY_PATH)
    snapshot = deepcopy(before)
    unclear = list_registry(onboarding="unclear", path=REGISTRY_PATH)
    assert unclear
    assert all(entry["onboarding"] == "unclear" for entry in unclear)
    assert before == snapshot


def test_validate_registry_rejects_duplicate_ids_and_unknown_status() -> None:
    data = load_registry(path=REGISTRY_PATH)
    data["entries"].append(deepcopy(data["entries"][0]))
    data["entries"][-1]["status"] = "unknown"
    errors = validate_registry(data)
    assert any("duplicate entry id" in error for error in errors)
    assert any("status must be one of" in error for error in errors)


def test_load_registry_rejects_malformed_file(tmp_path: Path) -> None:
    path = tmp_path / "registry.yaml"
    path.write_text("entries: nope\n", encoding="utf-8")
    with pytest.raises(RegistryError, match="version must be 1"):
        load_registry(path=path)


def test_registry_reader_does_not_write_custom_source(tmp_path: Path) -> None:
    path = tmp_path / "registry.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "entries": [
                    {
                        "id": "example/item",
                        "kind": "documentation",
                        "canonical": "README.md",
                        "status": "active",
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    original = path.read_text(encoding="utf-8")
    assert load_registry(path=path)["entries"][0]["id"] == "example/item"
    assert path.read_text(encoding="utf-8") == original
