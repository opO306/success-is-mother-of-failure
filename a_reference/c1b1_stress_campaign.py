"""C1-B1 runtime stress campaign (survey_only): the wide "real drive" after the 40-trajectory smoke.

Runs the UNCHANGED executor through a_reference.c1b1_stress_survey (observe-only instrumentation) in stages:

  overhead   telemetry on/off wall ratio, measured in FRESH worker processes after a warm-up and interleaved
             (the smoke's 0.60 was invalid: per-process constant caches warmed by whichever run came first)
  fixed      the designer's categories: head-on, near head-on, weak (large b), strong (near 10 De), the admission
             boundary E_rel = 10 De (nearest stored states on both sides, real check), long orbiting on BOTH sides of
             the orbiting boundary, the D_valid measured energies, and symmetry transforms of a few bases
  hard_case  all 61,936 shell 15-18 candidate points, one impulse each, kept apart from trajectory statistics
  stream     an endless deterministic stream (Halton sequence, exact rationals, no randomness) over
             e in (0, 10) De x b in [0, 2.75 Re) and over the orbiting boundary (both signs, rho down to 1e-25),
             written chunk by chunk until a STOP file appears in the output directory

Nothing here is a certification, nothing changes the executor, D_valid, a certificate or coverage. Results are
kept apart by D_valid status (numerical_validated vs everything else inside the integrator contract) and never
averaged together; hard-case points never enter the trajectory histogram.
"""
from __future__ import annotations

import json
import multiprocessing as mp
import os
import statistics
import sys
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from fractions import Fraction as Q
from pathlib import Path

import a_reference.c1b1_inner_validation as I
import a_reference.c1b1_stress_survey as X
import a_reference.c1b1_two_atom as C

VERSION = 'c1b1-stress-campaign-v0'
B_MAX_FRAC = Q(11, 4)                     # b < 2.75 Re ~ 19.56 bohr: below R_START = 20 so the inbound state exists
E_MAX = Q(10)                             # integrator contract E_rel <= 10 De (states above are refused at admission)
SCATTER_CAP = 100_000                     # smoke maximum was 29,685 steps
ORBIT_CAP = 1_000_000                     # long orbiting: the cap is recorded as end='step_cap', never as success
DVALID_ENERGIES = [Q(3, 20), Q(1, 5), Q(3, 10), Q(1, 2), Q(7, 10), Q(9, 10), Q(99, 100)]
CHUNK = 256


# ---------------------------------------------------------------------------------------------------------------------
# deterministic parameter sequences (exact rationals)
# ---------------------------------------------------------------------------------------------------------------------

def halton(i: int, base: int) -> Q:
    """Radical inverse of i >= 1 in `base`, exact: the base digits of i mirrored behind the point."""
    num, den = 0, 1
    while i:
        i, d = divmod(i, base)
        num, den = num * base + d, den * base
    return Q(num, den)


def _safe(fn, *args):
    try:
        return fn(*args)
    except Exception as exc:              # noqa: BLE001 -- a parameter the canonical generator cannot build is recorded
        return {'spec_error': f'{type(exc).__name__}: {exc}', 'args': [str(a) for a in args]}


def _spec(kind, label, e, b, cap, transform=None):
    st = _safe(X.canonical, e, b)
    if 'spec_error' in st:
        return {'kind': kind, 'label': label, 'spec_error': st['spec_error']}
    return X.spec(kind, label, st, cap, transform)


def orbit_b(e: Q):
    """b_orb (bohr) when an orbiting boundary exists at e De and fits below the start separation, else None."""
    return I.orbiting_b(Q(e), B_MAX_FRAC * X.RE)


# ---------------------------------------------------------------------------------------------------------------------
# fixed categories
# ---------------------------------------------------------------------------------------------------------------------

