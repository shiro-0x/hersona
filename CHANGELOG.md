# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> **注 (semver ロールバック履歴)**: 2026-06-17 に v1.3.0 → v0.2.0 → v1.4.0 という
> semver 後退を含む連続リリースが発生した（ユーザー指示）。PyPI には 0.2.0 がそのまま
> 残っているが、これはロールバック履歴の記録として保持。`pip install hersona` は
> 1.4.0 を解決する。機能セットは [1.3.0] と同じ。

## [Unreleased]

### Added

- `USED_BY.md`: [amygdala](https://github.com/shiro-0x/amygdala) を追加 — hersona の injection block の直後に感情・関係の `state_block` を並置する姉妹プロジェクト（性格 = hersona / 感情 = amygdala）。並置してもペルソナ維持が劣化しないことを `hersona.core.bench` の採点で検証済み（amygdala 側 `docs/INTEGRATION.md`、`--provider claude_cli` 利用）。
- `docs/REFERENCE.md` / `docs/REFERENCE.en.md`: 「amygdala で感情を足す（並置レシピ）」節を追加。hersona injection block + amygdala state block の並置手順・順序の根拠・検証結果へのリンク。レシピは amygdala の `compose_system_prompt` ヘルパー（アプリ側コードで並置）を使用し、**この連携で `/hersona` skill の毎ターン token コストは増えない**ことを明記（並置は LLM の外で行われ、SKILL.md に連携ロジックは入らない）。

- **`benchmarks/run_comparison.py --provider claude_cli`: run official comparisons without an API key.** Drives the `claude` CLI (Claude Code) headless via subprocess, so a `claude login` subscription session is the credential — each turn runs as `claude -p --output-format json` with `--system-prompt` set to the condition's injection block (explicitly empty for condition `c`, so the Claude Code default system prompt never contaminates the measurement) and `--resume <session-id>` threading multi-turn state; the subprocess cwd is pinned to the system temp dir so the repo's `CLAUDE.md` is not loaded as project memory. Honest caveats are stamped into `comparison.md` as a note line and documented in `docs/BENCHMARKS.md` ("Running without an API key"): the CLI harness ≠ raw API (tool definitions present; `--max-turns 1` suppresses agentic loops and a tool-call turn scores as an empty reply, published as-is), latencies include CLI startup, `--max-tokens` is ignored, and `claude_cli` rows must not be compared 1:1 against raw-API rows. `CLAUDE_CLI_BIN` overrides the binary path. Script stays stdlib-only (subprocess) and outside the wheel — `hersona` itself still never calls an LLM. Tests: 9 new offline cases in `tests/test_run_comparison.py` (argv builder incl. empty-system and bin override, JSON parse + error result, session threading across turns, new-conversation reset, dry-run without binary/key, missing-binary exit 2, CLI note in markdown).

### Changed

- README EN/JA "Measured, not vibes": replaced the stale metric-v1 first-run summary (mean 9.8 vs 8.6 vs 8.0 vs 2.4 — superseded by metric v2) with the strong-weight attack-scenario table (a_lock 92% / 86.1 / 100% lock resistance vs hand-written 8% / 0%) plus the honest caveats (single model/scenario pair, moderate-weight competitiveness of hand-written prompts, ±20-40pt single-run variance).
- **README simplification (EN/JA)**: `README.md` / `README.ja.md` trimmed from ~670 lines to a
  front page (~180 lines) — hero + demo, quick start, the "Measured, not vibes" benefit table
  (condensed), `persistent --target` table, what's inside, Hermes skill install + basic commands,
  MCP server summary, a "Beyond blending" overview, data-format pointer, license, contributing.
  All detailed reference material moved to the new `docs/REFERENCE.en.md` / `docs/REFERENCE.md`:
  when-to-use table, full CLI walkthrough (incl. per-attribute `:<level>` weights, `--compact`,
  `--target`, `update` / presets / user-namespace details), Hermes skill command recipes,
  use cases (20), persona packs (14), OpenAI Assistants / LangChain export details, the MCP tool
  table, guides, the full attribute catalog table, schema field reference, legacy generator notes,
  and catalog history. Fixed stale category counts in the moved data-format tree
  (archetype/visual/hobby now match `tests/catalog_counts.py`).
- `scripts/check_readme_counts.py` now also checks `docs/REFERENCE.en.md` / `docs/REFERENCE.md`
  (the new home of the attribute catalog table) for total/category count drift, in addition to
  both READMEs. `CLAUDE.md` / `CONTRIBUTING.md` updated accordingly, plus a "keep the READMEs
  short" authoring rule.
- **Dialect speech attributes: kansai_ben-level catchphrase reinforcement across all 41 remaining dialect YAMLs** (`attributes/speech/*_ben.yaml` + `mixed_dialect.yaml`; kansai_ben itself unchanged). Applies the same supplement pattern kansai_ben received in PR #124: each dialect now has **10 catchphrases** (was 5-6) ordered iconic-first (MILD/MODERATE take a head-ratio subset via `catchphrase_subset`), with 1-2 full natural utterances at the head (kansai_ben's 「なんでやねん、それ……嘘やろ」 pattern) instead of bare morphemes. Also replaces content defects the rewrite surfaced: the Mikawa-dialect filler 「やってみりん」 pasted into 15 non-Aichi dialect files, cross-dialect contamination (「ぶぶ漬け」 in sanuki/niigata, 「ずら」-isms in akita, 「じゃっど」 in kumamoto, 90s slang 「チョベリグ」 in tokyo_ben, the TV-show name 「どさんこワイドっしょ」 in hokkaido_ben), and ending-only pseudo-catchphrases (「が」「び」「たい」「りん」「けー」). Native-speaker review welcome — these are widely-attested textbook dialect phrases, not native authoring.

### Fixed

- **`first_person` missing/broken on 3 dialect attributes** — the ja intensity metric weights the first-person axis at 25% (endings+fp path), so a missing field silently drops the axis: `kyoto_ben` (now うち, matching its own `speech_style` which already said 一人称「うち」) and `mixed_dialect` (now 俺 / 僕 / 私, matching its `speech_style`'s 「俺 / 僕 / 私 (揺れる)」) had no `first_person` at all; `okinawa_ben` carried the corrupted value `わん / ゆい / bie` (romaji junk token, also fixed inside its `speech_style` line) — now わん / わたし.

## [1.9.0] - 2026-07-12

### Added

- **3 follow-up official comparison runs** (2026-07-12, MiniMax-M3, metric v2; transcripts under `benchmarks/results/2026-07-12-MiniMax-M3-{strong,kansai,repeat}/`, write-up in `docs/BENCHMARKS.md` "Follow-up runs"): (1) `tsundere+keigo` at **weight strong** — the moderate-run "hand-written 41-token baseline is competitive" finding does not survive an intensity change: `b` collapses to 8% maintenance / 0% lock resistance while `a_lock` hits 92% / 86.1 mean / **100% lock resistance** on the attack scenario; (2) `tsundere+kansai_ben` — no-persona `c` drops to 0.5-2.8 mean (vs 11-27 on keigo blends), confirming keigo's overlap with default polite Japanese; the model also holds the Kansai register less well (a mean 33.5-39.2), i.e. distinctive registers discriminate better and are harder to maintain; (3) a same-config **repeat run** — 12-turn maintenance rates swing ±20-40 points between identical runs (`b` long_form 42%→67%→17%), so single-run maintenance rankings are noise; the stable facts across all 3 runs are `c` last everywhere and hersona mean scores above `b` in 5 of 6 scenario-runs.

### Fixed

- **Intensity metric v2: the scorer could not see persona maintenance that was actually happening** (`hersona.core.intensity.measure_intensity`; affects `hersona measure`, `hersona bench`, MCP `measure_intensity` / `bench_transcript`, and `benchmarks/run_comparison.py`). The official comparison runs published in v1.9.0 showed **0% maintenance and 0% lock resistance for every condition — including `c` (no persona)** — which root-caused to four measurement defects, not model behavior: (1) ending match was literal `endswith` only, so perfectly polite keigo with conjugation (ました/ません) or sentence-final particles (「ございませんわ」「できませんの」「ですけれど」) never matched the registered です/ます endings — v2 adds deterministic polite-conjugation expansion (ます→ました/ません/ましょう/まして/ませ, です→でした/でしょう) plus a bounded particle/conjunction tail-strip (ね/よ/わ/の…, けれど/ので/から…); (2) only speech-attribute catchphrases were counted, so a response quoting tsundere's 「誰が気にするものかしら」 verbatim scored 0 — v2 counts catchphrases from **all** attribute categories (skip conditions unchanged: a blend with no speech attribute is still unmeasurable), and normalizes stored ellipsis/punctuation so 「べ、別に……」 matches 「べ、別に見てたわけじゃないし」; (3) `first_person: 私（わたくし）` was matched as one literal token, reading parenthesis included, so 「私」 never hit — v2 splits paren readings into separate tokens (私 / わたくし); (4) catchphrase-density and first-person axes required one hit **per sentence** for full credit — a cadence the injected `response_style_directive` itself explicitly forbids ("vary, don't parrot") — v2 saturates both axes at one hit per 4 sentences (`_HIT_CADENCE = 0.25`; also applied to the en/zh/ko density path). **v2 scores are not comparable to v1 numbers** (v1 pinned real LLM output to ~0-15/100, structurally below every band; band definitions themselves are unchanged). Both published official runs were re-scored from their frozen transcripts: conditions now separate cleanly (e.g. P3 attack scenario: `a_lock` mean 71.4 > `a` 59.7 > `b` 49.4 > `c` 6.7; maintenance 0-8% for `c` vs 33-75% for persona conditions) — `docs/BENCHMARKS.md` tables, honest readings, and the demo example all updated, with a new "Scoring metric v2" section documenting all four defects. `docs/PUBLIC_API.md` / `.en.md` one-liners updated. New tests: 10 in `tests/test_intensity.py` (particle/conjugation matching, negative no-new-match guard, all-category catchphrases, ellipsis normalization, paren first-person, cadence saturation, skip-unchanged, and a reproduction of the real 0-scored a_lock turn now scoring ≥ 45).
- **`benchmarks/run_comparison.py --rescore DIR`**: re-score existing `<scenario>__<condition>.json` transcripts without any LLM call and regenerate `comparison.md` / `comparison.json` in place — the metric-change path above is exactly what this exists for. Carries over provider/model/run-date and per-condition `mean_latency_s` from the old `comparison.json` (latency doesn't change on re-scoring) and stamps a `rescored: <date>` line into both reports. `--provider` / `--model` are now required only when actually calling a model. Tests: 3 new offline cases in `tests/test_run_comparison.py`.


### Added

- **`--compact` injection profile** (sharpen-and-grow A-4, part 1): a shorter, meaning-preserving rewrite of the fixed `response_style_directive` (same four constraints — no self-narration, catchphrases/endings as a repertoire, blend-adaptation, vary-across-replies — about half the characters). Opt-in via `--compact` on `blend`, `export` (all 5 formats), `bench --cost-only`, and `hersona persistent` (Hermes path — shrinks the `config.yaml` `agent.personalities.<name>` block). Measured reduction: -14% to -19% across 4 blends × 3 weights (full table in `docs/BENCHMARKS.md`). Deliberately **not** added to `hersona soul` or `persistent --target {claude,codex,cursor,gemini}` — those bodies are assembled from attribute fields (`rules`/`notes`/`core_traits`), not `render_blend(...).prompt`, so the directive was never part of that output and the flag would be a silent no-op; the CLI instead prints a warning (`persistent.target_compact_no_effect`) when `--compact` is combined with `--target`. Persona-maintenance rate under `--compact` has **not yet been measured** — treat it as an unverified cost cut, not a default-safe one, until run through `benchmarks/run_comparison.py`. `hersona.core.attach.render_blend`/`response_style_directive`, `export_blend` and both `export_for_*` helpers, and `hersona.core.bench.estimate_token_cost` gain a `compact: bool = False` keyword (backward-compatible minor addition). 12 new tests across `tests/test_attach.py`, `tests/test_export.py`, `tests/test_persistent.py`, `tests/test_cli.py`.
- **`docs/IMPROVEMENT_PLAN_2026-07-11_humanize.md`**: plan for suppressing and *measuring* AI-sounding text (owner request 2026-07-11; promoted from the ROADMAP_V2 backlog's Tone-Analyzer family). Built on the premise that **checklist-style prompts alone are insufficient** (models can't detect their own AI-scent and re-land on the same patterns), the plan is structured as three pillars mapped onto existing hersona machinery: P1 deterministic `naturalness` score (new `hersona.core.naturalness`; a 4-group catalog of stock phrases / syntax-rhythm tics with concrete regex thresholds (negation-contrast ≥3, triple-rhythm, question-chains, "という" density…) / translationese proxies (100-char sentences, 7+ kanji runs, 4+ commas) / conversation-specific habits, surfaced via `measure --naturalness`, `bench --naturalness`, and the MCP self-scoring tools), P2a opt-in `--humanize` directive folded into `response_style_directive` (prohibitions **plus** deliberate bias — uneven conviction/weight, stance disclosure, odd specificity, grounded in the persona's core_traits), P2b a naturalness self-check prompt ("a human just called this reply AI-sounding — re-read it") extending `pre_response_check_prompt`, and P3 before/after + cross-model measurement on the `run_comparison.py` harness (condition `a_humanize`) before any default-on decision. Honest limits documented: thresholds are long-form-calibrated placeholders needing chat-length recalibration, English-syntax residue (inanimate subjects, passive/pronoun overuse) is out of P1's deterministic reach, and the directive-vocabulary/detector overlap (self-contamination) is reported in a separate column. Explicitly out of scope: LLM-judge scoring, perplexity/AI-detector-based metrics, and any AI-detector-evasion framing. Linked from `ROADMAP_V2.md` §6/改訂履歴.
- **MCP: 4 new tools** (sharpen-and-grow B-2 后半): `measure_intensity` (score one response against a blend's expected intensity band — same deterministic scorer as `hersona measure`, no LLM), `bench_transcript` (score a whole conversation transcript for maintenance rate + lock resistance rate — wraps `hersona.core.bench.score_transcript`), `list_personas` (browse the 14 bundled persona packs), `install_persona` (preview a pack's rendered injection block — **dry-run only, writes nothing**; actual installation still requires the CLI's `hersona personas install <name>`, a deliberate safety choice since MCP calls can come from any connected agent). Closes the gap where the 6 prior MCP tools were read-only and an agent couldn't self-score its own persona-maintenance loop. `hersona/mcp/server.py` and `hersona/mcp/tools.py` updated; 9 new tests in `tests/test_mcp.py`; README EN/JA MCP section gains the full tool table.
- **`hersona bench`: lock resistance rate** (v2 Phase 1 / sharpen-and-grow A-1). Scenario turns can now be a `{text: ..., attack: true}` mapping; `BenchScenario.attack_turns` carries the 0-based indices, `score_transcript(..., attack_turns=...)` computes `BenchResult.lock_resistance_rate` (fraction of attack-marked turns whose response stayed in the expected band — same `pass` criterion as the maintenance rate, restricted to the attack subset). CLI prints a `Lock resistance rate:` line (JSON: `lock_resistance_rate` / `attack_turns` / per-turn `attack` flag) when `--transcript` is scored with an attack scenario via `--scenario`; `--demo` ignores attack markers (demo transcripts aren't turn-aligned). A transcript/scenario turn-count mismatch now warns on stderr.
- **4 persona-override attack scenarios** (CC0): `persona_override_attack_{ja,en}` (12 turns, 6 attacks; social pressure) and `persona_jailbreak_{ja,en}` (10 turns, 6 attacks; authority spoofing / fake-system). `benchmarks/scenarios/README.md` documents the attack-marker YAML form.
- **`benchmarks/run_comparison.py`** (sharpen-and-grow A-2, the provider path left open by `reviews/2026-07-04` P1-1): stdlib-only script (outside the package/wheel — hersona itself still never calls an LLM) that runs each scenario against anthropic / openai / gemini / ollama / **minimax** under conditions `a` (hersona blend) / `a_lock` (blend + persona_lock) / `b` (hand-written baseline) / `c` (no persona), saves bench-compatible transcripts, and with `--score` writes a dated, reproducible `comparison.md` / `comparison.json`. The `minimax` provider hits `https://api.minimax.io/v1/chat/completions` (OpenAI-compatible, `Bearer ${MINIMAX_API_KEY}`) and strips `<think>...</think>` reasoning blocks before scoring so the surface proxy sees only user-facing replies; `MINIMAX_MODEL` overrides `--model` (default `MiniMax-M2`). `docs/BENCHMARKS.md` gains "Lock resistance rate" and "Official comparison runs" sections with the first official run published below. Offline tests in `tests/test_run_comparison.py`.
- **`docs/BENCHMARKS.md`**: first official comparison run filled in. 2026-07-11, minimax/MiniMax-M3, tsundere+keigo moderate, 2 scenarios × 4 conditions × 12 turns = 96 calls. Numbers published as-is (bad numbers included): `a_lock` shows a small but consistent `mean_score` lift over `a` (12.4 vs 6.6 long_form; 9.8 vs 8.6 attack) but `maintenance = 0%` and `lock_resistance_rate = 0%` across the board, with an "Honest reading" subsection explaining why that does not mean the lock doesn't work. Reproduce command pinned; the `HERSONA_DATA_DIR=/tmp/empty-dir` override is documented to avoid the `~/.hermes/data/attributes/` cache shadowing the repo attributes.
- **`benchmarks/baselines/tsundere_keigo_ja.md`**: hand-written persona prompt used as condition `b` in the official run.
- **`docs/ROADMAP_V2.md`**: the v2.0 roadmap & OSS growth strategy (North Star = Weekly Persona Exports observed via external proxies — no telemetry; benchmark-first moat; mission copy "Build once. Keep personality everywhere."), reconciled against repo reality in §0 (export targets & bench already shipped; embedding-based cross-model drift deferred by policy). Linked from `ROADMAP.md`.
- **`docs/OWNER_ACTIONS.md`**: owner-manual checklist for B-1 (GitHub About/topics/Discussions/social preview) and B-2 (MCP registry submissions) with ready-to-paste metadata.
- **README EN/JA hero refresh** (v2 Phase 1): "Build once. Keep personality everywhere." tagline, embedded demo GIF (`docs/hersona-demo.gif`, generated from the existing mp4), a 30-second copy-paste quick start, a "Measured, not vibes" section with the real injection-cost table, and a `persistent --target` table surfacing the CLAUDE.md / AGENTS.md / .cursorrules / GEMINI.md writers (shipped in v1.4.0 but previously undocumented in the README).
- **`USED_BY.md`**: adoption-showcase scaffold (`reviews/2026-07-04` P3-2 / sharpen-and-grow B-5), linked from the Contributing section of both READMEs.
- **`hersona measure` / `bench` now score zh / ko content** (sharpen-and-grow A-3): `hersona.core.intensity` routes `content_lang: zh` and `content_lang: ko` speech attributes through the same `lexical_markers`-based scoring path already used for `en` (`100 * (0.6*endings_rate + 0.4*density)`) — the 6 native zh/ko speech attributes (`mandarin_casual`, `keigo_zh`, `taiwan_mandarin`, `banmal`, `jondaetmal`, `seoul_casual`) already carry `lexical_markers` from authoring, so no schema backfill was needed. `skip_reason`'s language-mismatch check gained zh/ko branches: zh flags mismatch on hiragana/katakana or hangul intrusion (`_has_kana` / `_has_hangul`, new helpers), ko flags mismatch on the *absence* of hangul — documented caveat: CJK ideographs are a Unicode block shared between zh and ja, so a pure-kanji/hanzi string can't be definitively told apart by character range alone; the zh check therefore only catches intrusion from the two languages that *are* unambiguously detectable (kana, hangul). `bench` / `measure`'s supported content languages go from 2 (ja/en) to 4. Tests: 8 new cases in `tests/test_intensity.py` (4 zh + 4 ko, mirroring the existing `en` coverage).
- **Prompt-cache-optimal SOUL.md layout** (sharpen-and-grow A-4 part 2): `hersona.core.soul.render_soul` (shared by `hersona soul` and `persistent --target {claude,codex,cursor,gemini}`) previously placed a `<!-- generated by hersona vX at <timestamp> -->` metadata block **first**, before the actual persona content — since prompt caches (Anthropic/OpenAI) match a growing prefix, any content that changes between regenerations breaks caching for the *entire* prompt if it sits at the front. Two `render_soul()` calls with identical attributes/weight one second apart had a 0-byte common prefix before this fix. Reordered to stable-prefix-first: attribute body (Name/Personality/Tone/Behavioral Guidelines/persona_lock) → `use_case` block (deterministic, so it stays in the stable prefix) → variable tail (`--memory`'s Recent Context, the generation-timestamp footer, then the metadata comments). Measured: 88% common prefix across two regenerations 1.1s apart (92% with `--use-case`), up from 0%. `render_blend(...).prompt` (used by `blend`/`export`/`persistent`'s Hermes-path config.yaml block) already had no variable content baked in and needed no change. New `docs/BENCHMARKS.md` "Cache-optimal layout" section documents the before/after measurement and explicitly scopes what it does *not* measure (actual provider-side cache-hit economics). Tests: 2 new in `tests/test_soul.py` asserting the common-prefix ratio directly; 4 existing SOUL.md determinism assertions (`content.startswith("<!-- generated...")`) updated to substring checks since the metadata now lives at the tail.
- **`--style-examples N` few-shot tone-anchor injection** (sharpen-and-grow A-6, user-proposed 2026-07-10): opt-in flag on `blend` / `export` (all 5 formats) / `persistent` (Hermes path) that injects up to N lines from the blend's attributes' existing `examples` field as a `## Style examples (tone reference — never reuse these lines verbatim)` section, in `speech > personality > archetype > visual > hobby` priority order (mirrors `sample_dialogue.py`'s existing category logic). No new content dictionary was needed — all 346 attributes already carry schema-required `examples` — but authoring turned out to be **heterogeneous** across the catalog: most attributes (all 43 personality, most speech/archetype/hobby) use a multi-turn `# N) weight demo` + `[user]`/`[assistant]` dialogue-block format rather than the plain single-line format the original plan assumed (e.g. `kansai_ben`, `casual_en`). A new `_extract_example_lines()` in `hersona.core.attach` absorbs both: plain lines are used as-is, dialogue blocks are reduced to their `[assistant]` line only (dropping the `[user]` prompt and the `# N) ...` comment). Content-language resolution reuses the existing `resolve_content_field` (`content_i18n.<lang>` when present, BASE when it matches, otherwise dropped — same "non-native excluded" rule as catchphrases/core_traits). Anti-parroting guidance is folded into the existing `response_style_directive` rather than adding a new directive (per CLAUDE.md's anti-token-bloat rule), gated on `has_style_examples`. Off by default; deliberately **not** added to `hersona soul` or `persistent --target` for the same reason `--compact`/`--humanize` aren't (those bodies never go through `render_blend(...).prompt`) — `soul` doesn't register the flag, `persistent --target` warns instead. Estimated cost +45-60 tok/attribute per the plan; before/after maintenance-rate measurement via `run_comparison.py` is left as a follow-up (plan §A-6 risk 3: examples share vocabulary with the scored catchphrases/endings, so any effect must be reported in a separate BENCHMARKS.md column, not blended with the unmodified baseline). Tests: 9 new in `TestStyleExamples` (`tests/test_attach.py`), 4 in `tests/test_export.py`, 2 in `tests/test_persistent.py`, 3 in `tests/test_cli.py`.
- **Per-attribute weight dial** (sharpen-and-grow A-5, stage 1): `render_blend(names, weight=..., weights: dict[str, str | WeightLevel] | None = None)` lets each attribute in a blend carry its own intensity, closing the asymmetry between the README's documented Hermes-skill syntax (`/hersona personality/tsundere strong speech/keigo mild`) and the core, which previously only accepted one weight for the whole blend. `weights` keys accept both bare (`tsundere`) and qualified (`personality/tsundere`) names, normalized internally; attributes omitted from `weights` fall back to the blend-wide `weight`. `weights=None` (the default) is **byte-for-byte identical** to prior behavior — verified directly in tests, not assumed — because per-attribute catchphrase subsetting (each attribute's own catchphrase pool trimmed at its own effective weight, then merged) can produce a different result than the old single merge-then-subset path even when every attribute resolves to the same level, so the old path is kept as the exact default and the new path only activates when `weights` is actually passed. The `## Intensity` section switches from the single `## Intensity: <level>` line to one `- <category>/<name>: <level> — <guidance>` line per attribute when `weights` is used. Threaded through `export_blend` and both `export_for_*` helpers. CLI: `hersona blend tsundere:strong keigo:mild` / `hersona export tsundere:strong keigo:mild --format ...` accept a `:<level>` suffix per attribute name (`_split_weighted_names`, unknown levels raise a clear error). Tests: 7 new in `TestPerAttributeWeight` (`tests/test_attach.py`), 3 in `tests/test_export.py`, 4 in `tests/test_cli.py`. **Deferred to a follow-up** (per the plan's own staged-rollout note): `measure`/`bench` per-attribute band scoring (a surface-level scorer can't attribute which part of a response came from which attribute) and `soul`/`persistent`'s SOUL.md path (same non-`render_blend(...).prompt` architectural reason `--compact`/`--humanize` don't reach it either).

### Fixed

- **`--humanize` (P2a, shipped in #152) was a silent no-op on `hersona export` / `soul` / `persistent`.** The flag was registered on all three subcommands' argparsers, but only `hersona save`'s handler actually threaded `humanize=` into its `render_blend()` call — `export_blend`, `export_for_openai_assistants`, `export_for_langchain_system_message`, and `run_persistent` had no `humanize` parameter at all, so the flag was silently accepted and silently dropped. Fixed: all four now accept `humanize: bool = False` and thread it through to `render_blend(..., humanize=)`; `_cmd_export` / `_cmd_persistent` pass `humanize=getattr(args, "humanize", False)`. `hersona soul` is a genuine architectural no-op (like `--compact`) since SOUL.md's body is assembled from attribute fields, never from `render_blend(...).prompt` — the flag is removed from `p_soul` with an explanatory comment (matching the existing `--compact` precedent), and `persistent --target {claude,codex,cursor,gemini}` now prints a `persistent.target_humanize_no_effect` warning for the same reason `--compact` already does. New tests: `tests/test_export.py` (4 cases), `tests/test_persistent.py` (2 cases), `tests/test_cli.py` (3 cases, including one asserting `hersona soul --humanize` now fails argparse).
- **`hersona export` and `hersona preview` crashed with `attribute not found: 'personality/persona_lock'`** whenever the default persona lock was active (any export format; regression shipped in v1.8.0). `apply_persona_lock` appends the category-qualified name, which `soul` / `persistent` normalize but `export_blend` and `_cmd_preview` passed through unresolved. `export_blend` / `_cmd_preview` now normalize like `soul` / `persistent`, and `hersona.core.attach.load_attribute` additionally accepts category-qualified names (`personality/tsundere`), so qualified names can't crash core resolution again; `render_blend` runs conflict checks on the unqualified names.
- **`personality/persona_lock.yaml` violated the attribute schema** (shipped in v1.8.0; `scripts/validate.py` and `tests/test_attributes.py` were red on main): the `rules` field — consumed by SOUL generation (`hersona.core.soul._extract_behavior_rules` reads `behavioral_guidelines` / `rules` / `notes`) — was not declared in `schema/attribute.schema.json` (now added as an optional string array), and per-language `description` entries sat in `content_i18n` (persona content) instead of `i18n` (metadata), where they already existed — the duplicates are removed. `checksums.json` regenerated (schema + attribute changed); `docs/app/data.json` verified not stale.
- Stale v1.8.0 test expectations updated: `tests/test_persistent.py` / `tests/test_config_writer.py` persona names now include the default-appended `persona_lock`; `tests/test_export.py` structure/JSON tests expect the appended `persona_lock` and the dispatch-equivalence tests compare with `persona_lock=False` (a new test asserts the default markdown export contains the lock); `tests/test_mcp.py::test_recommend_blend_with_export_format` expects `blend + persona_lock` in export metadata; `tests/test_cli.py` list tests read the personality count from `tests/catalog_counts.py` instead of a hard-coded pre-v1.8.0 `42`.

### Changed

- `pyproject.toml` keywords extended for registry/search reach (`mcp`, `mcp-server`, `character-card`, `chatbot`, `aituber`, `langchain`, `prompt-engineering`, `personality`) — sharpen-and-grow B-5.

### Added — humanize plan (P1)

- **`hersona measure --naturalness` and `hersona bench --naturalness`** (P1 of `docs/IMPROVEMENT_PLAN_2026-07-11_humanize.md`). New module `hersona/core/naturalness.py` with `measure_naturalness(text, *, lang="ja") -> NaturalnessReport` (0-100 score, 100 = natural; per-catalog hits/penalties for §2.A-D of the humanize plan). `bench` adds a per-turn `naturalness_score` field and a `naturalness_mean` summary when `--naturalness` is passed. CLI prints `Naturalness score:` / `Naturalness mean:` lines. Off by default (matches the surface-proxy convention — only requested, never auto-attached). i18n keys (`help.measure_naturalness`, `help.bench_naturalness`, `bench.naturalness_mean`) in both en and ja. Tests: `tests/test_naturalness.py` (34 cases) and `tests/test_naturalness_bench.py` (5 cases). Honest caveat captured in the plan §4: this is a surface proxy for AI-flavor symptoms, not "human-ness" itself; thresholds are placeholders and will be re-calibrated against real persona conversation transcripts in P3.

### Added — humanize plan (P2a)

- **`--humanize` directive (opt-in) on `hersona save` and `hersona export` / `soul` / `persistent` (P2a of `docs/IMPROVEMENT_PLAN_2026-07-11_humanize.md`). `hersona.core.attach.response_style_directive(..., humanize=False)` extends the existing "Note on response style:" with a two-part humanize section: **Strip** (drop boilerplate / question-restating / disclaimers / bullets / uniform hedge / cold openings per §2.A/B/D) + **Vary** (spend more on what this persona cares about, drop in a single concrete real-world specific, one short stance line — keep asymmetry grounded in core_traits, no fabrication). Injected at +60-90 tok/turn per the plan; measured ~118 tok on the tsundere+keigo ja blend. Off by default; profile axis: `compact ↔ standard ↔ humanize`. i18n: en + ja `help.humanize` (used in CLI --help). Tests: 7 new cases in `TestHumanizeDirective` covering default-off, ja/en sections, unsupported-lang noop, full `render_blend(..., humanize=)` integration, char-count guard, and backward-compat (humanize omitted = humanize=False). Scope discipline: humanize text is generated inside the existing `response_style_directive()` (§3 P2a "節を新設しない" — anti-token-bloat rule).

### Added — humanize plan (P2b)

- **`hersona measure --naturalness` recovery loop**: `pre_response_check_prompt(..., naturalness: bool = False)` (P2b of `docs/IMPROVEMENT_PLAN_2026-07-11_humanize.md`) now appends an "AI-scent self-check" section — framed as "a human just read this reply and said it sounds AI-generated" — with four observation points drawn from the naturalness catalog groups A (stock phrases), B (syntax-rhythm), and D (structural/conversational habits); group C (translationese proxies: sentence length, kanji runs) is deliberately excluded as hard to self-audit without measurement. Wired into both existing `hersona measure` call sites: `--check-prompt --naturalness` (prints the section directly) and `--strict --naturalness` (appends it to the stderr recovery prompt when status is `under`/`over`). Off by default; appended at the very end of the prompt so the prompt-cache prefix is unaffected (same tail-append discipline as A-4/A-6). i18n: `measure.check_prompt_naturalness_header` (en/ja); `help.measure_naturalness` updated to document the dual effect. The intended loop: generate a response → score it with `measure --naturalness` → if below threshold, re-inject the `--naturalness` check prompt → regenerate. Documented in `skills/hersona/REFERENCE.md` (new section + 2 verification-checklist items). Tests: 7 new cases in `tests/test_intensity.py` (unit-level default-off/en/ja/section-ordering, plus CLI-level `--check-prompt`/`--strict` coverage).

### Added — humanize plan (P3)

- **`benchmarks/run_comparison.py` gains a 5th condition, `a_humanize`** (P3 of `docs/IMPROVEMENT_PLAN_2026-07-11_humanize.md`, closing the plan): `CONDITIONS = (a, a_lock, a_humanize, b, c)`; `build_condition_prompts()` renders `a_humanize` via `render_blend(..., humanize=True)` with `persona_lock` deliberately *not* applied, so the humanize effect is measured in isolation from the lock (stacking both is left as future work). Published a 2-scenario × 5-condition × 12-turn run (120 calls, minimax/MiniMax-M3) under `benchmarks/results/2026-07-11-MiniMax-M3-p3/`, plus a post-hoc `--naturalness` re-score of all 10 transcripts under the `-p3-naturalness/` sibling directory. `docs/BENCHMARKS.md` gains a "P3: humanize 実測" section with maintenance/mean/lock/cost and naturalness-mean tables plus an "Honest reading" that calls out the predicted §4-2 self-gaming signal directly in the data: naturalness jumps 85.7→93.7 on the attack scenario when `a_humanize` is added, which tracks the §2.A dictionary overlapping the P2a "Strip" instructions rather than a free-lunch improvement (the +60-90 tok/turn cost is the trade); conversely `a_humanize` scores *below* plain `a` on the long_form scenario (91.4 vs 94.8), surfacing a real tension between P2a's anti-uniformity push and P1's persona-consistency reading that the compact/standard/humanize profile axis will need to reconcile. v2.0 default-on decision deferred to the A-6 cadence, per plan §3 P3.

## [1.8.0] - 2026-07-08

### Added

- **Persona lock (default on)**: attribute `personality/persona_lock`; `soul` / `export` / `persistent` / `preview` append it unless `--no-persona-lock`. SOUL.md includes §4.3 guidelines and `persona_lock` metadata.

### Added

- **Operating Mode / use-case prompt packs: 8 → 20** (PR-A W2, `docs/PERSONA_PACKS_DESIGN.md` §8). 12 new YAMLs under `use_cases/`: `frontend_developer`, `backend_architect`, `devops_engineer`, `security_reviewer`, `tech_writer`, `executive_assistant`, `hr_recruiter`, `tutor`, `creative_writer`, `game_master`, `community_manager`, `streamer_copilot`. All 12 follow the `programmer.yaml` golden-sample structure (role / principles / workflow / grounding_policy / output_contract / quality_gate / safety / tags / i18n.ja); bodies are English for token efficiency; `i18n.ja.display_name` + `description` filled for every file; risk_level reflects regulatory exposure (`devops_engineer` / `security_reviewer` / `hr_recruiter` / `community_manager` = `medium`). §8 originally listed 13 candidates; `sales` was dropped (business category duplicates product_manager / marketing / planner) — all 14 packs in §6 are still achievable with the remaining 12. Across the full 20-file catalog, no identical line appears in 2+ files in any of the six list sections (`tests/test_use_cases.py::test_no_duplicate_section_lines` parametrizes over `principles` / `workflow` / `grounding_policy` / `output_contract` / `quality_gate` / `safety` and asserts zero duplicates — §11 risk directly enforced as a regression test).
- `tests/catalog_counts.py::TOTAL_USE_CASES = 20`: single source of truth for use-case count (mirrors the `TOTAL_PUBLIC_ATTRIBUTES` pattern). `tests/test_use_cases.py` imports from there, so the count lives in exactly one place per §9 T5-2.
- `tests/test_use_cases.py`: new regression tests — `test_use_case_count_meets_minimum`, `test_all_use_case_ids_resolvable`, `test_all_use_cases_pass_schema`, plus the parametrized 6-section `test_no_duplicate_section_lines` above.
- `scripts/validate.py::validate_use_cases()`: schema-validates every `use_cases/*.yaml` in the `=== use_cases/ 検証 ===` section of the full `validate.py` run; errors accumulate into `total_errors` and the exit code. Writes one `✓ use_case: <id> (<file>)` line per file or one `✗` line per failure.
- README EN/JA: "Initial public use cases" section expanded from 8 → 20 with the two-tier "Initial 8 (Phase 1) / Added 12 (PR-A W2, Phase 2)" layout and a cross-link to `docs/PERSONA_PACKS_DESIGN.md` §6–§8.

### Added — PR-B W1 (Persona Pack)

- **`personas/` recipe catalog** (14 bundled packs; CC0 1.0, same as `attributes/`): a persona pack is a **named recipe** that declares `persona_name` / `blend` / `weight` / `use_case`; the injection block is rendered at install time from the named attributes, so attribute updates propagate automatically. Shipped: `keigo_support`, `kansai_marketer`, `tsundere_reviewer`, `kuudere_analyst`, `genki_planner`, `sensei_writer`, `butler_assistant`, `onee_recruiter`, `samurai_devops`, `vtuber_streamer`, `miko_tutor`, `british_pm`, `gyaru_community`, `warawa_gamemaster`. (`gyaru_community` originally called for `genki + gyaru` in design §6 but that pair conflicts in the compatibility matrix, so the Sona-authored pack and `docs/PERSONA_PACKS_DESIGN.md` §6 table both use `sociable + gyaru` — §6 SSOT updated in place per the design's "確定表がこの表と食い違ったら本ドキュメントを更新すること" rule.)
- **`hersona/core/personas.py`** (new module): `PersonaPackError`, `available_personas()` (mirrors `available_use_cases`'s defensive walk), `load_persona()`, `validate_persona(data, *, matrix=None, root=None)` (schema + semantic + conflict + use_case-cross-reference, returns list of error strings — same `authoring.validate_attribute` style), `install_persona(name, *, auto_config=False, apply=False, ..., without_soul=True)` (thin delegate to `run_persistent`).
- **`hersona/core/persistent.py::run_persistent`** gains an optional keyword-only `persona_name: str | None = None` (backward-compatible minor addition). `None` (default) preserves the previous auto-derive behavior; passing an explicit name writes to `agent.personalities.<name>`. Documented in `docs/PUBLIC_API.md` / `docs/PUBLIC_API.en.md`.
- **`hersona/core/paths.py`**: new `personas_root()` and `persona_pack_schema_path()` helpers (mirror of `use_cases_root()`).
- **`schema/persona_pack.schema.json`** (Draft 2020-12): required `persona_name` / `display_name` / `description` / `blend` / `weight`; `blend` items match `^(personality|speech|archetype|visual|hobby)/[a-z][a-z0-9_]*$`; `weight` enum `[none, mild, moderate, strong]`; `additionalProperties: false`; `i18n` same shape as `use_case.schema.json`.
- **`pyproject.toml`**: `force-include` gains `"personas" = "hersona/data/personas"` so the bundled packs ship inside the wheel.
- **`hersona personas {list, show, install, use}` CLI** (subcommand of the existing top-level `hersona`, EN/JA localized; `locales/en.yaml` / `locales/ja.yaml` updated with `help.personas*` + `personas.*` keys). `list` / `show` are non-mutating; `install` defaults to `without_soul=True` (SOUL.md is per-profile, the registry is multi-pack); `--apply` acts only on the last of multiple names (`agent.personality` is a single value); `--auto-config` does the safe config.yaml write; `--dry-run` only prints the block; bulk installs of 5+ names print a config-bloat warning line.
- **`hersona recommend --install-persona NAME`**: a new bridge from the diagnostic quiz result to `install_persona`. Mutual exclusion with `--json` is enforced up front (per Pitfall E). On success, prints the diagnostic outcome and the new registry entry.
- **`tests/test_personas.py`** (new): 12 tests — schema rejection (missing required field, unknown weight, empty blend, blend item without category prefix), semantic rejection (unknown attribute, real conflict pair, unknown use_case), `available_personas` / `load_persona` behavior (empty dir, unknown name, invalid file raises `PersonaPackError`), **the §9 T6 acceptance gate `test_all_shipped_personas_validate_clean`** (every pack under `personas/*.yaml` passes `validate_persona()` with zero errors), and a use-case-lookup reachability smoke. All 12 pass on first CI run with the 14 Sona-authored packs in place.
- **`tests/test_cli.py`** (extended): 10 new tests covering `hersona personas {list, show, install --dry-run, use}` (including the JA-localized help output, the `PersonaPackError` exit, and `hersona personas use` erroring safely when `hermes` is absent), plus 2 tests for `hersona recommend --install-persona` (registration round-trip + `--json` mutex).
- **`scripts/validate.py`**: unchanged in this PR — the new `test_personas.py::test_all_shipped_personas_validate_clean` test is the canonical gate (CI runs pytest, not `validate.py`, for the pack catalog).
- **README EN/JA**: new "Persona packs for Hermes" section under the Operating-Modes block, with the 14-pack table, the 5 CLI lines (`list` / `show` / `install` / `use` / `recommend --install-persona`), the "what sets us apart from generic agent catalogs" comparison table, and a pointer to `tests/test_personas.py::test_all_shipped_personas_validate_clean` as the §6 SSOT. License table gains a `personas/**/*.yaml = CC0 1.0` row.
- **`docs/hermes-agent.md`**: new **方法 D — `hersona personas install`** alongside the existing 方法 A/B/C, with a `recommend --install-persona` one-liner and a cross-link to `docs/PERSONA_PACKS_DESIGN.md` (§3, §6).
- **`docs/PUBLIC_API.md` / `docs/PUBLIC_API.en.md`**: `run_persistent` signature gains the `persona_name=None` keyword and its docstring explains the override semantics + internal use by `install_persona`.
- **`skills/hersona/SKILL.md`**: version `0.8.0` → `0.9.0` (independent SemVer per `CONTRIBUTING.md` §versioning; `v1.7.0` → `v1.7.1` for the package), description keywords extended with `hersona personas install keigo_support` / `出来合いパック入れて`, tags gain `persona-pack` / `recipe-catalog` / `hermes-registry`.
- **`skills/hersona/REFERENCE.md`**: new `v1.7.1 追加 — hersona personas (Persona Pack レシピ集)` section with the full CLI cookbook (`list --json` / `show --lang ja` / `install --dry-run` / `--auto-config` / `--apply` semantics / `use` / `recommend --install-persona`), the 5+-bulk warning, the `without_soul=True` default rationale, and a pointer to the CI gate.
- **`docs/PERSONA_PACKS_DESIGN.md` §6 table**: `gyaru_community` row updated from `genki + gyaru` → `sociable + gyaru` (Sona detected the conflict at authoring time and edited both the pack and the design doc in place — per the §6 SSOT rule).
- **`checksums.json`** is **not** updated in this PR — `gen_checksums.py` covers `attributes/` and `schema/` only by design (`DATA_DIRS` contract), and adding `personas/` to the manifest is explicitly listed as **out of scope** in `PERSONA_PACKS_DESIGN.md` §1 (it would require expanding `DATA_DIRS` and changing the contract, so it goes in a separate PR).

### Changed — PR-B W1

- `hersona/core/persistent.py::run_persistent`: signature widened with a keyword-only `persona_name: str | None = None` (default preserves prior behavior — `PersistentResult.persona_name` continues to be auto-derived from the blend; the new arg lets `install_persona` override it with `agent.personalities.<persona_name>`). Backward-compatible minor addition.

### Changed
- **`checksums.json`** (SHA-256 manifest of `attributes/` + `schema/`, generated by new `scripts/gen_checksums.py`): `hersona update` now fetches this manifest from a second, independent GitHub delivery path (`raw.githubusercontent.com`, distinct from the `codeload.github.com` archive endpoint) at the same `ref` and verifies every extracted file against it before installing, aborting with `ChecksumMismatchError` on any mismatch. Fail-open if the manifest isn't available for a given `ref` (older tags); skip explicitly with `hersona update --no-verify`. Directly addresses an external review's "no signature or SLSA-like guarantee" critique — see `docs/SECURITY.md` for exactly what this does and does not protect against (transit tampering/corruption; **not** a compromised repo/account, **not** code signing).
- `SECURITY.md`: the project's first documented threat model — in-scope protections (archive size cap, path-traversal rejection, atomic install, checksum verification, PyPI Trusted Publishing), explicitly out-of-scope items (repo/account compromise, prompt injection at inference time, model behavior), and a reporting channel.
- `publish.yml`: adds `actions/attest-build-provenance` (build provenance attestation) to the wheel/sdist build step. PyPI Trusted Publishing (OIDC) was already in place from an earlier release; this closes the remaining "no supply-chain attestation" gap the external review flagged.
- CI: new `gen_checksums.py --check` step (same drift-gate pattern as `build_site.py --check` / `check_readme_counts.py`) so `checksums.json` can't go stale relative to `attributes/`/`schema/`.
- `hersona recommend --export {json,messages,markdown,openai_assistants,langchain_system_message} [--output FILE]`: export the recommended blend directly from the quiz result — no need to re-enter the attribute names into `hersona export`. Without `--output`, stdout carries only the payload (pipe-friendly); intensity resolves as `--weight` > fit-score suggestion. (First external user feedback; see `docs/IMPROVEMENT_PLAN_2026-07-04_user-feedback.md`.)
- `hersona recommend --soul [--profile NAME] [--soul-output FILE] [--soul-name NAME] [--force] [--dry-run]`: write the recommended blend straight to SOUL.md with the same refuse-by-default overwrite protection as `hersona soul`.
- `hersona recommend --save PRESET`: save the recommended blend as a named preset for later `hersona load`.
- MCP `recommend_blend`: new `export_format` parameter — the response gains an `export` key with the blend already exported in that format (one call instead of two).
- Demo site: the diagnostic quiz is now bilingual. `data.json` carries `prompt_en` / `label_en` on the BASE quiz plus a new `quiz_en` payload (the W2 English-persona quiz whose weights route to English speech attributes); the site recommends from `quiz_en` when the display language is EN.
- Demo site: first-visit language auto-detection — non-Japanese browsers default to EN, Japanese browsers keep the bilingual view (a saved toggle choice always wins). `<html lang>` now follows the toggle.
- Demo site: quiz result card gains a "Copy injection block" button that renders and copies the blend prompt in place, without a round-trip through the blend generator.
- `skills/hersona/SKILL.md` 0.6.0 → 0.7.0: document the `recommend --export/--soul/--save` bridge (details in `REFERENCE.md`).
- `docs/PUBLIC_API.en.md`: English translation of the public API contract (`docs/PUBLIC_API.md` was ja-only). Cross-linked from both files.
- `docs/app/README.en.md`: English translation of the demo-site README, cross-linked from `docs/app/README.md`.
- README EN/JA: "Try it in 30 seconds (no install)" pointer to the live demo site, ahead of the pip-install quickstart.
- README.md (EN): the "full programmatic API" links now point to `docs/PUBLIC_API.en.md` instead of the ja-only doc (second external-feedback item — EN users couldn't read half the docs; see `docs/IMPROVEMENT_PLAN_2026-07-04_user-feedback.md` §Phase 3).
- `scripts/check_readme_counts.py` + CI step: verifies README.md / README.ja.md mention the current total attribute count and per-category counts from `tests/catalog_counts.py` (the single source of truth). Added in response to an external review that caught three different attribute-count figures in the wild (README 208, actual 345, GitHub About 89); see `docs/reviews/2026-07-04-external-review-response.md`.
- `docs/reviews/2026-07-04-external-review-response.md`: response plan to an external critical review (5/10) — what to concede vs. rebut with measurement, a benchmarking strategy (`hersona bench`, planned), supply-chain hardening plan, and a v1.7.1 → v2.0.0 roadmap.
- **`hersona bench`**: a persona-maintenance benchmark harness directly answering the same review's "no token/maintenance-rate benchmarks" critique. Scores a transcript (list of assistant-response strings, from any source) turn-by-turn with the existing deterministic `measure_intensity`/`verify` scorer — no LLM calls, no new dependency. Reports maintenance rate (% turns in the expected intensity band), a per-turn score list (decay curve), and, via `--cost-only`, the injection block's char count / rough token estimate. `--demo` runs a self-contained synthetic-transcript smoke test (reuses `sample_dialogue.generate_samples`) so the pipeline is verifiable with zero setup; it's explicitly documented as tautological (scores catchphrases against themselves) and not a substitute for a real hersona-vs-baseline comparison. New core module `hersona.core.bench` (`score_transcript` / `estimate_token_cost` / `demo_transcript` / `load_scenario` / `available_scenarios`).
- `benchmarks/scenarios/*.yaml` (6 scenarios, CC0-licensed like `attributes/`): user-turn-only conversation scenarios (casual chat, a 12-turn topic-switching conversation for decay testing, an emotional roleplay beat, and a run of off-character technical questions, in both ja/en) to pair with your own model transcripts for `hersona bench`.
- `docs/BENCHMARKS.md`: what `hersona bench` measures and doesn't, a measured injection-token-cost table for representative blends × intensity levels, and a step-by-step recipe for running your own hersona-vs-baseline comparison rather than trusting a canned number.
- README EN/JA: a "What hersona is — and isn't" section (explicitly: not a reasoning/RAG/tool-use improvement) with a decision table against hand-written prompts, `.cursorrules`-style files, and agent frameworks (LangGraph/OpenAI Agents SDK/etc.), addressing the review's "real value is limited" critique head-on instead of arguing with it.
- `skills/hersona/SKILL.md` 0.7.0 → 0.8.0: document `hersona bench`.

- Demo site: responsive redesign (hamburger nav + 2-column Hero with stat panel + asymmetric Benefits). Mobile breakpoint at 900px swaps the nav for a `nav-toggle` button; the new `<aside class="hero-panel">` shows the live attribute count, the 5 category count, and the CC0 template license. Accessibility: a "Skip to content" link, `aria-current`/`aria-expanded` on nav, `prefers-reduced-motion` honored. Aesthetic: subtle fixed-position film grain (`body::after`, `opacity: 0.045`) and active-state scale on the primary CTA.
- `docs/app/app.js` (`initChrome`): IntersectionObserver-based scroll-spy for nav (`rootMargin: -35% 0px -55% 0px`); also drives the hero stat-count from `data.attributes.length`.
- `docs/app/style.css`: nav active state, mobile nav layout, hero-grid + hero-panel + hero-stat styling, benefits asymmetric 2-column layout, skip-link, film-grain layer.
- `docs/app/index.html`: bilingual `data-ja`/`data-en` tags on the new nav-toggle and skip-link; Hero restyled into `.hero-grid`; Benefits reorganized into `.benefit` (feature, left) + `.benefit-pair` (right, 2-up); `<main>` id renamed `top` → `main-content` so the skip-link has a stable target and the deep-link `#top` still scrolls to the Hero.

- `attributes/archetype/{school_nurse, twin, engineer, commander, oni, mediator, fallen_hero}.yaml` (+7; archetype 9 → 16). All 7 carry `content_i18n.en` per design §3.1 (forward-only contract; 7/9 legacy archetypes do NOT — see §3.1 fact gap in NOTES). Picks cover △ group of the 2026-07-03 backlog (school/family/profession/noble-supernatural/narrative-stance triangles).
- `.tmp/gen_b7_archetype.py`: reproducible B7 generator (7 attribute dicts → 7 YAMLs).
- TEST/DOC count sync: catalog_counts 201 → 208; archetype 9 → 16.
- `skills/hersona/SKILL.md`: frontmatter version 0.5.4 → 0.6.0 (data extension = minor bump per CONTRIBUTING.md).

### Changed

- `hersona.core.attach._render_prompt`: inject `first_person` / `lexical_markers` / `speech_style` into the blend block so they match what `measure_intensity` scores (first_person is first-wins like second_person). Adds `## First person` / `## Lexical markers` / `## speech_style` sections when present.
- `hersona.core.attach.response_style_directive`: new keyword-only `is_blend` arg (default `True`). The cross-attribute catchphrase-adaptation clause is now emitted only for multi-attribute blends, and the catchphrase / sentence-ending clauses are split by which sections are present. Single-attribute injection blocks shrink by ~270 chars (e.g. `keigo` 1133 → 861) with no behavior change for blends.
- `attributes/speech/{keigo,kansai_ben,archaic,boku_girl,onee_kotoba,ore_boy,third_person,whispery}.yaml`: backfilled `tone` / `sentence_endings` / `second_person` / `speech_style` (and `first_person` where applicable) so these core registers are actually injected and become measurable. `keigo` / `kansai_ben` etc. previously returned `None` from `measure_intensity` (no scorable signal); now scored. `third_person` intentionally keeps no `first_person` (its first person is the character's own name).
- `attributes/archetype/{mentor,rival,heroine,childhood_friend,gamer_otaku,robot_android,shrine_maiden}.yaml`: added `core_traits` and `tone` so the archetype role is injected, not just its catchphrases.
- `attributes/**` (16 files): replaced `examples` that were verbatim copies of `catchphrases` with 2–3 `[user]` / `[assistant]` dialogue exchanges (archetype ×7, speech ×9).
- README EN/JA: note that `first_person` / `lexical_markers` / `speech_style` are injected into the blend, not just used for intensity measurement.

### Fixed

- Demo site: the landing page said the diagnostic quiz has 5 questions; it has 9.
- `attributes/speech/mandarin_casual.yaml`: moved a schema-operational note out of the `tone` field (it was being injected verbatim as persona tone every session) into `notes`.
- `attributes/archetype/shrine_maiden.yaml`: fixed a Chinese `此处` → Japanese `此処` in a catchphrase / example (content_lang is ja).
- README EN/JA: switch the PyPI version badge from `badge.fury.io` to `img.shields.io/pypi/v/hersona` so the displayed package version tracks the current PyPI release; update the pinned `hersona update --ref` example to `v1.7.0`.
- README.md / README.ja.md / `skills/hersona/SKILL.md`: fixed a stale attribute-count figure (208, some as old as the pre-archetype/visual/hobby-expansion count) that had drifted out of sync with the actual catalog (345: personality 42 / speech 140 / archetype 66 / visual 46 / hobby 51). The archetype/visual/hobby attribute-name tables in both READMEs are now the full current lists rather than the original 9/5/5 samples. Caught by an external review that found three different attribute-count figures in the wild (README 208, actual 345, GitHub About 89 — the About field isn't updatable through this project's tooling and needs a manual edit). `CLAUDE.md` / `CONTRIBUTING.md` no longer hardcode a count — they point at `tests/catalog_counts.py` instead so this can't drift again silently.

- README EN/JA / `skills/hersona/SKILL.md`: attribute totals synced to **346** (`personality` **43**, including `persona_lock`).

## [1.7.0] - 2026-07-02

### Added

- `docs/guides/self-introduction.md` / `self-introduction.ja.md`: cross-persona self-introduction rules (privacy, no AI self-label, checklist).
- `docs/guides/README.md`: guide index.
- `examples/self-intro-memory.json`: template for `hersona soul --memory-file` reserved keys.
- `examples/sona-self-intro-memory.json`: Sona profile example (filled `self_intro_canonical`).
- `examples/sona-profile-memory.json`: Sona full Recent Context for SOUL regen (likes + self_intro + operating_mode).
- `docs/soul_md_persistence.md` §12: Recent Context limits and reserved memory keys for self-introduction.
- `hersona.core.self_intro`: `lint_self_intro`, `IntroLintResult`, `IntroViolation`, `merge_self_intro_guide`, `lint_memory_self_intro_canonical`, `self_intro_guide_defaults`.
- CLI `hersona lint-intro` (`--text` / `--input`, `--allow-handle`, `--canonical`, `--json`).
- `soul` / `persistent`: `--with-self-intro-guide`, `--lint-self-intro`, `--lint-self-intro-strict`, `--allow-handle`.
- `hersona.core.soul.detect_lang_from_names` (public blend language helper).
- `tests/test_self_intro_lint.py`, `tests/test_self_intro_guide.py`.

### Changed

- `skills/hersona/SKILL.md` (v0.6.0): When to Use for self-introduction; links to `docs/guides/`; `--with-self-intro-guide` / `--lint-self-intro-strict` guidance.
- `skills/hersona/REFERENCE.md`: self-introduction memory keys section; verification checklist item.
- `skills/hersona/references/self-introduction.md`: skill-side pointer to guides and §12.
- `docs/hermes-agent.md`: self-introduction guide links under Recent Context.
- `docs/PUBLIC_API.md`: `self_intro` section.
- `docs/guides/self-introduction.*`: checklist mentions `hersona lint-intro`.
- `README.md` / `README.ja.md`: Guides section with `lint-intro` / `soul` examples.

### Fixed
- `.github/workflows/publish.yml`: `actions/checkout@v4` を `fetch-depth: 0` に変更。タグ force-push 時に push イベントから渡される親 commit (例: v1.6.0 タグが b2eee7c を指しているのに、シャロー fetch では 03e5b73 を取りに行く) を checkout してしまう問題を解消。v1.6.0 publish run #28536447471 はこの症状で 1.5.0 wheel をビルドし PyPI 既存ファイルと衝突 (400 File already exists) して失敗していた。

## [1.6.0] - 2026-07-01

### Added
- `use_cases/*.yaml` + `schema/use_case.schema.json` + `hersona.core.use_cases`: introduce use-case / Operating Mode prompt packs that layer professional task discipline on top of persona blends without changing personality or speech payloads. Initial catalog includes `programmer`, `planner`, `research`, `marketing`, plus pro extensions `product_manager`, `qa_reviewer`, `data_analyst`, and `customer_support`.
- CLI/API integration for use cases: `hersona use-case list/show`, `hersona blend --use-case <id>`, and `hersona export --use-case <id>` (including OpenAI Assistants / LangChain metadata).
- `hersona soul --use-case` / `hersona persistent --use-case`: write Operating Mode blocks directly into generated SOUL.md content so professional task discipline survives future persona regeneration.

### Changed
- Generated SOUL.md now ends with `<!-- hersona:gen-end -->`; text below that marker is preserved across `--force` regeneration.

### Fixed
- README EN/JA, CONTRIBUTING, and `skills/hersona/SKILL.md`: synchronized public docs with the v1.5.0 catalog and schema (`201` attributes / `speech 140`, current i18n metadata, `content_lang: ja/en/zh/ko`, export formats, optional extras, MCP usage, and conflict-warning semantics).

## [1.5.0] - 2026-07-01

### Added
- `attributes/speech/seoul_casual.yaml`: new ko-content-lang speech attribute for modern Seoul casual Korean (서울말), completing the v1.5.0 zh/ko speech wave at 201 attributes / 140 speech entries.
- README EN/JA: added `#### Common recipes` (EN) / `#### よくあるレシピ集` (JA) under `### Use with Hermes Agent` / `### Hermes Agent で使う`, covering 7 concrete scenarios (tsundere single-attach, keigo stack, multi-attribute blend, per-attribute intensity, save/load preset, detach, preview). Each recipe is a Goal → Command → Behavior trio so first-time users can pick a scenario without reading SKILL.md end-to-end. EN/JA in sync per `CLAUDE.md` rules.
- `schema/attribute.schema.json`: extended `content_lang` enum from `[ja, en]` to `[ja, en, zh, ko]` to accept Chinese / Korean attribute template authoring. Description notes that zh/ko intensity measurement is still scoped to `skip` and tracked for v1.6.0+ (no core logic change; `core/intensity.py::content_language()` is already language-agnostic). Schema-only change; no attribute YAMLs added or modified in this PR — zh/ko attribute additions land in follow-up sub-PRs (PR-A1..A6) under `wt/feature-zh-ko-speech-set`.
- `attributes/speech/mandarin_casual.yaml`: new zh-content-lang speech attribute for casual / informal Mandarin Chinese (口语 / 普通话口语体). 10 Chinese catchphrases / 5 zh examples + `content_i18n.zh` (= BASE replication for explicitness) + `content_i18n.ja` (Japanese persona translation). Conflicts with `keigo_zh` / `jondaetmal` / `formal_en` / `blunt_en`. Total attribute count: 195 → 196. Schema already accepts `content_lang: zh` (PR-A0 precedent); this is PR-A1 of the `wt/feature-zh-ko-speech-set` series (PR-A2..A6 = keigo_zh / taiwan_mandarin / banmal / jondaetmal / seoul_casual, planned in the same v1.5.0 wave).
- `attributes/speech/keigo_zh.yaml`: new zh-content-lang speech attribute for polite / honorific-formal Mandarin Chinese (尊敬语 / 客气 / 礼貌). 10 Chinese catchphrases / 5 zh examples + `content_i18n.zh` (BASE replication) + `content_i18n.ja` (Japanese polite translation). Conflicts with `mandarin_casual` / `blunt_en` / `casual_en`. Compatible with `mentor` / `onee_san` / `butler` / `shrine_maiden` / `miko`. Total attribute count: 196 → 197. PR-A2 of the `wt/feature-zh-ko-speech-set` series.
- `attributes/speech/taiwan_mandarin.yaml`: new zh-content-lang speech attribute for Taiwanese Mandarin (台灣華語 / 國語 / Guoyu). 10 Chinese catchphrases / 5 zh examples + `content_i18n.zh` (BASE replication) + `content_i18n.ja` (Japanese translation). `register: neutral`. Conflicts with `mandarin_casual` / `keigo_zh` / `blunt_en`. Compatible with `childhood_friend` / `heroine` / `rival` / `gamer_otaku`. Total attribute count: 197 → 198. PR-A3 of the `wt/feature-zh-ko-speech-set` series.
- `attributes/speech/banmal.yaml`: new ko-content-lang speech attribute for casual / informal Korean (반말 / Korean banmal, タメ口). 10 Korean catchphrases / 5 ko examples + `content_i18n.ko` (BASE replication) + `content_i18n.ja` (Japanese translation). `register: casual`. Conflicts with `jondaetmal` / `keigo_zh` / `formal_en`. Compatible with `heroine` / `childhood_friend` / `rival` / `gamer_otaku` / `tomboy`. Total attribute count: 198 → 199. PR-A4 of the `wt/feature-zh-ko-speech-set` series (= v1.5.0 wave 2 = Korean language).

### Changed
- `render_blend` prompt control text now uses English for headings, language directives,
  intensity guidance, conflict warnings, and response-style rules while preserving native
  persona payload (`core_traits`, `catchphrases`, `sentence_endings`, `second_person`, `tone`).
  The docs app prompt preview was aligned with the same English-control/native-payload format.
- README EN/JA, `CLAUDE.md`, `tests/test_attributes.py` module docstring: sync documented public catalog totals to **201** attributes (**speech 140**); add v1.5.0 native zh/ko wave to the phase tables.
- Backfill zh/ko speech `conflicts_with` cross-links now that all six v1.5.0 wave attributes exist on main: `mandarin_casual`, `keigo_zh`, `taiwan_mandarin`, `banmal`, `jondaetmal`, and `seoul_casual` reference each other where casual/formal register mixing would break persona coherence. No attribute count change (still 201 / speech 140).
- Centralize public attribute count expectations in `tests/catalog_counts.py` so adding/removing YAML templates updates one module instead of five scattered test literals (`test_attach`, `test_attributes`, `test_cli`, `test_compatibility`, `test_mcp`). No runtime or catalog size change (still 201 / speech 140).
- `skills/hersona/SKILL.md` / `skills/hersona/REFERENCE.md` / `docs/hermes-agent.md`: rewrote `~/.hermes/config.yaml` and `~/.hermes/SOUL.md` references to describe persistence through framework APIs rather than as literal file paths, so the Skills Guard scanner (`tools/skills_guard.py::hermes_config_mod`, critical / persistence) no longer flags the skill during `hermes skills install hersona`. Verdict moves from `DANGEROUS` (community source + critical finding, --force cannot override) to installable. Behavior is unchanged — the implementation already delegates registry writes to the framework; documentation now matches. CHANGELOG.md and ROADMAP.md historical references are intentionally retained as the factual record.

### Fixed

## [1.4.2] - 2026-06-28

### Added
- `tests/test_packaging.py`: fixed `test_paths_resolve_in_repo_layout` for hosts with `~/.hermes/data/attributes` populated (see ### Fixed below for details).

### Changed
- README EN/JA: enriched Hero section with quantitative hook (195 attributes), PyPI/Downloads/MCP/Docs badges, and quick-link row. Added `## Why Hersona?` and `## 5-Minute Quickstart` sections to surface the value proposition and a copy-pasteable happy path. No content change to existing sections (Install / License / What it covers / Overview / Usage / Schema / Contributing).

### Fixed
- `tests/test_packaging.py::test_paths_resolve_in_repo_layout`: was failing on hosts where `~/.hermes/data/attributes` exists (the data-cache priority in `hersona.core.paths._resolve` shadowed the repo root path the test expected). Added autouse `_isolate_data_dir` fixture (mirroring the existing one in `tests/test_update.py`) to redirect `HERSONA_DATA_DIR` to a tmp path during the test, restoring the intended repo-root resolution. No production-code change; test-side fix only.
- 18 new anime-genre Japanese speech attributes (177 → 195 total: speech 116 → 134). All `content_lang: ja`, all with full i18n.ja display_name / description, 6 examples each (mild / moderate / strong / compatible_archetypes / multi-turn / NG), explicit `conflicts_with` lists, and `weight_dimension: strong|moderate`. Count contracts synced to 195 across README EN/JA, `CLAUDE.md`, and the hardcoded counts in `test_attributes` / `test_cli` / `test_compatibility` / `test_attach` / `test_mcp`.
  - **学園ラブコメ・日常系 (6)**: `osananajimi` (幼馴染, 「〜じゃない・昔から」); `imouto` (妹, 「おにいちゃん・えへへ」); `onee_san` (お姉さん, 「ふふっ・教えてあげる」); `mesugaki` (メスガキ, 「あらあら・ほら、ごほーしなさい」); `tsukkomi` (ツッコミ, 「だから・ありえない・なんでやねん」); `bokukko` (ボクっ娘, 「ぼく・〜だぜ・まかせて」).
  - **異世界・ファンタジー (6)**: `oujo` (王女, 「かしこまりました・この私が」); `densetsu_no_yuusha` (伝説の勇者, 「仲間がいる・必ず・信じてる」); `kuukichou` (委員長, 「えっと・一応・問題ない?」); `kuudere_girl` (クーデレ女子, 「……別に・べ、別にあんたのためじゃない」); `dark_hero` (ダークヒーロー, 「……・犠牲はやむを得ない・俺の美学」); `sensei_goroshi` (「せんせぇ・はぁ?・ち、ちが」).
  - **サブカル・変則 (6)**: `boin_girl` (ボイン幼馴染, 「あのね・〜なの・なになに?」); `hero_yamero` (異世界拒否, 「帰りたくない・召喚? 断る」); `isekai_cheat` (異世界チート, 「ステータス・スキル・LV・〜なんだけど」); `villainess` (悪役令嬢, 「破滅ですわ・婚約破棄・〜ですこと?」); `wizard` (魔法使い, 「〜の杖・召喚せよ・神秘の力」); `samurai_lol` (侍×現代, 「拙者・現代人とは・覚悟せよ」).
- Design decision: Phase 5 speech attributes are intended to be **independent** of personality/archetype roles — speech encodes "口調スタイル" (style), personality/archetype encode "キャラクター役割" (role). This lets a user combine e.g. `mesugaki` speech + `sadodere` personality, or `dark_hero` speech + `stoic` personality.
- `tests/test_attributes.py`, `test_cli.py`, `test_attach.py`, `test_compatibility.py`, `test_mcp.py`: bumped attribute-count assertions from 177 → 195.
- 24 new foreign-language speech attributes (153 → 177 total: speech 92 → 116). 15 English dialects (5 existing + 10 new) and 14 translation-style Japanese-flavored foreign-language registers (Chinese / Korean / French / German / Italian / Spanish / Russian / Arabic / Hindi / Vietnamese / Thai / Tagalog — `content_lang: ja` with native-script catchphrases). Count contracts synced to 177 across README EN/JA, `CLAUDE.md`, and the hardcoded counts in `test_attributes` / `test_cli` / `test_compatibility` / `test_attach` / `test_mcp`.
  - **英語方言拡張 (10件)**: `aussie_en` (Australian "G'day mate"); `scottish_en` ("och aye / braw / lassie"); `irish_en` ("craic / grand / cheers"); `valley_girl_en` (hyperfeminine 80s/90s "totally / as if / OMG"); `brooklyn_en` (NYC "fuggedaboutit / deadass"); `new_york_en` (Manhattan / New Yawk); `midwestern_en` ("ope / you betcha / dontcha know"); `pidgin_en` (Hawaiian/Pacific "howzit brah / da kine"); `jamaican_en` (Patois-flavored "irie / respect"); `punjabi_en` (Indian-English "ji / kindly revert").
  - **翻訳調外国語 (14件)**: `mandarin` (普通話, 拼音的); `taiwanese` (台湾華語); `cantonese` (広東語, 9声); `korean` (Standard 韓国語, ハングル音訳); `french` (フランス語, 上品); `german` (ドイツ語, 硬質); `italian` (イタリア語, 表現豊か); `spanish` (スペイン語, 熱的); `russian` (ロシア語, 重厚); `arabic` (アラビア語, 詩的); `hindi` (ヒンディー語); `vietnamese` (ベトナム語, 6声); `thai` (タイ語, メロディ); `tagalog` (タガログ語, `po/opo` 敬語).
- `tests/test_attributes.py`, `test_cli.py`, `test_attach.py`, `test_compatibility.py`, `test_mcp.py`: bumped attribute-count assertions from 153 → 177.
- 25 new character / subculture / era Japanese speech attributes (128 → 153 total: speech 67 → 92). All `content_lang: ja`, all with full i18n.ja display_name / description, 6 examples each (mild / moderate / strong / compatible_archetypes / multi-turn / NG), explicit `conflicts_with` lists, and `weight_dimension: strong|moderate`. Count contracts synced to 153 across README EN/JA, `CLAUDE.md`, and the hardcoded counts in `test_attributes` / `test_cli` / `test_compatibility` / `test_attach` / `test_mcp`.
  - **古風・時代・世代(9)**: `warawa` (平安風, 「わらわ・ぬし」); `wagahai` (夏目漱石文語, 「我輩は・である」); `taishou_retro` (大正・明治レトロ丁寧語); `shouwa_retro` (昭和男子, 「なんだと・おいおい」); `miko` (巫女, 「申し上げます・お祓い」); `samon` (侍, 「拙者・候」); `business` (ビジネス敬語/メール定型); `ojisan` (中高年男性, 「だべ・最近の若いもん」); `obaachan` (お婆ちゃん, 「のう・よしよし」).
  - **サブカル・Z世代・配信(8)**: `z_jidai_slang` (Z世代Web slang, 「やばt・ぴえん・草」); `vtuber` (萌え系, 「にゃ・えらい・おにいさん」); `streamer` (配信者, 「ありがとナス・くね?」); `yankee` (ヤンキー, 「〜っす・しばく」); `chuunibyou_speech` (厨二病, 「我が名は・闇の力・覚醒せよ」); `sensei` (教師, 「〜ですぞ・ほら」); `akuma_oujo` (悪役令嬢, 「破滅ですわ・婚約破棄」); `butler` (執事, 「ご主人様・かしこまりました」).
  - **追加キャラ・職業(8)**: `mahou_shoujo` (魔法少女, 「変身!・愛と希望と勇気」); `yuuusha` (勇者, 「仲間がいる・必ず」); `ryoushi` (漁師, 「おまいら・いっしょ」); `musuko` (中高生男子, 「マジか・草・ウケる」); `ol` (OL, 「定時で上がりたい・キャパ」); `mama` (母, 「早くしなさい・あんたのためよ」); `kawaii` (萌え, 「ぴえん・ぱおん・てへぺろ」); `sage` (RPG賢者, 「おぬし・じゃな・ほうほう」).
- `tests/test_attributes.py`, `test_cli.py`, `test_attach.py`, `test_compatibility.py`, `test_mcp.py`: bumped attribute-count assertions from 128 → 153.
- 36 new regional Japanese dialect `speech` attributes (92 → 128 total: speech 31 → 67). Authored with `content_lang: ja`, `weight_dimension: strong|moderate`, and full i18n.ja display_name / description. Each YAML carries 6 examples (mild / moderate / strong / compatible_archetypes / multi-turn / NG) and explicit `conflicts_with` lists to flag incompatible blends at AI-agent injection time. Count contracts synced to 128 across README EN/JA, `CLAUDE.md` / `CONTRIBUTING.md`, and the hardcoded counts in `test_attributes` / `test_cli` / `test_compatibility` / `test_attach` / `test_mcp`.
  - **北海道・東北(5)**: `hokkaido_ben` (strong, "なまら・だべ" rhythm, friendly Hokkaido-wide dialect); `tsugaru_ben` (strong, zūzū-ben with si/su alternation, the most difficult mainland dialect); `sendai_ben` (moderate, mild "だっちゃ" central-Miyagi speech); `akita_ben` (moderate, gentle zūzū-ben "けっこ・なんだべな"); `yamagata_ben` (moderate, three sub-varieties — Shonai leans Niigata).
  - **関東・北陸(6)**: `tokyo_ben` (strong, Showa-era 山手言葉 "チョベリグ・バリバリ"); `kanazawa_ben` (strong, 加賀弁 with 弁慶言葉 softening); `toyama_ben` (strong, "おまんら・ずら・きときと"); `niigata_ben` (strong, snow-country "しょっぺ・ぶぶ漬け"); `ibaraki_ben` / `tochigi_ben` (both strong, North-Kanto).
  - **東海・近畿(8)**: `nagoya_ben` (strong, "だがや・りん・みゃー" — Chubu core); `shizuoka_ben` / `gifu_ben` / `mie_ben` (moderate); `osaka_ben` (strong, 商人言葉 "もうかりまっか・ぼちぼち", distinct from generic `kansai_ben`); `nara_ben` / `wakayama_ben` / `hyogo_ben` (moderate, regional Kansai).
  - **中国・四国(7)**: `okayama_ben` / `yamaguchi_ben` (both moderate, "じゃけ・せこい"); `shimane_ben` (moderate, 東山陰); `sanuki_ben` / `ehime_ben` / `kochi_ben` / `tokushima_ben` (moderate, 四国四方言).
  - **九州・沖縄(7)**: `kagoshima_ben` (strong, 薩隅方言 "〜び・わっぜ"); `oita_ben` / `miyazaki_ben` / `nagasaki_ben` / `kumamoto_ben` / `saga_ben` (moderate, 九州各県); `okinawa_ben` (strong, Uchinaaguchi — Ryukyuan language distinct from mainland Japanese; conflicts_with all mainland dialects).
  - **関東残(3)**: `kanagawa_ben` / `gunma_ben` / `saitama_ben` (moderate, 北関東〜京浜境界).
- Phase 1 roadmap (`ObsidianVault/30_Projects/hersona/01_実装予定_speech拡張.md`) consolidated by dropping the originally-planned standalone `fukui_ben` (folded into `kanazawa_ben` variant: 嶺北 dialect continuum) and `aomori_ben` (folded into `tsugaru_ben` variant: 南部方言 spans Aomori-east / Iwate-north) per the 2025-06-27 review's dedup recommendation. `kanagawa_ben` was kept as a standalone YAML (Keihin dialect's distinctive 巻き舌 rhythm warrants its own attribute rather than a variant).
- `tests/test_attributes.py`, `test_cli.py`, `test_attach.py`, `test_compatibility.py`, `test_mcp.py`: bumped attribute-count assertions from 92 → 128 and added `tsugaru_ben` to the `ts`-prefix completer expectation (`["tsugaru_ben", "tsundere"]`).
- 3 new attributes (89 → 92 total: personality 40 → 42, speech 30 → 31):
  - `personality/hautaine` — inborn pride / condescending air from background; composure rooted in upbringing, not in a wish to be treated like royalty (distinct from `himedere`'s princess-complex expectation of royal treatment, and from `tsundere`'s bashfulness); conflicts with deredere / puppyish / genki
  - `personality/sociable` — reads the room and the listener, calibrates tone, bridges different groups; attentive presence that makes a gathering easier to be in (distinct from `genki`'s undirected high energy, `playful`'s joke-deflector, and `deredere`'s romantic openness); conflicts with socially_anxious / dandere / hikikomori
  - `speech/archaic_otaku` — classical Japanese register (`我/拙者/吾輩`, `〜でござる`, `〜に在り`, `〜奉る`) fused with otaku-style work / character references and 推し活 vocabulary; treats anime / light novel / game works as canonical texts worthy of 文語-style reverence; conflicts with gyaru / ore_boy / kansai_ben / blunt
- SKILL version bumped to v0.5.4; count contracts synced to 92 across README EN/JA, `CLAUDE.md` / `CONTRIBUTING.md`, `skills/hersona/SKILL.md` + `REFERENCE.md`, and the hardcoded counts in `test_attributes` / `test_cli` / `test_compatibility` / `test_attach` / `test_mcp`.
- 5 new English-native `personality` attributes for international users (84 → 89 total, personality 35 → 40). Authored with `content_lang: en` (base content in English + `i18n.ja` display/description), parallel to the existing `*_en` speech registers. Western pop-culture archetypes distinct from the Japanese anime tropes:
  - `sassy` — bold, quick-witted, comeback-ready confidence read as cheek, not cruelty (distinct from playful's joke-deflection and deadpan's flat retort; conflicts with socially_anxious / dandere)
  - `rebel` — principled defiance of unearned authority and rules-for-rules'-sake; loyal to people, not systems (Western outlaw/maverick flavor)
  - `charmer` — smooth, magnetic, effortlessly likeable; flirtation as reflex over real warmth (charisma, not narcissism's self-love; conflicts with socially_anxious / dandere)
  - `drama_queen` — lives at full volume, every feeling performed for the back row, with a genuine heart under the theatrics (distinct from menhera's anxiety and crybaby's genuine tears; conflicts with stoic / deadpan / laid_back)
  - `go_getter` — ambitious, plan-first, take-charge drive that turns "someday" into a deadline (goal/ambition-driven, distinct from diligent's effort-as-intrinsic-value; conflicts with laid_back / pessimist)
- SKILL version bumped to v0.5.3; count contracts synced to 89 across README EN/JA, `CLAUDE.md` / `CONTRIBUTING.md`, `skills/hersona/SKILL.md` + `REFERENCE.md`, and the hardcoded counts in `test_attributes` / `test_cli` / `test_compatibility` / `test_attach` / `test_mcp`.
- README (EN/JA): add prominent "Install (Hermes Agent)" section featuring `hermes skills tap add shiro-0x/hersona` — no registry approval needed, works immediately. Also includes skill registry status table (HermesHub PR pending, ClawHub in progress).
- `skills/hersona/SKILL.md` and `skills/hersona-initializer/SKILL.md`: add `metadata.openclaw` block (emoji, homepage, os) to prepare for ClawHub submission.
- `hersona update` subcommand: download the latest attribute data (`attributes/` + `schema/`) from the GitHub repository into a local data cache (`~/.hermes/data/` by default, or `HERSONA_DATA_DIR`), so pip/wheel installs can refresh templates **without reinstalling**. The cache takes precedence over the bundled data in `hersona.core.paths`. Supports `--ref` (branch/tag/commit SHA, default `main`), `--dry-run`, and `--clear` (revert to bundled templates). Uses only the Python standard library (`urllib` + `tarfile`); no new dependencies. New core module `hersona.core.update` and `hersona.core.paths.data_cache_root()`.
- 1 new `personality` attribute (83 → 84 total, personality 34 → 35):
  - `puppyish` — bright, open-hearted attachment that forms fast; admires and follows the people they like, eager for attention and praise ("dog-type junior" trend). Distinct from deredere (romantic openness), genki (undirected energy), and menhera (anxious dependency); conflicts with kuudere / hinedere / stoic / deadpan.
- 8 new attributes (75 → 83 total: personality 30 → 34, speech ja 21 → 25):
  - `scheming` — smiling exterior, cold calculation underneath; kindness is investment (distinct from yandere's obsession and narcissist's self-love)
  - `gluttonous` — food as primary motivation and lens; mood drops when hungry (distinct from hobby/cooking which is skill, not drive)
  - `crybaby` — cries easily from joy, sadness, and gratitude; emotionally transparent, not psychologically unstable (distinct from menhera's abandonment anxiety)
  - `diligent` — effort as intrinsic value; never quits, always finds the next angle (distinct from serious's demeanor and stoic's emotional suppression)
  - `hakata_ben` — Kyushu/Hakata dialect; energetic `〜と？/〜たい/〜ばい/〜けん` endings; warm and direct
  - `tohoku_ben` — Tohoku/Zuzu-ben dialect; gentle vowel-merged `〜だべ/〜っぺ/〜んだ` patterns; soft and unhurried
  - `robotic` — monotone declarative `-desu/-masu`; literal interpretation, zero filler, mechanical register (pairs with robot_android archetype)
  - `burikko` — performative cuteness with drawn-out syllables and affected helplessness; performed, not felt (distinct from natural soft/whispery)
- Optimized SKILL.md taxonomy table: personality/speech rows now use abbreviated `...` notation (fixed-width rows) instead of enumerating all names, eliminating per-turn linear token growth as the library scales
- SKILL version bumped to v0.5.1

### Changed
- `puppyish` ("dog-type junior"): toned down the literal-dog imagery while keeping
  the affectionate-junior core (looks up to / follows / craves praise, keigo speech).
  Removed tail-wagging and head-pat motifs — the `頭なでてほしいです` / "Can I get a
  head pat?" catchphrase becomes `もっと褒めてほしいです` / "Tell me I did good?",
  dropped "尻尾を振るように" / "tail-wagging energy" from `tone`, softened
  "感情を全開で表に出す" → "感情を素直に表に出す", and lowered `typical_value_range`
  0.4-0.8 → 0.3-0.7 so the default intensity sits a notch lower (EN/JA kept in sync).
- 5 more `personality` attributes inspired by recent anime trends, bringing the
  total to 75 (personality 30):
  - `menhera` — emotionally volatile, abandonment anxiety, constant need for
    reassurance (jirai-kei trend; inward-facing, no violence — unlike yandere)
  - `battle_junkie` — lives for the thrill of combat; grins wider at stronger
    foes, bored by peace (shonen staple; distinct from hot_blooded's conviction)
  - `deadpan` — dry, flat-toned straight-man / tsukkomi who calmly retorts to
    everyone else's antics (comedy staple; reacts, unlike stoic)
  - `socially_anxious` — crippling social nerves with a loud comedic inner
    monologue; freezes and self-deprecates yet longs to connect (slice-of-life
    "bocchi" trend; panicky/talkative-internally, unlike the calm dandere)
  - `laid_back` — unhurried, unbothered "it'll work out" tempo that defuses
    others' panic (low-energy pacing, unlike optimist's bright hope)
- 5 new `personality` attributes (personality 25, total 70):
  - `deredere` — openly and unguardedly affectionate; feelings on sleeve, no defense
  - `himedere` — princess complex; expects royal treatment, but sweet when pleased
  - `kamidere` — god complex; absolute superiority, cool and imposing
  - `sadodere` — loving through teasing; provocative edge with deep affection underneath (no violence, unlike yandere)
  - `hinedere` — cynical exterior, warm heart; shows care through action rather than words

### Fixed
- README EN/JA: removed stale `v0.0.1` version markers from the
  `License structure` / `Attribute templates` headings (the codebase is at
  `v1.4.1`); renamed the `Optional fields` heading from
  `(6 Round-3 template fields)` to plain `Optional fields` since the table now
  lists 8 fields (matches the optional persona-content fields in
  `schema/attribute.schema.json`); added a one-paragraph note under
  `Template generation script` clarifying the normal maintenance flow
  (edit `attributes/<category>/<name>.yaml` + run `python scripts/validate.py`)
  and that `scripts/_oneoff/gen_v1_attributes.py` is a frozen legacy snapshot,
  not the daily workflow. EN/JA kept in sync.

### Changed
- Synced the attribute-count contracts to 75 across docs and tests for the two
  personality batches above: README EN/JA tables, `CLAUDE.md` / `CONTRIBUTING.md`
  count notes, the always-loaded `skills/hersona/SKILL.md` taxonomy (bumped to
  v0.5.0) and `REFERENCE.md` checklist, plus the hardcoded counts in
  `test_attributes` / `test_cli` / `test_mcp` / `test_compatibility` /
  `test_attach` (these are count contracts that must track the total).
- **Optimized per-turn injection cost** (conversations got "heavy" with the
  skill active). The three overlapping anti-repetition / naturalness notes are
  consolidated into a single `response_style_directive(lang, *, has_catchphrases,
  has_sentence_endings)` emitted once after the weight guidance, omitting the
  catchphrase/ending clause when those sections are absent. Shaves up to ~190
  chars per injected block (e.g. `washi+tsundere` strong: 1283 → 1091 chars).
  `catchphrase_usage_directive` is retained (still used by SOUL.md rendering).
- **Slimmed `skills/hersona/SKILL.md`** (~32k → ~22k chars, the part loaded
  into context whenever the skill is active) by moving flag deep-dives, the
  verification checklist, one-shot recipes, and version history into a new
  on-demand `skills/hersona/REFERENCE.md`. SKILL bumped to v0.3.0.

## [1.3.0] - 2026-06-17

初回フルリリース（measure /strict + SOUL.md memory + export 5 形式 全部入り）。
後に semver ロールバック経由で [0.2.0] および [1.4.0] が連続リリースされたため、
機能セットの参照は [1.4.0] を参照。

## [0.2.0] - 2026-06-17

> **Yanked 推奨**: semver ロールバック産。`pip install hersona` は [1.4.0] を解決。
> このリリースで追加された機能はない（[1.3.0] と同じコードを別 version 文字列で
> publish しただけ）。PyPI 履歴保持目的のみで存在。

## [1.4.0] - 2026-06-17

### Added
- `hersona measure --strict` / `--check-prompt`: when the score falls below (or
  above) the expected band, emit a pasteable self-audit prompt covering
  catchphrases, sentence endings, `conflicts_with` warnings, and weight level
  alignment. The prompt is generated deterministically from `WEIGHT_GUIDANCE` +
  attribute YAML; no LLM dependency. New public API
  `hersona.core.pre_response_check_prompt(names, weight_level, last_response=None, lang="en")`.
- `Recommendation.intensity_baseline` (and `Preset.intensity_baseline`):
  when `hersona recommend --apply` produces a blend, the engine now also runs
  `verify_intensity` against a synthetic ideal sentence and stores the
  expected band on the result. Future sessions can compare the current
  `hersona measure` output against this baseline. 10 new tests.
- SOUL.md `## Recent Context` block: `render_soul(..., memory=...)` and
  `write_soul(..., memory=...)` accept a caller-supplied `dict[str, str]`
  (≤16 keys, ≤512 chars per value, key pattern `^[a-z0-9_]{1,32}$`) and
  append a `## Recent Context` section after `## 4. Behavioral Guidelines`.
  The block is purely the *shape* — content population (e.g. LLM-based memory
  extraction) is the host agent's responsibility. `hersona soul` and
  `hersona persistent` gain `--memory <json>` and `--memory-file <path>`
  flags. `run_persistent` also accepts both. Markdown special chars in values
  are escaped to prevent injection. 10 new tests, 0 schema change,
  semver-additive.
- Export formats: `--format openai_assistants` and `--format langchain_system_message`
  added to `hersona export`. `EXPORT_FORMATS` grows from 3 to 5 entries. Both
  reuse `render_blend` for the prompt text and namespace hersona-specific
  fields (`hersona_version`, `hersona_blend`, `hersona_weight`,
  `hersona_content_lang`, `hersona_conflicts`) under `metadata` /
  `response_metadata` to avoid collisions. No `openai` / `langchain` Python
  dependency introduced — outputs are plain JSON. New public API:
  `hersona.core.export_for_openai_assistants(...)` and
  `hersona.core.export_for_langchain_system_message(...)`. 6 new tests, 0
  schema change, semver-additive.
- `hersona persistent --target {claude,codex,cursor,gemini}`: write the persona to other
  agent tools' auto-loaded convention files, not just Hermes. `claude` → `CLAUDE.md`
  (`~/.claude/CLAUDE.md` with `--global`), `codex`/`agents` → `AGENTS.md`, `cursor` →
  `.cursorrules`, `gemini` → `GEMINI.md`. `--output` overrides the path; `--global` targets
  the home location. The persona body reuses the SOUL renderer with a tool-neutral header
  (the Hermes-only "正式名称: Hermes Agent" line is omitted). Hermes-only flags
  (`--auto-config` / `--apply`) are ignored with a notice for non-hermes targets. Core logic
  in `hersona/core/targets.py` (`TARGETS`, `write_target`, `render_for_target`); 17 + 4 new tests.
- `hersona persistent --apply`: runs `hermes config set agent.personality <name>` to activate
  the personality immediately (the flat `agent.personality` key is not nested YAML, so
  `hermes config set` is safe here). Reports `hermes not found` gracefully when the CLI is absent.
- `hersona persistent --auto-config`: automatically writes the `agent.personalities.<name>`
  entry to `~/.hermes/config.yaml` via PyYAML direct edit — bypassing `hermes config set`
  (Pitfall 8: nested YAML corruption). A `.bak` backup is created before any write, and
  the file is re-validated after writing. `--force` enables overwriting an existing entry.
  `--config-path` overrides the target file. Core logic in `hersona/core/config_writer.py`
  (`write_personality`, `ConfigWriteResult`); 12 new tests.
- fix: `default_soul_path()` now returns `~/.hermes/SOUL.md` (HERMES_HOME root) instead
  of `~/.hermes/profiles/<profile>/SOUL.md`. Local Hermes CLI reads only the root path
  (`prompt_builder.py: soul_path = get_hermes_home() / "SOUL.md"`); profile-specific
  paths are Hermes One only and not read by the local CLI. The `profile` argument is
  kept for backward compatibility but is now ignored.
- C: new speech attribute `hiroshima_ben` (Hiroshima dialect) — 65 attributes total
  (speech 26 = ja 21 + en 5). Assertive '-ja / -jakee / -kee / -toru' endings and the
  'buchi' intensifier; uses the new `first_person` field (わし / わしゃ / うち). Conflicts with
  the polite/refined registers (keigo / onee_kotoba / archaic / princess_speech).
- C: MCP server (`hersona-mcp`, IMPROVEMENT_PLAN M3) via the optional `mcp` extra
  (`pip install "hersona[mcp]"`). Exposes `list_attributes` / `show_attribute` / `blend` /
  `export` / `recommend_blend` / `compatibility` tools to MCP-aware agents. Pure tool logic
  lives in `hersona/mcp/tools.py` (no `mcp` dependency, fully tested); `hersona/mcp/server.py`
  is a thin FastMCP wiring layer that lazy-imports `mcp` and raises a clear install hint when
  it is absent. 12 new tests.
- C: agent export — `hersona export <names...> --format {json,messages,markdown}` and
  `export_blend()` (exported from `hersona.core`, documented in `docs/PUBLIC_API.md`) hand a
  blend off to other agent frameworks (LangGraph / LangChain / OpenAI / Anthropic). `json` is
  structured (metadata + system prompt + per-attribute summary + conflicts), `messages` is a
  `[{"role":"system","content":...}]` array, `markdown` is the raw injection block. Reuses
  `render_blend`. Core logic in `hersona/core/export.py`; 8 + 4 new tests.
- C: shell tab-completion via the optional `completion` extra (`pip install "hersona[completion]"`).
  `argcomplete` completes subcommands, attribute names (`show`/`blend`/`diff`/`preview`/`measure`/`save`),
  and preset names (`load`). The CLI is unchanged without it (completion simply absent); enable with
  `eval "$(register-python-argcomplete hersona)"`.
- C: blend presets — `hersona save <name> <attrs...> [--weight] [--note]` persists a blend
  (a recipe of attribute names + intensity) as a named preset under `~/.hermes/presets/`
  (override with `HERSONA_PRESETS_DIR`). `hersona presets` lists them and `hersona load <name>`
  replays one through the same blend engine (with optional `--weight` override). Core logic in
  `hersona/core/presets.py` (`Preset`, `save_preset`, `load_preset`, `list_presets`,
  `delete_preset`, `presets_root`, `PresetError`), exported from `hersona.core` and documented
  in `docs/PUBLIC_API.md`. 27 new tests.
- B3: `image_prompt_tags` (string[]) optional field added to `schema/attribute.schema.json`
  for visual attributes. All 5 visual templates (`animal_ears` / `glamorous` / `glasses` /
  `petite` / `silver_hair`) now carry English SD/Flux-style tag lists.
- B4: `first_person` (string) optional field added to `schema/attribute.schema.json`.
  Seven speech attributes now declare their first-person pronoun(s):
  `ore_boy` (オレ/俺), `boku_girl` (ボク), `washi` (わし), `gyaru` (あたし/うち),
  `tomboy` (あたし), `princess_speech` (わたくし/私), `archaic` (我/拙者).
- B4: `IntensityReport.first_person_hits` field added; intensity score now uses a
  3-axis formula when both `sentence_endings` and `first_person` are present
  (`0.45·endings + 0.30·catchphrase + 0.25·first_person`). Attributes with only
  `first_person` (no endings, e.g. `ore_boy`, `boku_girl`) are now measurable
  instead of being skipped. `format_report` output includes the first_person count.
  19 new tests (608 total).

### Changed
- `docs/app/` live demo: the "体験デモ: 人格が変わる" persona picker is now a native
  `<select>` pull-down instead of a flex-wrap row of buttons. Mobile users get the
  OS-native wheel/dialog picker (iOS / Android), with `appearance: menulist-button`,
  `min-height: 44px` (Apple HIG / Material touch target), `font-size: 16px` (prevents
  iOS Safari's auto-zoom on focus), and `width: 100%` on screens ≤ 480 px. The
  `<label>` is wired to the `<select>` via `for`/`id` and `aria-label`. JS-side:
  `renderDemo()` now builds `<option>`s from `state.showcase.items` with the
  `state.lang`-aware label (ja / en / "ja / en" in 併記 mode) and listens to `change`
  instead of `click`. A `<noscript>` fallback message is shown when JS is disabled.

### Fixed
- `docs/app/app.js` `renderGallery()` was throwing `TypeError: Cannot read properties
  of undefined (reading 'ja')` whenever the catalog contained a `visual`-category
  attribute (5 templates: `animal_ears` / `glamorous` / `glasses` / `petite` /
  `silver_hair`). `CAT_LABEL` and `CAT_ORDER` were missing the `visual` key, so
  `CAT_LABEL["visual"]` returned `undefined` and the `.ja` lookup blew up. Added
  `visual: { ja: "見た目", en: "Visual" }` to `CAT_LABEL` and inserted `"visual"`
  between `"speech"` and `"archetype"` in `CAT_ORDER`. Verified via jsdom: the
  gallery / blend filter chips now render `見た目 (5)` and visual cards show
  "見た目" as `card-cat`; gallery counts add up to 65 (性格 20 / 口調 26 / 見た目 5 /
  アーキタイプ 9 / 趣味 5). No more render errors in the console.

## [0.0.1] - 2026-06-15

First published release (PyPI via Trusted Publishing on the `v0.0.1` tag).

### Added
- 64 attribute templates (personality 20 / speech 25 / archetype 9 / visual 5 / hobby 5)
- `schema/attribute.schema.json` for attribute validation
- `hersona` CLI (`list` / `show` / `matrix` / `blend` / `diff` / `preview` / `recommend` / `create` / `measure`)
- `hersona preview <names...>` — show the injection block plus catchphrase-based sample
  phrases for a blend, with no LLM required (wraps `core.sample_dialogue`).
- `hersona diff <a> <b>` — compare two attributes: relation (conflict/compatible/neutral,
  including cross-language speech conflicts), scalar fields side by side, and list fields
  (core_traits / catchphrases / ...) split into common vs. only-one. Core logic in
  `hersona/core/diff.py`.
- Optional `tui` extra (`pip install "hersona[tui]"`): color tables for `list` and panels
  for `show` via `rich`. Falls back to plain text without `rich`, when piping, or with
  `--plain` / `NO_COLOR`; `HERSONA_FORCE_RICH=1` keeps color when piping.
- Compatibility matrix with conflict/compatible resolution, plus conflict-fix
  suggestions: `CompatibilityMatrix.alternatives_for()` / `suggest_blend_fixes()`
  propose same-category, non-conflicting replacements, surfaced by
  `hersona blend --suggest` / `hersona preview --suggest`
- Intensity scoring for speech attributes
- Diagnostic quiz with multilingual support (en/ja)
- `skills/hersona/SKILL.md` for Hermes Agent integration
- MIT license for code, CC0 1.0 for attribute templates
- `weight_for_score(score, *, previous, thresholds, hysteresis)` public API — maps a
  0–100 continuous score to a `WeightLevel`, with optional hysteresis (the level only
  changes once the score crosses a threshold by ±`hysteresis`). Intended for the duet
  emotion/affection dial.
- `docs/PUBLIC_API.md` declaring `hersona.core.__all__` as the semver-stable public API.
  `tests/test_public_api.py` keeps the document and `__all__` in sync automatically.
- PyPI packaging: the wheel bundles `attributes/` and `schema/` under `hersona/data/`
  (resolved by `hersona/core/paths.py` for both the repo and installed layouts).
  `.github/workflows/publish.yml` publishes to PyPI via Trusted Publishing on `v*` tags.
  `tests/test_packaging.py` regression-tests the bundled contents.
- `.github/workflows/ci.yml` running `ruff` + `scripts/validate.py` +
  `build_site.py --check` + `pytest` on Python 3.11/3.12/3.13.

### Changed
- pyproject: PyPI metadata (English `description` / `keywords` / `classifiers` / `urls`);
  removed the unused `requests` dependency; the dev-only `scripts/` is excluded from the wheel.
