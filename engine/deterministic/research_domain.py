"""Computable regions of condition-space, distinct from any one world spec.

A `ResearchDomain` is a research coordinate ("equal-energy head-on collisions
between two kind-0 particles"), not a copy of a `CausalWorldSpec` -- the
originating world is always traced by its digest separately. Domains support
overlap/contains/intersection/matches so a research loop can eventually ask
"has anything like this already been tried" without re-deriving conditions
from free-text descriptions.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Union

from .research_axis import AxisRegistry

FORMAT = "research-domain-v1"


def _digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _text(value: str, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{context} must be non-empty text")
    return value


@dataclass(frozen=True, order=True)
class ExactConstraint:
    axis: str
    value: object

    def __post_init__(self) -> None:
        _text(self.axis, "axis")
        if isinstance(self.value, bool) or not isinstance(self.value, (int, str)):
            raise ValueError("ExactConstraint value must be an integer or text")

    def canonical(self) -> dict[str, object]:
        return {"axis": self.axis, "kind": "exact", "value": self.value}

    def matches(self, point: object) -> bool:
        return point == self.value

    def _overlaps_exact(self, other: "ExactConstraint") -> bool:
        return self.value == other.value

    def _overlaps_set(self, other: "SetConstraint") -> bool:
        return self.value in other.values

    def _overlaps_range(self, other: "IntegerRangeConstraint") -> bool:
        return other.minimum <= self.value <= other.maximum


@dataclass(frozen=True, order=True)
class SetConstraint:
    axis: str
    values: tuple[object, ...]

    def __post_init__(self) -> None:
        _text(self.axis, "axis")
        if not self.values:
            raise ValueError("SetConstraint values must be non-empty")
        if len(set(self.values)) != len(self.values):
            raise ValueError("SetConstraint values must be unique")
        for value in self.values:
            if isinstance(value, bool) or not isinstance(value, (int, str)):
                raise ValueError("SetConstraint values must be integers or text")

    def canonical(self) -> dict[str, object]:
        return {"axis": self.axis, "kind": "set", "values": sorted(self.values, key=str)}

    def matches(self, point: object) -> bool:
        return point in self.values

    def _overlaps_exact(self, other: ExactConstraint) -> bool:
        return other.value in self.values

    def _overlaps_set(self, other: "SetConstraint") -> bool:
        return bool(set(self.values) & set(other.values))

    def _overlaps_range(self, other: "IntegerRangeConstraint") -> bool:
        return any(other.minimum <= value <= other.maximum for value in self.values
                   if isinstance(value, int) and not isinstance(value, bool))


@dataclass(frozen=True, order=True)
class IntegerRangeConstraint:
    axis: str
    minimum: int
    maximum: int

    def __post_init__(self) -> None:
        _text(self.axis, "axis")
        if isinstance(self.minimum, bool) or not isinstance(self.minimum, int):
            raise ValueError("minimum must be an integer")
        if isinstance(self.maximum, bool) or not isinstance(self.maximum, int):
            raise ValueError("maximum must be an integer")
        if self.minimum > self.maximum:
            raise ValueError("minimum must not exceed maximum")

    def canonical(self) -> dict[str, object]:
        return {"axis": self.axis, "kind": "range", "maximum": self.maximum, "minimum": self.minimum}

    def matches(self, point: object) -> bool:
        return isinstance(point, int) and not isinstance(point, bool) and self.minimum <= point <= self.maximum

    def _overlaps_exact(self, other: ExactConstraint) -> bool:
        return isinstance(other.value, int) and self.minimum <= other.value <= self.maximum

    def _overlaps_set(self, other: SetConstraint) -> bool:
        return any(isinstance(value, int) and not isinstance(value, bool) and self.minimum <= value <= self.maximum
                   for value in other.values)

    def _overlaps_range(self, other: "IntegerRangeConstraint") -> bool:
        return self.minimum <= other.maximum and other.minimum <= self.maximum

    def intersect_range(self, other: "IntegerRangeConstraint") -> "IntegerRangeConstraint | None":
        low, high = max(self.minimum, other.minimum), min(self.maximum, other.maximum)
        return IntegerRangeConstraint(self.axis, low, high) if low <= high else None


Constraint = Union[ExactConstraint, SetConstraint, IntegerRangeConstraint]


_KIND_SUFFIX = {ExactConstraint: "exact", SetConstraint: "set", IntegerRangeConstraint: "range"}


def _constraint_overlaps(left: Constraint, right: Constraint) -> bool:
    if left.axis != right.axis:
        raise ValueError("constraints on different axes are not comparable for overlap")
    suffix = _KIND_SUFFIX.get(type(right))
    method = getattr(left, f"_overlaps_{suffix}", None) if suffix else None
    if method is not None:
        return method(right)
    suffix = _KIND_SUFFIX.get(type(left))
    method = getattr(right, f"_overlaps_{suffix}", None) if suffix else None
    if method is not None:
        return method(left)
    raise TypeError(f"unsupported constraint pair {type(left).__name__}/{type(right).__name__}")


def _constraint_intersection(left: Constraint, right: Constraint) -> Constraint | None:
    if not _constraint_overlaps(left, right):
        return None
    if isinstance(left, IntegerRangeConstraint) and isinstance(right, IntegerRangeConstraint):
        return left.intersect_range(right)
    if isinstance(left, ExactConstraint):
        return left
    if isinstance(right, ExactConstraint):
        return right
    if isinstance(left, SetConstraint) and isinstance(right, SetConstraint):
        shared = tuple(sorted(set(left.values) & set(right.values), key=str))
        return SetConstraint(left.axis, shared) if shared else None
    # set vs range: narrow the set to values the range admits
    set_side, range_side = (left, right) if isinstance(left, SetConstraint) else (right, left)
    narrowed = tuple(v for v in set_side.values if isinstance(v, int) and not isinstance(v, bool)
                     and range_side.minimum <= v <= range_side.maximum)
    return SetConstraint(set_side.axis, narrowed) if narrowed else None


@dataclass(frozen=True)
class ResearchDomain:
    """A named region of condition-space: at most one constraint per axis.

    Every axis named by a constraint must be registered in `registry`
    (`CAUSAL_AXIS_REGISTRY` for causal-A domains), which is checked at
    construction time rather than left to fail later at comparison time.
    """
    domain_id: str
    constraints: tuple[Constraint, ...]
    description: str = ""

    def __post_init__(self) -> None:
        _text(self.domain_id, "domain_id")
        axes = [item.axis for item in self.constraints]
        if len(set(axes)) != len(axes):
            raise ValueError("a domain may hold at most one constraint per axis")

    def validate_against(self, registry: AxisRegistry) -> None:
        for constraint in self.constraints:
            operator = {"exact": "eq", "set": "set", "range": "range"}[constraint.canonical()["kind"]]
            registry.require_operator(constraint.axis, operator)

    @property
    def digest(self) -> str:
        return _digest(self.canonical())

    def canonical(self) -> dict[str, object]:
        return {"constraints": sorted((x.canonical() for x in self.constraints), key=lambda c: c["axis"]),
                "description": self.description, "domain_id": self.domain_id, "format": FORMAT}

    def _by_axis(self) -> dict[str, Constraint]:
        return {item.axis: item for item in self.constraints}

    def overlaps(self, other: "ResearchDomain") -> bool:
        left, right = self._by_axis(), other._by_axis()
        shared_axes = set(left) & set(right)
        return all(_constraint_overlaps(left[axis], right[axis]) for axis in shared_axes)

    def contains(self, other: "ResearchDomain") -> bool:
        left, right = self._by_axis(), other._by_axis()
        if not set(left) <= set(right):
            return False
        for axis, constraint in left.items():
            intersection = _constraint_intersection(constraint, right[axis])
            if intersection is None or intersection.canonical() != right[axis].canonical():
                return False
        return True

    def intersection(self, other: "ResearchDomain") -> "ResearchDomain | None":
        left, right = self._by_axis(), other._by_axis()
        if not self.overlaps(other):
            return None
        combined: dict[str, Constraint] = dict(left)
        for axis, constraint in right.items():
            if axis in combined:
                merged = _constraint_intersection(combined[axis], constraint)
                if merged is None:
                    return None
                combined[axis] = merged
            else:
                combined[axis] = constraint
        return ResearchDomain(f"{self.domain_id}∩{other.domain_id}", tuple(combined.values()))

    def matches(self, point: dict[str, object]) -> bool:
        for constraint in self.constraints:
            if constraint.axis not in point or not constraint.matches(point[constraint.axis]):
                return False
        return True