def fixed_specs():
    re = X.RE
    out = []
    for e in (Q(1, 100), Q(1, 20), Q(1, 10), Q(1, 4), Q(1, 2), Q(1), Q(2), Q(3), Q(5), Q(7), Q(9), Q(99, 10),
              Q(999, 100)):
        out.append(_spec('headon', f'e={e} b=0', e, Q(0), SCATTER_CAP))
    for e in (Q(1, 10), Q(1, 2), Q(2), Q(9)):
        for bf in (Q(1, 10 ** 9), Q(1, 10 ** 6), Q(1, 10 ** 3), Q(1, 100), Q(1, 20)):
            out.append(_spec('near_headon', f'e={e} b={bf}Re', e, bf * re, SCATTER_CAP))
    for e in (Q(1, 100), Q(1, 10), Q(1, 2), Q(2), Q(9)):
        for bf in (Q(3, 2), Q(2), Q(5, 2), Q(11, 4) - Q(1, 100)):
            out.append(_spec('weak', f'e={e} b={bf}Re', e, bf * re, SCATTER_CAP))
    for e in (Q(9), Q(19, 2), Q(99, 10), Q(999, 100), Q(9999, 1000)):
        for bf in (Q(0), Q(1, 4), Q(1, 2), Q(1), Q(3, 2)):
            out.append(_spec('strong', f'e={e} b={bf}Re', e, bf * re, SCATTER_CAP))
    for e in DVALID_ENERGIES:
        for bf in (Q(0), Q(1, 4), Q(1, 2), Q(3, 4), Q(1), Q(5, 4), Q(3, 2), Q(7, 4), Q(2)):
            out.append(_spec('dvalid_band', f'e={e} b={bf}Re', e, bf * re, SCATTER_CAP))
    for e in (Q(1, 100), Q(1, 20), Q(1, 10), Q(1, 4), Q(1, 2), Q(3, 4), Q(9, 10), Q(99, 100)):
        bo = _safe(orbit_b, e)
        if bo is None or isinstance(bo, dict):
            out.append({'kind': 'orbit', 'label': f'e={e} (no orbiting b below {B_MAX_FRAC}Re)',
                        'spec_error': 'no_orbiting_boundary' if bo is None else bo['spec_error']})
            continue
        for k in (2, 4, 6, 9, 12, 16, 20, 25):
            for sign in (-1, 1):
                out.append(_spec('orbit', f'e={e} rho={sign}e-{k}', e, bo * (1 + sign * Q(1, 10 ** k)), ORBIT_CAP))
    bases = [s for s in out if 'spec_error' not in s and s['label'] in
             ('e=1/2 b=0', 'e=9 b=1/2Re', 'e=1/10 b=2Re', 'e=1/2 b=1/2Re', 'e=99/10 b=1/4Re')]
    for b in bases:
        for t in ('swap_xy', 'mirror_x', 'swap_atoms'):
            out.append(dict(b, kind='symmetry', transform=t, label=b['label'] + ' ' + t, base_kind=b['kind']))
    return out


def boundary_specs(b_fracs=(Q(0), Q(1, 4), Q(1, 2), Q(1), Q(3, 2), Q(2), Q(5, 2))):
    """Admission boundary E_rel = 10 De: the stored state just inside runs; the one just outside must be refused."""
    out, records = [], []
    for bf in b_fracs:
        try:
            br = X.admission_bracket(bf)
        except Exception as exc:          # noqa: BLE001
            records.append({'b_frac': str(bf), 'error': f'{type(exc).__name__}: {exc}'})
            continue
        st = br['outside']
        try:
            C.new_run(X.POS, X.DT, st['r_i'], st['p_i'], st['r_j'], st['p_j'], momentum_profile=X.MOM)
            refused = 'NOT_REFUSED'
        except Exception as exc:          # noqa: BLE001
            refused = X.classify(exc)
        records.append({'b_frac': br['b_frac'], 'inside_E_over_De': br['inside_E_over_De'],
                        'outside_E_over_De': br['outside_E_over_De'], 'outside_result': refused,
                        'nominal_e_gap': br['nominal_e_gap']})
        out.append(X.spec('energy_limit', f'10De inside b={bf}Re', br['inside'], SCATTER_CAP))
    return out, records


# ---------------------------------------------------------------------------------------------------------------------
# endless stream
# ---------------------------------------------------------------------------------------------------------------------

