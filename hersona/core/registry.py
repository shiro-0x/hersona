"""Read-only access to the repository component registry.

The registry is a governance index, not runtime configuration. This module
only loads, validates, and filters ``docs/REGISTRY.yaml``; it never writes,
changes lifecycle state, or deletes an unknown source.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

from hersona.core.paths import registry_path

REGISTRY_ENV = "HERSONA_REGISTRY_PATH"
STATUS_VALUES = frozenset({"active", "deprecated", "archived"})
ONBOARDING_VALUES = frozenset({"clear", "unclear", "blocked"})
REQUIRED_ENTRY_FIELDS = frozenset({"id", "kind", "canonical", "status"})


class RegistryError(ValueError):
    """Raised when the component registry is unavailable or malformed."""


def load_registry(*, path: Path | str | None = None) -> dict[str, Any]:
    """Load and validate the registry without changing any external state.

    ``path`` is primarily useful for tests and tools operating on a checked-out
    repository. When omitted, ``HERSONA_REGISTRY_PATH`` takes precedence over
    the repository's default ``docs/REGISTRY.yaml`` path.
    """
    source = Path(path).expanduser() if path is not None else _configured_path()
    if not source.exists():
        raise RegistryError(f"Registry not found: {source}")
    try:
        with source.open(encoding="utf-8") as handle:
            data = yaml.safe_load(handle)
    except (OSError, yaml.YAMLError) as exc:
        raise RegistryError(f"Could not read registry {source}: {exc}") from exc
    if not isinstance(data, dict):
        raise RegistryError("Registry root must be a mapping")
    _validate_registry(data)
    return data


def list_registry(
    *,
    kind: str | None = None,
    status: str | None = None,
    onboarding: str | None = None,
    path: Path | str | None = None,
) -> list[dict[str, Any]]:
    """Return registry entries, optionally filtered by read-only dimensions."""
    data = load_registry(path=path)
    entries = data["entries"]
    return [
        entry
        for entry in entries
        if (kind is None or entry["kind"] == kind)
        and (status is None or entry["status"] == status)
        and (onboarding is None or entry.get("onboarding") == onboarding)
    ]


def get_registry_entry(
    entry_id: str, *, path: Path | str | None = None
) -> dict[str, Any]:
    """Return one entry by ID, or raise ``KeyError`` when absent."""
    for entry in load_registry(path=path)["entries"]:
        if entry["id"] == entry_id:
            return entry
    raise KeyError(f"Registry entry not found: {entry_id}")


def validate_registry(data: dict[str, Any]) -> list[str]:
    """Return validation errors without mutating ``data``."""
    errors: list[str] = []
    if data.get("version") != 1:
        errors.append("version must be 1")
    entries = data.get("entries")
    if not isinstance(entries, list):
        return [*errors, "entries must be a list"]
    seen: set[str] = set()
    for index, entry in enumerate(entries):
        prefix = f"entries[{index}]"
        if not isinstance(entry, dict):
            errors.append(f"{prefix} must be a mapping")
            continue
        missing = REQUIRED_ENTRY_FIELDS - entry.keys()
        errors.extend(f"{prefix} missing {field}" for field in sorted(missing))
        entry_id = entry.get("id")
        if not isinstance(entry_id, str) or not entry_id:
            errors.append(f"{prefix}.id must be a non-empty string")
        elif entry_id in seen:
            errors.append(f"duplicate entry id: {entry_id}")
        else:
            seen.add(entry_id)
        if entry.get("status") not in STATUS_VALUES:
            errors.append(f"{prefix}.status must be one of {sorted(STATUS_VALUES)}")
        onboarding = entry.get("onboarding")
        if onboarding is not None and onboarding not in ONBOARDING_VALUES:
            errors.append(
                f"{prefix}.onboarding must be one of {sorted(ONBOARDING_VALUES)} or null"
            )
        for field in ("kind", "canonical"):
            if field in entry and not isinstance(entry[field], str):
                errors.append(f"{prefix}.{field} must be a string")
        for field in ("references", "dependencies"):
            if field in entry and not _is_string_list(entry[field]):
                errors.append(f"{prefix}.{field} must be a list of strings")
    return errors


def _validate_registry(data: dict[str, Any]) -> None:
    errors = validate_registry(data)
    if errors:
        raise RegistryError("Invalid registry: " + "; ".join(errors))


def _configured_path() -> Path:
    configured = os.environ.get(REGISTRY_ENV)
    return Path(configured).expanduser() if configured else registry_path()


def _is_string_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)
