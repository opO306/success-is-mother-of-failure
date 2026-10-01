"""Check rational-spacing family proofs without importing the survey/builder.

Rebuild the frozen PES identity term by term. Reuse only the source-bound
numeric endpoint error lemma and integer EXP enclosure as trusted foundations.
Certificates are JSON-compatible exact integers/canonical rational strings.
"""
from fractions import Fraction as F
from hashlib import sha256
from math import factorial, gcd, lcm
from pathlib import Path
import re

from a_numeric import exp as E
from a_reference import ar2_lang2024 as L
from a_reference import c1b1_axis_decision_bounds as A
from a_reference import c1b1_outer_bootstrap as O
from a_reference import c1b1_rounding_regions as R
from a_reference import c1b1_source_binding as S

VERSION = 'c1b1-rational-spacing-family-v1'
SCOPE = 'declared_positive_axis_lattice_domain_only'
ROOT = Path(__file__).resolve().parents[1]
FOUNDATION_HASHES = {
    'a_reference/ar2_lang2024.py': '2a454adf1ca6ce1f27ae7e9e6f622a9d6d6c9a576ff2c59d5a48e62264977959',
    'a_reference/c1b1_axis_decision_bounds.py': '3ff1590322cd9dbb7c34b345a56cac35ad649a5c3881661fb3a1ec8bebd7c68c',
    'a_reference/c1b1_rounding_regions.py': '3a3e0223bde14795fb8d3da02ff3bd1816595b20d63bb6b2ec227ef909f49f58',
    'a_reference/c1b1_two_atom.py': 'e5889e8af2901eaa594b9b593a2c47048c61a4b4811bb0af04fb6c5d25c32c0e',
    'a_numeric/exp.py': '33522adcb4cc07cac5c65ec26187993d0b43efd214a7b846c2a207605108d58b',
}
_ERROR_BINDING = A.axis_impulse_error
_RATIO_BINDING = A.evaluator_ratio_error
_HELPER_BINDINGS = tuple((owner, name, vars(owner)[name]) for owner, names in (
    (A, ('Num', 'Iv', 'enclosure', '_up', 'G_ceil', 'exp_endpoint_error', 'exp_range', '_representation', '_padd', '_pmul', '_pd', '_pscale')),
    (A.Num, ('exact', 'const', '_new', '__add__', '__neg__', '__mul__', 'scale', 'div', 'exp')),
    (A.Iv, ('of', 'outward', '__add__', '__neg__', '__sub__', '__mul__', 'reciprocal', '__pow__', 'magnitude')),
) for name in names)


def _require(condition, reason):
    if not condition:
        raise O.NotCertified(reason)


def _int(x):
    _require(type(x) is int, 'exact integer required')
    return x


def _fraction(x):
    if type(x) is int:
        return F(x)
    _require(type(x) is str and re.fullmatch(r'-?\d+(?:/[1-9]\d*)?', x), 'canonical exact rational required')
    value = F(x)
    _require(str(value) == x, 'noncanonical rational')
    return value


def foundation_guard():
    A.proof_guard()
    _require(A.axis_impulse_error is _ERROR_BINDING and A.evaluator_ratio_error is _RATIO_BINDING,
             'live numeric error foundation changed')
    _require(A.MATH_BITS == 512 and all(vars(owner).get(name) is original for owner, name, original in _HELPER_BINDINGS),
             'live numeric helper foundation changed')
    for path, expected in FOUNDATION_HASHES.items():
        _require(S.source_matches(ROOT/path, expected),
                 'family foundation source changed')


def _add(*polys):
    result = {}
    for poly in polys:
        for degree, value in poly.items():
            result[degree] = result.get(degree, F(0))+value
    return {k: v for k, v in result.items() if v}


def _multiply(p, q):
    result = {}
    for i, a in p.items():
        for j, b in q.items():
            result[i+j] = result.get(i+j, F(0))+a*b
    return {k: v for k, v in result.items() if v}


def _scaled(p, scale, shift=0):
    return {k+shift: v*scale for k, v in p.items() if v*scale}


