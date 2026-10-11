"""S3d (survey_only): production-style fixed-point arithmetic on the bench relative coordinate.

Independent re-implementation of the documented C1-B1 rounding rule (a_reference/c1b1_two_atom.py module docstring,
contract c1b1-two-atom-v2; read, NOT imported, NOT bit-checked against it). Positions on the grid 2^-FP (production
FX(96,48): FP = 48), momenta on 2^-FM (production FX(96,80): FM = 80). Two equal atoms, total momentum 0, so the
relative momentum equals atom j's momentum and the relative position is r_j - r_i:
  start  r_j = round_p(q/2), r_i = -r_j  ->  q = 2 round_p(q/2);   p = round_m(p)
  kick   J_k = round_m(F(R) q_k / R * c)  once per component, R = sqrt(q.q) never rounded;   p <- p + J (exact)
  drift  each atom moves round_p(p_atom d / m_atom), m_atom = 2 mu, opposite signs  ->  q <- q + 2 round_p(p d / (2 mu))
round = nearest, ties to even (odd-symmetric). The force value is evaluated with mpmath at FORCE_DPS digits and
rounded once; within 1e-30 grid units of a tie the step stops (Undecided, fail closed) instead of guessing.
Methods: KDK (production) and Chin 4A (each kick and each half drift rounded the same way).
The ladder fx_refine repeats refine.refine's rule on this arithmetic (refine.py is left unchanged: S3c used it).
"""
from fractions import Fraction

import mpmath as mm

from .potentials import MU
from .run import R0, initial, signed_angle

FORCE_DPS = 60
H0 = 40


class Undecided(Exception):
    pass


def _exact(x):
    """Exact Fraction of an mpf (binary)."""
    man, exp = mm.mpf(x).man_exp
    return Fraction(man) * Fraction(2) ** exp


def _half_even(num, den):
    q, r = divmod(num, den)
    if 2 * r > den or (2 * r == den and q & 1):
        q += 1
    return q


def _round_mpf(x, bits):
    """round(x * 2^bits) to nearest; refuse (Undecided) when x is within 1e-30 units of a tie."""
    y = mm.ldexp(x, bits)
    f = y - mm.floor(y)
    if abs(f - mm.mpf('0.5')) < mm.mpf('1e-30'):
        raise Undecided('impulse value too close to a rounding tie at the working precision')
    return int(mm.nint(y))


