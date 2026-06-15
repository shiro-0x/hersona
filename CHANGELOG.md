# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- C: blend presets — `hersona save <name> <attrs...> [--weight] [--note]` persists a blend
  (a recipe of attribute names + intensity) as a named preset under `~/.hermes/presets/`
  (override with `HERSONA_PRESETS_DIR`). `hersona presets` lists them and `hersona load <name>`
  replays one through the same blend engine (with optional `--weight` override). Core logic in
  `hersona/core/presets.py` (`Preset`, `save_preset`, `load_preset`, `list_presets`,
  `delete_preset`, `presets_root`, `PresetError`), exported from `hersona.core` and documented
  in `docs/PUBLIC_API.md`. 27 new tests.
- B3: `image_prompt_tags` (string[]) optional field added to `schema/attribute.schema.json`
  for visual attributes. All 5 visual templates (`animal_ears` / `glamorous` / `glasses` /
  `petite` / `silver_hair`) now carry English SD/Flux-style tag lists.
- B4: `first_person` (string) optional field added to `schema/attribute.schema.json`.
  Seven speech attributes now declare their first-person pronoun(s):
  `ore_boy` (オレ/俺), `boku_girl` (ボク), `washi` (わし), `gyaru` (あたし/うち),
  `tomboy` (あたし), `princess_speech` (わたくし/私), `archaic` (我/拙者).
- B4: `IntensityReport.first_person_hits` field added; intensity score now uses a
  3-axis formula when both `sentence_endings` and `first_person` are present
  (`0.45·endings + 0.30·catchphrase + 0.25·first_person`). Attributes with only
  `first_person` (no endings, e.g. `ore_boy`, `boku_girl`) are now measurable
  instead of being skipped. `format_report` output includes the first_person count.
  19 new tests (608 total).

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
- Compatibility matrix with conflict/compatible resolution, plus conflict-fix
  suggestions: `CompatibilityMatrix.alternatives_for()` / `suggest_blend_fixes()`
  propose same-category, non-conflicting replacements, surfaced by
  `hersona blend --suggest` / `hersona preview --suggest`
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
