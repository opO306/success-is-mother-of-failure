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
         otherwise merge each connected component of bindable events at once, and
         resolve each face contact that no process claims as a C1 collision
      7. repeat (a new event at the same t is a causal round, never a deferred one)

Contact (K3: axis-aligned squares, closed condition): per axis the times
with |d + s*dv| <= w form one closed interval; the first common time is the
contact. At that instant at least one touching axis (|d| == w) must be
closing; if none is, the pair only slides, rests or separates -- not an event.
One touching axis -> a face; both -> a corner (undefined, halt), including a
corner merely grazed for one instant. With
straight-line motion the touching set of a pair is one interval, so each
pair has at most one candidate event until some velocity changes.

C1 collisions (docs/current/A_MICRO_V5_COLLISION_ROTATION_PLAN_V1.md, approved):
contact first, then whatever process the world's laws allow (today: a bond);
only when no process claims a face contact is it a collision. C1 resolves just
the case it can resolve with no invented physics: frictionless (tangential
momentum untouched), perfectly elastic (e = 1, nothing to share out), rigid,
torque-free -- the impulse line runs through both centres of mass and lies
within the contact. Off-centre contacts (R3), mixed normals, and any body in
two events at one instant (R6, Newton's cradle) halt with a record instead.
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
class CollisionEvent:
    """A C1 collision: two structures stay separate and exchange momentum along the
    contact normal only. Recorded with full pre/post state for the audit."""
    time: Fraction
    round: int
    axis: str                                   # "x" or "y" -- the contact normal
    faces: frozenset[tuple[str, str]]           # every (label, face) in the contact
    pre: frozenset[StructureSnapshot]
    post: frozenset[StructureSnapshot]

    def relabeled(self, mapping: Mapping[str, str]) -> "CollisionEvent":
        return CollisionEvent(self.time, self.round, self.axis,
                              frozenset((mapping[label], face) for label, face in self.faces),
                              frozenset(p.relabeled(mapping) for p in self.pre),
                              frozenset(p.relabeled(mapping) for p in self.post))

    def canonical(self) -> dict[str, object]:
        return {"axis": self.axis, "faces": sorted([list(f) for f in self.faces]), "kind": "collision",
                "post": sorted((p.canonical() for p in self.post), key=lambda c: c["members"]),
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
    collisions: tuple[CollisionEvent, ...] = ()
    meter_summary: dict | None = field(default=None, compare=False)   # never in canonical()

    def relabeled(self, mapping: Mapping[str, str]) -> "RunResultV5":
        return RunResultV5(self.spec_digest, self.request, self.outcome, self.final_state.relabeled(mapping),
                           tuple(e.relabeled(mapping) for e in self.events),
                           tuple(u.relabeled(mapping) for u in self.unresolved),
                           tuple(o.relabeled(mapping) for o in self.observations),
                           tuple(c.relabeled(mapping) for c in self.collisions))

    def physics(self) -> dict[str, object]:
        """Everything the world did -- without the spec digest or how it was looked at."""
        return {"collisions": _sorted_by_canonical(self.collisions),
                "events": _sorted_by_canonical(self.events), "final_state": self.final_state.canonical(),
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
    bindable, nonbinding, unresolved = [], [], []
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
            nonbinding.append((contact, reason))            # no process claims it: a collision candidate (C1)
    port_count: dict[tuple[str, str], int] = {}
    for contact in bindable:
        for end in contact.faces:
            port_count[end] = port_count.get(end, 0) + 1
    contested = [c for c in bindable if any(port_count[end] > 1 for end in c.faces)]
    for contact in contested:
        unresolved.append(Unresolved(t, round_no, "contested_contact", "one port claimed by several contacts",
                                     contact.faces))
    return [c for c in bindable if c not in contested], nonbinding, unresolved


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


AXIS = {"E": 0, "W": 0, "N": 1, "S": 1}


def _merge_components(frozen: StateV5, bindable: list[Contact]) -> dict[tuple, tuple]:
    """structure key -> key of the merge component it joins this instant (itself if none)."""
    owner = {m: s.key for s in frozen.structures for m in s.members}
    parent = {s.key: s.key for s in frozen.structures}

    def find(k):
        while parent[k] != k:
            parent[k] = parent[parent[k]]
            k = parent[k]
        return k
    for contact in bindable:
        a, b = sorted(contact.pair)
        parent[find(owner[a])] = find(owner[b])
    return {s.key: find(s.key) for s in frozen.structures}


def _plan_collisions(spec: WorldSpecV5, frozen: StateV5, bindable: list[Contact], nonbinding, t: Fraction,
                     round_no: int, collided_labels: set[str], touched_labels: set[str]):
    """Which non-binding face contacts C1 can resolve, judged on the frozen state."""
    owner = {m: s for s in frozen.structures for m in s.members}
    component = _merge_components(frozen, bindable)
    groups: dict[frozenset, list[Contact]] = {}
    for contact, _reason in nonbinding:
        a, b = sorted(contact.pair)
        sa, sb = owner[a], owner[b]
        if component[sa.key] == component[sb.key]:
            continue                        # the two become one rigid body this instant: an internal touch
        groups.setdefault(frozenset({sa.key, sb.key}), []).append(contact)

    unresolved, plans = [], []
    merge_parts: dict[tuple, list[tuple]] = {}
    for key, root in component.items():
        merge_parts.setdefault(root, []).append(key)
    in_events: dict[tuple, int] = {}
    for parts in merge_parts.values():
        if len(parts) > 1:
            for key in parts:
                in_events[key] = in_events.get(key, 0) + 1
    for pair in groups:
        for key in pair:
            in_events[key] = in_events.get(key, 0) + 1

    def halt(reason: str, contacts) -> None:
        faces = frozenset(f for c in contacts for f in c.faces)
        unresolved.append(Unresolved(t, round_no, "non_binding_collision_unresolved", reason, faces))

    for root, parts in merge_parts.items():
        if len(parts) > 1 and any(set(key) & collided_labels for key in parts):
            halt("shared_body", [c for c in bindable if component[owner[sorted(c.pair)[0]].key] == root])
    for pair, contacts in groups.items():
        sa, sb = (owner[key[0]] for key in sorted(pair))
        axes = {AXIS[face] for c in contacts for _, face in c.faces}
        if len(axes) != 1:
            halt("mixed_normals", contacts)
            continue
        if any(in_events[key] > 1 for key in pair) or any(set(key) & touched_labels for key in pair):
            halt("shared_body", contacts)           # R6: one body in two events at one instant (Newton's cradle)
            continue
        axis = axes.pop()
        across = 1 - axis
        ca, cb = frozen.center_of_mass(spec, sa), frozen.center_of_mass(spec, sb)
        if ca[across] != cb[across]:
            halt("off_center_torque", contacts)     # R3: the impulse line misses a centre of mass
            continue
        low = high = None
        for contact in contacts:
            e1, e2 = (frozen.element(label) for label in sorted(contact.pair))
            h1, h2 = (spec.material(e.kind).contact_half_width for e in (e1, e2))
            lo = max(e1.position[across] - h1, e2.position[across] - h2)
            hi = min(e1.position[across] + h1, e2.position[across] + h2)
            low = lo if low is None else min(low, lo)
            high = hi if high is None else max(high, hi)
        if not low <= ca[across] <= high:
            halt("off_center_torque", contacts)     # the line through both centres misses the contact
            continue
        plans.append((sa, sb, axis, contacts))
    return plans, unresolved


def _collide(spec: WorldSpecV5, state: StateV5, plans, t: Fraction, round_no: int):
    """C1: frictionless, e = 1, torque-free. Only the normal component changes."""
    replaced: dict[tuple, Structure] = {}
    events = []
    for sa, sb, axis, contacts in plans:
        ma, mb = state.mass(spec, sa), state.mass(spec, sb)
        va, vb = state.velocity(spec, sa), state.velocity(spec, sb)
        impulse = exact(2 * ma * mb / (ma + mb) * (va[axis] - vb[axis]))
        pa, pb = list(sa.momentum), list(sb.momentum)
        pa[axis] -= impulse
        pb[axis] += impulse
        na = Structure(sa.members, sa.bonds, (exact(pa[0]), exact(pa[1])), sa.internal_energy)
        nb = Structure(sb.members, sb.bonds, (exact(pb[0]), exact(pb[1])), sb.internal_energy)
        replaced[sa.key], replaced[sb.key] = na, nb
        events.append(CollisionEvent(t, round_no, "xy"[axis], frozenset(f for c in contacts for f in c.faces),
                                     frozenset({StructureSnapshot.of(state, sa), StructureSnapshot.of(state, sb)}),
                                     frozenset({StructureSnapshot.of(state, na), StructureSnapshot.of(state, nb)})))
    structures = tuple(replaced.get(s.key, s) for s in state.structures)
    return StateV5(state.time, state.elements, structures), events


# ---------------------------------------------------------------------------
# The run.
# ---------------------------------------------------------------------------

def run_v5(spec: WorldSpecV5, request: RunRequest, meter=None) -> RunResultV5:
    state = initial_state(spec)
    events: list[MergeEvent] = []
    collisions: list[CollisionEvent] = []
    collided_labels: set[str] = set()                # bodies that bounced earlier at this instant
    touched_labels: set[str] = set()                 # bodies in any event earlier at this instant
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
            result = RunResultV5(spec.digest, request, "completed", state, tuple(events), (), tuple(observations),
                                 tuple(collisions))
            break
        step = min(c.after for c in contacts)
        t = exact(state.time + step)
        observe_before(t, inclusive=False)
        state = _advance(spec, state, step)
        if t == last_time:
            round_no += 1                         # a causal round: caused by the previous round at this instant
        else:
            round_no, seen_this_instant = 0, set()
            collided_labels, touched_labels = set(), set()
        batch = [c for c in contacts if c.after == step]
        pairs = {c.pair for c in batch}
        if pairs & seen_this_instant:
            raise InternalError("an event already present in an earlier round reappeared (K4: never defer)")
        bindable, nonbinding, unresolved = _judge(spec, state, batch, t, round_no)
        plans, blocked = _plan_collisions(spec, state, bindable, nonbinding, t, round_no, collided_labels,
                                          touched_labels)
        unresolved += blocked
        if unresolved:
            result = RunResultV5(spec.digest, request, "halted", state, tuple(events), tuple(unresolved),
                                 tuple(observations), tuple(collisions))
            break
        state, new_events = _merge(spec, state, bindable, t, round_no)
        state, new_collisions = _collide(spec, state, plans, t, round_no)
        validate(spec, state)
        events.extend(new_events)
        collisions.extend(new_collisions)
        for event in new_events:
            touched_labels |= event.post.members
        for event in new_collisions:
            labels = {m for snap in event.post for m in snap.members}
            touched_labels |= labels
            collided_labels |= labels
        if meter is not None:
            meter.record(spec, state, new_events)
        seen_this_instant |= pairs
        last_time = t
    if meter is not None:
        result = RunResultV5(result.spec_digest, result.request, result.outcome, result.final_state, result.events,
                             result.unresolved, result.observations, result.collisions, meter.summary())
    return result
