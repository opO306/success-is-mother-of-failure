"""Whole-class coverage, exact normalization, and evidence-boundary faults."""
from collections import defaultdict
from copy import deepcopy
from math import gcd
from pathlib import Path
import json

import pytest

from a_reference import c1b1_residue_class_survey as V
from a_reference import c1b1_modular_distance_survey as M
from a_reference import c1b1_family_checker as K
from a_reference import c1b1_outer_bootstrap as O
from a_reference import c1b1_rounding_diagnosis as T

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module')
def report():
    return V.example_report()


def _value(poly, n):
    return sum(c*n**k for k, c in poly.items())


def _toy(lo, hi, required):
    p, d = {0: 3, 1: 2}, {0: 1, 2: 1}
    q = {17: 5**8, 19: 2*5**8, 21: 5**8}
    group = {'shell_index': -1, 'domain': {'kind': 'axis_lattice_interval', 'axis': 0, 'lo': lo, 'hi': hi},
             'guard': {'required_uniform_M_strict': required}}
    return V.survey_domain(group, p, q, d), p, q, d


@pytest.mark.parametrize('lo,hi,required', [(1, 150, 33), (90, 250, 1000), (1, 120, 2_000_000)])
def test_complete_small_domain_cover_and_lower_bounds_by_exhaustion(lo, hi, required):
    group, p, q, _ = _toy(lo, hi, required)
    visited = []
    for leaf in group['classes']:
        scale = 2**leaf['v2_n']*5**leaf['v5_n']
        points = list(range(leaf['first_n'], leaf['last_n']+1, scale*leaf['unit_modulus']))
        assert len(points) == leaf['input_count']
        visited.extend(points)
        for n in points:
            assert V._v(n, 2) == leaf['v2_n'] and V._v(n, 5) == leaf['v5_n']
            pn, qn = _value(p, n), _value(q, n)
            exact = abs(2*pn % (2*qn)-qn)
            assert exact > 0  # the toy satisfies the non-tie precondition
            assert exact >= leaf['delta_lower_for_this_whole_class']
            a, b = leaf['common_25_orders_lower']
            assert pn % (2**a*5**b) == qn % (2**a*5**b) == 0
            if leaf['resolution'] == 'actual_small_delta_input':
                assert len(points) == 1 and exact < required
    assert sorted(visited) == list(range(lo, hi+1))
    assert group['covered_input_count'] == hi-lo+1


def test_normalized_zero_residue_is_lower_bound_not_exact_valuation():
    # F(u)=u-1 at u=1 mod 2: zero in the probe only implies v2>=1.
    poly = {0: -1, 1: 1}
    info = V._info(poly, {0: 0, 1: 0}, 2, 0, 1, 1, 2)
    assert info == (1, False)
    assert V._v(_value(poly, 3), 2) == 1
    assert V._v(_value(poly, 5), 2) == 2


@pytest.mark.parametrize('prime,order,other', [(2, 0, 5**7), (2, 10, 5**3), (5, 0, 2**12), (5, 4, 2**7)])
def test_normalized_valuation_information_for_every_small_lift(prime, order, other):
    poly = {0: 5, 1: -10, 2: 5}
    orders = {k: V._v(c, prime) for k, c in poly.items()}
    scale, modulus = prime**order*other, 2**4*5**2
    for residue in (1, 3, 7, 9):
        lower, exact = V._info(poly, orders, prime, order, scale, residue, modulus)
        for j in range(12):
            value = _value(poly, scale*(residue+modulus*j))
            actual = V._v(value, prime)
            if actual is not None:
                assert actual >= lower
                if exact:
                    assert actual == lower


def test_integer_shift_and_normalization_are_coefficient_identities():
    poly = {0: -8, 1: 12, 3: 4}
    shifted = V._shift(poly, 7, 10)
    divided = V._divide_integer(shifted, 4)
    for j in range(-5, 6):
        assert _value(shifted, j) == _value(poly, 7+10*j)
        assert 4*_value(divided, j) == _value(poly, 7+10*j)
    with pytest.raises(O.NotCertified):
        V._divide_integer(shifted, 3)


@pytest.mark.parametrize('p,q,count,c2,c5,d2,p5,q5', [
    ({0: 1, 1: 1}, {0: 3, 1: 2}, 107, 0, 0, 0, (0, True), (0, True)),
    ({0: 2, 1: 3}, {0: 5, 1: 5}, 121, 0, 0, 2, (0, True), (1, True)),
    ({0: 0}, {0: 2}, 3, 4, 2, 4, (0, False), (0, False)),
])
def test_fixed_CRT_period_against_all_lifts_and_odd_multipliers(p, q, count, c2, c5, d2, p5, q5):
    result = V.fixed_crt_cover(p, q, count, c2, c5, d2, p5, q5, 2**100)
    modulus = result['parameter_period']
    total_min = None
    for j in range(count):
        pp, qq = _value(p, j), _value(q, j)
        residues = {(2*pp-h*qq) % modulus for h in range(1, 2*modulus, 2)}
        # Independent search among nonzero signed integers in [-W,W].
        minimum = min(abs(z) for z in range(-modulus, modulus+1) if z and z % modulus in residues)
        lower = 2**c2*5**c5*minimum
        total_min = lower if total_min is None else min(total_min, lower)
    assert result['covered_input_count'] == count
    assert total_min == result['whole_class_delta_lower_from_fixed_info']
    witness = result['surviving_fixed_congruence']
    assert witness['actual_full_delta_witness'] is False
    assert witness['variable_moduli_checked_by_this_witness'] is False


