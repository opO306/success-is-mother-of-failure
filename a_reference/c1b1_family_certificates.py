"""Build/check the five surveyed spacing families and compose fresh coverage.

The independent checker never imports this module or the survey. No stronger
bound for the other 19 domains is introduced here.
"""
from fractions import Fraction as Q
from hashlib import sha256
from pathlib import Path
import json

from a_numeric import FixedPoint
from a_reference import c1b1_fractional_phase_survey as S
from a_reference import c1b1_family_checker as K
from a_reference import c1b1_half_ulp_boundaries as H
from a_reference import c1b1_rounding_regions as R
from a_reference import c1b1_rounding_diagnosis as T
from a_reference import c1b1_two_atom as C
from a_reference import c1b1_outer_bootstrap as O
from a_reference import c1b1_axis_decision_bounds as A
from a_reference import c1b1_outer_bound as B
from a_reference import c1b1_rounding_completeness as D

ROOT = Path(__file__).resolve().parents[1]


def propose_certificate(domain):
    """Untrusted construction. A proposal acquires authority only after checking."""
    group = S.survey_domain(domain)
    p, q, terms, _ = S.normal_form()
    attempt = group['precision_attempts'][-1]
    tie = group['tie_structure']
    exceptions = group['finite_exception_proofs']
    cert = {'version': K.VERSION, 'status': 'certified', 'scope': K.SCOPE,
            'global_4_4b': 'NotCertified', 'domain': domain, 'domain_hash': R.domain_hash(domain),
            'foundation_sha256': K.FOUNDATION_HASHES,
            'P': tuple(sorted(p.items())), 'Q': tuple(sorted(q.items())),
            'D_integer': tuple(sorted(S.denominator_structure(q)['D_integer'].items())),
            'Q_scalar': 5**8, 'Q_max': group['Q_max'], 'lattice_point_count': group['lattice_point_count'],
            'exponential_terms': tuple({'lambda': lam, 'laurent': tuple(sorted(poly.items()))}
                                       for lam, poly in sorted(terms.items())),
            'residual_interval': group['residual_signed_range_ulps'], 'residual_bits': 4096,
            'numeric_error': attempt['endpoint_error_upper_ulps'], 'signed_guard': attempt['signed_guard_ulps'],
            'spacing_lower': group['non_tie_spacing_lower_ulps'],
            'physical_margin_lower': group['non_tie_spacing_lower_ulps']-group['residual_abs_upper_ulps'],
            'impulse_abs_upper': Q(sum(abs(c)*domain['hi']**k for k, c in p.items()), S._value(q, domain['lo']))+group['residual_abs_upper_ulps'],
            'required_bits': attempt['bits'], 'max_decision_bits': attempt['bits'],
            'tie_cover': {
                'classes': tuple({k: x[k] for k in ('v2_n', 'v2_P', 'v2_Q')} for x in tie['classes']),
                'leaves': tuple({'v2_n': x['v2_n'], 'residue': x['odd_u_residue'], 'modulus': x['modulus'],
                                 'v2_P': x['v2_P'], 'v2_Q': x['v2_Q']} for x in tie['refined_classes']),
                'exceptions': tuple({'n': x['n'], 'residue': x['rational_phase']['residue']} for x in exceptions)},
            'direct_exceptions': tuple({'n': x['n'], 'bits': x['direct_point_certificate']['bits']}
                                       for x in exceptions if x['direct_point_certificate'] is not None)}
    return json.loads(json.dumps(T.serial(cert)))


def certify_axis_domain(domain):
    cert = propose_certificate(domain)
    K.verify_certificate(cert, domain)
    return cert


