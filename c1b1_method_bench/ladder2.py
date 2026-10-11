"""M9 (S3e, survey_only): two-axis refinement ladder -- step h AND position/momentum grid -- on fixed-point Chin 4A.

S3d found that on the production grid FX(48, 80) the rounding during an orbiting pass grows ~1/|rho| and is NOT
reduced by smaller steps, and that the S3c step-pair estimate under-covered the true error (rounding noise of the two
runs is of similar size). M9 separates the two error sources:

  levels (j, g): Chin 4A with h = H0 / 2^j on grid GRIDS[g] = (position bits, momentum bits); world tick H0 = 40 kept.
  one rung at (j, g) uses three runs from the SAME base-grid start state:
      A = (j, g),  B = (j, g+1),  C = (j+1, g+1)
      D_grid = |A - B|  (rounding at grid g; grid g+1 adds ~2^-16 of it)
      D_step = |B - C|  (step error at h_j, measured on the finer grid)
      estimate for C = D_grid + D_step   (each in sweep angle and in relative transit time, as in S3c)
  accept C when both estimates <= tol. Otherwise refine the larger source: grid (g+1) if max(D_grid) >= max(D_step),
  else step (j+1). Past j_max or the last grid: STOP (cap, no output). Runs are cached and reused across rungs.
  The accepted exit state is rounded back to the base grid once (the world keeps its base grid between collisions);
  that rounding happens outside the orbiting phase and is reported separately (out_base).
The base-grid start is exactly representable on every finer grid, so all runs start from the same state.
"""
import mpmath as mm

from .fixedpoint import FxTrack, _half_even, _round_mpf
from .potentials import MU
from .run import initial, signed_angle

H0 = 40
GRIDS = [(48, 80), (64, 96), (80, 112), (96, 128), (112, 144), (128, 160)]   # production ratio fm = fp + 32
DPS = 60


class FxTrackP(FxTrack):
    """FxTrack whose impulse is evaluated with enough digits for its momentum grid: fm bits ~ 0.30103 fm digits, plus
    40 guard digits (fixedpoint.FORCE_DPS = 60 is enough only up to ~112 bits; S3d used <= 112 and is unchanged)."""

    def _kick_raw(self, coef, gradient=False, h=None):
        with mm.workdps(max(60, int(self.fm * 0.30103) + 40)):
            q = self.q_mpf()
            r = mm.sqrt(q[0] ** 2 + q[1] ** 2)
            d1 = self.pot.dV(r)
            c = -d1 / r
            if gradient:
                hh = mm.mpf(h.numerator) / h.denominator
                c += hh ** 2 * d1 * self.pot.d2V(r) / (24 * self.mu * r)
            c *= mm.mpf(coef.numerator) / coef.denominator
            return [_round_mpf(c * x, self.fm) for x in q]


def base_start(pot, E, b, mu=MU, grid=GRIDS[0]):
    """The collision input as the world holds it: the bench initial state rounded to the base grid (exact mpf)."""
    with mm.workdps(40):
        q, p, _ = initial(pot, mu, mm.mpf(E), mm.mpf(b))
    t = FxTrackP(pot, q, p, 0, 'chin', grid[0], grid[1], mu)
    with mm.workdps(DPS):
        return t.q_mpf(), t.p_mpf()


def round_back(t, grid=GRIDS[0]):
    """Exit state of track t rounded to the base grid (per atom: r_j = round(q/2), p = round(p)); returns
    (q_raw_base, p_raw_base, sweep_correction) with the sweep moved to the rounded position."""
    fp, fm = grid
    if any(x % 2 for x in t.qr):                    # q = r_j - r_i = 2 r_j on every grid (FxTrack invariant)
        raise ValueError('relative position raw is not even')
    q_raw = [2 * _half_even(x // 2, 2 ** (t.fp - fp)) for x in t.qr]
    p_raw = [_half_even(x, 2 ** (t.fm - fm)) for x in t.pr_]
    with mm.workdps(DPS):
        qc = t.q_mpf()
        qb = [mm.ldexp(x, -fp) for x in q_raw]
        return q_raw, p_raw, signed_angle(qc, qb)


def ladder2(pot, E, b, tol, j_max=6, grids=GRIDS, mu=MU, h0=H0, max_ticks=300_000, choose=None):
    """Run M9 for one collision. `choose` (tests only) overrides the refine-axis rule: f(dg, ds) -> 'grid'|'step'."""
    with mm.workdps(DPS):
        tol = mm.mpf(tol)
        q0, p0 = base_start(pot, E, b, mu, grids[0])
        cache = {}

        def track(j, g):
            if (j, g) not in cache:
                t = FxTrackP(pot, q0, p0, j, 'chin', grids[g][0], grids[g][1], mu, h0)
                t.run_to_exit(max_ticks)
                cache[(j, g)] = t
            return cache[(j, g)]

        j = g = 0
        rungs, level0 = [], None
        while True:
            if j + 1 > j_max or g + 1 >= len(grids):
                return dict(status='cap_stop', j_out=None, g_out=None, rungs=rungs, level0=level0,
                            substeps=sum(t.substeps for t in cache.values()))
            A, B, C = track(j, g), track(j, g + 1), track(j + 1, g + 1)
            n = max(A.tick, B.tick, C.tick)
            for t in (A, B, C):
                t.run_to(n)
            if level0 is None:
                level0 = A.state()
            lag = lambda x, y: abs(x.r() - y.r()) * mu / abs(C.pr()) / (n * h0)
            dg = (abs(A.sweep - B.sweep), lag(A, B))
            ds = (abs(B.sweep - C.sweep), lag(B, C))
            est = (dg[0] + ds[0], dg[1] + ds[1])
            ok = est[0] <= tol and est[1] <= tol
            rungs.append(dict(j=j, g=g, tick=n, dgrid_sweep=mm.nstr(dg[0], 6), dgrid_time=mm.nstr(dg[1], 6),
                              dstep_sweep=mm.nstr(ds[0], 6), dstep_time=mm.nstr(ds[1], 6),
                              est_sweep=mm.nstr(est[0], 6), est_time=mm.nstr(est[1], 6), accepted=ok,
                              C_state=C.state()))
            if ok:
                qb, pb, dsw = round_back(C, grids[0])
                out = C.state()
                out.update(g=g + 1, grid=list(grids[g + 1]))
                with mm.workdps(DPS):
                    qbm = [mm.ldexp(x, -grids[0][0]) for x in qb]
                    out_base = dict(sweep=mm.nstr(C.sweep + dsw, 45), r=mm.nstr(mm.sqrt(qbm[0] ** 2 + qbm[1] ** 2), 45),
                                    time=out['time'], q_raw=[str(x) for x in qb], p_raw=[str(x) for x in pb],
                                    sweep_shift=mm.nstr(dsw, 6))
                return dict(status='accepted', j_out=j + 1, g_out=g + 1, out=out, out_base=out_base, rungs=rungs,
                            level0=level0, substeps=sum(t.substeps for t in cache.values()))
            pick = choose(dg, ds) if choose else ('grid' if max(dg) >= max(ds) else 'step')
            if pick == 'grid':
                g += 1
            else:
                j += 1
