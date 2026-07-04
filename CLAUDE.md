# CLAUDE.md

Guidance for AI agents (Claude Code, etc.) working in this repository.
The authoritative rules live in [CONTRIBUTING.md](./CONTRIBUTING.md); this file is
the short, must-follow summary.

## Update rule (keep docs in sync)

When you make a change that affects features or contracts, **check the README in
the same change and update it if it has drifted.** Do not leave README updates
"for later".

Check **both** `README.md` and `README.ja.md` (keep EN/JA in sync) whenever you
change any of:

- CLI subcommands / flags
- the `/hersona` skill's command syntax, modes, or behavior
- the attribute schema (`schema/attribute.schema.json`) or attribute count /
  categories (currently 224 / 5 categories)
- the public API (`hersona.core` / `docs/PUBLIC_API.md`)
- export formats / framework integrations
- any new user-facing file or doc (e.g. adding `REFERENCE.md` → link it from the README)

Then add a `## [Unreleased]` entry in `CHANGELOG.md` and run
`python scripts/validate.py` and `pytest`.

**If you add or remove attribute YAMLs**, also run:

```bash
python scripts/build_site.py
```

This regenerates `docs/app/data.json` (the site data file). CI's
`build_site.py --check` gate will fail if this file is stale.
`validate.py` and `pytest` do **not** cover this step.

## SKILL.md authoring rules

`skills/hersona/SKILL.md` is loaded into the LLM context **every turn the skill is
active**, so write it with token cost in mind (it directly affects perceived
conversation speed).

- **Write the body in English.** For the same meaning, Japanese costs more tokens
  than English (measured: an equivalent directive is 157 tok JA vs 102 tok EN).
- **Keep the Japanese trigger examples in the front-matter `description`** (e.g.
  'ツンデレで話したい'). They are functional matching keywords for activating the
  skill on Japanese input; translating them breaks activation for JA users.
- **Put detailed reference in `REFERENCE.md` (on-demand).** Flag examples,
  verification checklist, one-shot recipes, version history — anything not needed
  to converse — goes there, not in the always-loaded body.
- **Don't duplicate injection-block directives.** Anti-repetition / naturalness /
  catchphrase & sentence-ending usage are consolidated into
  `hersona.core.attach.response_style_directive`. Extend it rather than adding new
  per-section directives (avoids per-turn cost growth).
- **Never translate persona content** (catchphrases / sentence_endings / tone /
  core_traits) — it is language-bound and is the persona itself. Only directive
  prose is subject to language optimization.
- `version:` is an independent SemVer (see CONTRIBUTING.md "スキルのバージョン管理").
