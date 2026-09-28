"""C1-B1 runtime stress: WHERE and WHY decisions need 256 bits (survey_only).

The campaign (c1b1_stress_campaign) counted decisions by precision: ~0.645% need 256 bits, almost independent of energy,
impact parameter, orbiting distance, trajectory length and D_valid status; none needed 512+. This driver re-runs a
subset with the read-only per-decision profile of c1b1_stress_survey and records, for every decision:

  * the final precision M and the axis of the impulse component,
  * the separation R (0.5 bohr bins),
  * w128 = log2 of the 128-bit enclosure width in output ulps (FX(96,80): ulp = 2^-80),
  * d = log2 of the distance of the final enclosure midpoint from the nearest rounding boundary, in ulps,
  * the final enclosure width, and the single decision whose midpoint came nearest a boundary ("hardest").

A decision needs 256 bits exactly when a rounding boundary falls inside its 128-bit enclosure. If the exact values sit
at no special place relative to the boundaries, P(256 | w128) ~ 2^w128, and P(512 | 256) ~ 2^w256. This is a heuristic
reading, not a proof: the rational structure that the hard-case search looked for is precisely the non-random case.

Stages kept apart: hard_case (61,936 single impulses), fixed (the campaign's fixed categories), stream (items 1..N).
Nothing here changes the executor, a certificate, coverage or D_valid.
"""
from __future__ import annotations

import json
import sys
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from fractions import Fraction as Q
from pathlib import Path

import a_reference.c1b1_stress_campaign as K
import a_reference.c1b1_stress_survey as X
import a_reference.c1b1_two_atom as C

VERSION = 'c1b1-stress-profile-v0'


def _traj_job(sp):
    r = X.run_trajectory(sp, telemetry=True, profile=True)
    r.pop('final_raw', None)
    return r


def _stream_job(i):
    sp = K.stream_spec(i)
    if 'spec_error' in sp:
        return {'item': i, 'end': 'spec_error', 'spec_error': sp['spec_error'], 'label': sp['label']}
    r = _traj_job(sp)
    r['item'] = i
    return r


def _point_job(args):
    shell, n = args
    tel = X.Telemetry()
    tel.profile = True
    rec = {'shell': shell, 'n': str(n)}
    try:
        with X.instrumented(tel):
            C.impulse((Q(n, 1 << 48), Q(0), Q(0)), X.DT / 2, X.MOM)
        rec['end'] = 'decided'
    except Exception as exc:              # noqa: BLE001
        rec['end'] = X.classify(exc)
        rec['exception'] = f'{type(exc).__name__}: {exc}'
    rec['decisions'] = {str(k): v for k, v in tel.decisions.items()}
    rec['profile'] = X.profile_dump(tel)
    return rec


def combine(recs):
    """Merge per-record profiles into tables (bins keyed [M, axis, R_bin, w128, d_log2])."""
    bins, wfinal = Counter(), Counter()
    hardest = []
    for r in recs:
        p = r.get('profile')
        if not p:
            continue
        for k, v in p['bins']:
            bins[tuple(k)] += v
        for k, v in p['wfinal']:
            wfinal[tuple(k)] += v
        if p['hardest']:
            hardest.append({'label': r.get('label', f"shell {r.get('shell')} n={r.get('n')}"),
                            'kind': r.get('kind', 'hard_case'), **p['hardest']})

    def table(index):
        t = {}
        for k, v in bins.items():
            row = t.setdefault(str(k[index]), Counter())
            row[str(k[0])] += v
        out = {}
        for key, c in t.items():
            n = sum(c.values())
            out[key] = {'decisions': n, 'by_M': dict(c), 'p256_percent': 100 * c.get('256', 0) / n}
        return dict(sorted(out.items(), key=lambda kv: (len(kv[0]), kv[0])))

    hardest.sort(key=lambda h: Q(h['d']))
    return {'decisions': sum(bins.values()), 'by_axis': table(1), 'by_R_bin_half_bohr': table(2),
            'by_w128_log2': table(3), 'by_d_log2': table(4),
            'final_width_log2_by_M': {f'{m}': dict(sorted(Counter({w: v for (mm, w), v in wfinal.items()
                                                                  if mm == m}).items(), key=lambda kv: kv[0]))
                                      for m in sorted({m for m, _ in wfinal})},
            'hardest_10': hardest[:10]}


OUTGOING_CAP = 12_000_000


def outgoing_specs():
    """Outgoing flight to R_J (the zero-impulse radius, 10240 bohr): the pre-tail shells 0..26 that the stress
    campaign never entered (it stopped on returning to R = 20 bohr)."""
    import a_reference.c1b1_inner_validation as I
    import a_reference.c1b1_outer_bootstrap as O
    rj = O.zero_impulse_radius()
    out = []
    for e in (Q(1, 2), Q(1), Q(2), Q(5), Q(9)):
        for bf in (Q(1, 2), Q(3, 2)):
            out.append(dict(X.spec('outgoing', f'e={e} b={bf}Re', X.canonical(e, bf * X.RE), OUTGOING_CAP),
                            stop_R=str(rj)))
    for e in (Q(2), Q(9)):
        out.append(dict(X.spec('outgoing', f'e={e} b=0', X.canonical(e, Q(0)), OUTGOING_CAP), stop_R=str(rj)))
    bo = I.orbiting_b(Q(1, 2), K.B_MAX_FRAC * X.RE)
    for sign in (-1, 1):
        out.append(dict(X.spec('outgoing', f'e=1/2 rho={sign}e-6', X.canonical(Q(1, 2), bo * (1 + sign * Q(1, 10 ** 6))),
                               OUTGOING_CAP), stop_R=str(rj)))
    return out


