"""Experimental, pure validation and versioned self-models.

Only explicit, scoped presentation preferences are supported. Text is data, never
parsed for instructions or inferred preferences. Trust and evidence independence
are assertions supplied by the runtime, not facts established by this module.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime
from typing import Literal

Scope = Literal["session", "relationship", "persona"]
Policy = Literal["manual", "trusted_low_risk", "disabled"]
_PREFERENCES = {
    "preferences.response_length": ("brief", "detailed"),
    "preferences.explanation_style": ("examples", "steps"),
}


def _text(value: str, maximum: int = 256) -> None:
    if type(value) is not str or not value.strip() or len(value) > maximum:
        raise ValueError("Expected bounded, nonempty text")
    try:
        value.encode("utf-8")
    except UnicodeError as exc:
        raise ValueError("Invalid UTF-8 text") from exc
    if any(ord(c) < 32 and c not in "\n\r\t" for c in value):
        raise ValueError("Control character in text")


def _timestamp(value: str) -> None:
    _text(value, 64)
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("Expected ISO-8601 timestamp") from exc
    if parsed.utcoffset() is None:
        raise ValueError("Timestamp requires a timezone")


def _tuple(value: tuple, item_type: type) -> None:
    if type(value) is not tuple or any(type(item) is not item_type for item in value):
        raise ValueError("Expected an immutable typed tuple")


def _json(value: object) -> str:
    return json.dumps(
        value, sort_keys=True, ensure_ascii=True, separators=(",", ":"), allow_nan=False
    )


def _hash(value: object) -> str:
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


def _scope(scope: str, actor_scope: str) -> None:
    if scope not in ("session", "relationship", "persona"):
        raise ValueError("Invalid scope")
    _text(actor_scope)
    if scope == "persona":
        if actor_scope != "persona":
            raise ValueError("Invalid persona scope")
    elif not re.fullmatch(rf"{scope}:[A-Za-z0-9_.-]+", actor_scope):
        raise ValueError("Expected a namespaced actor scope")


@dataclass(frozen=True)
class IdentityKernel:
    persona_id: str
    display_name: str
    origin: str
    role: str
    persona_hash: str

    def __post_init__(self) -> None:
        for value in asdict(self).values():
            _text(value)
        if not re.fullmatch(r"[0-9a-f]{64}", self.persona_hash):
            raise ValueError("Expected SHA-256 persona hash")


@dataclass(frozen=True)
class ExperienceEvent:
    event_id: str
    actor_scope: str
    occurred_at: str
    content: str
    evidence_group: str
    source: Literal["runtime", "user", "tool", "imported"] = "runtime"
    trust: Literal["untrusted", "observed", "verified"] = "untrusted"
    retention: Literal["ephemeral", "normal", "durable"] = "ephemeral"
    preference_path: str | None = None
    preference_value: str | None = None
    content_hash: str = field(init=False)

    def __post_init__(self) -> None:
        _text(self.event_id)
        _text(self.evidence_group)
        _text(self.actor_scope)
        _scope(self.actor_scope.split(":", 1)[0], self.actor_scope)
        _timestamp(self.occurred_at)
        _text(self.content, 8000)
        if self.source not in ("runtime", "user", "tool", "imported"):
            raise ValueError("Invalid source")
        if self.trust not in ("untrusted", "observed", "verified"):
            raise ValueError("Invalid trust")
        if self.retention not in ("ephemeral", "normal", "durable"):
            raise ValueError("Invalid retention")
        if self.preference_path is not None:
            _text(self.preference_path)
            if self.preference_path not in _PREFERENCES:
                raise ValueError("Unsupported preference")
            if self.preference_value not in _PREFERENCES[self.preference_path]:
                raise ValueError("Unsupported preference value")
        elif self.preference_value is not None:
            raise ValueError("Preference value requires a path")
        object.__setattr__(self, "content_hash", _hash(self.content))


@dataclass(frozen=True)
class Observation:
    base_snapshot_id: str
    event: ExperienceEvent

    def __post_init__(self) -> None:
        _text(self.base_snapshot_id)
        if type(self.event) is not ExperienceEvent:
            raise ValueError("Expected ExperienceEvent")


@dataclass(frozen=True)
class GrowthProposal:
    proposal_id: str
    base_snapshot_id: str
    target_path: str
    candidate_value: str
    evidence_ids: tuple[str, ...]
    scope: Scope
    actor_scope: str
    created_at: str
    rationale: str = "Repeated explicit preference in independently labeled evidence."
    confidence: float = 1.0
    operation: Literal["add", "revise", "weaken", "supersede", "forget"] = "add"
    risk: Literal["low", "medium", "high"] = "low"
    status: Literal["pending", "accepted", "rejected", "expired"] = "pending"

    def __post_init__(self) -> None:
        for value in (
            self.proposal_id,
            self.base_snapshot_id,
            self.target_path,
            self.candidate_value,
        ):
            _text(value)
        _text(self.rationale, 2000)
        _timestamp(self.created_at)
        _scope(self.scope, self.actor_scope)
        _tuple(self.evidence_ids, str)
        for value in self.evidence_ids:
            _text(value)
        if type(self.confidence) not in (int, float) or not 0 <= self.confidence <= 1:
            raise ValueError("Confidence must be finite and within [0, 1]")
        if self.operation not in ("add", "revise", "weaken", "supersede", "forget"):
            raise ValueError("Invalid operation")
        if self.risk not in ("low", "medium", "high"):
            raise ValueError("Invalid risk")
        if self.status not in ("pending", "accepted", "rejected", "expired"):
            raise ValueError("Invalid status")


def _proposal_error(proposal: GrowthProposal, evidence: tuple[ExperienceEvent, ...]) -> str | None:
    if proposal.operation != "add" or proposal.target_path not in _PREFERENCES:
        return "unsupported_target_or_operation"
    if proposal.candidate_value not in _PREFERENCES[proposal.target_path]:
        return "unsupported_value"
    if proposal.scope not in ("session", "relationship") or proposal.risk != "low":
        return "unsupported_scope_or_risk"
    ids = tuple(e.event_id for e in evidence)
    if len(ids) < 2 or len(set(ids)) != len(ids) or sorted(ids) != sorted(proposal.evidence_ids):
        return "invalid_evidence"
    if len({e.evidence_group for e in evidence}) != len(evidence):
        return "dependent_evidence"
    if any(
        e.trust != "verified"
        or e.actor_scope != proposal.actor_scope
        or e.preference_path != proposal.target_path
        or e.preference_value != proposal.candidate_value
        for e in evidence
    ):
        return "untrusted_or_mismatched_evidence"
    return None


@dataclass(frozen=True)
class AdoptedPreference:
    proposal: GrowthProposal
    evidence: tuple[ExperienceEvent, ...]
    actor: str
    adopted_at: str

    def __post_init__(self) -> None:
        if type(self.proposal) is not GrowthProposal or self.proposal.status != "accepted":
            raise ValueError("Only accepted proposals belong in snapshots")
        _tuple(self.evidence, ExperienceEvent)
        _text(self.actor)
        _timestamp(self.adopted_at)
        if error := _proposal_error(self.proposal, self.evidence):
            raise ValueError(error)


@dataclass(frozen=True)
class SelfSnapshot:
    identity: IdentityKernel
    created_at: str
    values: tuple[str, ...] = ()
    boundaries: tuple[str, ...] = ()
    preferences: tuple[AdoptedPreference, ...] = ()
    lineage: tuple[str, ...] = ()
    rollback_of: str | None = None
    schema_version: str = field(default="evolution-mvp-1", init=False)
    snapshot_id: str = field(init=False)
    content_hash: str = field(init=False)

    def __post_init__(self) -> None:
        if type(self.identity) is not IdentityKernel:
            raise ValueError("Expected IdentityKernel")
        _timestamp(self.created_at)
        for items in (self.values, self.boundaries, self.lineage):
            _tuple(items, str)
            for value in items:
                _text(value)
        _tuple(self.preferences, AdoptedPreference)
        if any(not re.fullmatch(r"[0-9a-f]{64}", item) for item in self.lineage):
            raise ValueError("Invalid lineage hash")
        if len(set(self.lineage)) != len(self.lineage):
            raise ValueError("Duplicate lineage entry")
        if self.rollback_of is not None and self.rollback_of not in self.lineage:
            raise ValueError("Rollback target must be an ancestor")
        keys = [(p.proposal.actor_scope, p.proposal.target_path) for p in self.preferences]
        if len(set(keys)) != len(keys):
            raise ValueError("Conflicting preferences")
        if any(p.proposal.base_snapshot_id not in self.lineage for p in self.preferences):
            raise ValueError("Preference base must be in lineage")
        payload = {
            name: getattr(self, name)
            for name in (
                "created_at",
                "values",
                "boundaries",
                "lineage",
                "rollback_of",
                "schema_version",
            )
        }
        payload.update(
            identity=asdict(self.identity), preferences=[asdict(p) for p in self.preferences]
        )
        digest = _hash(payload)
        object.__setattr__(self, "content_hash", digest)
        object.__setattr__(self, "snapshot_id", digest)

    @property
    def parent_snapshot_id(self) -> str | None:
        return self.lineage[-1] if self.lineage else None

    @property
    def version(self) -> int:
        return len(self.lineage) + 1


@dataclass(frozen=True)
class Diagnostic:
    code: str
    subject_id: str


@dataclass(frozen=True)
class ProposalResult:
    proposals: tuple[GrowthProposal, ...]
    diagnostics: tuple[Diagnostic, ...] = ()


@dataclass(frozen=True)
class AdoptionResult:
    snapshot: SelfSnapshot
    proposals: tuple[GrowthProposal, ...]
    diagnostics: tuple[Diagnostic, ...] = ()


@dataclass(frozen=True)
class RenderResult:
    text: str
    snapshot_hash: str
    version: int


def observe(event: ExperienceEvent, snapshot: SelfSnapshot) -> Observation:
    """Normalize newlines without interpreting content or mutating the event."""
    return Observation(
        snapshot.snapshot_id,
        replace(event, content=event.content.replace("\r\n", "\n").replace("\r", "\n")),
    )


def _events(
    observations: tuple[Observation, ...], snapshot: SelfSnapshot
) -> tuple[ExperienceEvent, ...]:
    _tuple(observations, Observation)
    if any(o.base_snapshot_id != snapshot.snapshot_id for o in observations):
        raise ValueError("Observation belongs to another snapshot")
    events = tuple(sorted((o.event for o in observations), key=lambda e: e.event_id))
    if len({e.event_id for e in events}) != len(events):
        raise ValueError("Duplicate event ID")
    return events


def propose_growth(
    observations: tuple[Observation, ...], snapshot: SelfSnapshot, *, created_at: str
) -> ProposalResult:
    """Group explicit candidates only; require two verified evidence groups."""
    _timestamp(created_at)
    events = _events(observations, snapshot)
    groups: dict[tuple[str, str, str], list[ExperienceEvent]] = {}
    for event in events:
        if event.preference_path is not None and event.actor_scope != "persona":
            key = (event.actor_scope, event.preference_path, event.preference_value)
            groups.setdefault(key, []).append(event)
    proposals = []
    diagnostics = []
    for (actor_scope, path, value), evidence in sorted(groups.items()):
        proposal = GrowthProposal(
            proposal_id=_hash(
                [
                    snapshot.snapshot_id,
                    actor_scope,
                    path,
                    value,
                    [asdict(e) for e in evidence],
                    created_at,
                ]
            ),
            base_snapshot_id=snapshot.snapshot_id,
            target_path=path,
            candidate_value=value,
            evidence_ids=tuple(e.event_id for e in evidence),
            scope=actor_scope.split(":", 1)[0],
            actor_scope=actor_scope,
            created_at=created_at,
        )
        if error := _proposal_error(proposal, tuple(evidence)):
            diagnostics.append(Diagnostic(error, proposal.proposal_id))
        else:
            proposals.append(proposal)
    return ProposalResult(tuple(proposals), tuple(diagnostics))


def adopt(
    snapshot: SelfSnapshot,
    proposals: tuple[GrowthProposal, ...],
    *,
    observations: tuple[Observation, ...] = (),
    policy: Policy = "manual",
    approved_ids: tuple[str, ...] = (),
    actor: str = "runtime",
    created_at: str,
) -> AdoptionResult:
    """Validate a whole batch before adoption; invalid batches leave state unchanged.

    Manual adoption requires exact proposal IDs in ``approved_ids``. No approval
    is inferred from calling this function. Valid unapproved proposals stay pending.
    """
    _timestamp(created_at)
    _text(actor)
    _tuple(proposals, GrowthProposal)
    _tuple(approved_ids, str)
    if policy not in ("manual", "trusted_low_risk", "disabled"):
        raise ValueError("Invalid adoption policy")
    events = {e.event_id: e for e in _events(observations, snapshot)}
    proposal_ids = [p.proposal_id for p in proposals]
    if len(set(proposal_ids)) != len(proposal_ids):
        raise ValueError("Duplicate proposal ID")
    if len(set(approved_ids)) != len(approved_ids) or set(approved_ids) - set(proposal_ids):
        raise ValueError("Invalid approval IDs")
    keys = {(p.proposal.actor_scope, p.proposal.target_path) for p in snapshot.preferences}
    diagnostics = []
    evidence_by_id = {}
    for proposal in proposals:
        evidence = tuple(events[e] for e in proposal.evidence_ids if e in events)
        evidence_by_id[proposal.proposal_id] = evidence
        error = _proposal_error(proposal, evidence)
        if proposal.base_snapshot_id != snapshot.snapshot_id:
            error = "stale_base"
        elif proposal.status != "pending":
            error = "invalid_status"
        key = (proposal.actor_scope, proposal.target_path)
        if key in keys:
            error = "conflict"
        keys.add(key)
        if error:
            diagnostics.append(Diagnostic(error, proposal.proposal_id))
    if diagnostics:
        invalid = {d.subject_id for d in diagnostics}
        return AdoptionResult(
            snapshot,
            tuple(
                replace(p, status="rejected") if p.proposal_id in invalid else p for p in proposals
            ),
            tuple(diagnostics),
        )
    records = []
    resolved = []
    for proposal in sorted(proposals, key=lambda p: p.proposal_id):
        allowed = policy == "trusted_low_risk" or (
            policy == "manual" and proposal.proposal_id in approved_ids
        )
        if allowed:
            proposal = replace(proposal, status="accepted")
            records.append(
                AdoptedPreference(proposal, evidence_by_id[proposal.proposal_id], actor, created_at)
            )
        else:
            diagnostics.append(
                Diagnostic(
                    "disabled" if policy == "disabled" else "approval_required",
                    proposal.proposal_id,
                )
            )
        resolved.append(proposal)
    if records:
        snapshot = replace(
            snapshot,
            preferences=snapshot.preferences + tuple(records),
            created_at=created_at,
            lineage=snapshot.lineage + (snapshot.snapshot_id,),
            rollback_of=None,
        )
    return AdoptionResult(snapshot, tuple(resolved), tuple(diagnostics))


def rollback(snapshot: SelfSnapshot, ancestor: SelfSnapshot, *, created_at: str) -> SelfSnapshot:
    """Restore an actual ancestor's state in a new child of the current snapshot."""
    if ancestor.snapshot_id not in snapshot.lineage:
        raise ValueError("Rollback target is not an ancestor")
    index = snapshot.lineage.index(ancestor.snapshot_id)
    if ancestor.lineage != snapshot.lineage[:index] or ancestor.identity != snapshot.identity:
        raise ValueError("Invalid ancestor lineage")
    if ancestor.values != snapshot.values or ancestor.boundaries != snapshot.boundaries:
        raise ValueError("Stable state differs")
    return replace(
        ancestor,
        created_at=created_at,
        lineage=snapshot.lineage + (snapshot.snapshot_id,),
        rollback_of=ancestor.snapshot_id,
    )


