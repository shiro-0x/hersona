#!/usr/bin/env python3
"""Official hersona-vs-baseline comparison runner (docs/BENCHMARKS.md).

Runs each scenario's user turns against a real model under up to four
conditions, saves one bench-compatible transcript per condition, and
(with --score) writes a comparison.md / comparison.json report:

    a       system prompt = hersona blend injection block
    a_lock  same blend with personality/persona_lock appended
    b       hand-written baseline persona prompt (--baseline-file)
    c       no persona instructions at all

Design constraints (mirrors docs/IMPROVEMENT_PLAN_2026-07-10 §A-2):
- This script is the ONLY place that calls an LLM. The hersona package
  itself never does; this file lives outside the package and outside the
  wheel, and uses only the standard library (urllib) — no SDK deps.
- Scoring is delegated to hersona.core.bench (deterministic, reproducible).
- Bad numbers are published as-is (docs/BENCHMARKS.md convention).

Usage:
    python benchmarks/run_comparison.py \
        --provider ollama --model llama3.1 \
        --names tsundere keigo --weight moderate \
        --scenarios benchmarks/scenarios/persona_override_attack_ja.yaml \
        --conditions a,a_lock,c --score

API keys come from env vars: ANTHROPIC_API_KEY / OPENAI_API_KEY /
GEMINI_API_KEY. ollama needs a local server (OLLAMA_HOST, default
http://localhost:11434).

No API key at all? Two paths:
- --provider ollama: a local ollama server has no auth to begin with.
- --provider claude_cli: drives the `claude` CLI (Claude Code) headless via
  subprocess, so a `claude login` subscription session is the credential —
  no ANTHROPIC_API_KEY needed. Turns run as `claude -p --output-format json`
  with `--system-prompt` (the injection block) and `--resume <session-id>`
  for multi-turn state. Caveats (also rendered into comparison.md): the CLI
  harness is not the raw API (tool definitions are present; `--max-turns 1`
  suppresses agentic tool loops), latencies include CLI startup, and
  `--max-tokens` is not supported. Rows from claude_cli should not be
  compared 1:1 against raw-API rows.
"""
from __future__ import annotations

import argparse
import json
import os
import shlex
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from datetime import date
from pathlib import Path

from hersona import __version__ as hersona_version
from hersona.core.attach import render_blend
from hersona.core.bench import (
    BenchScenario,
    estimate_token_cost,
    load_scenario,
    score_transcript,
)
from hersona.core.persona_lock import apply_persona_lock

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SCENARIOS_DIR = Path(__file__).resolve().parent / "scenarios"
DEFAULT_OUT_DIR = Path(__file__).resolve().parent / "results"

Message = dict[str, str]  # {"role": "user"|"assistant", "content": str}
#: (system_prompt, messages) -> assistant reply text
CallModel = Callable[[str, list[Message]], str]

CONDITIONS = ("a", "a_lock", "a_humanize", "b", "c")

# --- HTTP (stdlib only, injectable opener for tests) ----------------------


def _http_post_json(
    url: str,
    headers: dict[str, str],
    body: dict,
    *,
    timeout: float = 120.0,
    opener: Callable[..., object] | None = None,
) -> dict:
    """POST JSON, return parsed JSON. Retries 429/5xx twice with backoff."""
    open_fn = opener or urllib.request.urlopen
    payload = json.dumps(body).encode("utf-8")
    last_err: Exception | None = None
    for attempt in range(3):
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json", **headers},
            method="POST",
        )
        try:
            with open_fn(req, timeout=timeout) as resp:  # type: ignore[call-arg]
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            last_err = e
            if e.code not in (429, 500, 502, 503, 529):
                raise
        except urllib.error.URLError as e:
            last_err = e
        time.sleep(2.0 * (attempt + 1))
    raise RuntimeError(f"request to {url} failed after retries: {last_err}")


# --- Provider request builders / response parsers (pure, unit-testable) ---


def _anthropic_request(model: str, system: str, messages: list[Message], max_tokens: int):
    body: dict = {"model": model, "max_tokens": max_tokens, "messages": messages}
    if system:
        body["system"] = system
    headers = {
        "x-api-key": os.environ.get("ANTHROPIC_API_KEY", ""),
        "anthropic-version": "2023-06-01",
    }
    return "https://api.anthropic.com/v1/messages", headers, body


