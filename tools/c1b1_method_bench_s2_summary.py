"""Summarize method bench S2 rows (survey_only).
  python tools/c1b1_method_bench_s2_summary.py ROWS.jsonl OUT.json
"""
import json
import math
import sys
from collections import defaultdict


def main():
    rows = [json.loads(x) for x in open(sys.argv[1], encoding='utf-8')]
    bad = [r for r in rows if r.get('status') != 'ok']
    print('rows', len(rows), 'not_ok', len(bad))
    for r in bad:
        print('NOT_OK', r.get('job'), r.get('status'), (r.get('error') or '')[:150])
    ok = [r for r in rows if r.get('status') == 'ok']
    t4 = defaultdict(dict)
    for r in ok:
        j = r['job']
        if j['pot'] == 'T4_exp_wall' and j['kind'] in ('fixed', 'adaptive'):
            key = f"{j['method']}_{j['x']}"
            t4[(float(j['e']), j['b'])][key] = (r['err_sweep'], r['err_chi'], r['n_force'] + r['n_grad'], r['steps'])
    orders = defaultdict(list)
    for (e, b), d in t4.items():
        for m, hs in (('kdk', [80, 40, 20, 10]), ('yoshida4', [160, 80, 40]), ('chin4a', [160, 80, 40])):
            es = [d.get(f'{m}_{h}', (None,))[0] for h in hs]
            for a, c in zip(es, es[1:]):
                if a and c:
                    orders[m].append(math.log2(a / c))
    for m, o in orders.items():
        print(f'T4 {m} observed order {min(o):.2f}..{max(o):.2f} (n={len(o)})')
    print('T4 E b | kdk40 | kdk10 | chin40 | yosh40 | adapt 1e-7 | adapt 1e-9 | adapt 1e-11   (sweep err / V-calls)')
    for (e, b), d in sorted(t4.items()):
        if b == 0:
            continue
        cells = []
        for k in ('kdk_40', 'kdk_10', 'chin4a_40', 'yoshida4_40', 'adaptive_1e-7', 'adaptive_1e-9', 'adaptive_1e-11'):
            v = d.get(k)
            cells.append(f'{v[0]:.1e}/{v[2]}' if v else '-')
        print(f'{e:g} {b} | ' + ' | '.join(cells))
    pred = []
    for r in ok:
        j = r['job']
        if j['kind'] == 'predict' and r.get('pred_d_sweep'):
            pred.append(dict(pot=j['pot'], e=j['e'], b=j['b'], h=j['x'], measured=r['d_sweep'],
                             predicted=r['pred_d_sweep'], ratio=r['d_sweep'] / r['pred_d_sweep']))
    for h in (40, 20):
        rs = [p['ratio'] for p in pred if p['h'] == h]
        if rs:
            print(f'M7 h={h}: measured/predicted ratio {min(rs):.4f}..{max(rs):.4f} (n={len(rs)})')
    worst = sorted(pred, key=lambda p: -abs(p['ratio'] - 1))[:6]
    for p in worst:
        print('M7 worst', p['pot'], p['e'], p['b'], p['h'], f"{p['ratio']:.4f}", f"{p['measured']:.2e}")
    json.dump(dict(format='c1b1-method-bench-s2-summary-v0', n_rows=len(rows), n_not_ok=len(bad),
                   not_ok=[dict(job=r.get('job'), status=r.get('status'), error=r.get('error')) for r in bad],
                   t4={f'{e}_{b}': d for (e, b), d in t4.items()}, orders=orders, predictor=pred),
              open(sys.argv[2], 'w', encoding='utf-8'), indent=1)


if __name__ == '__main__':
    main()
