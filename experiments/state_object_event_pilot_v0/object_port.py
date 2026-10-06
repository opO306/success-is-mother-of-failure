"""PART A6/A7: PhysicalObject / InteractionPort / InteractionEvent over the canonical C1-B1 physics.

No new physics: the port composes the canonical primitives of a_reference.c1b1_two_atom (impulse, _drift,
segment_min_R2, relative, the profiles' rounding) in the order of c1b1_two_atom.step. One InteractionEvent per force
evaluation carries J once; impulse_i = -J and impulse_j = +J. Applying an event checks impulse_i == -impulse_j and
that the raw total momentum is unchanged (Newton's third law on the stored grid). The event is dropped after the
step; only J is kept as the J cache of the next first half kick (recomputable from the current positions).
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction as Q

from a_reference import c1b1_two_atom as C


class EventInvariantViolation(AssertionError):
    """An InteractionEvent broke impulse_i == -impulse_j or raw momentum conservation."""


@dataclass(frozen=True)
class PhysicalObject:
    """Current state of one atom. CHANNELS names the state variables a law may read or write."""
    species: str
    r: tuple
    p: tuple
    CHANNELS = ("position", "momentum")


@dataclass(frozen=True)
class InteractionEvent:
    impulse_i: tuple
    impulse_j: tuple
    obligations: tuple          # ((name, proven), ...) checked by the law before the event exists


class PairLawPort:
    """InteractionPort of the frozen C1-B1 pair law (Lang 2024, retardation ON). Pair-only because C1-B1 is a pair
    law; the port interface does not assume that every law is pairwise."""

    def __init__(self, pos, mom, dt):
        self.pos, self.mom, self.half = pos, mom, dt / 2
        self.checks = 0

    def interact(self, a, b) -> InteractionEvent:
        rel = C.relative(self.pos, a, b)
        J = C.impulse(rel, self.half, self.mom)          # raises PhysicsDomainExceeded below r_min (canonical)
        return InteractionEvent(tuple(-x for x in J), tuple(J), (("R2_ge_rmin2", True),))

    def apply(self, ev: InteractionEvent, a, b):
        if ev.impulse_i != tuple(-x for x in ev.impulse_j):
            raise EventInvariantViolation("impulse_i != -impulse_j")
        mom = self.mom
        pi = tuple(C._limit(mom.from_exact, p + q) for p, q in zip(C.exact(mom, a.p), C.exact(mom, ev.impulse_i)))
        pj = tuple(C._limit(mom.from_exact, p + q) for p, q in zip(C.exact(mom, b.p), C.exact(mom, ev.impulse_j)))
        if any(x + y != u + v for x, y, u, v in zip(pi, pj, a.p, b.p)):
            raise EventInvariantViolation("raw total momentum changed by the event")
        self.checks += 1
        return PhysicalObject(a.species, a.r, pi), PhysicalObject(b.species, b.r, pj)

    def drift(self, a, dt):
        moved, end = C._drift(self.pos, self.mom, a, dt, rule="v2")
        return PhysicalObject(a.species, moved.r, moved.p), end

    def drift_obligations(self, a_old, end_i, end_j, ai, aj, step_no):
        d_exact = tuple(y - x - o for x, y, o in zip(end_i, end_j, a_old))
        if C.segment_min_R2(a_old, d_exact) < C.R_MIN2:
            raise C.PhysicsDomainExceeded(f"drift segment enters R < r_min at step {step_no}")
        rel = C.relative(self.pos, ai, aj)
        if sum((x * x for x in rel), Q(0)) < C.R_MIN2:
            raise C.PhysicsDomainExceeded(f"stored positions at R < r_min at step {step_no}")


class PortRun:
    """World state of the PORT model: two PhysicalObjects, the J cache, the step count."""

    def __init__(self, pos, mom, dt, objects, J_cache, t_steps):
        self.pos, self.mom, self.dt = pos, mom, dt
        self.atoms = objects
        self.J_cache = J_cache
        self.t_steps = t_steps
        self.law = PairLawPort(pos, mom, dt)
        self.events = 0

    @classmethod
    def from_run(cls, run):
        objs = tuple(PhysicalObject(a.species, tuple(a.r), tuple(a.p)) for a in run.atoms)
        return cls(run.pos, run.mom, run.dt, objs, run.J_cache, run.t_steps)

    def state_core(self):
        return (self.atoms, self.J_cache, self.t_steps)

    def report(self):
        return {"events": self.events, "event_invariant_checks": self.law.checks}


def step(w: PortRun) -> None:
    pos, mom, law = w.pos, w.mom, w.law
    values = [(pos, a.r) for a in w.atoms] + [(mom, a.p) for a in w.atoms]
    if w.J_cache is not None:
        values.append((mom, w.J_cache))
    for profile, raws in values:
        valid = getattr(profile, "valid_raw", None)
        if valid is not None and not all(valid(v) for v in raws):
            raise C.ContractViolation("invalid stored raw for profile")
    a, b = w.atoms
    if w.J_cache is not None:
        ev = InteractionEvent(tuple(-x for x in w.J_cache), tuple(w.J_cache), (("R2_ge_rmin2", True),))
    else:
        ev = law.interact(a, b)
    a, b = law.apply(ev, a, b)
    a_old = C.relative(pos, a, b)
    (ai, ei), (aj, ej) = law.drift(a, w.dt), law.drift(b, w.dt)
    law.drift_obligations(a_old, ei, ej, ai, aj, w.t_steps + 1)
    ev2 = law.interact(ai, aj)
    ai, aj = law.apply(ev2, ai, aj)
    w.atoms = (ai, aj)
    w.J_cache = ev2.impulse_j                              # J: the only part of the event the next step reads
    w.t_steps += 1
    w.events += 1
