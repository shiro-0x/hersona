# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.0.1] - 2026-06-15

First published release (PyPI via Trusted Publishing on the `v0.0.1` tag).

### Added
- 64 attribute templates (personality 20 / speech 25 / archetype 9 / visual 5 / hobby 5)
- `schema/attribute.schema.json` for attribute validation
- `hersona` CLI (`list` / `show` / `matrix` / `blend` / `diff` / `preview` / `recommend` / `create` / `measure`)
- `hersona preview <names...>` — show the injection block plus catchphrase-based sample
  phrases for a blend, with no LLM required (wraps `core.sample_dialogue`).
- `hersona diff <a> <b>` — compare two attributes: relation (conflict/compatible/neutral,
  including cross-language speech conflicts), scalar fields side by side, and list fields
  (core_traits / catchphrases / ...) split into common vs. only-one. Core logic in
  `hersona/core/diff.py`.
- Optional `tui` extra (`pip install "hersona[tui]"`): color tables for `list` and panels
  for `show` via `rich`. Falls back to plain text without `rich`, when piping, or with
  `--plain` / `NO_COLOR`; `HERSONA_FORCE_RICH=1` keeps color when piping.
- Compatibility matrix with conflict/compatible resolution
- Intensity scoring for speech attributes
- Diagnostic quiz with multilingual support (en/ja)
- `skills/hersona/SKILL.md` for Hermes Agent integration
- MIT license for code, CC0 1.0 for attribute templates
- `weight_for_score(score, *, previous, thresholds, hysteresis)` public API — maps a
  0–100 continuous score to a `WeightLevel`, with optional hysteresis (the level only
  changes once the score crosses a threshold by ±`hysteresis`). Intended for the duet
  emotion/affection dial.
- `docs/PUBLIC_API.md` declaring `hersona.core.__all__` as the semver-stable public API.
  `tests/test_public_api.py` keeps the document and `__all__` in sync automatically.
- PyPI packaging: the wheel bundles `attributes/` and `schema/` under `hersona/data/`
  (resolved by `hersona/core/paths.py` for both the repo and installed layouts).
  `.github/workflows/publish.yml` publishes to PyPI via Trusted Publishing on `v*` tags.
  `tests/test_packaging.py` regression-tests the bundled contents.
- `.github/workflows/ci.yml` running `ruff` + `scripts/validate.py` +
  `build_site.py --check` + `pytest` on Python 3.11/3.12/3.13.

### Changed
- pyproject: PyPI metadata (English `description` / `keywords` / `classifiers` / `urls`);
  removed the unused `requests` dependency; the dev-only `scripts/` is excluded from the wheel.
