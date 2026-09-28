"""④-4c-7 shell-17 hard-case search scalability survey (survey_only).

Same generator/checker as the shell-18 survey, run on shell 17 alone. Nothing
here certifies anything or edits coverage.
"""
from hashlib import sha256
from pathlib import Path
import json

import pytest

from a_reference import c1b1_hard_case_search as H
from a_reference import c1b1_hard_case_survey as V
from a_reference import c1b1_hard_case_survey_shell17 as S

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT/'a_reference/fixtures/c1b1_hard_case_survey_shell17_v1.json'


def _digest(name):
    return sha256((ROOT/name).read_bytes().replace(b'\r\n', b'\n')).hexdigest()


@pytest.fixture(scope='module')
def fixture():
    return json.loads(FIXTURE.read_text(encoding='utf-8'))


@pytest.fixture(scope='module')
def shell():
    return H.load_shell(17)


def test_fixture_keeps_every_certification_state(fixture):
    assert fixture['status'] == 'survey_only' and fixture['global_4_4b'] == 'NotCertified'
    assert fixture['new_certified_regions'] == 0 and fixture['coverage_modified'] is False
    assert fixture['precision_cap'] == 16384 and fixture['extended_to_other_shells'] is False
    assert fixture['not_a_shell_16_or_15_extension'] is True and fixture['policy']['shell'] == 17


def test_prior_coverage_is_read_from_the_certificate_fixture(fixture):
    coverage = json.loads((ROOT/S.CERTIFICATE).read_text(encoding='utf-8'))['coverage']
    assert fixture['prior_coverage'] == {
        'used_regions': coverage['used_regions'], 'region_budget': 64,
        'gap_count': len(coverage['uncovered_intervals']),
        'shell_17_gaps': sum(g['shell_index'] == 17 for g in coverage['uncovered_intervals'])}
    assert fixture['prior_fixture_sha256'][S.CERTIFICATE] == _digest(S.CERTIFICATE)   # LF-normalized: same on Windows and Linux


def test_fixture_is_bound_to_current_sources(fixture):
    for name, digest in fixture['source_sha256'].items():
        assert _digest(name) == digest, name


def test_shell18_survey_driver_is_unchanged():
    """The shell-17 survey reuses the shell-18 driver's helpers without editing it."""
    shell18 = json.loads((ROOT/'a_reference/fixtures/c1b1_hard_case_survey_v1.json').read_text(encoding='utf-8'))
    assert _digest('a_reference/c1b1_hard_case_survey.py') == shell18['source_sha256']['a_reference/c1b1_hard_case_survey.py']


def test_fixture_full_run_is_internally_consistent(fixture, shell):
    _, lo, hi, _, _ = shell
    run = fixture['full_run']
    assert fixture['domain'] == {'lo': lo, 'hi': hi, 'lattice_points': hi-lo+1}
    assert run['checker_superblocks_agree'] == run['superblocks'] == V.POLICY['full_run_superblocks']
    assert run['exact_recheck_count'] == run['candidate_count'] == run['independent_recheck']['exact_recheck_count']
    assert run['false_positive_count']+len(run['hazards']) == run['exact_recheck_count']
    assert run['independent_recheck']['hazards'] == len(run['hazards'])
    assert run['candidate_count'] == sum(b-a+1 for a, b in run['candidate_intervals'])
    assert abs(run['crossings']-run['half_ulp_fixture_boundary_count']) <= run['blocks']
    assert all(s['missed'] == 0 and s['hazards'] > 0 for s in fixture['synthetic_brute_force'])
    assert all(s['missed'] == 0 and s['hazards'] > 0 for s in fixture['shell_window_brute_force'])
    assert 0 < run['generator_parallel_efficiency'] <= 1 and 0 < run['checker_parallel_efficiency'] <= 1


def test_fixture_rows_reproduce(fixture, shell):
    """First, last, and the first row with candidates, recomputed with the shell-17 guard."""
    target, _, _, guard, _ = shell
    stored = fixture['superblock_rows']
    first_with = next(r for r in stored if r['candidate_intervals'])
    for row in (stored[0], first_with, stored[-1]):
        a0, b0 = row['superblock']
        mine = H.run_superblock(target, a0, b0, guard, 2, V.POLICY['full_run_points'])
        assert str(mine['derivative_bound']) == row['derivative_bound']
        assert mine['crossings'] == row['crossings'] and mine['record_sha256'] == row['record_sha256']
        assert [list(x) for x in mine['candidate_intervals']] == row['candidate_intervals']


def test_fixture_cost_table_reproduces(fixture, shell):
    target, lo, hi, guard, _ = shell
    bounds = V.derivative_table(target, lo, hi)
    table = V.cost_table(bounds, hi-lo+1, guard)
    assert json.loads(json.dumps(H.D.serial(table))) == fixture['cost_table']


def test_spawned_workers_match_the_serial_shell_17_rows(shell):
    target, lo, _, guard, _ = shell
    points = V.POLICY['full_run_points']
    rows, checks, _, _ = S.full_run(lo, lo+points*2-1, shell=17, workers=2)
    assert all(c['agrees'] for c in checks)
    for row in rows:
        a0, b0 = row['superblock']
        assert H.run_superblock(target, a0, b0, guard, 2, points)['record_sha256'] == row['record_sha256']


def test_the_shell_travels_in_every_worker_argument(shell, monkeypatch):
    """P/Q is shared by all shells and both guards are negligible on these ranges, so rows cannot tell
    shell 17 from shell 18. Check the mechanism instead: full_run puts the shell in each argument, and
    the worker function uses the guard of the shell it was given (spawned workers re-import modules,
    so module state would silently fall back to shell 18)."""
    _, lo, _, guard17, _ = shell
    guard18 = H.load_shell(18)[3]
    assert guard17 != guard18
    seen = []

    class Recording:
        def __init__(self, workers):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def map(self, fn, args, chunksize=1):
            args = list(args)
            seen.append((fn.__name__, [a[-1] for a in args]))
            return [{'superblock': a[:2], 'seconds': 0} if fn is S._generate else {'agrees': True, 'seconds': 0}
                    for a in args]

    monkeypatch.setattr(S, 'ProcessPoolExecutor', Recording)
    points = V.POLICY['full_run_points']
    S.full_run(lo, lo+points*3-1, shell=17)
    assert seen and all(set(shells) == {17} for _, shells in seen)
    taus = []
    monkeypatch.setattr(S.H, 'run_superblock', lambda target, a0, b0, tau, degree, pts: taus.append(tau))
    S._generate((lo, lo+points-1, 17))
    S._generate((lo, lo+points-1, 18))
    assert taus == [guard17, guard18]
