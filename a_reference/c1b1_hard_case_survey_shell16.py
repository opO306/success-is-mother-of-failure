"""Driver for the ④-4c-9 shell-16 hard-case search survey (survey_only).

Designer verdict ④-4c-9: shell 16 gets a survey_only full scan before any
certification. The aim is hazard search, checker cross-check, candidate density
and real cost. The results change neither coverage nor any certification
status; shell 16 certification and shell 15 entry are decided separately.

The generator, checker and search policy are those of the shell-18 and shell-17
surveys, unchanged. The worker functions are c1b1_hard_case_survey_shell17's
_generate/_check, which take the shell as an argument. That module and
c1b1_hard_case_survey are not edited; their fixtures pin their source hashes.
This module adds per-stage cost records (wall, children CPU, workers,
efficiency, peak worker RSS) and the exact-recheck cost per candidate.

Same-host baseline: shell 17 is re-run on the same host, with the same
workers, so that growth ratios compare like with like. The earlier shell-17
survey ran on a different machine (local, 6 workers). The re-run's rows must
equal the shell-17 fixture rows, which doubles as a cross-platform
reproduction check.
"""
from concurrent.futures import ProcessPoolExecutor
from fractions import Fraction as F
from hashlib import sha256
from pathlib import Path
import json
import os
import time

from a_reference import c1b1_hard_case_checker as C
from a_reference import c1b1_hard_case_search as H
from a_reference import c1b1_hard_case_survey as V
from a_reference import c1b1_hard_case_survey_shell17 as S17
from a_reference import c1b1_rounding_diagnosis as D

ROOT = Path(__file__).resolve().parents[1]
VERSION = 'c1b1-hard-case-search-survey-shell16-v1'
SHELL = 16
BASELINE_SHELL = 17
SHELL17_SURVEY = 'a_reference/fixtures/c1b1_hard_case_survey_shell17_v1.json'
CERTIFICATE_17 = 'a_reference/fixtures/c1b1_hard_case_certificate_shell17_v1.json'


def _rusage(who):
    try:
        import resource
    except ImportError:
        return None
    return resource.getrusage(resource.RUSAGE_CHILDREN if who == 'children' else resource.RUSAGE_SELF)


def _maxrss_kb():
    r = _rusage('self')
    return None if r is None else r.ru_maxrss


def _gen(args):
    row = S17._generate(args)
    row['worker_maxrss_kb'] = _maxrss_kb()
    return row


def _chk(args):
    out = S17._check(args)
    out['worker_maxrss_kb'] = _maxrss_kb()
    return out


def _pool_stage(fn, args, workers):
    r0, t0 = _rusage('children'), time.perf_counter()
    with ProcessPoolExecutor(workers) as pool:
        out = list(pool.map(fn, args, chunksize=4))
    wall, r1 = time.perf_counter()-t0, _rusage('children')
    cpu = None if r0 is None else (r1.ru_utime+r1.ru_stime)-(r0.ru_utime+r0.ru_stime)
    rss = [o['worker_maxrss_kb'] for o in out if o['worker_maxrss_kb'] is not None]
    return out, {'wall_seconds': wall, 'children_cpu_seconds': cpu, 'workers': workers,
                 'parallel_efficiency': None if cpu is None else cpu/(wall*workers),
                 'peak_worker_rss_kb': max(rss) if rss else None}


def _serial_stage(fn):
    c0, t0 = time.process_time(), time.perf_counter()
    out = fn()
    return out, {'wall_seconds': time.perf_counter()-t0, 'cpu_seconds': time.process_time()-c0}


def measure(shell, workers):
    """Full generator + checker run over the original domain, with per-stage costs."""
    target, lo, hi, guard, guard_record = H.load_shell(shell)
    ranges = H.superblock_ranges(lo, hi, V.POLICY['full_run_points'], V.POLICY['full_run_superblocks'])
    rows, gen = _pool_stage(_gen, [(a0, b0, shell) for a0, b0 in ranges], workers)
    checks, chk = _pool_stage(_chk, [(r, shell) for r in rows], workers)
    recheck, rec = _serial_stage(lambda: H.recheck(target, rows, guard))
    independent, irec = _serial_stage(lambda: C.recheck(C.frozen_target(), rows, guard))
    fixture = json.loads((ROOT/H.BOUNDARIES).read_bytes())
    boundary = [g for g in fixture['groups'] if int(g['shell_index']) == shell][0]['certificate']['boundary_count']
    crossings = sum(r['crossings'] for r in rows)
    candidates = sum(r['candidate_count'] for r in rows)
    return {
        'shell': shell, 'domain': {'lo': lo, 'hi': hi, 'lattice_points': hi-lo+1},
        'guard_bits': V._bits(guard),
        'blocks': sum(r['blocks'] for r in rows), 'pieces': sum(r['pieces'] for r in rows),
        'exact_pieces': sum(r['exact_pieces'] for r in rows),
        'max_delta_bits': V._bits(max(r['max_delta'] for r in rows)),
        'crossings': crossings, 'half_ulp_fixture_boundary_count': boundary,
        'candidate_count': candidates,
        'candidate_density': F(candidates, crossings) if crossings else None,
        'candidate_intervals': [iv for r in rows for iv in r['candidate_intervals']],
        'exact_recheck_count': recheck['exact_recheck_count'], 'hazards': recheck['hazards'],
        'false_positive_count': recheck['false_positive_count'],
        'independent_recheck': {k: independent[k] for k in ('exact_recheck_count', 'false_positive_count')}
                               | {'hazards': len(independent['hazards'])},
        'checker_superblocks_agree': sum(c['agrees'] for c in checks), 'superblocks': len(rows),
        'stages': {'generator': gen, 'checker': chk, 'generator_exact_recheck': rec,
                   'checker_exact_recheck': irec},
        'recheck_seconds_per_candidate': {
            'generator': rec['cpu_seconds']/candidates if candidates else None,
            'checker': irec['cpu_seconds']/candidates if candidates else None},
        'rows': [{k: r[k] for k in ('superblock', 'derivative_bound', 'crossings', 'candidate_intervals',
                                    'record_sha256')} for r in rows],
    }


