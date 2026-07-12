# hersona comparison run

- date: 2026-07-12
- rescored: 2026-07-12 (hersona v1.9.0 metric)
- provider / model: minimax / MiniMax-M3
- hersona: v1.9.0
- blend: tsundere + keigo (weight: moderate)
- reproduce: `run_comparison.py --rescore benchmarks/results/2026-07-11-MiniMax-M3-p3 --names tsundere keigo --weight moderate --scenarios benchmarks/scenarios/long_form_topic_switch_ja.yaml benchmarks/scenarios/persona_override_attack_ja.yaml --conditions a,a_lock,a_humanize,b,c --baseline-file benchmarks/baselines/tsundere_keigo_ja.md`

## long_form_topic_switch_ja

| Condition | Maintenance | Mean | Lock resistance | Injection cost | Mean latency |
|---|---:|---:|---:|---:|---:|
| a | 75% | 53.4 | — | 1931 chars (~482 tok) | 2.9s |
| a_lock | 33% | 49.9 | — | 2099 chars (~524 tok) | 5.0s |
| a_humanize | 58% | 47.1 | — | 2405 chars (~601 tok) | 6.5s |
| b | 67% | 55.8 | — | 166 chars (~41 tok) | 2.7s |
| c | 0% | 15.3 | — | 0 chars (~0 tok) | 3.9s |

## persona_override_attack_ja

| Condition | Maintenance | Mean | Lock resistance | Injection cost | Mean latency |
|---|---:|---:|---:|---:|---:|
| a | 42% | 59.7 | 33% | 1931 chars (~482 tok) | 6.5s |
| a_lock | 50% | 71.4 | 0% | 2099 chars (~524 tok) | 3.0s |
| a_humanize | 42% | 69.7 | 33% | 2405 chars (~601 tok) | 3.5s |
| b | 58% | 49.4 | 50% | 166 chars (~41 tok) | 6.1s |
| c | 0% | 6.7 | 0% | 0 chars (~0 tok) | 9.6s |

---

Scoring is the surface-level deterministic scorer of `hersona bench`
(sentence-ending match + catchphrase density) — it measures voice, not
answer quality. Numbers are specific to this model and date. Bad numbers
are published as-is.
