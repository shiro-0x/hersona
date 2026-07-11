# hersona comparison run

- date: 2026-07-11
- provider / model: minimax / MiniMax-M3
- hersona: v1.7.0
- blend: tsundere + keigo (weight: moderate)
- reproduce: `run_comparison.py --provider minimax --model MiniMax-M3 --names tsundere keigo --weight moderate --scenarios benchmarks/scenarios/long_form_topic_switch_ja.yaml benchmarks/scenarios/persona_override_attack_ja.yaml --conditions a,a_lock,b,c --baseline-file benchmarks/baselines/tsundere_keigo_ja.md --score --out-dir benchmarks/results/2026-07-11-MiniMax-M3 --sleep 1`

## long_form_topic_switch_ja

| Condition | Maintenance | Mean | Lock resistance | Injection cost | Mean latency |
|---|---:|---:|---:|---:|---:|
| a | 0% | 6.6 | — | 1931 chars (~482 tok) | 3.1s |
| a_lock | 0% | 12.4 | — | 2099 chars (~524 tok) | 2.8s |
| b | 0% | 4.1 | — | 166 chars (~41 tok) | 5.1s |
| c | 0% | 7.8 | — | 0 chars (~0 tok) | 3.5s |

## persona_override_attack_ja

| Condition | Maintenance | Mean | Lock resistance | Injection cost | Mean latency |
|---|---:|---:|---:|---:|---:|
| a | 0% | 8.6 | 0% | 1931 chars (~482 tok) | 4.5s |
| a_lock | 0% | 9.8 | 0% | 2099 chars (~524 tok) | 3.5s |
| b | 0% | 8.0 | 0% | 166 chars (~41 tok) | 3.9s |
| c | 0% | 2.4 | 0% | 0 chars (~0 tok) | 6.6s |

---

Scoring is the surface-level deterministic scorer of `hersona bench`
(sentence-ending match + catchphrase density) — it measures voice, not
answer quality. Numbers are specific to this model and date. Bad numbers
are published as-is.
