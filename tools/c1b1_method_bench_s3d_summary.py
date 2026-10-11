"""Summarize method bench S3d rows against the pre-run record (C1B1_METHOD_BENCH_PLAN_V0.md "S3d 실행 전 기록").

  P1  slope of log d_sweep vs log |rho| (kdk_fx, |rho| <= 1e-4) per series           predicted in [-1.3, -0.7]
  P2  first |rho| (decreasing) where kdk_fx d_sweep > 1e-9, per series                predicted in [1e-7, 1e-4]
  P3  grid: d(64)/d(48) in [1.5e-6, 1.5e-4]; d(80)/d(48) <= 1e-8; d(fm 112)/d(fm 80) in [0.3, 3]
  P4  chin levels: d(j=3)/d(j=0) >= 0.5
  P5  m8_fx: accepted outputs with true error > 1e-9 = 0; rho = -1e-8 cap_stop; rho = -1e-4 accepted
  P6  ordinary: d_sweep <= 1e-12
  P7  repeat rows identical to their originals
  python tools/c1b1_method_bench_s3d_summary.py ROWS.jsonl OUT_PREFIX
"""
import json
import math
import sys
from collections import defaultdict

TOL = 1e-9


def slope(pts):
    xs = [math.log10(abs(a)) for a, _ in pts]
    ys = [math.log10(b) for _, b in pts]
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)


def main():
    rows = [json.loads(line) for line in open(sys.argv[1], encoding='utf-8')]
    out = sys.argv[2]
    ok = [r for r in rows if r.get('status') in ('ok', 'accepted', 'cap_stop')]
    errors = [(r['job'], r.get('error')) for r in rows if r.get('status') == 'error']
    J = lambda r: r['job']
    series = defaultdict(list)
    for r in ok:
        j = J(r)
        if j['kind'] == 'kdk_fx':
            rho = float(j['x'])
            series[(j['pot'], j['e'], 'in' if rho < 0 else 'out')].append((rho, r['d_sweep'], r))
    P1, P2, table = [], [], []
    for k, pts in sorted(series.items()):
        pts.sort(key=lambda t: -abs(t[0]))
        near = [(a, b) for a, b, _ in pts if abs(a) <= 1e-4 and b > 0]
        s = slope(near) if len(near) >= 2 else None
        P1.append((k, s, s is not None and -1.3 <= s <= -0.7))
        first = next((abs(a) for a, b, _ in pts if b > TOL), None)
        P2.append((k, first, first is not None and 1e-7 <= first <= 1e-4))
        for a, b, r in pts:
            table.append('%-17s %-4s %-8s d_sweep=%-9.2e d_lag=%-9.2e FX err_s=%-9.2e err_t=%-9.2e HP err_s=%-9.2e '
                         'ticks=%d' % (k[0], k[1], j_x(r), b, r['d_lag'], r['fx']['err_sweep'], r['fx']['err_time'],
                                       r['hp']['err_sweep'], r['tick']))
    base = {(J(r)['pot'], J(r)['e'], J(r)['x']): r['d_sweep'] for r in ok if J(r)['kind'] == 'kdk_fx'}
    P3 = []
    for r in ok:
        j = J(r)
        if j['kind'] != 'grid':
            continue
        d0 = base.get((j['pot'], j['e'], j['x']))
        ratio = r['d_sweep'] / d0 if d0 else None
        if j['fm'] != 80:
            band = (0.3, 3)
        elif j['fp'] == 64:
            band = (1.5e-6, 1.5e-4)
        else:
            band = (0, 1e-8)
        P3.append((j['pot'], j['e'], j['x'], j['fp'], j['fm'], r['d_sweep'], ratio,
                   ratio is not None and band[0] <= ratio <= band[1]))
    lv = defaultdict(dict)
    for r in ok:
        j = J(r)
        if j['kind'] == 'chin_lv':
            lv[(j['pot'], j['e'], j['x'])][j['j']] = (r['d_sweep'], r['fx']['err_sweep'], r['hp']['err_sweep'])
    P4 = [(k, v, (v[3][0] / v[0][0] >= 0.5) if 0 in v and 3 in v and v[0][0] > 0 else None) for k, v in sorted(lv.items())]
    P5, V = [], []
    for r in ok:
        j = J(r)
        if j['kind'] not in ('m8_fx',) and not (j['kind'] == 'repeat' and 'pairs' in r):
            continue
        if r['status'] == 'accepted' and (r['out']['err_sweep'] > TOL or r['out']['err_time'] > TOL):
            V.append((j, r['out']['err_sweep'], r['out']['err_time']))
        expect = {'-1e-8': 'cap_stop', '-1e-4': 'accepted'}.get(j['x'])
        P5.append((j['kind'], j['pot'], j['e'], j['x'], r['status'], r['j_out'],
                   [(p['fine'], p['est_sweep'], '%.2e' % p['fine_state']['err_sweep']) for p in r['pairs']],
                   expect is None or expect == r['status']))
    P6 = [(J(r)['pot'], J(r)['e'], J(r)['x'], r['d_sweep'], r['d_sweep'] <= 1e-12) for r in ok if J(r)['kind'] == 'ordinary']
    orig = {(J(r)['kind'], J(r)['pot'], J(r)['e'], J(r)['x']): r for r in ok if J(r)['kind'] in ('kdk_fx', 'm8_fx')}
    P7 = []
    for r in ok:
        if J(r)['kind'] != 'repeat':
            continue
        kind = 'm8_fx' if 'pairs' in r else 'kdk_fx'
        o = orig.get((kind, J(r)['pot'], J(r)['e'], J(r)['x']))
        strip = lambda d: {k: v for k, v in d.items() if k not in ('job', 'cpu_s', 'wall_s')}
        P7.append((kind, J(r)['pot'], J(r)['x'], o is not None and strip(o) == strip(r)))
    summary = dict(P1_slope=P1, P2_first_above_tol=P2, P3_grid=P3, P4_chin_levels=P4, P5_m8_fx=P5,
                   V_m8_violations=V, P6_ordinary=P6, P7_repeat=P7, errors=errors,
                   counts=dict(rows=len(rows), ok=len(ok), error=len(errors)))
    with open(out + '.json', 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=1, default=str)
    with open(out + '.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(table) + '\n')
        for k in ('counts', 'P1_slope', 'P2_first_above_tol', 'P3_grid', 'P4_chin_levels', 'P5_m8_fx',
                  'V_m8_violations', 'P6_ordinary', 'P7_repeat', 'errors'):
            v = summary[k]
            f.write(f'\n{k}: {len(v)}\n')
            for item in (v.items() if isinstance(v, dict) else v):
                f.write(f'  {item}\n')
    print(open(out + '.txt', encoding='utf-8').read()[-8000:])


def j_x(r):
    return r['job']['x']


if __name__ == '__main__':
    main()
