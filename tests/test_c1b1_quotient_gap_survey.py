"""Independent exhaustion of necessary quotient constraints and fault probes."""
from fractions import Fraction as F
from hashlib import sha256
from pathlib import Path
import json

import pytest

from a_reference import c1b1_quotient_gap_survey as S
from a_reference import c1b1_residue_class_survey as V
from a_reference import c1b1_modular_distance_survey as M
from a_reference import c1b1_family_checker as K
from a_reference import c1b1_outer_bootstrap as O
from a_reference import c1b1_rounding_diagnosis as T

ROOT = Path(__file__).resolve().parents[1]


def at(poly, j):
    return sum(c*j**k for k, c in poly.items())


@pytest.mark.parametrize('m,g,want', [(10, 3, 4), (9, 3, 3), (1, 10, 1), (101, 100, 2)])
def test_reduction_changes_threshold(m, g, want):
    assert S.ceil_div(m, g) == want
    for z in range(-30, 31):
        assert (g*abs(z) >= m) == (abs(z) >= want)


@pytest.mark.parametrize('m,g', [(0, 1), (1, 0), (-1, 2), (1, 1.0)])
def test_invalid_reduction_rejected(m, g):
    with pytest.raises(ValueError):
        S.ceil_div(m, g)


@pytest.mark.parametrize('poly,end', [({0: 3, 1: -2, 2: 1}, 20), ({0: -1, 2: 4, 3: -1}, 15)])
def test_bernstein_encloses_every_real_grid_value(poly, end):
    controls = S.bernstein(poly, end, 5)
    for k in range(end*8+1):
        assert min(controls) <= at(poly, F(k, 8)) <= max(controls)


def test_ratio_positive_weight_enclosure_and_sign_refusal():
    numerator, denominator = {0: -7, 1: 5, 2: -2}, {0: 2, 2: 1}
    lo, hi = S.ratio_range(numerator, denominator, 11)
    for k in range(89):
        j = F(k, 8)
        assert lo <= at(numerator, j)/at(denominator, j) <= hi
    assert S.ratio_range({0: 1}, {0: -1, 1: 1}, 3) is None


@pytest.mark.parametrize('p,q,divisor,cofactor,c,a,rem', [
    ({0: 3}, {0: 6}, {0: 6}, {0: 1}, 1, {0: 1}, {}),
    ({0: 6}, {0: 6}, {0: 6}, {0: 1}, 1, {0: 2}, {}),
    ({0: 2}, {0: 2}, {0: 2}, {0: 1}, 2, {0: 4}, {}),
    ({0: 1}, {0: 2}, {0: 2}, {0: 1}, 2, {0: 2}, {}),
    ({0: 2}, {0: 12}, {0: 4}, {0: 3}, 2, {0: 2}, {}),
])
def test_zero_remainder_keeps_parity_cofactor_and_noninvertible_multiplier(p,q,divisor,cofactor,c,a,rem):
    result = S.range_exclusion(p,q,divisor,cofactor,c,a,rem,100,1)
    exact = min(abs(2*at(p,0)-h*at(q,0)) for h in range(-11,12,2))
    assert (result['resolution'] == 'whole_class_lower_bound') == (exact >= 1)
    assert result['multiplier_inverse_assumed'] is False


@pytest.mark.parametrize('required', [1, 3, 10, 31])
def test_joint_bounds_against_all_inputs_and_odd_quotients(required):
    # 2P=A*D+R; Q=B*D. Vary every piece with the same j.
    divisor, cofactor, a, rem = {0: 3, 1: 2}, {0: 1, 1: 2}, {0: 2, 1: -2}, {0: 2, 1: 2}
    q = V._multiply(divisor, cofactor)
    numerator2 = S._add(V._multiply(a, divisor), rem)
    p = V._divide_integer(numerator2, 2)
    result = S.range_exclusion(p,q,divisor,cofactor,1,a,rem,13,required)
    minimum = min(min(abs(2*at(p,j)-h*at(q,j)) for h in range(-101,102,2)) for j in range(13))
    if result['resolution'] == 'whole_class_lower_bound':
        assert minimum >= required
    assert result['actual_small_gap_witness'] is None
    for j in range(13):
        for h in range(-101,102,2):
            z = 2*at(p,j)-h*at(q,j)
            k = at(a,j)-h*at(cofactor,j)
            assert z == k*at(divisor,j)+at(rem,j)
            assert (k-result['k_coset']['residue']) % result['k_coset']['modulus'] == 0
            if abs(z) < required:
                assert result['h_integer_range'][0] <= h <= result['h_integer_range'][1]
                assert result['k_integer_range'][0] <= k <= result['k_integer_range'][1]


