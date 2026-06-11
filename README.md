# hersona

[English](./README.md) · [**日本語**](./README.ja.md)

> A template collection of **speech style, personality, and vocabulary** attributes for anime / game / manga characters
> Usable as a `/hersona` preset in AI agents (Hermes Agent, etc.)

[![License: MIT (code)](https://img.shields.io/badge/License-MIT-lightgrey.svg)](./LICENSE)
[![Templates: CC0 1.0](https://img.shields.io/badge/Templates-CC0_1.0-lightgrey.svg)](./LICENSE-CC0.txt)

## License structure (v1.0)

The repository is split into two layers, each under a different license:

| Scope | License | Notes |
|---|---|---|
| `scripts/`, `schema/`, `pyproject.toml`, etc. (code) | **MIT** | `LICENSE` |
| `attributes/**/*.yaml` (general attribute templates) | **CC0 1.0** | `LICENSE-CC0.txt` — public domain dedication |

> The v0.x line used a three-layer structure (code MIT / attributes CC0 / character data CC BY-SA 4.0), but
> v1.0 removed all character-dependent YAML under data/ entirely and moved to a design that ships **general attributes only**.

## Overview

An open-source project that systematizes the speech and personality of anime / game / manga characters as
**work-independent combinations of attributes**, distributed as a template collection that can be injected into
an AI agent's system prompt.

Through v0.x it shipped per-character YAML/MD (e.g. "Merina", "Rin Tohsaka", "Power"), but in v1.0 it has moved to
an architecture where:

- Per-character dependent data is removed entirely
- Instead it provides **attribute templates** such as `tsundere` / `keigo` / `heroine` (`attributes/<category>/<name>.yaml`)
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

After `pip install -e .`, the `hersona` command (or `python -m hersona.cli`) is available.
The default UI language is **English**; pass `--lang ja` or set `HERSONA_LANG=ja` to switch to Japanese:

```
hersona list                                  # list available attributes (public + user)
hersona show tsundere                          # attribute details
hersona matrix --json                          # dump the compatibility matrix as JSON
hersona blend tsundere keigo --weight strong   # compose attributes into an injection block (with intensity)
hersona recommend                              # diagnostic quiz -> recommendation (interactive)
hersona recommend --answers distance=1,speech=0,role=1 --apply
hersona create --category personality --name my_attr \
  --display-ja マイ属性 --display-en MyAttr \
  --desc-ja 説明 --desc-en desc --example "..."  # create an attribute and save to the user namespace
hersona measure kyoto_ben --weight strong --text "ようおいでやすどす"  # score intensity metrics of output
hersona measure tsundere heroine --weight moderate --input out.txt       # intensity metrics of a blend
hersona list --lang ja                         # Japanese UI
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
├── speech/                  # speech attributes (20)
├── archetype/               # archetype attributes (9)
├── visual/                  # visual attributes (5)
└── hobby/                   # hobby attributes (5)
```

Every attribute YAML conforms to [`schema/attribute.schema.json`](./schema/attribute.schema.json).

### Attribute templates (`attributes/`, v1.0+)

A template collection of **general attribute tags** to attach to a character profile, validated by
[schema/attribute.schema.json](./schema/attribute.schema.json). It currently defines 59 in total:
personality 20 / speech 20 / archetype 9 / visual 5 / hobby 5 (see under [attributes/](./attributes/)).

#### The 59 attributes

| category | count | attributes included |
|---|---|---|
| personality | 20 | airhead / chuunibyou / dandere / genki / hot_blooded / intellectual / klutz / kuudere / mysterious / narcissist / optimist / pessimist / playful / pragmatist / protective / serious / stoic / switch / tsundere / yandere |
| speech | 20 | archaic / blunt / boku_girl / gyaru / kansai_ben / keigo / kyoto_ben / mischievous / mixed_dialect / onee_kotoba / ore_boy / princess_speech / seductive / soft / stutter / theatrical / third_person / tomboy / washi / whispery |
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
| `examples` | string[] (1+) | ✓ | AI-agent usage examples (5 patterns recommended: injection / intensity / compatibility / NG). No proper nouns or specific works |

#### Optional fields (6 Round-3 template fields)

| field | type | description |
|---|---|---|
| `core_traits` | string[] (3-7) | personality trait list; the core the AI agent interprets at injection time |
| `speech_style` | string | overall description of the speech style (1 line) |
| `second_person` | string | second person (e.g. "貴方", "お前"); may include the user's role name |
| `sentence_endings` | string[] (3+) | sentence-ending patterns (e.g. "〜の", "〜のね") |
| `catchphrases` | string[] (optional) | catchphrases (3+ recommended) |
| `tone` | string | atmosphere of the voice (1 line) |

#### Relationship fields

| field | type | description |
|---|---|---|
| `compatible_archetypes` | string[] | list of archetype attribute_names expected to pair well |
| `conflicts_with` | string[] | list of other attribute_names expected to be mutually exclusive |
| `tags` | string[] | tags for cross-cutting search |
| `typical_value_range` | string | typical value when used with weighting (e.g. `0.4-0.7`) |
| `has_catchphrase` | bool | whether catchphrases exist |
| `variant` | string (snake_case) | variant label of the same attribute_name |
| `notes` | string | supplementary / operational notes |

#### Template generation script

`scripts/_oneoff/gen_v1_attributes.py` can regenerate the YAML as a Single Source of Truth.
Instead of editing YAML directly, update the lists and re-run:

```bash
# regenerate the 59 attribute YAMLs without confirmation
python scripts/_oneoff/gen_v1_attributes.py

# only show the paths that would be written
python scripts/_oneoff/gen_v1_attributes.py --dry-run
```

#### Validation

```bash
python scripts/validate.py
```

Confirms that all 59 attribute YAMLs validate against the schema.

## License

- Code in this repository: **MIT**
- Templates under `attributes/`: **CC0 1.0** (public domain dedication)
- Disclaimer on character rights / derivative works / commercial use: be sure to read [DISCLAIMER.md](./DISCLAIMER.md)

## Contributing

1. Add attribute templates in the `attributes/<category>/<name>.yaml` form
2. `examples` / `core_traits` / `catchphrases`, etc. need no source citation (the LLM interprets them), but
   must not include proper nouns or specific works
3. Validate with `python scripts/validate.py` before opening a PR
4. 1 PR = 1 attribute as a rule; for multiple additions, agree in an Issue first

See [CONTRIBUTING.md](./CONTRIBUTING.md) for details.

The implementation guide for agents / developers ("what to build next") is at
[docs/IMPLEMENTATION_GUIDE.md](./docs/IMPLEMENTATION_GUIDE.md).