def _anthropic_parse(resp: dict) -> str:
    return "".join(b.get("text", "") for b in resp.get("content", []))


def _openai_request(model: str, system: str, messages: list[Message], max_tokens: int):
    msgs = ([{"role": "system", "content": system}] if system else []) + messages
    body = {"model": model, "max_tokens": max_tokens, "messages": msgs}
    headers = {"Authorization": f"Bearer {os.environ.get('OPENAI_API_KEY', '')}"}
    return "https://api.openai.com/v1/chat/completions", headers, body


def _openai_parse(resp: dict) -> str:
    return resp["choices"][0]["message"]["content"] or ""


def _gemini_request(model: str, system: str, messages: list[Message], max_tokens: int):
    contents = [
        {"role": "user" if m["role"] == "user" else "model", "parts": [{"text": m["content"]}]}
        for m in messages
    ]
    body: dict = {
        "contents": contents,
        "generationConfig": {"maxOutputTokens": max_tokens},
    }
    if system:
        body["system_instruction"] = {"parts": [{"text": system}]}
    headers = {"x-goog-api-key": os.environ.get("GEMINI_API_KEY", "")}
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    return url, headers, body


def _gemini_parse(resp: dict) -> str:
    parts = resp["candidates"][0]["content"].get("parts", [])
    return "".join(p.get("text", "") for p in parts)


def _ollama_request(model: str, system: str, messages: list[Message], max_tokens: int):
    msgs = ([{"role": "system", "content": system}] if system else []) + messages
    body = {"model": model, "messages": msgs, "stream": False,
            "options": {"num_predict": max_tokens}}
    host = os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
    return f"{host}/api/chat", {}, body


def _ollama_parse(resp: dict) -> str:
    return resp["message"]["content"]


def _minimax_request(model: str, system: str, messages: list[Message], max_tokens: int):
    # MiniMax API is OpenAI-compatible (https://api.minimax.io/v1/chat/completions).
    # The model name can also be overridden by the MINIMAX_MODEL env var,
    # matching how project-sona wires it (packages/llm/src/chat.ts).
    actual_model = os.environ.get("MINIMAX_MODEL", model)
    msgs = ([{"role": "system", "content": system}] if system else []) + messages
    body = {
        "model": actual_model,
        "max_tokens": max_tokens,
        "temperature": 0.8,
        "messages": msgs,
    }
    headers = {"Authorization": f"Bearer {os.environ.get('MINIMAX_API_KEY', '')}"}
    return "https://api.minimax.io/v1/chat/completions", headers, body


def _strip_think_blocks(text: str) -> str:
    """Remove `<think>...</think>` blocks (non-greedy, multiline).

    Mirrors the helper in project-sona's packages/llm/src/chat.ts but
    inlined here to keep this script stdlib-only and avoid cross-package
    coupling for one regex.
    """
    import re
    cleaned = re.sub(r"<think>[\s\S]*?</think>", "", text)
    return cleaned.replace("\n\n\n", "\n\n").strip()


def _minimax_parse(resp: dict) -> str:
    # OpenAI-compatible shape. MiniMax-M3 / M2 reasoning models wrap their
    # reasoning in a `<think>...</think>` block at the start of `content`.
    # Strip it so scoring only sees the user-facing reply (keeps the
    # measurement fair across providers — surface text only).
    content = resp["choices"][0]["message"]["content"] or ""
    return _strip_think_blocks(content)


#: provider -> (request builder, response parser, required env var or None)
PROVIDERS = {
    "anthropic": (_anthropic_request, _anthropic_parse, "ANTHROPIC_API_KEY"),
    "openai": (_openai_request, _openai_parse, "OPENAI_API_KEY"),
    "gemini": (_gemini_request, _gemini_parse, "GEMINI_API_KEY"),
    "ollama": (_ollama_request, _ollama_parse, None),
    "minimax": (_minimax_request, _minimax_parse, "MINIMAX_API_KEY"),
}

# --- CLI providers (subscription auth via `claude login`, no API key) -------

#: providers driven through a local CLI subprocess instead of HTTP
CLI_PROVIDERS = ("claude_cli",)

#: (argv, stdin text) -> stdout text
RunCli = Callable[[list[str], str], str]

_CLI_TURN_TIMEOUT = 600.0


def _claude_cli_bin() -> str:
    return os.environ.get("CLAUDE_CLI_BIN", "claude")