def test_overlap_is_not_existence_and_remainder_sign_is_insufficient():
    # The continuous quotient interval contains an odd h even though no integer
    # j is a tie. A coarse range must remain unresolved, not manufacture a tie.
    result = S.range_exclusion({0: 1, 1: 2}, {0: 4}, {0: 4}, {0: 1},
                               1, {}, {0: 2, 1: 4}, 2, 1)
    assert result['resolution'] == 'unresolved'
    assert result['actual_small_gap_witness'] is None
    assert all(abs((2*(1+2*j) % 8)-4) == 2 for j in (0,1))


@pytest.mark.parametrize('fault', ['remainder', 'divisor', 'cofactor', 'multiplier'])
def test_corrupted_identities_are_rejected(fault):
    args = [{0: 6}, {0: 6}, {0: 6}, {0: 1}, 1, {0: 2}, {}]
    index = {'remainder': 6, 'divisor': 2, 'cofactor': 3, 'multiplier': 4}[fault]
    args[index] = args[index]+1 if index == 4 else {0: 99}
    with pytest.raises(O.NotCertified):
        S.range_exclusion(*args, 10, 1)


def test_odd_condition_fault_changes_result_and_is_detected(monkeypatch):
    # Replacing the odd k coset by all integers loses a real whole-class bound.
    args = ({0: 2, 1: 4}, {0: 8}, {0: 8}, {0: 1}, 2, {0: 1, 1: 2}, {})
    correct = S.range_exclusion(*args, 2, 1)
    assert correct['resolution'] == 'whole_class_lower_bound'
    monkeypatch.setattr(S, 'quotient_lattice', lambda *args: (0, 1))
    mutated = S.range_exclusion(*args, 2, 1)
    assert mutated['resolution'] == 'unresolved'
    assert mutated != correct


@pytest.fixture(scope='module')
def stored():
    return json.loads((ROOT/'a_reference/fixtures/c1b1_quotient_gap_survey_v1.json').read_text())


def test_real_inventory_and_evidence_boundaries(stored):
    prior = V.unpacked_report(json.loads((ROOT/S.PRIOR).read_text()))
    assert stored['status'] == 'survey_only' and stored['global_4_4b'] == 'NotCertified'
    assert stored['precision_cap'] == 16384 and stored['new_certified_regions'] == 0
    assert stored['coverage_modified'] is False
    assert stored['prior_coverage']['used_regions'] == 11 and stored['prior_coverage']['gap_count'] == 84
    assert stored['interval_overlap_implies_actual_input'] is False
    assert stored['multiplier_inverse_assumed'] is False
    assert stored['full_impulse_certified_by_rational_gap_alone'] is False
    assert [g['shell_index'] for g in stored['groups']] == [18,17,16,15]
    assert sum(g['class_count'] for g in stored['groups']) == 14271
    for group in stored['groups']:
        old = next(g for g in prior['groups'] if g['shell_index'] == group['shell_index'])
        assert group['domain'] == old['domain']
        assert [row[0] for row in group['class_rows']] == list(range(len(old['classes'])))
        assert sum(row[5] for row in group['class_rows']) == old['covered_input_count']
        for row, original in zip(group['class_rows'], old['classes']):
            g = 2**original['common_25_orders_lower'][0]*5**original['common_25_orders_lower'][1]
            assert row[3] == (old['required_M']+g-1)//g
            if row[1] == 'whole_class_lower_bound':
                assert row[4] >= row[3]
            else:
                assert row[4] == 0


