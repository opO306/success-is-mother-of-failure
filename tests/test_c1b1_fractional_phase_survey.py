"""Formula and guard audit: structure survey must never promote completeness."""
from copy import deepcopy
from fractions import Fraction as Q
from math import factorial, gcd
from pathlib import Path
import json

import pytest

from a_reference import c1b1_fractional_phase_survey as S
from a_reference import c1b1_axis_decision_bounds as A
from a_reference import c1b1_outer_bound as B
from a_reference import c1b1_outer_bootstrap as O
from a_reference import c1b1_rounding_diagnosis as T
from a_reference import c1b1_rounding_regions as R
from a_reference import ar2_lang2024 as L

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module')
def report():
    return S.example_report()


def independent_rational(radius):
    """Different expression: directly differentiate each frozen PES component."""
    n = 1+sum(c*radius**(i+1) for i, c in enumerate(L.RET_A))
    d = 1+sum(c*radius**(i+1) for i, c in enumerate(L.RET_B))
    dn = sum((i+1)*c*radius**i for i, c in enumerate(L.RET_A))
    dd = sum((i+1)*c*radius**i for i, c in enumerate(L.RET_B))
    dv = Q(0)
    for name, (_, (_, coefficients, _)) in L.COMPONENTS.items():
        for k, c in coefficients.items():
            if k == min(coefficients) and name == 'BO':
                dv += -c*(dn*d-n*dd)/(d*d*radius**(2*k))
                dv += c*2*k*n/(d*radius**(2*k+1))
            elif not (k == min(coefficients) and name == 'REL'):
                dv += 2*k*c/radius**(2*k+1)
    return -20*dv/B.UP


def independent_exp_terms():
    """Different expansion: differentiate individual short/damping monomials."""
    out = {}
    def add(lam, k, c):
        pol = out.setdefault(lam, {})
        pol[k] = pol.get(k, Q(0))-20*c/B.UP
    for shorts, (eta, coefficients, extra) in L.COMPONENTS.values():
        for alpha, poly in shorts.values():
            for k, c in poly.items():
                if k:
                    add(alpha, k-1, k*c)
                add(alpha, k, -alpha*c)
        for k, c in coefficients.items():
            power = 2*k
            for i in range(power+extra+1):
                weight = c*eta**i/factorial(i)
                add(eta, i-power-1, (i-power)*weight)
                add(eta, i-power, -eta*weight)
    return {lam: {k: c for k, c in poly.items() if c} for lam, poly in out.items()}


def test_all_24_original_obligations_without_domain_shrink(report):
    prior = json.loads((ROOT/S.PRIOR).read_text(encoding='utf-8'))
    expected = [g['certificate']['domain'] for g in prior['groups'][:-3]]
    assert [g['domain'] for g in report['groups']] == expected
    assert [g['shell_index'] for g in report['groups']] == list(range(24))
    assert report['global_4_4b'] == 'NotCertified'
    assert report['status'] == 'survey_only'
    assert report['new_certified_regions'] == 0 and not report['coverage_modified']
    assert report['region_budget'] == 64 and report['precision_cap'] == 16384
    assert all(g['family_phase_lower_bound'] is None for g in report['groups'])
    assert [g['finite_exceptional_inputs'] for g in report['groups'][:-1]] == [()]*23
    assert report['groups'][-1]['finite_exceptional_inputs'] == (1071856711314178048,)


def test_integer_normal_form_and_exact_square_denominator(report):
    p, q, _, common = S.normal_form()
    assert max(p) == 22 and max(q) == 29
    assert common == {0: 1}
    assert gcd(*p.values(), *q.values()) == 1
    structure = S.denominator_structure(q)
    assert structure['scalar'] == 390625 == 5**8
    assert structure['n_power'] == 17
    assert max(structure['D_integer']) == 6
    assert structure['D_integer_content'] == 1
    assert all(c > 0 for c in q.values())
    assert all(c % 5 == 0 for c in q.values())
    assert all(not g['Q_constant'] and not g['Q_power_of_two_family'] for g in report['groups'])


@pytest.mark.parametrize('raw', [5629499534213129, 7000000000000000,
                               900000000000000000, 1100000000000000000])
def test_rational_identity_against_independent_exact_component_derivatives(raw):
    p, q, _, _ = S.normal_form()
    assert Q(S._value(p, raw), S._value(q, raw)) == independent_rational(raw*B.UX)


