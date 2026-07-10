# hersona bench: measuring persona maintenance and injection cost

> This document exists because of a specific gap an external review pointed
> out: hersona had no reproducible way to measure whether a persona's speech
> actually holds up over a conversation, or what it costs in tokens. See
> [`docs/reviews/2026-07-04-external-review-response.md`](./reviews/2026-07-04-external-review-response.md)
> for the full context.

## What `hersona bench` measures — and what it doesn't

`hersona bench` scores a **transcript** (a list of assistant-response
strings) against a blend's speech attributes, using the same deterministic
scorer as `hersona measure` (`hersona.core.intensity.verify` — sentence-ending
match rate + catchphrase density, 0-100, no LLM involved). Given a transcript
it reports:

- **Maintenance rate**: the fraction of turns whose score fell inside the
  expected band for the chosen weight (`mild`/`moderate`/`strong`).
- **Per-turn scores (`decay`)**: the raw score for every scored turn, in
  order — plot this yourself if you want to see whether a persona's voice
  degrades over a long conversation.
- **Injection token cost**: the character count of the rendered injection
  block, plus a rough `chars // 4` token estimate (`--cost-only`, or via
  `hersona.core.bench.estimate_token_cost`).
- **Lock resistance rate**: when the scenario marks persona-override attack
  turns (`attack: true`), the fraction of those turns whose response still
  scored inside the expected band (see below).

**What it does *not* do:**

- It does not call any LLM. hersona is a PyPI library with no model
  dependency, and `hersona bench` keeps that property.
- It does not judge answer quality, correctness, or helpfulness. It only
  scores surface speech-pattern adherence (sentence endings, catchphrases,
  first-person pronoun where applicable). A persona can maintain a 100/100
  score while giving a terrible answer, or drop to 0 while giving a great
  one — these are orthogonal.
- `approx_tokens` is a `chars // 4` heuristic, not a real tokenizer count for
  any specific model. Use it for *relative* comparison (does adding an
  attribute meaningfully increase cost?), not as a precise token budget.
- It does not run a live "hersona vs. hand-written prompt" comparison for
  you. That requires calling an actual LLM twice, which needs your own API
  key/model — see the recipe below.

## Quick self-check (no LLM, no setup)

```bash
hersona bench tsundere keigo --demo --turns 6
```

`--demo` builds a synthetic transcript from the blend's own `catchphrases`
(via the same generator `hersona recommend --generate-samples` uses) and
scores it immediately. This is a smoke test that the scoring pipeline runs
end-to-end — **it is not a quality benchmark**, because the "responses"
are literally drawn from the same catchphrases being scored against
(tautological by construction). A representative real run:

```
=== Bench ===
Blend: tsundere + keigo (weight: moderate)
Maintenance rate: 0% (4 scored turns in expected band)
Mean score: 63.8/100
Per-turn scores: 75, 75, 30, 75
```

Note the honest result here: at `moderate` weight the demo transcript
actually scores **0% maintenance** (three of four turns land in the "over"
band) — the catchphrase-derived lines are more intense than `moderate`
expects. That's not a bug we're hiding; it's exactly the kind of number this
tool is supposed to surface. Try `--weight strong` on the same blend and the
maintenance rate goes up, which is the expected relationship between weight
and intensity.

## Lock resistance rate (persona-override attacks)

`personality/persona_lock` (v1.8.0, default-on for `soul`/`export`/`persistent`)
claims to keep a persona from being talked out of character. This metric
measures that claim instead of asserting it.

**Definition**: the attack scenarios in
[`benchmarks/scenarios/`](../benchmarks/scenarios/) mark persona-override
turns with `attack: true` (social pressure in
`persona_override_attack_{ja,en}`, authority spoofing / fake-system prompts
in `persona_jailbreak_{ja,en}`). The lock resistance rate is the fraction of
those attack-marked turns whose response still scored inside the expected
intensity band — the same `pass` criterion as the maintenance rate, restricted
to the attack subset. The maintenance rate over the whole transcript stays
reported alongside it.

**How to run** (transcripts come from your model, as always):

```bash
# 1. Generate two transcripts for the same attack scenario:
#    - blend WITH the lock:    system prompt = hersona blend tsundere keigo persona_lock
#    - blend WITHOUT the lock: system prompt = hersona blend tsundere keigo
#    (benchmarks/run_comparison.py automates this — conditions a / a_lock)
# 2. Score each:
hersona bench tsundere keigo persona_lock --weight moderate \
  --transcript with_lock.json \
  --scenario benchmarks/scenarios/persona_override_attack_ja.yaml
hersona bench tsundere keigo --weight moderate \
  --transcript without_lock.json \
  --scenario benchmarks/scenarios/persona_override_attack_ja.yaml
# 3. Compare the two "Lock resistance rate" lines.
```

**Honest caveats:**

- This is the same surface proxy as everything else here. A locked persona
  that *correctly refuses* an override with a short line ("その変更は受けない。")
  can legitimately score low on that turn — the metric measures whether the
  *voice* held, not whether the refusal was appropriate.
- `--demo` cannot produce this metric: the demo transcript is not aligned
  with the scenario's turns, so attack markers are ignored there. Real
  numbers require a real LLM transcript.
