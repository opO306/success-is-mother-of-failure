"""Pure comparison of two phase-level traces: where they first differ, and how the difference spreads.

Like `hypothesis_assessment.py` and `exploration_analysis.py`, this module
takes only immutable `TraceSnapshot` sequences and returns immutable
findings -- no journal, no execution, no A. It never claims a mechanism: a
`DivergenceChain` is an `OBSERVED_SEQUENCE`, the order two traces' fields
actually diverged in, not a claim that the earlier difference *caused* the
later one. Turning a chain into a claim worth checking is `mechanism_candidate.py`'s job.

An intervention is recorded as an *action* (`InterventionRecord`: target,
assigned value, applied tick, mode), not just a value pair, because how a
control's difference persists changes what later agreement or disagreement
on that same field means:

- `SET_ONCE`: assigned once at `applied_at_tick`; the field is then free to
  evolve under A's own rules. As long as the two traces' values on this
  field stay exactly what was assigned, the (unchanging) difference is
  `INTERVENTION_PERSISTED` -- nothing has happened yet, the initial
  difference is simply still there. Only once A actually changes the value
  away from what was assigned does a further difference become
  `ENDOGENOUS_RESPONSE`.
- `CLAMP`: held at the assigned value for the intervention's duration. A
  difference on this field for as long as the clamp holds is
  `INTERVENTION_MAINTAINED` -- indistinguishable in *cause* from
  `INTERVENTION_PERSISTED`, but named separately because a clamp is actively
  enforced every phase rather than merely not yet touched.
- `PULSE`: assigned only at `applied_at_tick` and released afterward -- like
  `SET_ONCE` but the caller marks exactly when the forcing stops.

The crucial point this buys: `FirstResponseDivergence` is never "the
earliest tick where two traces differ" -- an intervention guarantees that at
tick 0. It is the earliest point where A's own rules produced a *new*
difference: either a field the intervention never touched, or the
intervened field taking on a value different from what was assigned.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from .causal_kernel import KernelPhase
from .trace_model import TraceSnapshot

FORMAT = "divergence-analysis-v1"

DIVERGENCE_KINDS = frozenset({"STATE", "ENERGY", "POSITION", "TOPOLOGY", "RELATION", "STRUCTURAL", "EVENT", "OUTPUT"})
DIVERGENCE_ORIGINS = frozenset({
    "DIRECT_INTERVENTION", "INTERVENTION_PERSISTED", "INTERVENTION_MAINTAINED", "ENDOGENOUS_RESPONSE", "UNKNOWN",
})
INTERVENTION_MODES = frozenset({"SET_ONCE", "CLAMP", "PULSE"})
_RESPONSE_ORIGINS = frozenset({"ENDOGENOUS_RESPONSE", "UNKNOWN"})

_FIELD_KIND = {
    "x": "POSITION", "y": "POSITION", "direction": "STATE", "orientation": "STATE",
    "kinetic_energy": "ENERGY", "energy": "ENERGY", "exists": "TOPOLOGY", "stored_energy": "ENERGY",
}

# Kernel phases in the fixed order the observer emits them within one tick,
# used only to order two same-tick snapshots -- never to guess an order the
# kernel did not itself report.
_PHASE_ORDER = {KernelPhase.PRE_TICK: 0, KernelPhase.AFTER_BOND_BREAK_PHASE: 1, KernelPhase.POST_TICK: 2}


def _digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _text(value: str, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{context} must be non-empty text")
    return value


def classify_field_divergence(field: str) -> str:
    """Best-effort divergence kind for a known trace field. Unrecognized fields are STATE."""
    return _FIELD_KIND.get(field, "STATE")


@dataclass(frozen=True, order=True)
class InterventionRecord:
    """One control deliberately applied to produce the right-hand trace, as an action rather than a value.

    `left_value`/`right_value` are the values *as assigned*, at
    `applied_at_tick` -- what the field actually does afterward is read from
    the traces, not asserted here.
    """
    role: str
    field: str
    left_value: Any
    right_value: Any
    applied_at_tick: int
    mode: str

    def __post_init__(self) -> None:
        _text(self.role, "role")
        _text(self.field, "field")
        if self.mode not in INTERVENTION_MODES:
            raise ValueError(f"unsupported intervention mode {self.mode!r}")
        if isinstance(self.applied_at_tick, bool) or not isinstance(self.applied_at_tick, int) or self.applied_at_tick < 0:
            raise ValueError("applied_at_tick must be a nonnegative integer")

    def canonical(self) -> dict[str, object]:
        return {"applied_at_tick": self.applied_at_tick, "field": self.field, "format": FORMAT,
                "left_value": self.left_value, "mode": self.mode, "right_value": self.right_value, "role": self.role}


@dataclass(frozen=True, order=True)
class DivergenceEvent:
    """One (role, field) difference at one kernel phase, tagged with a divergence kind and origin."""
    tick: int
    phase: KernelPhase
    role: str
    field: str
    left_value: Any
    right_value: Any
    divergence_kind: str
    origin: str

    def __post_init__(self) -> None:
        if self.divergence_kind not in DIVERGENCE_KINDS:
            raise ValueError(f"unsupported divergence kind {self.divergence_kind!r}")
        if self.origin not in DIVERGENCE_ORIGINS:
            raise ValueError(f"unsupported divergence origin {self.origin!r}")

    def canonical(self) -> dict[str, object]:
        return {"divergence_kind": self.divergence_kind, "field": self.field, "format": FORMAT,
                "left_value": self.left_value, "origin": self.origin, "phase": self.phase.value,
                "right_value": self.right_value, "role": self.role, "tick": self.tick}


@dataclass(frozen=True)
class FirstResponseMoment:
    """Every `DivergenceEvent` whose origin is `ENDOGENOUS_RESPONSE`/`UNKNOWN`, at the earliest such (tick, phase).

    Deliberately not "the first field that responded": when several fields
    change together at the same (tick, phase), picking one by alphabetical
    (role, field) order would manufacture a claim the evidence never made --
    that this one field was somehow the leading response and the others
    followed it. The question this type answers is "when did the world
    first react, and what changed together in that moment", not "which
    field reacted first" -- exactly the atomic-event discipline
    `causal_timeline.AtomicChangeGroup` already applies on the single-trace
    side of B0.6.

    `DIRECT_INTERVENTION` and `INTERVENTION_MAINTAINED`/`INTERVENTION_PERSISTED`
    events are excluded by construction: they are the experiment's own
    design (or its continued enforcement/persistence), not the world's
    reaction to it.
    """
    tick: int
    phase: KernelPhase
    changes: tuple[DivergenceEvent, ...]

    def __post_init__(self) -> None:
        if not self.changes:
            raise ValueError("a first-response moment needs at least one change")
        if any((c.tick, c.phase) != (self.tick, self.phase) for c in self.changes):
            raise ValueError("all changes in a first-response moment must share its (tick, phase)")

    def canonical(self) -> dict[str, object]:
        return {"changes": [c.canonical() for c in sorted(self.changes, key=lambda c: (c.role, c.field))],
                "format": FORMAT, "phase": self.phase.value, "tick": self.tick}


@dataclass(frozen=True)
class DivergenceChain:
    """An observed, phase-ordered sequence of divergences -- not yet a causal claim."""
    trace_id_left: str
    trace_id_right: str
    interventions: tuple[InterventionRecord, ...]
    first_response: FirstResponseMoment | None
    events: tuple[DivergenceEvent, ...]

    def canonical(self) -> dict[str, object]:
        return {"events": [x.canonical() for x in self.events], "first_response":
                (self.first_response.canonical() if self.first_response is not None else None),
                "format": FORMAT, "interventions": [x.canonical() for x in sorted(self.interventions)],
                "trace_id_left": self.trace_id_left, "trace_id_right": self.trace_id_right}


def _snapshot_fields(snapshot: TraceSnapshot) -> tuple[tuple[str, str], ...]:
    return tuple(sorted((role, field) for role, values in snapshot.values.items() for field in values))


def _origin(role: str, field: str, tick: int, left_value: Any, right_value: Any,
           interventions_by_field: dict[tuple[str, str], InterventionRecord]) -> str:
    """Classify one differing (role, field) reading, given what was deliberately assigned to it (if anything).

    The key question is not "was this field ever intervened on" but "is the
    value observed right now still exactly what the intervention assigned":
    once A moves a `SET_ONCE`/`PULSE` field away from its assigned value, any
    further difference on it is the world's own doing, not the experiment's.
    """
    intervention = interventions_by_field.get((role, field))
    if intervention is None:
        return "ENDOGENOUS_RESPONSE"
    if tick == intervention.applied_at_tick:
        return "DIRECT_INTERVENTION"
    if intervention.mode == "CLAMP":
        return "INTERVENTION_MAINTAINED"
    # SET_ONCE / PULSE: still the assigned values on both sides -> the
    # difference is merely persisting, not something A has done yet.
    if left_value == intervention.left_value and right_value == intervention.right_value:
        return "INTERVENTION_PERSISTED"
    return "ENDOGENOUS_RESPONSE"


def compare_snapshot_sequences(
    trace_id_left: str, trace_id_right: str,
    left: tuple[TraceSnapshot, ...], right: tuple[TraceSnapshot, ...],
    interventions: tuple[InterventionRecord, ...] = (),
) -> DivergenceChain:
    """Compare two traces phase by phase, classifying each differing field's divergence origin.

    `left` and `right` must report exactly the same `(tick, phase)` pairs --
    both produced by `trace_model.run_traced` against comparable `TraceSpec`s.

    `(tick, phase)` is used here strictly as a *structural alignment key*:
    it identifies "baseline's AFTER_BOND_BREAK_PHASE at tick 1" and
    "contrast's AFTER_BOND_BREAK_PHASE at tick 1" as the same logical
    observation point across the two independent runs, so their values can
    be compared. It is never used to derive a cross-run time ordering --
    `observation_seq` is per-trace only (see `TraceSnapshot`'s docstring)
    and comparing `left.observation_seq` against `right.observation_seq`
    would be meaningless, since the two traces' counters advance
    independently. Within-trace ordering decisions (e.g. `causal_timeline.py`)
    must use `observation_seq`; this function's own within-chain event
    ordering (`_PHASE_ORDER`) is likewise a display/grouping convenience
    for one shared alignment key, not a claim about real elapsed time.
    """
    by_key_left = {(s.tick, s.phase): s for s in left}
    by_key_right = {(s.tick, s.phase): s for s in right}
    if set(by_key_left) != set(by_key_right):
        raise ValueError("compared snapshot sequences must cover the same (tick, phase) pairs")
    interventions_by_field = {(item.role, item.field): item for item in interventions}

    events: list[DivergenceEvent] = []
    for tick, phase in sorted(by_key_left, key=lambda key: (key[0], _PHASE_ORDER[key[1]])):
        snap_left, snap_right = by_key_left[(tick, phase)], by_key_right[(tick, phase)]
        fields = set(_snapshot_fields(snap_left)) | set(_snapshot_fields(snap_right))
        for role, field in sorted(fields):
            left_value = snap_left.values.get(role, {}).get(field)
            right_value = snap_right.values.get(role, {}).get(field)
            if left_value == right_value:
                continue
            origin = _origin(role, field, tick, left_value, right_value, interventions_by_field)
            events.append(DivergenceEvent(tick, phase, role, field, left_value, right_value,
                                          classify_field_divergence(field), origin))

    first_response = None
    responses = [e for e in events if e.origin in _RESPONSE_ORIGINS]
    if responses:
        earliest_key = min((e.tick, _PHASE_ORDER[e.phase]) for e in responses)
        moment_events = tuple(sorted((e for e in responses if (e.tick, _PHASE_ORDER[e.phase]) == earliest_key),
                                     key=lambda e: (e.role, e.field)))
        first_response = FirstResponseMoment(moment_events[0].tick, moment_events[0].phase, moment_events)
    return DivergenceChain(trace_id_left, trace_id_right, interventions, first_response, tuple(events))
