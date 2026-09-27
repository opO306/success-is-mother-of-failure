"""Uniform-output obstruction is not a pointwise precision counterexample."""
from copy import deepcopy
from fractions import Fraction as Q
import json
from pathlib import Path

import pytest

from a_reference import c1b1_rounding_diagnosis as T
from a_reference import c1b1_rounding_completeness as D
from a_reference import c1b1_two_atom as C
from a_reference import c1b1_outer_bootstrap as O
from a_reference import c1b1_outer_bound as B
from a_reference import c1b1_reachable_geometry as G
from a_numeric import FixedPoint


def run_at():
    return C.new_run(FixedPoint(96, 48), 40, (-10, 0, 0), (-1, 0, 0),
                     (10, 0, 0), (1, 0, 0), momentum_profile=FixedPoint(96, 80))


@pytest.fixture(scope='module')
def report():
    return T.example_report()


def test_all_original_records_are_classified_and_never_promoted(report):
    assert report['cell_budget'] == report['checked_cells'] == 64
    assert report['original_reason_counts'] == {'fixed_cell_budget_exhausted': 49, 'shell_not_checked': 27}
    assert len(report['records']) == 76
    assert {r['record_index'] for r in report['records']} == set(range(76))
    assert sum(report['classification_counts'].values()) == 76
    assert report['classification_counts']['proven_nonuniform_output'] == 74
    assert report['status'] == 'not_certified'
    assert report['rounding_decision_completeness'] == 'not_proved'
    assert report['cell_diagnosis_may_promote_cover'] is False
    assert all(r['original_check_status'].startswith('not_checked') for r in report['records'])


def test_different_outputs_are_supported_by_actual_executor_at_each_endpoint(report):
    records = [r for r in report['records'] if r['diagnosis']['classification'] == 'proven_nonuniform_output']
    for record in (records[0], records[48], records[-1]):
        part = record['diagnosis']['parts'][0]
        endpoints = part['endpoint_witnesses']
        assert endpoints[0]['rounded_impulse'] != endpoints[1]['rounded_impulse']
        assert part['cell_obligation']['blocked_axes'] == (0,)
        for point in endpoints:
            assert point['max_decision_bits'] <= 256
            assert C.impulse(point['q'], Q(20), FixedPoint(96, 80)) == point['rounded_impulse']
        assert part['interior_pointwise_completeness'] == 'not_proved'


def test_65_distinct_outputs_prove_only_uniform_cover_budget_obstruction(report):
    proof = report['uniform_cover_obstruction']
    assert proof['status'] == 'proved_budget_obstruction'
    assert proof['minimum_uniform_leaves'] == 65 > report['cell_budget']
    assert proof['distinct_grid_points'] == proof['distinct_rounded_outputs'] == 65
    assert all((w['q'][0]/B.UX).numerator % 2 == 0 for w in proof['witnesses'])
    assert proof['actual_trajectory_lower_bound'] == 'not_claimed'
    assert proof['pointwise_rounding_completeness'] == 'not_proved'


def test_equal_endpoint_outputs_do_not_certify_an_unresolved_parent(report):
    record = next(r for r in report['records'] if r['shell_index'] == 27)
    part = record['diagnosis']['parts'][0]
    assert all(w['rounded_impulse'] == (0, 0, 0) for w in part['endpoint_witnesses'])
    assert part['classification'] == 'parent_enclosure_not_separated'
    assert part['cell_obligation']['blocked_axes'] == (0,)
    assert part['interior_pointwise_completeness'] == 'not_proved'


def test_diagnosis_has_no_trajectory_or_D_valid_access(monkeypatch):
    def forbidden(*_args):
        raise AssertionError('diagnosis cannot use a trajectory or D_valid')
    monkeypatch.setattr(C, 'step', forbidden)
    monkeypatch.setattr(C.Run, 'validation', property(forbidden))
    run = run_at()
    before = deepcopy(run)
    report = T.diagnose_reachable_rounding(run, Q(2), max_cells=1)
    assert report['checked_cells'] == report['cell_budget'] == 1
    assert report['status'] == 'not_certified'
    assert run.atoms == before.atoms and run.J_cache == before.J_cache
    assert run.t_steps == 0 and run._validation is None


def root_geometry():
    geometry, projection = G.certify_outgoing_reachable(run_at(), Q(2))
    return projection['shells'][0]['root_box'], geometry['shells'][0], projection['shells'][0]


