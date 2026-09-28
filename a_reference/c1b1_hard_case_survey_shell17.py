"""Driver for the ④-4c-7 shell-17 hard-case search scalability survey (survey_only).

Reuses c1b1_hard_case_survey's helpers unchanged (cost_table,
synthetic_comparisons, window_comparisons, affine_slices, staging_estimates).
That module is not edited: its shell-18 fixture pins its source hash, and its
full_run reads shell 18 from module state. The parallel run below is a copy of
its full_run with the shell passed explicitly in every worker argument, since
ProcessPoolExecutor workers under spawn re-import modules fresh and would
silently see shell 18 again if the shell were only set as a global.

Single, separate scalability measurement per the designer's instruction:
shell 17 alone, not a shell 16/15 extension. Shell 18's existing survey_only
fixture and its certificate (c1b1_hard_case_certificate) are untouched.
"""
from concurrent.futures import ProcessPoolExecutor
from hashlib import sha256
from pathlib import Path
import json
import time

from a_reference import c1b1_hard_case_checker as C
from a_reference import c1b1_hard_case_search as H
from a_reference import c1b1_hard_case_survey as V
from a_reference import c1b1_rounding_diagnosis as D

ROOT = Path(__file__).resolve().parents[1]
VERSION = 'c1b1-hard-case-search-survey-shell17-v1'
SHELL = 17
CERTIFICATE = 'a_reference/fixtures/c1b1_hard_case_certificate_v1.json'
_CACHE = {}


def _shell(shell):
    if shell not in _CACHE:
        _CACHE[shell] = H.load_shell(shell)
    return _CACHE[shell]


def _generate(args):
    a0, b0, shell = args
    target, _, _, guard, _ = _shell(shell)
    return H.run_superblock(target, a0, b0, guard, V.POLICY['full_run_degree'], V.POLICY['full_run_points'])


def _check(args):
    row, shell = args
    if 'checker' not in _CACHE:
        _CACHE['checker'] = C.frozen_target()
    _, _, _, guard, _ = _shell(shell)
    started = time.perf_counter()
    a0, b0 = row['superblock']
    mine = C.superblock(_CACHE['checker'], a0, b0, guard, V.POLICY['full_run_degree'], V.POLICY['full_run_points'])
    ok = (row['derivative_bound'] >= mine['derivative_bound'] and row['crossings'] == mine['crossings']
          and [tuple(x) for x in row['candidate_intervals']] == mine['candidate_intervals'])
    return {'superblock': (a0, b0), 'agrees': ok, 'seconds': time.perf_counter()-started}


def full_run(lo, hi, shell=SHELL, workers=None):
    workers = workers or V.POLICY['workers']
    ranges = H.superblock_ranges(lo, hi, V.POLICY['full_run_points'], V.POLICY['full_run_superblocks'])
    started = time.perf_counter()
    with ProcessPoolExecutor(workers) as pool:
        rows = list(pool.map(_generate, [(a0, b0, shell) for a0, b0 in ranges], chunksize=4))
    generated = time.perf_counter()-started
    started = time.perf_counter()
    with ProcessPoolExecutor(workers) as pool:
        checks = list(pool.map(_check, [(r, shell) for r in rows], chunksize=4))
    checked = time.perf_counter()-started
    return rows, checks, generated, checked


