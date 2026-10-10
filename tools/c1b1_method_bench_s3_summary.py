"""Summarize method bench S3 rows (survey_only).  python tools/c1b1_method_bench_s3_summary.py ROWS.jsonl OUT.json"""
import json
import math
import sys
from collections import defaultdict


def main():
    rows = [json.loads(x) for x in open(sys.argv[1], encoding='utf-8')]
    bad = [r for r in rows if r.get('status') != 'ok']
    print('rows', len(rows), 'not_ok', len(bad))
    for r in bad:
        print('NOT_OK', r.get('job'), r.get('status'), (r.get('error') or '')[:160])
    ok = [r for r in rows if r.get('status') == 'ok']
    orders = defaultdict(list)
    fixed = defaultdict(dict)
    for r in ok:
        j = r['job']
        if j['kind'] == 'fixed':
            fixed[(j['pot'], j['e'], j['b'], j['method'])][j['x']] = r['err_sweep']
    for (pot, e, b, m), d in fixed.items():
        hs = sorted(d, reverse=True)
        for a, c in zip(hs, hs[1:]):
            if d[a] > 0 and d[c] > 0:
                orders[(pot, m)].append(math.log2(d[a] / d[c]))
    for k, o in sorted(orders.items()):
        print('ordinary', k, f'order {min(o):.2f}..{max(o):.2f} n={len(o)}')
    killer = defaultdict(dict)
    for r in ok:
        j = r['job']
        if j['kind'] in ('killer', 'direct'):
            key = (j['pot'], j['e'], float(j['b']))
            name = f"{j['method']}_{j['x']}" if j['kind'] == 'killer' else j['method']
            killer[key][name] = r
    print('pot frac rho | kdk40 | kdk20 | rich | M7 ratio40 | chin40 | yosh40 | adapt1e-9 | quad30 | cont30 (sweep error rad)')
    table = []
    for (pot, f, rho), d in sorted(killer.items(), key=lambda kv: (kv[0][0], kv[0][1], -abs(kv[0][2]), kv[0][2])):
        g = lambda n: d.get(n, {}).get('err_sweep')
        k40, k20 = d.get('kdk_40', {}), d.get('kdk_20', {})
        rich = None
        if 'd_sweep' in k40 and 'd_sweep' in k20:
            rich = abs((4 * k20['d_sweep'] - k40['d_sweep']) / 3)
        m7 = (k40['d_sweep'] / k40['pred_d_sweep']) if k40.get('pred_d_sweep') else None
        cells = [g('kdk_40'), g('kdk_20'), rich, m7, g('chin4a_40'), g('yoshida4_40'), g('adaptive_1e-9'),
                 g('quadref30'), g('continuous30')]
        table.append(dict(pot=pot, frac=f, rho=rho, kdk40=cells[0], kdk20=cells[1], richardson=rich, m7_ratio40=m7,
                          chin40=cells[4], yosh40=cells[5], adaptive=cells[6], quadref30=cells[7], continuous30=cells[8],
                          m7_error=k40.get('pred_error'), steps40=k40.get('steps'),
                          direct_s=[d.get(n, {}).get('direct_wall_s') for n in ('quadref30', 'continuous30')],
                          kdk40_wall_s=k40.get('wall_s')))
        fmt = lambda v: '-' if v is None else (f'{v:.4f}' if v is cells[3] else f'{v:.1e}')
        print(pot[:6], f, f'{rho:+.0e}', '|', ' | '.join(fmt(v) for v in cells))
    json.dump(dict(format='c1b1-method-bench-s3-summary-v0', n_rows=len(rows), n_not_ok=len(bad),
                   not_ok=[dict(job=r.get('job'), error=r.get('error')) for r in bad],
                   orders={f'{k[0]}|{k[1]}': v for k, v in orders.items()}, killer=table),
              open(sys.argv[2], 'w', encoding='utf-8'), indent=1)


if __name__ == '__main__':
    main()
