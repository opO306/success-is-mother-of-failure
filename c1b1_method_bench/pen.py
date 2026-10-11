"""M10 (S3f, survey_only): one-dial ladder ("brush pen") -- step and grid refined TOGETHER by a fixed rule.

S3c/S3d measured that BOTH the Chin step error and the fixed-point rounding grow ~1/|rho| near the orbiting boundary,
so their ratio is roughly independent of rho. One dial therefore suffices: level j uses
    h = H0 / 2^j,   position bits fp = FP0 + DBITS * j,   momentum bits fm = fp + 32 (production ratio)
DBITS = 4 because halving h divides the Chin error by 2^4; FP0 = 64 puts the rounding about 1e-3 or less of the step
error at level 0 (S3d: ~2e-14/|rho| at 48 bits; S3c: 2.2e-15/|rho| at h = 40; 2^-16 * 2e-14 = 3e-19).
Ladder (as S3c): compare levels j, j+1 at the common tick; est_step = |theta_j - theta_{j+1}| (+ radial-lag time).
When est_step <= tol, the rounding of level j+1 is CHECKED once (rule: no unknown error): the same h on a grid
CHECK_BITS finer, D_round = |C - C'|; accept C = level j+1 if est_step + D_round <= tol, else go on down the dial.
Cap j_max; then STOP. Start = the collision input on the world base grid (48, 80); exit rounded back to it (as S3e).
Per-track CPU time is recorded (instrumentation only; it does not touch the state).
"""
import time

import mpmath as mm

from .ladder2 import DPS, FxTrackP, base_start, round_back
from .potentials import MU

H0 = 40
FP0, DBITS, CHECK_BITS = 64, 4, 16
BASE = (48, 80)


def grid(j, fp0=FP0, dbits=DBITS):
    fp = fp0 + dbits * j
    return fp, fp + 32


def pen(pot, E, b, tol, j_max=6, fp0=FP0, dbits=DBITS, check_bits=CHECK_BITS, mu=MU, h0=H0, max_ticks=300_000):
    with mm.workdps(DPS):
        tol = mm.mpf(tol)
        q0, p0 = base_start(pot, E, b, mu, BASE)
        tracks, cpu = {}, {}

        def track(j, extra=0):
            key = (j, extra)
            if key not in tracks:
                fp, fm = grid(j, fp0, dbits)
                t0 = time.process_time()
                t = FxTrackP(pot, q0, p0, j, 'chin', fp + extra, fm + extra, mu, h0)
                t.run_to_exit(max_ticks)
                tracks[key], cpu[key] = t, time.process_time() - t0
            return tracks[key]

        def advance(ts, n):
            for t in ts:
                key = next(k for k, v in tracks.items() if v is t)
                t0 = time.process_time()
                t.run_to(n)
                cpu[key] += time.process_time() - t0

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
                                        time=C.state()['time'], sweep_shift=mm.nstr(dsw, 6))
                    return dict(status='accepted', j_out=j + 1, bits_out=list(grid(j + 1, fp0, dbits)),
                                out=C.state(), out_base=out_base, pairs=pairs, level0=level0,
                                substeps=sum(t.substeps for t in tracks.values()),
                                track_cost=[dict(j=k[0], extra=k[1], bits=list(grid(k[0], fp0, dbits)),
                                                 substeps=tracks[k].substeps, cpu_s=cpu[k]) for k in sorted(tracks)])
        return dict(status='cap_stop', j_out=None, pairs=pairs, level0=level0,
                    substeps=sum(t.substeps for t in tracks.values()),
                    track_cost=[dict(j=k[0], extra=k[1], bits=list(grid(k[0], fp0, dbits)),
                                     substeps=tracks[k].substeps, cpu_s=cpu[k]) for k in sorted(tracks)])
