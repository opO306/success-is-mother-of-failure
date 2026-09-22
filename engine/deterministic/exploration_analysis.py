"""Pure analysis over a completed exploration's outcomes: coverage, boundaries, isolated cases.

Like `hypothesis_assessment.py`, this module takes only immutable data and
returns immutable findings -- no journal, no storage, no execution. It never
asserts a threshold value: a `BoundaryCandidate` names the two adjacent
tested points where a status changed, not an inferred cutoff (docs/README's
"we tested points 2 and 3, not that the threshold is 2.5" distinction).
`IsolatedCaseCandidate` is deliberately not an `AnomalyRecord` -- promotion
happens later (B0.4 Deep Investigator territory), after reproduction is
checked; a single outlier out of many trials is a candidate for study, not
yet a confirmed anomaly, and "rare" here means "one of few tested points",
never a probability.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Mapping

FORMAT = "exploration-analysis-v1"


def _digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class CoverageReport:
    """Execution coverage and per-axis coverage, both as exact integer ratios.

    `axis_coverage` counts distinct *tested values* per control id against
    the plan's declared values for that control -- never a float, so
    "1 of 2 materials tested" stays exact rather than rounding to 50%.
    """
    plan_id: str
    planned_count: int
    executed_count: int
    invalid_count: int
    axis_coverage: Mapping[str, tuple[int, int]]

    def canonical(self) -> dict[str, object]:
        return {"axis_coverage": {k: list(v) for k, v in sorted(self.axis_coverage.items())},
                "executed_count": self.executed_count, "format": FORMAT, "invalid_count": self.invalid_count,
                "plan_id": self.plan_id, "planned_count": self.planned_count}


@dataclass(frozen=True, order=True)
class BoundaryCandidate:
    """Two adjacent tested points, on one axis, where the evidence relation changed.

    "Adjacent" means adjacent among the *tested* values on that axis, not
    adjacent in the underlying integers -- if only 2 and 5 were tested and
    they disagree, the boundary is reported as lying between 2 and 5, since
    3 and 4 were never run.
    """
    axis: str
    left_value: object
    left_relation: str
    right_value: object
    right_relation: str

    def canonical(self) -> dict[str, object]:
        return {"axis": self.axis, "format": FORMAT, "left_relation": self.left_relation,
                "left_value": self.left_value, "right_relation": self.right_relation,
                "right_value": self.right_value}


@dataclass(frozen=True, order=True)
class IsolatedCaseCandidate:
    """One candidate whose relation differs from every other tested candidate sharing its axis values.

    Not yet an `AnomalyRecord`: reproduction and hidden-variable checks (B0.4)
    happen before that promotion. This only preserves the observation so nothing
    gets silently averaged away as noise.
    """
    candidate_id: str
    relation: str
    majority_relation: str
    total_candidates: int
    matching_relation_count: int

    def canonical(self) -> dict[str, object]:
        return {"candidate_id": self.candidate_id, "format": FORMAT,
                "majority_relation": self.majority_relation, "matching_relation_count": self.matching_relation_count,
                "relation": self.relation, "total_candidates": self.total_candidates}


def compute_coverage(
    plan_id: str, dimensions: Mapping[str, tuple[object, ...]],
    planned_count: int, tested_values_by_axis: Mapping[str, set[object]],
    executed_count: int, invalid_count: int,
) -> CoverageReport:
    axis_coverage = {
        axis: (len(tested_values_by_axis.get(axis, set())), len(declared_values))
        for axis, declared_values in dimensions.items()
    }
    return CoverageReport(plan_id, planned_count, executed_count, invalid_count, axis_coverage)


def find_boundary_candidates(
    axis: str, points: tuple[tuple[object, str], ...],
) -> tuple[BoundaryCandidate, ...]:
    """Scan one axis's tested (value, relation) pairs, sorted by value, for adjacent disagreements."""
    ordered = tuple(sorted(points, key=lambda item: item[0]))
    boundaries = []
    for (left_value, left_relation), (right_value, right_relation) in zip(ordered, ordered[1:]):
        if left_relation != right_relation:
            boundaries.append(BoundaryCandidate(axis, left_value, left_relation, right_value, right_relation))
    return tuple(boundaries)


def find_isolated_cases(
    candidates: tuple[tuple[str, tuple[object, ...], str], ...],
) -> tuple[IsolatedCaseCandidate, ...]:
    """Group candidates by their non-varying axis values and flag minority relations within each group.

    `candidates` is `(candidate_id, other_axis_values, relation)`: two
    candidates are compared only when every axis except the one under
    scrutiny already matches, so "isolated" means "differs from its
    neighbours holding everything else fixed", not "rare across the whole
    plan".
    """
    groups: dict[tuple[object, ...], list[tuple[str, str]]] = {}
    for candidate_id, other_values, relation in candidates:
        groups.setdefault(other_values, []).append((candidate_id, relation))
    isolated = []
    for members in groups.values():
        if len(members) < 3:
            continue  # too few points in this group to call anything a minority
        counts: dict[str, int] = {}
        for _, relation in members:
            counts[relation] = counts.get(relation, 0) + 1
        majority_relation = max(counts, key=lambda r: counts[r])
        for candidate_id, relation in members:
            if relation != majority_relation:
                isolated.append(IsolatedCaseCandidate(
                    candidate_id, relation, majority_relation, len(members), counts[relation],
                ))
    return tuple(sorted(isolated, key=lambda item: item.candidate_id))