def test_real_diagnostic_examples_recompute_from_exact_class_identities(stored):
    prior = V.unpacked_report(json.loads((ROOT/S.PRIOR).read_text()))
    p,q,_,d = K.frozen_identity()
    raw = M.cleared_remainder({k: 2*c for k,c in p.items()}, V._power(d,2))
    for group in stored['groups']:
        old = next(g for g in prior['groups'] if g['shell_index'] == group['shell_index'])
        for example in group['diagnostic_examples'].values():
            row = old['classes'][example['prior_class_index']]
            actual = S.analyze_class(p,q,d,raw,row,old['required_M'])
            assert T.serial(actual) == {k:v for k,v in example.items() if k not in ('shell_index','prior_class_index')}
            if row['input_count'] > 1 and actual['reason'] != 'prior_whole_class_lower_bound':
                pp,qq,div,b,c,a,r,g = S.normalized_identity(p,q,d,raw,row)
                assert max(pp) == 22 and max(qq) == 29
                for j in (0,row['input_count']-1):
                    assert c*2*at(pp,j) == at(a,j)*at(div,j)+at(r,j)
                    assert at(qq,j) == at(b,j)*at(div,j)


def test_fixture_source_binding(stored):
    for name,digest in stored['source_sha256'].items():
        assert sha256((ROOT/name).read_bytes().replace(b'\r\n',b'\n')).hexdigest() == digest


def test_real_full_input_witness_is_only_a_sufficient_condition_counterexample():
    prior = V.unpacked_report(json.loads((ROOT/S.PRIOR).read_text()))
    row = next(x for x in prior['groups'][-1]['classes'] if 1 < x['input_count'] <= 8)
    p,q,_,d = K.frozen_identity()
    raw = M.cleared_remainder({k: 2*c for k,c in p.items()}, V._power(d,2))
    # Deliberately strengthen M to force a real sufficient-condition failure.
    # This synthetic threshold is never recorded as a failure of the real M.
    required = at(q,row['first_n'])+1
    result = S.analyze_class(p,q,d,raw,row,required)
    assert result['resolution'] == 'actual_small_gap_input'
    witness = result['actual_small_gap_witness']
    assert witness['raw_gap'] < required
    assert witness['odd_h'] % 2 == 1
    assert 2*witness['P_prime']-witness['odd_h']*witness['Q_prime'] == witness['signed_gap']
    assert witness['full_impulse_rounding_failure_proved'] is False
    assert witness['precision_cap_exceeded_proved'] is False


def test_normalized_polynomial_fault_is_rejected():
    prior = V.unpacked_report(json.loads((ROOT/S.PRIOR).read_text()))
    row = next(dict(x) for x in prior['groups'][-1]['classes'] if x['resolution'] == 'parametric_CRT_unresolved')
    row['normalized_polynomial_sha256'] = '0'*64
    p,q,_,d = K.frozen_identity()
    raw = M.cleared_remainder({k: 2*c for k,c in p.items()}, V._power(d,2))
    with pytest.raises(O.NotCertified,match='normalized class polynomial hash mismatch'):
        S.normalized_identity(p,q,d,raw,row)


def test_shell_inventory_fault_cannot_claim_complete_cover(monkeypatch):
    monkeypatch.setitem(S.POLICY,'shell_order',(18,17,16))
    with pytest.raises(O.NotCertified,match='shell inventory incomplete or repeated'):
        S.example_report()


def test_prior_inventory_fault_is_rejected(monkeypatch):
    original = Path.read_bytes
    monkeypatch.setattr(Path,'read_bytes',lambda p: original(p)+b' ' if p == ROOT/S.PRIOR else original(p))
    with pytest.raises(O.NotCertified,match='prior class fixture changed'):
        S.example_report()


def test_existing_checker_refuses_survey_with_forged_status(stored):
    group = dict(stored['groups'][0],version=K.VERSION,status='certified')
    with pytest.raises(O.NotCertified):
        K.verify_certificate(group,group['domain'])
