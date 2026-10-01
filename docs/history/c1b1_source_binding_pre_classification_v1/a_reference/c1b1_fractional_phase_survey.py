"""Exact formula survey for the 24 unresolved axis domains; not a certificate.

I is measured in momentum ulps, n is the positive relative FX raw integer.
No large input/boundary enumeration, changed physics, or coverage promotion.
"""
from fractions import Fraction as Q
from functools import lru_cache
from hashlib import sha256
from math import gcd, lcm
from pathlib import Path
import json

from a_reference import c1b1_axis_decision_bounds as A
from a_reference import c1b1_outer_bound as B
from a_reference import c1b1_outer_bootstrap as O
from a_reference import c1b1_rounding_regions as R
from a_reference import c1b1_rounding_diagnosis as T

VERSION = 'c1b1-fractional-phase-survey-v1'
RESIDUAL_BITS = 4096
ROOT = Path(__file__).resolve().parents[1]
PRIOR = 'a_reference/fixtures/c1b1_half_ulp_boundaries_v1.json'
PRIOR_SHA256 = '5874f229e5f87783c90713b6c0342ddf1e2290ae73753c02e3527624e928fd1f'


def _value(poly, x):
    return sum((c*x**k for k, c in poly.items()), 0)


def _divide(a, b):
    """Exact polynomial division over Q, used only for structural gcd."""
    a, quotient = dict(a), {}
    degree = max(b)
    while a and max(a) >= degree:
        k = max(a)-degree
        c = a[max(a)]/b[degree]
        quotient[k] = c
        a = A._padd(a, {j+k: -c*v for j, v in b.items()})
    return quotient, a


def _poly_gcd(a, b):
    while b:
        _, remainder = _divide(a, b)
        a, b = b, remainder
    return A._pscale(a, 1/a[max(a)])


