# Benchmark scenarios

Conversation scenarios for `hersona bench` (see [`docs/BENCHMARKS.md`](../../docs/BENCHMARKS.md)).

Each YAML defines **user-turn prompts only** — no responses. To run a
comparison, generate a transcript of assistant responses to these prompts
(with your own model, with and without a hersona blend injected) and score
each transcript with `hersona bench <names...> --transcript <file>
--scenario <this file>`.

| Scenario | Turns | Language | What it probes |
|---|---:|---|---|
| `casual_greeting_ja.yaml` | 8 | ja | Baseline small talk |
| `casual_greeting_en.yaml` | 8 | en | Baseline small talk |
| `long_form_topic_switch_ja.yaml` | 12 | ja | Persona maintenance over a longer, tonally varied conversation (decay curve) |
| `long_form_topic_switch_en.yaml` | 12 | en | Same, in English |
| `roleplay_scene_ja.yaml` | 8 | ja | Persona maintenance through an emotional beat (conflict → reconciliation) |
| `technical_distraction_en.yaml` | 8 | en | Whether persona voice survives a run of flat, off-character factual questions |

Licensed **CC0 1.0** (public domain dedication), same as `attributes/**/*.yaml`
— see [`../../LICENSE-CC0.txt`](../../LICENSE-CC0.txt). Use them freely,
including outside hersona.
