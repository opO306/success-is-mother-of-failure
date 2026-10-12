"""C3a-4 (survey_only): dev-panel check of the native track outside T7 (plan docs/active/C1B1_C3_NATIVE_PEN_PLAN_V0.md,
section "C3a-4"). The 14 dot-plan dev-panel inputs (G1-G6, B1-B6, H1-H2; not T7 inputs) are run twice through the
SEALED c1b1_t7.ladder.pen_state (M10, tol 1e-9, j_max 6) plus the world KDK track:
  py      c1b1_native.reference.PyOneTrack  (Python integer arithmetic, LangForceFX2, one-shot sweep)
  native  c1b1_native.track.NativeTrack     (C++ integer arithmetic, same Lang parameters, same one-shot sweep)
Both use the same one-shot sweep formula on their own integer state, so the whole world layer (every string included)
must be equal; there is no tolerance in this comparison.

  python tools/c1b1_native_panel.py run T7_INPUTS FIXTURE D0_RESULTS OUT.jsonl [WORKERS] [IDS] [ENGINES]
  python tools/c1b1_native_panel.py summary OUT.jsonl SUMMARY.json

run: checks the T7 seal (sealed code and PES hashes; the T7 jobs themselves are not used), rebuilds the panel with
     the D0 code (tools/c1b1_dot_d0.panel) and requires it to equal the inputs recorded in the D0 results file, and
     requires no panel start state to equal a T7 start state. Rows (one per input and engine) are appended to OUT.
     The sha256 of the files under test (native source, wrapper, reference track, force, this tool) is written to
     OUT.manifest.json; track.cpp must be an allowed source (C3a e71293f2..., or the committed C3b-1 source; hashes on
     LF-normalised bytes). ENGINES (default py,native) may be 'native' alone (C3b-1 replay against the C3a-4 Python
     rows, tools/c1b1_c3b_compare.py). OUT must be a new file (rows are appended;
     a rerun into the same file makes `summary` stop on duplicate rows).
summary: pairs py/native rows per input. Verdict IDENTICAL / DIFFERENT / UNRESOLVED (either side refused) / ERROR
     (an error, or a missing row). Both sides stopping with the same 'no exit' message counts as IDENTICAL (status
     no_exit); any other no_exit pairing is DIFFERENT or ERROR. Needs no project import.
"""
import hashlib
import importlib.util
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

D0_SHA256 = '3a2acae7bebdc1ec'
TRACK_CPP_SHA256 = 'e71293f22748f9c7'                 # C3a (C3a-4 ran with this)
TRACK_CPP_ALLOWED = {TRACK_CPP_SHA256: 'C3a', 'a3d7098f0ae51f64': 'C3b-1'}
UNDER_TEST = ['c1b1_native/track.cpp', 'c1b1_native/track.py', 'c1b1_native/reference.py', 'c1b1_native/build.py',
              'c1b1_t7/lang_fx2.py', 'tools/c1b1_native_panel.py', 'tools/c1b1_dot_d0.py']
