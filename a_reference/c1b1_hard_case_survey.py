"""Driver for the ④-4c-5 shell-18 hard-case search survey (survey_only).

Runs the candidate generator (c1b1_hard_case_search) and the independent
checker (c1b1_hard_case_checker) and records costs. Every setting below is fixed
before the run. The search threshold is always the pinned guard G plus the
rigorous interpolation error; the brute-force windows use a larger stated
tau only to make the comparison non-vacuous.

No region, coverage, precision cap or ④-4b status changes. Shell 18 results
are not extended to shells 0-17.
"""
from concurrent.futures import ProcessPoolExecutor
from fractions import Fraction as F
from hashlib import sha256
from pathlib import Path
import json
import math
import time

from a_reference import c1b1_hard_case_search as H
from a_reference import c1b1_hard_case_checker as C
from a_reference import c1b1_rounding_diagnosis as D

ROOT = Path(__file__).resolve().parents[1]
VERSION = 'c1b1-hard-case-search-survey-v1'
POLICY = {
    'shell': 18,
    'cost_table_block_log2': (24, 28, 32, 34, 35, 36, 38, 40),
    'full_run_degree': 2, 'full_run_points': 2**34+1, 'full_run_superblocks': 1024,
    'workers': 6,
    'affine_points': (2**24+1, 2**28+1), 'affine_slices': 8, 'affine_blocks_per_slice': 256,
    'window_positions': 8, 'window_half_width': 2048, 'window_tau_slope_multiple': 64,
    'window_settings': ((1, 257), (2, 257), (2, 1025)),
    'synthetic_domain': (1, 5000), 'synthetic_tau': '1/100',
    'synthetic_settings': ((1, 65), (1, 17), (2, 65), (2, 33)),
}
SYNTHETIC = (({3: 1, 1: 17, 0: 5}, {1: 4000, 0: 9}),
             ({3: -3, 2: 5, 0: 11}, {1: 2000, 0: 3}),
             ({4: 1, 0: 1}, {3: 3, 1: 300, 0: 11}))
_CACHE = {}


def _bits(x):
    x = abs(F(x))
    return x.numerator.bit_length()-x.denominator.bit_length() if x else None


def _shell():
    if 'shell' not in _CACHE:
        _CACHE['shell'] = H.load_shell(POLICY['shell'])
    return _CACHE['shell']


def _checker_target():
    if 'checker' not in _CACHE:
        _CACHE['checker'] = C.frozen_target()
    return _CACHE['checker']


def _generate(args):
    a0, b0 = args
    target, _, _, guard, _ = _shell()
    return H.run_superblock(target, a0, b0, guard, POLICY['full_run_degree'], POLICY['full_run_points'])


def _check(row):
    target = _checker_target()
    _, _, _, guard, _ = _shell()
    started = time.perf_counter()
    a0, b0 = row['superblock']
    mine = C.superblock(target, a0, b0, guard, POLICY['full_run_degree'], POLICY['full_run_points'])
    ok = (row['derivative_bound'] >= mine['derivative_bound'] and row['crossings'] == mine['crossings']
          and [tuple(x) for x in row['candidate_intervals']] == mine['candidate_intervals'])
    return {'superblock': (a0, b0), 'agrees': ok, 'seconds': time.perf_counter()-started}


def derivative_table(target, lo, hi):
    return {k: H.derivative_bound(target, k, lo, hi) for k in (2, 3, 4)}


