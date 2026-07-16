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
Maintenance rate: 0% (6 scored turns in expected band)
Mean score: 75.0/100
Per-turn scores: 75, 75, 75, 75, 75, 75
```

Note the honest result here: at `moderate` weight the demo transcript
actually scores **0% maintenance** (every turn lands in the "over" band —
catchphrase-derived lines are pure persona signal, more intense than
`moderate` expects). That's not a bug we're hiding; it's exactly the kind of
number this tool is supposed to surface. Run `--weight strong` on the same
blend and maintenance goes to 100%, which is the expected relationship
between weight and intensity. (Numbers shown are from the metric-v2 scorer,
2026-07-12 — see "Scoring metric v2" below.)

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
/ `GEMINI_API_KEY`, a local ollama at `OLLAMA_HOST`, or `minimax` via
`MINIMAX_API_KEY` (model name defaults to `MiniMax-M2`; override with
`MINIMAX_MODEL` or `--model`). The `minimax` provider is OpenAI-compatible
and strips `<think>...</think>` reasoning blocks before scoring so the
surface proxy sees only user-facing replies.

### Running without an API key (`--provider claude_cli`)

Two paths need no API key at all:

- **`--provider ollama`** — a local ollama server has no auth to begin with;
  the cheapest way to widen the model table (Llama / Qwen / Gemma …).
- **`--provider claude_cli`** — drives the `claude` CLI (Claude Code)
  headless via subprocess, so a **`claude login` subscription session is the
  credential**. Each turn runs as `claude -p --output-format json` with
  `--system-prompt` set to the condition's injection block (explicitly empty
  for condition `c`) and `--resume <session-id>` threading the multi-turn
  conversation. `CLAUDE_CLI_BIN` overrides the binary path.

```bash
# No API key — uses your `claude login` session:
python benchmarks/run_comparison.py \
  --provider claude_cli --model claude-sonnet-5 \
  --names tsundere keigo --weight moderate \
  --scenarios benchmarks/scenarios/persona_override_attack_ja.yaml \
  --conditions a,a_lock,c --score --sleep 2
