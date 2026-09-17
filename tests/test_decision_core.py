from __future__ import annotations

from hersona.core.decision import DecisionRequest, build_decision_state


def test_decision_state_uses_hersona_attribute_catalog() -> None:
    request = DecisionRequest(
        persona_names=("personality/kuudere", "speech/soft"),
        weight="moderate",
        user_message="おはよう",
        candidate_tools=("web_search",),
    )

    state = build_decision_state(request)

    assert state["persona"]["names"] == ["personality/kuudere", "speech/soft"]
    assert state["persona"]["weight"] == "moderate"
    assert state["persona"]["attributes"][0]["name"] == "personality/kuudere"
    assert state["persona"]["attributes"][0]["category"] == "personality"
    assert state["conversation"]["latest_user_message"] == "おはよう"
    assert state["environment"]["candidate_tools"] == ["web_search"]


def test_decision_request_bounds_untrusted_text() -> None:
    request = DecisionRequest(
        persona_names=("personality/kuudere",),
        weight="moderate",
        user_message="x" * 2500,
        conversation_summary="y" * 5000,
        proposed_response="z" * 5000,
    )

    state = build_decision_state(request)

    assert len(state["conversation"]["latest_user_message"]) == 2000
    assert len(state["conversation"]["summary"]) == 4000
    assert len(state["conversation"]["proposed_response"]) == 4000
