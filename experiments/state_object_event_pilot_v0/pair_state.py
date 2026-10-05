"""PART A8: lossless pair current state for the symmetric A2 case of C1-B1 only.

Stored state: S_r = r_i + r_j, D_r = r_j - r_i, S_p = p_i + p_j, D_p = p_j - p_i (raw integers; the SUM, not the
half-sum, so no half-grid value is ever needed: r_i = (S_r - D_r)/2 is exact because S_r - D_r = 2 r_i).
Stepping follows c1b1_two_atom.step with the canonical primitives and the symmetric shortcut, valid only while
S_r = 0 and S_p = 0: then r_i = -r_j, p_i = -p_j, and the half-even rounding is odd-symmetric, so atom i's displacement
is the negated raw of atom j's (one rounding instead of two). If the precondition fails the step refuses
(PairStateRefused); nothing is approximated. Both atoms' range checks are kept.
"""

from __future__ import annotations

from fractions import Fraction as Q

from a_reference import c1b1_two_atom as C


class PairStateRefused(Exception):
    """PAIR_STATE_REFUSED: the symmetric pair shortcut does not apply to this state."""


class _AtomView:
    __slots__ = ("species", "r", "p")

    def __init__(self, species, r, p):
        self.species, self.r, self.p = species, r, p


class PairRun:
    def __init__(self, pos, mom, dt, species, S_r, D_r, S_p, D_p, J_cache, t_steps):
        self.pos, self.mom, self.dt, self.species = pos, mom, dt, species
        self.S_r, self.D_r, self.S_p, self.D_p = S_r, D_r, S_p, D_p
        self.J_cache, self.t_steps = J_cache, t_steps
        self.refused_at = None

    @classmethod
    def from_run(cls, run):
        a, b = run.atoms
        if a.species != b.species:
            raise PairStateRefused("different species")
        S_r = tuple(x + y for x, y in zip(a.r, b.r))
        D_r = tuple(y - x for x, y in zip(a.r, b.r))
        S_p = tuple(x + y for x, y in zip(a.p, b.p))
        D_p = tuple(y - x for x, y in zip(a.p, b.p))
        w = cls(run.pos, run.mom, run.dt, a.species, S_r, D_r, S_p, D_p, run.J_cache, run.t_steps)
        if w.atoms[0].r != tuple(a.r) or w.atoms[1].p != tuple(b.p):
            raise PairStateRefused("reconstruction differs")
        return w

    @property
    def atoms(self):
        """Reconstructed stored atoms (exact integer halving; parity is guaranteed by construction)."""
        ri = tuple((s - d) // 2 for s, d in zip(self.S_r, self.D_r))
        rj = tuple((s + d) // 2 for s, d in zip(self.S_r, self.D_r))
        pi = tuple((s - d) // 2 for s, d in zip(self.S_p, self.D_p))
        pj = tuple((s + d) // 2 for s, d in zip(self.S_p, self.D_p))
        return _AtomView(self.species, ri, pi), _AtomView(self.species, rj, pj)

    def state_core(self):
        return (self.species, self.S_r, self.D_r, self.S_p, self.D_p, self.J_cache, self.t_steps)

    def report(self):
        return {"refused_at": self.refused_at}


def _parity_ok(S, D):
    return all((s - d) % 2 == 0 for s, d in zip(S, D))


def step(w: PairRun) -> None:
    pos, mom, dt = w.pos, w.mom, w.dt
    if any(w.S_r) or any(w.S_p) or not _parity_ok(w.S_r, w.D_r) or not _parity_ok(w.S_p, w.D_p):
        w.refused_at = w.t_steps
        raise PairStateRefused(f"symmetric precondition fails at step {w.t_steps}")
    half = dt / 2
    rj = tuple(d // 2 for d in w.D_r)                      # S_r = 0: r_j = D_r / 2, r_i = -r_j
    pj = tuple(d // 2 for d in w.D_p)
    for profile, raws in ((pos, rj), (mom, pj)):           # both atoms: the signed range is not symmetric
        if not all(profile.valid_raw(v) and profile.valid_raw(-v) for v in raws):
            raise C.ContractViolation("invalid stored raw for profile")
    if w.J_cache is not None and not all(mom.valid_raw(v) for v in w.J_cache):
        raise C.ContractViolation("invalid stored raw for profile")
    rel = tuple(Q(2 * x, 1 << pos.frac_bits) for x in rj)  # r_j - r_i, exact
    J = w.J_cache if w.J_cache is not None else C.impulse(rel, half, mom)

    def kick(p, J):                                        # p_i <- p_i - J and p_j <- p_j + J, with p_i = -p_j
        new_j = tuple(C._limit(mom.from_exact, x + y) for x, y in zip(C.exact(mom, p), C.exact(mom, J)))
        for v in new_j:
            C._limit(mom.from_exact, mom.to_exact(-v))     # atom i's range check (same value, negated)
        return new_j
    pj = kick(pj, J)
    m = C.SPECIES_MASS[w.species]
    pj_exact = C.exact(mom, pj)
    dj = tuple(C._limit(pos.from_exact, p * dt / m) for p in pj_exact)
    rj_new = tuple(C._limit(pos.add, r, d) for r, d in zip(rj, dj))
    for v in rj_new:
        C._limit(pos.neg, v)                               # atom i's position range check
    a_old = rel
    d_exact = tuple(2 * p * dt / m for p in pj_exact)      # (p_j - p_i) dt / m
    if C.segment_min_R2(a_old, d_exact) < C.R_MIN2:
        raise C.PhysicsDomainExceeded(f"drift segment enters R < r_min at step {w.t_steps + 1}")
    rel_new = tuple(Q(2 * x, 1 << pos.frac_bits) for x in rj_new)
    if sum((x * x for x in rel_new), Q(0)) < C.R_MIN2:
        raise C.PhysicsDomainExceeded(f"stored positions at R < r_min at step {w.t_steps + 1}")
    J2 = C.impulse(rel_new, half, mom)
    pj = kick(pj, J2)
    w.D_r = tuple(2 * x for x in rj_new)
    w.D_p = tuple(2 * x for x in pj)
    w.J_cache = J2
    w.t_steps += 1