def _claude_cli_args(model: str, system: str, session_id: str | None) -> list[str]:
    """argv for one `claude -p` turn (prompt is passed via stdin, not argv).

    - --system-prompt REPLACES the Claude Code default system prompt with the
      condition's prompt (empty string for condition c), so the persona
      injection is the whole system prompt — same contract as the HTTP
      providers.
    - --max-turns 1 keeps the run to a single model response (no agentic
      tool loop); a turn where the model chose a tool call instead of text
      scores as an empty reply, which is published as-is.
    - --resume threads the conversation state across turns; the session id
      comes from the previous turn's JSON output.
    """
    argv = [
        _claude_cli_bin(), "-p",
        "--output-format", "json",
        "--model", model,
        "--max-turns", "1",
        "--system-prompt", system,
    ]
    if session_id:
        argv += ["--resume", session_id]
    return argv


def _claude_cli_parse(stdout: str) -> tuple[str, str | None]:
    """Parse `claude -p --output-format json` output -> (reply text, session id)."""
    data = json.loads(stdout)
    if data.get("is_error"):
        detail = data.get("result") or data.get("subtype") or "unknown error"
        raise RuntimeError(f"claude CLI returned an error result: {detail}")
    return str(data.get("result") or ""), data.get("session_id")


def _run_cli(argv: list[str], stdin_text: str) -> str:
    """Run a CLI turn via subprocess (stdlib only; prompt on stdin).

    cwd is pinned to the system temp dir so `claude -p` does NOT pick up
    this repo's CLAUDE.md as project memory (which would contaminate the
    measured system prompt). Sessions are stored per cwd, so a fixed cwd
    also keeps --resume lookups consistent across turns. The user-level
    ~/.claude/CLAUDE.md still applies — see docs/BENCHMARKS.md caveats.
    """
    import subprocess
    import tempfile
    try:
        proc = subprocess.run(
            argv,
            input=stdin_text,
            capture_output=True,
            text=True,
            timeout=_CLI_TURN_TIMEOUT,
            cwd=tempfile.gettempdir(),
        )
    except FileNotFoundError:
        raise RuntimeError(
            f"claude CLI not found ({argv[0]}). Install Claude Code, run "
            "`claude login` (subscription auth), or point CLAUDE_CLI_BIN at "
            "the binary."
        ) from None
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout).strip()[-500:]
        raise RuntimeError(f"claude CLI exited {proc.returncode}: {tail}")
    return proc.stdout


def make_claude_cli_caller(model: str, *, runner: RunCli | None = None) -> CallModel:
    """CallModel backed by the `claude` CLI instead of an HTTP API.

    Conversation state lives in the CLI session (--resume), not in the
    message list: only the newest user turn is sent per invocation. A fresh
    conversation is detected by `len(messages) == 1` (run_scenario starts
    every condition run with a new message list), which resets the session.
    """
    run = runner or _run_cli
    state: dict[str, str | None] = {"session_id": None}

    def call_model(system: str, messages: list[Message]) -> str:
        if len(messages) == 1:
            state["session_id"] = None
        last = messages[-1]
        if last["role"] != "user":
            raise ValueError("claude_cli caller expects the newest message to be a user turn")
        stdout = run(_claude_cli_args(model, system, state["session_id"]), last["content"])
        text, session_id = _claude_cli_parse(stdout)
        if session_id:
            state["session_id"] = session_id
        return text

    return call_model


def make_caller(
    provider: str,
    model: str,
    *,
    max_tokens: int = 1024,
    opener: Callable[..., object] | None = None,
    cli_runner: RunCli | None = None,
) -> CallModel:
    if provider in CLI_PROVIDERS:
        # max_tokens is not supported by the claude CLI; ignored by design.
        return make_claude_cli_caller(model, runner=cli_runner)
    build, parse, _env = PROVIDERS[provider]

    def call_model(system: str, messages: list[Message]) -> str:
        url, headers, body = build(model, system, messages, max_tokens)
        return parse(_http_post_json(url, headers, body, opener=opener))

    return call_model


# --- Transcript generation -------------------------------------------------


