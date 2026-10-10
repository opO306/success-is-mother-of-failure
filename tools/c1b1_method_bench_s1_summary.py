"""Summarize method bench S1 rows: observed orders and error per force evaluation (survey_only).

  python tools/c1b1_method_bench_s1_summary.py ROWS.jsonl OUT.json
"""
import json
import math
import sys
from collections import defaultdict

FORCE_PER_STEP = dict(kdk=1, yoshida4=3, chin4a=3)      # with endpoint force reuse; chin adds 1 gradient term
GRAD_PER_STEP = dict(kdk=0, yoshida4=0, chin4a=1)


def main():
    rows = [json.loads(x) for x in open(sys.argv[1], encoding='utf-8')]
    bad = [r for r in rows if r.get('status') != 'ok']
    groups = defaultdict(list)
    for r in rows:
        if r.get('status') == 'ok':
            j = r['job']
            groups[(j['pot'], j['method'], j['e'], j['b'])].append(r)
    cases = []
    for (pot, m, e, b), rs in sorted(groups.items()):
        rs.sort(key=lambda r: -r['h'])
        orders = [math.log2(a['err_sweep'] / c['err_sweep']) if a['err_sweep'] > 0 and c['err_sweep'] > 0 else None
                  for a, c in zip(rs, rs[1:])]
        cases.append(dict(pot=pot, method=m, e=e, b=b,
                          h=[r['h'] for r in rs], err_sweep=[r['err_sweep'] for r in rs], err_chi=[r['err_chi'] for r in rs],
                          err_time=[r['err_time'] for r in rs], max_dH_over_E=[r['max_dH_over_E'] for r in rs],
                          forces=[r['steps'] * FORCE_PER_STEP[m] for r in rs], gradients=[r['steps'] * GRAD_PER_STEP[m] for r in rs],
                          observed_order=orders))
    # equal-work comparison at the outer step 40: KDK h=10 (4 forces per 40) vs Yoshida/Chin h=40
    duel = []
    for pot in ('T2_inv_square', 'T3_coulomb'):
        for c in cases:
            if c['pot'] != pot or c['method'] != 'kdk':
                continue
            row = dict(pot=pot, e=c['e'], b=c['b'])
            for m, h in (('kdk', 40), ('kdk', 10), ('yoshida4', 40), ('chin4a', 40)):
                g = next((x for x in cases if x['pot'] == pot and x['method'] == m and x['e'] == c['e'] and x['b'] == c['b']), None)
                if g and h in g['h']:
                    i = g['h'].index(h)
                    row[f'{m}_h{h}'] = dict(err_sweep=g['err_sweep'][i], err_chi=g['err_chi'][i], forces=g['forces'][i])
            duel.append(row)
    out = dict(format='c1b1-method-bench-s1-summary-v0', n_rows=len(rows), n_not_ok=len(bad),
               not_ok=[dict(job=r.get('job'), status=r.get('status'), error=r.get('error')) for r in bad],
               cases=cases, equal_outer40=duel)
    json.dump(out, open(sys.argv[2], 'w', encoding='utf-8'), indent=1)
    print('rows', len(rows), 'not_ok', len(bad))
    for r in bad:
        print('NOT_OK', r.get('job'), r.get('status'), (r.get('error') or '')[:120])
    def rng(xs):
        xs = [x for x in xs if x is not None]
        return f'{min(xs):.2f}..{max(xs):.2f}' if xs else '-'
    for m in ('kdk', 'yoshida4', 'chin4a'):
        allo = [o for c in cases if c['method'] == m and c['pot'] != 'T1_free' for o in c['observed_order']]
        print(m, 'observed order range', rng(allo), 'n', len(allo))
    print('pot e b | kdk40 | kdk10 | yosh40 | chin40  (sweep error rad; forces)')
    for d in duel:
        cells = []
        for k in ('kdk_h40', 'kdk_h10', 'yoshida4_h40', 'chin4a_h40'):
            v = d.get(k)
            cells.append(f"{v['err_sweep']:.1e}/{v['forces']}" if v else '-')
        print(d['pot'][:6], d['e'], d['b'], ' | '.join(cells))


if __name__ == '__main__':
    main()