def render_self(snapshot: SelfSnapshot, *, actor_scope: str | None = None) -> RenderResult:
    """Return JSON data; scoped preferences are excluded unless scope is selected."""
    if actor_scope is not None:
        _text(actor_scope)
        _scope(actor_scope.split(":", 1)[0], actor_scope)
    payload = {
        "schema_version": snapshot.schema_version,
        "snapshot_hash": snapshot.content_hash,
        "version": snapshot.version,
        "stable": {
            "identity": asdict(snapshot.identity),
            "values": snapshot.values,
            "boundaries": snapshot.boundaries,
        },
        "mutable": [
            {
                "path": r.proposal.target_path,
                "value": r.proposal.candidate_value,
                "confidence": r.proposal.confidence,
                "actor_scope": r.proposal.actor_scope,
                "evidence_ids": r.proposal.evidence_ids,
            }
            for r in snapshot.preferences
            if r.proposal.actor_scope == actor_scope
        ],
    }
    return RenderResult(_json(payload), snapshot.content_hash, snapshot.version)


def render_context(snapshot: SelfSnapshot, *, actor_scope: str, request: str) -> RenderResult:
    """Keep current request data separate; do not render events or proposal queues.

    JSON separation is not a downstream model's prompt-injection guarantee.
    """
    _text(request, 8000)
    rendered = render_self(snapshot, actor_scope=actor_scope)
    return RenderResult(
        _json({"self": json.loads(rendered.text), "request_data": request}),
        snapshot.content_hash,
        snapshot.version,
    )
