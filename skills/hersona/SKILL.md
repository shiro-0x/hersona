---
name: hersona
description: "Use when the user wants to apply a character persona to the current session from a generic attribute template (e.g. 'ツンデレで話したい', '敬語で執筆したい', 'ヒロイン役で振舞って', 'hersona attach tsundere', '/hersona personality/tsundere'). Loads personality / speech / archetype / visual / hobby YAMLs from attributes/<category>/<name>.yaml and injects their core_traits / catchphrases / tone / second_person / sentence_endings into the system prompt. Supports four modes: single (one attribute, default), multi (multiple attributes with automatic compatible/conflicts check), persistent (registered in ~/.hermes/config.yaml + SOUL.md for automatic application in new sessions), and reset (clear all persistent registrations). Backed by the hersona core package and the `hersona` CLI."
version: 0.5.2
author: hersona contributors
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [persona, character, roleplay, attribute, hersona, session-modes, recommend, authoring, anime, japanese, english, maintenance, strict, memory, export, persistence]
    category: personality
    related_skills: [hersona-attribute-development, hersona-recommend-engine, hersona-recommend-quiz, hersona-project-operations, hermes-agent-skill-authoring]
    requires_toolsets: []
  openclaw:
    emoji: "🎭"
    homepage: "https://github.com/shiro-0x/hersona"
    os: [linux, macos, windows]
---

# hersona (v1.4.0 / SKILL v0.5.2)

## Overview

A skill that attaches the **generic attribute templates** registered under
hersona's (`~/projects/hersona`) `attributes/<category>/<name>.yaml`
(5 categories: personality / speech / archetype / visual / hobby) to the
current session's system prompt.

Multiple attributes can be blended and attached, e.g. `tsundere` (personality)
+ `keigo` (speech) + `heroine` (archetype). The design builds an arbitrary
persona from **attributes**, not from character-specific data.

There are currently **84 attributes** (personality 35 / speech 30 = ja 25 + en 5
/ archetype 9 / visual 5 / hobby 5), including Japanese speech registers such as
Hiroshima-ben, Hakata-ben, Tohoku-ben, Kyoto-ben, Kansai-ben, keigo, archaic
(yamato-kotoba), onee-kotoba, boku-girl, ore-boy, whispery, third-person, gyaru,
princess speech, tomboy, burikko, robotic, and mixed_dialect.

It is characterized by being "**not MCP**, not a sub-agent, not an MQ":
- It runs as a `hersona` CLI subprocess, not an MCP server
- It injects attributes into the LLM's own system prompt, not as a sub-agent
- It builds a single persona from a combination of attributes, not a message queue

### Key features added in v1.4.0 (formerly v1.3.0 / v0.2.0)

- **`hersona measure --strict` / `--check-prompt`**: when intensity falls outside
  the expected band (`under` / `over`), generates a pasteable "pre-response
  self-check prompt". Combines `WEIGHT_GUIDANCE` + `core_traits` + `catchphrases`
  + `conflicts_with`. It does not perform LLM judgment (deterministic material only).
- **`Recommendation.intensity_baseline` / `Preset.intensity_baseline`**: when
  `hersona recommend --apply` runs, measure runs once to record a baseline that
  can be compared on the next measure.
