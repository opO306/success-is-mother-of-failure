"""Method bench S3d study (survey_only): does production-style fixed-point rounding grow near the orbiting boundary?

Every comparison starts both runs from the SAME grid-rounded state (fixedpoint.FxTrack's start), so FX - HP is the
rounding during flight only. HP = the S3c mpmath tracks (refine.Track, 40 digits), FX = fixedpoint.FxTrack.
True errors use quadref (80 digits) with E, L of the rounded start (R0 = 20 is on the grid).

  kdk_fx   KDK h = 40, FX(48, 80) vs HP: T5/T6 x E 0.3/0.6/0.9 E_max x rho = +-1e-2 ... +-1e-8 (each decade)
  grid     KDK h = 40, position grid 64 / 80 bits (momentum 80), and momentum 112 bits (position 48)
  chin_lv  Chin 4A levels j = 0..3, FX(48, 80) vs HP: Morse 0.9 and LJ 0.6 x rho = -1e-4, -1e-6
  m8_fx    the S3c ladder on FX(48, 80) Chin (fixedpoint.fx_refine, tol 1e-9, j_max 6) + quadref check
  ordinary KDK h = 40 FX vs HP away from the boundary
  repeat   two jobs again (determinism)
  python tools/c1b1_method_bench_s3d.py OUT.jsonl [WORKERS]
"""
import sys
import time

import mpmath as mm

from c1b1_method_bench import fixedpoint as fx, orbit, quadref, refine
from c1b1_method_bench.methods import chin4a, kdk
from c1b1_method_bench.potentials import DE, MU, ExpWall, LennardJones, Morse
from c1b1_method_bench.run import R0, initial
from c1b1_method_bench.runner import run_jobs

POTS = dict(T4_exp_wall=ExpWall, T5_morse=Morse, T6_lennard_jones=LennardJones)
TOL = '1e-9'
MAX_TICKS = 300_000
HARD = [('T5_morse', '0.9'), ('T6_lennard_jones', '0.6')]


def killer_input(pot, frac, rho):
    with mm.workdps(60):
        E = orbit.e_max(pot) * mm.mpf(frac)
        o = orbit.orbit(pot, MU, E)
        return E, o['b_orb'] * (1 + rho), o


def jobs():
    out = []
    for p, f in HARD:                                                     # most expensive first
        for x in ('-1e-8', '-1e-6', '-1e-4'):
            out.append(('m8_fx', p, f, x, 48, 80))
    for p in ('T5_morse', 'T6_lennard_jones'):
        for f in ('0.3', '0.6', '0.9'):
            for k in range(2, 9):
                for s in ('', '-'):
                    out.append(('kdk_fx', p, f, f'{s}1e-{k}', 48, 80))
    for p, f in HARD:
        for x in ('1e-4', '-1e-4', '1e-6', '-1e-6', '1e-8', '-1e-8'):
            out += [('grid', p, f, x, 64, 80), ('grid', p, f, x, 80, 80)]
        out.append(('grid', p, f, '-1e-6', 48, 112))
        for x in ('-1e-4', '-1e-6'):
            out += [('chin_lv', p, f, x, 48, 80, j) for j in range(4)]
    out += [('ordinary', p, e, b, 48, 80) for p, e, b in (('T5_morse', '2', '3'), ('T5_morse', '45', '3'),
                                                         ('T6_lennard_jones', '2', '3'), ('T6_lennard_jones', '45', '3'),
                                                         ('T4_exp_wall', '45', '2'))]
    out += [('repeat',) + j[1:] + (None, j[0]) for j in (('kdk_fx', 'T5_morse', '0.9', '-1e-6', 48, 80),
                                                         ('m8_fx', 'T6_lennard_jones', '0.6', '-1e-4', 48, 80))]
    return out


def rounded_EL(fxt):
    with mm.workdps(80):
        q, p = fxt.q_mpf(), fxt.p_mpf()
        r = mm.sqrt(q[0] ** 2 + q[1] ** 2)
        assert r == R0
        return (p[0] ** 2 + p[1] ** 2) / (2 * MU) + fxt.pot.V(r), q[0] * p[1] - q[1] * p[0]


