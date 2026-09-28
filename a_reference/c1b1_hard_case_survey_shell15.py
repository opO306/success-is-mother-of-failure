"""Driver for the shell-15 hard-case search survey (survey_only).

Designer verdict: shell 15 gets exactly one survey_only full scan. After this
result, the per-shell exhaustive hard-case search method stops (does not
continue to shell 14 and below) — this is the last survey of its kind, not a
stopping point for the rounding-decision work itself.

Reuses c1b1_hard_case_survey_shell16's helpers unchanged (_gen, _chk,
_pool_stage, _serial_stage, measure, growth, per_block_and_crossing), which
already take the shell as an argument. That module is not edited, because its
fixture pins its source hash. Same-host baseline: shell 16 is re-run on the
same host/workers so growth ratios compare like with like, and its rows must
equal the shell-16 survey fixture.
"""
from fractions import Fraction as F
from hashlib import sha256
from pathlib import Path
import json
import os
import time

from a_reference import c1b1_hard_case_search as H
from a_reference import c1b1_hard_case_survey as V
from a_reference import c1b1_hard_case_survey_shell16 as S16
from a_reference import c1b1_rounding_diagnosis as D

ROOT = Path(__file__).resolve().parents[1]
VERSION = 'c1b1-hard-case-search-survey-shell15-v1'
SHELL = 15
BASELINE_SHELL = 16
SHELL16_SURVEY = 'a_reference/fixtures/c1b1_hard_case_survey_shell16_v1.json'
CERTIFICATE_16 = 'a_reference/fixtures/c1b1_hard_case_certificate_shell16_v1.json'


def _digest(name):
    return sha256((ROOT/name).read_bytes().replace(b'\r\n', b'\n')).hexdigest()


def example_report(workers):
    target, lo, hi, guard, guard_record = H.load_shell(SHELL)
    n = hi-lo+1
    report = {'version': VERSION, 'status': 'survey_only', 'global_4_4b': 'NotCertified',
              'designer_verdict': 'shell 15 is the last survey of the per-shell exhaustive hard-case '
                                  'search method; result decides whether the method stops at shell 14 '
                                  'and below. No coverage or certification status change here.',
              'policy': {**V.POLICY, 'shell': SHELL, 'workers': workers},
              'domain': {'lo': lo, 'hi': hi, 'lattice_points': n},
              'target': 'psi(n)=P(n)/Q(n)-1/2; hazard iff dist(psi,Z)<=G',
              'guard': {'value_ulps': guard, 'bits': V._bits(guard), 'provenance': guard_record['provenance'],
                        'numeric_error_bits_at_4096': V._bits(guard_record['numeric_error_ulps']),
                        'residual_interval_ulps': guard_record['residual_interval_ulps']},
              'host': {'os': os.name, 'cpu_count': os.cpu_count(), 'workers': workers}}
    t0 = time.perf_counter()
    bounds = V.derivative_table(target, lo, hi)
    report['derivative_bounds'] = {f'psi_{k}': {'upper': v, 'bits': V._bits(v)} for k, v in bounds.items()}
    report['cost_table'] = V.cost_table(bounds, n, guard)
    report['synthetic_brute_force'] = V.synthetic_comparisons()
    report['shell_window_brute_force'] = V.window_comparisons(target, lo, hi)
    report['affine_slices'] = V.affine_slices(target, lo, hi, guard)
    report['preparation_seconds'] = time.perf_counter()-t0
    print(f'[{time.strftime("%H:%M:%S")}] preparation {report["preparation_seconds"]:.1f}s', flush=True)
    shell15 = S16.measure(SHELL, workers)
    print(f'[{time.strftime("%H:%M:%S")}] shell 15 done: crossings={shell15["crossings"]} '
          f'candidates={shell15["candidate_count"]} hazards={len(shell15["hazards"])} '
          f'agree={shell15["checker_superblocks_agree"]}', flush=True)
    shell16 = S16.measure(BASELINE_SHELL, workers)
    stored16 = json.loads((ROOT/SHELL16_SURVEY).read_bytes())['superblock_rows']
    shell16['rows_equal_shell16_survey_fixture'] = [
        (r['superblock'], r['derivative_bound'], r['crossings'], r['candidate_intervals'])
        for r in D.serial(shell16['rows'])
    ] == [(r['superblock'], r['derivative_bound'], r['crossings'], r['candidate_intervals']) for r in stored16]
    print(f'[{time.strftime("%H:%M:%S")}] shell 16 baseline done: rows equal fixture='
          f'{shell16["rows_equal_shell16_survey_fixture"]}', flush=True)
    report['full_run'] = {k: v for k, v in shell15.items() if k != 'rows'}
    report['superblock_rows'] = shell15['rows']
    report['same_host_shell16_baseline'] = {k: v for k, v in shell16.items() if k not in ('rows', 'candidate_intervals')}
    report['growth_vs_shell16_same_host'] = S16.growth(shell15, shell16)
    report['cost_split_same_host'] = S16.per_block_and_crossing(shell15, shell16)
    prior = json.loads((ROOT/H.PRIOR).read_bytes())
    report['staging_estimates'] = V.staging_estimates({g['shell_index']: F(g['guard']['abs_guard_ulps'])
                                                       for g in prior['groups']})
    coverage = json.loads((ROOT/CERTIFICATE_16).read_bytes())['coverage']
    report.update({'new_certified_regions': 0, 'coverage_modified': False, 'certificate_created': False,
                   'precision_cap': 16384, 'extended_to_other_shells': False,
                   'per_shell_exhaustive_search_stops_here': True,
                   'prior_coverage': {'used_regions': coverage['used_regions'],
                                      'region_budget': coverage['region_budget'],
                                      'gap_count': len(coverage['uncovered_intervals']),
                                      'shell_15_gaps': sum(g['shell_index'] == SHELL
                                                           for g in coverage['uncovered_intervals'])},
                   'source_sha256': {name: _digest(name) for name in (
                       'a_reference/c1b1_hard_case_search.py', 'a_reference/c1b1_hard_case_checker.py',
                       'a_reference/c1b1_hard_case_survey.py', 'a_reference/c1b1_hard_case_survey_shell16.py',
                       'a_reference/c1b1_hard_case_survey_shell15.py')},
                   'prior_fixture_sha256': {H.PRIOR: H.PRIOR_HASH, H.BOUNDARIES: H.BOUNDARIES_HASH,
                                            SHELL16_SURVEY: _digest(SHELL16_SURVEY),
                                            CERTIFICATE_16: _digest(CERTIFICATE_16)}})
    return report


if __name__ == '__main__':
    import sys
    workers = int(sys.argv[2]) if len(sys.argv) > 2 else V.POLICY['workers']
    out = json.dumps(D.serial(example_report(workers)), separators=(',', ':'))+'\n'
    Path(sys.argv[1]).write_text(out, encoding='utf-8')