def run_scenario(
    scenario: BenchScenario,
    system_prompt: str,
    call_model: CallModel,
    *,
    sleep: float = 0.0,
) -> tuple[list[str], list[float]]:
    """Run every user turn through the model with a growing message list.

    Persona drift over turns is the phenomenon under measurement, so the
    conversation accumulates (one message list per condition run).
    Returns (transcript, per-turn latency seconds).
    """
    messages: list[Message] = []
    transcript: list[str] = []
    latencies: list[float] = []
    for turn in scenario.turns:
        messages.append({"role": "user", "content": turn})
        t0 = time.monotonic()
        reply = call_model(system_prompt, messages)
        latencies.append(time.monotonic() - t0)
        messages.append({"role": "assistant", "content": reply})
        transcript.append(reply)
        if sleep:
            time.sleep(sleep)
    return transcript, latencies


def build_condition_prompts(
    names: list[str],
    weight: str,
    baseline_file: Path | None,
    conditions: list[str],
) -> dict[str, str]:
    """Return {condition: system prompt} for the requested conditions."""
    prompts: dict[str, str] = {}
    if "a" in conditions:
        prompts["a"] = render_blend(names, weight=weight).prompt
    if "a_lock" in conditions:
        prompts["a_lock"] = render_blend(apply_persona_lock(names), weight=weight).prompt
    if "a_humanize" in conditions:
        # P3 of docs/IMPROVEMENT_PLAN_2026-07-11_humanize.md: same blend with
        # --humanize on, so the response_style_directive appends the §3 P2a
        # humanize section. The persona_lock (a_lock vs a_humanize) is
        # intentionally NOT applied here so we measure the humanize effect
        # in isolation. To stack both, callers can use a_lock on top
        # (future work) or run two separate conditions.
        prompts["a_humanize"] = render_blend(
            names, weight=weight, humanize=True
        ).prompt
    if "b" in conditions:
        if baseline_file is None:
            raise ValueError("condition 'b' requires --baseline-file")
        prompts["b"] = baseline_file.read_text(encoding="utf-8")
    if "c" in conditions:
        prompts["c"] = ""
    return prompts


def _condition_names(names: list[str], condition: str) -> list[str]:
    """Blend names to score a condition's transcript against."""
    if condition == "a_lock":
        return apply_persona_lock(names)
    # a_humanize uses the same blend names as a (no persona_lock applied),
    # because P3 measures the humanize effect in isolation.
    return list(names)


# --- Scoring / report -------------------------------------------------------


def score_conditions(
    names: list[str],
    weight: str,
    scenario: BenchScenario,
    transcripts: dict[str, list[str]],
    prompts: dict[str, str],
    latencies: dict[str, list[float]] | None = None,
) -> dict:
    """Score every condition's transcript; return one report row set per condition."""
    rows: dict[str, dict] = {}
    for condition, transcript in transcripts.items():
        result = score_transcript(
            _condition_names(names, condition),
            transcript,
            weight=weight,
            scenario_id=scenario.id,
            attack_turns=scenario.attack_turns,
        )
        if condition in ("a", "a_lock"):
            cost = estimate_token_cost(_condition_names(names, condition), weight=weight)
            chars, tokens = cost.chars, cost.approx_tokens
        else:
            chars = len(prompts.get(condition, ""))
            tokens = chars // 4
        lat = (latencies or {}).get(condition) or []
        rows[condition] = {
            "maintenance_rate": result.maintenance_rate,
            "mean_score": result.mean_score,
            "lock_resistance_rate": result.lock_resistance_rate,
            "decay": result.decay,
            "injection_chars": chars,
            "injection_approx_tokens": tokens,
            "mean_latency_s": (sum(lat) / len(lat)) if lat else None,
        }
    return rows


def _fmt_pct(value: float | None) -> str:
    return "—" if value is None else f"{value * 100:.0f}%"


def _fmt_num(value: float | None, suffix: str = "") -> str:
    return "—" if value is None else f"{value:.1f}{suffix}"