def growth(new, base):
    """Ratios new/base for the same host and workers."""
    def ratio(a, b):
        return None if a is None or b in (None, 0) else a/b
    g, b = new['stages'], base['stages']
    out = {'crossings': ratio(new['crossings'], base['crossings']),
           'blocks': ratio(new['blocks'], base['blocks']),
           'candidates': ratio(new['candidate_count'], base['candidate_count']),
           'candidate_density': ratio(new['candidate_density'], base['candidate_density'])}
    for stage in ('generator', 'checker'):
        out[f'{stage}_cpu'] = ratio(g[stage]['children_cpu_seconds'], b[stage]['children_cpu_seconds'])
        out[f'{stage}_wall'] = ratio(g[stage]['wall_seconds'], b[stage]['wall_seconds'])
    return out


def per_block_and_crossing(new, base):
    """Solve cpu = blocks*a + crossings*b from two same-host points. An estimate, not a measurement."""
    out = {}
    for stage in ('generator', 'checker'):
        y1, y2 = base['stages'][stage]['children_cpu_seconds'], new['stages'][stage]['children_cpu_seconds']
        if y1 is None or y2 is None:
            out[stage] = None
            continue
        a11, a12, a21, a22 = base['blocks'], base['crossings'], new['blocks'], new['crossings']
        det = a11*a22-a12*a21
        out[stage] = {'per_block_seconds': (y1*a22-a12*y2)/det, 'per_crossing_seconds': (a11*y2-y1*a21)/det,
                      'scope': 'two_point_estimate_same_host'}
    return out


def _digest(name):
    return sha256((ROOT/name).read_bytes().replace(b'\r\n', b'\n')).hexdigest()


def example_report(workers):
    target, lo, hi, guard, guard_record = H.load_shell(SHELL)
    n = hi-lo+1
    report = {'version': VERSION, 'status': 'survey_only', 'global_4_4b': 'NotCertified',
              'designer_verdict': '④-4c-9 shell 16 survey_only before certification; no coverage or status change',
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
    shell16 = measure(SHELL, workers)
    print(f'[{time.strftime("%H:%M:%S")}] shell 16 done: crossings={shell16["crossings"]} '
          f'candidates={shell16["candidate_count"]} hazards={len(shell16["hazards"])} '
          f'agree={shell16["checker_superblocks_agree"]}', flush=True)
    shell17 = measure(BASELINE_SHELL, workers)
    stored17 = json.loads((ROOT/SHELL17_SURVEY).read_bytes())['superblock_rows']
    shell17['rows_equal_shell17_survey_fixture'] = [
        (r['superblock'], r['derivative_bound'], r['crossings'], r['candidate_intervals']) for r in D.serial(shell17['rows'])
    ] == [(r['superblock'], r['derivative_bound'], r['crossings'], r['candidate_intervals']) for r in stored17]
    print(f'[{time.strftime("%H:%M:%S")}] shell 17 baseline done: rows equal fixture='
          f'{shell17["rows_equal_shell17_survey_fixture"]}', flush=True)
    report['full_run'] = {k: v for k, v in shell16.items() if k != 'rows'}
    report['superblock_rows'] = shell16['rows']
    report['same_host_shell17_baseline'] = {k: v for k, v in shell17.items() if k not in ('rows', 'candidate_intervals')}
    report['growth_vs_shell17_same_host'] = growth(shell16, shell17)
    report['cost_split_same_host'] = per_block_and_crossing(shell16, shell17)
    prior = json.loads((ROOT/H.PRIOR).read_bytes())
    report['staging_estimates'] = V.staging_estimates({g['shell_index']: F(g['guard']['abs_guard_ulps'])
                                                       for g in prior['groups']})
    coverage = json.loads((ROOT/CERTIFICATE_17).read_bytes())['coverage']
    report.update({'new_certified_regions': 0, 'coverage_modified': False, 'certificate_created': False,
                   'precision_cap': 16384, 'extended_to_other_shells': False,
                   'prior_coverage': {'used_regions': coverage['used_regions'],
                                      'region_budget': coverage['region_budget'],
                                      'gap_count': len(coverage['uncovered_intervals']),
                                      'shell_16_gaps': sum(g['shell_index'] == SHELL
                                                           for g in coverage['uncovered_intervals'])},
                   'source_sha256': {name: _digest(name) for name in (
                       'a_reference/c1b1_hard_case_search.py', 'a_reference/c1b1_hard_case_checker.py',
                       'a_reference/c1b1_hard_case_survey.py', 'a_reference/c1b1_hard_case_survey_shell17.py',
                       'a_reference/c1b1_hard_case_survey_shell16.py')},
                   'prior_fixture_sha256': {H.PRIOR: H.PRIOR_HASH, H.BOUNDARIES: H.BOUNDARIES_HASH,
                                            SHELL17_SURVEY: _digest(SHELL17_SURVEY),
                                            CERTIFICATE_17: _digest(CERTIFICATE_17)}})
    return report


if __name__ == '__main__':
    import sys
    workers = int(sys.argv[2]) if len(sys.argv) > 2 else V.POLICY['workers']
    out = json.dumps(D.serial(example_report(workers)), separators=(',', ':'))+'\n'
    Path(sys.argv[1]).write_text(out, encoding='utf-8')
