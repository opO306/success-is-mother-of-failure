"""Independent arithmetic checks and evidence-boundary fault injection."""
from copy import deepcopy
from fractions import Fraction as Q
from math import gcd, lcm
from pathlib import Path
import json

import pytest

from a_reference import c1b1_modular_distance_survey as M
from a_reference import c1b1_fractional_phase_survey as S
from a_reference import c1b1_family_checker as K
from a_reference import c1b1_outer_bootstrap as O
from a_reference import c1b1_rounding_diagnosis as T

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module')
def report():
    return M.example_report()


def test_nearest_half_matches_exhaustive_independent_search():
    for denominator in range(1, 37):
        for numerator in range(-2*denominator, 2*denominator+1):
            exact = Q(numerator, denominator)
            expected = min(abs(exact-Q(2*k+1, 2)) for k in range(-4, 4))
            row = M.nearest_half(numerator, denominator)
            assert row['distance_ulps'] == expected
            assert row['signed_delta'] == 2*numerator-(2*row['nearest_k']+1)*denominator
            assert row['delta'] <= denominator
            assert row['delta'] == row['reduced_delta']*gcd(numerator, denominator)


@pytest.mark.parametrize('p,q', [(0, 0), (3, -1), (Q(3), 2), (3, 2.0), (True, 1)])
def test_invalid_exact_phase_input_rejected(p, q):
    with pytest.raises(ValueError):
        M.nearest_half(p, q)


def test_factor_two_and_odd_boundary_mutations_have_witnesses():
    # Mod Q loses the odd/even multiple condition. It reports zero at p/q=0,
    # while the actual distance to the half-integer lattice is 1/2.
    correct = M.nearest_half(0, 7)
    assert correct['distance_ulps'] == Q(1, 2)
    assert abs((2*0 % 7)-7) != 0
    assert min(2*0 % 7, 7-2*0 % 7) != correct['delta']
    assert Q(correct['delta'], correct['Q']) != correct['distance_ulps']


def test_reduction_invariance_detects_unreduced_delta_inflation():
    for p, q in ((1, 3), (4, 7), (-7, 11), (1, 2)):
        a, b = M.nearest_half(p, q), M.nearest_half(p*2**34*5**8, q*2**34*5**8)
        assert a['distance_ulps'] == b['distance_ulps']
        assert a['reduced_delta'] == b['reduced_delta']
        assert a['reduced_Q'] == b['reduced_Q']
        assert b['delta'] == a['delta']*2**34*5**8


@pytest.mark.parametrize('moduli', [(4, 6), (6, 10, 15), (8, 16, 32), (1, 7), (3, 5, 7)])
def test_generalized_crt_against_complete_small_integer_search(moduli):
    modulus = lcm(*moduli)
    for x in range(modulus):
        congruences = tuple((x % m, m) for m in moduli)
        residue, combined = M.generalized_crt(congruences)
        expected = [n for n in range(modulus) if all(n % m == r for r, m in congruences)]
        assert combined == modulus and expected == [residue] == [x]


def test_crt_incompatible_and_invalid_modulus_faults():
    for data in (((0, 4), (1, 6)), ((2, 0),), ((0, -4),)):
        with pytest.raises(ValueError):
            M.generalized_crt(data)
    # Treating the shared factors as coprime gives 24, not the actual 12.
    assert M.generalized_crt(((2, 4), (2, 6))) == (2, 12)


@pytest.mark.parametrize('lo,hi,modulus', [(1, 3, 10), (5, 105, 7), (1, 30, 10), (29, 29, 3)])
def test_closed_domain_residue_counts_against_enumeration(lo, hi, modulus):
    counts = M.residue_counts(lo, hi, modulus)
    assert counts == tuple(sum(n % modulus == r for n in range(lo, hi+1)) for r in range(modulus))
    assert sum(counts) == hi-lo+1


def test_exact_valuations_survive_small_modulus_information_loss():
    p, q, _, _ = S.normal_form()
    n = 1071856711314178048
    pn, qn = sum(c*n**k for k, c in p.items()), sum(c*n**k for k, c in q.items())
    row = M.nearest_half(pn, qn)
    assert (row['v2_P'], row['v2_Q']) == (1557, 1555)
    assert pn % 2**16 == qn % 2**16 == 0
    assert row['v2_reduced_P'] == 2 and row['v2_reduced_Q'] == 0
    assert not row['exact_tie']