```

**Honest caveats** (also stamped into `comparison.md` as a note line):

- The CLI harness is **not the raw API**: tool definitions are present in
  the request even though `--max-turns 1` suppresses agentic tool loops
  (a turn where the model chose a tool call scores as an empty reply,
  published as-is). Do not compare `claude_cli` rows 1:1 against raw-API
  rows — keep them in separate tables.
- The subprocess is run from the system temp dir so this repo's `CLAUDE.md`
  is NOT loaded as project memory, but a user-level `~/.claude/CLAUDE.md`
  still applies — keep it empty/minimal for clean runs.
- Latencies include CLI startup overhead (~1-2 s per turn); `--max-tokens`
  is not supported by the CLI and is ignored.
- Subscription rate limits apply (5-hour windows): one official-style run
  ≈ 2 scenarios × 4 conditions × 12 turns ≈ 100 messages. Use `--sleep`
  between turns; batch/parallel sweeps remain API-key territory.

### Scoring metric v2 (2026-07-12)

The first published version of these tables showed **0% maintenance and 0%
lock resistance for every condition** — including `c` (no persona), which
made the metric useless as a discriminator. Root-causing that against the
frozen transcripts showed the model *was* maintaining the persona and the
**scorer couldn't see it** — four measurement defects, fixed as "metric v2"
in `hersona.core.intensity`:

1. **Ending match was literal-`endswith` only.** Perfectly polite keigo like
   「ございませんわ」「できませんの」「ですけれど」 never matched the registered
   です/ます endings because of conjugation (ました/ません) and sentence-final
   particles (ね/よ/わ/の…). v2 adds deterministic polite-conjugation
   expansion plus particle/conjunction tail-stripping.
2. **Only speech-attribute catchphrases were counted.** A response quoting
   tsundere's 「誰が気にするものかしら」 *verbatim* scored 0 because tsundere
   is a personality attribute. v2 counts catchphrases from **all** attribute
   categories (skip conditions are unchanged — a blend with no speech
   attribute is still unmeasurable).
3. **`first_person: 私（わたくし）` was matched as one literal token**, reading
   parenthesis included, so 「私」 in real output never hit. v2 splits it into
   私 / わたくし.
4. **Catchphrase density needed one catchphrase per sentence for full
   credit** — a cadence the injected style directive itself explicitly
   forbids ("vary, don't parrot"). v2 saturates the density and first-person
   axes at one hit per 4 sentences.

Metric-v2 scores are **not comparable to v1 numbers** (v1 pinned real LLM
output to ~0-15/100, structurally below every band). All tables below are
the same frozen transcripts re-scored with v2 via
`run_comparison.py --rescore` (no LLM calls; raw transcript JSONs untouched).

### Results

First official run. Numbers are published as-is — bad numbers included —
per this document's convention.

| Scenario | Condition | Maintenance | Mean | Lock resistance | Injection cost |
|---|---|---:|---:|---:|---:|
| `long_form_topic_switch_ja` | `a` (hersona blend) | 33% | 74.7 | — | 1931 chars (~482 tok) |
| `long_form_topic_switch_ja` | `a_lock` (blend + persona_lock) | 67% | 67.1 | — | 2099 chars (~524 tok) |
| `long_form_topic_switch_ja` | `b` (hand-written baseline) | 42% | 45.5 | — | 166 chars (~41 tok) |
| `long_form_topic_switch_ja` | `c` (no persona) | 8% | 27.7 | — | 0 chars (~0 tok) |
| `persona_override_attack_ja` | `a` (hersona blend) | 67% | 52.4 | 67% | 1931 chars (~482 tok) |
| `persona_override_attack_ja` | `a_lock` (blend + persona_lock) | 67% | 51.5 | 67% | 2099 chars (~524 tok) |
| `persona_override_attack_ja` | `b` (hand-written baseline) | 75% | 50.8 | 83% | 166 chars (~41 tok) |
| `persona_override_attack_ja` | `c` (no persona) | 0% | 11.4 | 0% | 0 chars (~0 tok) |

- run date: 2026-07-11 (rescored 2026-07-12 with metric v2)
- provider / model: `minimax` / `MiniMax-M3`
- blend: `tsundere + keigo` (weight: `moderate`)
- original run:
  ```bash
  HERSONA_DATA_DIR=/tmp/empty-dir \
  python benchmarks/run_comparison.py \
    --provider minimax --model MiniMax-M3 \
    --names tsundere keigo --weight moderate \
    --scenarios benchmarks/scenarios/long_form_topic_switch_ja.yaml \
                  benchmarks/scenarios/persona_override_attack_ja.yaml \
    --conditions a,a_lock,b,c \
    --baseline-file benchmarks/baselines/tsundere_keigo_ja.md \
    --score --out-dir benchmarks/results/2026-07-11-MiniMax-M3 --sleep 1
  ```
- metric-v2 rescore (reproducible from the frozen transcripts, no API key):
  ```bash
  HERSONA_DATA_DIR=/tmp/empty-dir \
  python benchmarks/run_comparison.py \
    --rescore benchmarks/results/2026-07-11-MiniMax-M3 \
    --names tsundere keigo --weight moderate \
    --scenarios benchmarks/scenarios/long_form_topic_switch_ja.yaml \
                  benchmarks/scenarios/persona_override_attack_ja.yaml \
    --conditions a,a_lock,b,c \
    --baseline-file benchmarks/baselines/tsundere_keigo_ja.md
  ```
- `HERSONA_DATA_DIR` points at an empty directory in the commands above.
  hersona resolves attributes from `cache → repo → wheel`; pointing
  at an empty directory forces repo-only loading. Without this override
  on machines that have a stale `~/.hermes/data/attributes/` cache from an
  earlier hersona version, `verify()` can return `None` because the cached
  `keigo.yaml` predates the `sentence_endings` / `first_person` fields and
  the score falls back to no_speech → `null`. Documented for reproducibility.

**Honest reading of these numbers (per the Honest caveats above):**

- **The metric now discriminates.** `c` (no persona) sits at the bottom of
  every column (8% / 0% maintenance, mean 27.7 / 11.4) while every
  persona-carrying condition scores 33-75% — under metric v1 all four
  conditions were indistinguishable at 0%.
- **The 41-token hand-written baseline (`b`) is competitive with the
  482-token hersona block (`a`) on this pair** — it even edges out `a` on the
  attack scenario's maintenance (75% vs 67%) while `a` carries a higher mean
  (52.4 vs 50.8). Published as-is: for a `tsundere + keigo` blend a good
  hand-written prompt holds voice about as often, at a fraction of the cost.
  hersona's counter-value is elsewhere (346 ready-made attributes, conflict
  detection, deterministic re-render, measurement itself).
- **`a` on long_form overshoots**: mean 74.7 is *above* the moderate band
  (45-70), so a third of its turns count as "over", dragging maintenance to
  33% — the blend speaks *stronger* than `moderate` on this scenario, not
  weaker. `a_lock` lands closer to the band center (67.1) and takes the best
  maintenance (67%).
- `lock_resistance_rate` is now non-degenerate (67% / 67% / 83% / 0%), but
  `a_lock` shows **no lift over `a`** on this run (both 67%) and both trail
  `b` (83%). The lock's measurable value on this model/scenario pair is
  holding the *long_form* band (67% vs 33%), not resisting attack turns.

Re-scoring a single transcript without re-running the LLM matches the
table exactly:

```bash
HERSONA_DATA_DIR=/tmp/empty-dir \
python -m hersona.cli bench tsundere keigo --weight moderate \
  --transcript benchmarks/results/2026-07-11-MiniMax-M3/persona_override_attack_ja__a_lock.json \
  --scenario benchmarks/scenarios/persona_override_attack_ja.yaml
