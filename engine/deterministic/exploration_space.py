"""Finite, deterministic Cartesian sweeps over control values.

B0.3's first version is deliberately a full factorial sweep with no
sampling, no adaptive narrowing, no randomness: the goal is to prove the
plan -> candidate -> execute -> evidence -> coverage pipeline is correct
before any search strategy is layered on top (see docs/README/04's
broad/deep distinction -- "broad" names a research strategy, not a sampling
algorithm). A plan whose full Cartesian product exceeds `max_candidates` is
rejected outright, never silently truncated: truncating the front of a
sweep introduces an unstated bias no later reader could detect from the
journal alone.
"""
from __future__ import annotations

import hashlib
import itertools
import json
from dataclasses import dataclass

FORMAT = "exploration-space-v1"
STRATEGIES = frozenset({"full_factorial"})


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


@dataclass(frozen=True, order=True)
class SweepDimension:
    control_id: str
    values: tuple[object, ...]

    def __post_init__(self) -> None:
        _text(self.control_id, "control_id")
        if not self.values:
            raise ValueError("a sweep dimension needs at least one value")
        if len(set(self.values)) != len(self.values):
            raise ValueError("sweep dimension values must be unique")
        for value in self.values:
            if isinstance(value, bool) or not isinstance(value, (int, str)):
                raise ValueError("sweep dimension values must be integers or text")

    def canonical(self) -> dict[str, object]:
        return {"control_id": self.control_id, "values": list(self.values)}


@dataclass(frozen=True)
class ExplorationPlan:
    plan_id: str
    base_spec_digest: str
    target_hypothesis_ids: tuple[str, ...]
    dimensions: tuple[SweepDimension, ...]
    strategy: str
    max_candidates: int

    def __post_init__(self) -> None:
        _text(self.plan_id, "plan_id")
        _text(self.base_spec_digest, "base_spec_digest")
        _texts(self.target_hypothesis_ids, "target_hypothesis_ids")
        if not self.dimensions:
            raise ValueError("a plan needs at least one sweep dimension")
        control_ids = [item.control_id for item in self.dimensions]
        if len(set(control_ids)) != len(control_ids):
            raise ValueError("a plan cannot sweep the same control twice")
        if self.strategy not in STRATEGIES:
            raise ValueError(f"unsupported exploration strategy {self.strategy!r}")
        if isinstance(self.max_candidates, bool) or not isinstance(self.max_candidates, int) or self.max_candidates < 1:
            raise ValueError("max_candidates must be a positive integer")

    @property
    def planned_candidate_count(self) -> int:
        total = 1
        for dimension in self.dimensions:
            total *= len(dimension.values)
        return total

    @property
    def digest(self) -> str:
        return _digest(self.canonical())

    def canonical(self) -> dict[str, object]:
        return {"base_spec_digest": self.base_spec_digest,
                "dimensions": [x.canonical() for x in sorted(self.dimensions)], "format": FORMAT,
                "max_candidates": self.max_candidates, "plan_id": self.plan_id,
                "planned_candidate_count": self.planned_candidate_count, "strategy": self.strategy,
                "target_hypothesis_ids": list(self.target_hypothesis_ids)}


class ExplorationBudgetExceeded(ValueError):
    def __init__(self, requested: int, budget: int) -> None:
        super().__init__(f"exploration plan requests {requested} candidates, over the budget of {budget}")
        self.requested = requested
        self.budget = budget


@dataclass(frozen=True, order=True)
class ExplorationCandidate:
    """One point in a plan's control space, identified deterministically.

    `candidate_id` is derived from `plan_id` plus the canonical control
    values, not assigned sequentially: the same plan run twice (or resumed)
    produces the same candidate ids, which is what makes candidate/spec reuse
    detectable rather than coincidental.
    """
    candidate_id: str
    plan_id: str
    control_values: tuple[tuple[str, object], ...]

    def canonical(self) -> dict[str, object]:
        return {"candidate_id": self.candidate_id, "control_values": [list(pair) for pair in self.control_values],
                "plan_id": self.plan_id, "format": FORMAT}


def _candidate_id(plan_id: str, control_values: tuple[tuple[str, object], ...]) -> str:
    return f"CAND-{_digest({'control_values': control_values, 'plan_id': plan_id})[:16]}"


def generate_candidates(plan: ExplorationPlan) -> tuple[ExplorationCandidate, ...]:
    """Deterministically enumerate a plan's full Cartesian product.

    Raises `ExplorationBudgetExceeded` rather than truncating when the
    product exceeds `plan.max_candidates` -- see this module's docstring.
    """
    count = plan.planned_candidate_count
    if count > plan.max_candidates:
        raise ExplorationBudgetExceeded(count, plan.max_candidates)
    dimensions = sorted(plan.dimensions)
    control_ids = tuple(item.control_id for item in dimensions)
    candidates = []
    for combination in itertools.product(*(item.values for item in dimensions)):
        control_values = tuple(zip(control_ids, combination))
        candidates.append(ExplorationCandidate(_candidate_id(plan.plan_id, control_values), plan.plan_id, control_values))
    return tuple(candidates)
