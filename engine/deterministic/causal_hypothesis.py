"""Causal-A-specific hypotheses and typed predictions for the B0 research loop.

Deliberately separate from `hypotheses.py`'s `WorldHypothesis`/`HypothesisSet`,
which are environment-theory types (vapor, rule classes, `ApprovedChangeView`)
and keep their existing meaning unchanged. A hypothesis about causal A predicts
causal-A observables -- state digests, conserved quantities, bond counts -- and
giving it the same class as an environment hypothesis would only make
`predicted_observables: Mapping[str, Any]` an envelope for two unrelated
vocabularies. Only genuinely model-neutral parts are shared: `EvidenceReference`
and `RationalWeight` from `hypotheses.py`, and the digest/canonical discipline
from `b_language.py`.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Union

from .evidence import EvidenceReference, RationalWeight
from .interventional_prediction import InterventionalPrediction
from .research_observable_prediction import ObservablePrediction
from .research_state import HYPOTHESIS_STATUSES

FORMAT = "causal-hypothesis-v1"


def _digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _text(value: str, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{context} must be non-empty text")
    return value


def _texts(values: tuple[str, ...], context: str, allow_empty: bool = True) -> tuple[str, ...]:
    if not isinstance(values, tuple):
        raise ValueError(f"{context} must be a tuple")
    result = tuple(_text(value, context) for value in values)
    if not allow_empty and not result:
        raise ValueError(f"{context} cannot be empty")
    if len(set(result)) != len(result):
        raise ValueError(f"{context} values must be unique")
    return result


@dataclass(frozen=True)
class StateDigestPrediction:
    """The full world state at `tick` will hash to `expected_digest`."""
    tick: int
    expected_digest: str

    def __post_init__(self) -> None:
        if isinstance(self.tick, bool) or not isinstance(self.tick, int) or self.tick < 0:
            raise ValueError("tick must be a nonnegative integer")
        _text(self.expected_digest, "expected_digest")

    def canonical(self) -> dict[str, object]:
        return {"expected_digest": self.expected_digest, "kind": "state_digest", "tick": self.tick}


@dataclass(frozen=True)
class ConservationPrediction:
    """Total energy at `tick` will equal `expected_total_energy`.

    A separate type from momentum: causal A already treats energy and
    momentum as independently checked conserved quantities (see
    `step_causal_world`'s two separate `AssertionError`s), so a prediction
    that conflated them could be "half right" in a way neither this type nor
    its momentum sibling can be.
    """
    tick: int
    expected_total_energy: int

    def __post_init__(self) -> None:
        if isinstance(self.tick, bool) or not isinstance(self.tick, int) or self.tick < 0:
            raise ValueError("tick must be a nonnegative integer")
        if isinstance(self.expected_total_energy, bool) or not isinstance(self.expected_total_energy, int):
            raise ValueError("expected_total_energy must be an integer")

    def canonical(self) -> dict[str, object]:
        return {"expected_total_energy": self.expected_total_energy, "kind": "conservation", "tick": self.tick}


@dataclass(frozen=True)
class MomentumPrediction:
    """Total free-body momentum at `tick` will equal `expected_momentum`."""
    tick: int
    expected_momentum: tuple[int, int]

    def __post_init__(self) -> None:
        if isinstance(self.tick, bool) or not isinstance(self.tick, int) or self.tick < 0:
            raise ValueError("tick must be a nonnegative integer")
        if (not isinstance(self.expected_momentum, tuple) or len(self.expected_momentum) != 2
                or any(isinstance(v, bool) or not isinstance(v, int) for v in self.expected_momentum)):
            raise ValueError("expected_momentum must be a pair of integers")

    def canonical(self) -> dict[str, object]:
        return {"expected_momentum": list(self.expected_momentum), "kind": "momentum", "tick": self.tick}


@dataclass(frozen=True)
class BondCountPrediction:
    """The number of bonds (v1/v2 `PhysicalBond` plus v3/v4 `PortBond`) at `tick`."""
    tick: int
    expected_bond_count: int

    def __post_init__(self) -> None:
        if isinstance(self.tick, bool) or not isinstance(self.tick, int) or self.tick < 0:
            raise ValueError("tick must be a nonnegative integer")
        if isinstance(self.expected_bond_count, bool) or not isinstance(self.expected_bond_count, int) or self.expected_bond_count < 0:
            raise ValueError("expected_bond_count must be a nonnegative integer")

    def canonical(self) -> dict[str, object]:
        return {"expected_bond_count": self.expected_bond_count, "kind": "bond_count", "tick": self.tick}


@dataclass(frozen=True)
class MaterialCountsPrediction:
    """Particle counts per material kind at `tick` will equal `expected_counts`."""
    tick: int
    expected_counts: tuple[tuple[int, int], ...]

    def __post_init__(self) -> None:
        if isinstance(self.tick, bool) or not isinstance(self.tick, int) or self.tick < 0:
            raise ValueError("tick must be a nonnegative integer")
        kinds = [kind for kind, _ in self.expected_counts]
        if len(set(kinds)) != len(kinds):
            raise ValueError("expected_counts kinds must be unique")
        for kind, count in self.expected_counts:
            if isinstance(kind, bool) or not isinstance(kind, int):
                raise ValueError("material kind must be an integer")
            if isinstance(count, bool) or not isinstance(count, int) or count < 0:
                raise ValueError("material count must be a nonnegative integer")

    def canonical(self) -> dict[str, object]:
        return {"expected_counts": {str(k): v for k, v in sorted(self.expected_counts)},
                "kind": "material_counts", "tick": self.tick}


CausalPrediction = Union[
    StateDigestPrediction, ConservationPrediction, MomentumPrediction,
    BondCountPrediction, MaterialCountsPrediction,
]

# The actual domain `CausalHypothesis.predictions` accepts: physical A's five
# CausalPrediction kinds, plus the two world-agnostic kinds this project
# added after CausalPrediction was closed (ObservablePrediction, G6c-3;
# InterventionalPrediction, G7.0's representation repair). CausalPrediction
# itself is left untouched -- widening it would make every physical-A-only
# caller matching on `Union[StateDigestPrediction, ...]` also need to handle
# two kinds it can never actually receive. ResearchPrediction is the type a
# hypothesis's own `predictions` field actually promises; the earlier
# `predictions: tuple[CausalPrediction, ...]` hint was correct in practice
# only because nothing checked it -- documenting a wider domain without
# widening the type is exactly the "Python doesn't stop it" trap G7.0's
# repair exists to close.
ResearchPrediction = Union[CausalPrediction, ObservablePrediction, InterventionalPrediction]


@dataclass(frozen=True)
class CausalHypothesis:
    """A claim about causal A, scoped to the domain where it is meant to hold.

    `status` is never collapsed to true/false: `applicability_conditions`
    names where the claim is meant to apply, and `status` records what has
    been learned so far within that scope. A hypothesis contradicted in one
    domain keeps `contradicted_in_domain` rather than being deleted or marked
    globally false -- a later hypothesis may narrow or extend its domain.

    `predictions` is typed `ResearchPrediction`, not `CausalPrediction` --
    physical A's five kinds, plus `ObservablePrediction` and
    `InterventionalPrediction`, all equally sanctioned (see
    `ResearchPrediction`'s own comment above). `InterventionalPrediction`
    in particular is how a hypothesis expresses "under this specific
    intervention, this observable will be this value" -- a bare
    `CausalPrediction`/`ObservablePrediction` has no control-value context,
    so a hypothesis whose predictions vary by intervention needs this kind
    to say which intervention each prediction holds under.
    """
    hypothesis_id: str
    statement: str
    applicability_conditions: tuple[str, ...]
    predictions: tuple[ResearchPrediction, ...]
    evidence: tuple[EvidenceReference, ...]
    status: str
    parent_hypothesis_ids: tuple[str, ...] = ()
    child_hypothesis_ids: tuple[str, ...] = ()
    weight: RationalWeight | None = None

    def __post_init__(self) -> None:
        _text(self.hypothesis_id, "hypothesis_id")
        _text(self.statement, "statement")
        _texts(self.applicability_conditions, "applicability_conditions")
        if not isinstance(self.predictions, tuple) or not self.predictions:
            raise ValueError("predictions must be a non-empty tuple")
        if not isinstance(self.evidence, tuple):
            raise ValueError("evidence must be a tuple")
        if self.status not in HYPOTHESIS_STATUSES:
            raise ValueError(f"unsupported hypothesis status {self.status!r}")
        _texts(self.parent_hypothesis_ids, "parent_hypothesis_ids")
        _texts(self.child_hypothesis_ids, "child_hypothesis_ids")

    @property
    def digest(self) -> str:
        return _digest(self.canonical())

    def canonical(self) -> dict[str, object]:
        result = {
            "applicability_conditions": list(self.applicability_conditions),
            "child_hypothesis_ids": list(self.child_hypothesis_ids),
            "evidence": [x.canonical() for x in self.evidence], "format": FORMAT,
            "hypothesis_id": self.hypothesis_id,
            "parent_hypothesis_ids": list(self.parent_hypothesis_ids),
            "predictions": [x.canonical() for x in self.predictions],
            "statement": self.statement, "status": self.status,
        }
        if self.weight is not None:
            result["weight"] = self.weight.canonical()
        return result


@dataclass(frozen=True)
class CausalHypothesisSet:
    """A group of nonexclusive hypotheses B is holding open about one causal A subject.

    Unlike `hypotheses.HypothesisSet`, this is not scoped to a single next
    tick: a hypothesis may make predictions across many ticks (a boundary
    search over a temperature range, a claim about tick-10 stability), so
    nothing here fixes `source_tick`/`target_tick` to one pair.
    """
    subject_digest: str
    hypotheses: tuple[CausalHypothesis, ...]

    def __post_init__(self) -> None:
        _text(self.subject_digest, "subject_digest")
        ids = [item.hypothesis_id for item in self.hypotheses]
        if not ids or len(set(ids)) != len(ids):
            raise ValueError("hypothesis ids must be unique and non-empty")

    @property
    def digest(self) -> str:
        return _digest(self.canonical())

    def canonical(self) -> dict[str, object]:
        return {"format": FORMAT, "hypotheses": [x.canonical() for x in self.hypotheses],
                "message_type": "causal_hypothesis_set", "subject_digest": self.subject_digest}