def render_markdown(report: dict) -> str:
    """Render the comparison report as the markdown table BENCHMARKS.md embeds."""
    meta = report["meta"]
    lines = [
        "# hersona comparison run",
        "",
        f"- date: {meta['date']}",
        *(
            [f"- rescored: {meta['rescored']} (hersona v{meta['hersona_version']} metric)"]
            if meta.get("rescored")
            else []
        ),
        f"- provider / model: {meta['provider']} / {meta['model']}",
        *(
            [
                "- note: generated through the provider's CLI under subscription "
                "auth — the CLI harness is not the raw API (tool definitions "
                "present; latencies include CLI startup). Do not compare these "
                "rows 1:1 against raw-API rows."
            ]
            if meta["provider"] in CLI_PROVIDERS
            else []
        ),
        f"- hersona: v{meta['hersona_version']}",
        f"- blend: {' + '.join(meta['names'])} (weight: {meta['weight']})",
        f"- reproduce: `{meta['command']}`",
        "",
    ]
    for scenario_id, rows in report["scenarios"].items():
        lines.append(f"## {scenario_id}")
        lines.append("")
        lines.append("| Condition | Maintenance | Mean | Lock resistance | Injection cost | Mean latency |")
        lines.append("|---|---:|---:|---:|---:|---:|")
        for condition, row in rows.items():
            lines.append(
                f"| {condition} "
                f"| {_fmt_pct(row['maintenance_rate'])} "
                f"| {_fmt_num(row['mean_score'])} "
                f"| {_fmt_pct(row['lock_resistance_rate'])} "
                f"| {row['injection_chars']} chars (~{row['injection_approx_tokens']} tok) "
                f"| {_fmt_num(row['mean_latency_s'], 's')} |"
            )
        lines.append("")
    lines += [
        "---",
        "",
        "Scoring is the surface-level deterministic scorer of `hersona bench`",
        "(sentence-ending match + catchphrase density) — it measures voice, not",
        "answer quality. Numbers are specific to this model and date. Bad numbers",
        "are published as-is.",
        "",
    ]
    return "\n".join(lines)


def write_reports(out_dir: Path, report: dict) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "comparison.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out_dir / "comparison.md").write_text(render_markdown(report), encoding="utf-8")


def _rescore(
    args: argparse.Namespace,
    conditions: list[str],
    scenarios: list[BenchScenario],
    prompts: dict[str, str],
) -> int:
    """既存トランスクリプトを LLM 呼び出しなしで再採点する (--rescore DIR)。

    採点メトリクスが変わったとき (例: metric v2, 2026-07-12)、凍結済みの
    transcript JSON はそのままに comparison.md / comparison.json だけを
    再生成する。元の comparison.json があれば provider / model / 実行日と
    条件別 mean_latency_s を引き継ぐ (レイテンシは再採点で変わらないため)。
    """
    out_dir: Path = args.rescore
    old_meta: dict = {}
    old_rows: dict = {}
    cmp_path = out_dir / "comparison.json"
    if cmp_path.exists():
        old = json.loads(cmp_path.read_text(encoding="utf-8"))
        old_meta = old.get("meta", {})
        old_rows = old.get("scenarios", {})

    report: dict = {
        "meta": {
            "date": old_meta.get("date", date.today().isoformat()),
            "rescored": date.today().isoformat(),
            "provider": args.provider or old_meta.get("provider", "?"),
            "model": args.model or old_meta.get("model", "?"),
            "hersona_version": hersona_version,
            "names": args.names,
            "weight": args.weight,
            "command": shlex.join([Path(sys.argv[0]).name, *sys.argv[1:]]),
        },
        "scenarios": {},
    }
    for scenario in scenarios:
        transcripts: dict[str, list[str]] = {}
        for condition in conditions:
            f = out_dir / f"{scenario.id}__{condition}.json"
            if not f.exists():
                print(f"error: transcript not found: {f}", file=sys.stderr)
                return 2
            transcripts[condition] = json.loads(f.read_text(encoding="utf-8"))
        rows = score_conditions(args.names, args.weight, scenario, transcripts, prompts)
        for condition, row in rows.items():
            old_row = (old_rows.get(scenario.id) or {}).get(condition) or {}
            row["mean_latency_s"] = old_row.get("mean_latency_s")
        report["scenarios"][scenario.id] = rows
    write_reports(out_dir, report)
    print(f"report -> {out_dir / 'comparison.md'}", file=sys.stderr)
    return 0