def test_inventory_sampling_and_scope_are_unchanged(report):
    prior = json.loads((ROOT/next(iter(M.PRIOR_HASHES))).read_text(encoding='utf-8'))
    assert [g['shell_index'] for g in report['groups']] == list(range(19))
    assert report['sample_count'] == sum(g['sample_count'] for g in report['groups'])
    for group, old in zip(report['groups'], prior['groups']):
        assert group['domain'] == old['domain']
        d = group['domain']
        points = M.sample_points(d['lo'], d['hi'])
        assert d['lo'] == points[0] and d['hi'] == points[-1]
        assert len(points) == len(set(points)) == group['sample_count'] <= 205
        assert sum(group['distance_bin_counts'].values()) == len(points)
        assert group['sample_scope'] == 'selected_inputs_only'
        assert group['family_delta_lower_bound'] is group['family_phase_lower_bound'] is None
        assert group['global_4_4b'] == 'NotCertified' and group['new_certified_regions'] == 0
        assert sum(group['domain_residue_inventory']['counts']) == group['lattice_point_count']
        assert group['domain_residue_inventory']['all_residues_present']
    assert report['prior_coverage'] == {'used_regions': 11, 'region_budget': 64,
                                      'gap_count': 84, 'scope': 'pinned_previous_certificate_report'}
    assert report['family_phase_lower_bounds_proved'] == report['new_certified_regions'] == 0
    assert report['coverage_modified'] is False and report['precision_cap'] == 16384
    assert report['classification_counts'] == {
        'shifted_phase_or_tighter_signed_bound_required': 4,
        'denominator_normalization_or_local_guard_required': 1,
        'stronger_modular_family_bound_required': 14}


def test_distribution_extrema_and_strict_required_M_recomputed(report):
    p, q, _, _ = S.normal_form()
    for group in report['groups']:
        d = group['domain']
        independent = []
        for n in M.sample_points(d['lo'], d['hi']):
            pn, qn = sum(c*n**k for k, c in p.items()), sum(c*n**k for k, c in q.items())
            delta = abs(2*pn % (2*qn)-qn)
            independent.append((Q(delta, 2*qn), n, delta))
        distance, n, _ = min(independent)
        assert group['observed_min_distance']['n'] == n
        assert group['observed_min_distance']['distance_ulps'] == distance
        assert group['observed_min_delta']['delta'] == min(x[2] for x in independent)
        guard = group['guard']
        m = guard['required_uniform_M_strict']
        target = 2*guard['Q_max']*guard['abs_guard_ulps']
        assert m-1 <= target < m
        assert guard['uniform_M_over_2Qmax_strategy_impossible'] == (m > guard['Q_min'])
        counterexample = guard['exact_sample_counterexample_to_required_M']
        assert (counterexample is not None) == (min(x[2] for x in independent) < m)
        if counterexample is not None:
            assert counterexample['delta'] < m


def test_fixed_modulus_zero_witness_is_not_full_delta_zero(report):
    p, q, _, dpoly = K.frozen_identity()
    for group in report['groups']:
        n = group['fixed_5_power_8_residue_distance_min']['witness_n']
        pn, qn, dn = (sum(c*n**k for k, c in poly.items()) for poly in (p, q, dpoly))
        assert 2*pn % 5**8 == 0
        assert M.nearest_half(pn, qn)['delta'] != 0
        factors = M.factor_arithmetic(n, pn, qn, dn)
        assert factors['pairwise_gcd'] != (1, 1, 1)
        assert factors['crt_delta_lower'] <= M.nearest_half(pn, qn)['delta']
        assert factors['bound_scope'] == 'this_input_only'


def test_CRT_candidate_flags_recomputed_only_over_declared_samples(report):
    p, q, _, dpoly = K.frozen_identity()
    assert report['sampled_CRT_candidate_shells'] == (15, 16, 17, 18)
    for group in report['groups']:
        d = group['domain']
        count = 0
        for n in M.sample_points(d['lo'], d['hi']):
            pn, qn, dn = (sum(c*n**k for k, c in poly.items()) for poly in (p, q, dpoly))
            # Independent comparison: all three congruences equal 2P modulo
            # their lcm. This bound discards the odd-multiple parity.
            modulus = lcm(5**8, n**17, dn*dn)
            residue = 2*pn % modulus
            lower = min(residue, modulus-residue)
            count += lower >= group['guard']['required_uniform_M_strict']
        assert count == group['crt_sample_points_meeting_uniform_M']
        assert (count == group['sample_count']) == group['crt_meets_uniform_M_on_all_samples']
        assert group['family_delta_lower_bound'] is None