def true_err(pot, E, L, st):
    ref = quadref.reference(pot, MU, E, L, mm.mpf(st['r']))
    with mm.workdps(quadref.DPS):
        return dict(err_sweep=float(abs(mm.mpf(st['sweep']) - ref['sweep'])),
                    err_time=float(abs(mm.mpf(st['time']) - ref['time']) / ref['time']),
                    d_sweep_ref=float(mm.mpf(st['sweep']) - ref['sweep']))


def compare(pot, E, b, method, j, fp, fm):
    """FX and HP from the same rounded start, compared at the common tick; both checked against quadref."""
    with mm.workdps(40):
        q, p, _ = initial(pot, MU, mm.mpf(E), mm.mpf(b))
        f = fx.FxTrack(pot, q, p, j, method, fp, fm)
        E0, L0 = rounded_EL(f)                  # of the rounded START state (S3d test run 1: was taken after the run)
        with mm.workdps(fx.FORCE_DPS):
            q0, p0 = f.q_mpf(), f.p_mpf()
        h = refine.Track(pot, q0, p0, j, MU, 40, chin4a if method == 'chin' else kdk)
        f.run_to_exit(MAX_TICKS)
        h.run_to_exit(MAX_TICKS)
        n = max(f.tick, h.tick)
        f.run_to(n)
        h.run_to(n)
        d_s = abs(f.sweep - h.sweep)
        d_t = abs(f.r() - h.r()) * MU / abs(h.pr()) / (n * 40)
        sf, sh = f.state(), h.state()
    return dict(status='ok', tick=n, d_sweep=float(d_s), d_lag=float(d_t), signed_d_sweep=float(f.sweep - h.sweep),
                fx=dict(sf, **true_err(pot, E0, L0, sf)), hp=dict(sh, **true_err(pot, E0, L0, sh)),
                substeps=f.substeps + h.substeps)


def m8(pot, E, b, fp, fm):
    res = fx.fx_refine(pot, E, b, TOL, 'chin', fp, fm)
    with mm.workdps(40):
        q, p, _ = initial(pot, MU, mm.mpf(E), mm.mpf(b))
        f0 = fx.FxTrack(pot, q, p, 0, 'chin', fp, fm)
    E0, L0 = rounded_EL(f0)
    for st in [res['level0']] + [pr['fine_state'] for pr in res['pairs']]:
        st.update(true_err(pot, E0, L0, st))
    if res['status'] == 'accepted':
        res['out'].update({k: res['pairs'][-1]['fine_state'][k] for k in ('err_sweep', 'err_time')})
    return res


def one(job):
    kind, potname, e, x, fp, fm = job[:6]
    t0, w0 = time.process_time(), time.perf_counter()
    pot = POTS[potname]()
    try:
        meta = {}
        if kind == 'ordinary':
            E, b = DE * mm.mpf(e), mm.mpf(x)
        else:
            E, b, o = killer_input(pot, e, mm.mpf(x))
            meta = dict(E_over_De=float(E / DE), b_orb=mm.nstr(o['b_orb'], 30))
        real = job[7] if kind == 'repeat' else kind
        if real == 'm8_fx':
            row = m8(pot, E, b, fp, fm)
        elif real == 'chin_lv':
            row = compare(pot, E, b, 'chin', job[6], fp, fm)
        else:
            row = compare(pot, E, b, 'kdk', 0, fp, fm)
        row.update(meta)
    except Exception as exc:          # recorded, never hidden
        row = dict(status='error', error=repr(exc)[:300])
    row.update(job=dict(kind=kind, pot=potname, e=e, x=x, fp=fp, fm=fm, j=job[6] if len(job) > 6 else None),
               cpu_s=time.process_time() - t0, wall_s=time.perf_counter() - w0)
    return row


if __name__ == '__main__':
    run_jobs(one, jobs(), sys.argv[1], workers=int(sys.argv[2]) if len(sys.argv) > 2 else 4, label='S3d ')
