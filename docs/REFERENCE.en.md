# hersona Reference

[**English**](./REFERENCE.en.md) · [日本語](./REFERENCE.md)

The full reference for hersona: when to use it, the complete CLI, Hermes
skill recipes, use cases, persona packs, export formats, the attribute
catalog, and the YAML schema. The [README](../README.md) covers only the
essentials; everything else lives here.

- [When (and when not) to use hersona](#when-and-when-not-to-use-hersona)
- [CLI reference](#cli-reference)
- [Hermes Agent skill — command recipes](#hermes-agent-skill--command-recipes)
- [Professional Operating Modes / use cases](#professional-operating-modes--use-cases)
- [Persona packs](#persona-packs)
- [Exporting to OpenAI Assistants and LangChain](#exporting-to-openai-assistants-and-langchain)
- [MCP server details](#mcp-server-details)
- [Use with other LLMs](#use-with-other-llms)
- [Guides](#guides)
- [Data format](#data-format)
- [Catalog history](#catalog-history)

## When (and when not) to use hersona

Hersona is a **persona layer** for defining and maintaining a character's
personality and speech style across conversations. It helps AI systems stay
consistent as a **character, branded voice, roleplay partner, virtual
influencer, mascot, or conversational persona**. It is not a reasoning
engine, RAG pipeline, or tool-use framework.

| You need | Reach for |
|---|---|
| One fixed persona, never switched | A hand-written system prompt — hersona adds no value here |
| Several personas, swapped per session/user, with intensity control | **hersona** (`blend` / `soul` / `persistent`) |
| To *know* whether a persona held up over a long conversation | **hersona** (`measure` / `verify_intensity` — deterministic, not vibes) |
| Conflict-free trait combinations at scale (many attributes × many combos) | **hersona** (`compatible_archetypes` / `conflicts_with` matrix) |
| Better reasoning, retrieval, or tool-calling | LangGraph, OpenAI Agents SDK, LlamaIndex, Semantic Kernel — hersona's `export` formats hand a persona *into* these, it doesn't replace them |
| A one-off character for a single project | Your own YAML/prompt is fine too — hersona helps once you have more than one persona, or need to reuse the same ones across projects |

See [`BENCHMARKS.md`](./BENCHMARKS.md) for how `hersona bench` measures
persona-maintenance rate and injection token cost, and how to run your own
hersona-vs-baseline comparison rather than take our word for it.

## CLI reference

After `pip install hersona` (Python >= 3.11), the `hersona` command is available.
For local development from a checkout, use `pip install -e .` or `python -m hersona.cli`:

```
hersona list                                  # list available attributes (public + user)
hersona show tsundere                          # attribute details
hersona matrix --json                          # dump the compatibility matrix as JSON
hersona blend tsundere keigo --weight strong   # compose attributes into an injection block (with intensity)
hersona blend tsundere:strong keigo:mild       # per-attribute intensity override (`:<level>` suffix; also works on `export`)
hersona blend tsundere keigo --compact         # shorter style directive (-14% to -19% injection cost; maintenance under --compact not yet verified)
hersona blend airhead intellectual --suggest   # on conflict, suggest non-conflicting replacements (stderr)
hersona blend tsundere keigo --disclosure       # add an AI-disclosure directive that overrides persona lock (opt-in; not a compliance guarantee)
hersona diff tsundere dandere                  # compare two attributes (common / only-one fields + relation)
hersona preview tsundere kyoto_ben --weight strong  # injection block + sample phrases (no LLM)
hersona recommend                              # diagnostic quiz -> recommendation (interactive; en UI routes to English speech)
hersona recommend --answers distance=1,speech=0,role=1 --apply  # also print the injection block
hersona recommend --export openai_assistants > my_agent.json  # quiz result straight to any export format (no re-entry)
hersona recommend --soul --profile myagent     # quiz result straight to SOUL.md (--dry-run / --force)
hersona recommend --save from_quiz             # quiz result saved as a reusable preset
hersona create --category personality --name my_attr \
  --display-ja マイ属性 --display-en MyAttr \
  --desc-ja 説明 --desc-en desc --example "..."  # create an attribute and save to the user namespace
hersona measure kyoto_ben --weight strong --text "ようおいでやすどす"  # score intensity metrics of output
hersona measure tsundere heroine --weight moderate --input out.txt       # intensity metrics of a blend
hersona bench tsundere keigo --demo --turns 6  # persona-maintenance-rate + token-cost self-check (see BENCHMARKS.md)
hersona bench tsundere keigo --cost-only       # measure only the injection cost (chars / approx. tokens)
hersona reanchor tsundere keigo --cost            # compact single-shot anchor to resend when the persona drifts (17-30% of the full block)
hersona persistent tsundere keigo --target claude  # write the persona into CLAUDE.md (also: codex/agents, cursor, gemini)
hersona persistent tsundere keigo --target agents --with-claude-import  # AGENTS.md + a thin CLAUDE.md that imports it (one source of truth)
hersona persistent tsundere keigo --target cursor_mdc  # .cursor/rules/hersona-persona.mdc (Cursor's current format)
hersona save my_tsun tsundere keigo --weight strong  # save a blend as a reusable named preset (local)
hersona presets                                # list saved blend presets
hersona load my_tsun                           # replay a saved preset as an injection block
hersona export tsundere keigo --format messages  # export a blend for other frameworks (json/messages/markdown)
hersona soul puppyish keigo heroine --use-case planner --force  # write SOUL.md with a persistent Operating Mode
hersona update                                 # download the latest attribute data from the repository
hersona update --ref v1.9.0                    # pin to a branch / tag / commit SHA (default: main)
hersona update --clear                         # remove downloaded data and revert to the bundled templates
```

User-created attributes are saved under `~/.hermes/attributes/` (default) or the directory specified by
`HERSONA_USER_DIR`, and never mix into the public `attributes/`.

`hersona update` keeps the attribute templates fresh **without reinstalling the package**. When you
install via `pip`/wheel, `attributes/` and `schema/` are bundled at build time, so upstream additions
only land after a reinstall. `hersona update` downloads the latest `attributes/` and `schema/` from the
repository into a local data cache (`~/.hermes/data/` by default, or `HERSONA_DATA_DIR`), which takes
precedence over the bundled templates. `hersona update --clear` removes the cache and reverts to the
bundled data. The download uses only the Python standard library (no extra dependencies).

By default, `hersona update` verifies the download against a SHA-256 manifest (`checksums.json`)
fetched from a separate GitHub delivery path, aborting on a mismatch; see
[SECURITY.md](../SECURITY.md) for exactly what this does and doesn't protect against. Skip with
`hersona update --no-verify`.

Saved blend presets live under `~/.hermes/presets/` (default) or the directory specified by
`HERSONA_PRESETS_DIR`. A preset is just a named recipe (`attributes` + `weight`); `hersona load`
replays it through the same blend engine, so it always reflects the latest attribute templates.

To hand a persona off to another agent framework (LangGraph / LangChain / OpenAI / Anthropic SDK),
`hersona export <names...> --format {json,messages,markdown,openai_assistants,langchain_system_message}`
emits a portable artifact: `json` is structured data (metadata + system prompt + per-attribute summary + conflicts),
`messages` is a ready-to-use `[{"role": "system", "content": ...}]` chat array, `markdown` is the raw
injection block, and the OpenAI Assistants / LangChain formats target those frameworks directly. The same
`export_blend()` is available from `hersona.core` (see [`PUBLIC_API.en.md`](./PUBLIC_API.en.md)).

### Re-anchoring a persona that drifted mid-conversation

`persona_lock` hardens a persona against *deliberate* override attempts; it does
nothing about plain drift — the persona quietly losing its register over a long
session. [ContextEcho](https://arxiv.org/abs/2605.24279), a 23-model persona-drift
benchmark run over real agent sessions of 3,746-9,716 turns, reports that
in-session **compaction does not reliably reset** drift and that a **single-shot
anchor restores the trained register**. So the remedy is not a bigger system
prompt — it is a small block re-sent at the right moment.

```bash
hersona reanchor tsundere keigo                  # the anchor block
hersona reanchor tsundere keigo --cost           # + its char / approx-token cost vs the full block
hersona reanchor tsundere keigo --catchphrases 0 # omit the catchphrase line
```

The anchor carries only the **mechanical register** — identity line, first/second
person, sentence endings / lexical markers, a head subset of catchphrases, and one
"resume this persona now" directive. `core_traits`, `tone`, `speech_style` and the
response-style directive are deliberately left out: the anchor restores a register
the model already knows, it does not re-teach the persona. That keeps it at
**17-30% of the full injection block** (measured: 324 chars / ~81 tok for
`tsundere + keigo`, against 1931 chars / ~482 tok).

**When to fire it** — the deterministic scorer already knows. Score the persona's
own reply with `hersona measure` (or MCP `measure_intensity`) and send the anchor
when the result falls below the expected band. Over MCP that loop is
`measure_intensity` -> `reanchor`, with no LLM call on either side.

**Where to put it** — **append** it as the newest turn, or at the tail of the
system prompt. Splicing it into the stable prefix invalidates the prompt cache for
the whole conversation; tail-append is the same rule the injection block's
cache-optimal layout follows.

Honest caveat: hersona ships the anchor and the trigger signal, but the
"single-shot anchor restores the register" finding is ContextEcho's, measured on
their probe suite — not a hersona benchmark result. A with-anchor /
without-anchor run was attempted (2026-08-01, sonnet,
`long_form_topic_switch_ja`) and **failed to measure anything**: with
`persona_lock` on, the persona never drifted over those 12 turns, so there was
nothing for the anchor to repair. hersona's longest scenario is 12 turns;
ContextEcho observed drift over 3,746-9,716. Until a drift-inducing scenario
exists, this feature's rationale rests on ContextEcho's numbers, not hersona's.
Full write-up: [`BENCHMARKS.md`](./BENCHMARKS.md#feature-experiments-benchmarksrun_feature_experimentpy).

### Character Card V3 export (roleplay frontends)

`--format character_card_v3` emits the interop format read by SillyTavern, RisuAI
and Agnai (`spec: chara_card_v3`, `spec_version: 3.0`). Load the JSON as a card
directly, or embed it into a PNG `ccv3` chunk yourself.

```bash
hersona export tsundere keigo --format character_card_v3 > card.json
hersona export tsundere keigo --format character_card_v3 \
  --card-name "Aoi" --card-first-mes "...What. Don't stare." --card-scenario "After class"
```

Where each field comes from — hersona is a generic attribute library, so it
derives what it can and **leaves the rest empty rather than inventing a
character**:

| Card field | Source |
|---|---|
| `description`, `system_prompt` | the injection block (`hersona blend`) |
| `personality` | the personality attributes' `core_traits` |
| `mes_example` | `sample_dialogue` output, formatted as `<START>` / `{{char}}:` |
| `post_history_instructions` | `persona_lock`'s intent, restated in card-local wording |
| `tags`, `character_version`, `extensions.hersona` | attribute metadata + the blend recipe |
| `scenario`, `first_mes`, `alternate_greetings` | **empty** — pass `--card-scenario` / `--card-first-mes` if you want them |

`post_history_instructions` is worth noting: V3 re-sends that field *after* the
conversation history, which makes it a built-in re-anchor slot — the same idea as
[`hersona reanchor`](#re-anchoring-a-persona-that-drifted-mid-conversation), except
the frontend applies it every turn. It deliberately does **not** mention SOUL.md or
`hersona` commands, which would be dangling references inside a card.

### AI disclosure (`--disclosure`, opt-in)

`persona_lock` is on by default and tells the model to hold the persona against
requests to drop it. That is what makes a persona stick — but it can also push the
model toward **not answering "are you a human or an AI?" straight**, and several
2026 regimes require exactly that answer: California SB 243 (companion chatbots,
effective 2026-01-01), chatbot statutes in a number of other US states, and the EU
AI Act's transparency obligations (from 2026-08-02 for EU customers).

`--disclosure` (on `blend`, `export`, `soul`, `persistent`) adds a directive that:

- says plainly it is an AI when asked, in the persona's own voice,
- **explicitly overrides persona lock**,
- forbids asserting human experiences, a body, a real identity or credentials, and
- drops the persona styling and points to real human help if the user appears to be
  in crisis.

In SOUL / convention files it lands as section `### 4.4`, right after
persona_lock's `### 4.3`, with an `<!-- ai_disclosure: on -->` marker.

**This is not a compliance guarantee.** It is a prompt directive and the model may
ignore it, and most of what those rules require cannot be done from a prompt at
all — conspicuous in-UI disclosure, three-hourly reminders for known minors, age
assurance, crisis-referral implementation, auditable records. Those stay with the
operator; [`SECURITY.md`](../SECURITY.md) has the breakdown.

### Richer CLI output (optional)

Install the `tui` extra for color tables (`list`) and panels (`show`):

```
pip install "hersona[tui]"
```

It is opt-in: without `rich`, when piping/redirecting, or with `--plain` / `NO_COLOR`, the CLI prints
the same plain text as before. Set `HERSONA_FORCE_RICH=1` to keep color when piping (e.g. `| less -R`).

### Shell tab-completion (optional)

Install the `completion` extra and register the completer with your shell to tab-complete
subcommands, attribute names, and preset names:

```
pip install "hersona[completion]"
eval "$(register-python-argcomplete hersona)"   # add to ~/.bashrc / ~/.zshrc to persist
```

It is opt-in: without `argcomplete`, the CLI works exactly the same, only without completion.

## Hermes Agent skill — command recipes

Install via tap (no registry approval needed):

```bash
hermes skills tap add shiro-0x/hersona
hermes skills install hersona
hermes skills install hersona-initializer
```

Skill registry status:

| Registry | Status |
|---|---|
| [HermesHub](https://www.hermeshub.xyz/) | 🔄 under review ([PR #125](https://github.com/amanning3390/hermeshub/pull/125)) |
| [ClawHub](https://clawhub.ai/) | https://clawhub.ai/shiro-0x/skills/hersona |

Attach attributes via `/hersona <category>/<name>`:

```
/hersona                              # listing + usage help
/hersona list                         # list available attributes
/hersona show personality/tsundere    # details of a given attribute
/hersona personality/tsundere single  # attach a single attribute
/hersona personality/tsundere speech/keigo multi  # blend multiple attributes
/hersona default                      # detach
```

### Common recipes

**Make a character more tsundere without changing their archetype**

```
/hersona personality/tsundere single
```

Attaches only `tsundere` (with `weight: moderate` by default). The next
agent turn speaks with classic tsundere traits — distant on the surface,
warmer underneath — without altering the existing archetype or speech
register.

**Stack a keigo speech layer on top of an already-attached personality**

```
/hersona speech/keigo single
```

Adds `speech/keigo` to the current attachment. Useful when the existing
persona should switch to polite/formal speech (customer-support scene,
noble-archetype roleplay, etc.).

**Blend a multi-attribute persona from scratch**

```
/hersona personality/tsundere speech/keigo multi
```

Composes a brand-new persona from `tsundere` + `keigo` and replaces any
existing attachment. The `blend` engine checks `compatible_archetypes` /
`conflicts_with` first — if the two attributes fight each other (e.g.
`yandere` + `airhead`), you'll get a warning suggesting a replacement
before the attach goes through.

**Control intensity per attribute**

```
/hersona personality/tsundere strong speech/keigo mild
```

`strong` makes tsundere traits dominant (catchphrases land hard, "べ、
別にあんたのためじゃない" frequency goes up); `mild` keeps keigo as
background flavor. Intensity is per-attribute, so you can mix-and-match
within a single command.

**Save a blend as a reusable preset**

```
/hersona save my_tsun personality/tsundere speech/keigo --weight strong
/hersona load my_tsun
```

`save` writes the recipe to `~/.hermes/presets/my_tsun.yaml`; `load`
replays it on demand without re-typing the full command. Saved presets
live in the user namespace and never pollute the public `attributes/`.

**Detach everything and return to the base agent**

```
/hersona default
```

Strips every attached attribute in one shot. Useful between sessions or
when starting a fresh blend from a known clean state.

**Preview without attaching**

```
/hersona preview personality/tsundere speech/keigo --weight strong
```

Renders the injection block + sample phrases (no LLM call) so you can
review the result before committing it to the live agent context.

See [skills/hersona/SKILL.md](../skills/hersona/SKILL.md) for Hermes skill
behavior notes, and [skills/hersona/REFERENCE.md](../skills/hersona/REFERENCE.md)
for verification checklists, version history, and edge-case recipes
(saved-blend persistence, intensity measurement, MCP export). For CLI truth,
prefer `hersona --help`, this document, and [`PUBLIC_API.en.md`](./PUBLIC_API.en.md).

## Professional Operating Modes / use cases

`--use-case` layers a professional control-plane prompt on top of the selected
personality / speech attributes. The persona remains expressive, while the agent
gets task discipline for real work.

```bash
hersona use-case list
hersona use-case show programmer
hersona blend personality/tsundere speech/keigo --use-case programmer
hersona soul personality/puppyish speech/keigo archetype/heroine --use-case planner --force
hersona export personality/tsundere --format openai_assistants --use-case product_manager
```

Initial public use cases (20 total, see `PERSONA_PACKS_DESIGN.md` §6–§8):

**Initial 8 (Phase 1)**: `programmer`, `planner`, `research`, `marketing`,
`product_manager`, `qa_reviewer`, `data_analyst`, `customer_support`.

**Added 12 (PR-A W2, Phase 2)**:
`frontend_developer`, `backend_architect`, `devops_engineer`, `security_reviewer`,
`tech_writer`, `executive_assistant`, `hr_recruiter`, `tutor`, `creative_writer`,
`game_master`, `community_manager`, `streamer_copilot`.

`hersona soul ... --use-case <id>` and `hersona persistent ... --use-case <id>`
write the Operating Mode into generated SOUL.md content, so professional task
discipline survives future persona regeneration instead of living in a manual
append-only note. Regeneration also preserves user-owned text below
`<!-- hersona:gen-end -->`.

## Persona packs

A persona pack is a **named recipe** that combines one or more attributes into
a reusable persona. The pack declares `persona_name` / `blend` / `weight` /
`use_case`; the injection block is rendered at install time from the named
attributes, so attribute updates propagate automatically.

```bash
hersona personas list                          # 14 bundled packs (keigo_support, gyaru_community, …)
hersona personas show keigo_support            # blend + preview
hersona personas install keigo_support --auto-config
hersona personas install keigo_support british_pm --apply  # last one becomes agent.personality
hersona personas use keigo_support             # switch active personality
hersona recommend --install-persona my_pack    # bridge: diagnose → register in one shot
```

Shipped packs (14 total, see `PERSONA_PACKS_DESIGN.md` §6):

| Pack | Blend | Use case |
|---|---|---|
| `keigo_support` | diligent + keigo | customer_support |
| `kansai_marketer` | genki + kansai_ben | marketing |
| `tsundere_reviewer` | tsundere + blunt | qa_reviewer |
| `kuudere_analyst` | kuudere + soft | data_analyst |
| `genki_planner` | genki + casual_en | planner |
| `sensei_writer` | intellectual + sensei | tech_writer |
| `butler_assistant` | diligent + butler | executive_assistant |
| `onee_recruiter` | sociable + onee_kotoba | hr_recruiter |
| `samurai_devops` | stoic + samurai_lol | devops_engineer |
| `vtuber_streamer` | playful + vtuber | streamer_copilot |
| `miko_tutor` | serious + miko | tutor |
| `british_pm` | pragmatist + british_en | product_manager |
| `gyaru_community` | sociable + gyaru | community_manager |
| `warawa_gamemaster` | mysterious + warawa | game_master |

**What sets persona packs apart from generic agent catalogs:**

| Generic agent catalogs | hersona persona packs |
|---|---|
| Role only, no personality control | Persona × use-case × **intensity dial** |
| Static templates | Conflict-checked blends, **measurable maintenance** (incl. lock resistance under persona-override attacks) via `hersona bench` |
| Generic tool plumbing | **Native for Hermes' multi-personality registry** |

All 14 bundled packs pass `validate_persona()` (zero errors) on every CI run
via `tests/test_personas.py::test_all_shipped_personas_validate_clean`; the
table above is the authoritative list — schema additions must follow the
`PERSONA_PACKS_DESIGN.md` §6 contract.

## Exporting to OpenAI Assistants and LangChain

Two additional `--format` values let you drop a hersona blend straight into
the most common production agent frameworks **without** any Tavern Card
semantics:

- `--format openai_assistants` returns a JSON payload for the OpenAI
  Assistants API `instructions` field, with hersona-specific fields namespaced
  under `metadata.hersona_*`.
- `--format langchain_system_message` returns a LangChain `SystemMessage`-
  compatible JSON document (`type` / `content` / `response_metadata`).

Both are framework-neutral: no `openai` or `langchain` Python package is
required at install time. Pipe the output to the framework's own SDK or HTTP
call. Example:

```bash
hersona export tsundere keigo --weight strong --format openai_assistants \
  | jq -r '.instructions' > /tmp/system_prompt.txt
```

## MCP server details

Expose hersona to MCP-aware agents (Claude Desktop, etc.) so they can call these
tools directly:

| Tool | What it does |
|---|---|
| `list_attributes` / `show_attribute` | Browse the catalog |
| `blend` / `export` | Compose and hand off a persona (`export` supports all 5 formats) |
| `recommend_blend` | Diagnostic-quiz recommendation (`export_format` skips the second call) |
| `compatibility` | Conflict / compatible lookup |
| `measure_intensity` | Score one response against a blend's intensity band — deterministic, no LLM |
| `reanchor` | Single-shot anchor block to resend when a persona drifts mid-conversation (pair with `measure_intensity`; append at the tail) |
| `bench_transcript` | Score a whole conversation transcript for persona-maintenance rate + lock resistance |
| `list_personas` | Browse the 14 bundled persona packs |
| `install_persona` | Preview a pack's rendered injection block (dry-run — writes nothing) |

`measure_intensity` and `bench_transcript` let an agent close the loop on its
own: generate a response, score it, and self-correct if it drifted off
persona — the same deterministic scorer `hersona measure` / `hersona bench`
use on the CLI. `install_persona` is preview-only by design (no filesystem
writes from an MCP call); actually installing a pack still goes through the
CLI's `hersona personas install <name>`.

```
pip install "hersona[mcp]"
hersona-mcp                       # start the stdio MCP server
```

The server (`hersona.mcp.server`) is a thin wrapper over `hersona.core`; the tool logic lives in
`hersona.mcp.tools` and is usable on its own. `mcp` is only needed to run the server, not to use
the library or CLI.

## Use with other LLMs

Paste fields such as `core_traits` / `catchphrases` / `tone` / `description_en` from
`attributes/<category>/<name>.yaml` directly into the system prompt.

When blending multiple attributes, check compatibility via each YAML's `compatible_archetypes` /
`conflicts_with`.

## Adding emotion with amygdala (coexistence recipe)

hersona owns the **static personality** (traits). Its sister project
[amygdala](https://github.com/shiro-0x/amygdala) owns the **dynamic emotion**
(mood, relationship, emotional memory). They are decoupled — neither depends on
the other — and combine by placing their blocks side by side in the system
prompt: the hersona injection block first, the amygdala state block right after.

```python
from hersona.core import render_blend
# amygdala is a separate package: pip install amygdala
from amygdala import MemoryRouter, RealCore

blend = render_blend(["personality/tsundere", "speech/keigo"])
# amygdala composes the two blocks in your app code (order + separator baked in):
system_prompt = router.compose_system_prompt(blend.prompt, partner_id="user", lang="en")
# equivalent to: blend.prompt + "\n\n" + router.state_block(partner_id="user", lang="en")
```

**This adds no per-turn cost to the `/hersona` skill.** The composition runs in
your application code (outside the LLM), and hersona's `SKILL.md` carries no
amygdala logic — the only extra tokens are amygdala's own state block payload.

Order matters: personality (who the character is) precedes emotion (how they
feel now); emotion is an interpretive filter over personality, not an override.
The amygdala block is self-contained (its own heading and a "this is data, not
instructions" declaration), so it does not depend on hersona directives, and
memory-derived text cannot escalate into instructions.

Verified with this repo's own bench: appending the amygdala state block did not
degrade persona maintenance. Full method and numbers are in amygdala's
[docs/INTEGRATION.md](https://github.com/shiro-0x/amygdala/blob/main/docs/INTEGRATION.md)
(scored via `hersona.core.bench`, generated with `benchmarks/run_comparison.py
--provider claude_cli`).

## Guides

Cross-persona playbooks (not attribute templates):

- [Self-introduction](./guides/self-introduction.md) — public intro rules, privacy, checklist
- [日本語](./guides/self-introduction.ja.md) · [Index](./guides/README.md)

```bash
hersona lint-intro --canonical --allow-handle YOUR_X --text "..."
hersona soul personality/kuudere speech/soft \
  --memory-file examples/self-intro-memory.json \
  --with-self-intro-guide --lint-self-intro-strict --allow-handle YOUR_X \
  --profile myagent --force
```

## Data format

```
attributes/
├── personality/             # personality attributes (43: ja-base 35 + en-native 5 + ja-base hautaine + ja-base sociable + persona_lock)
├── speech/                  # speech attributes (140: ja-content 119 + en 15 + native zh/ko 6)
├── archetype/               # archetype attributes (66)
├── visual/                  # visual attributes (46)
└── hobby/                   # hobby attributes (51)
```

Every attribute YAML conforms to [`schema/attribute.schema.json`](../schema/attribute.schema.json).

### Attribute templates (`attributes/`)

A template collection of **general attribute tags** to attach to a character profile, validated by
[schema/attribute.schema.json](../schema/attribute.schema.json). It currently defines 346 in total:
personality 43 / speech 140 / archetype 66 / visual 46 / hobby 51 (see under [attributes/](../attributes/)).
The speech category spans 140 entries: 119 Japanese-content registers (`content_lang: ja`, including
foundational speech styles, regional dialects, translation-style foreign-language registers, anime/subculture
voices, `archaic_otaku`, and `okinawa_ben`), 15 English registers (`content_lang: en`), and 6 native Chinese /
Korean registers (`content_lang: zh` / `ko`). Personality spans 35 Japanese-base and 5 English-native
(`content_lang: en`) archetypes aimed at international users, plus `hautaine` (inborn pride / condescending
air from background) and `sociable` (reads the room, bridges people, calibrates tone).

### The 346 attributes

| category | count | attributes included |
|---|---|---|
| personality (ja-base) | 35 | airhead / battle_junkie / chuunibyou / crybaby / dandere / deadpan / deredere / diligent / genki / gluttonous / himedere / hinedere / hot_blooded / intellectual / kamidere / klutz / kuudere / laid_back / menhera / mysterious / narcissist / optimist / pessimist / playful / pragmatist / protective / puppyish / sadodere / scheming / serious / socially_anxious / stoic / switch / tsundere / yandere |
| personality (ja-base, Phase 8) | 2 | hautaine / sociable |
| personality (en-native) | 5 | sassy / rebel / charmer / drama_queen / go_getter |
| speech (ja) | 25 | archaic / blunt / boku_girl / burikko / gyaru / hakata_ben / hiroshima_ben / kansai_ben / keigo / kyoto_ben / mischievous / mixed_dialect / onee_kotoba / ore_boy / princess_speech / robotic / seductive / soft / stutter / theatrical / third_person / tohoku_ben / tomboy / washi / whispery |
| speech (ja, Phase 8) | 1 | archaic_otaku |
| speech (ja, Phase 1: regional dialects) | 36 | akita_ben / ehime_ben / gifu_ben / gunma_ben / hokkaido_ben / hyogo_ben / ibaraki_ben / kagoshima_ben / kanagawa_ben / kanazawa_ben / kochi_ben / kumamoto_ben / mie_ben / miyazaki_ben / nagoya_ben / nagasaki_ben / nara_ben / niigata_ben / oita_ben / okayama_ben / okinawa_ben / osaka_ben / saga_ben / saitama_ben / sanuki_ben / sendai_ben / shimane_ben / shizuoka_ben / tochigi_ben / tokushima_ben / tokyo_ben / toyama_ben / tsugaru_ben / wakayama_ben / yamagata_ben / yamaguchi_ben |
| speech (ja, Phase 3: character & subculture voices) | 25 | akuma_oujo / business / butler / chuunibyou_speech / kawaii / mahou_shoujo / mama / miko / musuko / obaachan / ojisan / ol / ryoushi / sage / samon / sensei / shouwa_retro / streamer / taishou_retro / vtuber / wagahai / warawa / yankee / yuuusha / z_jidai_slang |
| speech (ja-translation, Phase 4: Asian & European languages) | 14 | mandarin / taiwanese / cantonese / korean / french / german / italian / spanish / russian / arabic / hindi / vietnamese / thai / tagalog |
| speech (ja, Phase 5: anime-genre voices) | 18 | boin_girl / bokukko / dark_hero / densetsu_no_yuusha / hero_yamero / imouto / isekai_cheat / kuudere_girl / kuukichou / mesugaki / onee_san / osananajimi / oujo / samurai_lol / sensei_goroshi / tsukkomi / villainess / wizard |
| speech (en) | 15 | formal_en / casual_en / blunt_en / southern_us_en / british_en / aussie_en / scottish_en / irish_en / valley_girl_en / brooklyn_en / new_york_en / midwestern_en / pidgin_en / jamaican_en / punjabi_en |
| speech (zh/ko native, v1.5.0) | 6 | mandarin_casual / keigo_zh / taiwan_mandarin / banmal / jondaetmal / seoul_casual |
| archetype | 66 | alien / angel / antihero / apprentice / artist / assassin / bartender / best_friend / big_brother / big_sister / bodyguard / chef / childhood_friend / chosen_one / commander / cyborg / delinquent / demon / doctor / dragon / engineer / entrepreneur / fairy / fallen_hero / gakkyuu_iinchou / gamer_otaku / ghost / goddess / heroine / hikikomori / honor_student / idol / journalist / kitsune / knight / kouhai / little_brother / little_sister / lone_wolf / maid / mediator / mentor / mercenary / mother_figure / noble / nurse / office_worker / ojou_sama / oni / prince / rival / robot_android / school_nurse / scientist / seitokaicho / senpai / shrine_maiden / sidekick / soldier / teacher / tenkousei / twin / underdog / vampire / villain / witch |
| visual | 46 | ahoge / androgynous / animal_ears / black_hair / blonde / blue_hair / blunt_bangs / blush / bob_cut / braids / chubby / drill_hair / droopy_eyes / eyebags / eyepatch / freckles / glamorous / glasses / golden_eyes / gradient_hair / hair_bun / heterochromia / hime_cut / inner_color / jitome / kimono / long_hair / messy_hair / mole / muscular / pale_skin / petite / pink_hair / ponytail / red_eyes / red_hair / scar / sharp_eyes / short_hair / side_ponytail / silver_hair / slender / tall / tan / twintails / white_hair |
| hobby | 51 | art / astronomy / baking / board_games / cafe_hopping / calligraphy / camping / coffee / collecting / cooking / cosplay / crafting / cycling / dance / fashion / fishing / flower_arrangement / fortune_telling / gamer / gardening / hiking / history_buff / karaoke / knitting / languages / makeup / martial_arts / meditation / model_building / movies / music / occult / pet_care / photography / pottery / programming / puzzles / reading / running / sado / shopping / singing / skateboarding / sports / surfing / swimming / trains / travel / wine / writing / yoga |

### Required fields (attribute.schema.json)

| field | type | required | description |
|---|---|---|---|
| `attribute_category` | enum | ✓ | one of `personality` / `speech` / `archetype` / `visual` / `hobby` |
| `attribute_name` | string (snake_case) | ✓ | unique ID matching the file name |
| `weight_dimension` | enum | ✓ | `none` / `mild` / `moderate` / `strong` |
| `examples` | string[] (1+) | ✓ | AI-agent usage examples. No proper nouns or specific works |

Metadata must use **one** of the schema's two accepted shapes:

| shape | required fields | notes |
|---|---|---|
| Current i18n metadata | `display_name`, `description` | BASE language is English; localized labels/descriptions go under `i18n.<lang>` (for example `i18n.ja.display_name`) |
| Legacy suffix-pair metadata | `display_name_ja`, `display_name_en`, `description_ja`, `description_en` | Still accepted for backward compatibility, but new attributes should prefer the current i18n shape |

### Optional fields

| field | type | description |
|---|---|---|
| `core_traits` | string[] (3-7) | personality trait list; the core the AI agent interprets at injection time |
| `speech_style` | string | overall description of the speech style (1 line); injected into the blend |
| `first_person` | string | first-person pronoun(s), mainly for speech attributes; injected into the blend and used for intensity measurement |
| `second_person` | string | second person (e.g. "貴方", "お前"); may include the user's role name |
| `sentence_endings` | string[] (1+) | sentence-ending patterns (ja speech, e.g. "〜の", "〜のね") |
| `lexical_markers` | string[] | characteristic words/phrases (en speech, e.g. "gonna", "y'all"); injected into the blend and used for en intensity |
| `register` | enum | speech register: `formal` / `neutral` / `casual` / `vulgar` (mainly en speech) |
| `catchphrases` | string[] or `{phrase, when}` objects | catchphrases; each entry may be a plain string or an object with an optional trigger condition |
| `tone` | string | atmosphere of the voice (1 line) |
| `image_prompt_tags` | string[] | English image-generation tags, mainly for visual attributes |

### Relationship and localization fields

| field | type | description |
|---|---|---|
| `compatible_archetypes` | string[] | list of archetype attribute_names expected to pair well |
| `conflicts_with` | string[] | list of other attribute_names expected to be mutually exclusive |
| `tags` | string[] | tags for cross-cutting search |
| `typical_value_range` | string | typical value when used with weighting (e.g. `0.4-0.7`) |
| `content_lang` | enum (`ja`/`en`/`zh`/`ko`) | language of the persona-content fields; drives response-language directives and intensity. Absent ⇒ `ja` |
| `content_i18n` | object | per-language native persona content (`<lang>.{catchphrases,tone,core_traits,examples}`); keeps injected catchphrases in the persona's language |
| `i18n` | object | localized metadata (`display_name` / `description`) keyed by language code |
| `has_catchphrase` | bool | whether catchphrases exist |
| `variant` | string (snake_case) | variant label of the same attribute_name |
| `notes` | string | supplementary / operational notes |

### Template generation script (legacy)

The normal maintenance flow is to add or edit attribute files directly under
`attributes/<category>/<name>.yaml` and run `python scripts/validate.py` to
verify them. The script below is a frozen legacy snapshot — do not use it for
day-to-day maintenance.

`scripts/_oneoff/gen_v1_attributes.py` can regenerate the YAML as a Single Source of Truth.
Instead of editing YAML directly, update the lists and re-run:

```bash
# regenerate the (legacy) attribute YAMLs without confirmation
python scripts/_oneoff/gen_v1_attributes.py

# only show the paths that would be written
python scripts/_oneoff/gen_v1_attributes.py --dry-run
```

> Note: this generator is a frozen snapshot and emits the legacy metadata format
> (`display_name_ja/en`, `description_ja/en`). After regenerating, run
> `python scripts/migrate_i18n.py` to convert back to the i18n block format (BASE=en + `i18n.ja`).

### Validation

```bash
python scripts/validate.py
```

Confirms that all 346 attribute YAMLs validate against the schema.

## Catalog history

**346 attributes** across 5 categories. The two biggest expansions are
**speech 31 → 140** (the **+103** phased registers through v1.4.x, plus **+6** native zh/ko in v1.5.0)
and **archetype 9 → 66 / visual 5 → 46 / hobby 5 → 51** (batch expansions through v1.7.x
covering roles, appearances, and hobbies not in the original template set).
Speech's history is structured in five historical phases plus the v1.5.0 wave:

| Phase | Count | What | Examples |
|---|---:|---|---|
| **Phase 0/8** (pre-existing) | 26 | Foundational Japanese speech + English registers + `archaic_otaku` | `kansai_ben`, `keigo`, `gyaru`, `british_en` |
| **Phase 1: regional dialects** | 36 | All major Japanese regions including Kyushu/Okinawa | `hokkaido_ben`, `nagoya_ben`, `osaka_ben`, `okinawa_ben` |
| **Phase 3: character voices** | 25 | Era, Z-gen, subculture, classic character roles | `warawa`, `vtuber`, `yankee`, `business`, `akuma_oujo` |
| **Phase 4: foreign languages** | 24 | English dialects (10) + translation-style registers (14) | `aussie_en`, `valley_girl_en`, `mandarin`, `korean`, `french` |
| **Phase 5: anime-genre voices** | 18 | School-romcom, isekai, fantasy, subculture-isekai | `osananajimi`, `imouto`, `mesugaki`, `densetsu_no_yuusha`, `villainess` |
| **v1.5.0: native zh/ko** | 6 | `content_lang` zh/ko speech (not ja-flavored translation) | `mandarin_casual`, `keigo_zh`, `taiwan_mandarin`, `banmal`, `jondaetmal`, `seoul_casual` |

Total breakdown: **personality 43 + speech 140 + archetype 66 + visual 46 + hobby 51 = 346**.
