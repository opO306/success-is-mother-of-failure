"""Summarize S3b rows (survey_only).  python tools/c1b1_method_bench_s3b_summary.py ROWS.jsonl OUT.json

Per (potential, E): Q2_fin (K15), dQ2(h) = Q2_fin(modified h) - Q2_fin(true) with K15 and G7, the panel error
estimate sum |K15 - G7|, dQ2(40)/dQ2(20), contributions per unit of s = -ln|rho| near the orbit, the 'per-collision
accounting' 2 pi int |d sweep| b db (what adding worst-case collision errors would give), the excluded-window bound
4 pi b_orb^2 rho_min, and the M7-shortcut bound eps * 2 pi int |d sweep| b db with eps = max |ratio - 1| of spot checks.
"""
import json
import sys
from collections import defaultdict

import mpmath as mm

RHO_MIN = mm.mpf('1e-8')


def main():
    mm.mp.dps = 40
    rows = [json.loads(x) for x in open(sys.argv[1], encoding='utf-8')]
    bad = [r for r in rows if r.get('status') != 'ok']
    print('rows', len(rows), 'not_ok', len(bad))
    for r in bad:
        print('NOT_OK', r.get('job'), r.get('status'), (r.get('error') or '')[:200])
    spots = [r for r in rows if r['job'][0] == 'spot' and r.get('status') == 'ok']
    eps = max((abs(r['ratio'] - 1) for r in spots), default=None)
    print('spot checks (KDK40 measured / M7 predicted):')
    for r in sorted(spots, key=lambda r: r['job']):
        print('  ', r['job'][1][:6], r['job'][2], r['job'][3], f"d_sweep {r['d_sweep']:+.3e} ratio {r['ratio']:.6f} steps {r['steps']}")
    cfg = defaultdict(list)
    for r in rows:
        if r['job'][0] == 'panel' and r.get('status') == 'ok':
            cfg[(r['job'][1], r['job'][2])].append(r)
    expected = defaultdict(int)
    for r in rows:
        if r['job'][0] == 'panel':
            expected[(r['job'][1], r['job'][2])] += 1
    table = []
    for key in sorted(cfg):
        rs = cfg[key]
        q2 = mm.mpf(0); d = {h: mm.mpf(0) for h in ('40', '20')}; dg = {h: mm.mpf(0) for h in d}
        est = {h: mm.mpf(0) for h in d}; acct = mm.mpf(0); dec = defaultdict(lambda: mm.mpf(0))
        for r in rs:
            pk = {h: mm.mpf(0) for h in d}; pg = {h: mm.mpf(0) for h in d}
            for n in r['nodes']:
                w = 2 * mm.pi * mm.mpf(n['b']) * mm.mpf(n['jac'])
                wk, wg = w * mm.mpf(n['wk']), w * mm.mpf(n['wg'])
                st = mm.mpf(n['sin2_true'])
                q2 += wk * st
                acct += wk * abs(mm.mpf(n['d_sweep']['40']))
                for h in d:
                    diff = mm.mpf(n['sin2'][h]) - st
                    pk[h] += wk * diff; pg[h] += wg * diff
                if r['side'] != 'plain':
                    dec[(r['side'], int(mm.floor(mm.mpf(n['x']))))] += wk * (mm.mpf(n['sin2']['40']) - st)
            for h in d:
                d[h] += pk[h]; dg[h] += pg[h]; est[h] += abs(pk[h] - pg[h])
        b_orb = rs[0].get('b_orb')
        bound = 4 * mm.pi * mm.mpf(b_orb) ** 2 * RHO_MIN if b_orb else mm.mpf(0)
        t = dict(pot=key[0], frac=key[1], panels=len(rs), panels_expected=expected[key], b_orb=b_orb,
                 Q2_fin=float(q2), dQ2_40=float(d['40']), dQ2_20=float(d['20']), dQ2_40_G7=float(dg['40']),
                 est_40=float(est['40']), est_20=float(est['20']),
                 rel_40=float(d['40'] / q2), rel_20=float(d['20'] / q2),
                 ratio_40_20=float(d['40'] / d['20']) if d['20'] else None,
                 per_collision_accounting_40=float(acct), excluded_window_bound=float(bound),
                 m7_shortcut_bound_40=float(eps * acct) if eps is not None else None,
                 per_unit_s_40={f'{k[0]}{k[1]}': float(v) for k, v in sorted(dec.items())})
        table.append(t)
        print(f"{key[0][:6]} {key[1]} panels {len(rs)}/{expected[key]} Q2_fin {float(q2):.6e} | dQ2/Q2 h40 {t['rel_40']:+.3e} "
              f"h20 {t['rel_20']:+.3e} ratio {t['ratio_40_20']} | est40 {t['est_40']:.1e} | per-collision acct "
              f"{float(acct):.3e} | excl bound {float(bound):.1e} | M7 bound {t['m7_shortcut_bound_40']}")
    json.dump(dict(format='c1b1-method-bench-s3b-summary-v0', n_rows=len(rows), n_not_ok=len(bad), m7_eps=eps,
                   not_ok=[dict(job=r.get('job'), error=r.get('error')) for r in bad], table=table,
                   spots=[dict(job=r['job'], ratio=r['ratio'], d_sweep=r['d_sweep'], steps=r['steps']) for r in spots]),
              open(sys.argv[2], 'w', encoding='utf-8'), indent=1)


if __name__ == '__main__':
    main()
