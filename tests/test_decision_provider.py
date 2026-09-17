"""Exercise the real pinned SDK serialization/decoding through an offline transport."""

import asyncio
import json
import time

import pytest

from hersona.core.decision import DecisionError, DecisionRequest
from hersona.integrations.decision.typesafe import TypeSafeDecisionProvider

sdk = pytest.importorskip("typesafe_sdk")
httpx = pytest.importorskip("httpx2")

REQUEST = DecisionRequest(
    ("kuudere", "speech/soft"), "moderate", "hello", candidate_tools=("search",)
)


def body():
    return dict(
        model="test-model",
        usage=dict(input_tokens=123),
        answers=dict(
            action=dict(
                type="choice",
                choice="reply",
                confidence=0.9,
                probabilities=dict(reply=0.9, ask=0.025, search=0.025, use_tool=0.025, hold=0.025),
            ),
            risk=dict(
                type="choice",
                choice="low",
                confidence=0.9,
                probabilities=dict(low=0.9, medium=0.05, high=0.05),
            ),
            persona_alignment=dict(
                type="score",
                score=3.0,
                confidence=0.9,
                legend={str(i): str(i) for i in range(5)},
                probabilities={"0": 0.0, "1": 0.0, "2": 0.0, "3": 1.0, "4": 0.0},
            ),
        ),
    )


@pytest.fixture
def transport(monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-only-key")
    real_client = sdk.AsyncTypeSafeClient
    calls = []

    def install(handler):
        def factory(**kwargs):
            assert kwargs["retry"].max_retries == 0
            calls.append(kwargs)
            return real_client(
                **kwargs, transport=httpx.MockTransport(handler), base_url="https://offline.invalid"
            )

        monkeypatch.setattr(sdk, "AsyncTypeSafeClient", factory)
        return calls

    return install


def test_full_contract(transport):
    captured = []

    def handler(request):
        captured.append(json.loads(request.content))
        return httpx.Response(200, json=body())

    transport(handler)
    result = TypeSafeDecisionProvider(model="selected").evaluate(REQUEST)
    assert result.model == "test-model" and result.usage_input_tokens == 123
    sent = captured[0]
    assert sent["model"] == "selected"
    assert "system_prompt" in sent["state"]["persona"]
    assert sent["questions"]["action"]["type"] == "choice"
    assert sent["questions"]["persona_alignment"]["type"] == "score"


@pytest.mark.parametrize(
    "status,code",
    [
        (401, "authentication"),
        (403, "authentication"),
        (429, "rate_limited"),
        (500, "provider_error"),
    ],
)
def test_safe_http_errors(transport, status, code):
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(status, json={"message": "SECRET response body"})

    transport(handler)
    with pytest.raises(DecisionError) as exc:
        TypeSafeDecisionProvider().evaluate(REQUEST)
    assert exc.value.code == code and "SECRET" not in str(exc.value)
    assert len(seen) == 1


@pytest.mark.parametrize(
    "answer,field,value",
    [
        ("action", "confidence", "NaN"),
        ("risk", "confidence", 2),
        ("persona_alignment", "score", 5),
        ("persona_alignment", "confidence", None),
        ("risk", "probabilities", {"low": 1}),
        ("persona_alignment", "probabilities", {"0": 2}),
        ("action", "choice", "unknown"),
        ("action", "type", "future"),
    ],
)
def test_malformed_sdk_responses(transport, answer, field, value):
    data = body()
    data["answers"][answer][field] = value
    transport(lambda r: httpx.Response(200, json=data))
    with pytest.raises(DecisionError) as exc:
        TypeSafeDecisionProvider().evaluate(REQUEST)
    assert exc.value.code == "invalid_response"


def test_missing_answer(transport):
    data = body()
    del data["answers"]["risk"]
    transport(lambda r: httpx.Response(200, json=data))
    with pytest.raises(DecisionError, match="invalid_response"):
        TypeSafeDecisionProvider().evaluate(REQUEST)


def test_direct_provider_applies_gate(transport):
    data = body()
    data["answers"]["risk"]["choice"] = "high"
    transport(lambda r: httpx.Response(200, json=data))
    assert TypeSafeDecisionProvider().evaluate(REQUEST).gate == "block"


def test_deadline_cancels_io(transport):
    cancelled = []

    async def handler(request):
        try:
            await asyncio.sleep(10)
        finally:
            cancelled.append(True)

    transport(handler)
    start = time.monotonic()
    with pytest.raises(DecisionError, match="timeout"):
        TypeSafeDecisionProvider(timeout=0.05).evaluate(REQUEST)
    assert time.monotonic() - start < 0.5
    assert cancelled


def test_sync_api_inside_running_loop(transport):
    transport(lambda r: httpx.Response(200, json=body()))

    async def host():
        return TypeSafeDecisionProvider().evaluate(REQUEST)

    assert asyncio.run(host()).gate == "allow"


def test_cli_mcp_success(transport, capsys):
    from hersona.cli import main
    from hersona.mcp.tools import evaluate_decision

    transport(lambda r: httpx.Response(200, json=body()))
    assert main(["decide", "kuudere", "--message", "hello", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["executed"] is False
    assert evaluate_decision(["kuudere"], "hello")["gate"] == "allow"


@pytest.mark.parametrize(
    "field,limit",
    [("user_message", 2000), ("conversation_summary", 4000), ("proposed_response", 4000)],
)
@pytest.mark.parametrize("extra", [0, 1])
@pytest.mark.parametrize("high_risk", [False, True])
def test_direct_truncation_gate(transport, field, limit, extra, high_risk):
    from dataclasses import replace

    data = body()
    if high_risk:
        data["answers"]["risk"]["choice"] = "high"
    transport(lambda r: httpx.Response(200, json=data))
    request = replace(REQUEST, **{field: "x" * (limit + extra)})
    decision = TypeSafeDecisionProvider().evaluate(request)
    assert decision.gate == ("block" if high_risk else "review" if extra else "allow")
    assert len(decision.warnings) == extra
    if extra:
        assert "truncated" in decision.warnings[0] and field in decision.warnings[0]


def test_shared_provider_truncation_warning_is_not_duplicated(transport):
    from dataclasses import replace

    from hersona.core.decision import evaluate_decision

    transport(lambda r: httpx.Response(200, json=body()))
    decision = evaluate_decision(replace(REQUEST, user_message="x" * 2001))
    assert decision.gate == "review"
    assert len(decision.warnings) == 1
