# hersona comparison run

- date: 2026-07-12
- provider / model: minimax / MiniMax-M3
- hersona: v1.9.0
- blend: tsundere + keigo (weight: moderate)
- reproduce: `run_comparison.py --provider minimax --model MiniMax-M3 --names tsundere keigo --weight moderate --scenarios benchmarks/scenarios/long_form_topic_switch_ja.yaml benchmarks/scenarios/persona_override_attack_ja.yaml --conditions a,a_lock,b,c --baseline-file benchmarks/baselines/tsundere_keigo_ja.md --score --out-dir benchmarks/results/2026-07-12-MiniMax-M3-repeat --sleep 1`

## long_form_topic_switch_ja

| Condition | Maintenance | Mean | Lock resistance | Injection cost | Mean latency |
|---|---:|---:|---:|---:|---:|
| a | 75% | 65.0 | — | 1931 chars (~482 tok) | 4.6s |
| a_lock | 58% | 66.9 | — | 2099 chars (~524 tok) | 3.9s |
| b | 17% | 42.1 | — | 166 chars (~41 tok) | 3.2s |
| c | 0% | 1.9 | — | 0 chars (~0 tok) | 2.5s |

## persona_override_attack_ja

| Condition | Maintenance | Mean | Lock resistance | Injection cost | Mean latency |
|---|---:|---:|---:|---:|---:|
| a | 50% | 65.4 | 33% | 1931 chars (~482 tok) | 2.8s |
| a_lock | 42% | 66.3 | 50% | 2099 chars (~524 tok) | 7.9s |
| b | 67% | 46.4 | 67% | 166 chars (~41 tok) | 3.6s |
| c | 0% | 4.6 | 0% | 0 chars (~0 tok) | 6.3s |

---

Scoring is the surface-level deterministic scorer of `hersona bench`
(sentence-ending match + catchphrase density) — it measures voice, not
answer quality. Numbers are specific to this model and date. Bad numbers
are published as-is.
