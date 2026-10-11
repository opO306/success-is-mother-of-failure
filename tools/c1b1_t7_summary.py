"""Summarize T7 argon rows against the pre-run record (C1B1_T7_ARGON_HOLDOUT_PLAN_V0.md "봉인 기록").

Bundles O (O-1 inputs) and S (rho scan) are the judged set; H (> 10 De) is survey_only and reported separately.
  V  accepted output (C or base round-back) with true error > tol                                   expected 0
  U  ladder pair whose fine run C has true error > its estimate (est_step, or est_step + d_round)   expected 0
  C  cap_stop                                                                                       expected 0
  R  accepted with d_round > est_step / 100                                                         expected 0
  D  repeat rows identical to their main rows (CPU timings excluded)                                expected all
  X  UNRESOLVED: reference stopped, or the quadref cross-check differs by more than the seal limit  reported
  E  errors (no row content)                                                                        expected 0
  B  base round-back changes the true error by > 1e-13                                              reported
  P  S-bundle j_out above the S3c worst-case depth                                                  reported
  W  production-like KDK h = 40 on (48, 80): true error (comparison only, not a candidate)            reported
  python tools/c1b1_t7_summary.py ROWS.jsonl OUT_PREFIX
"""
import json
import sys
from collections import Counter, defaultdict

TOL = 1e-9
PRED_J = {1e-2: 1, 1e-4: 1, 1e-6: 2, 1e-8: 3, 1e-10: 5}
TIMING = ('cpu_s', 'wall_s', 'pen_cpu_s', 'ref_cpu_s', 'track_cost', 'job')


def strip(d):
    if isinstance(d, dict):
        return {k: strip(v) for k, v in d.items() if k not in TIMING}
    if isinstance(d, list):
        return [strip(v) for v in d]
    return d


def summarize(rows):
    S = defaultdict(list)
    lines, depth = [], defaultdict(Counter)
    for r in rows:
        job = r['job']
        jid, judged = job['id'], job['bundle'] in ('O', 'S')
        tag = '' if judged else 'H_'
        if r.get('status') not in ('accepted', 'cap_stop'):
            S['E_errors'].append((jid, r.get('error')))
            continue
        ref = r.get('reference', {})
        if ref.get('status') != 'ok':
            S['X_unresolved'].append((jid, 'reference', ref.get('reason')))
            continue
        cross = r.get('cross')
        if cross is not None and not cross.get('agree'):
            S['X_unresolved'].append((jid, 'cross', cross))
        for pr in r['pairs']:
            st = pr['C_state']
            es, et = (pr['est_sweep'], pr['est_time']) if pr.get('checked') else (pr['est_step_sweep'],
                                                                                  pr['est_step_time'])
            if st['err_sweep'] > float(es) or st['err_time'] > float(et):
                S[tag + 'U_underestimates'].append((jid, pr['j'], es, st['err_sweep'], et, st['err_time']))
        if r['status'] == 'cap_stop':
            S[tag + 'C_cap_stops'].append(jid)
        else:
            o, ob, last = r['out'], r['out_base'], r['pairs'][-1]
            for name, s in (('C', o), ('base', ob)):
                if s['err_sweep'] > TOL or s['err_time'] > TOL:
                    S[tag + 'V_violations'].append((jid, name, s['err_sweep'], s['err_time']))
            if abs(ob['err_sweep'] - o['err_sweep']) > 1e-13 or abs(ob['err_time'] - o['err_time']) > 1e-13:
                S['B_roundback'].append(jid)
            if (float(last['d_round_sweep']) > float(last['est_step_sweep']) / 100
                    or float(last['d_round_time']) > float(last['est_step_time']) / 100):
                S[tag + 'R_rounding_not_small'].append((jid, last['d_round_sweep'], last['est_step_sweep']))
            if job['bundle'] == 'S' and job['variant'] == 'main':
                rho = abs(float(job['rho']))
                depth[job['rho']][r['j_out']] += 1
                if r['j_out'] > PRED_J[rho]:
                    S['P_above_s3c_depth'].append((jid, r['j_out'], PRED_J[rho]))
        w = r['world_kdk']
        S['W_world_kdk'].append((jid, w['err_sweep'], w['err_time']))
        o = r.get('out') or {}
        lines.append('%-24s %-8s %-9s j_out=%s lvl0 err_s=%-9.2e kdk48 err_s=%-9.2e out err_s=%-9.2e err_t=%-9.2e '
                     'substeps=%-9d wall=%.0fs' % (jid, job['variant'], r['status'], r['j_out'],
                                                    r['level0']['err_sweep'], w['err_sweep'],
                                                    o.get('err_sweep', float('nan')), o.get('err_time', float('nan')),
                                                    r['substeps'], r['wall_s']))
    main = {r['job']['id']: r for r in rows if r['job']['variant'] == 'main'}
    S['D_repeat'] = [(r['job']['id'], r['job']['repeat_of'] in main and strip(main[r['job']['repeat_of']]) == strip(r))
                     for r in rows if r['job']['variant'] == 'repeat']
    S['j_out_by_rho'] = {k: dict(v) for k, v in depth.items()}
    S['status'] = sorted(Counter((r['job']['bundle'], r['job']['variant'], r.get('status')) for r in rows).items())
    S['cost'] = dict(rows=len(rows), cpu_s=sum(r.get('cpu_s', 0) for r in rows),
                     max_wall_s=max((r.get('wall_s', 0) for r in rows), default=0))
    return dict(S), lines


def main():
    rows = [json.loads(line) for line in open(sys.argv[1], encoding='utf-8')]
    out = sys.argv[2]
    summary, lines = summarize(rows)
    with open(out + '.json', 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=1, default=str)
    with open(out + '.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(sorted(lines)) + '\n')
        for k in sorted(summary):
            v = summary[k]
            f.write(f'\n{k}: {len(v) if hasattr(v, "__len__") else v}\n')
            for item in (v.items() if isinstance(v, dict) else v):
                f.write(f'  {item}\n')
    print(open(out + '.txt', encoding='utf-8').read()[-10000:])


if __name__ == '__main__':
    main()