def test_zero_fixed_coset_does_not_imply_exact_tie():
    result = V.fixed_crt_cover({0: 1}, {0: 6}, 10, 0, 0, 0, (0, True), (0, True), 100)
    assert result['whole_class_delta_lower_from_fixed_info'] > 0
    assert any(row[1] == 0 for row in result['cosets'])
    assert result['surviving_fixed_congruence']['actual_full_delta_witness'] is False


def test_full_real_cover_is_disjoint_and_complete_without_enumerating_inputs(report):
    prior = json.loads((ROOT/V.PRIOR).read_text(encoding='utf-8'))
    for group, original in zip(report['groups'], prior['groups'][15:19]):
        assert group['domain'] == original['domain']
        lo, hi = group['domain']['lo'], group['domain']['hi']
        assert sum(row['input_count'] for row in group['classes']) == hi-lo+1
        by_valuation = defaultdict(list)
        for row in group['classes']:
            t, s = row['v2_n'], row['v5_n']
            scale = 2**t*5**s
            first, count = V._count((lo+scale-1)//scale, hi//scale, row['unit_residue'], row['unit_modulus'])
            assert row['unit_modulus'] % 10 == 0 and gcd(row['unit_residue'], 10) == 1
            assert count == row['input_count'] and first*scale == row['first_n']
            assert row['last_n'] == scale*(first+(count-1)*row['unit_modulus']) <= hi
            by_valuation[t, s].append(row)
        for (t, s), leaves in by_valuation.items():
            scale = 2**t*5**s
            ul, uh = (lo+scale-1)//scale, hi//scale
            for i, left in enumerate(leaves):
                for right in leaves[i+1:]:
                    m, n = left['unit_modulus'], right['unit_modulus']
                    a, b = left['unit_residue'], right['unit_residue']
                    if (a-b) % gcd(m, n):
                        continue
                    residue, period = M.generalized_crt(((a, m), (b, n)))
                    assert ul+(residue-ul) % period > uh, 'overlapping class inputs'


def test_partial_results_are_not_family_certification(report):
    assert [g['shell_index'] for g in report['groups']] == [15, 16, 17, 18]
    assert report['all_class_covers_complete'] is True
    assert report['family_lemma_candidate_count'] == report['new_certified_regions'] == 0
    assert report['actual_small_delta_input_count'] == 0
    assert report['coverage_modified'] is False and report['global_4_4b'] == 'NotCertified'
    assert report['precision_cap'] == 16384 and report['prior_coverage']['used_regions'] == 11
    assert report['prior_coverage']['gap_count'] == 84
    for group in report['groups']:
        assert group['unresolved_class_count'] > 0 and not group['family_lemma_candidate']
        assert group['proved_lower_bound_input_count']+group['unresolved_input_count'] == group['covered_input_count']
        for leaf in group['classes']:
            if leaf['resolution'] == 'parametric_CRT_unresolved':
                assert leaf['full_variable_modulus_feasibility'] == 'unresolved'
                assert leaf['fixed_CRT_cover']['surviving_fixed_congruence']['actual_full_delta_witness'] is False


def test_variable_modulus_does_not_become_constant_on_a_fixed_class(report):
    p, q, _, d = K.frozen_identity()
    for group in report['groups']:
        row = next(x for x in group['classes'] if x['v2_n'] == x['v5_n'] == 0 and x['input_count'] > 1)
        n = row['first_n']
        next_n = n+row['unit_modulus']
        g = 2**row['common_25_orders_lower'][0]*5**row['common_25_orders_lower'][1]
        assert _value(q, n)//g != _value(q, next_n)//g
        assert _value(d, n)**2 != _value(d, next_n)**2
        assert row['full_CRT_modulus_varies_with_parameter']


def test_real_normalization_hashes_and_pairwise_coprimality(report):
    p, q, _, d = K.frozen_identity()
    for group in report['groups']:
        # Cover each resolution plus an unresolved normalized valuation case.
        selected = {}
        for leaf in group['classes']:
            selected.setdefault(leaf['resolution'], leaf)
            if not leaf['common_25_cancellation_exact']:
                selected.setdefault('nonexact_25', leaf)
        for row in selected.values():
            count, start = row['input_count'], row['first_n']
            step = 2**row['v2_n']*5**row['v5_n']*row['unit_modulus']
            (c2, c5), info = row['common_25_orders_lower'], row['valuations_P2_P5_D2_D5']
            common = 2**c2*5**c5
            pp = V._divide_integer(V._shift(p, start, step, count == 1), common)
            qq = V._divide_integer(V._shift(q, start, step, count == 1), common)
            dd = V._divide_integer(V._shift(d, start, step, count == 1), 2**info[2][0]*5**info[3][0])
            assert V._hash_polynomials(pp, qq, dd) == row['normalized_polynomial_sha256']
            for j in (0, count-1):
                n = start+step*j
                assert common*_value(pp, j) == _value(p, n)
                assert common*_value(qq, j) == _value(q, n)
                if row['normalized_moduli_pairwise_coprime_proved']:
                    u = n//(2**row['v2_n']*5**row['v5_n'])
                    assert gcd(u, _value(dd, j)) == gcd(10, _value(dd, j)) == 1


def test_lossless_fixture_reproduction(report):
    stored = json.loads((ROOT/'a_reference/fixtures/c1b1_residue_class_survey_rebound_v1.json').read_text(encoding='utf-8'))
    assert V.packed_report(report) == stored
    assert V.unpacked_report(stored) == T.serial(report)


def test_existing_checker_rejects_forged_class_cover_certificate(report):
    obj = deepcopy(report['groups'][0])
    obj.update(version=K.VERSION, status='certified', family_lemma_candidate=True)
    with pytest.raises(O.NotCertified):
        K.verify_certificate(obj, obj['domain'])


def test_parent_inventory_hash_fault(monkeypatch):
    original = Path.read_bytes
    def modified(path):
        return original(path)+b' ' if path == ROOT/V.PRIOR else original(path)
    monkeypatch.setattr(Path, 'read_bytes', modified)
    with pytest.raises(O.NotCertified, match='prior exact-distance survey changed'):
        V.example_report()


def test_tie_precondition_cannot_be_silently_assumed(monkeypatch):
    monkeypatch.setattr(K, 'check_tie_cover', lambda *args: (1,))
    with pytest.raises(O.NotCertified, match='unexpected rational tie exceptions'):
        V.example_report()


def test_incomplete_class_cover_fails_closed(monkeypatch):
    original = V._count
    def omitted(lo, hi, residue, modulus):
        first, count = original(lo, hi, residue, modulus)
        return first, 0 if residue % 10 == 9 else count
    monkeypatch.setattr(V, '_count', omitted)
    with pytest.raises(O.NotCertified, match='cover input count mismatch'):
        _toy(1, 100, 33)


def test_denominator_identity_fault_fails_closed(monkeypatch):
    original = V._multiply
    def wrong(a, b):
        value = original(a, b)
        value[0] = value.get(0, 0)+1
        return value
    monkeypatch.setattr(V, '_multiply', wrong)
    with pytest.raises(O.NotCertified, match='denominator identity mismatch'):
        _toy(1, 3, 33)


def test_analysis_budget_never_promotes_incomplete_cover(monkeypatch):
    monkeypatch.setitem(V.POLICY, 'max_leaves_per_domain', 1)
    with pytest.raises(O.NotCertified, match='analysis leaf work budget exceeded'):
        _toy(1, 100, 33)


def test_variable_gcd_foundation_fault_rejected(monkeypatch):
    original = K.frozen_identity
    def wrong():
        p, q, e, d = original()
        d = dict(d)
        d[0] += 1
        return p, q, e, d
    monkeypatch.setattr(K, 'frozen_identity', wrong)
    with pytest.raises(O.NotCertified, match=r'gcd\(n,D\) fixed-factor foundation changed'):
        V.example_report()


def test_all_higher_fixed_prime_powers_preserve_only_the_2F_coset():
    # Exhaust all odd multipliers for small higher prime powers; v is coprime
    # to 10, as proved for a class with exact D valuations.
    for fixed, unit, p in ((5, 3, 7), (10, 7, 11), (4, 9, -3), (25, 11, 2)):
        for modulus in (2**5*5**3, 2**6*5**3):
            residues = {(2*p-h*fixed*unit) % modulus for h in range(1, 2*modulus, 2)}
            expected = {x for x in range(modulus) if (x-2*p+fixed) % (2*fixed) == 0}
            assert residues == expected
            # The closest nonzero member is at most 2F; it need not satisfy
            # divisibility by the variable odd factor unit.
            offset = (2*p-fixed) % (2*fixed)
            distance = 2*fixed if not offset else min(offset, 2*fixed-offset)
            assert 0 < distance <= 2*fixed


def test_primitive_class_fixed_power_obstruction_holds_in_all_four_shells(report):
    for group in report['groups']:
        leaf = next(x for x in group['classes'] if x['v2_n'] == x['v5_n'] == 0 and
                    x['unit_residue'] == 3 and x['unit_modulus'] == 10)
        test = leaf['full_fixed_prime_power_test']
        assert test['raw_nonzero_compatible_gap_upper_orders'] == (1, 8)
        assert 2*5**8 < group['required_M']
        assert test['all_higher_2_5_moduli_same_coset_proved']
        assert test['small_gap_compatible_for_every_parameter_proved']
        assert test['actual_full_delta_witness'] is False
