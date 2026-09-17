import json

import pytest

from hersona.core.decision import (
    DecisionError,
    DecisionRequest,
    DecisionResult,
    apply_gate,
    evaluate_decision,
)


def result(**changes):
    values = dict(
        recommended_action="reply",
        action_confidence=0.9,
        action_probabilities=dict(reply=0.9, ask=0.025, search=0.025, use_tool=0.025, hold=0.025),
        persona_alignment=3.0,
        persona_alignment_confidence=0.9,
        risk="low",
        risk_confidence=0.9,
        gate="allow",
        provider="test",
    )
    return DecisionResult(**(values | changes))


@pytest.mark.parametrize(
    "field",
    ["action_confidence", "persona_alignment", "persona_alignment_confidence", "risk_confidence"],
)
@pytest.mark.parametrize("value", [float("nan"), float("inf"), -1, "0.9", True, None])
def test_malformed_numbers_block(field, value):
    assert apply_gate(result(**{field: value})) == "block"


@pytest.mark.parametrize(
    "changes,expected",
    [
        ({}, "allow"),
        ({"risk": "high"}, "block"),
        ({"risk": "medium"}, "review"),
        ({"gate": "review"}, "review"),
        ({"gate": "block"}, "block"),
        ({"recommended_action": "hold"}, "review"),
        ({"recommended_action": "use_tool"}, "block"),
        ({"action_confidence": 0.69}, "review"),
        ({"risk_confidence": 0.64}, "review"),
        ({"persona_alignment_confidence": 0.1}, "review"),
        ({"persona_alignment": 1.9}, "review"),
        ({"action_probabilities": {}}, "block"),
        ({"risk": "unknown"}, "block"),
        ({"action_probabilities": dict(reply=float("nan"))}, "block"),
    ],
)
def test_gate(changes, expected):
    assert apply_gate(result(**changes)) == expected


def test_tools_never_auto_authorized():
    assert (
        apply_gate(result(recommended_action="use_tool"), candidate_tools=("send_money",))
        == "review"
    )


def test_custom_provider_revalidated():
    class Provider:
        def evaluate(self, request):
            return result(action_confidence=float("nan"))

    with pytest.raises(DecisionError, match="invalid_response"):
        evaluate_decision(DecisionRequest(("kuudere",), "moderate", "hello"), provider=Provider())


def test_cli_no_key(monkeypatch, capsys):
    from hersona.cli import main

    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    assert main(["decide", "kuudere", "--message", "hello", "--json"]) == 2
    data = json.loads(capsys.readouterr().out)
    assert data["error"]["code"] == "provider_not_configured"
    assert data["executed"] is False and data["gate"] == "block"


def test_mcp_no_key(monkeypatch):
    from hersona.mcp.tools import evaluate_decision

    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    data = evaluate_decision(["kuudere"], "hello")
    assert data["error"]["code"] == "provider_not_configured"
    assert data["executed"] is False


def test_missing_dependency_and_lazy_offline_paths(monkeypatch):
    import builtins

    from hersona.core import export_blend, measure_intensity, render_blend
    from hersona.integrations.decision.typesafe import TypeSafeDecisionProvider

    original = builtins.__import__

    def blocked(name, *args, **kwargs):
        if name.startswith("typesafe_sdk"):
            raise ImportError("SECRET must not escape")
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", blocked)
    assert render_blend(["kuudere"]).prompt
    assert export_blend(["kuudere"])
    assert measure_intensity("hello", [render_blend(["speech/soft"]).attributes[0]])
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-only-key")
    with pytest.raises(DecisionError, match="dependency_missing") as exc:
        TypeSafeDecisionProvider().evaluate(DecisionRequest(("kuudere",), "moderate", "hi"))
    assert "SECRET" not in str(exc.value)


@pytest.mark.parametrize(
    "options",
    [
        dict(timeout=float("nan")),
        dict(timeout=float("inf")),
        dict(timeout=0),
        dict(timeout=31),
        dict(provider="arbitrary.module"),
        dict(weight="invalid"),
    ],
)
def test_safe_configuration_errors(options):
    from hersona.core.decision import decision_payload

    data, code = decision_payload(["kuudere"], "hi", **options)
    assert code == 1 and data["error"]["code"] == "invalid_input"


def test_unknown_attribute_is_input_error():
    from hersona.core.decision import decision_payload

    data, code = decision_payload(["does-not-exist"], "hi")
    assert code == 1 and data["gate"] == "block"


def test_blend_semantics_preserved():
    from hersona.core import build_decision_state, render_blend

    request = DecisionRequest(("kuudere", "speech/soft"), "none", "hi")
    state = build_decision_state(request)
    assert (
        state["persona"]["system_prompt"]
        == render_blend(list(request.persona_names), weight="none").prompt
    )


def test_extreme_integer_fails_closed():
    assert apply_gate(result(action_confidence=10**10000)) == "block"


def test_module_entrypoint_no_key():
    import os
    import subprocess
    import sys

    env = {
        k: os.environ[k]
        for k in ("PATH", "PYTHONPATH", "PYTHONDONTWRITEBYTECODE", "SYSTEMROOT")
        if k in os.environ
    }
    env["TYPESAFE_API_KEY"] = ""
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "hersona.cli.app",
            "decide",
            "kuudere",
            "--message",
            "hello",
            "--lang",
            "ja",
            "--json",
        ],
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert proc.returncode == 2
    assert json.loads(proc.stdout)["error"]["code"] == "provider_not_configured"


@pytest.mark.parametrize(
    "field,limit",
    [("user_message", 2000), ("conversation_summary", 4000), ("proposed_response", 4000)],
)
@pytest.mark.parametrize("extra", [0, 1])
@pytest.mark.parametrize("gate", ["allow", "review", "block"])
def test_shared_truncation_gate(field, limit, extra, gate):
    from dataclasses import replace

    request = replace(
        DecisionRequest(("kuudere",), "moderate", "hello"), **{field: "x" * (limit + extra)}
    )

    class Provider:
        def evaluate(self, request):
            return result(gate=gate, warnings=("existing warning",))

    decision = evaluate_decision(request, provider=Provider())
    assert decision.gate == ("review" if extra and gate == "allow" else gate)
    assert "existing warning" in decision.warnings
    truncation = [w for w in decision.warnings if "truncated" in w]
    assert len(truncation) == extra
    if extra:
        assert field in truncation[0]
