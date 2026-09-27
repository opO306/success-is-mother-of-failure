"""Pointwise decision is weaker than uniform-output and separate from coverage."""
from copy import deepcopy
from fractions import Fraction as Q
import json
from pathlib import Path

import pytest

from a_numeric import FixedPoint
from a_reference import c1b1_rounding_regions as R
from a_reference import c1b1_axis_decision_bounds as A
from a_reference import c1b1_rounding_diagnosis as T
from a_reference import c1b1_rounding_completeness as D
from a_reference import c1b1_outer_bound as B
from a_reference import c1b1_outer_bootstrap as O
from a_reference import c1b1_two_atom as C

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module')
def report():
    return R.example_report()


def test_65_different_outputs_have_one_common_finite_proof(report):
    proof = report['finite_acceptance']
    assert proof['input_count'] == proof['distinct_output_count'] == 65
    assert proof['bits'] == 256 <= C.MAX_PRECISION_BITS
    assert 0 <= proof['common_endpoint_error_upper'] < proof['common_margin_lower']
    assert R.verify_region(proof) == proof['domain']
    for raw, output in zip(proof['domain']['points'], proof['outputs']):
        assert C.impulse(tuple(x*B.UX for x in raw), Q(20), FixedPoint(96, 80)) == output
    with pytest.raises(O.NotCertified):
        R.certify_finite_points(proof['domain']['points'], bits=128)


def test_old_uniform_certifier_is_preserved_and_still_rejects_this_range(report):
    points = report['finite_acceptance']['domain']['points']
    # There are endpoints with DIFFERENT outputs; a uniform certificate must refuse.
    assert C.impulse(tuple(x*B.UX for x in points[0]), Q(20), FixedPoint(96, 80)) != C.impulse(
        tuple(x*B.UX for x in points[-1]), Q(20), FixedPoint(96, 80))
    with pytest.raises(O.NotCertified):
        D.zero_cell(points[0][0]*B.UX, points[-1][0]*B.UX)


def test_all_29_groups_have_monotonicity_but_27_lack_boundary_margin(report):
    groups = report['groups']
    assert len(groups) == 29
    assert all(g['monotonicity'] == 'strictly_increasing' for g in groups)
    assert all(g['adjacent_impulse_separation_lower'] > 0 for g in groups)
    assert all(g['V_prime_interval'][0] > 0 and g['V_second_interval'][1] < 0 for g in groups)
    assert all(g['interior_extrema'] == g['zero_crossing'] == 'excluded' for g in groups)
    blocked = [g for g in groups if not g['common_precision_certified']]
    assert len(blocked) == 27
    assert all(g['blocking_obligation'] == 'lattice_rounding_boundary_margin_not_proved' for g in blocked)
    assert all(g['common_rounding_margin_lower'] is None for g in blocked)
    assert all(g['actual_visited_point_count'] == 'not_proved' for g in groups)