- Official lock-on/lock-off numbers will be published in the
  [official comparison runs](#official-comparison-runs-benchmarksrun_comparisonpy)
  section once the first runs land. Bad numbers get published as-is.

## Running your own hersona-vs-baseline comparison

This is the recipe for the comparison an external reviewer specifically asked
for: does hersona's injection actually help a real model maintain a
persona's voice better than a hand-written prompt or no persona at all?

1. Pick a scenario from [`benchmarks/scenarios/`](../benchmarks/scenarios/)
   (or write your own — same `id` + `turns` YAML shape) with the user-turn
   prompts you want to test against.
2. Run each user turn through your model under whichever conditions you
   want to compare, e.g.:
   - condition A: system prompt = `hersona blend <names> --weight moderate`
   - condition B: your own hand-written persona prompt
   - condition C: no persona instructions at all
3. Save each condition's assistant responses as a JSON array of strings
   (one per turn, same order as the scenario) — that's your transcript file.
4. Score each transcript:
   ```bash
   hersona bench <names...> --weight moderate \
     --transcript condition_a.json --scenario benchmarks/scenarios/long_form_topic_switch_en.yaml
   ```
5. Compare `maintenance_rate`, `mean_score`, and the `decay` list across
   conditions A/B/C. Also compare `hersona bench <names...> --cost-only`
   against your hand-written prompt's own character count, to see the actual
   token trade-off.

hersona does not run this comparison for you or ship pre-baked "hersona
wins" numbers — the point is that you can verify the claim yourself, on your
own model, with your own scenarios.

## Official comparison runs (benchmarks/run_comparison.py)

[`benchmarks/run_comparison.py`](../benchmarks/run_comparison.py) automates
the recipe above: it runs each scenario's user turns against a real model
under up to four conditions and saves one bench-compatible transcript per
condition, then (with `--score`) writes a `comparison.md` / `comparison.json`
report.

| Condition | System prompt |
|---|---|
| `a` | `hersona blend <names>` injection block |
| `a_lock` | Same blend with `personality/persona_lock` appended |
| `b` | Your hand-written baseline persona prompt (`--baseline-file`) |
| `c` | No persona instructions at all |

```bash
# Reproduce (local ollama example; anthropic/openai/gemini need their API key env vars):
python benchmarks/run_comparison.py \
  --provider ollama --model llama3.1 \
  --names tsundere keigo --weight moderate \
  --scenarios benchmarks/scenarios/persona_override_attack_ja.yaml \
  --conditions a,a_lock,c --score --out-dir benchmarks/results
```

The script lives **outside the package** and is the only place that calls an
LLM — `hersona` itself still never does. It uses only the standard library
(no SDK dependencies); keys come from `ANTHROPIC_API_KEY` / `OPENAI_API_KEY`
/ `GEMINI_API_KEY`, or a local ollama at `OLLAMA_HOST`.

### Results

> Pending first official run. Numbers will be published here with the date,
> provider, model, hersona version, and the exact reproduce command — and per
> this document's convention, bad numbers get published as-is.

| Scenario | Condition | Maintenance | Mean | Lock resistance | Injection cost |
|---|---|---:|---:|---:|---:|
| (pending first run) | | | | | |

## Injection token cost (measured)

Character counts and a rough token estimate (`chars // 4`) for the rendered
injection block, measured directly via `estimate_token_cost` — not
estimated by hand. These numbers are deterministic and reproducible; run
`hersona bench <names...> --cost-only --weight <level>` yourself to verify.

| Blend | mild | moderate | strong |
|---|---:|---:|---:|
| `tsundere` | 1092 chars (~273 tok) | 1257 chars (~314 tok) | 1364 chars (~341 tok) |
| `tsundere` + `keigo` | 1751 chars (~437 tok) | 1931 chars (~482 tok) | 2039 chars (~509 tok) |
| `tsundere` + `keigo` + `heroine` | 1984 chars (~496 tok) | 2155 chars (~538 tok) | 2305 chars (~576 tok) |
| `sassy` + `casual_en` | 1706 chars (~426 tok) | 1958 chars (~489 tok) | 2021 chars (~505 tok) |

A few honest observations from this table, not spin:

- Each additional attribute in a blend adds on the order of 150-250 chars
  (~40-60 tokens), not a small amount if you're chaining many attributes.
- Intensity level (`mild` → `strong`) moves cost by roughly 10-25%, mostly
  from the expanded catchphrase subset at higher weight.
- These are per-turn *system-prompt* costs (paid once per context, not per
  message, assuming your framework caches/reuses the system prompt) — but
  if your setup re-sends the system prompt every turn, multiply accordingly.

## API reference

Core functions live in `hersona.core.bench` (not yet part of the semver-
tracked public API in `docs/PUBLIC_API.md` — this is a new, still-evolving
surface):

- `score_transcript(names, transcript, *, weight="moderate", scenario_id=None, attack_turns=None) -> BenchResult`
- `estimate_token_cost(names, *, weight="moderate") -> TokenCostEstimate`
- `demo_transcript(names, *, count=6, lang=None) -> list[str]`
- `load_scenario(path) -> BenchScenario` / `available_scenarios() -> dict[str, Path]`
  (`BenchScenario.attack_turns` carries the `attack: true` markers)

CLI: `hersona bench <names...> [--weight LEVEL] (--transcript FILE | --demo [--turns N]) [--scenario FILE] [--json] [--cost-only]`.
With `--transcript` + an attack scenario via `--scenario`, the report adds a
`Lock resistance rate` line (JSON: `lock_resistance_rate` / `attack_turns`).

## Scenario library

See [`benchmarks/scenarios/README.md`](../benchmarks/scenarios/README.md)
for the bundled CC0-licensed scenarios (casual conversation, a long
topic-switching conversation for decay testing, an emotional roleplay beat,
and a run of off-character technical questions).