class FxTrack:
    """Fixed-point run of one level j (2^j substeps per world tick of H0), KDK or Chin 4A; tick states only."""

    def __init__(self, pot, q, p, j, method='kdk', fp=48, fm=80, mu=MU, h0=H0):
        self.pot, self.j, self.method, self.fp, self.fm = pot, j, method, fp, fm
        self.sub = 2 ** j
        self.h = Fraction(h0) / self.sub
        self.h0 = Fraction(h0)
        self.mu, self.mu_x = mm.mpf(mu), _exact(mu)
        with mm.workdps(FORCE_DPS):
            self.qr = [2 * _round_mpf(mm.mpf(x) / 2, fp) for x in q]
            self.pr_ = [_round_mpf(mm.mpf(x), fm) for x in p]
        self.tick, self.substeps, self.exit_tick = 0, 0, None
        self.sweep = mm.mpf(0)
        self._J = None                       # cached second half kick (same positions, same value by definition)

    # exact <-> mpf
    def q_mpf(self):
        return [mm.ldexp(x, -self.fp) for x in self.qr]

    def p_mpf(self):
        return [mm.ldexp(x, -self.fm) for x in self.pr_]

    def _kick_raw(self, coef, gradient=False, h=None):
        with mm.workdps(FORCE_DPS):
            q = self.q_mpf()
            r = mm.sqrt(q[0] ** 2 + q[1] ** 2)
            d1 = self.pot.dV(r)
            c = -d1 / r
            if gradient:                     # h is a Fraction: convert explicitly (S3d test run 1)
                hh = mm.mpf(h.numerator) / h.denominator
                c += hh ** 2 * d1 * self.pot.d2V(r) / (24 * self.mu * r)
            c *= mm.mpf(coef.numerator) / coef.denominator
            return [_round_mpf(c * x, self.fm) for x in q]

    def _drift(self, d):
        # q_raw += 2 round_p(p d / (2 mu)) in units 2^-fp; p = p_raw 2^-fm
        num_scale = d * Fraction(2) ** self.fp / (Fraction(2) ** self.fm * 2 * self.mu_x)
        for k in range(2):
            v = self.pr_[k] * num_scale
            self.qr[k] += 2 * _half_even(v.numerator, v.denominator)

    def _substep(self):
        h = self.h
        if self.method == 'kdk':
            J = self._J if self._J is not None else self._kick_raw(h / 2)
            self.pr_ = [a + b for a, b in zip(self.pr_, J)]
            self._drift(h)
            self._J = self._kick_raw(h / 2)
            self.pr_ = [a + b for a, b in zip(self.pr_, self._J)]
        elif self.method == 'chin':
            J = self._J if self._J is not None else self._kick_raw(h / 6)
            self.pr_ = [a + b for a, b in zip(self.pr_, J)]
            self._drift(h / 2)
            G = self._kick_raw(2 * h / 3, gradient=True, h=h)
            self.pr_ = [a + b for a, b in zip(self.pr_, G)]
            self._drift(h / 2)
            self._J = self._kick_raw(h / 6)
            self.pr_ = [a + b for a, b in zip(self.pr_, self._J)]
        else:
            raise ValueError(self.method)

    def advance_tick(self):
        for _ in range(self.sub):
            q_old = self.q_mpf()
            self._substep()
            self.sweep += signed_angle(q_old, self.q_mpf())
        self.substeps += self.sub
        self.tick += 1

    def r(self):
        q = self.q_mpf()
        return mm.sqrt(q[0] ** 2 + q[1] ** 2)

    def pr(self):
        q, p = self.q_mpf(), self.p_mpf()
        return (q[0] * p[0] + q[1] * p[1]) / self.r()

    def run_to_exit(self, max_ticks):
        while self.exit_tick is None:
            self.advance_tick()
            if self.r() >= R0 and self.pr() > 0:
                self.exit_tick = self.tick
            elif self.tick >= max_ticks:
                raise RuntimeError(f'level {self.j}: no exit within {max_ticks} ticks')

    def run_to(self, n):
        while self.tick < n:
            self.advance_tick()

    def state(self):
        return dict(j=self.j, tick=self.tick, sweep=mm.nstr(self.sweep, 45), r=mm.nstr(self.r(), 45),
                    time=mm.nstr(self.tick * mm.mpf(self.h0.numerator), 45), exit_tick=self.exit_tick,
                    substeps=self.substeps, q_raw=[str(x) for x in self.qr], p_raw=[str(x) for x in self.pr_])


def start(pot, E, b, fp=48, fm=80, mu=MU, dps=40):
    """Bench initial state at R0 rounded to the grids; returns (q_mpf, p_mpf) of the ROUNDED state (exact in mpf)."""
    with mm.workdps(dps):
        q, p, _ = initial(pot, mu, mm.mpf(E), mm.mpf(b))
    t = FxTrack(pot, q, p, 0, fp=fp, fm=fm, mu=mu)
    with mm.workdps(FORCE_DPS):
        return t.q_mpf(), t.p_mpf()


def fx_refine(pot, E, b, tol, method='chin', fp=48, fm=80, j_max=6, mu=MU, h0=H0, max_ticks=300_000, dps=40):
    """refine.refine's ladder rule (same estimates, same acceptance, same cap) on the fixed-point arithmetic."""
    with mm.workdps(dps):
        q, p, _ = initial(pot, mu, mm.mpf(E), mm.mpf(b))
        tol = mm.mpf(tol)
        coarse = FxTrack(pot, q, p, 0, method, fp, fm, mu, h0)
        coarse.run_to_exit(max_ticks)
        pairs, first, substeps = [], None, coarse.substeps
        for _ in range(j_max):
            fine = FxTrack(pot, q, p, coarse.j + 1, method, fp, fm, mu, h0)
            fine.run_to_exit(max_ticks)
            n = max(coarse.tick, fine.tick)
            before = coarse.substeps
            coarse.run_to(n)
            fine.run_to(n)
            substeps += fine.substeps + coarse.substeps - before
            if first is None:
                first = coarse.state()
            est_s = abs(coarse.sweep - fine.sweep)
            est_t = abs(coarse.r() - fine.r()) * mu / abs(fine.pr()) / (n * h0)
            ok = est_s <= tol and est_t <= tol
            pairs.append(dict(coarse=coarse.j, fine=fine.j, tick=n, est_sweep=mm.nstr(est_s, 6),
                              est_time=mm.nstr(est_t, 6), accepted=ok, fine_state=fine.state()))
            if ok:
                return dict(status='accepted', j_out=fine.j, out=fine.state(), level0=first, pairs=pairs,
                            substeps=substeps)
            coarse = fine
        return dict(status='cap_stop', j_out=None, level0=first, pairs=pairs, substeps=substeps)