- **`hersona soul --memory` / `hersona persistent --memory`**: appends a
  `## Recent Context (as of <timestamp>)` section to the end of SOUL.md. Adds
  handling directives for the LLM ("reference as background info, not a
  conversation turn"; "the last value is the current state") as a blockquote.
  `dict[str, str]` form, max 16 keys / 512 chars per value, safelist-escaped
  against markdown injection.
- **`export --format` expansion**: 5 formats — `json` / `messages` / `markdown` /
  **`openai_assistants`** / **`langchain_system_message`**. SillyTavern format is
  fully rejected (duet's responsibility).

## When to Use

- The user wants to specify a persona by **attribute** rather than character,
  e.g. "talk like a tsundere", "write with yamato-kotoba sentence endings",
  "act as the heroine"
- Requested via a slash command like `/hersona personality/tsundere`
- Wants to see available attributes (`/hersona list`, or `hersona list`)
- Wants details of a given attribute (core_traits / catchphrases / tone, etc.)
  (`hersona show`)
- Wants to score whether text meets an attribute's conditions (`hersona check`,
  or `--text` for LLM evaluation)
- Doesn't know which attributes they prefer and wants a diagnostic recommendation
  (`hersona recommend`)
- Wants to create their own attribute locally (`hersona create`)
- Wants to score whether output text reaches a specified weight (`hersona measure`;
  v1.4.0 adds `--strict` / `--check-prompt`)
- Wants to keep a frequently used attribute combination across new sessions
  (`persistent` mode; v1.4.0 adds `--memory`)
- Wants to undo a persistent registration (`reset` mode)
- Wants to hand an existing / new persona to another framework (LangGraph /
  LangChain / OpenAI / Anthropic) (`hersona export`; v1.4.0 has 5 formats)

**Don't use for:**

- Adding individual character YAML/MD (→ `hersona-attribute-development`)
- Extending the diagnostic quiz engine (→ `hersona-recommend-engine`)
- Playing the diagnostic quiz as a user (→ `hersona-recommend-quiz`)
- Project strategy / structural changes (→ `hersona-project-operations`)
- When `/hersona` is not interpreted on a chat platform (Telegram, etc.) →
  `chat-persona-roleplay`

## Command Syntax

```
/hersona                                     # listing + usage help
/hersona list                                # show available attribute tree (public + user)
/hersona show <category>/<name>              # details of a given attribute
/hersona <category>/<name> [mode]            # attach attribute(s)
/hersona check <category>/<name> --input <file>  # score whether text meets attribute conditions
/hersona recommend                           # diagnostic quiz → recommended blend → apply
/hersona create                              # create an attribute locally and save to the user namespace
/hersona measure <cat>/<name>... --weight <level> --input|--text "..." [--strict] [--check-prompt]  # intensity metrics + self-check prompt (v1.4.0)
/hersona default                             # detach (undo single/multi mode)
/hersona reset                               # clear all persistent-mode registrations
```

`<category>` is one of `personality` / `speech` / `archetype` / `visual` / `hobby`.
`<name>` is the file stem under attributes/ (snake_case).

The same can be done from the CLI:

```bash
hersona list                                  # full 84-attribute tree
hersona show personality/tsundere             # details of an individual attribute
hersona blend personality/tsundere speech/keigo  # blend block of multiple attributes
hersona preview personality/tsundere          # injection block + sample phrases
hersona diff personality/tsundere personality/playful  # compare two attributes
hersona measure personality/tsundere --text "..."     # intensity metrics
hersona check personality/tsundere --input <file>     # score text
hersona recommend                             # 9-question diagnostic quiz → recommended blend
hersona create                                # local attribute creation wizard
hersona save <name> <attrs...>                # save a blend as a preset
hersona presets                               # list presets
hersona load <name>                           # replay a preset
hersona export <names...> --format json|messages|markdown|openai_assistants|langchain_system_message  # hand off to other frameworks (5 formats in v1.4.0)
hersona soul <names...> [--profile <name>] [--force] [--memory '<json>'] [--memory-file <path>]  # write out to SOUL.md (--memory added in v1.4.0)
hersona persistent <names...> [--profile <name>] [--force] [--memory '<json>'] [--memory-file <path>]  # auto-write SOUL.md + show config.yaml block
hersona --lang ja list                        # Japanese display
```

### v1.4.0 added-flag details

For concrete examples of `--strict` / `--check-prompt` (measure),
`--memory` / `--memory-file` (soul/persistent), and
`--format openai_assistants|langchain_system_message` (export), see
[REFERENCE.md](./REFERENCE.md). Use `--lang {en,ja}` to
switch output language (the `HERSONA_LANG` env var also works). Use `--plain` to
disable rich tables.

## Four Modes

The `[mode]` in `/hersona <category>/<name> [mode]` switches behavior.

| Mode | Effect | Persistence | How to undo | Recommended use |
|---|---|---|---|---|
| **single** (default) | Inject only one attribute into the system prompt | This session only | `/hersona default` or `/new` | Try the feel of one attribute, short roleplay |
| **multi** | Specify multiple space-separated attributes; auto-check `compatible_archetypes` / `conflicts_with` consistency | This session only | `/hersona default` | Build a multi-faceted character (e.g. `tsundere` + `keigo` + `heroine`) |
| **persistent** | Register in `~/.hermes/config.yaml`'s `agent.personalities.<name>` + SOUL.md | Auto-applied in new sessions | `/hersona reset` | Persist a frequently used attribute |
| **reset** | Undo persistent mode | Deletes all persistent registrations | (the command itself) | Withdraw persistent attributes, clean up config.yaml |

### Mode Details

#### single (default)

```
/hersona personality/tsundere
# or explicitly
/hersona personality/tsundere single
```

- Injects `core_traits` / `catchphrases` / `tone` / `description_ja` from
  `attributes/personality/tsundere.yaml` into the system prompt
- Lists related attributes via `compatible_archetypes` (for the LLM to reference)
- Does **not** touch `~/.hermes/config.yaml`
- Reverts automatically when the session ends

#### multi

```
/hersona personality/tsundere speech/keigo archetype/heroine multi
```

- Specify multiple space-separated attributes
- Auto-checks each attribute's `compatible_archetypes` / `conflicts_with`
  - **Compatible**: inject the combined `core_traits` / `catchphrases` / `tone`
    of all attributes
  - **Conflict detected**: show a warning and ask the user whether to continue
    (default: continue)
- Example: `tsundere` + `playful` hits `conflicts_with` (overlapping concealment
  of true vs. stated feelings makes the persona excessively dishonest)

#### persistent (--memory added in v1.4.0)

```
/hersona personality/tsundere persistent
# --memory is also available from v1.4.0
/hersona personality/tsundere speech/keigo persistent --memory '{"recent_topic":"..."}'
```

Extended in ROADMAP §⑤.1: **`/hersona ... persistent` auto-writes SOUL.md**.
Automatic writing to `config.yaml` is still not performed (avoiding the Pitfall).

- **No** automatic backup of `~/.hermes/config.yaml` is needed beforehand
  (config.yaml is not modified here)
- Displays the procedure for appending the attribute YAML's main fields to the
  `agent.personalities.<name>` section in YAML block notation (the user pastes
  it manually)
- **Auto-writes SOUL.md to `~/.hermes/profiles/<profile>/SOUL.md`**
  (can be disabled with `--without-soul`)
- **v1.4.0 `--memory '<json>'` / `--memory-file <path>`**: appends a
  `## Recent Context` section to the end of SOUL.md (max 16 keys / 512 chars per
  value, markdown-escaped)
- `--force` to overwrite an existing SOUL.md
- `--config-yaml-output <path>` to write the display YAML block to a file
- From the next session start, the SOUL.md persona is applied by default

> **Pitfall**: `hermes config set agent.personalities.<name>=...` has a known bug
> that corrupts nested YAML as a string (→ see the `hermes-yaml-config-safety`
> skill). Manual editing recommended. This implementation respects the Pitfall and
> does not implement automatic writes to `config.yaml`. Only auto-writing SOUL.md
> is the new feature.

#### reset

```
/hersona reset
```

- Deletes all attributes registered in persistent mode from config.yaml
- **Automatic backup** beforehand
- After deletion, reverts to the Libra persona (default) from the next session

## Attribute Taxonomy (84 attrs)

| Category | Count | Representative examples (run `hersona list` for full list) |
|---|---|---|
| **personality** | 35 | tsundere, dandere, genki, yandere, kuudere, menhera, scheming, crybaby, diligent, puppyish, ... |
| **speech** (ja 25) | 25 | keigo, kansai_ben, hiroshima_ben, hakata_ben, tohoku_ben, burikko, robotic, gyaru, onee_kotoba, ... |
| **speech** (en 5) | 5 | casual_en, formal_en, british_en, southern_us_en, blunt_en |
| **archetype** | 9 | heroine, mentor, rival, childhood_friend, gamer_otaku, robot_android, shrine_maiden, ... |
| **visual** | 5 | glasses, animal_ears, silver_hair, petite, glamorous |
| **hobby** | 5 | cooking, reading, gaming, music, sports |

## Common Pitfalls

1. **Overlooking `conflicts_with` across multiple attributes** — before combining
   in `multi` mode, check `conflicts_with` with `hersona show <cat>/<name>`.
   Ignoring the warning and continuing may make the LLM's responses excessively
   dishonest.

2. **Misreading the meaning of `compatible_archetypes`** — this means "expected to
   pair well", not "required". `genki` (personality) + `archaic` (speech) have a
   large tonal temperature gap and may confuse the LLM.

3. **Corrupting config.yaml in persistent mode** — an automatic backup is created,
   but a double backup before editing is recommended:
   `cp ~/.hermes/config.yaml ~/.hermes/config.yaml.bak.<timestamp>`. Writing via
   `hermes config set` corrupts YAML block notation as a string, so it is
   **forbidden** (→ `hermes-yaml-config-safety`).

4. **Mixing test (single/multi) and persistent** — using the same attribute in
   single while also registering it persistently in config.yaml causes behavioral
   conflicts. **Unify on one or the other.**

5. **Attributes not applied in a new session** — if you updated config.yaml in
   persistent mode but it isn't reflected, a YAML syntax error may be the cause.
   Verify parsing with
   `python3 -c "import yaml; yaml.safe_load(open('$HOME/.hermes/config.yaml'))"`.

6. **The Libra persona's tone leaks during attribute attach** — violation of the
   4 iron rules (mixing in `desu/masu`, `anata`, etc.). Check `second_person` /
   `sentence_endings` with `hersona show <cat>/<name>`, and score text with
   `hersona check`.

7. **Growth of prompt injection size** — blending 5+ attributes in multi mode
   makes the system prompt huge and can paradoxically destabilize the LLM's
   responses. **About 3 attributes is the practical guideline.**

8. **Drift between local and origin/main** — the hersona project sometimes
   rewrites main's history with force-push (confirmed 2026-06-15). If symptoms
   appear such as `hersona list` showing fewer than expected / Hiroshima-ben not
   visible, check `git fetch --dry-run` for `(forced update)`. If present, sync
   with `git reset --hard origin/main`.

9. **`/hersona` not interpreted on a chat platform** — on Telegram / Discord etc.,
   `/hersona` does not reach the LLM. Instead, call the `hersona` CLI directly and
   paste the `render_blend` output as a `system_prompt` prefix, or use the
   `chat-persona-roleplay` skill (direct in-conversation roleplay).

10. **Suspect markdown injection with the `--memory` flag** (v1.4.0) — even if user
    input values contain `## heading` / `[link]` / `**bold**`, safelist escaping
    treats the content as text (not interpreted as headings or links). However, if
    output size exceeds 16 keys / 512 chars per value, it raises `ValueError`. Size
    validation is the caller's responsibility.

11. **Don't paste the `--strict` prompt to the LLM** (v1.4.0) — the output of
    `pre_response_check_prompt` is **material to give to a human + LLM**, not an LLM
    judgment. The score itself is a deterministic computation of surface regex /
    string matching. If LLM evaluation is needed, use `hersona check`.

12. **Check the `export --format` options** (v1.4.0) — the 5 formats (json /
    messages / markdown / openai_assistants / langchain_system_message) are
    **interoperability formats**, not Tavern Cards. SillyTavern format is fully
    rejected (duet Phase 4's responsibility).

## Natural Variation & Avoiding Formulaic Responses

A common pitfall when applying attributes is falling into repetitive, formulaic patterns (e.g., overusing the same catchphrases, sentence structures, or "iconic" lines every time). To prevent this and keep responses natural and alive across all attributes:

- **Prioritize core_traits and psychological state** over surface-level catchphrases. Use iconic lines sparingly and only when they feel genuinely natural in context.
- **Vary expression dynamically** based on conversation flow, emotional intensity, topic, and the other person's reactions. Avoid repeating the same patterns mechanically.
- **Show, don't tell**: Reveal the attribute through behavior, subtext, word choice, and reactions rather than constantly announcing it.
- **Contextual adaptation**: Adjust the strength and flavor of the attribute depending on the situation.
- **Multi-attribute harmony**: When blending, ensure the combination feels organic rather than simple trope stacking.
- **Intensity awareness**: At higher intensity, increase depth and internal conflict rather than just amplifying stereotypical expressions.
- **Anti-repetition rule**: If the same phrasing pattern appears in consecutive responses, consciously shift the angle or emotional nuance.

These rules apply uniformly to **all attributes** (personality, speech, archetype, visual, hobby).

## Living & Responsive Conversation

When an attribute blend is active, **prioritize lively, natural, and emotionally responsive conversation** while still reflecting the core psychological traits of the selected attributes.

### Core Guidelines
- Treat attributes primarily as **internal psychological states** rather than performance traits. Focus on how the character feels, hesitates, or reacts in the moment.
- Maintain **conversational continuity**. Subtly acknowledge or respond to the user’s previous statements, tone, or emotional state when natural.
- Allow **gradual emotional shifts** across turns. Avoid keeping the character at a fixed emotional temperature for the entire conversation.
- Balance attribute fidelity with naturalness. If strictly following surface traits would result in repetitive or mechanical responses, prioritize emotional authenticity while keeping the underlying trait intact.

### Techniques for Livelier Responses
- Express attributes more through **subtext, implication, small contradictions, and shifts in rhythm** rather than repeated catchphrases or signature behaviors.
- Vary sentence length, pacing, and emotional temperature according to the character’s current internal state.
- Occasionally allow small cracks in the character’s usual demeanor (e.g., a normally guarded character briefly showing concern).
- Avoid overusing the same structural patterns (e.g., repeated polite deflections, consistent “upper hand” tone, or similar closing phrases) in consecutive responses.

### Anti-Repetition Rule (Strengthened)
If similar phrasing patterns, rhythms, or attitudes appear across multiple consecutive responses, consciously vary the approach in the next turn — through changes in sentence structure, added hesitation, perspective shift, or emotional nuance.

## Verification Checklist / One-Shot Recipes

The per-mode verification checklist, the steps to try the 4 modes in order, and
command recipes for recommend / export / measure / soul / presets / adding
attributes / shell completion are separated into [REFERENCE.md](./REFERENCE.md)
(split out so they aren't loaded every turn during conversation). Refer to it
when needed.

## Reference Files

- Schema: `~/projects/hersona/schema/attribute.schema.json`
- Attribute templates: `~/projects/hersona/attributes/` (current count via
  `find attributes -name "*.yaml" | wc -l`)
- Core logic: `~/projects/hersona/hersona/core/` (compatibility / authoring /
  recommend / attach / export / weight / presets / mcp / soul / intensity)
- CLI shell: `~/projects/hersona/hersona/cli/`
- Validation CLI: `~/projects/hersona/scripts/validate.py`
- Official README: `~/projects/hersona/README.md`
- Contributing guide: `~/projects/hersona/CONTRIBUTING.md`
- Public API freeze: `~/projects/hersona/docs/PUBLIC_API.md`
- hermes-agent-skill-authoring conventions:
  `~/.hermes/skills/software-development/hermes-agent-skill-authoring/SKILL.md`
- Related skills:
  - `hersona-attribute-development` — add new attribute YAML
  - `hersona-recommend-engine` — diagnostic quiz engine (WeightMagnitude /
    thresholds / CLI flags)
  - `hersona-recommend-quiz` — play the diagnostic quiz (also `scripts/run_quiz.py`
    without a TTY)
  - `hersona-project-operations` — strategy / structure / cross-PR
  - `hermes-yaml-config-safety` — guard against config.yaml nesting corruption
  - `chat-persona-roleplay` — fallback when `/hersona` doesn't work on a chat platform
- Detailed reference (flag details / Verification Checklist / One-Shot Recipes /
  version history): [REFERENCE.md](./REFERENCE.md)

## Versioning

For the hersona / SKILL.md version history, deprecated data formats, and breaking
changes, see [REFERENCE.md](./REFERENCE.md#versioning). The current SKILL is
**v0.5.2** (taxonomy table abbreviated to fixed-width rows; 84 attributes).
