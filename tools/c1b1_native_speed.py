"""C3a-5 (survey_only, information only): single-process speed measurement of the native track (plan
docs/active/C1B1_C3_NATIVE_PEN_PLAN_V0.md section "C3a-5", the plan's section 6 S). Run alone on the machine.

  python tools/c1b1_native_speed.py FIXTURE D0_RESULTS OUT.json [smoke]

Part A, per level: from the dev-panel start states G1 and B6, a track at each (level j, extra bits) runs TICKS ticks
  with PyOneTrack (Python integers) and with NativeTrack (C++), alternating which goes first, ROUNDS rounds.
  Per run: substeps, Python process CPU, native child CPU (reported by the child), wall time; raw states compared.
Part B, whole collision: sealed pen_state (M10, tol 1e-9) on G1 and B4 with both engines, once each (G1 native first,
  B4 Python first), native split into parent (Python) CPU and child (C++) CPU, and wall time; the two engines' results
  (status, level, substeps, out state) are compared.
`smoke` = 2 ticks, levels 0-1, one round, part B on G1 only (checks the tool, not a measurement).
Results are written after every run (partial results survive an interruption).
"""
import hashlib
import importlib.util
import json
import os
import platform
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

TICKS, ROUNDS = 1000, 3
CONFIGS = [(0, 0), (1, 0), (2, 0), (3, 0), (4, 0), (5, 0), (4, 16)]
A_INPUTS = ['G1', 'B6']
B_INPUTS = ['G1', 'B4']


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _panel(fixture_path, d0_path):
    spec = importlib.util.spec_from_file_location('dotd0', ROOT / 'tools/c1b1_dot_d0.py')
    d0 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(d0)
    from c1b1_t7.lang import reference_potential
    panel = d0.panel(json.loads(Path(fixture_path).read_bytes()), reference_potential())
    recorded = json.loads(Path(d0_path).read_bytes())['inputs']
    for k, v in panel.items():
        if [str(x) for x in v['raw']] != recorded[k]['raw']:
            raise ValueError(f'panel input {k} differs from the D0 record')
    return panel


def _start(raw):
    import mpmath as mm
    from c1b1_method_bench.ladder2 import DPS
    from c1b1_t7.state import MU, relative
    with mm.workdps(DPS):
        q0, p0 = relative(raw)
        mu = mm.mpf(MU.numerator) / MU.denominator
    return q0, p0, mu, MU


def track_run(engine, raw, j, extra, ticks):
    import mpmath as mm
    from c1b1_method_bench.ladder2 import DPS
    from c1b1_method_bench.pen import H0, grid
    from c1b1_native import track
    from c1b1_native.reference import PyOneTrack
    from c1b1_t7.lang_fx2 import LangForceFX2
    q0, p0, mu, MU = _start(raw)
    fp, fm = grid(j)
    cls = track.NativeTrack if engine == 'native' else PyOneTrack
    try:
        with mm.workdps(DPS):
            t = cls(LangForceFX2(), q0, p0, j, 'chin', fp + extra, fm + extra, mu, H0, MU)
            c0, w0 = time.process_time(), time.perf_counter()
            k0 = t.cpu_ns if engine == 'native' else 0
            t.run_to(ticks)
            cpu, wall = time.process_time() - c0, time.perf_counter() - w0
            child = (t.cpu_ns - k0) / 1e9 if engine == 'native' else 0.0
            raw_out = [str(x) for x in t.qr + t.pr_]
    finally:
        track.close_all()
    return dict(substeps=t.substeps, parent_cpu_s=cpu, child_cpu_s=child, wall_s=wall, raw=raw_out,
                us_per_substep=1e6 * (cpu + child) / t.substeps)