def stream_spec(i: int):
    """Stream item i >= 1. Three of every four items are scatter states over (e, b); one is an orbiting-boundary
    state. e = 10 u^2 puts more states at low energy; all parameters are exact rationals from Halton sequences."""
    if i % 4:
        u, v = halton(i, 2), halton(i, 3)
        e = E_MAX * u * u
        if e == 0:
            e = Q(1, 10 ** 4)
        b = B_MAX_FRAC * X.RE * v
        return _spec('stream_scatter', f'#{i} e={e} b={b}', e, b, SCATTER_CAP)
    u, v, w = halton(i, 5), halton(i, 7), halton(i, 11)
    e = Q(1, 100) + (Q(99, 100) - Q(1, 100)) * u          # orbiting exists only below ~0.9964 De
    rho = Q(1, 10 ** (2 + int(23 * v)))                     # 1e-2 .. 1e-24
    sign = 1 if w < Q(1, 2) else -1
    bo = _safe(orbit_b, e)
    if bo is None or isinstance(bo, dict):
        return {'kind': 'stream_orbit', 'label': f'#{i} e={e}', 'spec_error':
                'no_orbiting_boundary' if bo is None else bo['spec_error']}
    return _spec('stream_orbit', f'#{i} e={e} rho={sign}*{rho}', e, bo * (1 + sign * rho), ORBIT_CAP)


# ---------------------------------------------------------------------------------------------------------------------
# overhead (fresh processes, warm-up, interleaved)
# ---------------------------------------------------------------------------------------------------------------------

def _overhead_job(sp):
    warm = dict(sp, max_steps=50)
    X.run_trajectory(warm, telemetry=False)
    X.run_trajectory(warm, telemetry=True)
    walls = {'off': [], 'on': []}
    same = True
    ref = None
    for mode in ('off', 'on', 'off', 'on', 'off', 'on'):
        r = X.run_trajectory(sp, telemetry=(mode == 'on'))
        walls[mode].append(r['wall_seconds'])
        key = (r['end'], r['steps'], r.get('final_raw'))
        ref = ref or key
        same = same and key == ref
    return {'label': sp['label'], 'off': walls['off'], 'on': walls['on'],
            'ratio_median': statistics.median(walls['on']) / statistics.median(walls['off']), 'same_results': same}


def measure_overhead(specs, workers):
    ctx = mp.get_context('spawn')
    with ProcessPoolExecutor(min(workers, len(specs)), mp_context=ctx, max_tasks_per_child=1) as pool:
        rows = list(pool.map(_overhead_job, specs))
    return {'method': 'fresh spawn process per trajectory, warm-up 50 steps both modes, then off/on x3 interleaved',
            'rows': rows, 'ratio_median_of_medians': statistics.median(r['ratio_median'] for r in rows),
            'all_same_results': all(r['same_results'] for r in rows)}


# ---------------------------------------------------------------------------------------------------------------------
# running a set of specs
# ---------------------------------------------------------------------------------------------------------------------

def run_specs(specs, workers, log):
    runnable = [s for s in specs if 'spec_error' not in s]
    errors = [s for s in specs if 'spec_error' in s]
    runnable, dropped = X.dedupe(runnable)
    recs = []
    t0 = time.perf_counter()
    with ProcessPoolExecutor(workers) as pool:
        futs = {pool.submit(X._job, (sp, True)): sp for sp in runnable}
        for k, f in enumerate(as_completed(futs), 1):
            r = f.result()
            r.pop('final_raw', None)
            if 'base_kind' in futs[f]:
                r['base_kind'] = futs[f]['base_kind']
            recs.append(r)
            if k % 64 == 0 or k == len(runnable):
                log(f'  {k}/{len(runnable)} done ({time.perf_counter() - t0:.0f}s)')
    recs.sort(key=lambda r: (r['kind'], r['label'], str(r['transform'])))
    return {'records': recs, 'spec_errors': errors, 'dropped_duplicates': dropped,
            'wall_seconds': time.perf_counter() - t0}


def aggregate(recs):
    by_dvalid = {}
    for r in recs:
        by_dvalid.setdefault('numerical_validated' if r.get('d_valid') == 'numerical_validated'
                             else f"not_dvalid:{r.get('d_valid')}", []).append(r)
    hot = [{'kind': r['kind'], 'label': r['label'], 'transform': r['transform'], **h}
           for r in recs for h in r.get('hot', [])]
    s = X.summarize(recs)
    s.pop('steps_distribution'), s.pop('wall_seconds_distribution')
    return {'summary': s, 'precision_all': X.precision_distribution(recs),
            'precision_by_dvalid': {k: X.precision_distribution(v) for k, v in sorted(by_dvalid.items())},
            'hot_decisions': hot, 'max_steps_seen': max((r.get('steps', 0) for r in recs), default=0),
            'step_cap_hits': [r['label'] for r in recs if r['end'] == 'step_cap']}


def _dump(path: Path, obj):
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(obj, separators=(',', ':'), default=str) + '\n', encoding='utf-8')
    tmp.replace(path)