def test_duplicate_witnesses_cannot_inflate_the_lower_bound(report):
    witnesses = report['uniform_cover_obstruction']['witnesses']
    lower = T.uniform_cover_lower_bound([witnesses[0]]*65, *root_geometry())
    assert lower['minimum_uniform_leaves'] == lower['distinct_grid_points'] == 1


@pytest.mark.parametrize('fault', ['outside_guard', 'off_grid', 'false_raw', 'wide_interval'])
def test_obstruction_rejects_invalid_membership_and_rounding_witnesses(report, fault):
    witness = deepcopy(report['uniform_cover_obstruction']['witnesses'][0])
    if fault == 'outside_guard':
        witness['q'] = (Q(19), Q(0), Q(0))
    elif fault == 'off_grid':
        witness['q'] = (witness['q'][0]+B.UX/2, Q(0), Q(0))
    else:
        components = list(witness['components'])
        components[0] = dict(components[0])
        if fault == 'false_raw':
            components[0]['raw'] += 1
        else:
            raw = components[0]['raw']
            components[0]['impulse_interval'] = ((raw-1)*B.UP, (raw+1)*B.UP)
        witness['components'] = tuple(components)
    with pytest.raises(O.NotCertified):
        T.uniform_cover_lower_bound([witness], *root_geometry())


def test_point_precision_failure_is_preserved_without_inventing_spatial_variation(monkeypatch):
    box, shell, constraint = root_geometry()
    def undecided(_q):
        raise O.NotCertified('injected point separation failure')
    monkeypatch.setattr(D, 'certify_impulse_point', undecided)
    result = T.diagnose_cell(box, shell, constraint)
    assert result['classification'] == 'point_precision_not_separated'
    assert 'injected' in result['parts'][0]['reason']


def test_connected_groups_preserve_every_part_and_do_not_cross_shells(report):
    indices = [i for group in report['connected_groups'] for i in group['record_indices']]
    assert sorted(indices) == list(range(76))
    for group in report['connected_groups']:
        for index in group['record_indices']:
            record = report['records'][index]
            assert record['shell_index'] == group['shell_index']
            assert record['diagnosis']['classification'] == group['classification']


def test_mutation_endpoint_agreement_promoted_to_uniform_is_detected(report):
    bad = deepcopy(report)
    for record in bad['records']:
        if record['shell_index'] == 27:
            record['diagnosis']['parts'][0]['classification'] = 'uniform_cell_at_diagnostic_precision'
    with pytest.raises(AssertionError):
        test_equal_endpoint_outputs_do_not_certify_an_unresolved_parent(bad)


def test_mutation_duplicate_count_inflation_is_detected(monkeypatch, report):
    real = T.uniform_cover_lower_bound
    def inflated(witnesses, *args):
        result = real(witnesses, *args)
        result['minimum_uniform_leaves'] = len(witnesses)
        return result
    monkeypatch.setattr(T, 'uniform_cover_lower_bound', inflated)
    with pytest.raises(AssertionError):
        test_duplicate_witnesses_cannot_inflate_the_lower_bound(report)


def test_fixture_is_regenerated_with_live_source_hashes(report):
    path = Path(__file__).resolve().parents[1]/'a_reference/fixtures/c1b1_rounding_diagnosis_v1.json'
    assert json.loads(path.read_text(encoding='utf-8')) == T.serial(report)


def test_reflected_axis_intersection_preserves_closed_dot_and_radial_boundaries():
    unit = 2**48
    shell = {'a': Q(20), 'guard_b': Q(25)}
    constraint = {'exact_zero_relative_axes': (1, 2),
                  'initial_relative_momentum': (Q(-1), Q(0), Q(0)),
                  'dot_initial_momentum_lower': Q(20),
                  'cross_initial_momentum_norm_cap': Q(0)}
    axis, intervals = T._axis_intervals(((-30*unit, 30*unit), (0, 0), (0, 0)), shell, constraint)
    assert axis == 0 and intervals == ((-25*unit, -20*unit),)


def test_oblique_or_multidimensional_projection_is_reported_unsupported():
    box, shell, constraint = root_geometry()
    constraint = dict(constraint, exact_zero_relative_axes=(2,))
    result = T.diagnose_cell(box, shell, constraint)
    assert result['classification'] == 'unsupported_projection'
