"""Method bench S1 study (survey_only): M0-M3 on T1-T3 closed-form problems.

Grid sealed in docs/active/C1B1_METHOD_BENCH_PLAN_V0.md (S1 pre-run record). Rows are appended to a JSONL file
as they finish (partial results survive an interruption). Run on the laptop:
  python tools/c1b1_method_bench_s1.py OUT.jsonl [WORKERS]
"""
import json
import sys
import time
from multiprocessing import Pool

from c1b1_method_bench.potentials import DE, Coulomb, Free, InvSquare
from c1b1_method_bench.run import run

ENERGIES = ['0.5', '2', '10', '40']          # De
IMPACTS = [0, 3, 6, 10]                      # bohr
STEPS = dict(kdk=[80, 40, 20, 10], yoshida4=[160, 80, 40], chin4a=[160, 80, 40])
POTS = dict(T1_free=Free, T2_inv_square=InvSquare, T3_coulomb=Coulomb)
MAX_STEPS = 300_000


def jobs():
    out = [('T1_free', m, '2', 6, h) for m, hs in STEPS.items() for h in hs[:1]]
    for pot in ('T2_inv_square', 'T3_coulomb'):
        for e in ENERGIES:
            for b in IMPACTS:
                for m, hs in STEPS.items():
                    out += [(pot, m, e, b, h) for h in hs]
    return out


def one(job):
    pot, m, e, b, h = job
    t0 = time.process_time()
    try:
        row = run(POTS[pot](), m, DE * __import__('mpmath').mpf(e), b, h, max_steps=MAX_STEPS)
    except Exception as exc:          # recorded, never hidden
        row = dict(status='error', error=repr(exc))
    row.update(job=dict(pot=pot, method=m, e=e, b=b, h=h), cpu_s=time.process_time() - t0)
    return row


def main():
    out, workers = sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 4
    js = jobs()
    t0 = time.perf_counter()
    print(f'{len(js)} runs, {workers} workers', flush=True)
    with Pool(workers) as pool, open(out, 'a', encoding='utf-8') as f:
        for i, row in enumerate(pool.imap_unordered(one, js)):
            f.write(json.dumps(row) + '\n'); f.flush()
            if i % 20 == 0:
                print(f'{i + 1}/{len(js)} {time.perf_counter() - t0:.0f}s', flush=True)
    print(f'done {time.perf_counter() - t0:.0f}s', flush=True)


if __name__ == '__main__':
    main()
