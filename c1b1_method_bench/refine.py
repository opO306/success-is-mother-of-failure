"""M8 (S3c, survey_only): per-collision refinement ladder on Chin 4A, world tick fixed at H0 = 40.

World clock: every level advances in ticks of H0. Level j only splits each tick into 2^j Chin 4A substeps of
h = H0 / 2^j, so every level has a state at every world tick (no world-tick state is skipped). A collision ends at
the first tick with r >= R0 and outward motion.

Ladder: levels are compared in pairs (j, j+1) at a common tick N = the later of the two runs' current ticks once both
have exited (the other run is advanced to N):
    est_sweep = |theta_j(N) - theta_{j+1}(N)|
    est_time  = |r_j(N) - r_{j+1}(N)| mu / |p_r,{j+1}(N)| / (N H0)    (radial lag converted to transit time)
The finer run is accepted when both are <= tol. The full difference is used as the estimate; the asymptotic 4th-order
factor (finer error ~ difference / 15) is NOT applied. Otherwise the next pair (j+1, j+2) is tried. After the pair
(j_max - 1, j_max) the collision STOPs with no output (declared cap, fail closed).

This is mpmath binary floating point: the production fixed-point rounding is not represented (designer decision
2026-10-11; checked in a later step). The estimator has no reference access; the verification layer (quadref) is
applied outside this module by the study tool.
"""
import mpmath as mm

from .methods import chin4a
from .potentials import MU
from .run import R0, initial, signed_angle

H0 = 40


class MaxTicks(Exception):
    pass


class Track:
    """One level of the ladder: Chin 4A (or `step`) with 2^j substeps per world tick, tick states only."""

    def __init__(self, pot, q, p, j, mu=MU, h0=H0, step=chin4a):
        self.pot, self.q, self.p, self.mu, self.step = pot, list(q), list(p), mu, step
        self.j, self.sub = j, 2 ** j
        self.h0 = mm.mpf(h0)
        self.h = self.h0 / self.sub
        self.tick, self.sweep, self.exit_tick, self.substeps = 0, mm.mpf(0), None, 0

    def r(self):
        return mm.sqrt(self.q[0] ** 2 + self.q[1] ** 2)

    def pr(self):
        return (self.q[0] * self.p[0] + self.q[1] * self.p[1]) / self.r()

    def advance_tick(self):
        for _ in range(self.sub):
            q_old = self.q
            self.q, self.p = self.step(self.pot, self.q, self.p, self.h, self.mu)
            self.sweep += signed_angle(q_old, self.q)
        self.substeps += self.sub
        self.tick += 1

    def run_to_exit(self, max_ticks):
        while self.exit_tick is None:
            self.advance_tick()
            if self.r() >= R0 and self.pr() > 0:
                self.exit_tick = self.tick
            elif self.tick >= max_ticks:
                raise MaxTicks(f'level {self.j}: no exit within {max_ticks} ticks')

    def run_to(self, n):
        while self.tick < n:
            self.advance_tick()

    def state(self):
        return dict(j=self.j, tick=self.tick, sweep=mm.nstr(self.sweep, 45), r=mm.nstr(self.r(), 45),
                    time=mm.nstr(self.tick * self.h0, 45), exit_tick=self.exit_tick, substeps=self.substeps)


def refine(pot, E, b, tol, j_max=6, dps=40, mu=MU, h0=H0, max_ticks=300_000, step=chin4a,
           next_level=lambda j: j + 1):
    """Run the ladder for one collision. Returns dict(status='accepted'|'cap_stop', j_out, pairs, ...).
    next_level exists only for fault injection in tests (default: one level finer)."""
    with mm.workdps(dps):
        E, b, tol = mm.mpf(E), mm.mpf(b), mm.mpf(tol)
        q, p, L = initial(pot, mu, E, b)
        coarse = Track(pot, q, p, 0, mu, h0, step)
        coarse.run_to_exit(max_ticks)
        first = None
        pairs, substeps = [], coarse.substeps
        for _ in range(j_max):
            fine = Track(pot, q, p, next_level(coarse.j), mu, h0, step)
            fine.run_to_exit(max_ticks)
            n = max(coarse.tick, fine.tick)
            before = coarse.substeps
            coarse.run_to(n)
            fine.run_to(n)
            substeps += fine.substeps + coarse.substeps - before
            if first is None:
                first = coarse.state()
            est_s = abs(coarse.sweep - fine.sweep)
            est_t = abs(coarse.r() - fine.r()) * mu / abs(fine.pr()) / (n * coarse.h0)
            ok = est_s <= tol and est_t <= tol
            pairs.append(dict(coarse=coarse.j, fine=fine.j, tick=n, est_sweep=mm.nstr(est_s, 6),
                              est_time=mm.nstr(est_t, 6), accepted=ok, fine_state=fine.state()))
            if ok:
                return dict(status='accepted', j_out=fine.j, out=fine.state(), level0=first, pairs=pairs,
                            substeps=substeps, L=mm.nstr(L, 45), E=mm.nstr(E, 45), b=mm.nstr(b, 45))
            coarse = fine
        return dict(status='cap_stop', j_out=None, level0=first, pairs=pairs, substeps=substeps,
                    L=mm.nstr(L, 45), E=mm.nstr(E, 45), b=mm.nstr(b, 45))