ENGINES = ('py', 'native')
PANEL_IDS = ['G1', 'G2', 'G3', 'G4', 'G5', 'G6', 'B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'H1', 'H2']
VERIFY_KEYS = {'ref_sweep', 'ref_time', 'err_sweep', 'd_sweep', 'err_time', 'cpu_s'}
WORLD_KEYS = ('status', 'j_out', 'bits_out', 'out', 'out_base', 'pairs', 'level0', 'substeps', 'world_kdk')


# ------------------------------------------------------------------ pure part (summary; no project import)
def strip(d):
    if isinstance(d, dict):
        return {k: strip(v) for k, v in d.items() if k not in VERIFY_KEYS}
    if isinstance(d, list):
        return [strip(v) for v in d]
    return d


def world(res):
    """World layer of a pen_state result plus world_kdk (same selection as tools/c1b1_pen_fx_replay.world)."""
    out = {k: strip(res.get(k)) for k in WORLD_KEYS}
    out['track_substeps'] = [[t['j'], t['extra'], t['substeps']] for t in res.get('track_cost', [])]
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


def classify(py, nat):
    """Verdict for one input from its py row and native row (either may be None = missing)."""
    if py is None or nat is None:
        return dict(verdict='ERROR', reason='missing row: ' + ('py' if py is None else 'native'))
    kinds = (py['kind'], nat['kind'])
    if 'error' in kinds:
        return dict(verdict='ERROR', reason=f'error row(s): py={py["kind"]} native={nat["kind"]}')
    if 'refused' in kinds:
        return dict(verdict='UNRESOLVED', reason=f'refusal: py={py["kind"]} native={nat["kind"]}')
    if 'no_exit' in kinds:
        same = kinds == ('no_exit', 'no_exit') and py['message'] == nat['message']
        return dict(verdict='IDENTICAL' if same else 'DIFFERENT', status='no_exit',
                    reason=f'no exit: py={py.get("message", py["kind"])} native={nat.get("message", nat["kind"])}')
    diffs = diff_paths(py['world'], nat['world'])
    kicks_equal = py['kicks'] == nat['kicks']
    v = dict(verdict='IDENTICAL' if not diffs and kicks_equal else 'DIFFERENT', n_diffs=len(diffs),
             diffs=diffs[:20], kicks_equal=kicks_equal)
    v['status'], v['j_out'] = py['world']['status'], py['world']['j_out']
    return v


def summary(rows_path, out_path):
    rows = {}
    for line in open(rows_path, encoding='utf-8'):
        r = json.loads(line)
        key = (r['id'], r['engine'])
        if key in rows:
            raise ValueError(f'duplicate row {key}')
        rows[key] = r
    per, counts = {}, {}
    for i in PANEL_IDS:
        py, nat = rows.get((i, 'py')), rows.get((i, 'native'))
        v = classify(py, nat)
        if py and nat and py['kind'] == nat['kind'] == 'ok':
            v.update(py_pen_cpu_s=py['pen_cpu_s'], native_pen_cpu_s=nat['pen_cpu_s'],
                     pen_ratio=py['pen_cpu_s'] / nat['pen_cpu_s'] if nat['pen_cpu_s'] else None,
                     py_kdk_cpu_s=py['kdk_cpu_s'], native_kdk_cpu_s=nat['kdk_cpu_s'], kicks=py['kicks'],
                     substeps=py['world']['substeps'])
        per[i] = v
        counts[v['verdict']] = counts.get(v['verdict'], 0) + 1
    extra = sorted(k for k in rows if k[0] not in PANEL_IDS or k[1] not in ENGINES)
    man = Path(str(rows_path) + '.manifest.json')
    res = dict(rows_sha256=hashlib.sha256(Path(rows_path).read_bytes()).hexdigest(), counts=counts, per_input=per,
               unexpected_rows=[list(k) for k in extra],
               manifest=json.loads(man.read_text(encoding='utf-8')) if man.exists() else None)
    Path(out_path).write_text(json.dumps(res, indent=1), encoding='utf-8')
    print(json.dumps(counts), flush=True)
    return res


# ------------------------------------------------------------------ run part (project imports inside functions)
def _load_tool(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'tools' / file)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def run_world(raw, engine, binary, tol='1e-9', j_max=6):
    import mpmath as mm

    import c1b1_t7.ladder as L
    from c1b1_method_bench.ladder2 import DPS
    from c1b1_native import track
    from c1b1_native.reference import PyOneTrack
    from c1b1_t7.lang_fx2 import LangForceFX2
    from c1b1_t7.state import MU, relative
    cls = {'py': PyOneTrack, 'native': track.NativeTrack}[engine]
    if engine == 'native':
        track.configure(binary)
    pot = LangForceFX2()
    with mm.workdps(DPS):
        q0, p0 = relative([int(x) for x in raw])
        mu = mm.mpf(MU.numerator) / MU.denominator
    cpu = (lambda: time.process_time() + track.child_cpu_s()) if engine == 'native' else time.process_time
    orig = L.FxTrackX
    L.FxTrackX = cls                                    # sealed pen_state looks this name up when it runs
    try:
        c0 = cpu()
        res = L.pen_state(pot, q0, p0, tol, j_max=j_max, mu=mu, mu_exact=MU)
        res['pen_cpu_s'] = cpu() - c0
        with mm.workdps(DPS):
            w = cls(pot, q0, p0, 0, 'kdk', 48, 80, mu, 40, MU)
            c1 = cpu()
            w.run_to_exit(300_000)
            res['world_kdk'] = w.state()
            res['world_kdk']['cpu_s'] = cpu() - c1
        res['kicks'] = (sum(t.kicks for t in list(track._LIVE)) if engine == 'native' else pot.evaluations)
    finally:
        L.FxTrackX = orig
        track.close_all()
    return res


def one(args):
    pid, engine, raw, binary = args
    from c1b1_method_bench.fixedpoint import Undecided
    from c1b1_native.track import NativeRefused
    t0, w0 = time.process_time(), time.perf_counter()
    try:
        res = run_world(raw, engine, binary)
        row = dict(id=pid, engine=engine, kind='ok', world=world(res), kicks=res['kicks'],
                   pen_cpu_s=res['pen_cpu_s'], kdk_cpu_s=res['world_kdk']['cpu_s'])
    except (Undecided, NativeRefused) as exc:
        row = dict(id=pid, engine=engine, kind='refused', refusal=f'{type(exc).__name__}: {exc}'[:300])
    except RuntimeError as exc:
        msg = str(exc)
        if type(exc) is RuntimeError and msg.startswith('level ') and ': no exit within ' in msg:
            row = dict(id=pid, engine=engine, kind='no_exit', message=msg[:300])
        else:
            row = dict(id=pid, engine=engine, kind='error', error=repr(exc)[:300])
    except Exception as exc:                                          # recorded, never hidden
        row = dict(id=pid, engine=engine, kind='error', error=repr(exc)[:300])
    row.update(cpu_s=time.process_time() - t0, wall_s=time.perf_counter() - w0)
    return row


def order_key(job, panel):
    """Python before native, smallest |rho| first (the long jobs start early); order never changes a result."""
    from fractions import Fraction as Q
    rho = panel[job[0]]['rho']
    return (ENGINES.index(job[1]), abs(Q(rho)) if rho else Q(1), job[0])


def run(t7_inputs, fixture_path, d0_path, out, workers=6, ids=None, engines=ENGINES):
    from c1b1_method_bench.runner import run_jobs
    from c1b1_native.build import build
    from c1b1_t7.lang import reference_potential
    t7 = _load_tool('t7argon', 'c1b1_t7_argon.py')
    d0 = _load_tool('dotd0', 'c1b1_dot_d0.py')
    if Path(out).exists():
        raise FileExistsError(f'{out} exists; use a new file (failed-run files are kept as originals)')
    shas = {f: hashlib.sha256((ROOT / f).read_bytes().replace(b'
', b'
')).hexdigest() for f in UNDER_TEST}
    if shas['c1b1_native/track.cpp'][:16] not in TRACK_CPP_ALLOWED:
        raise ValueError('track.cpp is not an allowed source (C3a e71293f2... or C3b-1)')
    payload = t7.load(t7_inputs)                                      # T7 seal: sealed code + PES unchanged
    if hashlib.sha256(Path(d0_path).read_bytes()).hexdigest()[:16] != D0_SHA256:
        raise ValueError('D0 results file hash mismatch')
    panel = d0.panel(json.loads(Path(fixture_path).read_bytes()), reference_potential())
    recorded = json.loads(Path(d0_path).read_bytes())['inputs']
    for k in PANEL_IDS:
        if [str(x) for x in panel[k]['raw']] != recorded[k]['raw']:
            raise ValueError(f'panel input {k} differs from the D0 record')
    t7_raws = {json.dumps([str(x) for x in j['raw']]) for j in payload['jobs']}
    if any(json.dumps([str(x) for x in panel[k]['raw']]) in t7_raws for k in PANEL_IDS):
        raise ValueError('a panel start state equals a T7 start state (holdout)')
    binary = str(build('-O2'))
    chosen = PANEL_IDS if ids is None else ids.split(',')
    if not set(engines) <= set(ENGINES) or not engines:
        raise ValueError(f'engines {engines}')
    work = sorted(((k, e, [str(x) for x in panel[k]['raw']], binary) for k in chosen for e in engines),
                  key=lambda job: order_key(job, panel))
    from c1b1_t7.lang import pes_path
    Path(str(out) + '.manifest.json').write_text(json.dumps(dict(
        under_test_sha256=shas, track_source=TRACK_CPP_ALLOWED[shas['c1b1_native/track.cpp'][:16]],
        engines=list(engines), t7_inputs_payload_sha256=t7.digest(payload), d0_sha256_prefix=D0_SHA256,
        fixture_sha256=hashlib.sha256(Path(fixture_path).read_bytes()).hexdigest(),
        pes_sha256=hashlib.sha256(pes_path().read_bytes()).hexdigest(), binary=binary, ids=chosen,
        python=sys.version.split()[0]), indent=1), encoding='utf-8')
    print('manifest written; binary', binary, flush=True)
    run_jobs(one, work, out, workers=workers, label='C3a-4 panel ')


if __name__ == '__main__':
    a = sys.argv
    if len(a) > 1 and a[1] == 'run':
        run(a[2], a[3], a[4], a[5], int(a[6]) if len(a) > 6 else 6, (a[7] or None) if len(a) > 7 else None,
            tuple(a[8].split(',')) if len(a) > 8 else ENGINES)
    elif len(a) > 1 and a[1] == 'summary':
        summary(a[2], a[3])
    else:
        raise SystemExit(__doc__)
