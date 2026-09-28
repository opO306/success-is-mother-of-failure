"""④-4c-9 shell-16 hard-case search survey (survey_only, designer verdict ④-4c-9).

Same generator/checker as the shell-18/17 surveys, run on shell 16's original
domain on the remote node, plus a same-host shell-17 baseline. Nothing here
certifies anything or edits coverage.
"""
from fractions import Fraction as F
from hashlib import sha256
from pathlib import Path
import json

import pytest

from a_reference import c1b1_hard_case_search as H
from a_reference import c1b1_hard_case_survey as V
from a_reference import c1b1_hard_case_survey_shell16 as S

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT/'a_reference/fixtures/c1b1_hard_case_survey_shell16_v1.json'


def _digest(name):
    return sha256((ROOT/name).read_bytes().replace(b'\r\n', b'\n')).hexdigest()


@pytest.fixture(scope='module')
def fixture():
    return json.loads(FIXTURE.read_text(encoding='utf-8'))


@pytest.fixture(scope='module')
def shell():
    return H.load_shell(16)


def test_fixture_keeps_every_certification_state(fixture):
    assert fixture['status'] == 'survey_only' and fixture['global_4_4b'] == 'NotCertified'
    assert fixture['new_certified_regions'] == 0 and fixture['coverage_modified'] is False
    assert fixture['certificate_created'] is False and fixture['extended_to_other_shells'] is False
    assert fixture['precision_cap'] == 16384 and fixture['policy']['shell'] == 16


def test_prior_coverage_is_read_from_the_shell17_certificate_fixture(fixture):
    coverage = json.loads((ROOT/S.CERTIFICATE_17).read_text(encoding='utf-8'))['coverage']
    assert fixture['prior_coverage'] == {
        'used_regions': coverage['used_regions'], 'region_budget': 64,
        'gap_count': len(coverage['uncovered_intervals']),
        'shell_16_gaps': sum(g['shell_index'] == 16 for g in coverage['uncovered_intervals'])}


def test_fixture_is_bound_to_current_sources_and_prior_fixtures(fixture):
    for name, digest in fixture['source_sha256'].items():
        assert _digest(name) == digest, name
    for name in (S.SHELL17_SURVEY, S.CERTIFICATE_17):
        assert fixture['prior_fixture_sha256'][name] == _digest(name)


def test_full_run_is_internally_consistent(fixture, shell):
    _, lo, hi, _, _ = shell
    run = fixture['full_run']
    assert fixture['domain'] == run['domain'] == {'lo': lo, 'hi': hi, 'lattice_points': hi-lo+1}
    assert run['checker_superblocks_agree'] == run['superblocks'] == V.POLICY['full_run_superblocks']
    assert run['exact_recheck_count'] == run['candidate_count'] == run['independent_recheck']['exact_recheck_count']
    assert run['false_positive_count']+len(run['hazards']) == run['exact_recheck_count']
    assert run['independent_recheck']['hazards'] == len(run['hazards'])
    assert run['candidate_count'] == sum(b-a+1 for a, b in run['candidate_intervals'])
    assert F(run['candidate_density']) == F(run['candidate_count'], run['crossings'])
    assert abs(run['crossings']-run['half_ulp_fixture_boundary_count']) <= run['blocks']
    assert all(s['missed'] == 0 and s['hazards'] > 0 for s in fixture['synthetic_brute_force'])
    assert all(s['missed'] == 0 and s['hazards'] > 0 for s in fixture['shell_window_brute_force'])


def test_every_designer_metric_is_recorded(fixture):
    run = fixture['full_run']
    for stage in ('generator', 'checker'):
        rec = run['stages'][stage]
        assert rec['workers'] == fixture['host']['workers']
        for key in ('wall_seconds', 'children_cpu_seconds', 'parallel_efficiency', 'peak_worker_rss_kb'):
            assert rec[key] is not None and float(rec[key]) > 0, (stage, key)
    assert all(run['recheck_seconds_per_candidate'][k] > 0 for k in ('generator', 'checker'))
    growth = fixture['growth_vs_shell17_same_host']
    for key in ('crossings', 'candidates', 'candidate_density', 'generator_cpu', 'checker_cpu'):
        assert growth[key] is not None


def test_same_host_shell17_baseline_reproduces_the_shell17_fixture(fixture):
    base = fixture['same_host_shell17_baseline']
    assert base['shell'] == 17 and base['rows_equal_shell17_survey_fixture'] is True
    stored = json.loads((ROOT/S.SHELL17_SURVEY).read_text(encoding='utf-8'))['full_run']
    assert (base['crossings'], base['candidate_count'], len(base['hazards'])) == \
        (stored['crossings'], stored['candidate_count'], len(stored['hazards']))


def test_growth_and_cost_split_follow_from_the_stored_numbers(fixture):
    run, base = fixture['full_run'], fixture['same_host_shell17_baseline']
    growth = fixture['growth_vs_shell17_same_host']
    assert growth['crossings'] == pytest.approx(run['crossings']/base['crossings'])
    assert F(growth['candidate_density']) == F(run['candidate_density'])/F(base['candidate_density'])
    for stage in ('generator', 'checker'):
        split = fixture['cost_split_same_host'][stage]
        for rec, pts in ((base, base), (run, run)):
            fitted = pts['blocks']*split['per_block_seconds']+pts['crossings']*split['per_crossing_seconds']
            assert fitted == pytest.approx(rec['stages'][stage]['children_cpu_seconds'], rel=1e-9)


def test_fixture_rows_reproduce(fixture, shell):
    """First, last, and the first row with candidates, recomputed with the shell-16 guard."""
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
    table = V.cost_table(V.derivative_table(target, lo, hi), hi-lo+1, guard)
    assert json.loads(json.dumps(H.D.serial(table))) == fixture['cost_table']


def test_cost_split_solver_recovers_known_coefficients():
    def point(blocks, crossings, a_gen, b_gen, a_chk, b_chk):
        return {'blocks': blocks, 'crossings': crossings, 'stages': {
            'generator': {'children_cpu_seconds': blocks*a_gen+crossings*b_gen},
            'checker': {'children_cpu_seconds': blocks*a_chk+crossings*b_chk}}}
    base, new = point(100, 50, 2, 3, 1, 7), point(80, 400, 2, 3, 1, 7)
    split = S.per_block_and_crossing(new, base)
    assert split['generator']['per_block_seconds'] == pytest.approx(2)
    assert split['checker']['per_crossing_seconds'] == pytest.approx(7)
