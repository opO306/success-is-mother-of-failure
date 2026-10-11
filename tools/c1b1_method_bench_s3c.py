"""Method bench S3c study (survey_only): M8 per-collision refinement ladder (c1b1_method_bench.refine).

World layer: refine.refine (Chin 4A, H0 = 40, tol = 1e-9 on sweep angle and relative transit time, cap j_max = 6).
Verification layer (this tool, after the ladder has finished): quadref.reference at 80 digits for level 0 and for the
finer run of every compared pair, at that run's own radius and tick time.

  ordinary  T5/T6 E 0.5/2/10/45 De x b 0/3/6/9, T4 E 10/20/33/45 De x b 2/4/6
  killer    T5/T6 x E 0.3/0.6/0.9 E_max x rho = +-1e-2, 1e-4, 1e-6, 1e-7, 1e-8, 1e-9, 1e-10
  repeat    four inputs run again (determinism)
  dps50     two inputs at 50 digits (precision)
  cross     T5/T6 x 3 E x rho = +1e-8, +1e-9, +1e-10: c1b1_o1.continuous.scatter (40 digits) against quadref 80
            (narrow-band turning-point risk of the sealed module, recorded only)
One fresh process per job (c1b1_method_bench.runner). Rows are appended to JSONL.
  python tools/c1b1_method_bench_s3c.py OUT.jsonl [WORKERS]
"""
import sys
import time

import mpmath as mm

from c1b1_method_bench import orbit, quadref, refine
from c1b1_method_bench.potentials import DE, MU, ExpWall, LennardJones, Morse
from c1b1_method_bench.run import initial
from c1b1_method_bench.runner import run_jobs

POTS = dict(T4_exp_wall=ExpWall, T5_morse=Morse, T6_lennard_jones=LennardJones)
TOL = '1e-9'
J_MAX = 6
FRACS = ['0.3', '0.6', '0.9']
RHO_EXP = [2, 4, 6, 7, 8, 9, 10]
REPEAT = [('killer', 'T5_morse', '0.9', '-1e-8'), ('killer', 'T6_lennard_jones', '0.6', '1e-8'),
          ('ordinary', 'T4_exp_wall', '45', '2'), ('ordinary', 'T6_lennard_jones', '2', '6')]
DPS50 = [('killer', 'T5_morse', '0.9', '-1e-8'), ('killer', 'T6_lennard_jones', '0.9', '1e-8')]


def killer_input(pot, frac, rho):
    with mm.workdps(60):
        E = orbit.e_max(pot) * mm.mpf(frac)
        o = orbit.orbit(pot, MU, E)
        return E, o['b_orb'] * (1 + rho), o


def jobs():
    killer = [('killer', p, f, f'{s}1e-{k}', 'main') for k in RHO_EXP for p in ('T5_morse', 'T6_lennard_jones')
              for f in FRACS for s in ('', '-')]
    killer.sort(key=lambda j: -int(j[3].split('e-')[1]))          # most expensive (smallest |rho|) first
    ordinary = [('ordinary', p, e, str(b), 'main') for p in ('T5_morse', 'T6_lennard_jones')
                for e in ('0.5', '2', '10', '45') for b in (0, 3, 6, 9)]
    ordinary += [('ordinary', 'T4_exp_wall', e, str(b), 'main') for e in ('10', '20', '33', '45') for b in (2, 4, 6)]
    extra = [j + ('repeat',) for j in REPEAT] + [j + ('dps50',) for j in DPS50]
    cross = [('killer', p, f, f'1e-{k}', 'cross') for k in (8, 9, 10) for p in ('T5_morse', 'T6_lennard_jones')
             for f in FRACS]
    return extra + killer + ordinary + cross


def verify(pot, E, b, res, dps):
    """Verification layer: true-Hamiltonian quadrature at each recorded state's own radius (80 digits)."""
    with mm.workdps(dps):
        E, b = mm.mpf(E), mm.mpf(b)
        _, _, L = initial(pot, MU, E, b)
    states = [res['level0']] + [pr['fine_state'] for pr in res['pairs']]
    for st in states:
        ref = quadref.reference(pot, MU, E, L, mm.mpf(st['r']))
        with mm.workdps(quadref.DPS):
            d_s = mm.mpf(st['sweep']) - ref['sweep']
            d_t = mm.mpf(st['time']) - ref['time']
            st.update(err_sweep=float(abs(d_s)), err_time=float(abs(d_t) / ref['time']), d_sweep=float(d_s),
                      ref_sweep=mm.nstr(ref['sweep'], 30), ref_time=mm.nstr(ref['time'], 30))
    if res['status'] == 'accepted':
        res['out'].update({k: res['pairs'][-1]['fine_state'][k] for k in ('err_sweep', 'err_time', 'd_sweep')})


def cross(pot, E, b):
    from c1b1_o1 import continuous
    with mm.workdps(40):
        E, b = mm.mpf(E), mm.mpf(b)
        q, p, L = initial(pot, MU, E, b)
    ref = quadref.reference(pot, MU, E, L, mm.mpf(20), time=False)
    row = dict(status='ok', ref_sweep=mm.nstr(ref['sweep'], 30), ref_r_turn=mm.nstr(ref['r_turn'], 20))
    try:
        with mm.workdps(40):
            got = continuous.scatter(pot.V, MU, q, p, mm.mpf(20), 40)
        with mm.workdps(quadref.DPS):
            row.update(cont='ok', cont_sweep=got['sweep'], cont_r_min=got['r_min'],
                       diff_sweep=float(abs(mm.mpf(got['sweep']) - ref['sweep'])))
    except continuous.Unresolved as exc:
        row.update(cont='unresolved', cont_error=repr(exc)[:200])
    return row


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
            meta = dict(E_over_De=float(E / DE), b_orb=mm.nstr(o['b_orb'], 30), r_star=mm.nstr(o['r_star'], 20))
        if variant == 'cross':
            row = cross(pot, E, b)
        else:
            dps = 50 if variant == 'dps50' else 40
            row = refine.refine(pot, E, b, TOL, j_max=J_MAX, dps=dps)
            verify(pot, E, b, row, dps)
        row.update(meta)
    except Exception as exc:          # recorded, never hidden
        row = dict(status='error', error=repr(exc)[:300])
    row.update(job=dict(kind=kind, pot=potname, e=e, x=x, variant=variant),
               cpu_s=time.process_time() - t0, wall_s=time.perf_counter() - w0)
    return row


if __name__ == '__main__':
    run_jobs(one, jobs(), sys.argv[1], workers=int(sys.argv[2]) if len(sys.argv) > 2 else 4, label='S3c ')
