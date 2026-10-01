"""Independent family checks must see builder and proof-object defects."""
import ast
from copy import deepcopy
from fractions import Fraction as Q
from pathlib import Path
import json

import pytest

from a_reference import c1b1_family_certificates as F
from a_reference import c1b1_family_checker as K
from a_reference import c1b1_fractional_phase_survey as S
from a_reference import c1b1_outer_bootstrap as O
from a_reference import c1b1_axis_decision_bounds as A
from a_reference import c1b1_rounding_regions as R
from a_reference import c1b1_half_ulp_boundaries as H
from a_reference import c1b1_rounding_diagnosis as T
from a_reference import c1b1_two_atom as C
from a_numeric import FixedPoint

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module')
def report():
    return F.example_report()


def test_all_five_domains_certified_from_unmodified_obligations(report):
    prior = json.loads((ROOT/S.PRIOR).read_text(encoding='utf-8'))
    expected = {g['shell_index']: g['certificate']['domain'] for g in prior['groups']}
    assert [g['shell_index'] for g in report['groups']] == list(range(19, 24))
    assert [g['certificate']['required_bits'] for g in report['groups']] == [2048, 2048, 2048, 4096, 4096]
    for group in report['groups']:
        d = expected[group['shell_index']]
        assert K.verify_certificate(group['certificate'], d) == d == group['expected_domain']
    coverage = report['coverage']
    assert coverage['used_regions'] == 11 and coverage['region_budget'] == 64
    assert len(coverage['uncovered_intervals']) == 84
    assert coverage['global_4_4b'] == 'NotCertified' and report['global_4_4b'] == 'NotCertified'
    assert report['remaining_family_count'] == 19
    assert not set(range(19, 28)).intersection(x['shell_index'] for x in coverage['uncovered_intervals'])


def test_checker_does_not_import_or_call_builder_or_survey():
    tree = ast.parse(Path(K.__file__).read_text(encoding='utf-8'))
    names = [n.module or '' for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
    names += [x.name for n in ast.walk(tree) if isinstance(n, ast.Import) for x in n.names]
    names += [x.name for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) for x in n.names]
    assert not any('fractional_phase_survey' in n or 'family_certificates' in n for n in names)


