"""benchmarks/run_comparison.py (A-2 provider execution path) のオフラインテスト。

HTTP は一切呼ばない。call_model / opener を注入できる構造 (hersona.core.update の
opener パターンと同型) を利用し、トランスクリプト生成ループ・条件プロンプト構築・
プロバイダのリクエスト整形・レポート整形を検証する。
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from hersona.core.attach import render_blend
from hersona.core.bench import BenchScenario, score_transcript

REPO_ROOT = Path(__file__).resolve().parent.parent

# benchmarks/ はパッケージではないのでファイルパスから直接ロードする。
_spec = importlib.util.spec_from_file_location(
    "run_comparison", REPO_ROOT / "benchmarks" / "run_comparison.py"
)
run_comparison = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(run_comparison)


_SCENARIO = BenchScenario(
    id="unit", turns=["hello", "attack now", "bye"], attack_turns=(1,)
)


def test_run_scenario_grows_message_list() -> None:
    seen: list[int] = []

    def fake_call(system: str, messages: list[dict]) -> str:
        seen.append(len(messages))
        assert messages[-1]["role"] == "user"
        return f"reply-{len(seen)}"

    transcript, latencies = run_comparison.run_scenario(_SCENARIO, "sys", fake_call)
    # ターン i の呼び出し時には user/assistant が交互に積まれた 2i+1 件が見える
    assert seen == [1, 3, 5]
    assert transcript == ["reply-1", "reply-2", "reply-3"]
    assert len(latencies) == 3


def test_build_condition_prompts_a_and_c() -> None:
    prompts = run_comparison.build_condition_prompts(
        ["tsundere", "keigo"], "moderate", None, ["a", "c"]
    )
    assert prompts["a"] == render_blend(["tsundere", "keigo"], weight="moderate").prompt
    assert prompts["c"] == ""


def test_build_condition_prompts_a_lock_appends_persona_lock() -> None:
    prompts = run_comparison.build_condition_prompts(
        ["tsundere", "keigo"], "moderate", None, ["a", "a_lock"]
    )
    assert prompts["a_lock"] != prompts["a"]
    assert "persona_lock" in prompts["a_lock"]


def test_build_condition_prompts_a_humanize_uses_humanize_directive() -> None:
    prompts = run_comparison.build_condition_prompts(
        ["tsundere", "keigo"], "moderate", None, ["a", "a_humanize"]
    )
    assert prompts["a_humanize"] != prompts["a"]
    assert prompts["a_humanize"] == render_blend(
        ["tsundere", "keigo"], weight="moderate", humanize=True
    ).prompt
    # a_humanize measures the humanize effect in isolation: no persona_lock applied.
    assert "persona_lock" not in prompts["a_humanize"]


def test_condition_names_a_humanize_omits_persona_lock() -> None:
    assert run_comparison._condition_names(["tsundere"], "a_humanize") == ["tsundere"]
    assert run_comparison._condition_names(["tsundere"], "a_lock") != ["tsundere"]


def test_condition_b_requires_baseline_file() -> None:
    with pytest.raises(ValueError):
        run_comparison.build_condition_prompts(["tsundere"], "moderate", None, ["b"])
    assert run_comparison.main(
        ["--provider", "ollama", "--model", "m", "--names", "tsundere",
         "--conditions", "b", "--dry-run"]
    ) == 2


def test_main_rejects_unknown_condition() -> None:
    assert run_comparison.main(
        ["--provider", "ollama", "--model", "m", "--names", "tsundere",
         "--conditions", "z", "--dry-run"]
    ) == 2


@pytest.mark.parametrize("provider", ["anthropic", "openai", "gemini", "ollama"])
def test_provider_request_builders_shapes(provider: str) -> None:
    build, parse, _env = run_comparison.PROVIDERS[provider]
    messages = [{"role": "user", "content": "hi"}]
    url, headers, body = build("some-model", "SYSTEM", messages, 128)
    assert url.startswith("http")
    if provider == "anthropic":
        assert "x-api-key" in headers
        assert body["system"] == "SYSTEM"
        assert body["messages"] == messages
        assert parse({"content": [{"type": "text", "text": "ok"}]}) == "ok"
    elif provider == "openai":
        assert headers["Authorization"].startswith("Bearer")
        assert body["messages"][0] == {"role": "system", "content": "SYSTEM"}
        assert parse({"choices": [{"message": {"content": "ok"}}]}) == "ok"
    elif provider == "gemini":
        assert "x-goog-api-key" in headers
        assert body["system_instruction"] == {"parts": [{"text": "SYSTEM"}]}
        assert body["contents"][0]["role"] == "user"
        assert parse(
            {"candidates": [{"content": {"parts": [{"text": "ok"}]}}]}
        ) == "ok"
    else:  # ollama
        assert body["stream"] is False
        assert body["messages"][0] == {"role": "system", "content": "SYSTEM"}
        assert parse({"message": {"content": "ok"}}) == "ok"


@pytest.mark.parametrize("provider", ["anthropic", "openai", "gemini", "ollama"])
def test_provider_builders_omit_empty_system(provider: str) -> None:
    build, _parse, _env = run_comparison.PROVIDERS[provider]
    _url, _headers, body = build("m", "", [{"role": "user", "content": "hi"}], 64)
    if provider == "anthropic":
        assert "system" not in body
    elif provider == "gemini":
        assert "system_instruction" not in body
    else:
        assert all(m["role"] != "system" for m in body["messages"])


def test_saved_transcript_is_bench_compatible(tmp_path: Path) -> None:
    transcript, _ = run_comparison.run_scenario(
        _SCENARIO, "", lambda s, m: "べ、別にいいけど。"
    )
    out = tmp_path / "t.json"
    out.write_text(json.dumps(transcript, ensure_ascii=False), encoding="utf-8")
    loaded = json.loads(out.read_text(encoding="utf-8"))
    result = score_transcript(
        ["tsundere", "keigo"], loaded, weight="moderate",
        scenario_id=_SCENARIO.id, attack_turns=_SCENARIO.attack_turns,
    )
    assert result.scenario_id == "unit"
    assert result.lock_resistance_rate is not None


def test_comparison_markdown_contains_metadata_and_lock_column() -> None:
    prompts = {"a": "PROMPT", "c": ""}
    transcripts = {
        "a": ["べ、別にいいけど。"] * 3,
        "c": ["Sure, here is the answer."] * 3,
    }
    rows = run_comparison.score_conditions(
        ["tsundere", "keigo"], "moderate", _SCENARIO, transcripts, prompts
    )
    report = {
        "meta": {
            "date": "2026-07-10", "provider": "ollama", "model": "test-model",
            "hersona_version": "0.0.0", "names": ["tsundere", "keigo"],
            "weight": "moderate", "command": "python run_comparison.py ...",
        },
        "scenarios": {"unit": rows},
    }
    md = run_comparison.render_markdown(report)
    assert "test-model" in md
    assert "reproduce" in md
    assert "| a |" in md and "| c |" in md
    assert "Lock resistance" in md
    # 条件 c の注入コストは 0 chars
    assert rows["c"]["injection_chars"] == 0


def test_dry_run_makes_no_http_calls(capsys) -> None:
    # dry-run は API キー無しでも通り、HTTP を一切呼ばない (呼べば urlopen が落ちる
    # 環境でも成功することで担保)。
    rc = run_comparison.main(
        ["--provider", "anthropic", "--model", "claude-x", "--names", "tsundere",
         "--conditions", "a,c", "--dry-run"]
    )
    assert rc == 0
    out = capsys.readouterr().out
    assert "condition a" in out and "condition c" in out


def test_rescore_regenerates_reports_offline(tmp_path: Path) -> None:
    """--rescore は既存 transcript JSON だけから comparison.md/json を再生成する。

    LLM 呼び出しなし (API キー env 不要で成功することで担保)。旧 comparison.json
    があれば provider/model/date と mean_latency_s を引き継ぐ。
    """
    scenario_yaml = tmp_path / "unit.yaml"
    scenario_yaml.write_text(
        "id: unit\nturns:\n  - hello\n  - text: attack now\n    attack: true\n  - bye\n",
        encoding="utf-8",
    )
    (tmp_path / "unit__a.json").write_text(
        json.dumps(["べ、別にいいけど。"] * 3, ensure_ascii=False), encoding="utf-8"
    )
    (tmp_path / "unit__c.json").write_text(
        json.dumps(["Sure, here is the answer."] * 3), encoding="utf-8"
    )
    (tmp_path / "comparison.json").write_text(
        json.dumps({
            "meta": {"date": "2026-07-11", "provider": "minimax", "model": "M3"},
            "scenarios": {"unit": {"a": {"mean_latency_s": 1.5}}},
        }),
        encoding="utf-8",
    )
    rc = run_comparison.main([
        "--rescore", str(tmp_path),
        "--names", "tsundere", "keigo", "--weight", "moderate",
        "--scenarios", str(scenario_yaml), "--conditions", "a,c",
    ])
    assert rc == 0
    report = json.loads((tmp_path / "comparison.json").read_text(encoding="utf-8"))
    assert report["meta"]["provider"] == "minimax"
    assert report["meta"]["date"] == "2026-07-11"
    assert report["meta"]["rescored"]
    assert report["scenarios"]["unit"]["a"]["mean_latency_s"] == 1.5
    assert report["scenarios"]["unit"]["c"]["mean_latency_s"] is None
    md = (tmp_path / "comparison.md").read_text(encoding="utf-8")
    assert "rescored" in md
    assert "| a |" in md and "| c |" in md


def test_rescore_missing_transcript_errors(tmp_path: Path, capsys) -> None:
    scenario_yaml = tmp_path / "unit.yaml"
    scenario_yaml.write_text("id: unit\nturns:\n  - hello\n", encoding="utf-8")
    rc = run_comparison.main([
        "--rescore", str(tmp_path),
        "--names", "tsundere", "--weight", "moderate",
        "--scenarios", str(scenario_yaml), "--conditions", "a",
    ])
    assert rc == 2
    assert "transcript not found" in capsys.readouterr().err


def test_provider_and_model_required_without_rescore(capsys) -> None:
    rc = run_comparison.main(["--names", "tsundere", "--conditions", "c"])
    assert rc == 2
    assert "--provider and --model are required" in capsys.readouterr().err


# --- claude_cli provider (subscription auth, subprocess — all offline) ------


def _cli_json(text: str, session_id: str = "sess-1", **extra) -> str:
    return json.dumps({"result": text, "session_id": session_id,
                       "is_error": False, **extra})


def test_claude_cli_args_first_turn_vs_resume() -> None:
    first = run_comparison._claude_cli_args("claude-x", "SYSTEM", None)
    assert first[0] == "claude" and "-p" in first
    assert first[first.index("--output-format") + 1] == "json"
    assert first[first.index("--model") + 1] == "claude-x"
    assert first[first.index("--max-turns") + 1] == "1"
    assert first[first.index("--system-prompt") + 1] == "SYSTEM"
    assert "--resume" not in first

    resumed = run_comparison._claude_cli_args("claude-x", "SYSTEM", "sess-9")
    assert resumed[resumed.index("--resume") + 1] == "sess-9"


def test_claude_cli_args_keeps_empty_system_prompt_explicit() -> None:
    # 条件 c (ペルソナなし) でも --system-prompt "" を明示し、Claude Code の
    # 既定システムプロンプトが測定に混入しないようにする。
    argv = run_comparison._claude_cli_args("m", "", None)
    assert argv[argv.index("--system-prompt") + 1] == ""


def test_claude_cli_args_respects_bin_override(monkeypatch) -> None:
    monkeypatch.setenv("CLAUDE_CLI_BIN", "/opt/claude/bin/claude")
    argv = run_comparison._claude_cli_args("m", "s", None)
    assert argv[0] == "/opt/claude/bin/claude"


def test_claude_cli_parse_success_and_error() -> None:
    text, sid = run_comparison._claude_cli_parse(_cli_json("べ、別にいいけど。"))
    assert text == "べ、別にいいけど。"
    assert sid == "sess-1"
    with pytest.raises(RuntimeError, match="error result"):
        run_comparison._claude_cli_parse(
            json.dumps({"is_error": True, "subtype": "error_max_turns"})
        )


def test_claude_cli_caller_threads_session_and_sends_only_last_turn() -> None:
    calls: list[tuple[list[str], str]] = []

    def fake_runner(argv: list[str], stdin_text: str) -> str:
        calls.append((argv, stdin_text))
        return _cli_json(f"reply-{len(calls)}", session_id=f"sess-{len(calls)}")

    caller = run_comparison.make_caller("claude_cli", "claude-x", cli_runner=fake_runner)
    transcript, latencies = run_comparison.run_scenario(_SCENARIO, "SYS", caller)

    assert transcript == ["reply-1", "reply-2", "reply-3"]
    assert len(latencies) == 3
    # 1 ターン目は新規セッション、以降は直前ターンの session_id で --resume する
    assert "--resume" not in calls[0][0]
    assert calls[1][0][calls[1][0].index("--resume") + 1] == "sess-1"
    assert calls[2][0][calls[2][0].index("--resume") + 1] == "sess-2"
    # 会話履歴は CLI セッション側にあるので、送るのは最新 user ターンだけ
    assert [stdin for _argv, stdin in calls] == list(_SCENARIO.turns)


def test_claude_cli_caller_resets_session_on_new_conversation() -> None:
    calls: list[list[str]] = []

    def fake_runner(argv: list[str], stdin_text: str) -> str:
        calls.append(argv)
        return _cli_json("ok", session_id="sess-A")

    caller = run_comparison.make_caller("claude_cli", "m", cli_runner=fake_runner)
    # 1 本目の会話 (2 ターン)
    run_comparison.run_scenario(
        BenchScenario(id="one", turns=["t1", "t2"]), "SYS", caller
    )
    # 2 本目の会話 — run_scenario は新しい message list で始まるので新規セッション
    run_comparison.run_scenario(BenchScenario(id="two", turns=["t1"]), "SYS", caller)
    assert "--resume" not in calls[0]
    assert "--resume" in calls[1]
    assert "--resume" not in calls[2]


def test_main_claude_cli_dry_run_needs_no_binary_or_key(capsys) -> None:
    rc = run_comparison.main(
        ["--provider", "claude_cli", "--model", "claude-x", "--names", "tsundere",
         "--conditions", "a,c", "--dry-run"]
    )
    assert rc == 0
    out = capsys.readouterr().out
    assert "condition a" in out and "condition c" in out


def test_main_claude_cli_missing_binary_errors(monkeypatch, capsys) -> None:
    monkeypatch.setenv("CLAUDE_CLI_BIN", "/nonexistent/claude-cli-for-test")
    rc = run_comparison.main(
        ["--provider", "claude_cli", "--model", "claude-x", "--names", "tsundere",
         "--conditions", "c"]
    )
    assert rc == 2
    assert "claude CLI not found" in capsys.readouterr().err


def test_render_markdown_notes_cli_harness_for_claude_cli() -> None:
    report = {
        "meta": {
            "date": "2026-07-14", "provider": "claude_cli", "model": "claude-x",
            "hersona_version": "0.0.0", "names": ["tsundere"],
            "weight": "moderate", "command": "python run_comparison.py ...",
        },
        "scenarios": {},
    }
    md = run_comparison.render_markdown(report)
    assert "subscription auth" in md
    # HTTP プロバイダには注記を出さない
    report["meta"]["provider"] = "ollama"
    assert "subscription auth" not in run_comparison.render_markdown(report)
