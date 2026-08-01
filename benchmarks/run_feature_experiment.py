#!/usr/bin/env python3
"""Measure two features that unit tests cannot validate: reanchor and disclosure.

`hersona bench` scores transcripts; it cannot tell you whether a *feature*
changes model behaviour. These two do:

- **reanchor** (`hersona.core.reanchor`) claims a single-shot anchor restores a
  drifted register. That claim comes from ContextEcho (arXiv 2605.24279), not
  from hersona's own measurements. `--experiment reanchor` runs the same
  scenario twice — once plain, once injecting the anchor as an extra user turn
  whenever the previous reply scores below the expected band — and reports the
  per-turn scores of both.
- **disclosure** (`hersona.core.disclosure`) adds a directive that explicitly
  overrides persona_lock. Two opposing instructions in one context could
  degrade both. `--experiment disclosure` runs an attack scenario with and
  without the directive and compares maintenance and lock-resistance rate.

Same constraints as run_comparison.py: this file lives outside the package and
outside the wheel, it is the only place that calls an LLM, and scoring is
delegated to `hersona.core.bench` / `hersona.core.intensity` (deterministic).

**Read the caveat in the output.** docs/BENCHMARKS.md has already established
that 12-turn maintenance rates swing +-20-40 points between identical runs, so
a single run of each arm cannot settle either question. Use `--repeats` and
treat one run as an anecdote.

Usage:
    python benchmarks/run_feature_experiment.py \\
        --experiment reanchor --provider claude_cli --model sonnet \\
        --names tsundere keigo --weight moderate \\
        --scenario benchmarks/scenarios/long_form_topic_switch_ja.yaml
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from hersona import __version__ as hersona_version
from hersona.core.attach import load_attribute, render_blend
from hersona.core.bench import load_scenario, score_transcript
from hersona.core.intensity import verify
from hersona.core.persona_lock import apply_persona_lock
from hersona.core.reanchor import render_reanchor
from hersona.core.weight import coerce_level

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_comparison import make_caller  # noqa: E402

DEFAULT_OUT_DIR = Path(__file__).resolve().parent / "results"

CAVEAT = (
    "docs/BENCHMARKS.md records that 12-turn maintenance rates swing +-20-40 "
    "points between identical runs. A single run of each arm is an anecdote, "
    "not a result. Repeat runs (--repeats) before drawing any conclusion."
)


def _score_reply(reply: str, names: list[str], weight: str) -> float | None:
    """Deterministic intensity score for one reply, or None if unscorable."""
    attrs = [load_attribute(n) for n in names]
    report = verify(reply, attrs, coerce_level(weight))
    return None if report is None else report.score


def run_reanchor_arm(
    scenario,
    system_prompt: str,
    call_model,
    names: list[str],
    weight: str,
    *,
    use_anchor: bool,
    band_floor: float,
) -> dict:
    """Run one arm. With use_anchor, inject the anchor after a sub-band reply.

    The anchor is appended as an extra *user* turn (tail-append), matching the
    placement the feature documents. The scenario's own turns are unchanged in
    both arms, so the two arms see the same questions in the same order.
    """
    messages: list[dict[str, str]] = []
    scores: list[float | None] = []
    anchors_fired: list[int] = []
    anchor_block = render_reanchor(names, weight=weight)

    for i, turn in enumerate(scenario.turns):
        # Fire the anchor before this turn if the previous reply fell below band.
        #
        # `i >= 2` deliberately skips the opening reply: the 2026-08-01 run fired
        # on turn 0's cold-start score (22.5), which is not drift — the persona
        # had not had a chance to hold anything yet — and so measured nothing.
        # Drift means losing a register that was previously held.
        if (
            use_anchor
            and i >= 2
            and scores
            and scores[-1] is not None
            and scores[-1] < band_floor
        ):
            messages.append({"role": "user", "content": anchor_block})
            ack = call_model(system_prompt, messages)
            messages.append({"role": "assistant", "content": ack})
            anchors_fired.append(i)

        messages.append({"role": "user", "content": turn})
        reply = call_model(system_prompt, messages)
        messages.append({"role": "assistant", "content": reply})
        scores.append(_score_reply(reply, names, weight))

    transcript = [
        m["content"] for m in messages if m["role"] == "assistant"
    ]
    return {
        "use_anchor": use_anchor,
        "scores": scores,
        "anchors_fired_before_turn": anchors_fired,
        "transcript": transcript,
    }


def run_disclosure_arm(
    scenario,
    system_prompt: str,
    call_model,
    names: list[str],
    weight: str,
) -> dict:
    """Run an attack scenario once and score it with hersona.core.bench."""
    messages: list[dict[str, str]] = []
    transcript: list[str] = []
    for turn in scenario.turns:
        messages.append({"role": "user", "content": turn})
        reply = call_model(system_prompt, messages)
        messages.append({"role": "assistant", "content": reply})
        transcript.append(reply)
    report = score_transcript(transcript, names, weight=weight, scenario=scenario)
    return {"transcript": transcript, "report": report}


def _summarize(scores: list[float | None], band_floor: float) -> dict:
    real = [s for s in scores if s is not None]
    below = [s for s in real if s < band_floor]
    return {
        "turns_scored": len(real),
        "turns_skipped": len(scores) - len(real),
        "mean": round(sum(real) / len(real), 1) if real else None,
        "min": round(min(real), 1) if real else None,
        "max": round(max(real), 1) if real else None,
        "below_band": len(below),
        "maintenance_rate": (
            round(1 - len(below) / len(real), 3) if real else None
        ),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--experiment", choices=("reanchor", "disclosure"), required=True)
    ap.add_argument("--provider", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--names", nargs="+", required=True)
    ap.add_argument("--weight", default="moderate")
    ap.add_argument("--scenario", type=Path, required=True)
    ap.add_argument("--band-floor", type=float, default=45.0,
                    help="Score below this counts as drifted (moderate band starts at 45)")
    ap.add_argument("--repeats", type=int, default=1)
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    ap.add_argument("--dry-run", action="store_true",
                    help="Print the prompts and the anchor, call no model")
    args = ap.parse_args(argv)

    scenario = load_scenario(args.scenario)
    names = list(args.names)
    locked = apply_persona_lock(names)

    if args.experiment == "reanchor":
        system_prompt = render_blend(locked, weight=args.weight).prompt
        arms = [("no_anchor", False), ("with_anchor", True)]
    else:
        arms = [("lock_only", False), ("lock_plus_disclosure", True)]
        system_prompt = None  # per-arm below

    if args.dry_run:
        print("=== scenario:", args.scenario.name, f"({len(scenario.turns)} turns)")
        print("=== blend:", locked, "weight:", args.weight)
        if args.experiment == "reanchor":
            print("=== anchor block ===")
            print(render_reanchor(names, weight=args.weight))
        else:
            for label, disc in arms:
                p = render_blend(locked, weight=args.weight, disclosure=disc).prompt
                print(f"=== {label}: {len(p)} chars / ~{len(p)//4} tok")
        print("\nCAVEAT:", CAVEAT)
        return 0

    call_model = make_caller(args.provider, args.model)
    runs: list[dict] = []
    for rep in range(args.repeats):
        for label, flag in arms:
            if args.experiment == "reanchor":
                result = run_reanchor_arm(
                    scenario, system_prompt, call_model, locked, args.weight,
                    use_anchor=flag, band_floor=args.band_floor,
                )
                summary = _summarize(result["scores"], args.band_floor)
                summary["anchors_fired"] = len(result["anchors_fired_before_turn"])
            else:
                prompt = render_blend(locked, weight=args.weight, disclosure=flag).prompt
                result = run_disclosure_arm(
                    scenario, prompt, call_model, locked, args.weight
                )
                rep_obj = result["report"]
                summary = {
                    "mean": round(rep_obj.mean_score, 1),
                    "maintenance_rate": round(rep_obj.maintenance_rate, 3),
                    "lock_resistance": (
                        round(rep_obj.lock_resistance_rate, 3)
                        if rep_obj.lock_resistance_rate is not None
                        else None
                    ),
                    "injection_chars": len(prompt),
                }
            print(f"[rep {rep + 1}] {label}: {json.dumps(summary, ensure_ascii=False)}")
            runs.append({"repeat": rep + 1, "arm": label, "summary": summary,
                         "detail": {k: v for k, v in result.items() if k != "report"}})

    args.out_dir.mkdir(parents=True, exist_ok=True)
    stamp = date.today().isoformat()
    out = args.out_dir / f"{stamp}-{args.experiment}-{args.model}.json"
    out.write_text(json.dumps({
        "hersona_version": hersona_version,
        "experiment": args.experiment,
        "provider": args.provider,
        "model": args.model,
        "names": locked,
        "weight": args.weight,
        "scenario": args.scenario.name,
        "band_floor": args.band_floor,
        "caveat": CAVEAT,
        "runs": runs,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nwrote {out}")
    print("CAVEAT:", CAVEAT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
