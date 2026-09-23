"""causal v5 reference executor (plan sections 4-6).

Deliberately slow and obvious -- that is why it exists (designer decision X2).
It never uses: a spatial index, a cache, parallelism, floats, heuristics,
labels to order anything, or "skip candidates for speed". Every pair of
elements in different structures is checked, every time.

    state <- the spec's first picture, time = 0
    loop:
      1. every pair in different structures -> its next contact event, if any
      2. earliest time t; beyond end_time -> move to end_time and finish
      3. move every structure to t (exact: position += velocity * dt)
      4. collect ALL contact events at t
      5. freeze the pre-event state; judge every event against it only
      6. any undefined event -> record and halt (a normal result, not an error)
         otherwise merge each connected component of bindable events at once
      7. repeat (a new event at the same t is a causal round, never a deferred one)

Contact (K3: axis-aligned squares, closed condition): per axis the times
with |d + s*dv| <= w form one closed interval; the first common time is the
contact. At that instant at least one touching axis (|d| == w) must be
closing; if none is, the pair only slides, rests or separates -- not an event.
One touching axis -> a face; both -> a corner (undefined, halt), including a
corner merely grazed for one instant. With
straight-line motion the touching set of a pair is one interval, so each
pair has at most one candidate event until some velocity changes.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Mapping

from .v5_number import Vec, add, dot, exact, scale, ser, ser_vec, sub
from .v5_spec import OPPOSITE, BondSpec, RunRequest, WorldSpecV5
from .v5_state import Element, StateV5, Structure, initial_state, validate

FORMAT = "causal-v5-run-v1"
HALT_KINDS = ("corner_contact", "non_binding_collision_unresolved", "contested_contact")


class InternalError(RuntimeError):
    """A bug or a broken invariant -- never a physical outcome."""


# ---------------------------------------------------------------------------
# Records (all relabel-able, all canonical).
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class StructureSnapshot:
    members: frozenset[str]
    momentum: Vec
    internal_energy: Fraction
    positions: tuple[tuple[str, Vec], ...]

    @classmethod
    def of(cls, state: StateV5, s: Structure) -> "StructureSnapshot":
        return cls(s.members, s.momentum, s.internal_energy,
                   tuple(sorted((m, state.element(m).position) for m in s.members)))

    def relabeled(self, mapping: Mapping[str, str]) -> "StructureSnapshot":
        return StructureSnapshot(frozenset(mapping[m] for m in self.members), self.momentum, self.internal_energy,
                                 tuple(sorted((mapping[m], p) for m, p in self.positions)))

    def canonical(self) -> dict[str, object]:
        return {"internal_energy": ser(self.internal_energy), "members": sorted(self.members),
                "momentum": ser_vec(self.momentum),
                "positions": [[m, ser_vec(p)] for m, p in sorted(self.positions)]}


@dataclass(frozen=True)
class MergeEvent:
    time: Fraction
    round: int
    bonds: frozenset[BondSpec]
    pre: frozenset[StructureSnapshot]
    post: StructureSnapshot
    kinetic_energy_absorbed: Fraction          # a claim for the audit to check, not an input to it
    angular_momentum_residual: Fraction        # E7: L_before - L_after, audit only

    def relabeled(self, mapping: Mapping[str, str]) -> "MergeEvent":
        return MergeEvent(self.time, self.round, frozenset(b.relabeled(mapping) for b in self.bonds),
                          frozenset(p.relabeled(mapping) for p in self.pre), self.post.relabeled(mapping),
                          self.kinetic_energy_absorbed, self.angular_momentum_residual)

    def canonical(self) -> dict[str, object]:
        return {"angular_momentum_residual": ser(self.angular_momentum_residual),
                "bonds": [b.canonical() for b in sorted(self.bonds)], "kind": "merge",
                "kinetic_energy_absorbed": ser(self.kinetic_energy_absorbed), "post": self.post.canonical(),
                "pre": sorted((p.canonical() for p in self.pre), key=lambda c: c["members"]),
                "round": self.round, "time": ser(self.time)}


@dataclass(frozen=True)
class Unresolved:
    """The world reached physics v5 does not define. Recorded, then the run halts."""
    time: Fraction
    round: int
    kind: str                                   # one of HALT_KINDS
    reason: str
    participants: frozenset[tuple[str, str]]    # (label, face) -- face "corner" for a corner contact

    def relabeled(self, mapping: Mapping[str, str]) -> "Unresolved":
        return Unresolved(self.time, self.round, self.kind, self.reason,
                          frozenset((mapping[label], face) for label, face in self.participants))

    def canonical(self) -> dict[str, object]:
        return {"kind": self.kind, "participants": sorted([list(p) for p in self.participants]),
                "reason": self.reason, "round": self.round, "time": ser(self.time)}


def _sorted_by_canonical(items) -> list[dict[str, object]]:
    return sorted((i.canonical() for i in items),
                  key=lambda c: (Fraction(c["time"][0], c["time"][1]), c["round"], json.dumps(c, sort_keys=True)))


@dataclass(frozen=True)
class RunResultV5:
    spec_digest: str
    request: RunRequest
    outcome: str                                  # "completed" | "halted"
    final_state: StateV5
    events: tuple[MergeEvent, ...]
    unresolved: tuple[Unresolved, ...]
    observations: tuple[StateV5, ...]
    meter_summary: dict | None = field(default=None, compare=False)   # never in canonical()

    def relabeled(self, mapping: Mapping[str, str]) -> "RunResultV5":
        return RunResultV5(self.spec_digest, self.request, self.outcome, self.final_state.relabeled(mapping),
                           tuple(e.relabeled(mapping) for e in self.events),
                           tuple(u.relabeled(mapping) for u in self.unresolved),
                           tuple(o.relabeled(mapping) for o in self.observations))

    def physics(self) -> dict[str, object]:
        """Everything the world did -- without the spec digest or how it was looked at."""
        return {"events": _sorted_by_canonical(self.events), "final_state": self.final_state.canonical(),
                "outcome": self.outcome, "unresolved": _sorted_by_canonical(self.unresolved)}

    def canonical(self) -> dict[str, object]:
        body = self.physics()
        body.update({"format": FORMAT, "observations": [o.canonical() for o in self.observations],
                     "request": self.request.canonical(), "spec_digest": self.spec_digest})
        return body


# ---------------------------------------------------------------------------
# Geometry of one pair.
# ---------------------------------------------------------------------------

def _axis_interval(d: Fraction, dv: Fraction, w: Fraction) -> tuple[Fraction, Fraction | None] | None:
    """Closed set of s >= 0 with |d + s*dv| <= w; hi None means unbounded."""
    if dv == 0:
        return (Fraction(0), None) if abs(d) <= w else None
    s1, s2 = (-w - d) / dv, (w - d) / dv
    lo, hi = min(s1, s2), max(s1, s2)
    if hi < 0:
        return None
    return (max(lo, Fraction(0)), hi)


@dataclass(frozen=True)
class Contact:
    after: Fraction                               # time from now
    corner: bool
    faces: frozenset[tuple[str, str]]             # (label, face); face "corner" for corners

    @property
    def pair(self) -> frozenset[str]:
        return frozenset(label for label, _ in self.faces)


def _contact(spec: WorldSpecV5, state: StateV5, velocity: Mapping[str, Vec], a: Element, b: Element) -> Contact | None:
    w = spec.material(a.kind).contact_half_width + spec.material(b.kind).contact_half_width
    d = sub(b.position, a.position)
    dv = sub(velocity[b.label], velocity[a.label])
    ix, iy = _axis_interval(d[0], dv[0], w), _axis_interval(d[1], dv[1], w)
    if ix is None or iy is None:
        return None
    s = max(ix[0], iy[0])
    ends = [h for h in (ix[1], iy[1]) if h is not None]
    if ends and s > min(ends):
        return None
    at = add(d, scale(dv, s))
    touching = [axis for axis in (0, 1) if abs(at[axis]) == w]
    if not touching:
        raise InternalError(f"{a.label} and {b.label} overlap without an event")
    if not any(at[axis] * dv[axis] < 0 for axis in touching):
        return None                               # resting, sliding or separating on every touching axis (P4)
    # `any`, not `all`: a body sweeping past a corner -- one axis closing, the other
    # opening -- touches for exactly one instant. That is a real corner contact
    # (K6: record + halt), not "no contact". Found by review, 2026-09-24.
    if len(touching) == 2:
        return Contact(s, True, frozenset({(a.label, "corner"), (b.label, "corner")}))
    axis = touching[0]
    if axis == 0:
        face_a = "E" if at[0] > 0 else "W"
    else:
        face_a = "S" if at[1] > 0 else "N"
    return Contact(s, False, frozenset({(a.label, face_a), (b.label, OPPOSITE[face_a])}))


def _velocities(spec: WorldSpecV5, state: StateV5) -> dict[str, Vec]:
    by_structure = {s.key: state.velocity(spec, s) for s in state.structures}
    return {m: by_structure[s.key] for s in state.structures for m in s.members}


def _advance(spec: WorldSpecV5, state: StateV5, dt: Fraction) -> StateV5:
    if dt == 0:
        return state
    velocity = _velocities(spec, state)
    moved = tuple(Element(e.label, e.kind, add(e.position, scale(velocity[e.label], dt))) for e in state.elements)
    return StateV5(exact(state.time + dt), moved, state.structures)


def _all_contacts(spec: WorldSpecV5, state: StateV5) -> list[Contact]:
    velocity = _velocities(spec, state)
    owner = {m: s.key for s in state.structures for m in s.members}
    elements = state.elements
    found = []
    for i, a in enumerate(elements):                  # every pair, every time -- no index, no pruning
        for b in elements[i + 1:]:
            if owner[a.label] == owner[b.label]:
                continue
            contact = _contact(spec, state, velocity, a, b)
            if contact is not None:
                found.append(contact)
    return found


# ---------------------------------------------------------------------------
# Judging and merging at one instant.
# ---------------------------------------------------------------------------

def _judge(spec: WorldSpecV5, frozen: StateV5, batch: list[Contact], t: Fraction, round_no: int):
    """Every event against the frozen pre-event state only (plan section 5)."""
    used_ports = {end for s in frozen.structures for b in s.bonds for end in b.ends()}
    bindable, unresolved = [], []
    for contact in batch:
        if contact.corner:
            unresolved.append(Unresolved(t, round_no, "corner_contact", "face undefined at a corner",
                                         contact.faces))
            continue
        (la, fa), (lb, fb) = sorted(contact.faces)
        ea, eb = frozen.element(la), frozen.element(lb)
        reason = None
        if fa not in spec.material(ea.kind).ports or fb not in spec.material(eb.kind).ports:
            reason = "no_port"
        elif (la, fa) in used_ports or (lb, fb) in used_ports:
            reason = "port_occupied"
        else:
            rule = spec.rule_for((ea.kind, fa), (eb.kind, fb))
            if rule is None:
                reason = "no_rule"
            else:
                sa, sb = frozen.structure_of(la), frozen.structure_of(lb)
                ma, mb = frozen.mass(spec, sa), frozen.mass(spec, sb)
                dv = sub(frozen.velocity(spec, sb), frozen.velocity(spec, sa))
                relative_ke = exact(ma * mb / (ma + mb) * dot(dv, dv) / 2)
                if relative_ke < rule.threshold:
                    reason = "below_threshold"
        if reason is None:
            bindable.append(contact)
        else:
            unresolved.append(Unresolved(t, round_no, "non_binding_collision_unresolved", reason, contact.faces))
    port_count: dict[tuple[str, str], int] = {}
    for contact in bindable:
        for end in contact.faces:
            port_count[end] = port_count.get(end, 0) + 1
    contested = [c for c in bindable if any(port_count[end] > 1 for end in c.faces)]
    for contact in contested:
        unresolved.append(Unresolved(t, round_no, "contested_contact", "one port claimed by several contacts",
                                     contact.faces))
    return [c for c in bindable if c not in contested], unresolved


def _merge(spec: WorldSpecV5, frozen: StateV5, bindable: list[Contact], t: Fraction, round_no: int):
    """Each connected component of bindable contacts merges at once (6.2) --
    never pairwise in sequence."""
    owner = {m: s for s in frozen.structures for m in s.members}
    parent = {s.key: s.key for s in frozen.structures}

    def find(k):
        while parent[k] != k:
            parent[k] = parent[parent[k]]
            k = parent[k]
        return k
    for contact in bindable:
        a, b = sorted(contact.pair)
        parent[find(owner[a].key)] = find(owner[b].key)
    groups: dict[tuple, list[Structure]] = {}
    for s in frozen.structures:
        groups.setdefault(find(s.key), []).append(s)
    new_bonds: dict[tuple, set[BondSpec]] = {}
    for contact in bindable:
        (la, fa), (lb, fb) = sorted(contact.faces)
        new_bonds.setdefault(find(owner[la].key), set()).add(BondSpec(la, fa, lb, fb))

    structures, events = [], []
    for root, parts in groups.items():
        if len(parts) == 1:
            structures.append(parts[0])
            continue
        momentum = (Fraction(0), Fraction(0))
        internal = kinetic = Fraction(0)
        for s in parts:
            momentum = add(momentum, s.momentum)
            internal += s.internal_energy
            kinetic += frozen.kinetic_energy(spec, s)
        merged_members = frozenset().union(*(s.members for s in parts))
        merged_bonds = frozenset().union(*(s.bonds for s in parts)) | frozenset(new_bonds[root])
        mass = sum((frozen.mass(spec, s) for s in parts), Fraction(0))
        kinetic_after = exact((momentum[0] ** 2 + momentum[1] ** 2) / (2 * mass))
        absorbed = exact(kinetic - kinetic_after)
        merged = Structure(merged_members, merged_bonds, momentum, exact(internal + absorbed))   # U' = ΣU + ΣK − K'
        structures.append(merged)
        residual = exact(frozen.angular_momentum(spec, parts) - frozen.angular_momentum(spec, [merged]))
        events.append(MergeEvent(t, round_no, frozenset(new_bonds[root]),
                                 frozenset(StructureSnapshot.of(frozen, s) for s in parts),
                                 StructureSnapshot.of(frozen, merged), absorbed, residual))
    return StateV5(frozen.time, frozen.elements, tuple(structures)), events


# ---------------------------------------------------------------------------
# The run.
# ---------------------------------------------------------------------------

def run_v5(spec: WorldSpecV5, request: RunRequest, meter=None) -> RunResultV5:
    state = initial_state(spec)
    events: list[MergeEvent] = []
    observations: list[StateV5] = []
    next_observation = Fraction(0)
    last_time: Fraction | None = None
    round_no = 0
    seen_this_instant: set[frozenset[str]] = set()

    def observe_before(limit: Fraction, inclusive: bool) -> None:
        nonlocal next_observation
        while next_observation < limit or (inclusive and next_observation == limit):
            observations.append(_advance(spec, state, next_observation - state.time))
            next_observation += request.observation_interval

    while True:
        contacts = _all_contacts(spec, state)
        if not contacts or state.time + min(c.after for c in contacts) > request.end_time:
            observe_before(request.end_time, inclusive=True)
            state = _advance(spec, state, request.end_time - state.time)
            result = RunResultV5(spec.digest, request, "completed", state, tuple(events), (), tuple(observations))
            break
        step = min(c.after for c in contacts)
        t = exact(state.time + step)
        observe_before(t, inclusive=False)
        state = _advance(spec, state, step)
        if t == last_time:
            round_no += 1                         # a causal round: caused by the previous round at this instant
        else:
            round_no, seen_this_instant = 0, set()
        batch = [c for c in contacts if c.after == step]
        pairs = {c.pair for c in batch}
        if pairs & seen_this_instant:
            raise InternalError("an event already present in an earlier round reappeared (K4: never defer)")
        bindable, unresolved = _judge(spec, state, batch, t, round_no)
        if unresolved:
            result = RunResultV5(spec.digest, request, "halted", state, tuple(events), tuple(unresolved),
                                 tuple(observations))
            break
        state, new_events = _merge(spec, state, bindable, t, round_no)
        validate(spec, state)
        events.extend(new_events)
        if meter is not None:
            meter.record(spec, state, new_events)
        seen_this_instant |= pairs
        last_time = t
    if meter is not None:
        result = RunResultV5(result.spec_digest, result.request, result.outcome, result.final_state, result.events,
                             result.unresolved, result.observations, meter.summary())
    return result
