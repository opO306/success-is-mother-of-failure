"""Method bench S3f study (survey_only): M10 one-dial ladder (c1b1_method_bench.pen) + grid-bits cost probe.

  study (default): the S3e inputs (killer 84, ordinary 44, two repeats); world layer pen.pen (tol 1e-9, j_max 6);
                   verification layer: quadref 80 digits from E, L of the base-grid start, for level 0, every pair's C,
                   the accepted output and its base-grid round-back.
  bits:            CPU per Chin substep vs grid bits (48 ... 128, momentum +32) on one input, h = 40, three
                   interleaved rounds in ONE process (run it alone: no other jobs on the machine).
  python tools/c1b1_method_bench_s3f.py OUT.jsonl [WORKERS]
  python tools/c1b1_method_bench_s3f.py --bits OUT.json
"""
import json
import sys
import time

import mpmath as mm

from c1b1_method_bench import ladder2, orbit, pen, quadref
from c1b1_method_bench.potentials import DE, MU, ExpWall, LennardJones, Morse
from c1b1_method_bench.runner import run_jobs

POTS = dict(T4_exp_wall=ExpWall, T5_morse=Morse, T6_lennard_jones=LennardJones)
TOL = '1e-9'
FRACS = ['0.3', '0.6', '0.9']
RHO_EXP = [2, 4, 6, 7, 8, 9, 10]
BITS = [48, 64, 80, 96, 112, 128]


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
    states = [res['level0']] + [pr['C_state'] for pr in res['pairs']]
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
        row = pen.pen(pot, E, b, TOL)
        verify(pot, E, b, row)
        row.update(meta)
    except Exception as exc:          # recorded, never hidden
        row = dict(status='error', error=repr(exc)[:300])
    row.update(job=dict(kind=kind, pot=potname, e=e, x=x, variant=variant),
               cpu_s=time.process_time() - t0, wall_s=time.perf_counter() - w0)
    return row


def bits_probe(out, rounds=3):
    """CPU per Chin 4A substep (h = 40) vs grid bits, LJ 0.5 De b = 6, same base start, interleaved rounds."""
    pot, E, b = LennardJones(), DE * mm.mpf('0.5'), mm.mpf(6)
    rows = []
    with mm.workdps(ladder2.DPS):
        q0, p0 = ladder2.base_start(pot, E, b)
        for rnd in range(rounds):
            for fp in BITS:
                t0 = time.process_time()
                t = ladder2.FxTrackP(pot, q0, p0, 0, 'chin', fp, fp + 32)
                t.run_to_exit(300_000)
                dt = time.process_time() - t0
                rows.append(dict(round=rnd, fp=fp, fm=fp + 32, substeps=t.substeps, cpu_s=dt,
                                 us_per_substep=1e6 * dt / t.substeps, sweep=mm.nstr(t.sweep, 30)))
                print(rows[-1], flush=True)
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(rows, f, indent=1)


if __name__ == '__main__':
    if sys.argv[1] == '--bits':
        bits_probe(sys.argv[2])
    else:
        run_jobs(one, jobs(), sys.argv[1], workers=int(sys.argv[2]) if len(sys.argv) > 2 else 4, label='S3f ')
