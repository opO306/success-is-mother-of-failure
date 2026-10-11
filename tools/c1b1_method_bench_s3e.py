"""Method bench S3e study (survey_only): M9 two-axis ladder (c1b1_method_bench.ladder2) on fixed-point Chin 4A.

Same inputs as S3c (killer 84: T5/T6 x 0.3/0.6/0.9 E_max x rho = +-1e-2, 1e-4, 1e-6 ... 1e-10; ordinary 44) plus two
repeats. World layer: ladder2 (tol 1e-9 sweep and relative time, j_max 6, grids 48/80 ... 128/160). Verification layer
(this tool, after the ladder): quadref 80 digits from E, L of the base-grid start, for level 0 (= production-grid
Chin 40), every rung's C run, the accepted output C and its base-grid round-back.
  python tools/c1b1_method_bench_s3e.py OUT.jsonl [WORKERS]
"""
import sys
import time

import mpmath as mm

from c1b1_method_bench import ladder2, orbit, quadref
from c1b1_method_bench.potentials import DE, MU, ExpWall, LennardJones, Morse
from c1b1_method_bench.runner import run_jobs

POTS = dict(T4_exp_wall=ExpWall, T5_morse=Morse, T6_lennard_jones=LennardJones)
TOL = '1e-9'
FRACS = ['0.3', '0.6', '0.9']
RHO_EXP = [2, 4, 6, 7, 8, 9, 10]


def killer_input(pot, frac, rho):
    with mm.workdps(60):
        E = orbit.e_max(pot) * mm.mpf(frac)
        o = orbit.orbit(pot, MU, E)
        return E, o['b_orb'] * (1 + rho), o


def jobs():
    killer = [('killer', p, f, f'{s}1e-{k}', 'main') for k in RHO_EXP for p in ('T5_morse', 'T6_lennard_jones')
              for f in FRACS for s in ('', '-')]
    killer.sort(key=lambda j: -int(j[3].split('e-')[1]))
    ordinary = [('ordinary', p, e, str(b), 'main') for p in ('T5_morse', 'T6_lennard_jones')
                for e in ('0.5', '2', '10', '45') for b in (0, 3, 6, 9)]
    ordinary += [('ordinary', 'T4_exp_wall', e, str(b), 'main') for e in ('10', '20', '33', '45') for b in (2, 4, 6)]
    repeat = [('killer', 'T5_morse', '0.9', '-1e-8', 'repeat'), ('ordinary', 'T6_lennard_jones', '2', '6', 'repeat')]
    return repeat + killer + ordinary


def verify(pot, E, b, res):
    q0, p0 = ladder2.base_start(pot, E, b)
    with mm.workdps(quadref.DPS):
        r0 = mm.sqrt(q0[0] ** 2 + q0[1] ** 2)
        if r0 != 20:
            raise ValueError('base start is not at R0')
        E0 = (p0[0] ** 2 + p0[1] ** 2) / (2 * MU) + pot.V(r0)
        L0 = q0[0] * p0[1] - q0[1] * p0[0]
    states = [res['level0']] + [rg['C_state'] for rg in res['rungs']]
    if res['status'] == 'accepted':
        states += [res['out'], res['out_base']]
    for st in states:
        ref = quadref.reference(pot, MU, E0, L0, mm.mpf(st['r']))
        with mm.workdps(quadref.DPS):
            d_s = mm.mpf(st['sweep']) - ref['sweep']
            st.update(err_sweep=float(abs(d_s)), d_sweep=float(d_s),
                      err_time=float(abs(mm.mpf(st['time']) - ref['time']) / ref['time']))


def one(job):
    kind, potname, e, x, variant = job
    t0, w0 = time.process_time(), time.perf_counter()
    pot = POTS[potname]()
    try:
        meta = {}
        if kind == 'ordinary':
            E, b = DE * mm.mpf(e), mm.mpf(x)
        else:
            E, b, o = killer_input(pot, e, mm.mpf(x))
            meta = dict(E_over_De=float(E / DE), b_orb=mm.nstr(o['b_orb'], 30))
        row = ladder2.ladder2(pot, E, b, TOL)
        verify(pot, E, b, row)
        row.update(meta)
    except Exception as exc:          # recorded, never hidden
        row = dict(status='error', error=repr(exc)[:300])
    row.update(job=dict(kind=kind, pot=potname, e=e, x=x, variant=variant),
               cpu_s=time.process_time() - t0, wall_s=time.perf_counter() - w0)
    return row


if __name__ == '__main__':
    run_jobs(one, jobs(), sys.argv[1], workers=int(sys.argv[2]) if len(sys.argv) > 2 else 4, label='S3e ')
