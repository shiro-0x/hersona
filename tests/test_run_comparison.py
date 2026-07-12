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
