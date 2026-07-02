# Self-introduction (cross-persona)

**Canonical guides (repo):**

- [self-introduction.ja.md](../../../docs/guides/self-introduction.ja.md)
- [self-introduction.md](../../../docs/guides/self-introduction.md)

**SOUL `--memory` contract:** [soul_md_persistence.md §12](../../../docs/soul_md_persistence.md#12-recent-context-and-reserved-memory-keys)

| Key | Purpose |
|-----|---------|
| `self_intro_canonical` | Public intro (≤512 chars) |
| `self_intro_style` | Pointer to guides |
| `privacy_inner_circle` | Family / third-party privacy |
| `self_intro_canonical_ref` | Profile file path if text >512 chars |

**Example:** `examples/self-intro-memory.json` + `hersona soul ... --memory-file ...`

**CLI lint (Phase 2):**

```bash
hersona lint-intro --text "..." --allow-handle hersona_agent --canonical
hersona lint-intro --input draft.txt --json
```

When the user asks for a **self-introduction** (自己紹介): read the JA or EN guide, use `self_intro_canonical` from SOUL Recent Context if present, apply persona voice without meta / AI self-label / third-party names. Profile-specific deltas live in the Hermes skill `hermes-hersona-personality` (e.g. Sona).