def _merge_totals(out: Path):
    """Running totals over every finished file, kept apart by stage and by D_valid status."""
    totals = {}
    for p in sorted(out.glob('*.json')):
        if p.name in ('totals.json',) or p.name.startswith('overhead') or p.name.startswith('hard_case'):
            continue
        d = json.loads(p.read_text(encoding='utf-8'))
        stage = 'stream' if p.name.startswith('stream_') else p.stem
        t = totals.setdefault(stage, {'files': 0, 'trajectories': 0, 'steps': 0, 'decisions': Counter(),
                                      'by_dvalid': {}, 'ends': Counter(), 'hot': 0, 'failure_candidates': 0})
        a = d['aggregate']
        t['files'] += 1
        t['trajectories'] += a['summary']['trajectories']
        t['steps'] += a['summary']['steps']
        t['ends'].update(a['summary']['ends'])
        t['decisions'].update(a['precision_all']['by_precision'])
        t['hot'] += len(a['hot_decisions'])
        t['failure_candidates'] += len(a['summary']['failure_candidates'])
        for k, v in a['precision_by_dvalid'].items():
            t['by_dvalid'].setdefault(k, Counter()).update(v['by_precision'])
        keys = [r['state_key'] for r in d['records'] if 'state_key' in r]
        t.setdefault('_keys', Counter()).update(keys)
    for t in totals.values():
        t['cross_file_duplicate_states'] = sum(c - 1 for c in t.pop('_keys', Counter()).values() if c > 1)
    return totals


def main(out_dir: str, workers: int, stages: str, max_chunks: int | None = None):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    logf = open(out / 'campaign.log', 'a', encoding='utf-8')

    def log(m):
        line = f'[{time.strftime("%Y-%m-%d %H:%M:%S")}] {m}'
        print(line, flush=True)
        logf.write(line + '\n')
        logf.flush()

    log(f'{VERSION} start workers={workers} stages={stages} pid={os.getpid()}')
    want = stages.split(',')
    if 'overhead' in want and not (out / 'overhead.json').exists():
        sps = [_spec('overhead', f'e={e} b={bf}Re', e, bf * X.RE, SCATTER_CAP)
               for e, bf in ((Q(1, 2), Q(1, 2)), (Q(2), Q(0)), (Q(1, 10), Q(1)), (Q(9), Q(1, 4)))]
        ov = measure_overhead(sps, workers)
        _dump(out / 'overhead.json', {'version': VERSION, **ov})
        log(f'overhead median ratio {ov["ratio_median_of_medians"]:.3f} same_results={ov["all_same_results"]}')
    if 'hard_case' in want and not (out / 'hard_case.json').exists():
        pts = X.hard_case_points()
        t0 = time.perf_counter()
        with ProcessPoolExecutor(workers) as pool:
            prec = list(pool.map(X._point_job, pts, chunksize=64))
        ends = Counter(p['end'] for p in prec)
        by_shell = {s: X.precision_distribution([p for p in prec if p['shell'] == s]) for s in (15, 16, 17, 18)}
        odd = [p for p in prec if p['end'] != 'decided' or any(k not in ('128', '256') for k in p['decisions'])]
        _dump(out / 'hard_case.json', {'version': VERSION, 'stage': 'hard_case', 'points': len(prec),
                                       'wall_seconds': time.perf_counter() - t0, 'ends': dict(ends),
                                       'precision': X.precision_distribution(prec), 'by_shell': by_shell,
                                       'not_decided_or_above_256': odd})
        log(f'hard_case {len(prec)} points {time.perf_counter() - t0:.0f}s ends={dict(ends)} '
            f'dist={X.precision_distribution(prec)["by_precision"]} odd={len(odd)}')
    if 'fixed' in want and not (out / 'fixed.json').exists():
        specs = fixed_specs()
        bspecs, brecords = boundary_specs()
        log(f'fixed: {len(specs)} + {len(bspecs)} boundary specs; boundary {[(b["b_frac"], b.get("outside_result", b.get("error"))) for b in brecords]}')
        res = run_specs(specs + bspecs, workers, log)
        res['admission_boundary'] = brecords
        res['aggregate'] = aggregate(res['records'])
        _dump(out / 'fixed.json', {'version': VERSION, 'stage': 'fixed', **res})
        log(f'fixed done {res["wall_seconds"]:.0f}s ends={res["aggregate"]["summary"]["ends"]} '
            f'dist={res["aggregate"]["precision_all"]["by_precision"]} hot={len(res["aggregate"]["hot_decisions"])}')
    if 'stream' in want:
        run_stream(out, workers, log, max_chunks)
    _dump(out / 'totals.json', _merge_totals(out))
    log('campaign exit')


