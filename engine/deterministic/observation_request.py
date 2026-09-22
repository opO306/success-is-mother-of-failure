"""Structured requests B0.7 hands to B0.4/B0.5, plus the machinery that stops it from repeating itself.

Every request type here is deliberately narrow-scoped (docs/README section
24: "observe everything" is explicitly forbidden) and carries a deterministic
`fingerprint` so `has_been_requested` can recognize a repeat before a
duplicate investigation cycle is spent on it (section 33).
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

FORMAT = "observation-request-v1"


def _digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _text(value: str, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{context} must be non-empty text")
    return value


def _texts(values: tuple[str, ...], context: str, allow_empty: bool = False) -> tuple[str, ...]:
    if not isinstance(values, tuple):
        raise ValueError(f"{context} must be a tuple")
    result = tuple(_text(value, context) for value in values)
    if not allow_empty and not result:
        raise ValueError(f"{context} cannot be empty")
    if len(set(result)) != len(result):
        raise ValueError(f"{context} values must be unique")
    return result


@dataclass(frozen=True)
class ObservationGap:
    """Two adjacent observations with a suspiciously coarse gap between them -- a resolution complaint, not a claim.

    Means exactly "the kernel may have finer-grained steps between these two
    observation_seq points that the current TraceSpec never asked for" --
    never "there is definitely something hidden here".
    """
    gap_id: str
    earlier_observation_seq: int
    later_observation_seq: int
    tracked_roles: tuple[str, ...]
    tracked_fields: tuple[str, ...]
    reason: str

    def __post_init__(self) -> None:
        _text(self.gap_id, "gap_id")
        if isinstance(self.earlier_observation_seq, bool) or not isinstance(self.earlier_observation_seq, int):
            raise ValueError("earlier_observation_seq must be an integer")
        if isinstance(self.later_observation_seq, bool) or not isinstance(self.later_observation_seq, int):
            raise ValueError("later_observation_seq must be an integer")
        if self.later_observation_seq <= self.earlier_observation_seq:
            raise ValueError("later_observation_seq must be after earlier_observation_seq")
        _texts(self.tracked_roles, "tracked_roles", allow_empty=True)
        _texts(self.tracked_fields, "tracked_fields", allow_empty=True)
        _text(self.reason, "reason")

    def canonical(self) -> dict[str, object]:
        return {"earlier_observation_seq": self.earlier_observation_seq, "format": FORMAT, "gap_id": self.gap_id,
                "later_observation_seq": self.later_observation_seq, "reason": self.reason,
                "tracked_fields": sorted(self.tracked_fields), "tracked_roles": sorted(self.tracked_roles)}


@dataclass(frozen=True)
class ObservationBudget:
    """A hard ceiling on how much a single ObservationRequest may ask for. No unlimited requests, ever."""
    max_roles: int
    max_fields: int
    max_tick_span: int
    max_pending_requests: int

    def __post_init__(self) -> None:
        for name in ("max_roles", "max_fields", "max_tick_span", "max_pending_requests"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError(f"{name} must be a positive integer")

    def canonical(self) -> dict[str, object]:
        return {"format": FORMAT, "max_fields": self.max_fields, "max_pending_requests": self.max_pending_requests,
                "max_roles": self.max_roles, "max_tick_span": self.max_tick_span}


def default_observation_budget() -> ObservationBudget:
    return ObservationBudget(max_roles=4, max_fields=8, max_tick_span=10, max_pending_requests=5)


class ObservationBudgetExceeded(ValueError):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)


@dataclass(frozen=True)
class ObservationRequest:
    """A minimal, purpose-scoped request for B0.4 to trace something it currently does not.

    `fingerprint` is deterministic over the request's identifying fields, so
    `has_been_requested` can compare it against `InvestigationHistory`
    without re-deriving equality semantics elsewhere.
    """
    request_id: str
    missing_link_investigation_id: str
    target_role: str
    target_field: str
    start_tick: int
    end_tick: int
    reason: str
    expected_effect: str

    def __post_init__(self) -> None:
        for field_name in ("request_id", "missing_link_investigation_id", "target_role", "target_field",
                          "reason", "expected_effect"):
            _text(getattr(self, field_name), field_name)
        if isinstance(self.start_tick, bool) or not isinstance(self.start_tick, int) or self.start_tick < 0:
            raise ValueError("start_tick must be a nonnegative integer")
        if isinstance(self.end_tick, bool) or not isinstance(self.end_tick, int) or self.end_tick < self.start_tick:
            raise ValueError("end_tick must be an integer at least start_tick")

    def validate_against_budget(self, budget: ObservationBudget) -> None:
        if self.end_tick - self.start_tick > budget.max_tick_span:
            raise ObservationBudgetExceeded(
                f"requested tick span {self.end_tick - self.start_tick} exceeds budget {budget.max_tick_span}")

    @property
    def fingerprint(self) -> str:
        return _digest({"end_tick": self.end_tick, "investigation_id": self.missing_link_investigation_id,
                        "start_tick": self.start_tick, "target_field": self.target_field,
                        "target_role": self.target_role})

    def canonical(self) -> dict[str, object]:
        return {"end_tick": self.end_tick, "expected_effect": self.expected_effect, "fingerprint": self.fingerprint,
                "format": FORMAT, "missing_link_investigation_id": self.missing_link_investigation_id,
                "reason": self.reason, "request_id": self.request_id, "start_tick": self.start_tick,
                "target_field": self.target_field, "target_role": self.target_role}


@dataclass(frozen=True)
class MechanismTestRequest:
    """A minimal request for B0.5 to run an intervention that would discriminate two missing-link hypotheses."""
    request_id: str
    missing_link_investigation_id: str
    target_hypothesis_id: str
    competing_hypothesis_id: str
    reason: str

    def __post_init__(self) -> None:
        for field_name in ("request_id", "missing_link_investigation_id", "target_hypothesis_id",
                          "competing_hypothesis_id", "reason"):
            _text(getattr(self, field_name), field_name)

    @property
    def fingerprint(self) -> str:
        return _digest({"competing": self.competing_hypothesis_id, "investigation_id": self.missing_link_investigation_id,
                        "target": self.target_hypothesis_id})

    def canonical(self) -> dict[str, object]:
        return {"competing_hypothesis_id": self.competing_hypothesis_id, "fingerprint": self.fingerprint,
                "format": FORMAT, "missing_link_investigation_id": self.missing_link_investigation_id,
                "reason": self.reason, "request_id": self.request_id,
                "target_hypothesis_id": self.target_hypothesis_id}


@dataclass(frozen=True)
class InstrumentationRequest:
    """"This cannot be checked until A exposes this value" -- handed to a human/higher system, never acted on alone.

    B0.7 never makes an unobservable value observable itself; this is the
    structured way of saying so.
    """
    request_id: str
    missing_link_investigation_id: str
    role_kind: str
    field: str
    reason: str

    def __post_init__(self) -> None:
        for field_name in ("request_id", "missing_link_investigation_id", "role_kind", "field", "reason"):
            _text(getattr(self, field_name), field_name)

    @property
    def fingerprint(self) -> str:
        return _digest({"field": self.field, "investigation_id": self.missing_link_investigation_id,
                        "role_kind": self.role_kind})

    def canonical(self) -> dict[str, object]:
        return {"field": self.field, "fingerprint": self.fingerprint, "format": FORMAT,
                "missing_link_investigation_id": self.missing_link_investigation_id, "reason": self.reason,
                "request_id": self.request_id, "role_kind": self.role_kind}


@dataclass(frozen=True)
class InvestigationHistory:
    """Fingerprints of every request already made, so B0.7 never repeats an identical one without new evidence."""
    requested_fingerprints: tuple[str, ...]

    def has_been_requested(self, fingerprint: str) -> bool:
        return fingerprint in self.requested_fingerprints

    def with_fingerprint(self, fingerprint: str) -> "InvestigationHistory":
        if fingerprint in self.requested_fingerprints:
            return self
        return InvestigationHistory(self.requested_fingerprints + (fingerprint,))

    def canonical(self) -> dict[str, object]:
        return {"format": FORMAT, "requested_fingerprints": sorted(self.requested_fingerprints)}


def empty_investigation_history() -> InvestigationHistory:
    return InvestigationHistory(())
