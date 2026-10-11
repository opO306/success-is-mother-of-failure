"""Summarize method bench S3e rows against the pre-run record (C1B1_METHOD_BENCH_PLAN_V0.md "S3e 실행 전 기록").

  V  accepted output (C or its base-grid round-back) with true error > tol            expected 0
  U  any rung whose C run has true error > its estimate (sweep or time)                expected 0
  C  cap_stop for |rho| >= 1e-10                                                      expected 0
  B  round-back changes the true sweep/time error by more than 1e-13                  expected 0
  A  first refinement axis of killer inputs not accepted at the base rung = 'grid'    expected all
  P  killer (j_out, g_out) above the worst-case prediction                            reported
  D  repeat rows identical                                                             expected all
  K  substeps relative to S3c for the same input (if S3C_ROWS given)                  reported
  python tools/c1b1_method_bench_s3e_summary.py ROWS.jsonl OUT_PREFIX [S3C_ROWS.jsonl]
"""
import json
import sys
from collections import Counter, defaultdict

TOL = 1e-9
# worst-case models: Chin step error 2.2e-15 (h/40)^4 / |rho| (S3, S3c), FX(48) rounding ~2e-14 / |rho| (S3d),
# each +16 grid bits x ~1.5e-5 (S3d); acceptance needs D_grid + D_step <= 1e-9 (see the record for the traces)
PRED = {1e-2: (1, 1), 1e-4: (1, 1), 1e-6: (2, 2), 1e-7: (3, 2), 1e-8: (3, 2), 1e-9: (4, 2), 1e-10: (5, 3)}


def key(r):
    j = r['job']
    return (j['kind'], j['pot'], j['e'], j['x'])


def main():
    rows = [json.loads(line) for line in open(sys.argv[1], encoding='utf-8')]
    out = sys.argv[2]
    s3c = {}
    if len(sys.argv) > 3:
        for line in open(sys.argv[3], encoding='utf-8'):
            r = json.loads(line)
            if r['job']['variant'] == 'main' and 'substeps' in r:
                s3c[key(r)] = r['substeps']
    status = Counter((r['job']['variant'], r.get('status')) for r in rows)
    V, U, C, B, A, P, K, lines = [], [], [], [], [], [], [], []
    by_rho = defaultdict(Counter)
    for r in rows:
        if r.get('status') not in ('accepted', 'cap_stop'):
            continue
        j = r['job']
        for rg in r['rungs']:
            st = rg['C_state']
            if st['err_sweep'] > float(rg['est_sweep']) or st['err_time'] > float(rg['est_time']):
                U.append((key(r), j['variant'], rg['j'], rg['g'], rg['est_sweep'], st['err_sweep'], rg['est_time'],
                          st['err_time']))
        if r['status'] == 'accepted':
            o, ob = r['out'], r['out_base']
            for name, s in (('C', o), ('base', ob)):
                if s['err_sweep'] > TOL or s['err_time'] > TOL:
                    V.append((key(r), j['variant'], name, s['err_sweep'], s['err_time']))
            dsw, dt = abs(ob['err_sweep'] - o['err_sweep']), abs(ob['err_time'] - o['err_time'])
            if dsw > 1e-13 or dt > 1e-13:
                B.append((key(r), dsw, dt))
        if j['variant'] != 'main':
            continue
        if j['kind'] == 'killer':
            rho = abs(float(j['x']))
            if r['status'] == 'cap_stop' and rho >= 1e-10:
                C.append(key(r))
            if len(r['rungs']) > 1:
                A.append((key(r), 'grid' if r['rungs'][1]['g'] == 1 else 'step'))
            if r['status'] == 'accepted':
                pj, pg = PRED[rho]
                by_rho[j['x']][(r['j_out'], r['g_out'])] += 1
                if r['j_out'] > pj or r['g_out'] > pg:
                    P.append((key(r), (r['j_out'], r['g_out']), (pj, pg)))
        if key(r) in s3c:
            K.append((key(r), r['substeps'] / s3c[key(r)]))
        o = r.get('out') or {}
        lines.append('%-8s %-17s %-5s %-7s %-9s (j,g)=(%s,%s) rungs=%d lvl0 err_s=%-9.2e out err_s=%-9.2e err_t=%-9.2e '
                     'base err_s=%-9.2e substeps=%-9d wall=%.0fs' % (
                         j['kind'], j['pot'], j['e'], j['x'], r['status'], r['j_out'], r['g_out'], len(r['rungs']),
                         r['level0']['err_sweep'], o.get('err_sweep', float('nan')), o.get('err_time', float('nan')),
                         (r.get('out_base') or {}).get('err_sweep', float('nan')), r['substeps'], r['wall_s']))
    main_rows = {key(r): r for r in rows if r['job']['variant'] == 'main'}
    strip = lambda d: {k: v for k, v in d.items() if k not in ('job', 'cpu_s', 'wall_s')}
    D = [(key(r), key(r) in main_rows and strip(main_rows[key(r)]) == strip(r))
         for r in rows if r['job']['variant'] == 'repeat']
    ks = sorted(x for _, x in K)
    summary = dict(status=sorted(((k[0], str(k[1])), v) for k, v in status.items()),
                   V_violations=V, U_underestimates=U, C_cap_stops=C, B_roundback=B,
                   A_first_axis=Counter(a for _, a in A), P_above_prediction=P,
                   by_rho={k: {str(kk): vv for kk, vv in v.items()} for k, v in by_rho.items()},
                   K_substeps_vs_s3c=dict(n=len(ks), min=ks[0] if ks else None, median=ks[len(ks) // 2] if ks else None,
                                          max=ks[-1] if ks else None),
                   D_repeat=D, errors=[(key(r), r.get('error')) for r in rows if r.get('status') == 'error'])
    with open(out + '.json', 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=1, default=str)
    with open(out + '.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(sorted(lines)) + '\n')
        for k, v in summary.items():
            f.write(f'\n{k}: {len(v) if hasattr(v, "__len__") else v}\n')
            for item in (v.items() if isinstance(v, dict) else v):
                f.write(f'  {item}\n')
    print(open(out + '.txt', encoding='utf-8').read()[-8000:])


if __name__ == '__main__':
    main()
