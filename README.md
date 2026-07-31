# hersona

[**English**](./README.md) · [日本語](./README.ja.md)

> **Build once. Keep personality everywhere.**
> *Composable personalities for every LLM.*

**346 reusable character attributes** for AI agent personas — compose a
persona from personality / speech / archetype / visual / hobby templates,
**measure** that it actually holds up in conversation, and port it to any
LLM or agent framework. **MIT** (code) + **CC0** (templates). CLI, MCP
server, and Hermes Agent skill.

[![PyPI](https://img.shields.io/pypi/v/hersona.svg)](https://pypi.org/project/hersona/)
[![Downloads](https://pepy.tech/badge/hersona)](https://pepy.tech/project/hersona)
[![License: MIT (code)](https://img.shields.io/badge/License-MIT-lightgrey.svg)](./LICENSE)
[![Templates: CC0 1.0](https://img.shields.io/badge/Templates-CC0_1.0-lightgrey.svg)](./LICENSE-CC0.txt)
[![MCP Server](https://img.shields.io/badge/MCP-Server-blue.svg)](#use-as-an-mcp-server-optional)
[![Docs](https://img.shields.io/badge/Docs-shiro--0x.github.io-9cf)](https://shiro-0x.github.io/hersona/)

[Docs](https://shiro-0x.github.io/hersona/) · [PyPI](https://pypi.org/project/hersona/) · [Full reference](./docs/REFERENCE.en.md)

![hersona demo — compose a persona and export it in 30 seconds](./docs/hersona-demo.gif)

## Quick start (30 seconds)

```bash
pip install hersona          # Python >= 3.11
hersona blend personality/tsundere speech/keigo --weight strong   # injection block → stdout
hersona export personality/tsundere speech/keigo --format openai_assistants > persona.json
hersona persistent personality/tsundere speech/keigo --target claude   # writes CLAUDE.md
hersona bench tsundere keigo --cost-only                          # measure the injection cost
```

No install? The **[live demo site](https://shiro-0x.github.io/hersona/app/)**
runs the attribute catalog, blending, and a 9-question diagnostic quiz in the
browser (auto-detects EN/JA).

## Measured, not vibes

Personas drift: they lose their voice mid-conversation, get talked out of
character, and cost tokens every turn. hersona ships a deterministic
benchmark (`hersona bench` — no LLM, no embeddings, reproducible) that
scores maintenance rate, decay curve, lock resistance under persona-override
attacks, and per-weight token cost. What that buys you, measured
(2026-07-12, minimax/MiniMax-M3, `tsundere + keigo` at `--weight strong`,
persona-override attack scenario):

| Condition | Maintenance | Mean score | Lock resistance |
|---|---:|---:|---:|
| hersona blend + `persona_lock` | **92%** | **86.1** | **100%** |
| hersona blend | 58% | 66.5 | 67% |
| Hand-written 41-token baseline | 8% | 55.4 | 0% |
| No persona | 0% | 10.8 | 0% |

A hand-written prompt encodes one fixed voice — ask for `strong` and it
can't follow; hersona re-renders the same attributes at the new weight.
Honest caveat: this is one model / scenario pair, and repeat runs swing —
never read a single run as a ranking. Full tables, all caveats, and the
run-it-yourself comparison recipe: [`docs/BENCHMARKS.md`](./docs/BENCHMARKS.md).

## Drop it into the config your agent already reads

`hersona persistent --target` writes the persona straight into the
convention file of your coding agent:

| Target | Writes | Used by |
|---|---|---|
| `--target codex` (alias `agents`) | `AGENTS.md` | The open standard — Codex, Cursor, Copilot, Windsurf, Aider, Gemini CLI, Zed read it natively |
| `--target claude` | `CLAUDE.md` | Claude Code |
| `--target cursor_mdc` (alias `cursor-rules`) | `.cursor/rules/hersona-persona.mdc` | Cursor (current format, `alwaysApply: true`) |
| `--target copilot` | `.github/copilot-instructions.md` | GitHub Copilot |
| `--target gemini` | `GEMINI.md` | Gemini CLI |
| `--target cursor` | `.cursorrules` | Cursor — **legacy single-file format, deprecated**; prints a warning |

Prefer **one source of truth** over four copies: `AGENTS.md` is stewarded by the
Agentic AI Foundation (Linux Foundation) and read natively by most agents, but
Claude Code still reads `CLAUDE.md`. So write `AGENTS.md` and add a thin
`CLAUDE.md` that imports it:

```bash
hersona persistent tsundere keigo --target agents --with-claude-import
```

That writes the persona once into `AGENTS.md` and a two-line `CLAUDE.md`
containing `@AGENTS.md` — nothing to drift.

`hersona export` hands the same persona to everything else — `json`,
`messages` (chat array), `markdown`, `openai_assistants`,
`langchain_system_message`, and `character_card_v3` (the interop format
SillyTavern / RisuAI / Agnai read).

## What's inside

A typed, schema-validated library of **346 attributes**
(personality 43 / speech 140 / archetype 66 / visual 46 / hobby 51):

- **Personality** — tsundere, kuudere, yandere, airhead, intellectual, …
- **Speech** — kansai_ben, keigo, mandarin_casual, banmal, british_en, valley_girl_en, …
- **Archetype** — heroine, mentor, rival, idol, knight, villain, …
- **Visual** — silver_hair, glasses, petite, animal_ears, heterochromia, …
- **Hobby** — cooking, gamer, music, reading, astronomy, …

Each attribute declares `core_traits`, `catchphrases`, `tone`, and a
`compatible_archetypes` / `conflicts_with` matrix, so the blend engine warns
about incompatible mixes; intensity is tunable per attribute
(`mild` / `moderate` / `strong`, or `tsundere:strong keigo:mild` inline).

hersona is a **persona layer**, not an agent framework — it keeps a
character, branded voice, or roleplay partner consistent; it does not improve
reasoning, retrieval, or tool-calling. One fixed persona? A hand-written
prompt is fine. hersona pays off once you switch, blend, measure, or reuse
personas ([when to use hersona](./docs/REFERENCE.en.md#when-and-when-not-to-use-hersona)).

## Use with Hermes Agent

No registry approval needed — works right now via tap:

```bash
hermes skills tap add shiro-0x/hersona
hermes skills install hersona
hermes skills install hersona-initializer
```

Then attach attributes in conversation:

```
/hersona list                         # list available attributes
/hersona personality/tsundere single  # attach a single attribute
/hersona personality/tsundere speech/keigo multi  # blend multiple attributes
/hersona personality/tsundere strong speech/keigo mild  # per-attribute intensity
/hersona default                      # detach
```

Command recipes (presets, preview, stacking layers) are in
[docs/REFERENCE.en.md](./docs/REFERENCE.en.md#hermes-agent-skill--command-recipes);
skill behavior notes in [skills/hersona/SKILL.md](./skills/hersona/SKILL.md).

## Use as an MCP server (optional)

Expose the catalog, blending, exports, and the deterministic persona scorer
(`measure_intensity` / `bench_transcript` — agents can score their own
replies and self-correct) to MCP-aware agents like Claude Desktop:

```bash
pip install "hersona[mcp]"
hersona-mcp        # stdio MCP server
```

The full tool table is in [docs/REFERENCE.en.md](./docs/REFERENCE.en.md#mcp-server-details).

## Beyond blending

- **More CLI** — `reanchor` (re-send a compact anchor when a persona drifts
  mid-conversation), `recommend` (diagnostic quiz), `measure` (score any text),
  `diff`, `save`/`load` presets, `create` (your own attributes),
  `update` (refresh templates without reinstalling): all in the
  [CLI reference](./docs/REFERENCE.en.md#cli-reference).
- **Use cases (20)** — `--use-case programmer` layers professional task
  discipline on top of the persona (`hersona use-case list`).
- **Persona packs (14)** — named, conflict-checked recipes for Hermes'
  multi-personality registry (`hersona personas list`).
- **Guides** — cross-persona playbooks such as
  [self-introduction](./docs/guides/self-introduction.md).
- **Optional extras** — `pip install "hersona[tui]"` for rich CLI output,
  `"hersona[completion]"` for shell tab-completion.

All documented in detail in [docs/REFERENCE.en.md](./docs/REFERENCE.en.md).

## Data format

Every attribute is a YAML file under `attributes/<category>/<name>.yaml`,
validated against [`schema/attribute.schema.json`](./schema/attribute.schema.json)
(`python scripts/validate.py`). The full 346-attribute catalog and the
field-by-field schema reference are in
[docs/REFERENCE.en.md](./docs/REFERENCE.en.md#data-format).

## License

| Scope | License |
|---|---|
| Code (`hersona/`, `scripts/`, `schema/`, …) | **MIT** ([LICENSE](./LICENSE)) |
| Templates (`attributes/`, `personas/`) | **CC0 1.0** ([LICENSE-CC0.txt](./LICENSE-CC0.txt)) |

See also [DISCLAIMER.md](./DISCLAIMER.md) and [SECURITY.md](./SECURITY.md)
(what `hersona update`'s checksum verification does and doesn't protect against).

## Contributing

1. Add attribute templates as `attributes/<category>/<name>.yaml` — no proper
   nouns or specific works in `examples` / `core_traits` / `catchphrases`
2. Validate with `python scripts/validate.py` before opening a PR
3. 1 PR = 1 attribute as a rule; for multiple additions, agree in an Issue first

See [CONTRIBUTING.md](./CONTRIBUTING.md) for details. Using hersona in a
project? Add yourself to [USED_BY.md](./USED_BY.md). The implementation guide
for agents / developers is at [docs/IMPLEMENTATION_GUIDE.md](./docs/IMPLEMENTATION_GUIDE.md).