def test_residual_coefficients_against_independent_termwise_derivatives():
    assert S.normal_form()[2] == independent_exp_terms()


@pytest.mark.parametrize('raw', [5629499534213129, 7000000000000000,
                               900000000000000000, 1071856711314178048])
def test_combined_formula_inside_unchanged_physical_evaluator(raw):
    p, q, terms, _ = S.normal_form()
    radius = raw*B.UX
    skeleton = Q(S._value(p, raw), S._value(q, raw))
    residual, _ = S.residual_enclosure(radius, radius, terms)
    dv = A.C._model(radius*radius, 512, True)[1]
    lower, upper = -20*Q(dv[1], 1 << 512)/B.UP, -20*Q(dv[0], 1 << 512)/B.UP
    assert lower <= skeleton+residual[0] <= skeleton+residual[1] <= upper


@pytest.mark.parametrize('fault', ['drop_inverse', 'flip_retardation', 'wrong_units'])
def test_rational_audit_detects_wrong_formula(fault):
    p, q, _, _ = S.normal_form()
    p, q = dict(p), dict(q)
    if fault == 'drop_inverse':
        p[0] = 0
    elif fault == 'flip_retardation':
        p = {k: -c for k, c in p.items()}
    else:
        q = {k: 2*c for k, c in q.items()}
    raw = 5629499534213129
    assert Q(S._value(p, raw), S._value(q, raw)) != independent_rational(raw*B.UX)


@pytest.mark.parametrize('fault', ['drop_term', 'flip_sign'])
def test_residual_audit_detects_missing_or_reversed_term(fault):
    terms = deepcopy(S.normal_form()[2])
    key = next(iter(terms))
    if fault == 'drop_term':
        del terms[key]
    else:
        terms[key] = {k: -c for k, c in terms[key].items()}
    assert terms != independent_exp_terms()


@pytest.mark.parametrize('p,q', [(0, 1), (1, 2), (-1, 2), (-4, 3),
                                (123456789, 17), (-123456789, 18)])
def test_modular_phase_matches_direct_nearest_half_integer(p, q):
    value = Q(p, q)
    k = value.numerator//value.denominator
    direct = abs(value-Q(2*k+1, 2))
    assert S.phase(p, q)['distance'] == direct
    assert S.phase(p, q)['exact_tie'] == (direct == 0)


@pytest.mark.parametrize('p,q', [(1, 0), (1, -1), (Q(1, 2), 2)])
def test_phase_rejects_invalid_denominators_or_nonintegers(p, q):
    with pytest.raises(O.NotCertified):
        S.phase(p, q)


def test_signed_residual_keeps_direction_and_covers_whole_interval():
    # Test-only analytic e^-R and -e^-R; no physical reachability claim.
    for sign in (1, -1):
        bound, _ = S.residual_enclosure(Q(20), Q(25), {Q(1): {0: Q(sign)}}, bits=512)
        assert bound[0] > 0 if sign > 0 else bound[1] < 0
        for radius in (Q(20), Q(21), Q(25)):
            exact_enclosure = S._exp_neg(radius, 768)
            signed = S._multiply(exact_enclosure, (Q(sign), Q(sign)))
            assert bound[0] <= signed[0] <= signed[1] <= bound[1]
        wrong = tuple(-x for x in bound[::-1])
        assert not (wrong[0] <= signed[0] <= signed[1] <= wrong[1])


def test_spacing_and_signed_guard_are_exact_not_float_estimates(report):
    successes = [g for g in report['groups'] if g['spacing_sufficient']]
    assert [g['shell_index'] for g in successes] == [19, 20, 21, 22, 23]
    assert report['spacing_sufficient_count'] == 5
    assert [g['precision_attempts'][-1]['bits'] for g in successes] == [2048, 2048, 2048, 4096, 4096]
    for g in report['groups']:
        assert g['non_tie_spacing_lower_ulps'] == Q(1, 2*g['Q_max'])
        last = g['precision_attempts'][-1]
        error = last['endpoint_error_upper_ulps']
        lower, upper = g['residual_signed_range_ulps']
        assert last['signed_guard_ulps'] == (lower-error, upper+error)
        assert g['spacing_sufficient'] == (max(abs(x) for x in last['signed_guard_ulps']) < Q(1, 2*g['Q_max']))
        if not g['spacing_sufficient']:
            assert g['reason'] == 'residual_enclosure_exceeds_spacing'


