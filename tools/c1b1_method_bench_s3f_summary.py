"""Summarize method bench S3f rows against the pre-run record (C1B1_METHOD_BENCH_PLAN_V0.md "S3f 실행 전 기록").

  V  accepted output (C or base round-back) with true error > tol                           expected 0
  U  pair whose C has true error > its estimate (est_step; est_step + d_round when checked)  expected 0
  C  cap_stop for |rho| >= 1e-10                                                            expected 0
  B  round-back changes the true error by > 1e-13                                           expected 0
  R  accepted with d_round > est_step / 100 (rounding not negligible by design)             expected 0
  P  killer j_out above the S3c worst-case prediction                                       expected 0
  D  repeat rows identical (CPU timings excluded)                                            expected all
  K  substeps vs S3e and vs S3c for the same input                                           reported
  T  bits probe: median CPU per substep by grid bits, ratio to 48 bits                       reported
  python tools/c1b1_method_bench_s3f_summary.py ROWS.jsonl OUT_PREFIX [S3E_ROWS] [S3C_ROWS] [BITS_JSON]
"""
import json
import sys
from collections import Counter, defaultdict

TOL = 1e-9
PRED_J = {1e-2: 1, 1e-4: 1, 1e-6: 2, 1e-7: 3, 1e-8: 3, 1e-9: 4, 1e-10: 5}


def key(r):
    j = r['job']
    return (j['kind'], j['pot'], j['e'], j['x'])


def load(path, variant='main'):
    out = {}
    for line in open(path, encoding='utf-8'):
        r = json.loads(line)
        if r['job']['variant'] == variant and 'substeps' in r:
            out[key(r)] = r['substeps']
    return out


def main():
    a = sys.argv
    rows = [json.loads(line) for line in open(a[1], encoding='utf-8')]
    out = a[2]
    s3e = load(a[3]) if len(a) > 3 else {}
    s3c = load(a[4]) if len(a) > 4 else {}
    V, U, C, B, R, P, lines = [], [], [], [], [], [], []
    K = defaultdict(list)
    dist = defaultdict(Counter)
    for r in rows:
        if r.get('status') not in ('accepted', 'cap_stop'):
            continue
        j = r['job']
        for pr in r['pairs']:
            st = pr['C_state']
            es, et = (pr['est_sweep'], pr['est_time']) if pr.get('checked') else (pr['est_step_sweep'],
                                                                                  pr['est_step_time'])
            if st['err_sweep'] > float(es) or st['err_time'] > float(et):
                U.append((key(r), j['variant'], pr['j'], es, st['err_sweep'], et, st['err_time']))
        if r['status'] == 'accepted':
            o, ob, last = r['out'], r['out_base'], r['pairs'][-1]
            for name, s in (('C', o), ('base', ob)):
                if s['err_sweep'] > TOL or s['err_time'] > TOL:
                    V.append((key(r), j['variant'], name, s['err_sweep'], s['err_time']))
            if abs(ob['err_sweep'] - o['err_sweep']) > 1e-13 or abs(ob['err_time'] - o['err_time']) > 1e-13:
                B.append(key(r))
            if (float(last['d_round_sweep']) > float(last['est_step_sweep']) / 100
                    or float(last['d_round_time']) > float(last['est_step_time']) / 100):
                R.append((key(r), last['d_round_sweep'], last['est_step_sweep'], last['d_round_time'],
                          last['est_step_time']))
        if j['variant'] != 'main':
            continue
        if j['kind'] == 'killer':
            rho = abs(float(j['x']))
            if r['status'] == 'cap_stop' and rho >= 1e-10:
                C.append(key(r))
            if r['status'] == 'accepted':
                dist[j['x']][r['j_out']] += 1
                if r['j_out'] > PRED_J[rho]:
                    P.append((key(r), r['j_out'], PRED_J[rho]))
        for name, ref in (('s3e', s3e), ('s3c', s3c)):
            if key(r) in ref:
                K[name].append(r['substeps'] / ref[key(r)])
        o = r.get('out') or {}
        lines.append('%-8s %-17s %-5s %-7s %-9s j_out=%s bits=%s lvl0 err_s=%-9.2e out err_s=%-9.2e err_t=%-9.2e '
                     'substeps=%-9d wall=%.0fs' % (j['kind'], j['pot'], j['e'], j['x'], r['status'], r['j_out'],
                                                    r.get('bits_out'), r['level0']['err_sweep'],
                                                    o.get('err_sweep', float('nan')), o.get('err_time', float('nan')),
                                                    r['substeps'], r['wall_s']))
    strip = lambda d: {k: v for k, v in d.items() if k not in ('job', 'cpu_s', 'wall_s', 'track_cost')}
    main_rows = {key(r): r for r in rows if r['job']['variant'] == 'main'}
    D = [(key(r), key(r) in main_rows and strip(main_rows[key(r)]) == strip(r))
         for r in rows if r['job']['variant'] == 'repeat']
    Ks = {}
    for name, v in K.items():
        v.sort()
        Ks[name] = dict(n=len(v), min=v[0], median=v[len(v) // 2], max=v[-1])
    T = {}
    if len(a) > 5:
        probe = json.load(open(a[5], encoding='utf-8'))
        by = defaultdict(list)
        for p in probe:
            by[p['fp']].append(p['us_per_substep'])
        med = {fp: sorted(v)[len(v) // 2] for fp, v in by.items()}
        T = {fp: dict(us_per_substep=med[fp], ratio_to_48=med[fp] / med[48], runs=sorted(by[fp])) for fp in sorted(med)}
    summary = dict(status=sorted(((k[0], str(k[1])), v) for k, v in Counter((r['job']['variant'], r.get('status'))
                                                                             for r in rows).items()),
                   V_violations=V, U_underestimates=U, C_cap_stops=C, B_roundback=B, R_rounding_not_small=R,
                   P_above_prediction=P, j_out_by_rho={k: dict(v) for k, v in dist.items()}, D_repeat=D,
                   K_substeps=Ks, T_bits_cost=T,
                   errors=[(key(r), r.get('error')) for r in rows if r.get('status') == 'error'])
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