def test_polynomial_modulus_identities_and_denominator_clearing(report):
    p, q, _, d = K.frozen_identity()
    structure = report['factor_structure']
    assert d[0] == 2**structure['D0_v2']*5**structure['D0_v5']
    assert structure['D0_after_2_5_removal'] == 1
    d_squared = {}
    for i, a in d.items():
        for j, b in d.items():
            d_squared[i+j] = d_squared.get(i+j, 0)+a*b
    for key, divisor in (('cleared_mod_D', d), ('cleared_mod_D_squared', d_squared)):
        obj, coefficients = structure[key], {}
        for i, a in obj['quotient'].items():
            for j, b in divisor.items():
                coefficients[i+j] = coefficients.get(i+j, 0)+a*b
        for i, a in obj['remainder'].items():
            coefficients[i] = coefficients.get(i, 0)+a
        assert {i: a for i, a in coefficients.items() if a} == {i: obj['multiplier']*2*a for i, a in p.items()}
    for n in (1, 5, 117*2**53, 119*2**53, 5629499534213129):
        pn, qn, dn = (sum(c*n**k for k, c in poly.items()) for poly in (p, q, d))
        assert d[0] % gcd(n, dn) == 0
        assert 2*pn % n == 2*p[0] % n
        truncated = sum(c*n**k for k, c in structure['mod_n_power_17_remainder'].items())
        assert truncated % n**17 == 2*pn % n**17
        for key, divisor in (('cleared_mod_D', dn), ('cleared_mod_D_squared', dn*dn)):
            obj = structure[key]
            quotient = sum(c*n**k for k, c in obj['quotient'].items())
            remainder = sum(c*n**k for k, c in obj['remainder'].items())
            assert obj['multiplier']*2*pn == quotient*divisor+remainder
            assert obj['unscaled_integer_congruence_claimed'] is False


def test_rational_remainder_must_not_be_used_as_unscaled_congruence():
    obj = M.cleared_remainder({1: 1}, {1: 2, 0: 1})
    assert obj['multiplier'] == 2 and obj['remainder'] == {0: -1}
    # At n=2, divisor=5, the unscaled remainder -1 is not 2 mod 5.
    assert obj['remainder'][0] % 5 != 2 % 5
    assert obj['remainder'][0] % 5 == obj['multiplier']*2 % 5


def test_survey_fixture_exact_reproduction(report):
    stored = json.loads((ROOT/'a_reference/fixtures/c1b1_modular_distance_survey_v1.json').read_text(encoding='utf-8'))
    assert json.loads(json.dumps(T.serial(report))) == stored


def test_independent_checker_rejects_survey_as_certificate(report):
    # Even a forged pass/status flag cannot turn this sampled object into
    # the whole-domain proof object required by the unchanged checker.
    obj = deepcopy(report['groups'][0])
    obj['version'] = K.VERSION
    obj['status'] = 'certified'
    obj['spacing_sufficient'] = True
    obj['family_phase_lower_bound'] = obj['observed_min_distance']['distance_ulps']
    with pytest.raises(O.NotCertified):
        K.verify_certificate(obj, obj['domain'])


@pytest.mark.parametrize('target,message', [
    ('a_reference/fixtures/c1b1_fractional_phase_survey_v1.json', 'fixture changed'),
    ('a_reference/c1b1_fractional_phase_survey.py', 'source binding changed')])
def test_source_and_fixture_binding_faults_rejected(monkeypatch, target, message):
    original = Path.read_bytes
    def wrong_bytes(path):
        if path == ROOT/target:
            return original(path)+b' '
        return original(path)
    monkeypatch.setattr(Path, 'read_bytes', wrong_bytes)
    with pytest.raises(O.NotCertified, match=message):
        M.example_report()


def test_mismatched_exact_decomposition_rejected(monkeypatch):
    original = K.frozen_identity
    def altered():
        p, q, terms, d = original()
        p = dict(p)
        p[0] += 1
        return p, q, terms, d
    monkeypatch.setattr(K, 'frozen_identity', altered)
    with pytest.raises(O.NotCertified, match='decompositions disagree'):
        M.example_report()


def test_denominator_factor_corruption_is_rejected():
    with pytest.raises(ValueError, match='factorization mismatch'):
        M.factor_arithmetic(3, 2, 5**8*3**17*7**2+1, 7)


def test_sample_membership_and_uniqueness_for_small_intervals():
    for lo, hi in ((1, 1), (2, 3), (100, 120), (1, 390625)):
        points = M.sample_points(lo, hi)
        assert min(points) == lo and max(points) == hi
        assert len(set(points)) == len(points) <= 205
        assert all(lo <= n <= hi for n in points)
