"""Method bench S3 study (survey_only): orbiting potentials T5 Morse and T6 Lennard-Jones.

  A 'fixed'  ordinary grid (E 0.5/2/10/45 De, b 0/3/6/9): KDK, Yoshida4, Chin 4A.
  B 'killer' near-orbiting set: E = 0.3/0.6/0.9 E_max, b = b_orb (1 + rho), rho = +-1e-2 ... +-1e-6:
             KDK 40/20 (+ M7 modified-Hamiltonian prediction), Chin 40, Yoshida 40, adaptive KDK tol 1e-9.
  C 'direct' M5 direct quadrature on the killer inputs: (a) quadref at 30 digits, (b) the independent
             c1b1_o1.continuous.scatter at 30 digits, both against quadref at 80 digits; wall time recorded.
M6 Richardson is computed in the summary from the KDK 40/20 signed errors. Rows are appended to JSONL.
  python tools/c1b1_method_bench_s3.py OUT.jsonl [WORKERS]
"""
import functools
import json
import sys
import time
from multiprocessing import Pool

import mpmath as mm

from c1b1_method_bench import orbit, quadref
from c1b1_method_bench.methods import adaptive_kdk
from c1b1_method_bench.potentials import DE, MU, LennardJones, Morse
from c1b1_method_bench.run import initial, run

POTS = dict(T5_morse=Morse, T6_lennard_jones=LennardJones)
ORD_E = ['0.5', '2', '10', '45']
ORD_B = [0, 3, 6, 9]
FIXED = dict(kdk=[80, 40, 20, 10], yoshida4=[160, 80, 40], chin4a=[160, 80, 40])
FRACS = ['0.3', '0.6', '0.9']
RHOS = [s * mm.mpf(10) ** -k for k in (2, 3, 4, 5, 6) for s in (1, -1)]
KILLER = [('kdk', 40), ('kdk', 20), ('chin4a', 40), ('yoshida4', 40), ('adaptive', '1e-9')]
MAX_STEPS = 600_000


def killer_input(pot, frac, rho):
    with mm.workdps(60):
        E = orbit.e_max(pot) * mm.mpf(frac)
        o = orbit.orbit(pot, MU, E)
        return E, o['b_orb'] * (1 + rho), o


def jobs():
    out = []
    for pot in POTS:
        for e in ORD_E:
            for b in ORD_B:
                out += [('fixed', pot, m, e, b, h) for m, hs in FIXED.items() for h in hs]
        for f in FRACS:
            for rho in RHOS:
                r = mm.nstr(rho, 3)
                out += [('killer', pot, m, f, r, x) for m, x in KILLER]
                out += [('direct', pot, d, f, r, 30) for d in ('quadref30', 'continuous30')]
    return out


def one(job):
    kind, potname, m, e, b, x = job
    t0, w0 = time.process_time(), time.perf_counter()
    pot = POTS[potname]()
    row = dict()
    try:
        if kind == 'fixed':
            row = run(pot, m, DE * mm.mpf(e), b, x, max_steps=MAX_STEPS)
        else:
            E, bb, o = killer_input(pot, e, mm.mpf(b))
            row_meta = dict(E_over_De=float(E / DE), b_orb=mm.nstr(o['b_orb'], 30), r_star=mm.nstr(o['r_star'], 20))
            if kind == 'killer':
                if m == 'adaptive':
                    step = functools.partial(adaptive_kdk, tol=mm.mpf(x), h_min=mm.mpf(40) / 1024)
                    row = run(pot, 'adaptive', E, bb, 40, step=step, max_steps=MAX_STEPS)
                else:
                    row = run(pot, m, E, bb, x, max_steps=MAX_STEPS)
                if m == 'kdk' and row.get('status') == 'ok':
                    try:
                        mod = quadref.kdk_modified(pot, MU, row['q0'], row['p0'], x, row['r_exit'])
                        L = bb * mm.sqrt(2 * MU * E)
                        true = quadref.reference(pot, MU, E, L, row['r_exit'])
                        with mm.workdps(quadref.DPS):
                            row['pred_d_sweep'] = float(mod['sweep'] - true['sweep'])
                    except Exception as exc:
                        row['pred_error'] = repr(exc)[:200]
            else:
                with mm.workdps(80):
                    q, p, L = initial(pot, MU, E, bb)
                    ref = quadref.reference(pot, MU, E, L, mm.mpf(20))
                w1 = time.perf_counter()
                if m == 'quadref30':
                    old = quadref.DPS
                    try:
                        quadref.DPS = 30
                        got = quadref.reference(pot, MU, E, L, mm.mpf(20))
                    finally:
                        quadref.DPS = old
                    sweep = got['sweep']
                else:
                    from c1b1_o1 import continuous
                    with mm.workdps(30):
                        got = continuous.scatter(pot.V, MU, q, p, mm.mpf(20), 30)
                    sweep = mm.mpf(got['sweep'])
                with mm.workdps(80):
                    row = dict(status='ok', err_sweep=float(abs(sweep - ref['sweep'])),
                               direct_wall_s=time.perf_counter() - w1)
            row.update(row_meta)
    except Exception as exc:          # recorded, never hidden
        row = dict(status='error', error=repr(exc)[:300])
    row.update(job=dict(kind=kind, pot=potname, method=m, e=e, b=b, x=x),
               cpu_s=time.process_time() - t0, wall_s=time.perf_counter() - w0)
    return row


def main():
    out, workers = sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 4
    js = jobs()
    t0 = time.perf_counter()
    print(f'{len(js)} jobs, {workers} workers', flush=True)
    with Pool(workers) as pool, open(out, 'a', encoding='utf-8') as f:
        for i, row in enumerate(pool.imap_unordered(one, js)):
            f.write(json.dumps(row) + '\n'); f.flush()
            if i % 20 == 0:
                print(f'{i + 1}/{len(js)} {time.perf_counter() - t0:.0f}s', flush=True)
    print(f'done {time.perf_counter() - t0:.0f}s', flush=True)


if __name__ == '__main__':
    main()