def test_q_max_is_a_whole_domain_bound_and_point_reduction_is_not_a_family_claim(report):
    p, q, *_ = S.normal_form()
    for g in report['groups']:
        assert g['Q_max'] == S._value(q, g['domain']['hi'])
        for witness in g['phase_witnesses']:
            assert 0 < witness['Q'] <= g['Q_max']
            assert witness['point_gcd'] == gcd(witness['P'], witness['Q'])
            assert witness['distance'] == S.phase(witness['P'], witness['Q'])['distance']
        assert g['phase_witness_scope'] == 'diagnostic_points_only'
        assert g['two_adic_spacing_limit']['odd_n_v2_of_2P_minus_oddQ'] == 0
        assert not g['two_adic_spacing_limit']['stronger_than_unit_integer_gap_from_v2_alone']


def test_valuation_families_do_not_exclude_exact_ties():
    # Noncanonical synthetic formula P/Q=1/2 everywhere: every class is a tie.
    tie = S.tie_structure({0: 1}, {0: 2}, 1, 1000)
    assert not tie['all_ties_excluded']
    assert all(not x['tie_excluded'] for x in tie['refined_classes'])
    # Equal minima can cancel; unique-minimum inference must refuse them.
    assert S._unique_valuation({0: 1, 1: 1}, 0) is None
    assert S._residue_valuation({0: 1, 1: 1}, 0, 255, 8) is None


def test_square_factor_cannot_be_forged():
    p, q, *_ = S.normal_form()
    wrong = S.denominator_structure(q)
    wrong['scalar'] += 1
    with pytest.raises(O.NotCertified, match='square denominator'):
        S.tie_structure(p, q, 1, 100, wrong)


def test_odd_residue_valuation_holds_across_the_entire_class():
    pol = {0: 3, 1: 9, 2: 2}
    for t in (0, 2, 7):
        for u in (1, 3, 17, 127):
            bound = S._residue_valuation(pol, t, u, 8)
            if bound is not None:
                for repeat in (0, 1, 1000):
                    assert S._v2(S._value(pol, (u+256*repeat)*(1 << t))) == bound


def test_physical_tie_class_records_agree_with_exact_point_valuations(report):
    p, q, *_ = S.normal_form()
    for g in report['groups']:
        lo, hi = g['domain']['lo'], g['domain']['hi']
        for row in g['tie_structure']['refined_classes']:
            step, modulus = 1 << row['v2_n'], row['modulus']
            umin = (lo+step-1)//step
            u = umin+(row['odd_u_residue']-umin) % modulus
            raw = u*step
            assert lo <= raw <= hi and u % 2 == 1
            pn, qn = S._value(p, raw), S._value(q, raw)
            if row['v2_P'] is not None:
                assert row['v2_P'] == S._v2(pn)
            if row['v2_Q'] is not None:
                assert row['v2_Q'] == S._v2(qn)
            if row['tie_excluded']:
                assert not S.phase(pn, qn)['exact_tie']


def test_one_bounded_exception_reuses_existing_point_checker(report):
    assert report['tie_excluded_count'] == 23
    assert report['tie_excluded_with_finite_fallback_count'] == 24
    last = report['groups'][-1]
    assert last['tie_structure']['finite_fallback_count'] == 1
    exception = last['finite_exception_proofs'][0]
    assert not exception['rational_phase']['exact_tie']
    proof = exception['direct_point_certificate']
    R.verify_region(proof)
    assert proof['bits'] <= 256 and proof['status'] == 'certified'
    assert last['status'] == 'survey_only'


def test_source_drift_fails_closed(monkeypatch):
    monkeypatch.setattr(A.C, 'MAX_PRECISION_BITS', 32768)
    with pytest.raises(O.NotCertified):
        S.example_report()


def test_prior_inventory_hash_cannot_be_bypassed(monkeypatch):
    monkeypatch.setattr(S, 'PRIOR_SHA256', '0'*64)
    with pytest.raises(O.NotCertified, match='inventory changed'):
        S.example_report()


def test_wrong_axis_domain_is_refused():
    with pytest.raises(O.NotCertified):
        S.survey_domain(R.axis_domain(0, -6000000000000000, -5900000000000000))


def test_fixture_is_exactly_reproducible(report):
    stored = json.loads((ROOT/'a_reference/fixtures/c1b1_fractional_phase_survey_rebound_v1.json').read_text(encoding='utf-8'))
    assert json.loads(json.dumps(T.serial(report))) == stored
