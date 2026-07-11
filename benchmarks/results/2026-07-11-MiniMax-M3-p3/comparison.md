# hersona comparison run

- date: 2026-07-12
- provider / model: minimax / MiniMax-M3
- hersona: v1.7.0
- blend: tsundere + keigo (weight: moderate)
- reproduce: `run_comparison.py --provider minimax --model MiniMax-M3 --names tsundere keigo --weight moderate --scenarios benchmarks/scenarios/long_form_topic_switch_ja.yaml benchmarks/scenarios/persona_override_attack_ja.yaml --conditions a,a_lock,a_humanize,b,c --baseline-file benchmarks/baselines/tsundere_keigo_ja.md --score --out-dir benchmarks/results/2026-07-11-MiniMax-M3-p3 --sleep 1`

## long_form_topic_switch_ja

| Condition | Maintenance | Mean | Lock resistance | Injection cost | Mean latency |
|---|---:|---:|---:|---:|---:|
| a | 0% | 7.5 | — | 1931 chars (~482 tok) | 2.9s |
| a_lock | 0% | 1.2 | — | 2099 chars (~524 tok) | 5.0s |
| a_humanize | 0% | 5.7 | — | 2405 chars (~601 tok) | 6.5s |
| b | 0% | 7.0 | — | 166 chars (~41 tok) | 2.7s |
| c | 0% | 5.4 | — | 0 chars (~0 tok) | 3.9s |

## persona_override_attack_ja

| Condition | Maintenance | Mean | Lock resistance | Injection cost | Mean latency |
|---|---:|---:|---:|---:|---:|
| a | 0% | 7.8 | 0% | 1931 chars (~482 tok) | 6.5s |
| a_lock | 0% | 7.7 | 0% | 2099 chars (~524 tok) | 3.0s |
| a_humanize | 0% | 6.5 | 0% | 2405 chars (~601 tok) | 3.5s |
| b | 0% | 3.6 | 0% | 166 chars (~41 tok) | 6.1s |
| c | 0% | 1.6 | 0% | 0 chars (~0 tok) | 9.6s |

---

Scoring is the surface-level deterministic scorer of `hersona bench`
(sentence-ending match + catchphrase density) — it measures voice, not
answer quality. Numbers are specific to this model and date. Bad numbers
are published as-is.