def pen_run(engine, raw):
    import c1b1_t7.ladder as L
    from c1b1_native import track
    from c1b1_native.reference import PyOneTrack
    from c1b1_t7.lang_fx2 import LangForceFX2
    q0, p0, mu, MU = _start(raw)
    orig = L.FxTrackX
    L.FxTrackX = track.NativeTrack if engine == 'native' else PyOneTrack
    try:
        c0, k0, w0 = time.process_time(), track.child_cpu_s(), time.perf_counter()
        res = L.pen_state(LangForceFX2(), q0, p0, '1e-9', j_max=6, mu=mu, mu_exact=MU)
        cpu, wall = time.process_time() - c0, time.perf_counter() - w0
        child = track.child_cpu_s() - k0
    finally:
        L.FxTrackX = orig
        track.close_all()
    out = res.get('out') or {}
    return dict(status=res['status'], j_out=res.get('j_out'), substeps=res['substeps'], parent_cpu_s=cpu,
                child_cpu_s=child, wall_s=wall, out_q_raw=out.get('q_raw'), out_p_raw=out.get('p_raw'),
                out_sweep=out.get('sweep'))


def main(fixture_path, d0_path, out_path, smoke=False):
    from c1b1_native import track
    from c1b1_native.build import build
    ticks, rounds, configs, b_inputs = (2, 1, CONFIGS[:2], B_INPUTS[:1]) if smoke else (TICKS, ROUNDS, CONFIGS,
                                                                                          B_INPUTS)
    binary = str(build('-O2'))
    track.configure(binary)
    panel = _panel(fixture_path, d0_path)
    res = dict(script_sha256=_sha(__file__), track_cpp_sha256=_sha(ROOT / 'c1b1_native/track.cpp'), binary=binary,
               smoke=smoke, ticks=ticks, rounds=rounds, python=sys.version.split()[0], platform=platform.platform(),
               cpu_count=os.cpu_count(), loadavg_start=Path('/proc/loadavg').read_text().split()[:3]
               if Path('/proc/loadavg').exists() else None, part_a=[], part_b=[])

    def save():
        Path(out_path).write_text(json.dumps(res, indent=1), encoding='utf-8')

    save()
    for rnd in range(rounds):
        for name in A_INPUTS:
            for j, extra in configs:
                order = ('py', 'native') if (rnd + j) % 2 == 0 else ('native', 'py')
                runs = {e: track_run(e, panel[name]['raw'], j, extra, ticks) for e in order}
                same = runs['py']['raw'] == runs['native']['raw'] and runs['py']['substeps'] == runs['native']['substeps']
                for e in order:
                    runs[e].pop('raw')
                res['part_a'].append(dict(round=rnd, input=name, j=j, extra=extra, order=list(order), raw_equal=same,
                                          py=runs['py'], native=runs['native'],
                                          ratio=runs['py']['us_per_substep'] / runs['native']['us_per_substep']))
                print(name, rnd, j, extra, round(res['part_a'][-1]['ratio'], 2), same, flush=True)
                save()
    keys = ('status', 'j_out', 'substeps', 'out_q_raw', 'out_p_raw', 'out_sweep')
    for i, name in enumerate(b_inputs):
        got = {}
        for e in (('native', 'py') if i % 2 == 0 else ('py', 'native')):
            got[e] = pen_run(e, panel[name]['raw'])
            res['part_b'].append(dict(input=name, engine=e, **got[e]))
            print('pen', name, e, round(got[e]['parent_cpu_s'] + got[e]['child_cpu_s'], 1), flush=True)
            save()
        res['part_b'].append(dict(input=name, engines_equal=all(got['py'][k] == got['native'][k] for k in keys)))
        save()
    res['loadavg_end'] = Path('/proc/loadavg').read_text().split()[:3] if Path('/proc/loadavg').exists() else None
    save()


if __name__ == '__main__':
    a = sys.argv
    if len(a) < 4:
        raise SystemExit(__doc__)
    main(a[1], a[2], a[3], smoke=len(a) > 4 and a[4] == 'smoke')