def check_outgoing_coverage(run, p_cap, legacy_certificates, boundary_obligations, family_obligations):
    """Only externally checked whole domains enter fresh closed-integer coverage."""
    legacy_certificates = tuple(legacy_certificates)
    boundary_obligations, family_obligations = tuple(boundary_obligations), tuple(family_obligations)
    count = len(legacy_certificates)+len(boundary_obligations)+len(family_obligations)
    if count > R.MAX_REGIONS:
        raise O.NotCertified('fixed 64-region budget exceeded')
    previous = H.check_outgoing_coverage(run, p_cap, legacy_certificates, boundary_obligations)
    domains = [K.verify_certificate(cert, expected) for cert, expected in family_obligations]
    gaps = []
    for required in previous['uncovered_intervals']:
        lo, hi = required['raw_interval']
        covered = [(d['lo'], d['hi']) for d in domains if d['axis'] == required['axis']]
        gaps.extend({**required, 'raw_interval': gap} for gap in R._gaps(lo, hi, covered))
    return {**previous, 'version': K.VERSION, 'status': 'not_certified' if gaps else 'certified',
            'global_4_4b': 'NotCertified', 'used_regions': count,
            'uncovered_intervals': tuple(gaps), 'tail': D.certify_zero_tail() if not gaps else None}


def example_report():
    K.foundation_guard()
    # Provenance of the original 27 domains is frozen; no survey pass flag is used.
    prior_path = ROOT/S.PRIOR
    if sha256(prior_path.read_bytes().replace(b'\r\n', b'\n')).hexdigest() != S.PRIOR_SHA256:
        raise O.NotCertified('original obligation inventory changed')
    prior = json.loads(prior_path.read_text(encoding='utf-8'))
    groups = []
    for group in prior['groups']:
        if group['shell_index'] not in range(19, 24):
            continue
        domain = group['certificate']['domain']
        certificate = certify_axis_domain(domain)
        groups.append({'shell_index': group['shell_index'], 'expected_domain': domain, 'certificate': certificate})
    if len(groups) != 5:
        raise O.NotCertified('five complete obligations required')
    original = json.loads((ROOT/'a_reference/fixtures/c1b1_rounding_regions_v1.json').read_text(encoding='utf-8'))
    legacy = [R.certify_finite_points(original['finite_acceptance']['domain']['points'], bits=256)]
    for c in original['analytic_and_singleton_certificates']:
        d = c['domain']
        legacy.append(R.certify_finite_points(d['points'], bits=c['bits']) if d['kind'] == 'finite_points' else
                      R.certify_axis_zero_region(d['axis'], d['lo'], d['hi'], bits=c['bits']))
    boundaries = []
    for g in prior['groups']:
        if g['certificate']['status'] == 'certified':
            d = g['certificate']['domain']
            certificate = H.certify_axis_domain(d['axis'], d['lo'], d['hi'])
            boundaries.append((certificate, d))
    run = C.new_run(FixedPoint(96, 48), 40, (-10, 0, 0), (-1, 0, 0),
                    (10, 0, 0), (1, 0, 0), momentum_profile=FixedPoint(96, 80))
    families = tuple((g['certificate'], g['expected_domain']) for g in groups)
    coverage = check_outgoing_coverage(run, Q(2), legacy, boundaries, families)
    return {'version': K.VERSION, 'status': 'not_certified', 'global_4_4b': 'NotCertified',
            'groups': tuple(groups), 'certified_family_count': 5, 'remaining_family_count': 19,
            'coverage': coverage, 'prior_fixture_sha256': S.PRIOR_SHA256,
            'source_sha256': {str(Path(m.__file__).relative_to(ROOT)).replace('\\', '/'): sha256(Path(m.__file__).read_bytes().replace(b'\r\n', b'\n')).hexdigest()
                              for m in (K, S)} |
                             {'a_reference/c1b1_family_certificates.py': sha256(Path(__file__).read_bytes().replace(b'\r\n', b'\n')).hexdigest()}}


if __name__ == '__main__':
    import sys
    output = json.dumps(T.serial(example_report()), indent=2)+'\n'
    if len(sys.argv) == 2:
        Path(sys.argv[1]).write_text(output, encoding='utf-8')
    else:
        print(output)
