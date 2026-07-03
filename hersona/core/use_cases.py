"""Operating Mode / use-case prompt packs.

Use cases are control-plane prompt packs: they describe how an agent should work
for a professional task while leaving personality and speech attributes intact.
The injected prompt sections are authored in English for token efficiency and
LLM instruction-following reliability; localized labels may live in ``i18n``.

Discovery order: the public root (``use_cases/``) is scanned first, then the
user root (``~/.hermes/use_cases`` or ``HERSONA_USER_USE_CASES_DIR``). A user
pack with the same ``use_case_id`` overrides the public one; duplicate IDs
within the same root raise :class:`UseCaseError`.
"""
from __future__ import annotations

import os
from functools import cache
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

from hersona.core.paths import use_case_schema_path, use_cases_root

PUBLIC_USE_CASES_ROOT = use_cases_root()

#: ユーザー作成 use-case の保存先を上書きする環境変数。
_USER_DIR_ENV = "HERSONA_USER_USE_CASES_DIR"


class UseCaseError(ValueError):
    """Raised when a use-case prompt pack is malformed."""


def user_use_cases_root() -> Path:
    """ユーザー作成 use-case のルートディレクトリ。

    環境変数 ``HERSONA_USER_USE_CASES_DIR`` があればそれを、
    無ければ ``~/.hermes/use_cases`` (属性の ``~/.hermes/attributes`` と同列)。
    """
    env = os.environ.get(_USER_DIR_ENV)
    if env:
        return Path(env).expanduser()
    return Path.home() / ".hermes" / "use_cases"


def available_use_cases(
    *, root: Path | None = None, user_root: Path | None = None
) -> dict[str, dict[str, Any]]:
    """Return available use cases keyed by ``use_case_id``.

    User packs override public packs with the same ID (``source`` tells which
    root a pack came from).
    """
    found: dict[str, dict[str, Any]] = {}
    for base, source in _roots(root, user_root):
        for use_case_id, (path, data) in _scan_root(base).items():
            found[use_case_id] = {
                "display_name": data.get("display_name", use_case_id),
                "description": data.get("description", ""),
                "category": data.get("category", ""),
                "risk_level": data.get("risk_level", ""),
                "tags": data.get("tags", []),
                "i18n": data.get("i18n", {}),
                "source": source,
                "path": path,
            }
    return found


def load_use_case(
    name: str, *, root: Path | None = None, user_root: Path | None = None
) -> dict[str, Any]:
    """Load a use-case YAML by ID (user root wins over public root)."""
    for base, _source in reversed(_roots(root, user_root)):
        match = _scan_root(base).get(name)
        if match is not None:
            data = match[1]
            validate_use_case(data)
            return data
    raise KeyError(f"Use case not found: {name}")


def validate_use_case(data: dict[str, Any]) -> None:
    """Validate a use-case prompt pack against ``schema/use_case.schema.json``."""
    validator = _validator(str(use_case_schema_path()))
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


# --- 内部 ---------------------------------------------------------------


def _roots(root: Path | None, user_root: Path | None) -> list[tuple[Path, str]]:
    """走査対象 (root, source) を優先度の低い順 (public → user) に返す。"""
    return [
        (root or PUBLIC_USE_CASES_ROOT, "public"),
        (user_root or user_use_cases_root(), "user"),
    ]


def _scan_root(base: Path) -> dict[str, tuple[Path, dict[str, Any]]]:
    """1 ルート配下の use-case を ID で索引する。同一ルート内の重複 ID はエラー。"""
    found: dict[str, tuple[Path, dict[str, Any]]] = {}
    if not base.exists():
        return found
    for yml in sorted(base.rglob("*.yaml")):
        data = _safe_load(yml)
        if not isinstance(data, dict):
            continue
        use_case_id = data.get("use_case_id")
        if not isinstance(use_case_id, str):
            continue
        if use_case_id in found:
            raise UseCaseError(
                f"Duplicate use_case_id '{use_case_id}': "
                f"{found[use_case_id][0]} and {yml}"
            )
        found[use_case_id] = (yml, data)
    return found


@cache
def _validator(schema_path: str) -> Draft202012Validator:
    """スキーマ Validator をパス単位でキャッシュする (呼び出しごとの再読込を避ける)。"""
    return Draft202012Validator(_safe_load(Path(schema_path)))


def _append_list_section(lines: list[str], title: str, values: list[str]) -> None:
    if not values:
        return
    lines.append(f"### {title}")
    lines.extend(f"- {v}" for v in values)
    lines.append("")


def _safe_load(path: Path) -> Any:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}
