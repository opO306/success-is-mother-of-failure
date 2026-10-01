"""Boundary exclusion faults must not promote omitted inputs or exact ties."""
from copy import deepcopy
from fractions import Fraction as Q
from pathlib import Path
import json

import pytest

from a_reference import c1b1_half_ulp_boundaries as H
from a_reference import c1b1_outer_bootstrap as O
from a_reference import c1b1_outer_bound as B
from a_reference import c1b1_rounding_regions as R
from a_reference import c1b1_rounding_diagnosis as T
from a_reference import c1b1_axis_decision_bounds as A
from a_reference import c1b1_two_atom as C
from a_numeric import FixedPoint

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module')
def report():
    return H.example_report()


def synthetic(*, lo=0, hi=3, slope=Q(1), offset=Q(1, 10), error=None, blur=Q(0)):
    """Test-only affine function, never claimed to be reachable Lang physics."""
    if error is None:
        error = lambda bits: Q(1, 1000)
    def point(n):
        value = slope*n+offset
        return value-blur, value+blur
    def direct(n, bits):
        value = slope*n+offset
        e = error(bits)
        nearest = H._floor(value)
        distance = abs(value-(Q(nearest)+Q(1, 2)))
        if distance <= 2*e:
            raise O.NotCertified('synthetic exact tie or unresolved margin')
        return {'bits': bits, 'margin_lower': distance-e, 'endpoint_error_upper': e}
    return H._Problem({'kind': 'NON_CANONICAL_SYNTHETIC_PROOF_TEST', 'lo': lo, 'hi': hi},
                      'synthetic_not_C1B1', point, lambda: (slope, slope), error, direct)


def test_all_27_spans_and_counts_are_recorded_before_enumeration(report):
    assert len(report['groups']) == 27
    assert all(g['certificate']['boundary_count_exact'] for g in report['groups'])
    assert report['groups'][0]['certificate']['boundary_count'] == 6304880043134911522
    assert [g['certificate']['boundary_count'] for g in report['groups'][-4:]] == [249, 42, 8, 1]
    assert report['certified_group_count'] == 3
    assert report['symbolic_family_group_count'] == 24
    for group in report['groups'][:-3]:
        proof = group['certificate']
        assert proof['status'] == 'not_certified'
        assert proof['reason'] == 'symbolic_boundary_family_required'
        assert proof['records'] == ()
        assert proof['candidate_lattice_point_count'] is None


def test_three_large_domains_compress_to_51_boundaries_and_three_candidates(report):
    last = report['groups'][-3:]
    assert [g['certificate']['candidate_lattice_point_count'] for g in last] == [2, 0, 1]
    assert sum(g['certificate']['boundary_count'] for g in last) == 51
    assert [g['certificate']['lattice_point_count'] for g in last] == [
        298023842104416266, 372529648073654547, 465661905535202398]
    for group in last:
        proof = group['certificate']
        assert H.verify_certificate(proof, proof['domain']) == proof['domain']
        assert proof['bits'] == proof['max_decision_bits'] == 256
        assert proof['endpoint_error_upper_ulps'] < proof['common_margin_lower_ulps']
        for candidate in proof['direct_point_proofs']:
            point = candidate['proof']['point_certificate']
            R.verify_region(point)
            raw = point['domain']['points'][0]
            assert C.impulse(tuple(x*B.UX for x in raw), Q(20), FixedPoint(96, 80)) == point['outputs'][0]


def test_checked_composition_keeps_remaining_gaps_and_fixed_region_budget(report):
    coverage = report['outgoing_coverage']
    assert coverage['status'] == 'not_certified'
    assert coverage['global_4_4b'] == 'NotCertified'
    assert coverage['region_budget'] == 64 and coverage['used_regions'] == 6
    assert len(coverage['uncovered_intervals']) == 89
    assert not {24, 25, 26, 27}.intersection(g['shell_index'] for g in coverage['uncovered_intervals'])
    with pytest.raises(O.NotCertified, match='64-region'):
        H.check_outgoing_coverage(None, Q(2), ({},)*64, (({}, {}),))


def test_continuous_inverse_enclosure_agrees_with_rewritten_physical_algebra(report):
    proof = report['groups'][-3]['certificate']
    problem = H._axis_problem(proof['domain'])
    for record in (proof['records'][0], proof['records'][-1]):
        raw = sum(record['lower_inverse_bracket'])/2
        radius = raw*B.UX
        derivative = A.axis_derivatives(radius, radius)[0]
        lower, upper = -20*derivative.hi/B.UP, -20*derivative.lo/B.UP
        a, b = problem.point(raw)
        assert max(lower, a) <= min(upper, b)