def cost_table(bounds, n, guard):
    rows = []
    for e in POLICY['cost_table_block_log2']:
        length = 2**e
        for degree, bound, usable in ((1, bounds[2], length), (2, bounds[3], length), (3, bounds[4], 3*(length//3))):
            delta = H.interpolation_error(degree, bound, usable)
            rows.append({'degree': degree, 'block_length_log2': e, 'blocks': -(-n//length),
                         'delta_bits': _bits(delta), 'threshold_bits': _bits(guard+delta),
                         'predicted_false_positives': 2*n*(guard+delta),
                         'prediction_scope': 'equidistribution_heuristic_not_bound'})
    return rows


def synthetic_comparisons():
    lo, hi = POLICY['synthetic_domain']
    tau = F(POLICY['synthetic_tau'])
    out = []
    for index, (p, q) in enumerate(SYNTHETIC):
        gen, chk = H.Target(p, q), C.Rational(p, q)
        for degree, points in POLICY['synthetic_settings']:
            rows = H.search(gen, lo, hi, tau, degree, points, hi)
            C.verify_rows(chk, lo, hi, tau, degree, points, hi, rows)
            cmp = C.compare_with_brute_force(chk, lo, hi, tau, [iv for r in rows for iv in r['candidate_intervals']])
            out.append({'function': index, 'degree': degree, 'points': points, **cmp})
    return out


def _crossing_near(target, n):
    """Lattice point near an integer crossing of psi (float-free Newton on exact values)."""
    y = target.value(n)
    slope = F(H.at(target.numerators[1], n), H.at(target.q, n)**2)
    m = math.ceil(y) if slope > 0 else math.floor(y)
    for _ in range(4):
        slope = F(H.at(target.numerators[1], n), H.at(target.q, n)**2)
        n += round((m-target.value(n))/slope)
    return n, abs(slope)


def window_comparisons(target, lo, hi):
    out, chk = [], _checker_target()
    half = POLICY['window_half_width']
    for i in range(POLICY['window_positions']):
        centre, slope = _crossing_near(target, lo+(hi-lo)*(2*i+1)//(2*POLICY['window_positions']))
        a, b = centre-half, centre+half-1
        tau = slope*POLICY['window_tau_slope_multiple']
        for degree, points in POLICY['window_settings']:
            rows = H.search(target, a, b, tau, degree, points, 1)
            C.verify_rows(chk, a, b, tau, degree, points, 1, rows)
            cmp = C.compare_with_brute_force(chk, a, b, tau, [iv for r in rows for iv in r['candidate_intervals']])
            out.append({'window': i, 'range': (a, b), 'tau_bits': _bits(tau), 'degree': degree,
                        'points': points, **cmp})
    return out


def affine_slices(target, lo, hi, guard):
    out, n = [], hi-lo+1
    for points in POLICY['affine_points']:
        for i in range(POLICY['affine_slices']):
            a0 = lo+n*i//POLICY['affine_slices']
            b0 = min(a0+POLICY['affine_blocks_per_slice']*points-1, hi)
            row = H.run_superblock(target, a0, b0, guard, 1, points)
            out.append({'points': points, 'slice': i, 'range': (a0, b0), 'crossings': row['crossings'],
                        'candidates': row['candidate_count'], 'max_delta_bits': _bits(row['max_delta']),
                        'seconds': row['seconds']})
    return out


def full_run(lo, hi):
    ranges = H.superblock_ranges(lo, hi, POLICY['full_run_points'], POLICY['full_run_superblocks'])
    started = time.perf_counter()
    with ProcessPoolExecutor(POLICY['workers']) as pool:
        rows = list(pool.map(_generate, ranges, chunksize=4))
    generated = time.perf_counter()-started
    started = time.perf_counter()
    with ProcessPoolExecutor(POLICY['workers']) as pool:
        checks = list(pool.map(_check, rows, chunksize=4))
    checked = time.perf_counter()-started
    return rows, checks, generated, checked


def staging_estimates(guards):
    """Order-of-magnitude inputs only, from pinned fixtures; nothing here is measured on these shells."""
    data = json.loads((ROOT/H.BOUNDARIES).read_bytes())
    out = []
    for group in data['groups']:
        cert = group['certificate']
        shell = int(group['shell_index'])
        if shell > 18:
            continue
        n = cert['domain']['hi']-cert['domain']['lo']+1
        guard = guards[shell]
        out.append({'shell': shell, 'lattice_points': n, 'boundary_count': cert['boundary_count'],
                    'guard_bits': _bits(guard),
                    'heuristic_guard_hits_2GN_bits': _bits(min(2*guard*n, F(n))),
                    'scope': 'estimate_from_pinned_fixture_not_measured'})
    return sorted(out, key=lambda x: x['shell'])


def example_report():
    target, lo, hi, guard, guard_record = _shell()
    n = hi-lo+1
    report = {'version': VERSION, 'status': 'survey_only', 'global_4_4b': 'NotCertified',
              'policy': POLICY, 'domain': {'lo': lo, 'hi': hi, 'lattice_points': n},
              'target': 'psi(n)=P(n)/Q(n)-1/2; hazard iff dist(psi,Z)<=G',
              'guard': {'value_ulps': guard, 'bits': _bits(guard),
                        'provenance': guard_record['provenance'],
                        'numeric_error_bits_at_4096': _bits(guard_record['numeric_error_ulps']),
                        'residual_interval_ulps': guard_record['residual_interval_ulps']}}
    t0 = time.perf_counter()
    bounds = derivative_table(target, lo, hi)
    report['derivative_bounds'] = {f'psi_{k}': {'upper': v, 'bits': _bits(v)} for k, v in bounds.items()}
    report['cost_table'] = cost_table(bounds, n, guard)
    report['synthetic_brute_force'] = synthetic_comparisons()
    report['shell18_window_brute_force'] = window_comparisons(target, lo, hi)
    report['affine_slices'] = affine_slices(target, lo, hi, guard)
    report['preparation_seconds'] = time.perf_counter()-t0
    rows, checks, generated, checked = full_run(lo, hi)
    recheck = H.recheck(target, rows, guard)
    independent = C.recheck(_checker_target(), rows, guard)
    fixture = json.loads((ROOT/H.BOUNDARIES).read_bytes())
    boundary = [g for g in fixture['groups'] if int(g['shell_index']) == 18][0]['certificate']['boundary_count']
    report['full_run'] = {
        'degree': POLICY['full_run_degree'], 'block_length': POLICY['full_run_points']-1,
        'blocks': sum(r['blocks'] for r in rows), 'pieces': sum(r['pieces'] for r in rows),
        'exact_pieces': sum(r['exact_pieces'] for r in rows),
        'max_delta_bits': _bits(max(r['max_delta'] for r in rows)),
        'max_threshold_bits': _bits(guard+max(r['max_delta'] for r in rows)),
        'crossings': sum(r['crossings'] for r in rows), 'half_ulp_fixture_boundary_count': boundary,
        'candidate_intervals': [iv for r in rows for iv in r['candidate_intervals']],
        'candidate_count': sum(r['candidate_count'] for r in rows),
        'exact_recheck_count': recheck['exact_recheck_count'], 'hazards': recheck['hazards'],
        'false_positive_count': recheck['false_positive_count'],
        'independent_recheck': {k: independent[k] for k in ('exact_recheck_count', 'false_positive_count')}
                               | {'hazards': len(independent['hazards'])},
        'checker_superblocks_agree': sum(c['agrees'] for c in checks), 'superblocks': len(rows),
        'generator_wall_seconds': generated, 'checker_wall_seconds': checked, 'workers': POLICY['workers'],
        'generator_cpu_seconds': sum(r['seconds'] for r in rows),
        'checker_cpu_seconds': sum(c['seconds'] for c in checks),
        'rows_sha256': sha256(json.dumps(D.serial(rows), separators=(',', ':')).encode()).hexdigest()}
    report['superblock_rows'] = [{k: r[k] for k in ('superblock', 'derivative_bound', 'crossings',
                                                    'candidate_intervals', 'record_sha256')} for r in rows]
    prior = json.loads((ROOT/H.PRIOR).read_bytes())
    report['staging_estimates'] = staging_estimates({g['shell_index']: F(g['guard']['abs_guard_ulps'])
                                                     for g in prior['groups']})
    report.update({'new_certified_regions': 0, 'coverage_modified': False, 'precision_cap': 16384,
                   'prior_coverage': {'used_regions': 11, 'region_budget': 64, 'gap_count': 84},
                   'extended_to_other_shells': False,
                   'source_sha256': {name: sha256((ROOT/name).read_bytes().replace(b'\r\n', b'\n')).hexdigest()
                                     for name in ('a_reference/c1b1_hard_case_search.py',
                                                  'a_reference/c1b1_hard_case_checker.py',
                                                  'a_reference/c1b1_hard_case_survey.py')},
                   'prior_fixture_sha256': {H.PRIOR: H.PRIOR_HASH, H.BOUNDARIES: H.BOUNDARIES_HASH}})
    return report


if __name__ == '__main__':
    import sys
    out = json.dumps(D.serial(example_report()), separators=(',', ':'))+'\n'
    Path(sys.argv[1]).write_text(out, encoding='utf-8')
