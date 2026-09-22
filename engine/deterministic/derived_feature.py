"""Derived feature candidates: analysis results computed from existing observables, never new physical state.

A `DerivedFeatureCandidate` such as `heat.energy >= bond.break_heat` is a
relation B computed by reading two already-catalogued values -- it never
becomes a new field A tracks (docs/README's explicit warning: computing
`heat >= break_heat` must never turn into injecting a `break_condition`
state into A). Only a small, fixed set of operations is allowed at this
stage (docs/README section 13); this module does not attempt general
feature engineering or expression search.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

FORMAT = "derived-feature-v1"

# The fixed operation vocabulary docs/README section 13 allows for B0.7 v0.1.
# Comparisons (>, >=, <, <=, ==) and simple arithmetic (-, abs_diff, +, /) only.
DERIVED_OPERATIONS = frozenset({
    "SUBTRACT", "ABS_DIFFERENCE", "ADD", "DIVIDE",
    "GREATER_THAN", "GREATER_OR_EQUAL", "LESS_THAN", "LESS_OR_EQUAL", "EQUAL",
    "DELTA_FROM_PREVIOUS",
})
_UNARY_OPERATIONS = frozenset({"DELTA_FROM_PREVIOUS"})


def _digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _text(value: str, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{context} must be non-empty text")
    return value


@dataclass(frozen=True, order=True)
class ObservableRef:
    """One (role, field) reference into already-collected trace data -- never a newly invented value."""
    role: str
    field: str

    def canonical(self) -> dict[str, object]:
        return {"field": self.field, "role": self.role}


@dataclass(frozen=True)
class DerivedFeatureCandidate:
    """A caller-proposed relation over one or two existing observables, using a fixed operation vocabulary.

    `right` is `None` only for `DELTA_FROM_PREVIOUS` (a unary operation over
    one observable's own history). This dataclass never evaluates itself
    against a trace -- `evaluate_derived_feature` does that, taking the
    actual observed values as plain arguments, so this type stays pure
    description.
    """
    candidate_id: str
    operation: str
    left: ObservableRef
    right: ObservableRef | None = None

    def __post_init__(self) -> None:
        _text(self.candidate_id, "candidate_id")
        if self.operation not in DERIVED_OPERATIONS:
            raise ValueError(f"unsupported derived feature operation {self.operation!r}")
        is_unary = self.operation in _UNARY_OPERATIONS
        if is_unary and self.right is not None:
            raise ValueError(f"{self.operation} is unary and must not have a right observable")
        if not is_unary and self.right is None:
            raise ValueError(f"{self.operation} requires a right observable")

    @property
    def digest(self) -> str:
        return _digest(self.canonical())

    def canonical(self) -> dict[str, object]:
        result = {"candidate_id": self.candidate_id, "format": FORMAT, "left": self.left.canonical(),
                  "operation": self.operation}
        if self.right is not None:
            result["right"] = self.right.canonical()
        return result


def evaluate_derived_feature(operation: str, left_value, right_value=None):
    """Compute one derived feature's value. Raises ValueError on a division by zero rather than crashing silently."""
    if operation == "SUBTRACT":
        return left_value - right_value
    if operation == "ABS_DIFFERENCE":
        return abs(left_value - right_value)
    if operation == "ADD":
        return left_value + right_value
    if operation == "DIVIDE":
        if right_value == 0:
            raise ValueError("cannot divide by zero")
        return left_value / right_value
    if operation == "GREATER_THAN":
        return left_value > right_value
    if operation == "GREATER_OR_EQUAL":
        return left_value >= right_value
    if operation == "LESS_THAN":
        return left_value < right_value
    if operation == "LESS_OR_EQUAL":
        return left_value <= right_value
    if operation == "EQUAL":
        return left_value == right_value
    if operation == "DELTA_FROM_PREVIOUS":
        return left_value - right_value if right_value is not None else None
    raise ValueError(f"unsupported derived feature operation {operation!r}")


def candidate_relevant_to_gap(
    candidate: DerivedFeatureCandidate, source_role: str, target_role: str, related_roles: frozenset[str],
) -> bool:
    """Docs/README section 14's relevance filter: a candidate must touch roles actually near this gap.

    Prevents the combinatorial explosion of pairing every observable with
    every other -- a candidate is only worth proposing if at least one side
    references the gap's own source/target role or another role already
    known to be related (e.g. co-occurring in the same AtomicChangeGroup).
    """
    allowed = related_roles | {source_role, target_role}
    sides = (candidate.left.role,) + ((candidate.right.role,) if candidate.right is not None else ())
    return any(role in allowed for role in sides)
