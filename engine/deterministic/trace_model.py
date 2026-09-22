"""Role-bound observation targets and per-tick snapshots for Deep Investigator traces.

Shares `role_resolver.py` with `exploration_control.py` so a role means the
same subject whether it is being mutated (Control) or observed (Trace) --
see that module's docstring. `TraceBinding` is nonetheless its own type, not
`ControlBinding` reused: "this is what I changed" and "this is what I'm
watching" are different research statements even when they resolve to the
same particle id.

A role resolves against the *base* spec once; the resulting particle_id (or
heat-cell coordinate, or bond pair) is then looked up in every tick's
`CausalWorldState` directly. This is what lets a trace follow "the particle
that started at (9, 10) moving east" across ticks where its position and
even its bonded/free status change, without re-running role matching (which
would fail once two once-distinguishable particles land on the same cell).

Only fields the causal kernel already exposes are traceable -- no derived
physics ("stress", "break_condition") is invented here. If a quantity is not
a field on `CausalParticleSpec`, `PhysicalBond`/`PortBond`, or `HeatCellSpec`,
it cannot be a trace field.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping, Union

from .causal_kernel import CausalWorldState, KernelPhase, initial_causal_state, step_causal_world
from .causal_spec import CausalWorldSpec
from .role_resolver import resolve_heat_cell_role, resolve_particle_role

FORMAT = "trace-model-v1"

PARTICLE_TRACE_FIELDS = frozenset({"x", "y", "direction", "orientation", "kinetic_energy"})
HEAT_TRACE_FIELDS = frozenset({"energy"})
BOND_TRACE_FIELDS = frozenset({"exists", "stored_energy"})


def _digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _text(value: str, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{context} must be non-empty text")
    return value


@dataclass(frozen=True, order=True)
class ParticleTraceSubject:
    role: str
    match_x: int
    match_y: int
    match_direction: str
    fields: tuple[str, ...]

    def __post_init__(self) -> None:
        _text(self.role, "role")
        if not self.fields or any(f not in PARTICLE_TRACE_FIELDS for f in self.fields):
            raise ValueError(f"unsupported particle trace fields {self.fields!r}")
        if len(set(self.fields)) != len(self.fields):
            raise ValueError("trace fields must not repeat")

    def canonical(self) -> dict[str, object]:
        return {"fields": list(self.fields), "kind": "particle", "match_direction": self.match_direction,
                "match_x": self.match_x, "match_y": self.match_y, "role": self.role}


@dataclass(frozen=True, order=True)
class HeatCellTraceSubject:
    role: str
    x: int
    y: int
    fields: tuple[str, ...]

    def __post_init__(self) -> None:
        _text(self.role, "role")
        if not self.fields or any(f not in HEAT_TRACE_FIELDS for f in self.fields):
            raise ValueError(f"unsupported heat trace fields {self.fields!r}")

    def canonical(self) -> dict[str, object]:
        return {"fields": list(self.fields), "kind": "heat_cell", "role": self.role, "x": self.x, "y": self.y}


@dataclass(frozen=True, order=True)
class BondTraceSubject:
    """Traces whether two particles (named by role, like `ParticleTraceSubject`) are bonded.

    `exists` reports the v1/v2 `PhysicalBond` relation between the two
    resolved particle ids; `stored_energy` reports that bond's stored energy
    when it exists (`None` while unbonded).
    """
    role: str
    particle_role_a: str
    particle_role_b: str
    fields: tuple[str, ...]

    def __post_init__(self) -> None:
        _text(self.role, "role")
        _text(self.particle_role_a, "particle_role_a")
        _text(self.particle_role_b, "particle_role_b")
        if not self.fields or any(f not in BOND_TRACE_FIELDS for f in self.fields):
            raise ValueError(f"unsupported bond trace fields {self.fields!r}")

    def canonical(self) -> dict[str, object]:
        return {"fields": list(self.fields), "kind": "bond", "particle_role_a": self.particle_role_a,
                "particle_role_b": self.particle_role_b, "role": self.role}


TraceSubject = Union[ParticleTraceSubject, HeatCellTraceSubject, BondTraceSubject]


@dataclass(frozen=True)
class TraceSpec:
    """What to watch, and for how long, in a Deep Investigator trace.

    `context` names bond-rule-level values (e.g. `break_heat`) that are part
    of the spec, not the per-tick state, and so are recorded once rather than
    repeated in every snapshot.
    """
    trace_id: str
    subjects: tuple[TraceSubject, ...]
    start_tick: int
    end_tick: int
    context_fields: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _text(self.trace_id, "trace_id")
        roles = [s.role for s in self.subjects]
        if not roles or len(set(roles)) != len(roles):
            raise ValueError("trace subjects must have unique, non-empty roles")
        if isinstance(self.start_tick, bool) or not isinstance(self.start_tick, int) or self.start_tick < 0:
            raise ValueError("start_tick must be a nonnegative integer")
        if isinstance(self.end_tick, bool) or not isinstance(self.end_tick, int) or self.end_tick < self.start_tick:
            raise ValueError("end_tick must be an integer at least start_tick")

    def canonical(self) -> dict[str, object]:
        return {"context_fields": list(self.context_fields), "end_tick": self.end_tick, "format": FORMAT,
                "start_tick": self.start_tick, "subjects": [x.canonical() for x in sorted(self.subjects)],
                "trace_id": self.trace_id}


@dataclass(frozen=True)
class TraceBinding:
    """A trace subject's role resolved against one base spec, kept distinct from `ControlBinding`.

    "What I mutated" and "what I'm watching" are different research
    statements even when, as often happens, they resolve to the same
    particle id.
    """
    role: str
    resolved_identity: str

    def canonical(self) -> dict[str, object]:
        return {"resolved_identity": self.resolved_identity, "role": self.role}


def bind_trace_subject(subject: TraceSubject, spec: CausalWorldSpec) -> TraceBinding:
    if isinstance(subject, ParticleTraceSubject):
        particle_id = resolve_particle_role(spec, subject.role, subject.match_x, subject.match_y, subject.match_direction)
        return TraceBinding(subject.role, str(particle_id))
    if isinstance(subject, HeatCellTraceSubject):
        x, y = resolve_heat_cell_role(spec, subject.role, subject.x, subject.y)
        return TraceBinding(subject.role, f"{x},{y}")
    if isinstance(subject, BondTraceSubject):
        return TraceBinding(subject.role, f"{subject.particle_role_a}~{subject.particle_role_b}")
    raise TypeError(f"unsupported trace subject type {type(subject).__name__}")


@dataclass(frozen=True)
class TraceSnapshot:
    """One kernel phase's observed values for every subject in a `TraceSpec`.

    `values` is `{role: {field: value}}`. A missing subject at a given tick
    (a heat cell with zero energy has no `HeatCellSpec` entry, an unbonded
    pair has no bond) reports `None` for every requested field rather than
    omitting the subject -- so "no bond" is a recorded fact, not a gap.

    `phase` names which `KernelPhase` this snapshot was taken at (see
    `causal_kernel.py`'s `KernelObserver`). Two snapshots can share a tick --
    `AFTER_BOND_BREAK_PHASE` and `POST_TICK` both belong to tick 1 -- which is
    exactly what lets a divergence be placed *within* a tick rather than only
    between ticks.
    """
    tick: int
    phase: KernelPhase
    values: Mapping[str, Mapping[str, Any]]

    def canonical(self) -> dict[str, object]:
        return {"phase": self.phase.value, "tick": self.tick,
                "values": {role: dict(sorted(fields.items())) for role, fields in sorted(self.values.items())}}


def _particle_by_id(state: CausalWorldState) -> dict[int, object]:
    return {p.particle_id: p for p in state.particles}


def _read_particle(state: CausalWorldState, particle_id: int, fields: tuple[str, ...]) -> dict[str, Any]:
    particle = _particle_by_id(state).get(particle_id)
    if particle is None:
        return {field: None for field in fields}
    return {field: getattr(particle, field) for field in fields}


def _read_heat(state: CausalWorldState, x: int, y: int, fields: tuple[str, ...]) -> dict[str, Any]:
    cell = next((c for c in state.heat if c.x == x and c.y == y), None)
    if "energy" in fields:
        return {"energy": cell.energy if cell is not None else 0}
    return {}


def _read_bond(state: CausalWorldState, particle_id_a: int, particle_id_b: int, fields: tuple[str, ...]) -> dict[str, Any]:
    pair = {particle_id_a, particle_id_b}
    bond = next((b for b in state.bonds if {b.left_id, b.right_id} == pair), None)
    result: dict[str, Any] = {}
    if "exists" in fields:
        result["exists"] = bond is not None
    if "stored_energy" in fields:
        result["stored_energy"] = bond.stored_energy if bond is not None else None
    return result


def collect_snapshot(spec: CausalWorldSpec, state: CausalWorldState, trace_spec: TraceSpec,
                     bindings: Mapping[str, TraceBinding], phase: KernelPhase) -> TraceSnapshot:
    """Read `trace_spec`'s subjects off one `CausalWorldState`, using pre-resolved `bindings`."""
    values: dict[str, dict[str, Any]] = {}
    for subject in trace_spec.subjects:
        if isinstance(subject, ParticleTraceSubject):
            particle_id = int(bindings[subject.role].resolved_identity)
            values[subject.role] = _read_particle(state, particle_id, subject.fields)
        elif isinstance(subject, HeatCellTraceSubject):
            x, y = subject.x, subject.y
            values[subject.role] = _read_heat(state, x, y, subject.fields)
    for subject in trace_spec.subjects:
        if isinstance(subject, BondTraceSubject):
            particle_id_a = int(bindings[subject.particle_role_a].resolved_identity)
            particle_id_b = int(bindings[subject.particle_role_b].resolved_identity)
            values[subject.role] = _read_bond(state, particle_id_a, particle_id_b, subject.fields)
    return TraceSnapshot(state.tick, phase, values)


def bind_trace_spec(trace_spec: TraceSpec, spec: CausalWorldSpec) -> dict[str, TraceBinding]:
    """Resolve every subject's role once against `spec`. Particle roles resolve against the base spec only."""
    bindings: dict[str, TraceBinding] = {}
    for subject in trace_spec.subjects:
        if isinstance(subject, (ParticleTraceSubject, HeatCellTraceSubject)):
            bindings[subject.role] = bind_trace_subject(subject, spec)
    for subject in trace_spec.subjects:
        if isinstance(subject, BondTraceSubject):
            bindings[subject.role] = bind_trace_subject(subject, spec)
    return bindings


class _TraceCollectingObserver:
    """A read-only `KernelObserver` that snapshots `trace_spec` at every phase in range.

    Never mutates `state` -- only reads it into a `TraceSnapshot`. Passed to
    `step_causal_world` exactly as any other observer would be; `run_traced`
    is not special kernel access, it is an ordinary consumer of the public
    observer hook.
    """
    def __init__(self, spec: CausalWorldSpec, trace_spec: TraceSpec, bindings: Mapping[str, TraceBinding]) -> None:
        self._spec = spec
        self._trace_spec = trace_spec
        self._bindings = bindings
        self.snapshots: list[TraceSnapshot] = []

    def on_phase(self, *, tick: int, phase: KernelPhase, state: CausalWorldState) -> None:
        if self._trace_spec.start_tick <= tick <= self._trace_spec.end_tick:
            self.snapshots.append(collect_snapshot(self._spec, state, self._trace_spec, self._bindings, phase))


def run_traced(spec: CausalWorldSpec, trace_spec: TraceSpec) -> tuple[TraceSnapshot, ...]:
    """Run `spec` through the real causal kernel via its public `KernelObserver` hook.

    Collects one `TraceSnapshot` per phase per tick in `[start_tick, end_tick]`
    -- `PRE_TICK`, `AFTER_BOND_BREAK_PHASE`, and `POST_TICK` for each tick --
    never by calling any private kernel function directly. Uses
    `step_causal_world` rather than `run_causal_world`, because
    `CausalRun.checkpoints` only carries digests and summary counts at
    `hash_interval` boundaries; a trace needs every tick's actual field
    values, not their hash.
    """
    bindings = bind_trace_spec(trace_spec, spec)
    observer = _TraceCollectingObserver(spec, trace_spec, bindings)
    state = initial_causal_state(spec)
    # `step_causal_world` is what actually calls the observer (`PRE_TICK` at
    # its start, so even tick 0 needs one call to be observed at all) -- run
    # at least one step so `end_tick == 0` still yields tick 0's phases,
    # without ever stepping past `end_tick`.
    while state.tick <= trace_spec.end_tick:
        state = step_causal_world(spec, state, observer)
    return tuple(observer.snapshots)