def _stream_job(i: int) -> dict:
    """Build stream item i and run it inside the worker (building an orbiting state costs a bisection)."""
    t0 = time.perf_counter()
    sp = stream_spec(i)
    if 'spec_error' in sp:
        return {'item': i, 'kind': sp['kind'], 'label': sp['label'], 'end': 'spec_error',
                'spec_error': sp['spec_error'], 'decide_calls': 0, 'decisions': {}, 'wall_seconds': 0.0}
    r = run_trajectory_keyed(sp)
    r['item'] = i
    r['spec_seconds'] = time.perf_counter() - t0 - r['wall_seconds']
    return r


def run_trajectory_keyed(sp: dict) -> dict:
    r = X.run_trajectory(sp, telemetry=True)
    r.pop('final_raw', None)
    r['state_key'] = X.state_key(X._state(sp))
    return r


def run_stream(out: Path, workers: int, log, max_chunks: int | None):
    """One persistent pool; chunks complete out of order (a 1e6-step orbit does not hold 255 other items back).
    A chunk file is written when all its items are back. Duplicate stored states are dropped within a chunk (lowest
    item kept); duplicates across chunks are counted in totals.json, not dropped."""
    from concurrent.futures import FIRST_COMPLETED, wait
    done = {int(p.stem.split('_')[1]) for p in out.glob('stream_*.json')}
    groups, inflight, k_next, t_open = {}, {}, 0, {}
    stopping = False
    with ProcessPoolExecutor(workers) as pool:
        while True:
            if not stopping and (out / 'STOP').exists():
                stopping = True
                log(f'STOP file found: no new chunks; waiting for {len(inflight)} in-flight items')
            while not stopping and len(inflight) < 2 * workers and (max_chunks is None or k_next < max_chunks):
                if k_next in done:
                    k_next += 1
                    continue
                lo, hi = k_next * CHUNK + 1, (k_next + 1) * CHUNK
                groups[k_next] = []
                t_open[k_next] = time.perf_counter()
                for i in range(lo, hi + 1):
                    inflight[pool.submit(_stream_job, i)] = k_next
                log(f'stream chunk {k_next} opened: items {lo}..{hi}')
                k_next += 1
            if not inflight:
                break
            fin, _ = wait(list(inflight), timeout=60, return_when=FIRST_COMPLETED)
            for f in fin:
                k = inflight.pop(f)
                groups[k].append(f.result())
                if len(groups[k]) == CHUNK:
                    _finish_chunk(out, k, groups.pop(k), time.perf_counter() - t_open.pop(k), log)


def _finish_chunk(out: Path, k: int, recs: list, wall: float, log):
    recs.sort(key=lambda r: r['item'])
    errors = [r for r in recs if r['end'] == 'spec_error']
    seen, kept, dropped = set(), [], []
    for r in recs:
        if r['end'] == 'spec_error':
            continue
        if r['state_key'] in seen:
            dropped.append(r['label'])
            continue
        seen.add(r['state_key'])
        kept.append(r)
    a = aggregate(kept)
    _dump(out / f'stream_{k:05d}.json', {'version': VERSION, 'stage': 'stream', 'chunk': k,
                                         'items': [k * CHUNK + 1, (k + 1) * CHUNK], 'wall_seconds': wall,
                                         'records': kept, 'spec_errors': errors, 'dropped_duplicates': dropped,
                                         'aggregate': a})
    log(f'stream chunk {k} done {wall:.0f}s ends={a["summary"]["ends"]} dist={a["precision_all"]["by_precision"]} '
        f'hot={len(a["hot_decisions"])} spec_errors={len(errors)} dup={len(dropped)} max_steps={a["max_steps_seen"]}')
    _dump(out / 'totals.json', _merge_totals(out))


if __name__ == '__main__':
    main(sys.argv[1], int(sys.argv[2]), sys.argv[3] if len(sys.argv) > 3 else 'overhead,fixed,hard_case,stream',
         int(sys.argv[4]) if len(sys.argv) > 4 else None)
