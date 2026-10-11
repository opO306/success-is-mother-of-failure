"""Summarize method bench S3c rows (tools/c1b1_method_bench_s3c.py) against the pre-run record.

Checks (sealed before the run, C1B1_METHOD_BENCH_PLAN_V0.md "S3c 실행 전 기록"):
  V  accepted output with true error > tol (sweep or relative time)        expected 0
  U  compared pair whose finer run has true error > its estimate              expected 0
  C  cap_stop for |rho| >= 1e-10                                            expected 0
  P  killer j_out above the worst-case prediction pred_j(|rho|)              reported
  D  repeat rows identical to main rows; dps50 vs dps40 sweep difference      reported
  X  continuous.scatter vs quadref on rho = +1e-8..+1e-10                     reported
  python tools/c1b1_method_bench_s3c_summary.py ROWS.jsonl OUT_PREFIX
"""
import json
import sys
from collections import Counter

TOL = 1e-9
# worst-case Chin 4A model from S3 (Morse 0.9 E_max, rho = -1e-6, h = 40: 2.2e-9): err(h) = 2.2e-15 (h/40)^4 / |rho|;
# a pair (h, h/2) is accepted when err(h) * 15/16 <= 1e-9, i.e. err(h) <= 1.067e-9.
PRED_EDGES = [(2.06e-6, 1), (1.29e-7, 2), (8.06e-9, 3), (5.0e-10, 4), (3.1e-11, 5)]


def pred_j(rho):
    for edge, j in PRED_EDGES:
        if abs(rho) >= edge:
            return j
    return 6


def key(r):
    j = r['job']
    return (j['kind'], j['pot'], j['e'], j['x'])


def main():
    rows = [json.loads(line) for line in open(sys.argv[1], encoding='utf-8')]
    out = sys.argv[2]
    main_rows = {key(r): r for r in rows if r['job']['variant'] == 'main'}
    status = Counter((r['job']['variant'], r.get('status')) for r in rows)
    V, U, C, P, lines = [], [], [], [], []
    for r in rows:
        if r['job']['variant'] not in ('main', 'repeat', 'dps50') or r.get('status') not in ('accepted', 'cap_stop'):
            continue
        j = r['job']
        for pr in r['pairs']:
            st = pr['fine_state']
            if st['err_sweep'] > float(pr['est_sweep']) or st['err_time'] > float(pr['est_time']):
                U.append((key(r), pr['coarse'], pr['fine'], pr['est_sweep'], st['err_sweep'], pr['est_time'],
                          st['err_time']))
        if r['status'] == 'accepted':
            o = r['out']
            if o['err_sweep'] > TOL or o['err_time'] > TOL:
                V.append((key(r), o['err_sweep'], o['err_time']))
        if j['kind'] == 'killer':
            rho = float(j['x'])
            if r['status'] == 'cap_stop' and abs(rho) >= 1e-10:
                C.append(key(r))
            if r['status'] == 'accepted' and r['j_out'] > pred_j(rho):
                P.append((key(r), r['j_out'], pred_j(rho)))
        if j['variant'] == 'main':
            o = r.get('out') or {}
            lines.append('%-8s %-17s %-5s %-7s %-10s j_out=%-4s lvl0 err_s=%-9.2e est0=%-9s out err_s=%-9.2e '
                         'err_t=%-9.2e substeps=%-9d wall=%.0fs' % (
                             j['kind'], j['pot'], j['e'], j['x'], r['status'], r['j_out'],
                             r['level0']['err_sweep'], r['pairs'][0]['est_sweep'], o.get('err_sweep', float('nan')),
                             o.get('err_time', float('nan')), r['substeps'], r['wall_s']))
    D = []
    for r in rows:
        v = r['job']['variant']
        if v not in ('repeat', 'dps50'):
            continue
        m = main_rows.get(key(r))
        if m is None or 'out' not in m or 'out' not in r:
            D.append((v, key(r), 'missing'))
            continue
        if v == 'repeat':
            same = (m['out'] == r['out'] and m['pairs'] == r['pairs'])
            D.append((v, key(r), 'identical' if same else 'DIFFERENT'))
        else:
            from mpmath import mp, mpf
            mp.dps = 60
            D.append((v, key(r), m['j_out'] == r['j_out'],
                      float(abs(mpf(m['out']['sweep']) - mpf(r['out']['sweep'])))))
    X = [(key(r), r.get('cont'), r.get('diff_sweep'), r.get('cont_r_min', '')[:12], r.get('ref_r_turn', '')[:12],
          r.get('cont_error', '')) for r in rows if r['job']['variant'] == 'cross']
    summary = dict(status=sorted(((k[0], str(k[1])), v) for k, v in status.items()),
                   V_violations=V, U_underestimates=U, C_cap_stops=C, P_above_prediction=P, D_checks=D, X_cross=X,
                   errors=[(key(r), r['job']['variant'], r.get('error')) for r in rows if r.get('status') == 'error'])
    with open(out + '.json', 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=1)
    with open(out + '.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(sorted(lines)) + '\n')
        for k in ('status', 'V_violations', 'U_underestimates', 'C_cap_stops', 'P_above_prediction', 'D_checks',
                  'X_cross', 'errors'):
            f.write(f'\n{k}: {len(summary[k])}\n')
            for item in summary[k]:
                f.write(f'  {item}\n')
    print(open(out + '.txt', encoding='utf-8').read()[-6000:])


if __name__ == '__main__':
    main()
