"""C3a replay (survey_only): re-run sealed T7 jobs with the native track swapped into the SEALED pen_state and compare
the world layer with the T7 rows (plan docs/active/C1B1_C3_NATIVE_PEN_PLAN_V0.md section 6 R).

  python tools/c1b1_native_replay.py INPUTS ROWS OUT.jsonl IDS [WORKERS] [BINARY]
Exact: every integer field and every string Python derives from integers (r, time, est_*_time, out_base.r).
Within 1e-40: fields derived from the sweep (T7 recorded the accumulated sweep; C3a uses the one-shot sweep).
Verdict per job: IDENTICAL / DIFFERENT / UNRESOLVED (a native refusal) / ERROR.
CPU: parent process time plus the native children's own CPU (reported by each child).
"""
import hashlib
import importlib.util
import json
import sys
import time
from pathlib import Path

import mpmath as mm

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

ROWS_SHA256 = '8d8ad172e5db3121'
SWEEP_FIELDS = {'sweep', 'sweep_shift', 'est_step_sweep', 'd_round_sweep', 'est_sweep'}
TOL_SWEEP = mm.mpf('1e-40')


def _replay_module():
    spec = importlib.util.spec_from_file_location('fxreplay', ROOT / 'tools/c1b1_pen_fx_replay.py')
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def leaves(a, b, path=''):
    if type(a) is not type(b):
        yield path, a, b
    elif isinstance(a, dict):
        for k in sorted(set(a) | set(b)):
            yield from leaves(a.get(k), b.get(k), f'{path}.{k}')
    elif isinstance(a, list):
        if len(a) != len(b):
            yield path + '[len]', a, b
        else:
            for i, (x, y) in enumerate(zip(a, b)):
                yield from leaves(x, y, f'{path}[{i}]')
    elif a != b:
        yield path, a, b


def compare(a, b):
    """(hard differences, sweep differences within tolerance, sweep differences beyond tolerance)."""
    hard, soft, soft_bad = [], [], []
    for path, x, y in leaves(a, b):
        key = path.rsplit('.', 1)[-1].split('[')[0]
        if key in SWEEP_FIELDS and isinstance(x, str) and isinstance(y, str):
            with mm.workdps(60):
                d = abs(mm.mpf(x) - mm.mpf(y))
            (soft if d <= TOL_SWEEP else soft_bad).append((path, mm.nstr(d, 3)))
        else:
            hard.append(path)
    return hard, soft, soft_bad


def near_tol(row, tol=1e-9):
    """T7 6-digit estimate strings that sit at the acceptance threshold (plan 3.4 pre-check)."""
    out = []
    for i, pr in enumerate(row.get('pairs', [])):
        for k in ('est_step_sweep', 'est_sweep'):
            if k in pr and abs(float(pr[k]) / tol - 1) < 1e-5:
                out.append(f'pairs[{i}].{k}={pr[k]}')
    return out


def run_world(job, binary, tol='1e-9', j_max=6):
    import c1b1_t7.ladder as L
    from c1b1_method_bench.ladder2 import DPS
    from c1b1_native import track
    from c1b1_t7.lang_fx2 import LangForceFX2
    from c1b1_t7.state import MU, relative
    track.configure(binary)
    pot = LangForceFX2()
    with mm.workdps(DPS):
        q0, p0 = relative(job['raw'])
        mu = mm.mpf(MU.numerator) / MU.denominator
    orig = L.FxTrackX
    L.FxTrackX = track.NativeTrack                      # sealed pen_state looks this name up when it runs
    try:
        t0, c0 = time.process_time(), track.child_cpu_s()
        res = L.pen_state(pot, q0, p0, tol, j_max=j_max, mu=mu, mu_exact=MU)
        res['pen_cpu_s'] = time.process_time() - t0 + track.child_cpu_s() - c0
        with mm.workdps(DPS):
            w = track.NativeTrack(pot, q0, p0, 0, 'kdk', 48, 80, mu, 40, MU)
            t1, c1 = time.process_time(), track.child_cpu_s()
            w.run_to_exit(300_000)
            res['world_kdk'] = w.state()
            res['world_kdk']['cpu_s'] = time.process_time() - t1 + track.child_cpu_s() - c1
        res['native_kicks'] = sum(t.kicks for t in list(track._LIVE))
    finally:
        L.FxTrackX = orig
        track.close_all()
    return res


def one(args):
    job, ref, binary = args
    from c1b1_native.track import NativeRefused
    rp = _replay_module()
    t0, w0 = time.process_time(), time.perf_counter()
    try:
        res = run_world(job, binary)
        hard, soft, soft_bad = compare(rp.world(res), rp.world(ref))
        verdict = 'IDENTICAL' if not hard and not soft_bad else 'DIFFERENT'
        row = dict(id=job['id'], verdict=verdict, hard=hard[:20], n_hard=len(hard), sweep_within=len(soft),
                   sweep_max=max([d for _, d in soft], key=lambda s: float(s), default='0'), sweep_beyond=soft_bad[:20],
                   near_tol_t7=near_tol(ref), native_pen_cpu_s=res['pen_cpu_s'], t7_pen_cpu_s=ref.get('pen_cpu_s'),
                   native_kdk_cpu_s=res['world_kdk']['cpu_s'], t7_kdk_cpu_s=ref['world_kdk'].get('cpu_s'),
                   native_kicks=res['native_kicks'], t7_force_evaluations=ref.get('force_evaluations'))
    except NativeRefused as exc:
        row = dict(id=job['id'], verdict='UNRESOLVED', refusal=str(exc)[:300])
    except Exception as exc:                                          # recorded, never hidden
        row = dict(id=job['id'], verdict='ERROR', error=repr(exc)[:300])
    row.update(cpu_s=time.process_time() - t0, wall_s=time.perf_counter() - w0)
    return row


def replay(inputs, rows, out, ids, workers=6, binary=None):
    from c1b1_method_bench.runner import run_jobs
    from c1b1_native.build import build
    sys.path.insert(0, str(ROOT / 'tools'))
    spec = importlib.util.spec_from_file_location('t7argon', ROOT / 'tools/c1b1_t7_argon.py')
    t7 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(t7)
    payload = t7.load(inputs)                                         # seal + code + PES hash checks
    if hashlib.sha256(Path(rows).read_bytes()).hexdigest()[:16] != ROWS_SHA256:
        raise ValueError('T7 rows file hash mismatch')
    binary = str(binary or build('-O2'))
    from c1b1_native.build import lf_sha256                          # C3b-1: tie the result to its source
    Path(str(out) + '.manifest.json').write_text(json.dumps(dict(
        track_cpp_lf_sha256=lf_sha256(ROOT / 'c1b1_native/track.cpp'), binary=binary, ids=ids,
        tool_lf_sha256=lf_sha256(__file__)), indent=1), encoding='utf-8')
    jobs = {j['id']: j for j in payload['jobs']}
    refs = {r['job']['id']: r for r in (json.loads(line) for line in open(rows, encoding='utf-8'))}
    work = [(jobs[i], refs[i], binary) for i in ids.split(',')]
    run_jobs(one, work, out, workers=workers, label='C3a replay ')


if __name__ == '__main__':
    a = sys.argv
    replay(a[1], a[2], a[3], a[4], int(a[5]) if len(a) > 5 else 6, a[6] if len(a) > 6 else None)
