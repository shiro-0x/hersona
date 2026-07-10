# hersona Public API (semver scope)

> The symbols listed in this document are hersona's **public API** and are
> subject to semver. Breaking changes only happen in a major version.
> Modules/functions prefixed with `_`, and any symbol not listed here, are
> internal implementation details and may change without notice.
>
> External projects (e.g. hersona-duet) must import only the public exports of
> `hersona.core`. Consistency is enforced mechanically by
> `tests/test_public_api.py`.

日本語版: [`PUBLIC_API.md`](./PUBLIC_API.md)

## Import path

Everything is imported from `hersona.core` (matches `__all__` in
`hersona/core/__init__.py`):

```python
from hersona.core import render_blend, load_matrix, verify_intensity, weight_for_score
```

## attach / blend — attribute resolution and injection-block composition

| Symbol | Description |
|---|---|
| `available_attributes(*, public_root=None, user_root=None) -> dict[str, dict]` | Available attributes as `{name: {category, source, path}}`. If a user-namespace attribute shares a name with a public one, the user version wins |
| `load_attribute(name, *, public_root=None, user_root=None) -> dict` | Resolve an attribute name to its YAML dict. Accepts both bare (`tsundere`) and category-qualified (`personality/tsundere`) names (a qualified name must also match the category). Raises `KeyError` if not found |
| `render_blend(names, *, matrix=None, public_root=None, user_root=None, weight=WeightLevel.MODERATE, use_case=None, use_case_root=None) -> BlendResult` | Compose multiple attributes into a system-prompt injection block. Conflicts are appended as a warning. When `use_case` is given, an English Operating Mode block is appended at the end |
| `BlendResult` | `.names: list[str]` / `.attributes: list[dict]` / `.conflicts: list[tuple[str, str]]` / `.prompt: str` |

## use cases / Operating Modes — task-specific prompt discipline

| Symbol | Description |
|---|---|
| `available_use_cases(*, root=None) -> dict[str, dict]` | Available use-case / Operating Mode prompt packs as `{use_case_id: metadata}` |
| `load_use_case(name, *, root=None) -> dict` | Load a use-case prompt pack from `use_cases/*.yaml`, validated against `schema/use_case.schema.json`. Raises `KeyError` if not found |
| `validate_use_case(data) -> None` | Validate a use-case prompt pack dict. Raises a `ValueError`-family exception on schema violations |
| `render_use_case_block(data) -> str` | Render a use-case prompt pack into an English `## Operating Mode: ...` injection block |

## export — hand-off to other frameworks

| Symbol | Description |
|---|---|
| `export_blend(names, *, weight=WeightLevel.MODERATE, fmt="json", matrix=None, public_root=None, user_root=None) -> str` | Convert a blend to `json` (structured) / `messages` (`[{role:system,content}]`) / `markdown` (raw injection block) / `openai_assistants` / `langchain_system_message`. Reuses `render_blend` |
| `EXPORT_FORMATS` | Tuple of supported formats (`("json", "messages", "markdown", "openai_assistants", "langchain_system_message")`) |
| `export_for_openai_assistants(names, *, weight=WeightLevel.MODERATE, matrix=None, public_root=None, user_root=None) -> str` | JSON for the OpenAI Assistants API `instructions` field (`{"model": "gpt-4o", "instructions": ..., "metadata": {"hersona_*": ...}}`). Does not generate fixed-character fields (`first_mes` / `scenario`) |
| `export_for_langchain_system_message(names, *, weight=WeightLevel.MODERATE, matrix=None, public_root=None, user_root=None) -> str` | LangChain `SystemMessage`-compatible JSON (`{"type": "system", "content": ..., "response_metadata": {"hersona_*": ...}}`) |

## compatibility — the compatibility matrix

| Symbol | Description |
|---|---|
| `load_matrix(attributes_root=None) -> CompatibilityMatrix` | Load compatibility relations across all attributes |
| `CompatibilityMatrix` | `.attributes` / `.is_compatible(a, b)` / `.conflicts(a, b)` / `.relation(a, b)` / `.check_blend(names) -> list[tuple[str, str]]` |
| `Relation` | Relation enum (compatible / conflict / neutral) |
| `Attribute` | An attribute's view inside the matrix |

## weight — the intensity dial