# --- CLI --------------------------------------------------------------------


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Run hersona-vs-baseline comparisons against a real model "
        "and score them with hersona bench (see docs/BENCHMARKS.md)."
    )
    p.add_argument("--provider", choices=sorted([*PROVIDERS, *CLI_PROVIDERS]),
                   help="required unless --rescore; claude_cli needs no API key "
                        "(uses the `claude login` subscription session)")
    p.add_argument("--model", help="model name, e.g. llama3.1 / gpt-4o "
                                   "(required unless --rescore)")
    p.add_argument("--names", required=True, nargs="+", help="blend attribute names")
    p.add_argument("--weight", default="moderate",
                   choices=["none", "mild", "moderate", "strong"])
    p.add_argument("--scenarios", nargs="*", type=Path,
                   help=f"scenario YAMLs (default: all in {DEFAULT_SCENARIOS_DIR})")
    p.add_argument("--conditions", default="a,c",
                   help=f"comma-separated subset of {','.join(CONDITIONS)} (default: a,c)")
    p.add_argument("--baseline-file", type=Path,
                   help="hand-written persona prompt for condition b")
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    p.add_argument("--score", action="store_true",
                   help="also score transcripts and write comparison.md / comparison.json")
    p.add_argument("--rescore", type=Path, metavar="DIR",
                   help="re-score existing <scenario>__<condition>.json transcripts "
                        "in DIR without any LLM call (metric changes re-use frozen "
                        "transcripts); writes comparison.md / comparison.json to DIR")
    p.add_argument("--max-tokens", type=int, default=1024)
    p.add_argument("--sleep", type=float, default=0.0,
                   help="seconds to sleep between turns (rate limits)")
    p.add_argument("--dry-run", action="store_true",
                   help="print planned calls and prompts without any HTTP request")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    conditions = [c.strip() for c in args.conditions.split(",") if c.strip()]
    unknown = [c for c in conditions if c not in CONDITIONS]
    if unknown:
        print(f"error: unknown condition(s): {', '.join(unknown)}", file=sys.stderr)
        return 2
    if "b" in conditions and args.baseline_file is None:
        print("error: condition 'b' requires --baseline-file", file=sys.stderr)
        return 2
    if args.rescore is None:
        if not args.provider or not args.model:
            print("error: --provider and --model are required unless --rescore",
                  file=sys.stderr)
            return 2
        if args.provider in CLI_PROVIDERS:
            import shutil
            if not args.dry_run and shutil.which(_claude_cli_bin()) is None:
                print(
                    f"error: claude CLI not found ({_claude_cli_bin()}). Install "
                    "Claude Code and run `claude login`, or set CLAUDE_CLI_BIN.",
                    file=sys.stderr,
                )
                return 2
        else:
            _build, _parse, env_var = PROVIDERS[args.provider]
            if env_var and not os.environ.get(env_var) and not args.dry_run:
                print(f"error: {env_var} is not set (required for --provider {args.provider})",
                      file=sys.stderr)
                return 2

    scenario_paths = args.scenarios or sorted(DEFAULT_SCENARIOS_DIR.glob("*.yaml"))
    scenarios = [load_scenario(p) for p in scenario_paths]
    prompts = build_condition_prompts(args.names, args.weight, args.baseline_file, conditions)

    if args.rescore is not None:
        return _rescore(args, conditions, scenarios, prompts)

    if args.dry_run:
        print(f"provider={args.provider} model={args.model} weight={args.weight}")
        for scenario in scenarios:
            print(f"scenario {scenario.id}: {len(scenario.turns)} turns "
                  f"(attack: {list(scenario.attack_turns) or 'none'})")
        for condition, prompt in prompts.items():
            print(f"--- condition {condition}: system prompt {len(prompt)} chars ---")
        return 0

    caller = make_caller(args.provider, args.model, max_tokens=args.max_tokens)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    report: dict = {
        "meta": {
            "date": date.today().isoformat(),
            "provider": args.provider,
            "model": args.model,
            "hersona_version": hersona_version,
            "names": args.names,
            "weight": args.weight,
            "command": shlex.join([Path(sys.argv[0]).name, *sys.argv[1:]]),
        },
        "scenarios": {},
    }
    for scenario in scenarios:
        transcripts: dict[str, list[str]] = {}
        latencies: dict[str, list[float]] = {}
        for condition in conditions:
            print(f"[{scenario.id}] condition {condition}: {len(scenario.turns)} turns ...",
                  file=sys.stderr)
            transcript, lat = run_scenario(
                scenario, prompts[condition], caller, sleep=args.sleep
            )
            transcripts[condition] = transcript
            latencies[condition] = lat
            out = args.out_dir / f"{scenario.id}__{condition}.json"
            out.write_text(
                json.dumps(transcript, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            print(f"  -> {out}", file=sys.stderr)
        if args.score:
            report["scenarios"][scenario.id] = score_conditions(
                args.names, args.weight, scenario, transcripts, prompts, latencies
            )

    if args.score:
        write_reports(args.out_dir, report)
        print(f"report -> {args.out_dir / 'comparison.md'}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