def _integer_pair(p, q):
    multiplier = lcm(*(c.denominator for c in (*p.values(), *q.values())))
    p = {k: int(c*multiplier) for k, c in p.items()}
    q = {k: int(c*multiplier) for k, c in q.items()}
    content = gcd(*p.values(), *q.values())
    return ({k: c//content for k, c in p.items()},
            {k: c//content for k, c in q.items()})


@lru_cache(maxsize=1)
def normal_form():
    """Derivative of the frozen PES, exactly P(n)/Q(n) + exp residual.

    The rational derivative denominator is R^17 D(R)^2. Its numerator
    combines the retardation derivative and every inverse-power derivative.
    Polynomial gcd is removed before substituting R=n*2^-48.
    """
    A.proof_guard()
    leading, den, inverse, exponentials = A._representation()
    rd = A._padd(A._pmul({1: Q(1)}, A._pmul(den, A._pd(leading))),
                 A._pscale(A._pmul(A._padd(A._pscale(den, 6),
                     A._pmul({1: Q(1)}, A._pd(den))), leading), -1))
    d_inverse = A._pd(inverse)
    power = max(7, -min(d_inverse))
    den2 = A._pmul(den, den)
    p = A._padd(A._pmul(rd, {power-7: Q(1)}),
               A._pmul({k+power: c for k, c in d_inverse.items()}, den2))
    q = {k+power: c for k, c in den2.items()}
    common = _poly_gcd(p, q)
    p, rem_p = _divide(p, common)
    q, rem_q = _divide(q, common)
    if rem_p or rem_q:
        raise O.NotCertified('inexact polynomial cancellation')
    p = {k: -B.H/2/B.UP*c*B.UX**k for k, c in p.items()}
    q = {k: c*B.UX**k for k, c in q.items()}
    p, q = _integer_pair(p, q)
    if any(c <= 0 for c in q.values()):
        raise O.NotCertified('positive monotone Q(n) not proved')
    residual = {lam: A._pscale(A._padd(A._pd(poly), A._pscale(poly, -lam)),
                              -B.H/2/B.UP)
                for lam, poly in exponentials.items()}
    return p, q, residual, common


def phase(p, q):
    """Exact distance to Z+1/2, including negative p and unreduced q."""
    if type(p) is not int or type(q) is not int or q <= 0:
        raise O.NotCertified('integer P and positive integer Q required')
    residue = (2*p) % (2*q)
    return {'residue': residue, 'modulus': 2*q, 'distance': Q(abs(residue-q), 2*q),
            'exact_tie': residue == q, 'point_gcd': gcd(p, q),
            'reduced_denominator': q//gcd(p, q)}


def denominator_structure(q):
    den = {k: c*B.UX**k for k, c in A._representation()[1].items()}
    multiplier = lcm(*(c.denominator for c in den.values()))
    den = {k: int(c*multiplier) for k, c in den.items()}
    content = gcd(*den.values())
    den = {k: c//content for k, c in den.items()}
    scalar = Q(q[17], den[0]**2)
    rebuilt = {k+17: c*scalar for k, c in A._pmul(den, den).items()}
    if rebuilt != q or scalar <= 0 or scalar.denominator != 1:
        raise O.NotCertified('exact square denominator factorization failed')
    return {'scalar': scalar.numerator, 'n_power': 17, 'D_integer': den,
            'D_integer_content': gcd(*den.values()),
            'v2_Q_parity': 'v2(scalar)+17*v2(n) modulo 2'}


def _exp_neg(x, bits):
    if x < 0 or type(bits) is not int or bits < 128 or bits > 16384:
        raise O.NotCertified('bounded nonnegative exponential proof required')
    if x >= bits*A.C.LN2_UPPER:
        return Q(0), Q(1, 1 << bits)
    k = max(0, x.numerator.bit_length()-x.denominator.bit_length()+1)+8
    lo, hi = A.enclosure(-x, bits, k)
    return Q(lo, 1 << bits), Q(hi, 1 << bits)


def _multiply(x, y):
    values = [a*b for a in x for b in y]
    return min(values), max(values)


def residual_enclosure(a, b, terms, bits=RESIDUAL_BITS):
    """Signed mathematical residual; exact Laurent bounds plus EXP enclosure.

    Positive-radius monomials are monotone even for negative exponents.
    Sum term bounds without replacing signed intervals by magnitudes.
    """
    if not 20 <= a <= b:
        raise O.NotCertified('positive outer radius required')
    records, lower, upper = [], Q(0), Q(0)
    for lam, poly in sorted(terms.items()):
        pl = pu = Q(0)
        for k, c in poly.items():
            endpoints = c*a**k, c*b**k
            pl += min(endpoints)
            pu += max(endpoints)
        ex = _exp_neg(lam*b, bits)[0], _exp_neg(lam*a, bits)[1]
        lo, hi = _multiply((pl, pu), ex)
        lower, upper = lower+lo, upper+hi
        records.append({'lambda': lam, 'laurent': poly, 'polynomial_range': (pl, pu),
                        'exponential_range': ex, 'signed_range': (lo, hi)})
    return (lower, upper), tuple(records)


def _v2(n):
    if not n:
        raise ValueError('v2(0) is not finite')
    n = abs(n)
    return (n & -n).bit_length()-1


def _unique_valuation(poly, t):
    orders = [_v2(c)+k*t for k, c in poly.items()]
    m = min(orders)
    return m if orders.count(m) == 1 else None


def _residue_valuation(poly, t, odd_residue, bits=8):
    """v2 on n=2^t*u, u fixed modulo 2^bits; None if precision insufficient.

    Divide all terms by their common power of two before modular evaluation.
    Integer polynomials preserve congruence, so a nonzero residue gives an
    exact valuation for every integer in the class, not just its representative.
    """
    minimum = min(_v2(c)+k*t for k, c in poly.items())
    modulus = 1 << bits
    residue = sum((c//(1 << _v2(c)))*
                  pow(2, _v2(c)+k*t-minimum, modulus)*
                  pow(odd_residue, k, modulus) for k, c in poly.items()) % modulus
    return minimum+_v2(residue) if residue else None


def tie_structure(p, q, lo, hi, square=None):
    """Cheap 2-adic family survey. Equal minima remain explicitly unresolved.

    For n=2^t*u with u odd, a unique least-valuation term determines v2.
    A half-integer requires v2(P)-v2(Q)=-1, regardless of point cancellation.
    """
    records, refined = [], []
    if square is not None:
        rebuilt = {k+square['n_power']: c*square['scalar']
                   for k, c in A._pmul(square['D_integer'], square['D_integer']).items()}
        if rebuilt != q or square['scalar'] <= 0:
            raise O.NotCertified('unverified square denominator')
    def exclusion(vp, vq, t):
        if vp is not None and vq is not None and vp-vq != -1:
            return 'valuation_mismatch'
        if square is not None and vp is not None and (vp+1-_v2(square['scalar'])-square['n_power']*t) % 2:
            return 'square_denominator_valuation_parity'
        return None
    def refine(t, residue, bits, umin, umax):
        rp = _residue_valuation(p, t, residue, bits)
        rq = _residue_valuation(q, t, residue, bits)
        reason = exclusion(rp, rq, t)
        if reason is None and bits < 16:
            for j in range(16):
                child = residue+(j << bits)
                if umin+(child-umin) % (1 << (bits+4)) <= umax:
                    refine(t, child, bits+4, umin, umax)
        else:
            refined.append({'v2_n': t, 'odd_u_residue': residue, 'modulus': 1 << bits,
                            'v2_P': rp, 'v2_Q': rq, 'tie_excluded': reason is not None,
                            'reason': reason or 'valuation_unresolved_at_modulus_cap'})
    for t in range(hi.bit_length()):
        step = 1 << t
        first = (((lo+step-1)//step) | 1)*step
        if first > hi:
            continue
        vp, vq = _unique_valuation(p, t), _unique_valuation(q, t)
        reason = exclusion(vp, vq, t)
        excluded = reason is not None
        records.append({'v2_n': t, 'v2_P': vp, 'v2_Q': vq,
                        'tie_excluded': excluded,
                        'reason': reason or 'valuation_unresolved'})
        if not excluded:
            umin, umax = (lo+step-1)//step, hi//step
            for residue in range(1, 256, 2):
                first_u = umin+(residue-umin) % 256
                if first_u > umax:
                    continue
                refine(t, residue, 8, umin, umax)
    return {'method': 'unique_least_2_adic_term_then_bounded_odd_u_residues_and_square_parity',
            'modulus_cap': 65536,
            'classes': tuple(records), 'refined_classes': tuple(refined),
            'all_ties_excluded': all(x['tie_excluded'] for x in refined)}


def survey_domain(domain):
    A.proof_guard()
    checked = R.axis_domain(domain['axis'], domain['lo'], domain['hi'])
    if checked != domain or domain['lo'] <= 0:
        raise O.NotCertified('survey requires declared positive axis lattice domain')
    p, q, terms, _ = normal_form()
    lo, hi = domain['lo'], domain['hi']
    a, b = lo*B.UX, hi*B.UX
    qmax = _value(q, hi)
    spacing = Q(1, 2*qmax)
    residual, records = residual_enclosure(a, b, terms)
    magnitude = max(abs(x) for x in residual)
    attempts = []
    # If the residual guard alone already defeats this sufficient test,
    # increasing numerical precision cannot rescue this bound.
    schedule = (256,) if magnitude >= spacing else tuple(256 << k for k in range(7))
    for bits in schedule:
        error = A.axis_impulse_error(a, b, bits)/B.UP
        guard = residual[0]-error, residual[1]+error
        success = max(abs(x) for x in guard) < spacing
        attempts.append({'bits': bits, 'endpoint_error_upper_ulps': error,
                         'signed_guard_ulps': guard, 'spacing_sufficient': success})
        if success:
            break
    tie = tie_structure(p, q, lo, hi, denominator_structure(q))
    unresolved = [x for x in tie['refined_classes'] if not x['tie_excluded']]
    exceptions, exception_proofs = [], []
    count = 0
    for row in unresolved:
        step, modulus = 1 << row['v2_n'], row['modulus']
        umin, umax = (lo+step-1)//step, hi//step
        first = umin+(row['odd_u_residue']-umin) % modulus
        count += (umax-first)//modulus+1
    # Count BEFORE expanding. This is a finite fallback, not a lattice scan.
    if count <= 64:
        for row in unresolved:
            step, modulus = 1 << row['v2_n'], row['modulus']
            umin, umax = (lo+step-1)//step, hi//step
            first = umin+(row['odd_u_residue']-umin) % modulus
            for u in range(first, umax+1, modulus):
                raw = u*step
                rational_phase = phase(_value(p, raw), _value(q, raw))
                exceptions.append(raw)
                # Existing physical point proof, kept separate from rational tie test.
                point = tuple(raw if k == domain['axis'] else 0 for k in range(3))
                direct = None
                for point_bits in (128 << k for k in range(8)):
                    try:
                        direct = R.certify_finite_points((point,), bits=point_bits)
                        break
                    except O.NotCertified:
                        continue
                exception_proofs.append({'n': raw, 'rational_phase': rational_phase,
                                         'direct_point_certificate': direct})
        tie['all_ties_excluded_with_finite_fallback'] = all(not x['rational_phase']['exact_tie'] for x in exception_proofs)
    else:
        exceptions = None
        tie['all_ties_excluded_with_finite_fallback'] = False
    tie['finite_fallback_count'] = count
    success = attempts[-1]['spacing_sufficient']
    reason = ('spacing_reduces_to_tie_exclusion' if success else
              'residual_enclosure_exceeds_spacing' if magnitude >= spacing else
              'numeric_error_bound_exceeds_spacing_at_cap')
    witnesses = []
    for n in (lo, (lo+hi)//2, hi):
        pn, qn = _value(p, n), _value(q, n)
        witnesses.append({'n': n, 'P': pn, 'Q': qn, **phase(pn, qn)})
    odd_vp, odd_vq = _unique_valuation(p, 0), _unique_valuation(q, 0)
    odd_phase_order = (0 if odd_vp is not None and odd_vp >= 0 and odd_vq == 0 else None)
    return {'domain': domain, 'domain_hash': R.domain_hash(domain), 'status': 'survey_only',
            'lattice_point_count': hi-lo+1, 'radius_interval': (a, b),
            'Q_constant': False, 'Q_positive_monotone': True,
            'Q_power_of_two_family': False,
            'Q_power_of_two_exclusion': 'Q=5^8*n^17*D_integer(n)^2; unreduced Q always has factor 5',
            'Q_max': qmax, 'non_tie_spacing_lower_ulps': spacing,
            'residual_signed_range_ulps': residual,
            'residual_sign': 'positive' if residual[0] > 0 else 'negative' if residual[1] < 0 else 'undetermined',
            'residual_abs_upper_ulps': magnitude, 'residual_proof_bits': RESIDUAL_BITS,
            'residual_terms': records, 'precision_attempts': tuple(attempts),
            'spacing_sufficient': success, 'reason': reason, 'tie_structure': tie,
            'phase_witnesses': tuple(witnesses), 'phase_witness_scope': 'diagnostic_points_only',
            'two_adic_spacing_limit': {'odd_n_v2_P': odd_vp, 'odd_n_v2_Q': odd_vq,
                                      'odd_n_v2_of_2P_minus_oddQ': odd_phase_order,
                                      'stronger_than_unit_integer_gap_from_v2_alone': False},
            'family_phase_lower_bound': None, 'finite_exceptional_inputs': None if exceptions is None else tuple(exceptions),
            'finite_exception_proofs': tuple(exception_proofs),
            'next_obligation': ('independent_certificate_contract_and_check' if success and tie['all_ties_excluded_with_finite_fallback'] else
                                'exact_tie_exclusion' if success else 'signed_modular_family_bound'),
            'global_4_4b': 'NotCertified'}


def example_report():
    A.proof_guard()
    prior_path = ROOT/PRIOR
    if sha256(prior_path.read_bytes().replace(b'\r\n', b'\n')).hexdigest() != PRIOR_SHA256:
        raise O.NotCertified('prior domain inventory changed')
    prior = json.loads(prior_path.read_text(encoding='utf-8'))
    earlier_path = ROOT/'a_reference/fixtures/c1b1_rounding_regions_v1.json'
    if sha256(earlier_path.read_bytes().replace(b'\r\n', b'\n')).hexdigest() != prior['prior_fixture_sha256']:
        raise O.NotCertified('prior formula inventory changed')
    earlier = json.loads(earlier_path.read_text(encoding='utf-8'))
    for path, expected in {**earlier['source_sha256'], **prior['source_sha256']}.items():
        if sha256((ROOT/path).read_bytes().replace(b'\r\n', b'\n')).hexdigest() != expected:
            raise O.NotCertified('prior source provenance changed')
    p, q, terms, common = normal_form()
    groups = tuple({'shell_index': g['shell_index'], **survey_domain(g['certificate']['domain'])}
                   for g in prior['groups'] if g['certificate'].get('reason') == 'symbolic_boundary_family_required')
    if len(groups) != 24:
        raise O.NotCertified('expected all 24 unmodified obligations')
    return {'version': VERSION, 'status': 'survey_only', 'global_4_4b': 'NotCertified',
            'unit': 'momentum_ulp', 'n_unit': 'positive_relative_FX_raw',
            'identity': 'I(n)=P(n)/Q(n)+sum(exp(-lambda*n*UX)*Laurent_lambda(n*UX))',
            'normal_form': {'P': p, 'Q': q, 'degree_P': max(p), 'degree_Q': max(q),
                            'polynomial_gcd_removed_in_radius': common,
                            'joint_integer_content': gcd(*p.values(), *q.values()),
                            'exponential_laurent_terms': tuple({'lambda': x, 'laurent': v} for x, v in sorted(terms.items())),
                            'Q_structure': denominator_structure(q),
                            'point_gcd_scope': 'variable point cancellation; witnesses are not a family proof'},
            'groups': groups, 'spacing_sufficient_count': sum(g['spacing_sufficient'] for g in groups),
            'tie_excluded_count': sum(g['tie_structure']['all_ties_excluded'] for g in groups),
            'tie_excluded_with_finite_fallback_count': sum(g['tie_structure']['all_ties_excluded_with_finite_fallback'] for g in groups),
            'new_certified_regions': 0, 'coverage_modified': False, 'region_budget': 64,
            'precision_cap': 16384, 'prior_fixture_sha256': PRIOR_SHA256,
            'source_sha256': {str(Path(__file__).relative_to(ROOT)).replace('\\', '/'): sha256(Path(__file__).read_bytes().replace(b'\r\n', b'\n')).hexdigest()}}


if __name__ == '__main__':
    import sys
    output = json.dumps(T.serial(example_report()), indent=2)+'\n'
    if len(sys.argv) == 2:
        Path(sys.argv[1]).write_text(output, encoding='utf-8')
    else:
        print(output)