def _differentiate(p):
    return {k-1: k*c for k, c in p.items() if k*c}


def _at(p, n):
    return sum((c*n**k for k, c in p.items()), 0)


def frozen_identity():
    """Independent construction from each component, not survey representation."""
    den = {0: F(1), **{i+1: c for i, c in enumerate(L.RET_B)}}
    num = {0: F(1), **{i+1: c for i, c in enumerate(L.RET_A)}}
    den2 = _multiply(den, den)
    numerator, exponential = {}, {}
    def exp_add(lam, k, c):
        poly = exponential.setdefault(lam, {})
        poly[k] = poly.get(k, F(0))-20*c/(F(1, 1 << 80))
    for name, (shorts, (eta, coefficients, extra)) in L.COMPONENTS.items():
        for alpha, poly in shorts.values():
            for k, c in poly.items():
                if k:
                    exp_add(alpha, k-1, k*c)
                exp_add(alpha, k, -alpha*c)
        for k, c in coefficients.items():
            if name == 'BO' and k == min(coefficients):
                # d[-c N/(D R^6)]: quotient derivative plus R^-6 derivative.
                part = _add(_scaled(_multiply(_differentiate(num), den), -c, 11),
                            _scaled(_multiply(num, _differentiate(den)), c, 11),
                            _scaled(_multiply(num, den), 6*c, 10))
                numerator = _add(numerator, part)
            elif not (name == 'REL' and k == min(coefficients)):
                numerator = _add(numerator, _scaled(den2, 2*k*c, 16-2*k))
            for i in range(2*k+extra+1):
                weight = c*eta**i/factorial(i)
                exp_add(eta, i-2*k-1, (i-2*k)*weight)
                exp_add(eta, i-2*k, -eta*weight)
    ux, up = F(1, 1 << 48), F(1, 1 << 80)
    p = {k: -20*c*ux**k/up for k, c in numerator.items()}
    q = {k+17: c*ux**(k+17) for k, c in den2.items()}
    multiplier = lcm(*(c.denominator for c in (*p.values(), *q.values())))
    pi, qi = ({k: int(c*multiplier) for k, c in poly.items()} for poly in (p, q))
    content = gcd(*pi.values(), *qi.values())
    pi, qi = ({k: c//content for k, c in poly.items()} for poly in (pi, qi))
    exponential = {lam: {k: c for k, c in poly.items() if c} for lam, poly in exponential.items()}
    raw_den = {k: c*ux**k for k, c in den.items()}
    dm = lcm(*(c.denominator for c in raw_den.values()))
    di = {k: int(c*dm) for k, c in raw_den.items()}
    dc = gcd(*di.values())
    di = {k: c//dc for k, c in di.items()}
    _require(qi == {k+17: c*5**8 for k, c in _multiply(di, di).items()}, 'frozen square identity changed')
    return pi, qi, exponential, di


def _poly(rows, rational=False):
    _require(type(rows) in (tuple, list) and rows, 'polynomial rows required')
    pairs = [(_int(row[0]), _fraction(row[1]) if rational else _int(row[1])) for row in rows]
    _require(len({k for k, _ in pairs}) == len(pairs) and all(c for _, c in pairs), 'duplicate/zero polynomial term')
    return dict(pairs)


def _exp(x, bits):
    if x >= bits*F(6932, 10000):
        return F(0), F(1, 1 << bits)
    k = max(0, x.numerator.bit_length()-x.denominator.bit_length()+1)+8
    lo, hi = E.enclosure(-x, bits, k)
    return F(lo, 1 << bits), F(hi, 1 << bits)


def residual_range(a, b, terms, bits):
    lower = upper = F(0)
    for lam, poly in terms.items():
        pl = pu = F(0)
        for k, c in poly.items():
            l, u = sorted((c*a**k, c*b**k))
            pl, pu = pl+l, pu+u
        el, eu = _exp(lam*b, bits)[0], _exp(lam*a, bits)[1]
        products = (pl*el, pl*eu, pu*el, pu*eu)
        lower, upper = lower+min(products), upper+max(products)
    return lower, upper


def _v2(n):
    n = abs(n)
    _require(n > 0, 'finite valuation required')
    return (n & -n).bit_length()-1


def _valuation(poly, t, residue=None, modulus=None):
    base = min(_v2(c)+k*t for k, c in poly.items())
    if residue is None:
        return base if sum(_v2(c)+k*t == base for k, c in poly.items()) == 1 else None
    # Exact divisibility of normalized polynomial, evaluated by modular Horner.
    normalized = {k: (c//(1 << _v2(c)))*pow(2, _v2(c)+k*t-base, modulus)
                  for k, c in poly.items()}
    value = 0
    for k in range(max(normalized), -1, -1):
        value = (value*residue+normalized.get(k, 0)) % modulus
    return base+_v2(value) if value else None


def _tie_excluded(vp, vq, t):
    return (vp is not None and vq is not None and vp+1 != vq) or (vp is not None and (vp+1-t) % 2 != 0)


def check_tie_cover(proof, p, q, lo, hi):
    """Check a complete radix tree of residue classes, with exact exceptions."""
    rows = proof['classes']
    by_t = {_int(x['v2_n']): x for x in rows}
    _require(len(by_t) == len(rows), 'duplicate valuation class')
    leaves = {}
    for x in proof['leaves']:
        key = (_int(x['v2_n']), _int(x['residue']), _int(x['modulus']))
        _require(key not in leaves and key[2] in (256, 4096, 65536)
                 and 0 < key[1] < key[2] and key[1] % 2 == 1, 'invalid/duplicate residue leaf')
        leaves[key] = x
    used, needed_t, unresolved = set(), set(), []
    def visit(t, residue, modulus, umin, umax):
        first = umin+(residue-umin) % modulus
        if first > umax:
            return
        key = (t, residue, modulus)
        if key in leaves:
            used.add(key)
            row = leaves[key]
            vp, vq = _valuation(p, t, residue, modulus), _valuation(q, t, residue, modulus)
            _require((row['v2_P'], row['v2_Q']) == (vp, vq), 'residue valuation changed')
            if not _tie_excluded(vp, vq, t):
                unresolved.append((t, first, umax, modulus))
            return
        _require(modulus < 65536, 'tie cover residue leaf omitted')
        for j in range(16):
            visit(t, residue+j*modulus, modulus*16, umin, umax)
    for t in range(hi.bit_length()):
        step = 1 << t
        umin, umax = (lo+step-1)//step, hi//step
        if (umin | 1) > umax:
            continue
        needed_t.add(t)
        _require(t in by_t, 'valuation class omitted')
        vp, vq = _valuation(p, t), _valuation(q, t)
        _require((by_t[t]['v2_P'], by_t[t]['v2_Q']) == (vp, vq), 'whole-class valuation changed')
        if not _tie_excluded(vp, vq, t):
            for residue in range(1, 256, 2):
                visit(t, residue, 256, umin, umax)
    _require(set(by_t) == needed_t and set(leaves) == used, 'extra/overlapping/outside tie class')
    count = sum((umax-first)//modulus+1 for _, first, umax, modulus in unresolved)
    _require(count <= 64, 'finite tie exceptions exceed work budget')
    expected = sorted(u*(1 << t) for t, first, umax, modulus in unresolved
                      for u in range(first, umax+1, modulus))
    exceptions = proof['exceptions']
    _require([_int(x['n']) for x in exceptions] == expected, 'finite tie exception omitted')
    for row in exceptions:
        pn, qn = _at(p, row['n']), _at(q, row['n'])
        residue = 2*pn % (2*qn)
        _require(row['residue'] == residue and residue != qn, 'rational exact tie or changed exception residue')
    return tuple(expected)


def verify_certificate(cert, expected_domain, *, execution_limit=16384):
    """External domain and execution ceiling are obligations, never inferred from cert."""
    try:
        foundation_guard()
        domain = R.axis_domain(expected_domain['axis'], expected_domain['lo'], expected_domain['hi'])
        _require(domain == expected_domain and domain['lo'] > 0, 'positive declared domain required')
        _require(cert['version'] == VERSION and cert['status'] == 'certified' and cert['scope'] == SCOPE
                 and cert['global_4_4b'] == 'NotCertified', 'wrong family certificate contract')
        _require(cert['domain'] == domain and cert['domain_hash'] == R.domain_hash(domain), 'external domain mismatch')
        _require(cert['foundation_sha256'] == FOUNDATION_HASHES, 'foundation provenance changed')
        bits = _int(cert['required_bits'])
        A.precision_guard(bits)
        A.precision_guard(_int(execution_limit))
        _require(bits <= execution_limit <= A.C.MAX_PRECISION_BITS, 'proof precision exceeds actual execution limit')
        _require(_int(cert['max_decision_bits']) == bits and _int(cert['residual_bits']) == 4096, 'precision metadata changed')
        p, q, terms, di = frozen_identity()
        _require(_poly(cert['P']) == p and _poly(cert['Q']) == q, 'frozen rational identity mismatch')
        supplied = {_fraction(x['lambda']): _poly(x['laurent'], rational=True) for x in cert['exponential_terms']}
        _require(len(supplied) == len(cert['exponential_terms']) and supplied == terms, 'frozen exponential identity mismatch')
        _require(_poly(cert['D_integer']) == di and cert['Q_scalar'] == 5**8, 'square denominator identity mismatch')
        lo, hi = domain['lo'], domain['hi']
        _require(all(k >= 0 and c > 0 for k, c in q.items()), 'positive monotone Q not proved')
        qmax = _at(q, hi)
        _require(_int(cert['Q_max']) == qmax and _int(cert['lattice_point_count']) == hi-lo+1, 'domain endpoints/Q_max changed')
        a, b = F(lo, 1 << 48), F(hi, 1 << 48)
        residual = residual_range(a, b, terms, 4096)
        _require(tuple(_fraction(x) for x in cert['residual_interval']) == residual, 'signed residual interval changed')
        error = A.axis_impulse_error(a, b, bits)* (1 << 80)
        _require(_fraction(cert['numeric_error']) == error and error >= 0, 'numeric endpoint error changed')
        guard = residual[0]-error, residual[1]+error
        _require(tuple(_fraction(x) for x in cert['signed_guard']) == guard, 'signed numeric guard changed')
        spacing = F(1, 2*qmax)
        margin = spacing-max(abs(x) for x in residual)
        _require(_fraction(cert['spacing_lower']) == spacing and _fraction(cert['physical_margin_lower']) == margin,
                 'spacing direction or physical margin changed')
        _require(error < margin and max(abs(x) for x in guard) < spacing, 'strict family separation not proved')
        impulse_bound = F(sum(abs(c)*hi**k for k, c in p.items()), _at(q, lo))+max(abs(x) for x in residual)
        _require(_fraction(cert['impulse_abs_upper']) == impulse_bound and
                 impulse_bound+error < F((1 << 96)-1, 2), 'legal momentum output not proved')
        exceptions = check_tie_cover(cert['tie_cover'], p, q, lo, hi)
        _require([x['n'] for x in cert['direct_exceptions']] == list(exceptions), 'direct exception omitted')
        for row in cert['direct_exceptions']:
            # This redundant point proof is independently regenerated by the old API.
            point = tuple(row['n'] if k == domain['axis'] else 0 for k in range(3))
            direct_bits = _int(row['bits'])
            A.precision_guard(direct_bits)
            _require(direct_bits <= bits, 'exception precision exceeds family maximum')
            actual = R.certify_finite_points((point,), bits=direct_bits)
            _require(actual['status'] == 'certified', 'direct exception unresolved')
        return domain
    except (KeyError, TypeError, ValueError, IndexError, ZeroDivisionError) as error:
        raise O.NotCertified(f'invalid family proof object: {error}') from error
