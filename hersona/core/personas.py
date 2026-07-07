"""Persona packs for Hermes (PR-B W1, docs/PERSONA_PACKS_DESIGN.md §2–§3).

A persona pack is a *recipe* (not an injection block) that names a blend of
real attributes, a weight, and an optional use_case. The actual injection
block is rendered at install time by delegating to the existing core
(``attach.render_blend`` / ``persistent.run_persistent``), which means
attribute updates propagate automatically and the ``build_site.py``-style
drift gate is unnecessary for packs (designer §2.1).

The module is a thin shell on top of the existing core, mirroring the role
``hersona.core.use_cases`` plays on the control-plane side.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

from hersona.core.paths import persona_pack_schema_path, personas_root

PUBLIC_PERSONAS_ROOT = personas_root()


class PersonaPackError(ValueError):
    """Raised when a persona pack is malformed or fails semantic validation."""


def available_personas(*, root: Path | None = None) -> dict[str, dict[str, Any]]:
    """Return available persona packs keyed by ``persona_name``.

    Mirrors ``available_use_cases``: walks ``root`` recursively, parses each
    YAML, returns ``{persona_name: {display_name, description, weight,
    use_case, path}}``. YAML files that aren't dicts, that are missing a
    non-empty ``persona_name`` string, or that fail to load are silently
    skipped — the catalogue reader's contract is to surface what *is*
    loadable, not to raise on the first broken file.
    """
    base = root or PUBLIC_PERSONAS_ROOT
    found: dict[str, dict[str, Any]] = {}
    if not base.exists():
        return found
    for yml in sorted(base.rglob("*.yaml")):
        data = _safe_load(yml)
        if not isinstance(data, dict):
            continue
        persona_name = data.get("persona_name")
        if not isinstance(persona_name, str) or not persona_name:
            continue
        found[persona_name] = {
            "display_name": data.get("display_name", persona_name),
            "description": data.get("description", ""),
            "weight": data.get("weight", ""),
            "use_case": data.get("use_case"),
            "blend": data.get("blend", []),
            "path": yml,
        }
    return found


def load_persona(name: str, *, root: Path | None = None) -> dict[str, Any]:
    """Load a persona pack by ID and validate it.

    Raises:
        KeyError: pack not found in the catalogue.
        PersonaPackError: schema or semantic validation failed.
    """
    base = root or PUBLIC_PERSONAS_ROOT
    if not base.exists():
        raise KeyError(f"Persona pack not found: {name}")
    for yml in sorted(base.rglob("*.yaml")):
        data = _safe_load(yml)
        if isinstance(data, dict) and data.get("persona_name") == name:
            errors = validate_persona(data, root=base)
            if errors:
                raise PersonaPackError(
                    f"Persona pack '{name}' failed validation: " + "; ".join(errors)
                )
            return data
    raise KeyError(f"Persona pack not found: {name}")


def validate_persona(
    data: dict[str, Any], *, matrix: Any = None, root: Path | None = None
) -> list[str]:
    """Validate a persona pack dict. Returns a list of error strings (empty = OK).

    Three layers, in order:

    1. JSON Schema (structural — required fields, blend item pattern,
       weight enum, i18n shape).
    2. Semantic: every blend item must resolve to a real attribute
       (``<category>/<name>`` → ``load_attribute``).
    3. Conflict: ``check_blend`` on the resolved bare names must return zero
       pairs.
    4. Cross-reference: an optional ``use_case`` must resolve under
       ``use_cases/``.

    ``matrix`` and ``root`` are exposed for testability (override the
    compatibility matrix / persona root without touching the cached
    ``load_matrix()``).
    """
    errors: list[str] = []

    # (1) JSON Schema
    schema_path = persona_pack_schema_path()
    schema = _safe_load(schema_path)
    validator = Draft202012Validator(schema)
    schema_errors = sorted(validator.iter_errors(data), key=lambda e: list(e.path))
    for e in schema_errors:
        path = ".".join(str(p) for p in e.path) or "<root>"
        errors.append(f"schema {path}: {e.message}")

    if errors:
        # 構造 NG のときは意味検証は走らせない (false positive 抑止)
        return errors

    # (2) Semantic — blend 内の各 <category>/<name> が実在するか
    from hersona.core.attach import load_attribute  # local import: avoid cycles

    blend = data.get("blend", [])
    bare_names: list[str] = []
    for ref in blend:
        if not isinstance(ref, str) or "/" not in ref:
            errors.append(f"blend item not in <category>/<name> form: {ref!r}")
            continue
        category, _, attr_name = ref.partition("/")
        try:
            load_attribute(attr_name)
        except KeyError:
            errors.append(f"unknown attribute in blend: {ref!r}")
        bare_names.append(attr_name)

    # (3) Conflict
    if bare_names and not errors:
        if matrix is None:
            from hersona.core.compatibility import load_matrix

            matrix = load_matrix()
        try:
            pairs = matrix.check_blend(bare_names)
        except KeyError as e:
            errors.append(f"check_blend error: {e}")
        else:
            for a, b in pairs:
                errors.append(f"blend has conflict pair: {a} ↔ {b}")

    # (4) Cross-reference — use_case 実在
    use_case = data.get("use_case")
    if use_case:
        from hersona.core.use_cases import available_use_cases

        if use_case not in available_use_cases():
            errors.append(f"unknown use_case: {use_case!r}")

    return errors


def install_persona(
    name: str,
    *,
    profile: str = "default",
    auto_config: bool = False,
    apply: bool = False,
    force: bool = False,
    without_soul: bool = True,
    config_path: str | Path | None = None,
    root: Path | None = None,
) -> Any:
    """Install a persona pack into the local Hermes profile.

    Thin delegate to ``persistent.run_persistent`` with ``persona_name`` set
    to the pack's own ``persona_name`` (designer §3: 設計書 §3 末尾の
    persona_name 引数オーバーライドを使う)。

    Returns:
        ``hersona.core.persistent.PersistentResult``.

    Raises:
        KeyError: pack not found.
        PersonaPackError: schema or semantic validation failed.
    """
    pack = load_persona(name, root=root)

    from hersona.core.persistent import run_persistent

    weight = pack.get("weight") or "moderate"
    use_case = pack.get("use_case")
    # blend は "<category>/<name>" 形式なので、persistent.run_persistent は
    # "category/name" をそのまま受け取れる (内部で裸名に split する)
    names = list(pack.get("blend", []))

    return run_persistent(
        names,
        weight=weight,
        profile=profile,
        without_soul=without_soul,
        force=force,
        auto_config=auto_config,
        apply=apply,
        config_path=config_path,
        use_case=use_case,
        persona_name=name,
    )


def _safe_load(path: Path) -> Any:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}
