# hersona demo site

日本語版: [`README.md`](./README.md)

A **static demo site** for experiencing hersona's value proposition (dressing
an agent in a standardized personality with one line). Deployable on GitHub
Pages (no backend required).

## Structure

| File | Role |
|---|---|
| `index.html` | The page itself (bilingual EN/JA; switch with `日本語 / EN / 併記` in the header) |
| `style.css` | Styles |
| `app.js` | Attribute catalog, before/after demo, blend injection-prompt generation, diagnostic quiz logic |
| `data.json` | **Auto-generated**. A dump of `attributes/**/*.yaml` + the diagnostic quiz (both the BASE/ja quiz and the English-persona `quiz_en`) + intensity guidance |
| `showcase.json` | Pre-recorded responses for the before/after demo (hand-written, EN/JA, 3 intensity levels) |

`app.js`'s `renderPrompt` / `recommend` are faithful ports of the logic in
`hersona/core/attach.py` / `hersona/core/recommend.py` (output parity
verified).

## Sections

1. **Live demo** — Shows the same prompt before/after an attribute is applied,
   side by side. Has an intensity slider.
2. **Attribute catalog** — Filter 345 attributes by category; click a card for
   details (core_traits / catchphrases / tone / compatibility).
3. **Blend & injection-prompt generator** — Pick multiple attributes and
   compose them. Conflicts are flagged automatically, and the resulting
   system-prompt injection block can be copied.
4. **Diagnostic quiz** — Answer 9 questions to get a conflict-checked
   recommended blend. When the display language is EN, the quiz uses a
   separate English-persona question set (`quiz_en`) whose weights route
   toward English speech attributes, not just an English label swap of the
   Japanese quiz. The result card can be sent straight to the blend generator,
   or copied directly as an injection block.

## Regenerating the data

After editing `attributes/`, regenerate `data.json` and commit it:

```bash
python scripts/build_site.py          # regenerate docs/app/data.json
python scripts/build_site.py --check  # CI: verify it's up to date
```

> `build_site.py` only needs PyYAML (no `jsonschema` dependency).

## Checking it locally

```bash
cd docs/app && python3 -m http.server 8000
# → http://localhost:8000
```

## Deployment

GitHub Pages serves the `/docs` folder (landing page at `docs/index.html`,
demo app in this directory `docs/app/`). In the repository's
**Settings → Pages → Build and deployment → Source**, set it to
**Deploy from a branch**, branch `main` / folder `/docs`.
