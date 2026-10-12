"""Cost plan C1 (survey_only): re-run sealed T7 jobs with the fixed-point jet (c1b1_t7.lang_fx.LangForceFX) and
compare every world-layer state with the T7 rows bit for bit; plus an interleaved speed probe.

  replay INPUTS ROWS OUT.jsonl IDS [WORKERS] [FORCE]
                                              M10 (pen_state) + world_kdk with FORCE (fx = LangForceFX, default;
                                              fx2 = LangForceFX2, cost plan C1.1), same settings as T7;
                                              compare level0, every pair (estimates, C_state), out, out_base,
                                              world_kdk and per-track substeps; verification fields are ignored
  speed  INPUTS OUT.json JOB TICKS [ROUNDS]     level 0 and level 1 tracks, LangForce / LangForceFX / LangForceFX2,
                                              CPU per substep and raw-state equality (run alone on the machine)
"""
import json
import sys
import time
from pathlib import Path

import mpmath as mm

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

VERIFY_KEYS = {'ref_sweep', 'ref_time', 'err_sweep', 'd_sweep', 'err_time', 'cpu_s'}
WORLD_KEYS = ('status', 'j_out', 'bits_out', 'out', 'out_base', 'pairs', 'level0', 'substeps', 'world_kdk')


def strip(d):
    if isinstance(d, dict):
        return {k: strip(v) for k, v in d.items() if k not in VERIFY_KEYS}
    if isinstance(d, list):
        return [strip(v) for v in d]
    return d


def world(row):
    out = {k: strip(row.get(k)) for k in WORLD_KEYS}
    out['track_substeps'] = [[t['j'], t['extra'], t['substeps']] for t in row.get('track_cost', [])]
    return out


def diff_paths(a, b, path=''):
    if type(a) is not type(b):
        return [path]
    if isinstance(a, dict):
        return [p for k in sorted(set(a) | set(b)) for p in diff_paths(a.get(k), b.get(k), f'{path}.{k}')]
    if isinstance(a, list):
        if len(a) != len(b):
            return [path + '[len]']
        return [p for i, (x, y) in enumerate(zip(a, b)) for p in diff_paths(x, y, f'{path}[{i}]')]
    return [] if a == b else [path]


def run_world(job, force_cls, tol='1e-9', j_max=6):
    from c1b1_method_bench.ladder2 import DPS
    from c1b1_t7.ladder import FxTrackX, pen_state
    from c1b1_t7.state import MU, relative
    pot = force_cls()
    with mm.workdps(DPS):
        q0, p0 = relative(job['raw'])
        mu = mm.mpf(MU.numerator) / MU.denominator
    t0 = time.process_time()
    res = pen_state(pot, q0, p0, tol, j_max=j_max, mu=mu, mu_exact=MU)
    pen_cpu = time.process_time() - t0
    with mm.workdps(DPS):
        w = FxTrackX(pot, q0, p0, 0, 'kdk', 48, 80, mu, 40, MU)
        tw = time.process_time()
        w.run_to_exit(300_000)
        res['world_kdk'] = w.state()
        res['world_kdk']['cpu_s'] = time.process_time() - tw
    res['pen_cpu_s'] = pen_cpu
    res['force_evaluations'] = pot.evaluations
    return res


def force_class(name):
    if name == 'fx2':
        from c1b1_t7.lang_fx2 import LangForceFX2
        return LangForceFX2
    from c1b1_t7.lang_fx import LangForceFX
    return LangForceFX


def one(args):
    job, ref, force = args
    t0, w0 = time.process_time(), time.perf_counter()
    try:
        res = run_world(job, force_class(force))
        a, b = world(res), world(ref)
        diffs = diff_paths(a, b)
        row = dict(id=job['id'], force=force, identical=not diffs, diffs=diffs[:20], n_diffs=len(diffs),
                   fx_pen_cpu_s=res['pen_cpu_s'], t7_pen_cpu_s=ref.get('pen_cpu_s'),
                   fx_kdk_cpu_s=res['world_kdk']['cpu_s'], t7_kdk_cpu_s=ref['world_kdk'].get('cpu_s'),
                   force_evaluations=res['force_evaluations'], t7_force_evaluations=ref.get('force_evaluations'))
    except Exception as exc:                                          # recorded, never hidden
        row = dict(id=job['id'], identical=False, error=repr(exc)[:300])
    row.update(cpu_s=time.process_time() - t0, wall_s=time.perf_counter() - w0)
    return row


def replay(inputs, rows, out, ids, workers=4, force='fx'):
    from c1b1_method_bench.runner import run_jobs
    jobs = {j['id']: j for j in json.loads(Path(inputs).read_bytes())['payload']['jobs']}
    refs = {r['job']['id']: r for r in (json.loads(l) for l in open(rows, encoding='utf-8'))}
    work = [(jobs[i], refs[i], force) for i in ids.split(',')]
    run_jobs(one, work, out, workers=workers, label='C1 replay ')


def speed(inputs, out, jid, ticks, rounds=3):
    from c1b1_method_bench.ladder2 import DPS
    from c1b1_method_bench.pen import grid
    from c1b1_t7.ladder import FxTrackX
    from c1b1_t7.lang import LangForce
    from c1b1_t7.lang_fx import LangForceFX
    from c1b1_t7.lang_fx2 import LangForceFX2
    from c1b1_t7.state import MU, relative
    job = next(j for j in json.loads(Path(inputs).read_bytes())['payload']['jobs'] if j['id'] == jid)
    rows = []
    with mm.workdps(DPS):
        q0, p0 = relative(job['raw'])
        mu = mm.mpf(MU.numerator) / MU.denominator
        for rnd in range(rounds):
            for j in (0, 1):
                fp, fm = grid(j)
                raws = {}
                for cls in (LangForce, LangForceFX, LangForceFX2):
                    t = FxTrackX(cls(), q0, p0, j, 'chin', fp, fm, mu, 40, MU)
                    a = time.process_time()
                    t.run_to(ticks)
                    dt = time.process_time() - a
                    raws[cls.__name__] = (t.qr, t.pr_)
                    rows.append(dict(round=rnd, j=j, force=cls.__name__, substeps=t.substeps,
                                     us_per_substep=1e6 * dt / t.substeps))
                    print(rows[-1], flush=True)
                rows.append(dict(round=rnd, j=j, raw_identical=raws['LangForce'] == raws['LangForceFX'] == raws['LangForceFX2']))
                print(rows[-1], flush=True)
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(dict(job=jid, ticks=ticks, rows=rows), f, indent=1)


if __name__ == '__main__':
    a = sys.argv
    if a[1] == 'replay':
        replay(a[2], a[3], a[4], a[5], int(a[6]) if len(a) > 6 else 4, a[7] if len(a) > 7 else 'fx')
    elif a[1] == 'speed':
        speed(a[2], a[3], a[4], int(a[5]), int(a[6]) if len(a) > 6 else 3)
    else:
        raise SystemExit(__doc__)