def run_outgoing(out: Path, workers: int, log):
    specs = outgoing_specs()
    t0 = time.perf_counter()
    recs = []
    with ProcessPoolExecutor(min(workers, len(specs))) as pool:
        for r in pool.map(_traj_job, specs, chunksize=1):
            recs.append(r)
            log(f"outgoing {r['label']}: end={r['end']} steps={r.get('steps')} wall={r['wall_seconds']:.0f}s "
                f"dist={r['decisions']} hot={len(r['hot'])}")
    res = {'version': VERSION, 'stage': 'outgoing', 'trajectories': len(recs),
           'wall_seconds': time.perf_counter() - t0, 'ends': dict(Counter(r['end'] for r in recs)),
           'precision': X.precision_distribution(recs), 'all': combine(recs),
           'records': [{k: v for k, v in r.items() if k != 'profile'} for r in recs],
           'per_trajectory': {r['label']: combine([r]) for r in recs}}
    _dump(out / 'profile_outgoing.json', res)
    log(f'outgoing done {res["wall_seconds"]:.0f}s ends={res["ends"]} dist={res["precision"]["by_precision"]}')


def _dump(path: Path, obj):
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(obj, separators=(',', ':'), default=str) + '\n', encoding='utf-8')
    tmp.replace(path)


def main(out_dir: str, workers: int, stream_items: int):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    def log(m):
        print(f'[{time.strftime("%Y-%m-%d %H:%M:%S")}] {m}', flush=True)

    log(f'{VERSION} start workers={workers} stream_items={stream_items}')
    if not (out / 'profile_hard_case.json').exists():
        t0 = time.perf_counter()
        with ProcessPoolExecutor(workers) as pool:
            recs = list(pool.map(_point_job, X.hard_case_points(), chunksize=64))
        res = {'version': VERSION, 'stage': 'hard_case', 'points': len(recs), 'wall_seconds': time.perf_counter() - t0,
               'ends': dict(Counter(r['end'] for r in recs)), 'precision': X.precision_distribution(recs),
               'by_shell': {s: combine([r for r in recs if r['shell'] == s]) for s in (15, 16, 17, 18)},
               'all': combine(recs)}
        _dump(out / 'profile_hard_case.json', res)
        log(f'hard_case {len(recs)} {res["wall_seconds"]:.0f}s ends={res["ends"]} '
            f'w128={ {k: v["decisions"] for k, v in res["all"]["by_w128_log2"].items()} }')
    if not (out / 'profile_fixed.json').exists():
        specs = [s for s in K.fixed_specs() if 'spec_error' not in s]
        specs, dropped = X.dedupe(specs)
        t0 = time.perf_counter()
        with ProcessPoolExecutor(workers) as pool:
            recs = list(pool.map(_traj_job, specs, chunksize=1))
        res = {'version': VERSION, 'stage': 'fixed', 'trajectories': len(recs), 'dropped_duplicates': dropped,
               'wall_seconds': time.perf_counter() - t0, 'ends': dict(Counter(r['end'] for r in recs)),
               'precision': X.precision_distribution(recs), 'all': combine(recs),
               'by_kind': {k: combine([r for r in recs if r['kind'] == k]) for k in sorted({r['kind'] for r in recs})},
               'by_dvalid': {k: combine([r for r in recs if str(r.get('d_valid')) == k])
                             for k in sorted({str(r.get('d_valid')) for r in recs})}}
        _dump(out / 'profile_fixed.json', res)
        log(f'fixed {len(recs)} {res["wall_seconds"]:.0f}s ends={res["ends"]} '
            f'dist={res["precision"]["by_precision"]}')
    if stream_items and not (out / 'profile_stream.json').exists():
        t0 = time.perf_counter()
        with ProcessPoolExecutor(workers) as pool:
            recs = list(pool.map(_stream_job, range(1, stream_items + 1), chunksize=1))
        ok = [r for r in recs if r['end'] != 'spec_error']
        res = {'version': VERSION, 'stage': 'stream', 'items': [1, stream_items], 'trajectories': len(ok),
               'spec_errors': [r for r in recs if r['end'] == 'spec_error'],
               'wall_seconds': time.perf_counter() - t0, 'ends': dict(Counter(r['end'] for r in ok)),
               'precision': X.precision_distribution(ok), 'all': combine(ok),
               'by_kind': {k: combine([r for r in ok if r['kind'] == k]) for k in sorted({r['kind'] for r in ok})},
               'by_dvalid': {k: combine([r for r in ok if str(r.get('d_valid')) == k])
                             for k in sorted({str(r.get('d_valid')) for r in ok})}}
        _dump(out / 'profile_stream.json', res)
        log(f'stream {len(ok)} {res["wall_seconds"]:.0f}s ends={res["ends"]} dist={res["precision"]["by_precision"]}')
    log('profile exit')


if __name__ == '__main__':
    if len(sys.argv) > 3 and sys.argv[3] == 'outgoing':
        o = Path(sys.argv[1])
        o.mkdir(parents=True, exist_ok=True)
        run_outgoing(o, int(sys.argv[2]), lambda m: print(f'[{time.strftime("%Y-%m-%d %H:%M:%S")}] {m}', flush=True))
    else:
        main(sys.argv[1], int(sys.argv[2]), int(sys.argv[3]) if len(sys.argv) > 3 else 1024)
