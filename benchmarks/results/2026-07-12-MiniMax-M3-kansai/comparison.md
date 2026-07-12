# hersona comparison run

- date: 2026-07-12
- provider / model: minimax / MiniMax-M3
- hersona: v1.9.0
- blend: tsundere + kansai_ben (weight: moderate)
- reproduce: `run_comparison.py --provider minimax --model MiniMax-M3 --names tsundere kansai_ben --weight moderate --scenarios benchmarks/scenarios/long_form_topic_switch_ja.yaml benchmarks/scenarios/persona_override_attack_ja.yaml --conditions a,a_lock,c --score --out-dir benchmarks/results/2026-07-12-MiniMax-M3-kansai --sleep 1`

## long_form_topic_switch_ja

| Condition | Maintenance | Mean | Lock resistance | Injection cost | Mean latency |
|---|---:|---:|---:|---:|---:|
| a | 8% | 33.5 | — | 1910 chars (~477 tok) | 1.6s |
| a_lock | 0% | 21.1 | — | 2078 chars (~519 tok) | 3.6s |
| c | 0% | 0.5 | — | 0 chars (~0 tok) | 3.6s |

## persona_override_attack_ja

| Condition | Maintenance | Mean | Lock resistance | Injection cost | Mean latency |
|---|---:|---:|---:|---:|---:|
| a | 33% | 39.2 | 50% | 1910 chars (~477 tok) | 3.0s |
| a_lock | 42% | 43.3 | 33% | 2078 chars (~519 tok) | 3.6s |
| c | 0% | 2.8 | 0% | 0 chars (~0 tok) | 7.0s |

---

Scoring is the surface-level deterministic scorer of `hersona bench`
(sentence-ending match + catchphrase density) — it measures voice, not
answer quality. Numbers are specific to this model and date. Bad numbers
are published as-is.
