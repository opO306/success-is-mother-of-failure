"""M10 "brush pen" (c1b1_method_bench.pen, S3f rule unchanged) started from a STORED base-grid state (T7).

pen.pen builds its start from (E, b) with the bench initial state; T7 starts from the raw O-1 / canonical states.
pen_state repeats pen.pen line for line with the start state passed in, and optionally the exact reduced mass
(Fraction) for the drift (the bench MU is an mpf; the world drift divides by the exact atom mass 2 mu).
With mu_exact=None and the bench start it returns exactly what pen.pen returns (test: test_pen_state_equals_pen).
pen.py itself is left unchanged (S3f used it).
"""
import time

import mpmath as mm

from c1b1_method_bench.ladder2 import DPS, FxTrackP, round_back
from c1b1_method_bench.pen import BASE, CHECK_BITS, DBITS, FP0, H0, grid
from c1b1_method_bench.potentials import MU


class FxTrackX(FxTrackP):
    """FxTrackP whose drift uses an exact rational reduced mass."""

    def __init__(self, pot, q, p, j, method, fp, fm, mu, h0, mu_exact):
        super().__init__(pot, q, p, j, method, fp, fm, mu, h0)
        self.mu_x = mu_exact


def pen_state(pot, q0, p0, tol, j_max=6, fp0=FP0, dbits=DBITS, check_bits=CHECK_BITS, mu=MU, h0=H0,
              max_ticks=300_000, mu_exact=None):
    with mm.workdps(DPS):
        tol = mm.mpf(tol)
        mu = mm.mpf(mu)
        tracks, cpu = {}, {}

        def track(j, extra=0):
            key = (j, extra)
            if key not in tracks:
                fp, fm = grid(j, fp0, dbits)
                t0 = time.process_time()
                if mu_exact is None:
                    t = FxTrackP(pot, q0, p0, j, 'chin', fp + extra, fm + extra, mu, h0)
                else:
                    t = FxTrackX(pot, q0, p0, j, 'chin', fp + extra, fm + extra, mu, h0, mu_exact)
                t.run_to_exit(max_ticks)
                tracks[key], cpu[key] = t, time.process_time() - t0
            return tracks[key]

        def advance(ts, n):
            for t in ts:
                key = next(k for k, v in tracks.items() if v is t)
                t0 = time.process_time()
                t.run_to(n)
                cpu[key] += time.process_time() - t0

        def cost():
            return [dict(j=k[0], extra=k[1], bits=list(grid(k[0], fp0, dbits)), substeps=tracks[k].substeps,
                         cpu_s=cpu[k]) for k in sorted(tracks)]

        lag = lambda x, y, ref, n: abs(x.r() - y.r()) * mu / abs(ref.pr()) / (n * h0)
        pairs, level0 = [], None
        for j in range(j_max):
            A, C = track(j), track(j + 1)
            n = max(A.tick, C.tick)
            advance((A, C), n)
            if level0 is None:
                level0 = A.state()
            es = (abs(A.sweep - C.sweep), lag(A, C, C, n))
            rec = dict(j=j, tick=n, est_step_sweep=mm.nstr(es[0], 6), est_step_time=mm.nstr(es[1], 6),
                       C_state=C.state(), C_bits=list(grid(j + 1, fp0, dbits)))
            pairs.append(rec)
            if es[0] <= tol and es[1] <= tol:
                Cp = track(j + 1, check_bits)
                n2 = max(n, Cp.tick)
                advance((A, C, Cp), n2)
                dr = (abs(C.sweep - Cp.sweep), lag(C, Cp, Cp, n2))
                est = (es[0] + dr[0], es[1] + dr[1])
                rec.update(checked=True, tick_check=n2, d_round_sweep=mm.nstr(dr[0], 6),
                           d_round_time=mm.nstr(dr[1], 6), est_sweep=mm.nstr(est[0], 6), est_time=mm.nstr(est[1], 6),
                           C_state=C.state())
                if est[0] <= tol and est[1] <= tol:
                    qb, pb, dsw = round_back(C, BASE)
                    with mm.workdps(DPS):
                        qbm = [mm.ldexp(x, -BASE[0]) for x in qb]
                        out_base = dict(sweep=mm.nstr(C.sweep + dsw, 45),
                                        r=mm.nstr(mm.sqrt(qbm[0] ** 2 + qbm[1] ** 2), 45),
                                        time=C.state()['time'], sweep_shift=mm.nstr(dsw, 6),
                                        q_raw=[str(x) for x in qb], p_raw=[str(x) for x in pb])
                    return dict(status='accepted', j_out=j + 1, bits_out=list(grid(j + 1, fp0, dbits)),
                                out=C.state(), out_base=out_base, pairs=pairs, level0=level0,
                                substeps=sum(t.substeps for t in tracks.values()), track_cost=cost())
        return dict(status='cap_stop', j_out=None, pairs=pairs, level0=level0,
                    substeps=sum(t.substeps for t in tracks.values()), track_cost=cost())
