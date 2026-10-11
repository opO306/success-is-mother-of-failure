"""T7 argon holdout (S4, survey_only): M10 brush pen on the Lang 2024 Ar2 potential, once, from a sealed input list.

  seal OUT_JSON O1_INPUTS FIXTURE      build the 51-job list (O-1 raws, canonical rho scan, >10 De) and hash every
                                       code file the run uses; written once (never overwritten)
  run  INPUTS ROWS [WORKERS] [IDS]     verify the seal, run the jobs (IDS: comma-separated job ids, for splitting the
                                       list between machines; default all), one fresh process per job
World layer: c1b1_t7.ladder.pen_state (M10, tol 1e-9, j_max 6) from the stored base-grid state, exact Ar mass.
Comparison track (not a candidate): production-like KDK h = 40 on the base grid (48, 80).
Verification layer: c1b1_t7.reference.scatter_many (cont2, 40 digits, checked at 60) for every verified state;
cross-check (cross=True jobs): bench quadref (80 digits) for the accepted output.
"""
import hashlib
import json
import os
import sys
import time
from fractions import Fraction as Q
from pathlib import Path

import mpmath as mm

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

TOL = '1e-9'
J_MAX = 6
REF_DPS = 40
CROSS_LIMIT = '1e-18'
S_ENERGIES = ['3/20', '1/2', '9/10']
S_RHO = ['1e-2', '-1e-2', '1e-4', '-1e-4', '1e-6', '-1e-6', '1e-8', '-1e-8', '1e-10', '-1e-10']
H_ENERGIES = ['20', '33', '45']
H_B = ['0', '71129/20000', '71129/10000']            # 0, Re/2, Re (Re = bench Ar2 scale 7.1129 bohr)
REPEATS = ['O:boundary_pass', 'S:1/2:-1e-8']
CODE = ['c1b1_t7/__init__.py', 'c1b1_t7/lang.py', 'c1b1_t7/state.py', 'c1b1_t7/ladder.py', 'c1b1_t7/reference.py',
        'c1b1_method_bench/pen.py', 'c1b1_method_bench/ladder2.py', 'c1b1_method_bench/fixedpoint.py',
        'c1b1_method_bench/run.py', 'c1b1_method_bench/potentials.py', 'c1b1_method_bench/quadref.py',
        'c1b1_cont2/scatter.py', 'c1b1_o1/model.py', 'tools/c1b1_t7_argon.py', 'tools/c1b1_t7_summary.py']


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def digest(payload):
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def build_jobs(o1_inputs, fixture, V):
    """The job list. o1_inputs: the O-1 seal payload; fixture: the orbit boundary fixture v3 (dict)."""
    from c1b1_t7.state import canonical_raw
    jobs = []
    for row in o1_inputs['inputs']:
        jobs.append(dict(id='O:' + row['id'], bundle='O', variant='main', e=row['E_De'], b=row['b_bohr'],
                         rho=row['rho'], raw=row['raw'], cross=True))
    orbit = {Q(r['e']): Q(r['b_orb']) for r in fixture['energies']}
    for e in S_ENERGIES:
        for rho in S_RHO:
            b = orbit[Q(e)] * (1 + Q(rho))
            jobs.append(dict(id=f'S:{e}:{rho}', bundle='S', variant='main', e=e, b=str(b), rho=rho,
                             raw=canonical_raw(e, b * b, V), cross=Q(rho) > 0))
    for e in H_ENERGIES:
        for b in H_B:
            jobs.append(dict(id=f'H:{e}:{b}', bundle='H', variant='main', e=e, b=b, rho=None,
                             raw=canonical_raw(e, Q(b) ** 2, V), cross=False))
    by_id = {j['id']: j for j in jobs}
    for rid in REPEATS:
        jobs.append(dict(by_id[rid], id='R:' + rid, variant='repeat', repeat_of=rid))
    return jobs


def order_key(job):
    """Hardest first (smallest |rho|), so the long jobs start early; order never changes a result."""
    rho = abs(float(Q(job['rho']))) if job['rho'] else 1.0
    return (rho, job['id'])


def seal(out, o1_path, fixture_path):
    from c1b1_t7.lang import pes_path, reference_potential
    out = Path(out)
    o1 = json.loads(Path(o1_path).read_bytes())
    if digest(o1['payload']) != o1['payload_sha256']:
        raise ValueError('O-1 input seal mismatch')
    fixture = json.loads(Path(fixture_path).read_bytes())
    V = reference_potential()
    jobs = sorted(build_jobs(o1['payload'], fixture, V), key=order_key)
    payload = dict(schema='c1b1-t7-argon-inputs-v0', candidate='M10 brush pen (c1b1_t7.ladder.pen_state)',
                   tol=TOL, j_max=J_MAX, ref_dps=REF_DPS, cross_limit=CROSS_LIMIT, jobs=jobs,
                   o1_input_payload_sha256=o1['payload_sha256'], fixture_sha256=sha(fixture_path),
                   pes_sha256=sha(pes_path()), code_sha256={f: sha(ROOT / f) for f in CODE},
                   created_before_any_t7_run=True, push=False)
    with out.open('x', encoding='utf-8') as f:                       # never overwrite a seal
        json.dump(dict(payload=payload, payload_sha256=digest(payload)), f, indent=1)
        f.write('\n')
    print('SEALED', digest(payload), len(jobs), flush=True)


