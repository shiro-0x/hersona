# hersona

[**English**](./README.md) · [日本語](./README.ja.md)

> **201 reusable character attributes** for AI agent personas —
> compose your own system prompts from personality, speech, archetype, visual, and hobby templates.
> **MIT** (code) + **CC0** (templates). CLI, MCP server, and Hermes Agent skill.

[![PyPI](https://img.shields.io/pypi/v/hersona.svg)](https://pypi.org/project/hersona/)
[![Downloads](https://pepy.tech/badge/hersona)](https://pepy.tech/project/hersona)
[![License: MIT (code)](https://img.shields.io/badge/License-MIT-lightgrey.svg)](./LICENSE)
[![Templates: CC0 1.0](https://img.shields.io/badge/Templates-CC0_1.0-lightgrey.svg)](./LICENSE-CC0.txt)
[![MCP Server](https://img.shields.io/badge/MCP-Server-blue.svg)](#use-as-an-mcp-server-optional)
[![Docs](https://img.shields.io/badge/Docs-shiro--0x.github.io-9cf)](https://shiro-0x.github.io/hersona/)

[Docs](https://shiro-0x.github.io/hersona/) · [PyPI](https://pypi.org/project/hersona/) · [Repository](https://github.com/shiro-0x/hersona)

## Why Hersona?

System-prompt authoring is the most copy-pasted code in AI agents.
Most teams either hand-roll long persona descriptions or steal prompts
from Discord threads — and the resulting characters drift, contradict
themselves, or lose intensity mid-conversation.

Hersona gives you a typed, schema-validated library of 206 character
attributes you can mix and match:

- **Personality (42)** — tsundere, kuudere, yandere, airhead, intellectual, …
- **Speech (140)** — kansai_ben, keigo, mandarin_casual, banmal, british_en, valley_girl_en, …
- **Archetype (9)** — heroine, mentor, rival, idol, shrine_maiden, …
- **Visual (5)** — silver_hair, glasses, petite, glamorous, animal_ears
- **Hobby (5)** — cooking, gamer, music, reading, sports

Each attribute declares `core_traits`, `catchphrases`, `tone`, and an
explicit `compatible_archetypes` / `conflicts_with` matrix — so the
blend engine can detect incompatible mixes and surface warnings (persistence
paths may reject conflicting blends), while you tune intensity per attribute
(`mild` / `moderate` / `strong`).

Use it with any Hermes agent, OpenAI-compatible API, Claude, local LLMs, LangChain,
AutoGen, CrewAI—or as a drop-in MCP server for Claude Desktop.

## 5-Minute Quickstart

```bash
pip install hersona
```

```bash
hersona list                          # browse all 206 attributes
hersona show personality/tsundere     # inspect one attribute
hersona blend personality/tsundere speech/keigo --weight strong
```

```bash
hersona export personality/tsundere speech/keigo --weight strong \
  --format openai_assistants > system_prompt.json
```

Then drop `system_prompt.json["instructions"]` into your agent's system
message — `hersona export` also handles `messages` (chat array),
`langchain_system_message`, `json`, and plain `markdown` formats.

For the full programmatic API, see [`docs/PUBLIC_API.md`](./docs/PUBLIC_API.md).

## Guides

Cross-persona playbooks (not attribute templates):

- [Self-introduction](./docs/guides/self-introduction.md) — public intro rules, privacy, checklist
- [日本語](./docs/guides/self-introduction.ja.md) · [Index](./docs/guides/README.md)

```bash
hersona lint-intro --canonical --allow-handle YOUR_X --text "..."
hersona soul personality/kuudere speech/soft \
  --memory-file examples/self-intro-memory.json \
  --with-self-intro-guide --lint-self-intro-strict --allow-handle YOUR_X \
  --profile myagent --force
```

## Install (Hermes Agent)

No registry approval needed — works right now via tap:

```bash
hermes skills tap add shiro-0x/hersona
hermes skills install hersona
hermes skills install hersona-initializer
```

## License structure

The repository is split into two layers, each under a different license:

| Scope | License | Notes |
|---|---|---|
| `scripts/`, `schema/`, `pyproject.toml`, etc. (code) | **MIT** | `LICENSE` |
| `attributes/**/*.yaml` (general attribute templates) | **CC0 1.0** | `LICENSE-CC0.txt` — public domain dedication |

## What it covers now

**206 attributes** across 5 categories. The biggest recent expansion is
**speech 31 → 140** (the **+103** phased registers through v1.4.x, plus **+6** native zh/ko in v1.5.0),
structured in five historical phases plus the v1.5.0 wave:

| Phase | Count | What | Examples |
|---|---:|---|---|
| **Phase 0/8** (pre-existing) | 26 | Foundational Japanese speech + English registers + `archaic_otaku` | `kansai_ben`, `keigo`, `gyaru`, `british_en` |
| **Phase 1: regional dialects** | 36 | All major Japanese regions including Kyushu/Okinawa | `hokkaido_ben`, `nagoya_ben`, `osaka_ben`, `okinawa_ben` |
| **Phase 3: character voices** | 25 | Era, Z-gen, subculture, classic character roles | `warawa`, `vtuber`, `yankee`, `business`, `akuma_oujo` |
| **Phase 4: foreign languages** | 24 | English dialects (10) + translation-style registers (14) | `aussie_en`, `valley_girl_en`, `mandarin`, `korean`, `french` |
| **Phase 5: anime-genre voices** | 18 | School-romcom, isekai, fantasy, subculture-isekai | `osananajimi`, `imouto`, `mesugaki`, `densetsu_no_yuusha`, `villainess` |
| **v1.5.0: native zh/ko** | 6 | `content_lang` zh/ko speech (not ja-flavored translation) | `mandarin_casual`, `keigo_zh`, `taiwan_mandarin`, `banmal`, `jondaetmal`, `seoul_casual` |

Total breakdown: **personality 42 + speech 140 + archetype 9 + visual 5 + hobby 10 = 206**.

## Overview

An open-source project that systematizes the speech and personality of anime characters and distributes them
as a template collection that can be injected into an AI agent's system prompt.

- Provides **attribute templates** (`attributes/<category>/<name>.yaml`)
- A user (or agent) builds the personality of any character by assigning the attributes they need

## Usage

### Use with Hermes Agent

Attach attributes via `/hersona <category>/<name>`:

```
/hersona                              # listing + usage help
/hersona list                         # list available attributes
/hersona show personality/tsundere    # details of a given attribute
/hersona personality/tsundere single  # attach a single attribute
/hersona personality/tsundere speech/keigo multi  # blend multiple attributes
/hersona default                      # detach
```

#### Common recipes

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

See [skills/hersona/SKILL.md](./skills/hersona/SKILL.md) for Hermes skill
behavior notes, and [skills/hersona/REFERENCE.md](./skills/hersona/REFERENCE.md)
for verification checklists, version history, and edge-case recipes
(saved-blend persistence, intensity measurement, MCP export). For CLI truth,
prefer `hersona --help`, this README, and [`docs/PUBLIC_API.md`](./docs/PUBLIC_API.md).

#### Professional Operating Modes / use cases

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

Initial public use cases: `programmer`, `planner`, `research`, `marketing`,
`product_manager`, `qa_reviewer`, `data_analyst`, and `customer_support`.

`hersona soul ... --use-case <id>` and `hersona persistent ... --use-case <id>`
write the Operating Mode into generated SOUL.md content, so professional task
discipline survives future persona regeneration instead of living in a manual
append-only note. Regeneration also preserves user-owned text below
`<!-- hersona:gen-end -->`.

### Use from the CLI

After `pip install hersona` (Python >= 3.11), the `hersona` command is available.
For local development from a checkout, use `pip install -e .` or `python -m hersona.cli`:

```
hersona list                                  # list available attributes (public + user)
hersona show tsundere                          # attribute details
hersona matrix --json                          # dump the compatibility matrix as JSON
hersona blend tsundere keigo --weight strong   # compose attributes into an injection block (with intensity)
hersona blend airhead intellectual --suggest   # on conflict, suggest non-conflicting replacements (stderr)
hersona diff tsundere dandere                  # compare two attributes (common / only-one fields + relation)
hersona preview tsundere kyoto_ben --weight strong  # injection block + sample phrases (no LLM)
hersona recommend                              # diagnostic quiz -> recommendation (interactive; en UI routes to English speech)
hersona recommend --answers distance=1,speech=0,role=1 --apply
hersona create --category personality --name my_attr \
  --display-ja マイ属性 --display-en MyAttr \
  --desc-ja 説明 --desc-en desc --example "..."  # create an attribute and save to the user namespace
hersona measure kyoto_ben --weight strong --text "ようおいでやすどす"  # score intensity metrics of output
hersona measure tsundere heroine --weight moderate --input out.txt       # intensity metrics of a blend
hersona save my_tsun tsundere keigo --weight strong  # save a blend as a reusable named preset (local)
hersona presets                                # list saved blend presets
hersona load my_tsun                           # replay a saved preset as an injection block
hersona export tsundere keigo --format messages  # export a blend for other frameworks (json/messages/markdown)
hersona soul puppyish keigo heroine --use-case planner --force  # write SOUL.md with a persistent Operating Mode
hersona update                                 # download the latest attribute data from the repository
hersona update --ref v1.7.0                    # pin to a branch / tag / commit SHA (default: main)
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

Saved blend presets live under `~/.hermes/presets/` (default) or the directory specified by
`HERSONA_PRESETS_DIR`. A preset is just a named recipe (`attributes` + `weight`); `hersona load`
replays it through the same blend engine, so it always reflects the latest attribute templates.

To hand a persona off to another agent framework (LangGraph / LangChain / OpenAI / Anthropic SDK),
`hersona export <names...> --format {json,messages,markdown,openai_assistants,langchain_system_message}`
emits a portable artifact: `json` is structured data (metadata + system prompt + per-attribute summary + conflicts),
`messages` is a ready-to-use `[{"role": "system", "content": ...}]` chat array, `markdown` is the raw
injection block, and the OpenAI Assistants / LangChain formats target those frameworks directly. The same
`export_blend()` is available from `hersona.core`.

#### Exporting to OpenAI Assistants and LangChain

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

#### Richer CLI output (optional)

Install the `tui` extra for color tables (`list`) and panels (`show`):

```
pip install "hersona[tui]"
```

It is opt-in: without `rich`, when piping/redirecting, or with `--plain` / `NO_COLOR`, the CLI prints
the same plain text as before. Set `HERSONA_FORCE_RICH=1` to keep color when piping (e.g. `| less -R`).

#### Shell tab-completion (optional)

Install the `completion` extra and register the completer with your shell to tab-complete
subcommands, attribute names, and preset names:

```
pip install "hersona[completion]"
eval "$(register-python-argcomplete hersona)"   # add to ~/.bashrc / ~/.zshrc to persist
```

It is opt-in: without `argcomplete`, the CLI works exactly the same, only without completion.

### Use as an MCP server (optional)

Expose hersona to MCP-aware agents (Claude Desktop, etc.) so they can call
`list_attributes` / `show_attribute` / `blend` / `export` / `recommend_blend` / `compatibility`
directly:

```
pip install "hersona[mcp]"
hersona-mcp                       # start the stdio MCP server
```

The server (`hersona.mcp.server`) is a thin wrapper over `hersona.core`; the tool logic lives in
`hersona.mcp.tools` and is usable on its own. `mcp` is only needed to run the server, not to use
the library or CLI.

### Use with other LLMs

Paste fields such as `core_traits` / `catchphrases` / `tone` / `description_en` from
`attributes/<category>/<name>.yaml` directly into the system prompt.

When blending multiple attributes, check compatibility via each YAML's `compatible_archetypes` /
`conflicts_with`.

## Data format

```
attributes/
├── personality/             # personality attributes (42: ja-base 35 + en-native 5 + ja-base hautaine + ja-base sociable)
├── speech/                  # speech attributes (140: ja-content 119 + en 15 + native zh/ko 6)
├── archetype/               # archetype attributes (9)
├── visual/                  # visual attributes (5)
├── hobby/                   # hobby attributes (10)
```

Every attribute YAML conforms to [`schema/attribute.schema.json`](./schema/attribute.schema.json).

### Attribute templates (`attributes/`)

A template collection of **general attribute tags** to attach to a character profile, validated by
[schema/attribute.schema.json](./schema/attribute.schema.json). It currently defines 206 in total:
personality 42 / speech 140 / archetype 9 / visual 5 / hobby 10 (see under [attributes/](./attributes/)).
The speech category spans 140 entries: 119 Japanese-content registers (`content_lang: ja`, including
foundational speech styles, regional dialects, translation-style foreign-language registers, anime/subculture
voices, `archaic_otaku`, and `okinawa_ben`), 15 English registers (`content_lang: en`), and 6 native Chinese /
Korean registers (`content_lang: zh` / `ko`). Personality spans 35 Japanese-base and 5 English-native
(`content_lang: en`) archetypes aimed at international users, plus `hautaine` (inborn pride / condescending
air from background) and `sociable` (reads the room, bridges people, calibrates tone).

#### The 206 attributes

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
| archetype | 9 | childhood_friend / gamer_otaku / heroine / hikikomori / idol / mentor / rival / robot_android / shrine_maiden |
| visual | 5 | animal_ears / glamorous / glasses / petite / silver_hair |
| hobby | 10 | cooking / gamer / music / reading / sports / art / photography / dance / gardening / fortune_telling |

#### Required fields (attribute.schema.json)

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

#### Optional fields

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

#### Relationship and localization fields

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

#### Template generation script

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

#### Validation

```bash
python scripts/validate.py
```

Confirms that all 206 attribute YAMLs validate against the schema.

## License

- Code in this repository: **MIT**
- Templates under `attributes/`: **CC0 1.0** (public domain dedication)
- Disclaimer: be sure to read [DISCLAIMER.md](./DISCLAIMER.md)

## Contributing

1. Add attribute templates in the `attributes/<category>/<name>.yaml` form
2. `examples` / `core_traits` / `catchphrases`, etc. need no source citation (the LLM interprets them), but
   must not include proper nouns or specific works
3. Validate with `python scripts/validate.py` before opening a PR
4. 1 PR = 1 attribute as a rule; for multiple additions, agree in an Issue first

See [CONTRIBUTING.md](./CONTRIBUTING.md) for details.

The implementation guide for agents / developers ("what to build next") is at
[docs/IMPLEMENTATION_GUIDE.md](./docs/IMPLEMENTATION_GUIDE.md).
