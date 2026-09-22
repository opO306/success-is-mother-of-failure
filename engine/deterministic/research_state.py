"""B0 research-loop vocabulary: observations, hypothesis status, anomalies, accidents.

These types describe what B has seen and learned about causal A. They hold no
opinion about *how* B decides what to try next -- that lives in research_loop.py.
A contradicted hypothesis is never deleted here: its status changes, and the
domain where it failed is recorded alongside the domain where it still holds.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Mapping

FORMAT = "b0-research-state-v1"

HYPOTHESIS_STATUSES = frozenset({
    "untested", "supported", "conditional", "contradicted_in_domain",
    "underspecified", "superseded", "incompatible", "anomalous",
})
DOMAIN_STATUSES = frozenset({"untested", "tested"})
LIFECYCLE_STATUSES = frozenset({"active", "superseded", "incompatible"})
ANOMALY_STATUSES = frozenset({"unresolved", "persistent", "measurement_error", "explained"})
ACCIDENT_STATUSES = frozenset({"unresolved", "explained_by_accident", "explained_by_hidden_variable",
                               "explained_by_bug", "resolved"})


def _digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _text(value: str, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{context} must be non-empty text")
    return value


def _json_value(value: Any, context: str = "payload") -> None:
    if value is None or isinstance(value, (str, int, bool)):
        return
    if isinstance(value, float):
        raise ValueError(f"{context} cannot contain floating point")
    if isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _json_value(item, f"{context}[{index}]")
        return
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError(f"{context} keys must be text")
            _json_value(item, f"{context}.{key}")
        return
    raise ValueError(f"{context} contains unsupported value type {type(value).__name__}")


@dataclass(frozen=True)
class ObservationRecord:
    """A fact B has read off causal A, before any interpretation.

    `observables` holds only what was directly read from a spec or a run --
    material counts, a state digest, a momentum tuple. It must never hold an
    interpretation ("momentum looks wrong") or a hypothesis ("the scatter rule
    ignores energy"): those are separate records that cite this one by id.
    """
    observation_id: str
    source_digest: str
    observed_at_tick: int
    observables: Mapping[str, Any]
    description: str

    def __post_init__(self) -> None:
        _text(self.observation_id, "observation_id")
        _text(self.source_digest, "source_digest")
        _text(self.description, "description")
        if isinstance(self.observed_at_tick, bool) or not isinstance(self.observed_at_tick, int) or self.observed_at_tick < 0:
            raise ValueError("observed_at_tick must be a nonnegative integer")
        if not isinstance(self.observables, Mapping):
            raise ValueError("observables must be an object")
        _json_value(self.observables, "observables")

    @property
    def digest(self) -> str:
        return _digest(self.canonical())

    def canonical(self) -> dict[str, object]:
        return {
            "description": self.description, "format": FORMAT,
            "observables": dict(self.observables), "observation_id": self.observation_id,
            "observed_at_tick": self.observed_at_tick, "record_kind": "observation",
            "source_digest": self.source_digest,
        }


@dataclass(frozen=True)
class AccidentRecord:
    """The executed experiment differed from what B intended to run.

    This is a difference in *process*: B meant to submit one spec, a different
    one reached the executor, or the executor reports having run something
    else again. It says nothing about whether the result was surprising --
    that is `AnomalyRecord`, and the two may co-occur.
    """
    accident_id: str
    arm_id: str
    intended_spec_digest: str
    submitted_spec_digest: str
    executed_spec_digest: str
    difference_description: str
    observation_id: str
    original_test_valid: bool
    research_value: str

    def __post_init__(self) -> None:
        for field_name in ("accident_id", "arm_id", "intended_spec_digest", "submitted_spec_digest",
                          "executed_spec_digest", "difference_description", "observation_id", "research_value"):
            _text(getattr(self, field_name), field_name)
        if not isinstance(self.original_test_valid, bool):
            raise ValueError("original_test_valid must be boolean")

    @property
    def digest(self) -> str:
        return _digest(self.canonical())

    def canonical(self) -> dict[str, object]:
        return {
            "accident_id": self.accident_id, "arm_id": self.arm_id,
            "difference_description": self.difference_description,
            "executed_spec_digest": self.executed_spec_digest, "format": FORMAT,
            "intended_spec_digest": self.intended_spec_digest,
            "observation_id": self.observation_id, "original_test_valid": self.original_test_valid,
            "record_kind": "accident", "research_value": self.research_value,
            "submitted_spec_digest": self.submitted_spec_digest,
        }


@dataclass(frozen=True)
class AnomalyRecord:
    """The experiment ran exactly as intended, but the result was unexpected.

    Not automatically promoted to "new physics": persistence, measurement
    error, and hidden state are all checked first (that checking is the Deep
    Investigator's job in a later B0 stage). Here the record only preserves
    the observation so it cannot be discarded as noise.
    """
    anomaly_id: str
    hypothesis_id: str
    arm_id: str
    predicted: Mapping[str, Any]
    observed: Mapping[str, Any]
    observation_id: str
    reproduced_count: int
    status: str

    def __post_init__(self) -> None:
        for field_name in ("anomaly_id", "hypothesis_id", "arm_id", "observation_id", "status"):
            _text(getattr(self, field_name), field_name)
        if self.status not in ANOMALY_STATUSES:
            raise ValueError("unsupported anomaly status")
        if not isinstance(self.predicted, Mapping) or not isinstance(self.observed, Mapping):
            raise ValueError("predicted and observed must be objects")
        _json_value(self.predicted, "anomaly.predicted")
        _json_value(self.observed, "anomaly.observed")
        if isinstance(self.reproduced_count, bool) or not isinstance(self.reproduced_count, int) or self.reproduced_count < 0:
            raise ValueError("reproduced_count must be a nonnegative integer")

    @property
    def digest(self) -> str:
        return _digest(self.canonical())

    def canonical(self) -> dict[str, object]:
        return {
            "anomaly_id": self.anomaly_id, "arm_id": self.arm_id, "format": FORMAT,
            "hypothesis_id": self.hypothesis_id, "observation_id": self.observation_id,
            "observed": dict(self.observed), "predicted": dict(self.predicted),
            "record_kind": "anomaly", "reproduced_count": self.reproduced_count,
            "status": self.status,
        }


@dataclass(frozen=True)
class ResearchState:
    """The current shape of B's research, reconstructed by replaying the journal.

    This is never the authoritative record -- the journal is. ResearchState is
    a fold over it: given the same journal prefix, rebuilding this must always
    produce the same value.

    `hypothesis_status` (B0.1) holds whatever `hypothesis_status_changed`
    events wrote directly, kept for backward-compatible journal replay.
    `hypothesis_evidence_status`/`hypothesis_lifecycle_status` (B0.2) are
    instead *derived* from `DomainEvidence` and the hypothesis graph via
    `hypothesis_assessment.py` -- see `research_loop.archive` for how the two
    are kept from being conflated.
    """
    active_hypothesis_ids: tuple[str, ...]
    hypothesis_status: Mapping[str, str]
    open_anomaly_ids: tuple[str, ...]
    open_accident_ids: tuple[str, ...]
    unexplored_domains: tuple[str, ...]
    unresolved_contradictions: tuple[tuple[str, str], ...]
    current_research_mode: str | None
    last_sequence: int
    hypothesis_evidence_status: Mapping[str, str] = field(default_factory=dict)
    hypothesis_lifecycle_status: Mapping[str, str] = field(default_factory=dict)
    domain_status: Mapping[str, str] = field(default_factory=dict)
    anomaly_status: Mapping[str, str] = field(default_factory=dict)
    accident_status: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if len(set(self.active_hypothesis_ids)) != len(self.active_hypothesis_ids):
            raise ValueError("active_hypothesis_ids must be unique")
        for hypothesis_id, status in self.hypothesis_status.items():
            if status not in HYPOTHESIS_STATUSES:
                raise ValueError(f"unsupported hypothesis status {status!r} for {hypothesis_id!r}")
        for hypothesis_id, status in self.hypothesis_evidence_status.items():
            if status not in HYPOTHESIS_STATUSES:
                raise ValueError(f"unsupported evidence status {status!r} for {hypothesis_id!r}")
        for hypothesis_id, status in self.hypothesis_lifecycle_status.items():
            if status not in LIFECYCLE_STATUSES:
                raise ValueError(f"unsupported lifecycle status {status!r} for {hypothesis_id!r}")
        for domain_id, status in self.domain_status.items():
            if status not in DOMAIN_STATUSES:
                raise ValueError(f"unsupported domain status {status!r} for {domain_id!r}")
        for anomaly_id, status in self.anomaly_status.items():
            if status not in ANOMALY_STATUSES:
                raise ValueError(f"unsupported anomaly status {status!r} for {anomaly_id!r}")
        for accident_id, status in self.accident_status.items():
            if status not in ACCIDENT_STATUSES:
                raise ValueError(f"unsupported accident status {status!r} for {accident_id!r}")
        if isinstance(self.last_sequence, bool) or not isinstance(self.last_sequence, int) or self.last_sequence < -1:
            raise ValueError("last_sequence must be an integer of at least -1")

    @property
    def digest(self) -> str:
        return _digest(self.canonical())

    def canonical(self) -> dict[str, object]:
        return {
            "accident_status": dict(sorted(self.accident_status.items())),
            "active_hypothesis_ids": list(self.active_hypothesis_ids),
            "anomaly_status": dict(sorted(self.anomaly_status.items())),
            "current_research_mode": self.current_research_mode, "domain_status": dict(sorted(self.domain_status.items())),
            "format": FORMAT,
            "hypothesis_evidence_status": dict(sorted(self.hypothesis_evidence_status.items())),
            "hypothesis_lifecycle_status": dict(sorted(self.hypothesis_lifecycle_status.items())),
            "hypothesis_status": dict(sorted(self.hypothesis_status.items())),
            "last_sequence": self.last_sequence,
            "open_accident_ids": list(self.open_accident_ids),
            "open_anomaly_ids": list(self.open_anomaly_ids),
            "unexplored_domains": list(self.unexplored_domains),
            "unresolved_contradictions": [list(pair) for pair in self.unresolved_contradictions],
        }