def example_report():
    target, lo, hi, guard, guard_record = H.load_shell(SHELL)
    n = hi-lo+1
    policy = {**V.POLICY, 'shell': SHELL}
    report = {'version': VERSION, 'status': 'survey_only', 'global_4_4b': 'NotCertified',
              'policy': policy, 'domain': {'lo': lo, 'hi': hi, 'lattice_points': n},
              'target': 'psi(n)=P(n)/Q(n)-1/2; hazard iff dist(psi,Z)<=G',
              'guard': {'value_ulps': guard, 'bits': V._bits(guard),
                        'provenance': guard_record['provenance'],
                        'numeric_error_bits_at_4096': V._bits(guard_record['numeric_error_ulps']),
                        'residual_interval_ulps': guard_record['residual_interval_ulps']}}
    t0 = time.perf_counter()
    bounds = V.derivative_table(target, lo, hi)
    report['derivative_bounds'] = {f'psi_{k}': {'upper': v, 'bits': V._bits(v)} for k, v in bounds.items()}
    report['cost_table'] = V.cost_table(bounds, n, guard)
    report['synthetic_brute_force'] = V.synthetic_comparisons()
    report['shell_window_brute_force'] = V.window_comparisons(target, lo, hi)
    report['affine_slices'] = V.affine_slices(target, lo, hi, guard)
    report['preparation_seconds'] = time.perf_counter()-t0
    rows, checks, generated, checked = full_run(lo, hi, shell=SHELL)
    recheck = H.recheck(target, rows, guard)
    checker_target = C.frozen_target()
    independent = C.recheck(checker_target, rows, guard)
    fixture = json.loads((ROOT/H.BOUNDARIES).read_bytes())
    boundary = [g for g in fixture['groups'] if int(g['shell_index']) == SHELL][0]['certificate']['boundary_count']
    report['full_run'] = {
        'degree': V.POLICY['full_run_degree'], 'block_length': V.POLICY['full_run_points']-1,
        'blocks': sum(r['blocks'] for r in rows), 'pieces': sum(r['pieces'] for r in rows),
        'exact_pieces': sum(r['exact_pieces'] for r in rows),
        'max_delta_bits': V._bits(max(r['max_delta'] for r in rows)),
        'max_threshold_bits': V._bits(guard+max(r['max_delta'] for r in rows)),
        'crossings': sum(r['crossings'] for r in rows), 'half_ulp_fixture_boundary_count': boundary,
        'candidate_intervals': [iv for r in rows for iv in r['candidate_intervals']],
        'candidate_count': sum(r['candidate_count'] for r in rows),
        'exact_recheck_count': recheck['exact_recheck_count'], 'hazards': recheck['hazards'],
        'false_positive_count': recheck['false_positive_count'],
        'independent_recheck': {k: independent[k] for k in ('exact_recheck_count', 'false_positive_count')}
                               | {'hazards': len(independent['hazards'])},
        'checker_superblocks_agree': sum(c['agrees'] for c in checks), 'superblocks': len(rows),
        'generator_wall_seconds': generated, 'checker_wall_seconds': checked, 'workers': V.POLICY['workers'],
        'generator_cpu_seconds': sum(r['seconds'] for r in rows),
        'checker_cpu_seconds': sum(c['seconds'] for c in checks),
        'generator_parallel_efficiency': sum(r['seconds'] for r in rows)/(generated*V.POLICY['workers']),
        'checker_parallel_efficiency': sum(c['seconds'] for c in checks)/(checked*V.POLICY['workers']),
        'rows_sha256': sha256(json.dumps(D.serial(rows), separators=(',', ':')).encode()).hexdigest()}
    report['superblock_rows'] = [{k: r[k] for k in ('superblock', 'derivative_bound', 'crossings',
                                                    'candidate_intervals', 'record_sha256')} for r in rows]
    prior = json.loads((ROOT/H.PRIOR).read_bytes())
    from fractions import Fraction as F
    report['staging_estimates'] = V.staging_estimates({g['shell_index']: F(g['guard']['abs_guard_ulps'])
                                                       for g in prior['groups']})
    # Coverage as last computed by the ④-4c-6 compositor, read rather than restated.
    coverage = json.loads((ROOT/CERTIFICATE).read_bytes())['coverage']
    prior_coverage = {'used_regions': coverage['used_regions'], 'region_budget': coverage['region_budget'],
                      'gap_count': len(coverage['uncovered_intervals']),
                      'shell_17_gaps': sum(g['shell_index'] == SHELL for g in coverage['uncovered_intervals'])}
    report.update({'new_certified_regions': 0, 'coverage_modified': False, 'precision_cap': 16384,
                   'prior_coverage': prior_coverage,
                   'extended_to_other_shells': False, 'not_a_shell_16_or_15_extension': True,
                   'compared_to_shell_18_reference': 'a_reference/fixtures/c1b1_hard_case_survey_v1.json',
                   'source_sha256': {name: sha256((ROOT/name).read_bytes().replace(b'\r\n', b'\n')).hexdigest()
                                     for name in ('a_reference/c1b1_hard_case_search.py',
                                                  'a_reference/c1b1_hard_case_checker.py',
                                                  'a_reference/c1b1_hard_case_survey.py',
                                                  'a_reference/c1b1_hard_case_survey_shell17.py')},
                   'prior_fixture_sha256': {H.PRIOR: H.PRIOR_HASH, H.BOUNDARIES: H.BOUNDARIES_HASH,
                                            CERTIFICATE: sha256((ROOT/CERTIFICATE).read_bytes()).hexdigest()}})
    return report


if __name__ == '__main__':
    import sys
    out = json.dumps(D.serial(example_report()), separators=(',', ':'))+'\n'
    Path(sys.argv[1]).write_text(out, encoding='utf-8')
