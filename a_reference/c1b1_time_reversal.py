"""C1-B1 inbound V0: the exact time reversal of the executor step (lemma TR). It states a property of
c1b1_two_atom.step and never changes it. Design and scope: docs/active/C1B1_INBOUND_V0.md.

Lemma TR. Execution profile: FixedPoint positions and momenta (half-even from_exact, so round(-x) = -round(x)),
drift v2 (the displacement is rounded, then added exactly). T negates every momentum raw and keeps positions. Let
step(s0) succeed and give s1, with s0.J_cache in {None, J(q0)}. Unless a stored or half-step momentum raw equals the
profile minimum (its negation is out of range), step(T s1), with J_cache J(q1) kept or None:
  (i)  returns exactly T s0, with J_cache = J(q0); or
  (ii) raises PhysicsDomainExceeded from the drift-SEGMENT guard, and does so iff
       segment_min_R2(q0 + d, v h) < r_min^2, where v h is the forward step's exact relative drift and
       d = q1 - q0 - v h its rounding residual (|d_k| <= 2^-48). The reverse segment is the forward one moved by d.
It raises nothing else: every impulse it needs is at q1 or q0, which the forward step already decided (the same
rounding questions, so the same STOP / Proof Cache witness, keyed by relative position, component and dt_kick), and
every number it stores is the negation of one the forward step stored.

Proof. _kick does p_i - J, p_j + J, and J depends on positions only. Forward: p' = (p_i0 - J0, p_j0 + J0),
p1 = (p_i' - J1, p_j' + J1). Reverse, first kick at q1: -p_i1 - J1 = -p_i', -p_j1 + J1 = -p_j'. The drift rounds
-p' h/m to -round(p' h/m) exactly, so the positions return to r0; the second kick at q0: -p_i' - J0 = -p_i0,
-p_j' + J0 = -p_j0. The stored-endpoint guard checks |q0|^2, which the forward run stored legally; the segment guard
sees {q1 - s v h : s in [0, 1]} = {q0 + d + (1 - s) v h}.

What TR does NOT give (docs/active/C1B1_INBOUND_V0.md section 3): T maps a forward INBOUND orbit to a BACKWARD
outgoing orbit, so the outgoing shell induction (c1b1_outer_bootstrap, a forward statement from a known entry) does not
certify inbound infall; TR does not shrink the set of positions whose rounding must be decided; D_valid is not closed
under T (a canonical F state reverses to a non-canonical one).
"""
from __future__ import annotations

from a_numeric import FixedPoint
from a_reference import c1b1_two_atom as C

VERSION = "c1b1-time-reversal-v0"


class NotReversible(ValueError):
    """The state is outside lemma TR's premises (profile, drift rule, or a momentum raw at the profile minimum)."""


def _premises(run) -> None:
    if type(run.pos) is not FixedPoint or type(run.mom) is not FixedPoint:
        raise NotReversible("lemma TR is stated for FixedPoint positions and momenta")
    if run.drift != "v2":
        raise NotReversible("lemma TR needs drift v2 (v1 is irreversible at odd positions with ties)")


def time_reverse(run) -> C.Run:
    """T run: a new run with every momentum raw negated, the same positions, dt, profiles and J_cache (the impulse at
    these positions is unchanged). Refuses a momentum raw equal to the profile minimum."""
    _premises(run)
    atoms = []
    for a in run.atoms:
        if any(v == run.mom.lo for v in a.p):
            raise NotReversible("a momentum raw equals the profile minimum; its negation is out of range")
        atoms.append(C.Atom(a.species, a.r, tuple(run.mom.neg(v) for v in a.p)))
    atoms = tuple(atoms)
    return C.Run(run.pos, run.mom, run.dt, atoms, J_cache=run.J_cache, drift=run.drift, initial=atoms)


def forward_drift(run) -> dict:
    """The next step's relative drift, without stepping: q0, the exact relative drift v h, the stored relative
    displacement and the residual d = stored - v h. Raises what step() would raise before its drift (the impulse)."""
    _premises(run)
    pos, mom, dt = run.pos, run.mom, run.dt
    J = run.J_cache if run.J_cache is not None else C.impulse(C.relative(pos, *run.atoms), dt / 2, mom)
    i, j = C._kick(mom, run.atoms, J)
    q0 = C.relative(pos, i, j)
    exact = [tuple(C.exact(mom, a.p)[k] * dt / C.SPECIES_MASS[a.species] for k in range(3)) for a in (i, j)]
    stored = [C.exact(pos, C.displacement(pos, mom, a, dt)) for a in (i, j)]
    vh = tuple(y - x for x, y in zip(*exact))
    moved = tuple(y - x for x, y in zip(*stored))
    return {"q0": q0, "vh": vh, "moved": moved, "d": tuple(m - v for m, v in zip(moved, vh))}


def reverse_segment_passes(run) -> bool:
    """Lemma TR (ii): True iff, after this step, the reverse step's drift-segment guard would pass. Exact."""
    f = forward_drift(run)
    start = tuple(a + b for a, b in zip(f["q0"], f["d"]))
    return C.segment_min_R2(start, f["vh"]) >= C.R_MIN2
