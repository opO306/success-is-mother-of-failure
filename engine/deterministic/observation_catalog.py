"""What causal A officially lets B look at -- the boundary B0.7 must never cross by inventing a value.

Wraps the same field sets `trace_model.py` already declares
(`PARTICLE_TRACE_FIELDS`/`HEAT_TRACE_FIELDS`/`BOND_TRACE_FIELDS`) rather than
inventing a second list: those are already "the officially observable
surface", since they are exactly what `TraceSpec` subjects are allowed to
request. `ObservationCatalog` exists so B0.7 code asks a structured question
("is (role_kind, field) observable?") instead of re-deriving the answer from
`trace_model`'s internals, and so a `MissingLinkHypothesis` naming a mediator
candidate can be checked against this catalog before anything is proposed.

Feasibility here mirrors `intervention_feasibility.py`'s discipline
(AVAILABLE/UNAVAILABLE/AMBIGUOUS/INVALID): "can we observe this" is answered
honestly, including "no" -- B0.7 never reads a private engine value just
because it exists in the source code.
"""
from __future__ import annotations

from dataclasses import dataclass

from .trace_model import BOND_TRACE_FIELDS, HEAT_TRACE_FIELDS, PARTICLE_TRACE_FIELDS

FORMAT = "observation-catalog-v1"
OBSERVATION_FEASIBILITY_STATUSES = frozenset({"AVAILABLE", "UNAVAILABLE", "AMBIGUOUS", "INVALID"})

ROLE_KINDS = frozenset({"particle", "heat_cell", "bond"})
_FIELDS_BY_ROLE_KIND = {"particle": PARTICLE_TRACE_FIELDS, "heat_cell": HEAT_TRACE_FIELDS, "bond": BOND_TRACE_FIELDS}


@dataclass(frozen=True, order=True)
class ObservableField:
    """One (role_kind, field) causal A officially exposes through `trace_model.TraceSubject`s."""
    role_kind: str
    field: str

    def canonical(self) -> dict[str, object]:
        return {"field": self.field, "format": FORMAT, "role_kind": self.role_kind}


@dataclass(frozen=True)
class ObservationCatalog:
    """The fixed, closed set of (role_kind, field) pairs B may ever propose observing.

    Built once from `trace_model.py`'s existing field declarations --
    `default_catalog()` is the only constructor B0.7 code should use, so the
    catalog can never silently drift out of sync with what `TraceSpec`
    actually accepts.
    """
    fields: tuple[ObservableField, ...]

    def __post_init__(self) -> None:
        pairs = [(f.role_kind, f.field) for f in self.fields]
        if len(set(pairs)) != len(pairs):
            raise ValueError("observation catalog entries must be unique (role_kind, field) pairs")

    def contains(self, role_kind: str, field: str) -> bool:
        return any(f.role_kind == role_kind and f.field == field for f in self.fields)

    def fields_for(self, role_kind: str) -> tuple[str, ...]:
        return tuple(sorted(f.field for f in self.fields if f.role_kind == role_kind))

    def canonical(self) -> dict[str, object]:
        return {"fields": [f.canonical() for f in sorted(self.fields)], "format": FORMAT}


def default_catalog() -> ObservationCatalog:
    """The catalog derived from `trace_model.py`'s current officially traceable fields."""
    fields = tuple(ObservableField(role_kind, field) for role_kind in sorted(ROLE_KINDS)
                  for field in sorted(_FIELDS_BY_ROLE_KIND[role_kind]))
    return ObservationCatalog(fields)


@dataclass(frozen=True)
class ObservationFeasibility:
    """Whether observing one (role_kind, field) pair is possible at all -- never whether it is worthwhile.

    `UNAVAILABLE` is the honest, structural answer for a value causal A does
    not expose through its public observation interface -- this is what
    stands between B0.7 and "just read the private state, it's right there
    in the source code".
    """
    role_kind: str
    field: str
    status: str
    reason: str

    def __post_init__(self) -> None:
        if self.status not in OBSERVATION_FEASIBILITY_STATUSES:
            raise ValueError(f"unsupported observation feasibility status {self.status!r}")
        if not isinstance(self.reason, str) or not self.reason.strip():
            raise ValueError("reason must be non-empty text")

    def canonical(self) -> dict[str, object]:
        return {"field": self.field, "format": FORMAT, "reason": self.reason, "role_kind": self.role_kind,
                "status": self.status}


def assess_observation_feasibility(catalog: ObservationCatalog, role_kind: str, field: str) -> ObservationFeasibility:
    """Check whether (role_kind, field) is in `catalog`. Never raises -- an unobservable value is B0.7 data too."""
    if role_kind not in ROLE_KINDS:
        return ObservationFeasibility(role_kind, field, "INVALID", f"unrecognized role kind {role_kind!r}")
    if catalog.contains(role_kind, field):
        return ObservationFeasibility(role_kind, field, "AVAILABLE",
                                      "this field is part of causal A's official observation catalog")
    return ObservationFeasibility(role_kind, field, "UNAVAILABLE",
                                  f"causal A does not expose {role_kind}.{field} through its public observation interface")
