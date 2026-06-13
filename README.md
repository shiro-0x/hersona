# hersona

[**English**](./README.md) · [日本語](./README.ja.md)

> A template collection of **speech style, personality, and vocabulary** attributes for anime characters
> Designed to be used as a `/hersona` preset in AI agents (Hermes Agent, etc.)

[![License: MIT (code)](https://img.shields.io/badge/License-MIT-lightgrey.svg)](./LICENSE)
[![Templates: CC0 1.0](https://img.shields.io/badge/Templates-CC0_1.0-lightgrey.svg)](./LICENSE-CC0.txt)

## License structure (v0.0.1)

The repository is split into two layers, each under a different license:

| Scope | License | Notes |
|---|---|---|
| `scripts/`, `schema/`, `pyproject.toml`, etc. (code) | **MIT** | `LICENSE` |
| `attributes/**/*.yaml` (general attribute templates) | **CC0 1.0** | `LICENSE-CC0.txt` — public domain dedication |

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

See [skills/hersona/SKILL.md](./skills/hersona/SKILL.md) for details.

### Use from the CLI

After `pip install -e .`, the `hersona` command (or `python -m hersona.cli`) is available:

```
hersona list                                  # list available attributes (public + user)
hersona show tsundere                          # attribute details
hersona matrix --json                          # dump the compatibility matrix as JSON
hersona blend tsundere keigo --weight strong   # compose attributes into an injection block (with intensity)
hersona recommend                              # diagnostic quiz -> recommendation (interactive; en UI routes to English speech)
hersona recommend --answers distance=1,speech=0,role=1 --apply
hersona create --category personality --name my_attr \
  --display-ja マイ属性 --display-en MyAttr \
  --desc-ja 説明 --desc-en desc --example "..."  # create an attribute and save to the user namespace
hersona measure kyoto_ben --weight strong --text "ようおいでやすどす"  # score intensity metrics of output
hersona measure tsundere heroine --weight moderate --input out.txt       # intensity metrics of a blend
```

User-created attributes are saved under `~/.hermes/attributes/` (default) or the directory specified by
`HERSONA_USER_DIR`, and never mix into the public `attributes/`.

### Use with other LLMs

Paste fields such as `core_traits` / `catchphrases` / `tone` / `description_en` from
`attributes/<category>/<name>.yaml` directly into the system prompt.

When blending multiple attributes, check compatibility via each YAML's `compatible_archetypes` /
`conflicts_with`.

## Data format

```
attributes/
├── personality/             # personality attributes (20)
├── speech/                  # speech attributes (25: ja 20 + en 5)
├── archetype/               # archetype attributes (9)
├── visual/                  # visual attributes (5)
└── hobby/                   # hobby attributes (5)
```

Every attribute YAML conforms to [`schema/attribute.schema.json`](./schema/attribute.schema.json).

### Attribute templates (`attributes/`, v0.0.1+)

A template collection of **general attribute tags** to attach to a character profile, validated by
[schema/attribute.schema.json](./schema/attribute.schema.json). It currently defines 64 in total:
personality 20 / speech 25 / archetype 9 / visual 5 / hobby 5 (see under [attributes/](./attributes/)).
The speech category spans 20 Japanese (`content_lang: ja`) and 5 English (`content_lang: en`) registers.

#### The 64 attributes

| category | count | attributes included |
|---|---|---|
| personality | 20 | airhead / chuunibyou / dandere / genki / hot_blooded / intellectual / klutz / kuudere / mysterious / narcissist / optimist / pessimist / playful / pragmatist / protective / serious / stoic / switch / tsundere / yandere |
| speech (ja) | 20 | archaic / blunt / boku_girl / gyaru / kansai_ben / keigo / kyoto_ben / mischievous / mixed_dialect / onee_kotoba / ore_boy / princess_speech / seductive / soft / stutter / theatrical / third_person / tomboy / washi / whispery |
| speech (en) | 5 | formal_en / casual_en / blunt_en / southern_us_en / british_en |
| archetype | 9 | childhood_friend / gamer_otaku / heroine / hikikomori / idol / mentor / rival / robot_android / shrine_maiden |
| visual | 5 | animal_ears / glamorous / glasses / petite / silver_hair |
| hobby | 5 | cooking / gamer / music / reading / sports |

#### Required fields (attribute.schema.json)

| field | type | required | description |
|---|---|---|---|
| `attribute_category` | enum | ✓ | one of `personality` / `speech` / `archetype` / `visual` / `hobby` |
| `attribute_name` | string (snake_case) | ✓ | unique ID matching the file name |
| `display_name_ja` / `display_name_en` | string | ✓ | Japanese / English display name |
| `weight_dimension` | enum | ✓ | `none` / `mild` / `moderate` / `strong` |
| `description_ja` / `description_en` | string | ✓ | attribute description |
| `examples` | string[] (1+) | ✓ | AI-agent usage examples (7 patterns recommended: injection / intensity x2 / compatibility / multi-turn dialogue / English dialogue / NG). No proper nouns or specific works |

#### Optional fields (6 Round-3 template fields)

| field | type | description |
|---|---|---|
| `core_traits` | string[] (3-7) | personality trait list; the core the AI agent interprets at injection time |
| `speech_style` | string | overall description of the speech style (1 line) |
| `second_person` | string | second person (e.g. "貴方", "お前"); may include the user's role name |
| `sentence_endings` | string[] (3+) | sentence-ending patterns (ja speech, e.g. "〜の", "〜のね") |
| `lexical_markers` | string[] | characteristic words/phrases (en speech, e.g. "gonna", "y'all"); used for en intensity |
| `register` | enum | speech register: `formal` / `neutral` / `casual` / `vulgar` (mainly en speech) |
| `catchphrases` | string[] (optional) | catchphrases (3+ recommended) |
| `tone` | string | atmosphere of the voice (1 line) |

#### Relationship fields

| field | type | description |
|---|---|---|
| `compatible_archetypes` | string[] | list of archetype attribute_names expected to pair well |
| `conflicts_with` | string[] | list of other attribute_names expected to be mutually exclusive |
| `tags` | string[] | tags for cross-cutting search |
| `typical_value_range` | string | typical value when used with weighting (e.g. `0.4-0.7`) |
| `content_lang` | enum (`ja`/`en`) | language of the persona-content fields; drives response-language directives and intensity. Absent ⇒ `ja` |
| `content_i18n` | object | per-language native content (`<lang>.{catchphrases,tone,core_traits,examples}`); BASE top-level fields are the `content_lang` language, `content_i18n.en` adds the English version. Keeps injected catchphrases in the persona's language |
| `has_catchphrase` | bool | whether catchphrases exist |
| `variant` | string (snake_case) | variant label of the same attribute_name |
| `notes` | string | supplementary / operational notes |

#### Template generation script

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

Confirms that all 64 attribute YAMLs validate against the schema.

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