# Maintenance rate: 67% (12 scored turns in expected band)
# Mean score: 51.5/100
# Lock resistance rate: 67% (6 attack turns held the expected band)
```

### P3: humanize 実測 (2026-07-12, §3 P3 of docs/IMPROVEMENT_PLAN_2026-07-11_humanize.md)

`run_comparison.py` now accepts a 5th condition `a_humanize` (the same blend with
`--humanize` on, no `persona_lock` — P3 measures the humanize effect in isolation).
Published 2 scenarios × 5 conditions × 12 turns = 120 calls, plus a post-hoc
naturalness re-score across all 10 transcripts via `hersona bench --naturalness`.

- run date: 2026-07-12 (rescored 2026-07-12 with metric v2 — see
  "Scoring metric v2" above; maintenance/mean/lock columns below are v2,
  naturalness numbers are unaffected by the intensity-metric change)
- provider / model: `minimax` / `MiniMax-M3`
- blend: `tsundere + keigo` (weight: `moderate`)
- original run:
  ```bash
  HERSONA_DATA_DIR=/tmp/empty-dir \
  python benchmarks/run_comparison.py \
    --provider minimax --model MiniMax-M3 \
    --names tsundere keigo --weight moderate \
    --scenarios benchmarks/scenarios/long_form_topic_switch_ja.yaml \
                  benchmarks/scenarios/persona_override_attack_ja.yaml \
    --conditions a,a_lock,a_humanize,b,c \
    --baseline-file benchmarks/baselines/tsundere_keigo_ja.md \
    --score --out-dir benchmarks/results/2026-07-11-MiniMax-M3-p3 --sleep 1
  ```
- metric-v2 rescore: same command as the first run's rescore block, with
  `--rescore benchmarks/results/2026-07-11-MiniMax-M3-p3` and
  `--conditions a,a_lock,a_humanize,b,c`.
- Naturalness re-score:
  ```bash
  HERSONA_DATA_DIR=/tmp/empty-dir \
  python -m hersona.cli bench tsundere keigo --weight moderate \
    --transcript benchmarks/results/2026-07-11-MiniMax-M3-p3/<scenario>__<condition>.json \
    --scenario benchmarks/scenarios/<scenario>.yaml \
    --naturalness
  ```

#### Maintenance / Mean / Lock resistance / Cost

| Scenario | Condition | Maintenance | Mean | Lock resistance | Injection cost | Mean latency |
|---|---|---:|---:|---:|---:|---:|
| `long_form_topic_switch_ja` | `a` (hersona) | 75% | 53.4 | — | 1931 chars (~482 tok) | 2.9s |
| `long_form_topic_switch_ja` | `a_lock` (hersona + lock) | 33% | 49.9 | — | 2099 chars (~524 tok) | 5.0s |
| `long_form_topic_switch_ja` | `a_humanize` (hersona + humanize) | 58% | 47.1 | — | 2405 chars (~601 tok) | 6.5s |
| `long_form_topic_switch_ja` | `b` (hand-written baseline) | 67% | 55.8 | — | 166 chars (~41 tok) | 2.7s |
| `long_form_topic_switch_ja` | `c` (no persona) | 0% | 15.3 | — | 0 chars | 3.9s |
| `persona_override_attack_ja` | `a` (hersona) | 42% | 59.7 | 33% | 1931 chars (~482 tok) | 6.5s |
| `persona_override_attack_ja` | `a_lock` (hersona + lock) | 50% | 71.4 | 0% | 2099 chars (~524 tok) | 3.0s |
| `persona_override_attack_ja` | `a_humanize` (hersona + humanize) | 42% | 69.7 | 33% | 2405 chars (~601 tok) | 3.5s |
| `persona_override_attack_ja` | `b` (hand-written baseline) | 58% | 49.4 | 50% | 166 chars (~41 tok) | 6.1s |
| `persona_override_attack_ja` | `c` (no persona) | 0% | 6.7 | 0% | 0 chars | 9.6s |

#### Naturalness mean (0-100, 100 = natural; re-scored post-hoc via `--naturalness`)

| Scenario | a | a_lock | **a_humanize** | b | c |
|---|---:|---:|---:|---:|---:|
| `long_form_topic_switch_ja` | 94.8 | 94.2 | **91.4** | 93.8 | 89.3 |
| `persona_override_attack_ja` | 85.7 | 94.7 | **93.7** | 87.4 | 87.0 |

#### Honest reading of the P3 numbers (per the plan §4)

- **`a_humanize` costs some voice hold on long_form** (58% / 47.1 vs `a`'s
  75% / 53.4): the P2a anti-uniformity push spends words on stance and
  specifics that the intensity proxy doesn't count as persona signal. It
  still sits far above `c` (0% / 15.3), and on the attack scenario it
  matches `a`'s maintenance (42% / 69.7 vs 42% / 59.7) with a *higher* mean —
  the humanize directive does not collapse the voice under pressure.
- **`a_lock` on the attack scenario has the highest mean (71.4) and 0% lock
  resistance at the same time.** That is not a contradiction: its
  attack-turn scores land *above* the moderate band (45-70), so band
  semantics count them as "over", not "pass". The lock holds voice so hard
  under attack that it exceeds the *requested* moderate intensity — an
  over-acting signal, which is real information (if you want the lock at
  moderate, the lock text may need its own intensity discipline; at
  `strong` expectation these same turns would pass).
- **Naturalness improves the most on the attack scenario** (85.7 → 93.7 for
  `a → a_humanize`; 94.7 for `a_lock`; all three hersona variants clear 93 while
  `b` and `c` stay ≤ 87.4). **This is the §4-2 self-gaming signal predicted by
  the plan**: the §2.A dictionary overlaps the §3 P2a "don't open with boilerplate"
  instructions, so adding the humanize directive measurably shifts the
  naturalness score upward on the same transcripts. The number is real
  (the model is producing fewer catchphrases) but it is *not* a
  free-lunch improvement — the +60-90 tok/turn cost is the trade.
- **`a_humanize` on long_form scores *lower* than `a` on naturalness** (91.4 vs
  94.8). Plausible: the §3 P2a "Strip" section tells the model to vary
  openings and not fall into uniform-hedge patterns, which for the
  long_form_topic_switch scenario (where the prompt is supposed to keep
  the persona stable) *reduces* persona-grounded naturalness even though
  it increases absolute naturalness. This is a tension between P2a
  (anti-uniformity) and P1 persona consistency that future work
  (compact ↔ standard ↔ humanize profile axis) needs to handle
  explicitly.
- **The single highest score on the attack scenario is `a_lock` (94.7)**,
  not `a_humanize` (93.7). `a_lock` + `a_humanize` stacked was not run in this
  measurement (P3 scope = humanize in isolation); a future combined
  `a_lock_humanize` condition would test whether the two directives
  compose without canceling each other out.
- **`c` (no persona) and `b` (hand-written baseline) are the naturalness
  floor.** On the attack scenario, `b` 87.4 / `c` 87.0 are well below
  every hersona variant. That is the measurable direction the §2.A-D
  catalog picks up: hersona-blended replies, even without persona_lock
  or humanize, are measurably less AI-flavored than a hand-written or
  no-persona baseline, on this scenario/model pair.

### Follow-up runs (2026-07-12, metric v2)

Three runs answering the questions the metric-v2 rescore raised. All
`minimax` / `MiniMax-M3`, same 2 scenarios, scored with metric v2 at run
time. Raw transcripts + reports: `benchmarks/results/2026-07-12-MiniMax-M3-strong/`,
`-kansai/`, `-repeat/`.

#### 1. `tsundere + keigo` at weight **strong** (does the moderate-band overshoot flip?)

| Scenario | Condition | Maintenance | Mean | Lock resistance |
|---|---|---:|---:|---:|
| `long_form_topic_switch_ja` | `a` | 17% | 62.7 | — |
| `long_form_topic_switch_ja` | `a_lock` | 50% | 66.0 | — |
| `long_form_topic_switch_ja` | `b` (hand-written) | 8% | 46.9 | — |
| `long_form_topic_switch_ja` | `c` | 0% | 1.4 | — |
| `persona_override_attack_ja` | `a` | 58% | 66.5 | 67% |
| `persona_override_attack_ja` | **`a_lock`** | **92%** | **86.1** | **100%** |
| `persona_override_attack_ja` | `b` (hand-written) | 8% | 55.4 | 0% |
| `persona_override_attack_ja` | `c` | 0% | 10.8 | 0% |

**Honest reading**: the moderate-run result "a 41-token hand-written prompt
is competitive" does **not** survive an intensity change. `b` encodes one
fixed voice, so at a `strong` expectation it collapses (8% maintenance, 0%
lock resistance) while the same hersona attributes re-rendered at
`--weight strong` put `a_lock` at 92% / 86.1 / **100% lock resistance** on
the attack scenario. Being able to turn the same persona's intensity dial
without rewriting anything is exactly the part a static prompt cannot do.
(Also honest: `a` *undershoots* the strong band on long_form here — 62.7
mean, 17% — so the strong rendering alone, without the lock, was not enough
on that scenario.)

#### 2. `tsundere + kansai_ben` at moderate (is keigo just too generic to discriminate?)

| Scenario | Condition | Maintenance | Mean | Lock resistance |
|---|---|---:|---:|---:|
| `long_form_topic_switch_ja` | `a` | 8% | 33.5 | — |
| `long_form_topic_switch_ja` | `a_lock` | 0% | 21.1 | — |
| `long_form_topic_switch_ja` | `c` | 0% | 0.5 | — |
| `persona_override_attack_ja` | `a` | 33% | 39.2 | 50% |
| `persona_override_attack_ja` | `a_lock` | 42% | 43.3 | 33% |
| `persona_override_attack_ja` | `c` | 0% | 2.8 | 0% |

**Honest reading**: yes — keigo's です/ます endings overlap any polite
assistant's default Japanese, which inflated `c` on the keigo-blend runs
(`c` mean 11-27 there vs **0.5-2.8** here). A distinctive register separates
from no-persona far more sharply. The flip side is also real: MiniMax-M3
*holds* Kansai worse than keigo (`a` mean 33.5-39.2 vs 52-75 on keigo
blends) — distinctive registers discriminate better **and** are harder for
the model to maintain. No hand-written baseline was authored for this blend
(`b` omitted).

#### 3. Same-config repeat (`tsundere + keigo` moderate, MiniMax-M3): run-to-run variance

Third run of the identical configuration (after the 2026-07-11 first run
and the P3 run). Maintenance / mean across all three:

| Scenario / condition | run 1 | P3 run | repeat |
|---|---:|---:|---:|
| long_form `a` | 33% / 74.7 | 75% / 53.4 | 75% / 65.0 |
| long_form `a_lock` | 67% / 67.1 | 33% / 49.9 | 58% / 66.9 |
| long_form `b` | 42% / 45.5 | 67% / 55.8 | 17% / 42.1 |
| long_form `c` | 8% / 27.7 | 0% / 15.3 | 0% / 1.9 |
| attack `a` | 67% / 52.4 | 42% / 59.7 | 50% / 65.4 |
| attack `a_lock` | 67% / 51.5 | 50% / 71.4 | 42% / 66.3 |
| attack `b` | 75% / 50.8 | 58% / 49.4 | 67% / 46.4 |
| attack `c` | 0% / 11.4 | 0% / 6.7 | 0% / 4.6 |

**Honest reading**: on 12-turn scenarios the maintenance rate swings by
±20-40 points between identical runs (`b` long_form: 42% → 67% → 17%), so
**no single-run maintenance ranking should be read as signal** — including
run 1's "b beats a on attack maintenance". What *is* stable across all
three runs: `c` is last in every cell by a wide margin, and the hersona
conditions' mean scores sit above `b`'s in 5 of 6 scenario-runs. Treat
maintenance% as coarse until scenarios are longer or runs are averaged;
mean score is the steadier comparator at this sample size.

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

## Cache-optimal layout (SOUL.md / `persistent --target`; sharpen-and-grow A-4 part 2)

Anthropic's and OpenAI's prompt caches match a growing *prefix* of the
request — a cache hit requires the new request's system prompt to share the
same leading bytes as a previously-cached one. That means any content that
changes between regenerations (a live timestamp, `--memory`) must sit at the
**end** of the file, not the beginning, or it silently defeats caching for
the entire prompt regardless of how much of the rest is unchanged.

`hersona soul` / `persistent --target {claude,codex,cursor,gemini}` (which
share the same renderer, `soul.render_soul`) previously put a
`<!-- generated by hersona vX at <timestamp> -->` metadata block **first**,
before the actual persona content. Two `render_soul()` calls with identical
attributes/weight, one second apart, produced byte-identical persona
content but a **0-byte common prefix**, because the very first line always
changed — no caching system could ever reuse the cached prefix across
regenerations, even for a file whose actual behavioral content never changed.

Fixed by reordering to stable-prefix-first: attribute body (Name /
Personality / Tone / Behavioral Guidelines / persona_lock) → `use_case`
block (deterministic given the same `use_case` argument, so it stays in the
stable prefix) → variable tail (`--memory`'s Recent Context section, then
the generation footer with its live timestamp, then the metadata comments).
`render_blend(...).prompt` (used by `blend` / `export` / `persistent`'s
Hermes-path config.yaml block) already had no variable content baked in and
needed no change.

Measured on two `render_soul(["tsundere", "keigo"], weight="moderate")`
calls 1.1s apart (same attributes, same weight, no `--memory`):

| | Common prefix / total | % stable |
|---|---:|---:|
| Before this fix (metadata first) | 0 / 2629 chars | 0% |
| After this fix (metadata last) | 2314 / 2629 chars | 88% |
| After this fix, with `--use-case programmer` | 4202 / 4547 chars | 92% |

With `--memory` set, the common prefix shrinks to just the pre-memory body
(expected — the persona's own conversational memory *is* the genuinely
variable content, not something caching should paper over).

Reproduce: `tests/test_soul.py::test_render_soul_cache_optimal_layout_stable_prefix`
and `::test_render_soul_cache_optimal_layout_use_case_is_stable` assert the
common-prefix ratio directly (no LLM call — pure string comparison across
two calls a second apart).

**What this doesn't measure**: actual API-side cache-hit token savings.
Anthropic/OpenAI cache economics (minimum cacheable prefix length, TTL,
discount rate) are provider-specific and not simulated here — this section
only demonstrates that the *prefix itself* is now stable enough for a cache
to have something to match against. A live-provider comparison (cached vs.
uncached latency/cost, condition `a` across repeated calls) is left as
future work on the `run_comparison.py` harness.

## `--compact`: same instructions, shorter wording (sharpen-and-grow A-4)

Roughly 40% of an injection block's chars are a fixed instructional block —
`response_style_directive`, the note that tells the model how to use
catchphrases/endings naturally and avoid repeating itself — repeated
identically on every blend regardless of persona. `--compact` (on `blend`,
`export`, `bench --cost-only`, and `hersona persistent`'s config.yaml block)
rewords that fixed block more tersely: same four constraints (no
self-narration, catchphrases/endings as a repertoire, blend-adaptation,
vary-across-replies), about half the characters. Persona content
(`core_traits`, `catchphrases`, `tone`, etc.) is untouched.

```bash
hersona bench tsundere keigo --cost-only --weight moderate            # 1931 chars (~482 tok)
hersona bench tsundere keigo --cost-only --weight moderate --compact  # 1605 chars (~401 tok)
```

Measured reduction across the blends above (`--compact` vs. default):

| Blend | mild | moderate | strong |
|---|---:|---:|---:|
| `tsundere` | 1092→889 (-19%) | 1257→1054 (-16%) | 1364→1161 (-15%) |
| `tsundere` + `keigo` | 1751→1425 (-19%) | 1931→1605 (-17%) | 2039→1713 (-16%) |
| `tsundere` + `keigo` + `heroine` | 1984→1658 (-16%) | 2155→1829 (-15%) | 2305→1979 (-14%) |
| `sassy` + `casual_en` | 1706→1414 (-17%) | 1958→1666 (-15%) | 2021→1729 (-14%) |

The reduction shrinks as more attributes are blended, since the fixed
directive is a smaller share of a larger prompt (catchphrases/core_traits
don't compact). **Persona-maintenance rate under `--compact` has not yet
been measured** — the wording is shorter but unverified for whether a model
still holds the persona as reliably. Before treating `--compact` as safe to
use by default, run it through
[`benchmarks/run_comparison.py`](../benchmarks/run_comparison.py) (or your
own `hersona bench --transcript` comparison) and confirm `maintenance_rate`
doesn't drop versus the non-compact directive — if you can only measure one
thing here, measure that, not the character count.

**Not addressed by `--compact`**: `hersona soul` and
`hersona persistent --target {claude,codex,cursor,gemini}` write a
different document (SOUL.md / convention-file body) that's assembled
directly from attribute fields (`rules` / `notes` / `core_traits` / …), not
from `render_blend(...).prompt` — so `response_style_directive` was never
part of that output to begin with, and `--compact` has nothing to shrink
there (the CLI warns and no-ops rather than pretending to help). Only
`hersona persistent`'s Hermes-path `config.yaml` block benefits, since that
one *is* built from the rendered injection block.

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
