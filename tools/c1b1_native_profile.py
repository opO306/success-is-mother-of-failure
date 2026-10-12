"""C3b-0 (survey_only, information only): gprof profile of the C3a native track (plan
docs/active/C1B1_C3B_NATIVE_KERNEL_SPEED_PLAN_V0.md section 3). Run alone on a Linux machine with g++ and gprof.

  python tools/c1b1_native_profile.py FIXTURE D0_RESULTS OUT_DIR

Builds c1b1_native/track.cpp three ways: -O2 (reference, as c1b1_native.build), -O2 -pg, -O1 -fno-inline -pg.
Workloads (dev panel, Chin): G1 level 0, G1 level 4, B6 level 4, each `to 1000` ticks from the start state, one track
per process, each profiled process in its own directory (gmon.out). Writes OUT_DIR/profile.txt (gprof flat profile and
the top of the call graph per build and workload) and OUT_DIR/profile.json (raw states, CPU, equality with the
reference build). Profiling must not change a result: every profiled raw state is compared with the reference.
"""
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

SRC = ROOT / 'c1b1_native/track.cpp'
BUILDS = {'O2pg': ['-O2', '-pg'], 'O1noinline_pg': ['-O1', '-fno-inline', '-pg']}
WORKLOADS = [('G1', 0), ('G1', 4), ('B6', 4)]
TICKS = 1000


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


def run_track(binary, raw, j, workdir):
    import mpmath as mm
    from c1b1_method_bench.ladder2 import DPS
    from c1b1_method_bench.pen import H0, grid
    from c1b1_native import track
    from c1b1_t7.lang_fx2 import LangForceFX2
    from c1b1_t7.state import MU, relative
    track.configure(binary)
    here = os.getcwd()
    os.makedirs(workdir, exist_ok=True)
    os.chdir(workdir)                                   # the child inherits it; gmon.out lands here
    try:
        with mm.workdps(DPS):
            q0, p0 = relative(raw)
            mu = mm.mpf(MU.numerator) / MU.denominator
            fp, fm = grid(j)
            t = track.NativeTrack(LangForceFX2(), q0, p0, j, 'chin', fp, fm, mu, H0, MU)
            k0, w0 = t.cpu_ns, time.perf_counter()
            t.run_to(TICKS)
            out = dict(substeps=t.substeps, kicks=t.kicks, child_cpu_s=(t.cpu_ns - k0) / 1e9,
                       wall_s=time.perf_counter() - w0, raw=[str(x) for x in t.qr + t.pr_])
    finally:
        track.close_all()                               # 'quit' -> normal exit -> gmon.out written
        os.chdir(here)
    out['us_per_substep'] = 1e6 * out['child_cpu_s'] / out['substeps']
    return out


def main(fixture_path, d0_path, out_dir):
    from c1b1_native.build import build
    out_dir = Path(out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=False)
    panel = _panel(fixture_path, d0_path)
    bins = {'O2ref': str(build('-O2'))}
    for name, flags in BUILDS.items():
        exe = out_dir / f'track_{name}'
        subprocess.run(['g++', *flags, '-std=c++17', '-Wall', '-Wextra', '-DINJECT=0', '-o', str(exe), str(SRC)],
                       check=True)
        bins[name] = str(exe)
    res = dict(script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               track_cpp_sha256=hashlib.sha256(SRC.read_bytes()).hexdigest(), builds={k: BUILDS.get(k, ['-O2'])
               for k in bins}, ticks=TICKS, runs=[])
    text = []
    for wname, j in WORKLOADS:
        ref = run_track(bins['O2ref'], panel[wname]['raw'], j, out_dir / f'ref_{wname}_{j}')
        res['runs'].append(dict(build='O2ref', input=wname, j=j, **ref))
        for name in BUILDS:
            wd = out_dir / f'{name}_{wname}_{j}'
            r = run_track(bins[name], panel[wname]['raw'], j, wd)
            r['raw_equal_ref'] = r['raw'] == ref['raw'] and r['substeps'] == ref['substeps']
            res['runs'].append(dict(build=name, input=wname, j=j, **r))
            flat = subprocess.run(['gprof', '-b', '-p', bins[name], str(wd / 'gmon.out')], capture_output=True,
                                  text=True, check=True).stdout
            graph = subprocess.run(['gprof', '-b', '-q', bins[name], str(wd / 'gmon.out')], capture_output=True,
                                   text=True, check=True).stdout
            text.append(f'===== {name} {wname} level {j}: {r["us_per_substep"]:.1f} us/substep, '
                        f'raw_equal_ref={r["raw_equal_ref"]}\n--- flat profile (top 40 lines)\n'
                        + '\n'.join(flat.splitlines()[:40]) + '\n--- call graph (top 120 lines)\n'
                        + '\n'.join(graph.splitlines()[:120]) + '\n')
            print(name, wname, j, round(r['us_per_substep'], 1), r['raw_equal_ref'], flush=True)
            (out_dir / 'profile.json').write_text(json.dumps(res, indent=1), encoding='utf-8')
            (out_dir / 'profile.txt').write_text('\n'.join(text), encoding='utf-8')


if __name__ == '__main__':
    if len(sys.argv) != 4:
        raise SystemExit(__doc__)
    main(*sys.argv[1:])
