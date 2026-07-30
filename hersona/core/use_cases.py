"""Operating Mode / use-case prompt packs.

Use cases are control-plane prompt packs: they describe how an agent should work
for a professional task while leaving personality and speech attributes intact.
The injected prompt sections are authored in English for token efficiency and
LLM instruction-following reliability; localized labels may live in ``i18n``.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from hersona.core.paths import use_case_schema_path, use_cases_root
from hersona.core.yamlcache import load_yaml

PUBLIC_USE_CASES_ROOT = use_cases_root()


class UseCaseError(ValueError):
    """Raised when a use-case prompt pack is malformed."""


def available_use_cases(*, root: Path | None = None) -> dict[str, dict[str, Any]]:
    """Return available use cases keyed by ``use_case_id``."""
    base = root or PUBLIC_USE_CASES_ROOT
    found: dict[str, dict[str, Any]] = {}
    if not base.exists():
        return found
    for yml in sorted(base.rglob("*.yaml")):
        data = _safe_load(yml)
        if not isinstance(data, dict):
            continue
        use_case_id = data.get("use_case_id")
        if not isinstance(use_case_id, str):
            continue
        found[use_case_id] = {
            "display_name": data.get("display_name", use_case_id),
            "description": data.get("description", ""),
            "category": data.get("category", ""),
            "risk_level": data.get("risk_level", ""),
            "path": yml,
        }
    return found


def load_use_case(name: str, *, root: Path | None = None) -> dict[str, Any]:
    """Load a use-case YAML by ID."""
    base = root or PUBLIC_USE_CASES_ROOT
    if not base.exists():
        raise KeyError(f"Use case not found: {name}")
    for yml in sorted(base.rglob("*.yaml")):
        data = _safe_load(yml)
        if isinstance(data, dict) and data.get("use_case_id") == name:
            validate_use_case(data)
            return data
    raise KeyError(f"Use case not found: {name}")


def validate_use_case(data: dict[str, Any]) -> None:
    """Validate a use-case prompt pack against ``schema/use_case.schema.json``."""
    schema_path = use_case_schema_path()
    schema = _safe_load(schema_path)
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda e: list(e.path))
    if errors:
        first = errors[0]
        path = ".".join(str(p) for p in first.path) or "<root>"
        raise UseCaseError(f"Invalid use case at {path}: {first.message}")


def render_use_case_block(data: dict[str, Any]) -> str:
    """Render one use-case prompt pack as an English Operating Mode block."""
    validate_use_case(data)
    display = data.get("display_name") or data["use_case_id"]
    lines: list[str] = [f"## Operating Mode: {display}", ""]
    lines.append(
        "You must keep the selected personality and speech style, but add the "
        "following professional operating discipline."
    )
    lines.append("")

    role = data.get("role", {})
    if role:
        lines.append("### Role")
        for key in ("domain", "seniority", "primary_responsibility"):
            value = role.get(key)
            if value:
                label = key.replace("_", " ").title()
                lines.append(f"- {label}: {value}")
        for key, title in (("success_criteria", "Success criteria"), ("boundaries", "Boundaries")):
            values = role.get(key) or []
            if values:
                lines.append(f"- {title}:")
                lines.extend(f"  - {v}" for v in values)
        lines.append("")

    _append_list_section(lines, "Principles", data.get("principles", []))
    _append_list_section(lines, "Workflow", data.get("workflow", []))
    _append_list_section(lines, "Grounding Policy", data.get("grounding_policy", []))
    _append_list_section(lines, "Output Contract", data.get("output_contract", []))
    _append_list_section(lines, "Quality Gate", data.get("quality_gate", []))
    _append_list_section(lines, "Safety", data.get("safety", []))
    return "\n".join(lines).rstrip() + "\n"


def _append_list_section(lines: list[str], title: str, values: list[str]) -> None:
    if not values:
        return
    lines.append(f"### {title}")
    lines.extend(f"- {v}" for v in values)
    lines.append("")


def _safe_load(path: Path) -> Any:
    return load_yaml(path, default={})