def test_inverse_is_proof_of_no_integer_or_only_listed_integers(report):
    for group in report['groups'][-3:]:
        proof = group['certificate']
        problem = H._axis_problem(proof['domain'])
        for record in proof['records']:
            a, b = record['forbidden_preimage_outer']
            assert record['candidate_count'] == max(0, H._floor(b)-H._ceil(a)+1)
            h = Q(record['half_ulp_index'])+Q(1, 2)
            band = proof['forbidden_radius_ulps']
            if a > problem.domain['lo']:
                assert problem.point(a)[1] <= h-band
            if b < problem.domain['hi']:
                assert problem.point(b)[0] >= h+band


@pytest.mark.parametrize('fault', ['direction', 'error', 'index', 'inverse_lower', 'inverse_upper',
                                  'candidate', 'domain', 'precision', 'global', 'margin'])
def test_checker_rejects_fault_injection(report, fault):
    original = report['groups'][-3]['certificate']
    proof = deepcopy(original)
    expected = deepcopy(original['domain'])
    records = list(proof['records'])
    if fault == 'direction':
        proof['monotonic_direction'] = 'strictly_decreasing'
    elif fault == 'error':
        proof['endpoint_error_upper_ulps'] /= 2
    elif fault == 'index':
        proof['records'] = proof['records'][1:]
    elif fault == 'inverse_lower':
        records[0]['lower_inverse_bracket'] = (Q(expected['hi']), Q(expected['hi']))
    elif fault == 'inverse_upper':
        records[0]['upper_inverse_bracket'] = (Q(expected['lo']), Q(expected['lo']))
    elif fault == 'candidate':
        record = next(r for r in records if r['candidate_count'])
        record['candidate_integers'] = ()
        record['candidate_count'] = 0
    elif fault == 'domain':
        proof['domain']['hi'] -= 1
    elif fault == 'precision':
        points = list(proof['direct_point_proofs'])
        points[0]['proof']['bits'] = 32768
        proof['direct_point_proofs'] = tuple(points)
    elif fault == 'global':
        proof['global_4_4b'] = 'Certified'
    else:
        proof['common_margin_lower_ulps'] *= 2
    if fault in ('inverse_lower', 'inverse_upper', 'candidate'):
        proof['records'] = tuple(records)
    with pytest.raises(O.NotCertified):
        H.verify_certificate(proof, expected)


def test_exact_half_ulp_input_never_certifies():
    problem = synthetic(offset=Q(1, 2))
    proof = H._construct(problem, 256)
    assert proof['status'] == 'not_certified'
    assert proof['reason'] == 'candidate_margin_requires_common_precision_refinement'
    assert proof['candidate_lattice_point_count'] > 0
    assert proof['point_precision_cap'] == 16384


def test_maximum_precision_includes_common_domain_precision():
    problem = synthetic(lo=0, hi=1, offset=Q(49, 100))
    proof = H._construct(problem, 256)
    assert proof['status'] == 'certified' and proof['candidate_lattice_point_count'] == 1
    point = proof['direct_point_proofs'][0]
    point['proof'] = problem.direct(point['input_raw'], 128)
    proof['max_decision_bits'] = 128
    with pytest.raises(O.NotCertified, match='common margin or precision changed'):
        H._verify(problem, proof)


@pytest.mark.parametrize('sign', [-1, 1])
def test_inputs_immediately_next_to_boundary_are_not_rounded_away(sign):
    tiny = Q(1, 1 << 200)
    problem = synthetic(lo=0, hi=1, offset=Q(1, 2)+sign*tiny,
                        error=lambda bits: Q(1, 1 << bits))
    proof = H._construct(problem, 256)
    assert proof['status'] == 'certified'
    assert proof['candidate_lattice_point_count'] >= 1
    H._verify(problem, proof)
    assert all(p['proof']['margin_lower'] > proof['endpoint_error_upper_ulps']
               for p in proof['direct_point_proofs'])


def test_synthetic_margin_unresolved_even_at_16384_bits():
    tiny = Q(1, 1 << 20000)
    problem = synthetic(lo=0, hi=1, offset=Q(1, 2)+tiny,
                        error=lambda bits: Q(1, 1 << bits))
    proof = H._construct(problem, 16384)
    assert proof['status'] == 'not_certified'
    assert proof['point_precision_cap'] == 16384
    assert proof['scope'] == 'synthetic_not_C1B1'


def test_public_schedule_reaches_16384_without_certifying_synthetic_tie(monkeypatch):
    problem = synthetic(lo=0, hi=1, offset=Q(1, 2),
                        error=lambda bits: Q(1, 1 << bits))
    monkeypatch.setattr(H, '_axis_problem', lambda domain: problem)
    proof = H.certify_axis_domain(0, 20 << 48, 21 << 48)
    assert proof['status'] == 'not_certified'
    assert proof['reason'] == 'candidate_margin_not_certified_at_precision_cap'
    assert proof['common_precision_attempts'] == (256, 512, 1024, 2048, 4096, 8192, 16384)
    assert proof['scope'] == 'synthetic_not_C1B1'


