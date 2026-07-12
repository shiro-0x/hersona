# hersona comparison run

- date: 2026-07-12
- provider / model: minimax / MiniMax-M3
- hersona: v1.9.0
- blend: tsundere + keigo (weight: strong)
- reproduce: `run_comparison.py --provider minimax --model MiniMax-M3 --names tsundere keigo --weight strong --scenarios benchmarks/scenarios/long_form_topic_switch_ja.yaml benchmarks/scenarios/persona_override_attack_ja.yaml --conditions a,a_lock,b,c --baseline-file benchmarks/baselines/tsundere_keigo_ja.md --score --out-dir benchmarks/results/2026-07-12-MiniMax-M3-strong --sleep 1`

## long_form_topic_switch_ja

| Condition | Maintenance | Mean | Lock resistance | Injection cost | Mean latency |
|---|---:|---:|---:|---:|---:|
| a | 17% | 62.7 | — | 2039 chars (~509 tok) | 4.0s |
| a_lock | 50% | 66.0 | — | 2207 chars (~551 tok) | 3.0s |
| b | 8% | 46.9 | — | 166 chars (~41 tok) | 4.1s |
| c | 0% | 1.4 | — | 0 chars (~0 tok) | 3.4s |

## persona_override_attack_ja

| Condition | Maintenance | Mean | Lock resistance | Injection cost | Mean latency |
|---|---:|---:|---:|---:|---:|
| a | 58% | 66.5 | 67% | 2039 chars (~509 tok) | 4.6s |
| a_lock | 92% | 86.1 | 100% | 2207 chars (~551 tok) | 3.0s |
| b | 8% | 55.4 | 0% | 166 chars (~41 tok) | 3.8s |
| c | 0% | 10.8 | 0% | 0 chars (~0 tok) | 6.6s |

---

Scoring is the surface-level deterministic scorer of `hersona bench`
(sentence-ending match + catchphrase density) — it measures voice, not
answer quality. Numbers are specific to this model and date. Bad numbers
are published as-is.