def test_checker_runs_after_all_survey_functions_are_poisoned(report, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('checker called untrusted survey')
    for name in ('normal_form', 'survey_domain', 'residual_enclosure', 'tie_structure', '_value', '_residue_valuation'):
        monkeypatch.setattr(S, name, forbidden)
    for group in report['groups']:
        K.verify_certificate(group['certificate'], group['expected_domain'])


@pytest.mark.parametrize('fault', [
    'P', 'Q', 'D', 'scalar', 'exp_missing', 'exp_sign', 'qmax_small', 'qmax_wrong_end',
    'residual_shrink', 'residual_swap', 'residual_sign', 'error_shrink', 'guard_shrink',
    'spacing_up', 'margin_up', 'precision_low', 'precision_cap', 'precision_max',
    'residual_precision', 'count', 'domain_shrink', 'domain_axis', 'domain_hash',
    'source_hash', 'status', 'scope', 'global_promotion', 'overflow_bound', 'float_error',
    'tie_class_missing', 'tie_leaf_missing', 'tie_valuation', 'tie_duplicate', 'tie_extra',
])
def test_real_proof_object_faults_are_rejected(report, fault):
    group = report['groups'][0]
    cert = deepcopy(group['certificate'])
    if fault in ('P', 'Q'):
        cert[fault][0][1] += 1
    elif fault == 'D':
        cert['D_integer'][0][1] += 1
    elif fault == 'scalar':
        cert['Q_scalar'] += 1
    elif fault == 'exp_missing':
        cert['exponential_terms'].pop()
    elif fault == 'exp_sign':
        row = cert['exponential_terms'][0]['laurent'][0]
        row[1] = str(-Q(row[1]))
    elif fault == 'qmax_small':
        cert['Q_max'] -= 1
    elif fault == 'qmax_wrong_end':
        cert['Q_max'] = sum(c*cert['domain']['lo']**k for k, c in cert['Q'])
    elif fault == 'residual_shrink':
        cert['residual_interval'] = ['0', '0']
    elif fault == 'residual_swap':
        cert['residual_interval'].reverse()
    elif fault == 'residual_sign':
        cert['residual_interval'] = [str(-Q(x)) for x in cert['residual_interval'][::-1]]
    elif fault == 'error_shrink':
        cert['numeric_error'] = '0'
    elif fault == 'guard_shrink':
        cert['signed_guard'] = ['0', '0']
    elif fault == 'spacing_up':
        cert['spacing_lower'] = str(2*Q(cert['spacing_lower']))
    elif fault == 'margin_up':
        cert['physical_margin_lower'] = str(2*Q(cert['physical_margin_lower']))
    elif fault == 'precision_low':
        cert['required_bits'] = 256
        cert['max_decision_bits'] = 256
    elif fault == 'precision_cap':
        cert['required_bits'] = 32768
    elif fault == 'precision_max':
        cert['max_decision_bits'] = 128
    elif fault == 'residual_precision':
        cert['residual_bits'] = 8192
    elif fault == 'count':
        cert['lattice_point_count'] -= 1
    elif fault == 'domain_shrink':
        cert['domain']['lo'] += 1
        cert['domain_hash'] = R.domain_hash(cert['domain'])
    elif fault == 'domain_axis':
        cert['domain']['axis'] = 1
    elif fault == 'domain_hash':
        cert['domain_hash'] = '0'*64
    elif fault == 'source_hash':
        cert['foundation_sha256']['a_numeric/exp.py'] = '0'*64
    elif fault == 'status':
        cert['status'] = 'survey_only'
    elif fault == 'scope':
        cert['scope'] = 'whole_world'
    elif fault == 'global_promotion':
        cert['global_4_4b'] = 'Certified'
    elif fault == 'overflow_bound':
        cert['impulse_abs_upper'] = '0'
    elif fault == 'float_error':
        cert['numeric_error'] = 0.0
    elif fault == 'tie_class_missing':
        cert['tie_cover']['classes'].pop()
    elif fault == 'tie_leaf_missing':
        cert['tie_cover']['leaves'].pop()
    elif fault == 'tie_valuation':
        cert['tie_cover']['leaves'][0]['v2_P'] = -1
    elif fault == 'tie_duplicate':
        cert['tie_cover']['leaves'].append(cert['tie_cover']['leaves'][0])
    elif fault == 'tie_extra':
        cert['tie_cover']['leaves'].append({'v2_n': 0, 'residue': 1, 'modulus': 256, 'v2_P': 411, 'v2_Q': 0})
    with pytest.raises(O.NotCertified):
        K.verify_certificate(cert, group['expected_domain'])


@pytest.mark.parametrize('fault', ['omit', 'wrong_n', 'fake_residue', 'bits', 'direct_omit'])
def test_last_domain_finite_exception_cannot_be_hidden(report, fault):
    group = report['groups'][-1]
    cert = deepcopy(group['certificate'])
    assert cert['tie_cover']['exceptions'][0]['n'] == 1071856711314178048
    if fault == 'omit':
        cert['tie_cover']['exceptions'] = []
    elif fault == 'wrong_n':
        cert['tie_cover']['exceptions'][0]['n'] += 1
    elif fault == 'fake_residue':
        cert['tie_cover']['exceptions'][0]['residue'] = 1
    elif fault == 'bits':
        cert['direct_exceptions'][0]['bits'] = 8192
    else:
        cert['direct_exceptions'] = []
    with pytest.raises(O.NotCertified):
        K.verify_certificate(cert, group['expected_domain'])


def test_required_precision_must_fit_external_execution_ceiling(report):
    group = report['groups'][0]
    with pytest.raises(O.NotCertified, match='execution limit'):
        K.verify_certificate(group['certificate'], group['expected_domain'], execution_limit=1024)


def test_synthetic_exact_tie_is_never_excluded():
    # Noncanonical square denominator Q=5^8*n^17, P/Q=1/2 at n=2.
    proof = {'classes': [{'v2_n': 1, 'v2_P': 16, 'v2_Q': 17}],
             'leaves': [{'v2_n': 1, 'residue': 1, 'modulus': 256, 'v2_P': 16, 'v2_Q': 17}],
             'exceptions': [{'n': 2, 'residue': 5**8*2**17}]}
    with pytest.raises(O.NotCertified, match='exact tie'):
        K.check_tie_cover(proof, {0: 5**8*2**16}, {17: 5**8}, 2, 2)


def test_strict_equality_is_not_certifiable(report, monkeypatch):
    group = report['groups'][0]
    cert = deepcopy(group['certificate'])
    # Inject a numerical error exactly equal to the proved physical margin.
    target = Q(cert['physical_margin_lower'])
    numeric = lambda a, b, bits: target/Q(1 << 80)
    monkeypatch.setattr(A, 'axis_impulse_error', numeric)
    monkeypatch.setattr(K, '_ERROR_BINDING', numeric)
    cert['numeric_error'] = str(target)
    cert['signed_guard'] = [str(Q(cert['residual_interval'][0])-target),
                            str(Q(cert['residual_interval'][1])+target)]
    with pytest.raises(O.NotCertified, match='strict'):
        K.verify_certificate(cert, group['expected_domain'])


def test_changed_live_error_foundation_is_rejected(report, monkeypatch):
    group = report['groups'][0]
    monkeypatch.setattr(A, 'axis_impulse_error', lambda *args: Q(0))
    with pytest.raises(O.NotCertified, match='foundation changed'):
        K.verify_certificate(group['certificate'], group['expected_domain'])


def test_changed_numeric_helper_cannot_fake_small_error(report, monkeypatch):
    group = report['groups'][0]
    monkeypatch.setattr(A.Num, 'scale', lambda self, c: self)
    with pytest.raises(O.NotCertified, match='helper foundation changed'):
        K.verify_certificate(group['certificate'], group['expected_domain'])


@pytest.mark.parametrize('name', ['Num', 'Iv', 'enclosure'])
def test_rebinding_numeric_class_or_exp_alias_is_rejected(name, monkeypatch):
    monkeypatch.setattr(A, name, object())
    with pytest.raises(O.NotCertified, match='helper foundation changed'):
        K.foundation_guard()


def test_forged_survey_pass_cannot_certify_one_of_the_19(monkeypatch):
    prior = json.loads((ROOT/S.PRIOR).read_text(encoding='utf-8'))
    domain = prior['groups'][18]['certificate']['domain']
    original = S.survey_domain
    def forged(d):
        data = original(d)
        data['spacing_sufficient'] = True
        data['precision_attempts'][-1]['spacing_sufficient'] = True
        return data
    monkeypatch.setattr(S, 'survey_domain', forged)
    with pytest.raises(O.NotCertified, match='strict'):
        F.certify_axis_domain(domain)


def test_whole_closed_domain_endpoints_are_both_checked(report):
    group = report['groups'][0]
    certificate = group['certificate']
    lo, hi = group['expected_domain']['lo'], group['expected_domain']['hi']
    assert certificate['lattice_point_count'] == hi-lo+1
    for n in (lo, hi):
        point = R.certify_finite_points(((n, 0, 0),), bits=256)
        R.verify_region(point)
        assert C.impulse((Q(n, 1 << 48), Q(0), Q(0)), Q(20), FixedPoint(96, 80)) == point['outputs'][0]


def test_compositor_enforces_fixed_total_region_budget(report):
    run = C.new_run(FixedPoint(96, 48), 40, (-10, 0, 0), (-1, 0, 0),
                    (10, 0, 0), (1, 0, 0), momentum_profile=FixedPoint(96, 80))
    g = report['groups'][0]
    with pytest.raises(O.NotCertified, match='64-region'):
        F.check_outgoing_coverage(run, Q(2), (), (), [(g['certificate'], g['expected_domain'])]*65)


def test_json_proof_objects_are_self_contained_and_reproducible(report):
    wire = json.loads(json.dumps(T.serial(report)))
    for group in wire['groups']:
        K.verify_certificate(group['certificate'], group['expected_domain'])
    stored = json.loads((ROOT/'a_reference/fixtures/c1b1_family_certificates_rebound_v1.json').read_text(encoding='utf-8'))
    assert wire == stored