| Symbol | Description |
|---|---|
| `WeightLevel` | `NONE / MILD / MODERATE / STRONG` (StrEnum; maps to the schema's `weight_dimension`) |
| `WEIGHT_GUIDANCE: dict[WeightLevel, str]` | Prompt-injection guidance text for each intensity |
| `coerce_level(value) -> WeightLevel` | Normalize a string / `WeightLevel` |
| `normalize_catchphrase(item) -> dict` | Normalize a catchphrase item (str or `{phrase, when}` dict) into a `{phrase, when}` dict (trigger-annotation support) |
| `catchphrase_subset(catchphrases, level) -> list[dict]` | The exposure subset of catchphrases for a given intensity. Each item is already normalized to `{phrase, when}` via `normalize_catchphrase` |
| `suggest_weight(score: float) -> WeightLevel` | Infer a suggested intensity from **recommend's fit score (0–3+)** |
| `weight_for_score(score, *, previous=None, thresholds=(25, 55, 85), hysteresis=5.0) -> WeightLevel` | Map a **continuous 0-100 score** to an intensity. With `previous` set, applies hysteresis (keeps the current level until the score crosses the boundary ± hysteresis). Used by duet's affection/emotional-temperature dial |

## intensity — deterministic scoring of output intensity

| Symbol | Description |
|---|---|
| `measure_intensity(text, attributes) -> IntensityReport \| None` | Score 0-100 from surface metrics (60% sentence-ending match + 40% catchphrase density). Returns `None` if there is no speech attribute |
| `verify_intensity(text, attributes, level) -> IntensityReport \| None` | Score + compare against the expected band. `report.status` is `"pass" / "under" / "over"` |
| `expected_band(level) -> tuple[int, int]` | Expected score band for a given intensity |
| `format_report(report, level) -> str` | Human-readable one-line report |
| `pre_response_check_prompt(names, weight_level, last_response=None, lang="en") -> str` | A self-audit prompt tailored to the intensity level, used by `measure --strict` / `--check-prompt` |
| `IntensityReport` | `.score` / `.endings_rate` / `.catchphrase_hits` / `.band` / `.status` |

## recommend — diagnostic quiz → recommendation

| Symbol | Description |
|---|---|
| `DEFAULT_QUIZ` / `DEFAULT_QUIZ_PATH` / `RECOMMEND_THRESHOLDS` | The default (ja) quiz and threshold constants |
| `QuizQuestion` / `QuizOption` / `WeightMagnitude` | Quiz data types |
| `load_quiz(path=None) -> list[QuizQuestion]` | Load a quiz |
| `score_answers(answers, quiz=None) -> dict[str, float]` | Answers → attribute scores |
| `recommend(answers, ...) -> Recommendation` | A conflict-resolved recommended blend (`.blend` is input-compatible with `render_blend`) |

## authoring — creating local attributes (with a validation gate)

| Symbol | Description |
|---|---|
| `build_attribute(...) -> dict` / `override_attribute(base, **fields) -> dict` | Assemble an attribute dict / derive an overridden copy of an existing attribute |
| `validate_attribute(data) -> list[str]` | Schema validation (list of error messages) |
| `save_attribute(data, *, ...) -> Path` | Save to the user namespace. Schema violations raise `ValidationGateError` |
| `list_user_attributes()` / `user_attributes_root()` | Enumerate the user namespace / its root |
| `find_proper_noun_risks(data) -> list[str]` / `assert_shareable(data)` | Detect proper-noun risk / guard that applies **only when sharing** (`ShareGuardError`) |
| `AuthoringError` / `ValidationGateError` / `ShareGuardError` | Exception hierarchy |

## presets — local storage of blend presets

| Symbol | Description |
|---|---|
| `Preset` | `.name` / `.attributes: list[str]` / `.weight` / `.note` / `.created` / `.tags` |
| `save_preset(name, attributes, *, weight="moderate", note="", tags=None, root=None, overwrite=False) -> Path` | Save a blend (attribute names + intensity) to `~/.hermes/presets/<name>.yaml` |
| `load_preset(name, *, root=None) -> Preset` | Load a preset by name. Raises `PresetError` if missing |
| `list_presets(root=None) -> list[Preset]` | Enumerate saved presets, alphabetically by name |
| `delete_preset(name, *, root=None) -> Path` | Delete a preset |
| `presets_root() -> Path` | Root directory for presets (`HERSONA_PRESETS_DIR`, or a `presets/` sibling of the attributes root) |
| `PresetError` | Exception for preset operations |

## soul — SOUL.md persistence (writes to the official Hermes One spec)

| Symbol | Description |
|---|---|
| `SoulRenderResult` | `.content` / `.output_path` / `.blend_names` / `.weight` / `.lang` / `.name` / `.memory` / `.use_case` |
| `render_soul(names, *, weight="moderate", name="Libra", matrix=None, public_root=None, user_root=None, memory=None, use_case=None, use_case_root=None) -> str` | Render a blend as a SOUL.md markdown string (official 4 elements: name / personality / tone / behavioral guidelines). When `use_case` is given, also generates `## Operating Mode`. Raises `ValueError` on conflict detection |
| `write_soul(output, names, *, weight="moderate", name="Libra", append=False, overwrite=False, force=False, matrix=None, public_root=None, user_root=None, memory=None, use_case=None, use_case_root=None) -> SoulRenderResult` | Write SOUL.md to `output`. Raises `FileExistsError` by default if the file already exists (controlled by `overwrite` / `force` / `append`). User-added text below `<!-- hersona:gen-end -->` is preserved across `overwrite` / `force` regeneration |
| `default_soul_path(profile="default") -> Path` | Returns `~/.hermes/SOUL.md` (`profile` is accepted for backward compatibility but currently ignored) |

## persistent — automatic SOUL.md write-out + config.yaml block display

| Symbol | Description |
|---|---|
| `PersistentResult` | `.persona_name` / `.config_yaml_block` / `.soul_result` / `.config_write_result` / `.apply_result` / `.skipped: dict` / `.memory` / `.use_case` |
| `run_persistent(names, *, weight="moderate", profile="default", without_soul=False, without_config=False, force=False, config_yaml_output=None, auto_config=False, config_path=None, apply=False, memory=None, memory_file=None, use_case=None, persona_name=None) -> PersistentResult` | Run persistent mode: automatic SOUL.md write-out (on by default) + generation of a YAML block to append to `config.yaml`. When `use_case` is given, both the config block and SOUL.md include the Operating Mode. With `persona_name=None` (default), the persona name is auto-derived from the blend; passing `persona_name="my_pack"` overrides it and writes to `agent.personalities.my_pack` (used internally by `install_persona` in `hersona/core/personas.py`) |

## self_intro — deterministic lint for public-facing self-introductions

| Symbol | Description |
|---|---|
| `IntroViolation` | `.rule` / `.message` / `.excerpt` |
| `IntroLintResult` | `.ok` / `.violations` — `.to_dict()` for JSON serialization |
| `lint_self_intro(text, *, allow_handles=None, canonical=False) -> IntroLintResult` | Mechanical checks from `docs/guides/self-introduction.*` (AI self-disclosure, meta-commentary, unauthorized `@`-handles, etc.). CLI: `hersona lint-intro` |
| `merge_self_intro_guide(memory, *, lang="ja") -> dict[str, str] \| None` | Fill in unset `self_intro_style` / `privacy_inner_circle` from the guide |
| `lint_memory_self_intro_canonical(memory, *, allow_handles=None, canonical=True)` | Lint the `self_intro_canonical` key inside memory (`None` = key absent) |
| `self_intro_guide_defaults(lang="ja") -> dict[str, str]` | A guide-derived template with just the 2 keys |

`soul` / `persistent` CLI: `--with-self-intro-guide`, `--lint-self-intro`, `--lint-self-intro-strict`, `--allow-handle` (repeatable).

## Where the data lives (reference)

Regardless of install method, attributes (`attributes/`) and the schema
(`schema/attribute.schema.json`) are resolved internally by the library
(repository checkout first, falling back to the wheel-bundled
`hersona/data/`). External projects never need to construct these paths
themselves.

## Compatibility policy

- Removing a public symbol, or an incompatible signature change: **major** release
- Adding a public symbol, or adding a keyword argument with a default: **minor** release
- Adding attribute data or wording fixes: **minor / patch** release
- Removing an attribute from `attributes/`, or changing an `attribute_name`, is
  treated as a data-compatibility break: **major**