def test_last_interval_is_certified_whole_without_endpoint_interpolation(report):
    proof = report['analytic_and_singleton_certificates'][-1]
    assert proof['method'] == 'analytic_axis_zero'
    assert proof['input_count'] == 553997943205884291
    assert proof['output'] == (0, 0, 0)
    assert -B.UP/2 < proof['physical_impulse_interval'][0] < proof['physical_impulse_interval'][1] < 0
    assert proof['physical_derivative_intervals'][0][0] > 0
    assert proof['physical_derivative_intervals'][1][1] < 0
    assert R.verify_region(proof) == proof['domain']
    assert proof['common_endpoint_error_upper'] < proof['common_margin_lower']
    domain = proof['domain']
    for raw in (domain['lo'], (domain['lo']+domain['hi'])//2, domain['hi']):
        assert C.impulse((raw*B.UX, Q(0), Q(0)), Q(20), FixedPoint(96, 80)) == (0, 0, 0)


def test_reflection_reuses_bounds_with_opposite_impulse_sign(report):
    original = report['analytic_and_singleton_certificates'][-1]
    domain = original['domain']
    reflected = R.certify_axis_zero_region(2, -domain['hi'], -domain['lo'])
    assert reflected['physical_impulse_interval'] == tuple(-x for x in reversed(original['physical_impulse_interval']))
    assert reflected['common_margin_lower'] == original['common_margin_lower']
    assert reflected['common_endpoint_error_upper'] == original['common_endpoint_error_upper']
    R.verify_region(reflected)


def test_finite_acceptance_and_last_region_do_not_promote_global_gate(report):
    coverage = report['outgoing_coverage']
    assert coverage['status'] == report['status'] == 'not_certified'
    assert coverage['region_budget'] == 64 and coverage['used_regions'] == 3
    assert len(coverage['uncovered_intervals']) == 92
    assert coverage['tail'] is None
    assert all(g['shell_index'] != 27 for g in coverage['uncovered_intervals'])
    assert coverage['global_initial_state_family_completeness'] == 'not_claimed'
    assert report['finite_acceptance']['actual_trajectory_membership'] == 'not_claimed'


@pytest.mark.parametrize('fault', ['domain', 'omit', 'output', 'enclosure', 'margin', 'precision', 'count', 'scope'])
def test_finite_proof_checker_rejects_faults(report, fault):
    proof = deepcopy(report['finite_acceptance'])
    if fault == 'domain':
        proof['domain']['points'] = proof['domain']['points'][:-1]
    elif fault == 'omit':
        proof['outputs'] = proof['outputs'][:-1]
    elif fault == 'output':
        proof['outputs'] = ((0, 0, 0), *proof['outputs'][1:])
    elif fault == 'enclosure':
        proof['enclosures'] = (((Q(0), Q(0)),)*3, *proof['enclosures'][1:])
    elif fault == 'margin':
        proof['common_margin_lower'] += B.UP
    elif fault == 'precision':
        proof['bits'] = 32768
    elif fault == 'count':
        proof['input_count'] -= 1
    else:
        proof['scope'] = 'all_future_kicks'
    with pytest.raises(O.NotCertified):
        R.verify_region(proof)


@pytest.mark.parametrize('fault', ['domain', 'derivative', 'error', 'margin'])
def test_analytic_proof_checker_rejects_faults(report, fault):
    proof = deepcopy(report['analytic_and_singleton_certificates'][-1])
    if fault == 'domain':
        proof['domain']['lo'] -= 1
    elif fault == 'derivative':
        proof['physical_derivative_intervals'] = ((Q(0), Q(0)),)*2
    elif fault == 'error':
        proof['common_endpoint_error_upper'] = 0
    else:
        proof['common_margin_lower'] = B.UP
    with pytest.raises(O.NotCertified):
        R.verify_region(proof)


@pytest.mark.parametrize('bits', [True, 127, 192, 32768])
def test_precision_schedule_is_fixed(bits):
    with pytest.raises(O.NotCertified):
        A.evaluator_ratio_error(Q(20), Q(25), bits)


@pytest.mark.parametrize('radius', [20, 25, 100, 10000])
def test_uniform_endpoint_error_contains_actual_evaluator_endpoints(radius):
    r = Q(radius)
    true = -A.axis_derivatives(r, r)[0]*Q(20)
    error = A.axis_impulse_error(r, r, 256)
    actual = R._point_enclosures(R.finite_domain(((int(r/B.UX), 0, 0),)), 256)[0][0]
    # Stronger than overlap: every possible true value in the tight 512-bit
    # mathematical enclosure is within the derived endpoint error.
    assert all(true.hi-error <= endpoint <= true.lo+error for endpoint in actual)
    # A zero-error mutation cannot hide behind sampling or a repeated formula.
    assert not all(true.hi <= endpoint <= true.lo for endpoint in actual)


def test_exp_endpoint_error_controls_nonmonotone_execution_branches():
    for bits in (128, 256):
        for value in (Q(1, 100), Q(1), Q(255, 256), bits*C.LN2_UPPER):
            argument = A.Iv.of(value)
            error = A.exp_endpoint_error(argument, Q(0), bits)
            exact = A.exp_range(argument)
            raw = C._const(value, bits)
            endpoints = tuple(Q(x, 1 << bits) for x in C._exp_neg(raw, bits))
            assert all(exact.hi-error <= endpoint <= exact.lo+error for endpoint in endpoints)


@pytest.mark.parametrize('radius', [20, 100, 10000])
def test_rewritten_derivatives_agree_with_existing_jet_algebra(radius):
    original = B.derivatives(Q(radius), Q(radius))
    rewritten = A.axis_derivatives(Q(radius), Q(radius))
    for order, interval in enumerate(rewritten, start=1):
        assert max(interval.lo, original[order].lo) <= min(interval.hi, original[order].hi)


def test_derivative_check_detects_a_missing_polynomial_term(monkeypatch):
    original = B.derivatives(Q(20), Q(20))
    differentiate = A._pd
    def missing_term(polynomial):
        result = differentiate(polynomial)
        if result:
            result.pop(max(result))
        return result
    monkeypatch.setattr(A, '_pd', missing_term)
    broken = A.axis_derivatives(Q(20), Q(20))
    assert any(max(iv.lo, original[n].lo) > min(iv.hi, original[n].hi)
               for n, iv in enumerate(broken, start=1))


def test_monotonicity_and_adjacent_separation_do_not_imply_rounding_margin():
    tiny = Q(1, 1 << 20000)
    values = tuple(k*B.UP+B.UP/2+tiny for k in range(3))
    assert all(b-a == B.UP for a, b in zip(values, values[1:]))
    assert tiny < Q(1, 1 << C.MAX_PRECISION_BITS)
    ambiguous = (((B.UP/2-Q(1, 1 << 16384), B.UP/2+Q(1, 1 << 16384)), (Q(0), Q(0)), (Q(0), Q(0))),)
    with pytest.raises(O.NotCertified):
        R._finite_obligations(ambiguous, ((1, 0, 0),))


def test_exact_tie_is_not_certified_by_strict_margin_proof():
    tie = (((B.UP/2, B.UP/2), (Q(0), Q(0)), (Q(0), Q(0))),)
    assert FixedPoint(96, 80).from_exact(B.UP/2) == 0
    with pytest.raises(O.NotCertified):
        R._finite_obligations(tie, ((0, 0, 0),))


@pytest.mark.parametrize('fault', ['duplicate', 'fractional_raw', 'outside', 'crosses_zero'])
def test_invalid_domain_refused(fault):
    with pytest.raises(O.NotCertified):
        if fault == 'duplicate':
            R.finite_domain(((20 << 48, 0, 0),)*2)
        elif fault == 'fractional_raw':
            R.finite_domain(((Q(20 << 48), 0, 0),))
        elif fault == 'outside':
            R.finite_domain(((1 << 96, 0, 0),))
        else:
            R.axis_domain(0, -20 << 48, 20 << 48)


def test_live_evaluator_mutation_invalidates_error_proof(monkeypatch):
    monkeypatch.setattr(C, '_mul', lambda a, b, bits: (0, 0))
    with pytest.raises(O.NotCertified, match='live evaluator'):
        R.certify_finite_points(((20 << 48, 0, 0),))


def test_coverage_never_fills_a_gap_or_raises_region_budget():
    assert R._gaps(1, 10, ((1, 4), (6, 10))) == ((5, 5),)
    assert R._gaps(1, 10, ((1, 4), (5, 10))) == ()
    with pytest.raises(O.NotCertified, match='64-region'):
        R.check_outgoing_coverage(None, Q(2), ({},)*65)


def test_no_trajectory_D_valid_or_subdivision_access(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('proof must not replay, read D_valid or split')
    monkeypatch.setattr(C, 'step', forbidden)
    monkeypatch.setattr(C.Run, 'validation', property(forbidden))
    monkeypatch.setattr(D, 'zero_cell', forbidden)
    result = R.example_report()
    assert result['status'] == 'not_certified'


def test_recorded_report_reproduces_exactly(report):
    recorded = json.loads((ROOT/'a_reference/fixtures/c1b1_rounding_regions_v1.json').read_text(encoding='utf-8'))
    assert T.serial(report) == recorded
