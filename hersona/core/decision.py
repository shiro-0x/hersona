"""Runtime-neutral decision models, real blend state, and conservative local gates."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from math import isfinite
from typing import Literal, Protocol

from hersona.core.attach import render_blend
from hersona.core.weight import coerce_level

_CONVERSATION_LIMITS = {
    "user_message": 2000,
    "conversation_summary": 4000,
    "proposed_response": 4000,
}


@dataclass(frozen=True)
class DecisionRequest:
    """Persona selection and conversation data for an optional decision provider."""

    persona_names: tuple[str, ...]
    weight: str
    user_message: str
    conversation_summary: str | None = None
    candidate_tools: tuple[str, ...] = ()
    proposed_response: str | None = None

    def __post_init__(self) -> None:
        for name, values, maximum in (
            ("persona_names", self.persona_names, 32),
            ("candidate_tools", self.candidate_tools, 64),
        ):
            if not isinstance(values, tuple) or len(values) > maximum:
                raise ValueError(f"{name} must be a bounded tuple")
            if any(not isinstance(v, str) or not v.strip() or len(v) > 256 for v in values):
                raise ValueError(f"{name} contains an invalid identifier")
        if not self.persona_names:
            raise ValueError("persona_names must not be empty")
        if not isinstance(self.user_message, str) or not self.user_message.strip():
            raise ValueError("user_message must be text")
        for value in (self.conversation_summary, self.proposed_response):
            if value is not None and not isinstance(value, str):
                raise ValueError("optional conversation values must be text")
        coerce_level(self.weight)


def build_decision_state(request: DecisionRequest) -> dict:
    """Resolve the real catalog and blend locally, retaining Hersona semantics.

    Conversation fields are truncated; persona prompts are rejected rather than
    truncated so their meaning is not silently changed. Evaluation forces review
    with warnings when conversation content is truncated. No runtime executes here.
    """
    weight = coerce_level(request.weight).value
    blend = render_blend(list(request.persona_names), weight=weight)
    if len(blend.prompt) > 64000:
        raise ValueError("persona prompt exceeds decision input limit")
    return {
        "persona": {
            "names": list(request.persona_names),
            "weight": weight,
            "attributes": [
                {"name": name, "category": attribute["attribute_category"]}
                for name, attribute in zip(request.persona_names, blend.attributes, strict=True)
            ],
            "system_prompt": blend.prompt,
            "conflicts": [list(pair) for pair in blend.conflicts],
        },
        "conversation": {
            "latest_user_message": request.user_message[: _CONVERSATION_LIMITS["user_message"]],
            "summary": (request.conversation_summary or "")[
                : _CONVERSATION_LIMITS["conversation_summary"]
            ],
            "proposed_response": (
                request.proposed_response[: _CONVERSATION_LIMITS["proposed_response"]]
                if request.proposed_response is not None
                else None
            ),
        },
        "environment": {
            "candidate_tools": list(request.candidate_tools),
            "tool_execution_requires_gate": True,
        },
    }


# This module intentionally imports no SDK or runtime framework.

Action = Literal["reply", "ask", "search", "use_tool", "hold"]
Risk = Literal["low", "medium", "high"]
Gate = Literal["allow", "review", "block"]
ACTIONS = ("reply", "ask", "search", "use_tool", "hold")
RISKS = ("low", "medium", "high")


class DecisionError(RuntimeError):
    """A public, content-free error. Never includes SDK exception text."""

    CODES = {
        "invalid_input": (1, "Invalid decision input, attribute, or configuration."),
        "provider_not_configured": (2, "Configure TYPESAFE_API_KEY to use decisions."),
        "dependency_missing": (2, "Install hersona[decision] to use TypeSafe."),
        "authentication": (3, "Provider authentication or access denied."),
        "rate_limited": (3, "Provider rate limit reached."),
        "timeout": (3, "Provider deadline exceeded."),
        "connection": (3, "Provider connection failed."),
        "provider_error": (3, "Provider request failed."),
        "invalid_response": (3, "Provider returned invalid decision data."),
    }

    def __init__(self, code: str):
        self.code = code if code in self.CODES else "provider_error"
        self.exit_code, self.message = self.CODES[self.code]
        super().__init__(f"{self.code}: {self.message}")

    def to_dict(self) -> dict:
        return {
            "executed": False,
            "gate": "block",
            "recommended_action": "hold",
            "error": {"code": self.code, "message": self.message},
        }


@dataclass(frozen=True)
class DecisionResult:
    recommended_action: Action
    action_confidence: float
    action_probabilities: dict[str, float]
    persona_alignment: float
    persona_alignment_confidence: float
    risk: Risk
    risk_confidence: float
    gate: Gate
    provider: str
    model: str | None = None
    usage_input_tokens: int | None = None
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        validate_decision(self)
        return {**asdict(self), "executed": False}


class DecisionProvider(Protocol):
    def evaluate(self, request: DecisionRequest) -> DecisionResult: ...


def valid_number(value: object, maximum: float = 1.0) -> bool:
    return type(value) in (int, float) and 0 <= value <= maximum and isfinite(value)


def validate_probabilities(values: object, labels: tuple) -> None:
    if (
        not isinstance(values, dict)
        or set(values) != set(labels)
        or not all(valid_number(v) for v in values.values())
        or abs(sum(values.values()) - 1.0) > 0.001
    ):
        raise DecisionError("invalid_response")


def validate_decision(result: DecisionResult) -> None:
    if not isinstance(result, DecisionResult):
        raise DecisionError("invalid_response")
    if (
        result.recommended_action not in ACTIONS
        or result.risk not in RISKS
        or result.gate not in ("allow", "review", "block")
        or not all(
            valid_number(v)
            for v in (
                result.action_confidence,
                result.risk_confidence,
                result.persona_alignment_confidence,
            )
        )
        or not valid_number(result.persona_alignment, 4)
        or not isinstance(result.provider, str)
        or (result.model is not None and not isinstance(result.model, str))
        or (
            result.usage_input_tokens is not None
            and (type(result.usage_input_tokens) is not int or result.usage_input_tokens < 0)
        )
        or not isinstance(result.warnings, tuple)
        or any(not isinstance(w, str) for w in result.warnings)
    ):
        raise DecisionError("invalid_response")
    validate_probabilities(result.action_probabilities, ACTIONS)


def apply_gate(decision: DecisionResult, *, candidate_tools: tuple[str, ...] = ()) -> Gate:
    """Fail closed; preserve stricter gates. Tools always require runtime review."""
    try:
        validate_decision(decision)
    except DecisionError:
        return "block"
    if decision.gate == "block" or decision.risk == "high":
        return "block"
    if decision.recommended_action in ("search", "use_tool") and not candidate_tools:
        return "block"
    if (
        decision.gate == "review"
        or decision.risk == "medium"
        or decision.recommended_action in ("hold", "search", "use_tool")
        or decision.action_confidence < 0.70
        or decision.risk_confidence < 0.65
        or decision.persona_alignment_confidence < 0.65
        or decision.persona_alignment < 2
    ):
        return "review"
    return "allow"


def finalize_decision(result: DecisionResult, request: DecisionRequest) -> DecisionResult:
    """Apply local gates and disclose incomplete input on every evaluation path."""
    validate_decision(result)
    gate = apply_gate(result, candidate_tools=request.candidate_tools)
    warnings = list(result.warnings)
    for field, limit in _CONVERSATION_LIMITS.items():
        if len(getattr(request, field) or "") > limit:
            warning = f"Input {field} was truncated to {limit} characters; review required."
            if warning not in warnings:
                warnings.append(warning)
            if gate == "allow":
                gate = "review"
    return replace(result, gate=gate, warnings=tuple(warnings))


def create_provider(name: str = "typesafe", **options: object) -> DecisionProvider:
    if name != "typesafe":
        raise DecisionError("invalid_input")
    from hersona.integrations.decision.typesafe import TypeSafeDecisionProvider

    return TypeSafeDecisionProvider(**options)


def evaluate_decision(
    request: DecisionRequest, *, provider: DecisionProvider | None = None
) -> DecisionResult:
    """Explicit, runtime-neutral recommendation. Never executes an action or falls back."""
    try:
        build_decision_state(request)
    except Exception:
        raise DecisionError("invalid_input") from None
    try:
        result = (provider if provider is not None else create_provider()).evaluate(request)
        return finalize_decision(result, request)
    except DecisionError:
        raise
    except Exception:
        raise DecisionError("provider_error") from None


def decision_payload(
    names: list[str],
    user_message: str,
    *,
    weight: str = "moderate",
    conversation_summary: str | None = None,
    candidate_tools: list[str] | None = None,
    proposed_response: str | None = None,
    provider: str = "typesafe",
    model: str | None = None,
    timeout: float = 3.0,
) -> tuple[dict, int]:
    """Shared safe JSON boundary for CLI and MCP."""
    try:
        if not isinstance(names, list) or (
            candidate_tools is not None and not isinstance(candidate_tools, list)
        ):
            raise ValueError
        request = DecisionRequest(
            tuple(names),
            weight,
            user_message,
            conversation_summary,
            tuple(candidate_tools or ()),
            proposed_response,
        )
        build_decision_state(request)
    except Exception:
        error = DecisionError("invalid_input")
        return error.to_dict(), error.exit_code
    try:
        result = evaluate_decision(
            request, provider=create_provider(provider, model=model, timeout=timeout)
        )
        return result.to_dict(), 0
    except DecisionError as error:
        return error.to_dict(), error.exit_code
