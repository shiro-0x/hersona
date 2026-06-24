# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> **注 (semver ロールバック履歴)**: 2026-06-17 に v1.3.0 → v0.2.0 → v1.4.0 という
> semver 後退を含む連続リリースが発生した（ユーザー指示）。PyPI には 0.2.0 がそのまま
> 残っているが、これはロールバック履歴の記録として保持。`pip install hersona` は
> 1.4.0 を解決する。機能セットは [1.3.0] と同じ。

## [Unreleased]

### Added
- 5 new English-native `personality` attributes for international users (84 → 89 total, personality 35 → 40). Authored with `content_lang: en` (base content in English + `i18n.ja` display/description), parallel to the existing `*_en` speech registers. Western pop-culture archetypes distinct from the Japanese anime tropes:
  - `sassy` — bold, quick-witted, comeback-ready confidence read as cheek, not cruelty (distinct from playful's joke-deflection and deadpan's flat retort; conflicts with socially_anxious / dandere)
  - `rebel` — principled defiance of unearned authority and rules-for-rules'-sake; loyal to people, not systems (Western outlaw/maverick flavor)
  - `charmer` — smooth, magnetic, effortlessly likeable; flirtation as reflex over real warmth (charisma, not narcissism's self-love; conflicts with socially_anxious / dandere)
  - `drama_queen` — lives at full volume, every feeling performed for the back row, with a genuine heart under the theatrics (distinct from menhera's anxiety and crybaby's genuine tears; conflicts with stoic / deadpan / laid_back)
  - `go_getter` — ambitious, plan-first, take-charge drive that turns "someday" into a deadline (goal/ambition-driven, distinct from diligent's effort-as-intrinsic-value; conflicts with laid_back / pessimist)
- SKILL version bumped to v0.5.3; count contracts synced to 89 across README EN/JA, `CLAUDE.md` / `CONTRIBUTING.md`, `skills/hersona/SKILL.md` + `REFERENCE.md`, and the hardcoded counts in `test_attributes` / `test_cli` / `test_compatibility` / `test_attach` / `test_mcp`.
- README (EN/JA): add prominent "Install (Hermes Agent)" section featuring `hermes skills tap add shiro-0x/hersona` — no registry approval needed, works immediately. Also includes skill registry status table (HermesHub PR pending, ClawHub in progress).
- `skills/hersona/SKILL.md` and `skills/hersona-initializer/SKILL.md`: add `metadata.openclaw` block (emoji, homepage, os) to prepare for ClawHub submission.
- `hersona update` subcommand: download the latest attribute data (`attributes/` + `schema/`) from the GitHub repository into a local data cache (`~/.hermes/data/` by default, or `HERSONA_DATA_DIR`), so pip/wheel installs can refresh templates **without reinstalling**. The cache takes precedence over the bundled data in `hersona.core.paths`. Supports `--ref` (branch/tag/commit SHA, default `main`), `--dry-run`, and `--clear` (revert to bundled templates). Uses only the Python standard library (`urllib` + `tarfile`); no new dependencies. New core module `hersona.core.update` and `hersona.core.paths.data_cache_root()`.
- 1 new `personality` attribute (83 → 84 total, personality 34 → 35):
  - `puppyish` — bright, open-hearted attachment that forms fast; admires and follows the people they like, eager for attention and praise ("dog-type junior" trend). Distinct from deredere (romantic openness), genki (undirected energy), and menhera (anxious dependency); conflicts with kuudere / hinedere / stoic / deadpan.
- 8 new attributes (75 → 83 total: personality 30 → 34, speech ja 21 → 25):
  - `scheming` — smiling exterior, cold calculation underneath; kindness is investment (distinct from yandere's obsession and narcissist's self-love)
  - `gluttonous` — food as primary motivation and lens; mood drops when hungry (distinct from hobby/cooking which is skill, not drive)
  - `crybaby` — cries easily from joy, sadness, and gratitude; emotionally transparent, not psychologically unstable (distinct from menhera's abandonment anxiety)
  - `diligent` — effort as intrinsic value; never quits, always finds the next angle (distinct from serious's demeanor and stoic's emotional suppression)
  - `hakata_ben` — Kyushu/Hakata dialect; energetic `〜と？/〜たい/〜ばい/〜けん` endings; warm and direct
  - `tohoku_ben` — Tohoku/Zuzu-ben dialect; gentle vowel-merged `〜だべ/〜っぺ/〜んだ` patterns; soft and unhurried
  - `robotic` — monotone declarative `-desu/-masu`; literal interpretation, zero filler, mechanical register (pairs with robot_android archetype)
  - `burikko` — performative cuteness with drawn-out syllables and affected helplessness; performed, not felt (distinct from natural soft/whispery)
- Optimized SKILL.md taxonomy table: personality/speech rows now use abbreviated `...` notation (fixed-width rows) instead of enumerating all names, eliminating per-turn linear token growth as the library scales
- SKILL version bumped to v0.5.1

### Changed
- `puppyish` ("dog-type junior"): toned down the literal-dog imagery while keeping
  the affectionate-junior core (looks up to / follows / craves praise, keigo speech).
  Removed tail-wagging and head-pat motifs — the `頭なでてほしいです` / "Can I get a
  head pat?" catchphrase becomes `もっと褒めてほしいです` / "Tell me I did good?",
  dropped "尻尾を振るように" / "tail-wagging energy" from `tone`, softened
  "感情を全開で表に出す" → "感情を素直に表に出す", and lowered `typical_value_range`
  0.4-0.8 → 0.3-0.7 so the default intensity sits a notch lower (EN/JA kept in sync).
- 5 more `personality` attributes inspired by recent anime trends, bringing the
  total to 75 (personality 30):
  - `menhera` — emotionally volatile, abandonment anxiety, constant need for
    reassurance (jirai-kei trend; inward-facing, no violence — unlike yandere)
  - `battle_junkie` — lives for the thrill of combat; grins wider at stronger
    foes, bored by peace (shonen staple; distinct from hot_blooded's conviction)
  - `deadpan` — dry, flat-toned straight-man / tsukkomi who calmly retorts to
    everyone else's antics (comedy staple; reacts, unlike stoic)
  - `socially_anxious` — crippling social nerves with a loud comedic inner
    monologue; freezes and self-deprecates yet longs to connect (slice-of-life
    "bocchi" trend; panicky/talkative-internally, unlike the calm dandere)
  - `laid_back` — unhurried, unbothered "it'll work out" tempo that defuses
    others' panic (low-energy pacing, unlike optimist's bright hope)
- 5 new `personality` attributes (personality 25, total 70):
  - `deredere` — openly and unguardedly affectionate; feelings on sleeve, no defense
  - `himedere` — princess complex; expects royal treatment, but sweet when pleased
  - `kamidere` — god complex; absolute superiority, cool and imposing
  - `sadodere` — loving through teasing; provocative edge with deep affection underneath (no violence, unlike yandere)
  - `hinedere` — cynical exterior, warm heart; shows care through action rather than words

### Fixed
- Injection block now guides the model away from **monotonous, repetitive
  delivery** ("毎回同じ口調が続く"): treat catchphrases and sentence endings as a
  repertoire rather than a suffix stamped on every sentence, vary openings and
  rhythm across consecutive replies, and embody traits through word choice and
  attitude instead of self-narrating personality or adding preamble like
  "I'll now tell you…". Applies to every consumer of the blend
  (CLI / export / MCP / load).

### Changed
- Synced the attribute-count contracts to 75 across docs and tests for the two
  personality batches above: README EN/JA tables, `CLAUDE.md` / `CONTRIBUTING.md`
  count notes, the always-loaded `skills/hersona/SKILL.md` taxonomy (bumped to
  v0.5.0) and `REFERENCE.md` checklist, plus the hardcoded counts in
  `test_attributes` / `test_cli` / `test_mcp` / `test_compatibility` /
  `test_attach` (these are count contracts that must track the total).
- **Optimized per-turn injection cost** (conversations got "heavy" with the
  skill active). The three overlapping anti-repetition / naturalness notes are
  consolidated into a single `response_style_directive(lang, *, has_catchphrases,
  has_sentence_endings)` emitted once after the weight guidance, omitting the
  catchphrase/ending clause when those sections are absent. Shaves up to ~190
  chars per injected block (e.g. `washi+tsundere` strong: 1283 → 1091 chars).
  `catchphrase_usage_directive` is retained (still used by SOUL.md rendering).
- **Slimmed `skills/hersona/SKILL.md`** (~32k → ~22k chars, the part loaded
  into context whenever the skill is active) by moving flag deep-dives, the
  verification checklist, one-shot recipes, and version history into a new
  on-demand `skills/hersona/REFERENCE.md`. SKILL bumped to v0.3.0.

## [1.3.0] - 2026-06-17

初回フルリリース（measure /strict + SOUL.md memory + export 5 形式 全部入り）。
後に semver ロールバック経由で [0.2.0] および [1.4.0] が連続リリースされたため、
機能セットの参照は [1.4.0] を参照。

## [0.2.0] - 2026-06-17

> **Yanked 推奨**: semver ロールバック産。`pip install hersona` は [1.4.0] を解決。
> このリリースで追加された機能はない（[1.3.0] と同じコードを別 version 文字列で
> publish しただけ）。PyPI 履歴保持目的のみで存在。

## [1.4.0] - 2026-06-17

### Added
- `hersona measure --strict` / `--check-prompt`: when the score falls below (or
  above) the expected band, emit a pasteable self-audit prompt covering
  catchphrases, sentence endings, `conflicts_with` warnings, and weight level
  alignment. The prompt is generated deterministically from `WEIGHT_GUIDANCE` +
  attribute YAML; no LLM dependency. New public API
  `hersona.core.pre_response_check_prompt(names, weight_level, last_response=None, lang="en")`.
- `Recommendation.intensity_baseline` (and `Preset.intensity_baseline`):
  when `hersona recommend --apply` produces a blend, the engine now also runs
  `verify_intensity` against a synthetic ideal sentence and stores the
  expected band on the result. Future sessions can compare the current
  `hersona measure` output against this baseline. 10 new tests.
- SOUL.md `## Recent Context` block: `render_soul(..., memory=...)` and
  `write_soul(..., memory=...)` accept a caller-supplied `dict[str, str]`
  (≤16 keys, ≤512 chars per value, key pattern `^[a-z0-9_]{1,32}$`) and
  append a `## Recent Context` section after `## 4. Behavioral Guidelines`.
  The block is purely the *shape* — content population (e.g. LLM-based memory
  extraction) is the host agent's responsibility. `hersona soul` and
  `hersona persistent` gain `--memory <json>` and `--memory-file <path>`
  flags. `run_persistent` also accepts both. Markdown special chars in values
  are escaped to prevent injection. 10 new tests, 0 schema change,
  semver-additive.
- Export formats: `--format openai_assistants` and `--format langchain_system_message`
  added to `hersona export`. `EXPORT_FORMATS` grows from 3 to 5 entries. Both
  reuse `render_blend` for the prompt text and namespace hersona-specific
  fields (`hersona_version`, `hersona_blend`, `hersona_weight`,
  `hersona_content_lang`, `hersona_conflicts`) under `metadata` /
  `response_metadata` to avoid collisions. No `openai` / `langchain` Python
  dependency introduced — outputs are plain JSON. New public API:
  `hersona.core.export_for_openai_assistants(...)` and
  `hersona.core.export_for_langchain_system_message(...)`. 6 new tests, 0
  schema change, semver-additive.
- `hersona persistent --target {claude,codex,cursor,gemini}`: write the persona to other
  agent tools' auto-loaded convention files, not just Hermes. `claude` → `CLAUDE.md`
  (`~/.claude/CLAUDE.md` with `--global`), `codex`/`agents` → `AGENTS.md`, `cursor` →
  `.cursorrules`, `gemini` → `GEMINI.md`. `--output` overrides the path; `--global` targets
  the home location. The persona body reuses the SOUL renderer with a tool-neutral header
  (the Hermes-only "正式名称: Hermes Agent" line is omitted). Hermes-only flags
  (`--auto-config` / `--apply`) are ignored with a notice for non-hermes targets. Core logic
  in `hersona/core/targets.py` (`TARGETS`, `write_target`, `render_for_target`); 17 + 4 new tests.
- `hersona persistent --apply`: runs `hermes config set agent.personality <name>` to activate
  the personality immediately (the flat `agent.personality` key is not nested YAML, so
  `hermes config set` is safe here). Reports `hermes not found` gracefully when the CLI is absent.
- `hersona persistent --auto-config`: automatically writes the `agent.personalities.<name>`
  entry to `~/.hermes/config.yaml` via PyYAML direct edit — bypassing `hermes config set`
  (Pitfall 8: nested YAML corruption). A `.bak` backup is created before any write, and
  the file is re-validated after writing. `--force` enables overwriting an existing entry.
  `--config-path` overrides the target file. Core logic in `hersona/core/config_writer.py`
  (`write_personality`, `ConfigWriteResult`); 12 new tests.
- fix: `default_soul_path()` now returns `~/.hermes/SOUL.md` (HERMES_HOME root) instead
  of `~/.hermes/profiles/<profile>/SOUL.md`. Local Hermes CLI reads only the root path
  (`prompt_builder.py: soul_path = get_hermes_home() / "SOUL.md"`); profile-specific
  paths are Hermes One only and not read by the local CLI. The `profile` argument is
  kept for backward compatibility but is now ignored.
- C: new speech attribute `hiroshima_ben` (Hiroshima dialect) — 65 attributes total
  (speech 26 = ja 21 + en 5). Assertive '-ja / -jakee / -kee / -toru' endings and the
  'buchi' intensifier; uses the new `first_person` field (わし / わしゃ / うち). Conflicts with
  the polite/refined registers (keigo / onee_kotoba / archaic / princess_speech).
- C: MCP server (`hersona-mcp`, IMPROVEMENT_PLAN M3) via the optional `mcp` extra
  (`pip install "hersona[mcp]"`). Exposes `list_attributes` / `show_attribute` / `blend` /
  `export` / `recommend_blend` / `compatibility` tools to MCP-aware agents. Pure tool logic
  lives in `hersona/mcp/tools.py` (no `mcp` dependency, fully tested); `hersona/mcp/server.py`
  is a thin FastMCP wiring layer that lazy-imports `mcp` and raises a clear install hint when
  it is absent. 12 new tests.
- C: agent export — `hersona export <names...> --format {json,messages,markdown}` and
  `export_blend()` (exported from `hersona.core`, documented in `docs/PUBLIC_API.md`) hand a
  blend off to other agent frameworks (LangGraph / LangChain / OpenAI / Anthropic). `json` is
  structured (metadata + system prompt + per-attribute summary + conflicts), `messages` is a
  `[{"role":"system","content":...}]` array, `markdown` is the raw injection block. Reuses
  `render_blend`. Core logic in `hersona/core/export.py`; 8 + 4 new tests.
- C: shell tab-completion via the optional `completion` extra (`pip install "hersona[completion]"`).
  `argcomplete` completes subcommands, attribute names (`show`/`blend`/`diff`/`preview`/`measure`/`save`),
  and preset names (`load`). The CLI is unchanged without it (completion simply absent); enable with
  `eval "$(register-python-argcomplete hersona)"`.
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

### Changed
- `docs/app/` live demo: the "体験デモ: 人格が変わる" persona picker is now a native
  `<select>` pull-down instead of a flex-wrap row of buttons. Mobile users get the
  OS-native wheel/dialog picker (iOS / Android), with `appearance: menulist-button`,
  `min-height: 44px` (Apple HIG / Material touch target), `font-size: 16px` (prevents
  iOS Safari's auto-zoom on focus), and `width: 100%` on screens ≤ 480 px. The
  `<label>` is wired to the `<select>` via `for`/`id` and `aria-label`. JS-side:
  `renderDemo()` now builds `<option>`s from `state.showcase.items` with the
  `state.lang`-aware label (ja / en / "ja / en" in 併記 mode) and listens to `change`
  instead of `click`. A `<noscript>` fallback message is shown when JS is disabled.

### Fixed
- `docs/app/app.js` `renderGallery()` was throwing `TypeError: Cannot read properties
  of undefined (reading 'ja')` whenever the catalog contained a `visual`-category
  attribute (5 templates: `animal_ears` / `glamorous` / `glasses` / `petite` /
  `silver_hair`). `CAT_LABEL` and `CAT_ORDER` were missing the `visual` key, so
  `CAT_LABEL["visual"]` returned `undefined` and the `.ja` lookup blew up. Added
  `visual: { ja: "見た目", en: "Visual" }` to `CAT_LABEL` and inserted `"visual"`
  between `"speech"` and `"archetype"` in `CAT_ORDER`. Verified via jsdom: the
  gallery / blend filter chips now render `見た目 (5)` and visual cards show
  "見た目" as `card-cat`; gallery counts add up to 65 (性格 20 / 口調 26 / 見た目 5 /
  アーキタイプ 9 / 趣味 5). No more render errors in the console.

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