def load(path):
    from c1b1_t7.lang import pes_path
    data = json.loads(Path(path).read_bytes())
    p = data['payload']
    if digest(p) != data['payload_sha256']:
        raise ValueError('T7 input seal mismatch')
    for f, h in p['code_sha256'].items():
        if sha(ROOT / f) != h:
            raise ValueError('code changed since the seal: ' + f)
    if sha(pes_path()) != p['pes_sha256']:
        raise ValueError('PES file changed since the seal')
    return p


class _VOnly:
    """quadref needs pot.V only."""
    def __init__(self, V):
        self.V = V


def one(job, tol=TOL, j_max=J_MAX, ref_dps=REF_DPS, cross_limit=CROSS_LIMIT):
    from c1b1_method_bench import quadref
    from c1b1_method_bench.ladder2 import DPS
    from c1b1_t7.ladder import FxTrackX, pen_state
    from c1b1_t7.lang import LangForce, reference_potential
    from c1b1_t7.reference import Unresolved, scatter_many
    from c1b1_t7.state import MU, relative
    t0, w0 = time.process_time(), time.perf_counter()
    row = dict(job={k: v for k, v in job.items() if k != 'raw'})
    pot, V = LangForce(), reference_potential()
    with mm.workdps(DPS):
        q0, p0 = relative(job['raw'])
        mu = mm.mpf(MU.numerator) / MU.denominator
    try:
        res = pen_state(pot, q0, p0, tol, j_max=j_max, mu=mu, mu_exact=MU)
        with mm.workdps(DPS):
            w = FxTrackX(pot, q0, p0, 0, 'kdk', 48, 80, mu, 40, MU)
            tw = time.process_time()
            w.run_to_exit(300_000)
            res['world_kdk'] = w.state()
            res['world_kdk']['cpu_s'] = time.process_time() - tw
        row.update(res)
    except Exception as exc:                                          # recorded, never hidden
        row.update(status='error', error=repr(exc)[:300])
        row.update(cpu_s=time.process_time() - t0, wall_s=time.perf_counter() - w0)
        return row
    row['pen_cpu_s'] = time.process_time() - t0
    states = [row['level0'], row['world_kdk']] + [pr['C_state'] for pr in row['pairs']]
    if row['status'] == 'accepted':
        states += [row['out'], row['out_base']]
    tr = time.process_time()
    try:
        ref = scatter_many(V, mu, q0, p0, [st['r'] for st in states], dps=ref_dps)
        row['reference'] = dict(r_min=ref['r_min'], precision_diff=ref['precision_diff'], status='ok')
        with mm.workdps(ref_dps + 20):
            for st, x in zip(states, ref['exits']):
                d_s = mm.mpf(st['sweep']) - mm.mpf(x['sweep'])
                st.update(ref_sweep=x['sweep'], ref_time=x['time'], err_sweep=float(abs(d_s)), d_sweep=float(d_s),
                          err_time=float(abs(mm.mpf(st['time']) - mm.mpf(x['time'])) / mm.mpf(x['time'])))
    except Unresolved as exc:
        row['reference'] = dict(status='UNRESOLVED', reason=str(exc)[:300])
    row['ref_cpu_s'] = time.process_time() - tr
    if job['cross'] and row['status'] == 'accepted' and row['reference']['status'] == 'ok':
        tc = time.process_time()
        try:
            with mm.workdps(quadref.DPS):
                q, p = [mm.mpf(x) for x in q0], [mm.mpf(x) for x in p0]
                mu80 = mm.mpf(MU.numerator) / MU.denominator
                E = (p[0] ** 2 + p[1] ** 2) / (2 * mu80) + V(mm.sqrt(q[0] ** 2 + q[1] ** 2))
                L = q[0] * p[1] - q[1] * p[0]
                x = quadref.reference(_VOnly(V), mu80, E, L, mm.mpf(row['out']['r']))
                ds = abs(x['sweep'] - mm.mpf(row['out']['ref_sweep']))
                dt = abs(x['time'] - mm.mpf(row['out']['ref_time'])) / x['time']
                row['cross'] = dict(status='ok', d_sweep=mm.nstr(ds, 6), d_time=mm.nstr(dt, 6),
                                    agree=bool(ds <= mm.mpf(cross_limit) and dt <= mm.mpf(cross_limit)))
        except Exception as exc:
            row['cross'] = dict(status='error', error=repr(exc)[:300], agree=False)
        row['cross']['cpu_s'] = time.process_time() - tc
    row.update(force_evaluations=pot.evaluations, cpu_s=time.process_time() - t0, wall_s=time.perf_counter() - w0)
    return row


def run(inputs, rows, workers=4, ids=None):
    from c1b1_method_bench.runner import run_jobs
    p = load(inputs)
    jobs = p['jobs']
    if ids:
        want = ids.split(',')
        unknown = set(want) - {j['id'] for j in jobs}
        if unknown:
            raise ValueError(f'unknown job ids {sorted(unknown)}')
        jobs = [j for j in jobs if j['id'] in want]
    run_jobs(one, jobs, rows, workers=workers, label='T7 ')


if __name__ == '__main__':
    a = sys.argv
    if a[1] == 'seal':
        seal(a[2], a[3], a[4])
    elif a[1] == 'run':
        run(a[2], a[3], int(a[4]) if len(a) > 4 else 4, a[5] if len(a) > 5 else None)
    else:
        raise SystemExit(__doc__)