def test_negative_axis_reflection_preserves_error_and_boundary_count(report):
    original = report['groups'][-1]['certificate']
    domain = original['domain']
    proof = H.certify_axis_domain(1, -domain['hi'], -domain['lo'])
    assert proof['status'] == 'certified'
    assert proof['boundary_count'] == original['boundary_count']
    assert proof['endpoint_error_upper_ulps'] == original['endpoint_error_upper_ulps']
    first, last = original['half_ulp_index_range']
    assert proof['half_ulp_index_range'] == (-last-1, -first-1)
    H.verify_certificate(proof, proof['domain'])


def test_no_integer_boundaries_can_cover_many_inputs():
    problem = synthetic(lo=0, hi=10**18, slope=Q(1, 10**18), offset=Q(1, 10),
                        error=lambda bits: Q(1, 1 << bits))
    proof = H._construct(problem, 256)
    # The crossing happens exactly at an INTEGER for this affine test, so it
    # must produce a direct tie failure rather than a false no-integer proof.
    assert proof['boundary_count'] == 1
    assert proof['status'] == 'not_certified'


def test_negative_half_ulp_indices_and_inclusive_integer_candidates():
    problem = synthetic(lo=-3, hi=0, offset=Q(1, 10))
    proof = H._construct(problem, 256)
    assert proof['half_ulp_index_range'] == (-3, -1)
    assert proof['candidate_lattice_point_count'] == 0
    H._verify(problem, proof)
    assert H._candidate_interval((Q(-2), Q(-1)), (Q(0), Q(1))) == (-2, 1)


def test_zero_boundary_case_and_clipped_endpoint_inverse():
    problem = synthetic(lo=0, hi=2, slope=Q(1, 100), offset=Q(1, 10))
    proof = H._construct(problem, 256)
    assert proof['boundary_count'] == 0
    assert proof['candidate_lattice_point_count'] == 0
    H._verify(problem, proof)
    for target, expected in ((Q(-1), (Q(0), Q(0))), (Q(3), (Q(2), Q(2)))):
        bracket = H._inverse(problem, target)
        assert bracket == expected
        H._verify_inverse(problem, bracket, target)


def test_partial_boundary_work_never_promotes_a_certificate():
    problem = synthetic(lo=0, hi=100)
    proof = H._construct(problem, 256, boundary_budget=1)
    assert proof['status'] == 'not_certified'
    assert proof['candidate_lattice_point_count'] is None
    with pytest.raises(O.NotCertified):
        H._verify(problem, proof)


def test_large_ambiguous_inverse_keeps_all_candidate_inputs():
    problem = synthetic(lo=0, hi=1000, blur=Q(10))
    # Do not enumerate either the 1000 boundaries or the broad candidates.
    proof = H._construct(problem, 256)
    assert proof['status'] == 'not_certified'
    assert proof['candidate_lattice_point_count'] is None


def test_candidate_work_limit_keeps_uncertain_inverse_open():
    problem = synthetic(lo=0, hi=1000, slope=Q(1, 1000), offset=Q(1, 10), blur=Q(1, 50))
    proof = H._construct(problem, 256, candidate_budget=2)
    assert proof['boundary_count'] == 1
    assert proof['status'] == 'not_certified'
    assert proof['reason'] == 'candidate_work_limit'
    assert proof['blocked_candidate_count'] > 2


def test_invalid_monotonicity_and_live_model_mutation_refuse(monkeypatch):
    with pytest.raises(O.NotCertified):
        H._construct(synthetic(slope=Q(-1)), 256)
    monkeypatch.setattr(C, '_model', lambda *args: ((0, 0),)*3)
    with pytest.raises(O.NotCertified, match='live evaluator'):
        H.certify_axis_domain(0, 20 << 48, 25 << 48)


def test_no_replay_D_valid_or_prior_point_list_interpolation(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('boundary proof must use no replay or D_valid')
    monkeypatch.setattr(C, 'step', forbidden)
    monkeypatch.setattr(C.Run, 'validation', property(forbidden))
    proof = H.certify_axis_domain(0, 1862645149230957032, 2328307054766159429)
    assert proof['status'] == 'certified'
    assert proof['actual_trajectory_membership'] == 'not_claimed'


def test_recorded_report_reproduces_exactly(report):
    # The original file remains the hash-pinned inventory of later proofs.
    # Current provenance comes from a fresh generator execution, with the
    # entire mathematical payload compared to that original by the re-audit.
    stored = json.loads((ROOT/'a_reference/fixtures/c1b1_half_ulp_boundaries_rebound_v1.json').read_text(encoding='utf-8'))
    assert T.serial(report) == stored
