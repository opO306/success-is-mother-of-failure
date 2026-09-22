"""Mechanism hypotheses drawn from a DivergenceChain, and how to test them next.

A `MechanismCandidate`'s `path` is read directly off a `DivergenceChain`'s
`events` (in phase order) -- it is a proposal that this observed sequence
might be causal, not a proof. Multiple candidates over the same chain are
expected and kept side by side in a `MechanismCandidateSet`: B0.4 does not
pick a winner. Testing a candidate (removing/clamping/replacing a mid-path
role) is `FollowupExperimentProposal`'s job to *propose*, never to execute --
running the intervention is later work, explicitly out of this module's scope.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

FORMAT = "mechanism-candidate-v1"
MECHANISM_STATUSES = frozenset({"NEEDS_INTERVENTION", "UNDER_TEST", "SUPPORTED", "REJECTED"})
INTERVENTION_OPERATIONS = frozenset({"remove", "clamp", "replace"})


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
    return result


@dataclass(frozen=True, order=True)
class MechanismStep:
    """One (role, field) step along a proposed mechanism path, in the order it was observed to diverge."""
    role: str
    field: str

    def canonical(self) -> dict[str, object]:
        return {"field": self.field, "role": self.role}


@dataclass(frozen=True)
class MechanismCandidate:
    """One proposed explanation for a DivergenceChain's outcome difference: an ordered path of steps.

    `status` starts at `NEEDS_INTERVENTION` -- a candidate is never
    `SUPPORTED` from observation alone (docs/README section 3.2: correlation
    is weaker evidence than intervention). Reaching `SUPPORTED`/`REJECTED`
    requires running a `FollowupExperimentProposal` this module only drafts.
    """
    candidate_id: str
    investigation_target_id: str
    source_role: str
    path: tuple[MechanismStep, ...]
    status: str = "NEEDS_INTERVENTION"

    def __post_init__(self) -> None:
        _text(self.candidate_id, "candidate_id")
        _text(self.investigation_target_id, "investigation_target_id")
        _text(self.source_role, "source_role")
        if not self.path:
            raise ValueError("a mechanism candidate needs at least one path step")
        if self.status not in MECHANISM_STATUSES:
            raise ValueError(f"unsupported mechanism status {self.status!r}")

    @property
    def digest(self) -> str:
        return _digest(self.canonical())

    def canonical(self) -> dict[str, object]:
        return {"candidate_id": self.candidate_id, "format": FORMAT,
                "investigation_target_id": self.investigation_target_id,
                "path": [x.canonical() for x in self.path], "source_role": self.source_role, "status": self.status}


@dataclass(frozen=True)
class MechanismCandidateSet:
    """Every mechanism candidate proposed for one investigation, kept side by side.

    B0.4 never narrows this to one winner: `research_loop`/journal callers
    may later update individual candidates' status as follow-up experiments
    run, but this module does not rank or select among them.
    """
    investigation_target_id: str
    candidates: tuple[MechanismCandidate, ...]

    def __post_init__(self) -> None:
        _text(self.investigation_target_id, "investigation_target_id")
        ids = [item.candidate_id for item in self.candidates]
        if len(set(ids)) != len(ids):
            raise ValueError("mechanism candidate ids must be unique")

    @property
    def digest(self) -> str:
        return _digest(self.canonical())

    def canonical(self) -> dict[str, object]:
        return {"candidates": [x.canonical() for x in sorted(self.candidates, key=lambda c: c.candidate_id)],
                "format": FORMAT, "investigation_target_id": self.investigation_target_id}


@dataclass(frozen=True)
class FollowupExperimentProposal:
    """A proposed (not executed) intervention to discriminate one mechanism candidate from "not this".

    `expected_if_mechanism_true`/`expected_if_mechanism_false` state, in
    text, what the outcome should look like under each possibility -- the
    same discriminating-prediction discipline `PredictionSeal` already
    enforces for B0.1/B0.3 experiments. Running this proposal (an actual
    intervention against causal A) is explicitly out of B0.4's scope.
    """
    proposal_id: str
    mechanism_candidate_id: str
    intervention_target_role: str
    intervention_field: str
    operation: str
    expected_if_mechanism_true: str
    expected_if_mechanism_false: str

    def __post_init__(self) -> None:
        for field_name in ("proposal_id", "mechanism_candidate_id", "intervention_target_role", "intervention_field",
                          "expected_if_mechanism_true", "expected_if_mechanism_false"):
            _text(getattr(self, field_name), field_name)
        if self.operation not in INTERVENTION_OPERATIONS:
            raise ValueError(f"unsupported intervention operation {self.operation!r}")

    @property
    def digest(self) -> str:
        return _digest(self.canonical())

    def canonical(self) -> dict[str, object]:
        return {"expected_if_mechanism_false": self.expected_if_mechanism_false,
                "expected_if_mechanism_true": self.expected_if_mechanism_true, "format": FORMAT,
                "intervention_field": self.intervention_field, "intervention_target_role": self.intervention_target_role,
                "mechanism_candidate_id": self.mechanism_candidate_id, "operation": self.operation,
                "proposal_id": self.proposal_id}


def propose_mechanism_candidates(investigation_target_id: str, events, source_role: str) -> MechanismCandidateSet:
    """Build one straight-line MechanismCandidate per (role) touched by `events`, in observed order.

    `events` is a `DivergenceChain.events` tuple already in phase order. Each
    distinct role that appears becomes its own candidate path from
    `source_role` through every field on that role that diverged, in the
    order the events list already carries -- one candidate per role rather
    than one candidate covering everything, since a single straight path
    through every touched field would silently assert a single mechanism
    where several competing ones are equally consistent with the same
    observation.
    """
    if not events:
        raise ValueError("cannot propose mechanism candidates from an empty divergence chain")
    seen_roles: list[str] = []
    steps_by_role: dict[str, list[MechanismStep]] = {}
    for event in events:
        if event.role not in steps_by_role:
            steps_by_role[event.role] = []
            seen_roles.append(event.role)
        steps_by_role[event.role].append(MechanismStep(event.role, event.field))

    candidates = []
    for role in seen_roles:
        candidate_id = f"MECH-{investigation_target_id}-{role}"
        candidates.append(MechanismCandidate(candidate_id, investigation_target_id, source_role,
                                             tuple(steps_by_role[role])))
    return MechanismCandidateSet(investigation_target_id, tuple(candidates))
