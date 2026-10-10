"""Method bench S2 study (survey_only): T4 steep exponential wall up to 45 De (high-energy pre-study),
M4 adaptive KDK and M7 modified-Hamiltonian error predictor. Grid recorded in C1B1_METHOD_BENCH_PLAN_V0.md
before running. Rows are appended to JSONL as they finish.
  python tools/c1b1_method_bench_s2.py OUT.jsonl [WORKERS]
"""
import functools
import json
import sys
import time
from multiprocessing import Pool

import mpmath as mm

from c1b1_method_bench import quadref
from c1b1_method_bench.methods import adaptive_kdk
from c1b1_method_bench.potentials import DE, MU, Coulomb, ExpWall, InvSquare
from c1b1_method_bench.run import run

POTS = dict(T2_inv_square=InvSquare, T3_coulomb=Coulomb, T4_exp_wall=ExpWall)
T4_E = ['0.5', '2', '10', '20', '33', '45']
T4_B = [0, 2, 4, 6]
FIXED = dict(kdk=[80, 40, 20, 10], yoshida4=[160, 80, 40], chin4a=[160, 80, 40])
TOLS = ['1e-7', '1e-9', '1e-11']
H_MIN = mm.mpf(40) / 1024
PRED = dict(T2_inv_square=(['0.5', '2', '10', '40'], [3, 6]), T3_coulomb=(['0.5', '2', '10', '40'], [3, 6]),
            T4_exp_wall=(T4_E, [2, 4]))
MAX_STEPS = 400_000


def jobs():
    out = []
    for e in T4_E:
        for b in T4_B:
            out += [('fixed', 'T4_exp_wall', m, e, b, h) for m, hs in FIXED.items() for h in hs]
            out += [('adaptive', 'T4_exp_wall', 'adaptive', e, b, t) for t in TOLS]
    for pot, (es, bs) in PRED.items():
        out += [('predict', pot, 'kdk', e, b, h) for e in es for b in bs for h in (40, 20)]
    return out


def one(job):
    kind, pot, m, e, b, x = job
    t0 = time.process_time()
    try:
        E = DE * mm.mpf(e)
        if kind == 'adaptive':
            step = functools.partial(adaptive_kdk, tol=mm.mpf(x), h_min=H_MIN)
            row = run(POTS[pot](), 'adaptive', E, b, 40, step=step, max_steps=MAX_STEPS)
        else:
            row = run(POTS[pot](), m, E, b, x, max_steps=MAX_STEPS)
        if kind == 'predict' and row.get('status') == 'ok':
            P = POTS[pot]()
            mod = quadref.kdk_modified(P, MU, row['q0'], row['p0'], x, row['r_exit'])
            L = mm.mpf(b) * mm.sqrt(2 * MU * E)
            true = quadref.reference(P, MU, E, L, row['r_exit'])
            with mm.workdps(quadref.DPS):
                row['pred_d_sweep'] = float(mod['sweep'] - true['sweep'])
                row['pred_d_time'] = float(mod['time'] - true['time'])
    except Exception as exc:          # recorded, never hidden
        row = dict(status='error', error=repr(exc))
    row.update(job=dict(kind=kind, pot=pot, method=m, e=e, b=b, x=x), cpu_s=time.process_time() - t0)
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
