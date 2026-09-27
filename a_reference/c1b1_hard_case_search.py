"""C1-B1 ④-4c-5: shell-18 hard-case search feasibility survey (survey_only).

Target: psi(n) = P(n)/Q(n) - 1/2, the rational part of the axis impulse in
momentum ULPs shifted so rounding boundaries are integers. A lattice input is
a hazard for the pinned guard G when dist(psi(n), Z) <= G. Here G is the prior
4096-bit signed-residual + numeric-error guard, read from the pinned fixture.

Each block replaces psi by an interpolating polynomial q and a rigorous
interpolation error delta from an exact Bernstein bound of the derivative
numerator. The search threshold is T = G + delta; nothing smaller is used.
Every candidate is rechecked with the original exact P/Q.

This module proposes candidates only. The independent checker lives in
c1b1_hard_case_checker and does not import this file. No region, coverage,
precision cap or ④-4b status changes.
"""
from fractions import Fraction as F
from hashlib import sha256
from math import comb, factorial, lcm
from pathlib import Path
import json
import time

from a_reference import c1b1_fractional_phase_survey as S
from a_reference import c1b1_rounding_diagnosis as D
from a_reference import c1b1_outer_bootstrap as O

ROOT = Path(__file__).resolve().parents[1]
VERSION = 'c1b1-hard-case-search-survey-v1'
PRIOR = 'a_reference/fixtures/c1b1_modular_distance_survey_v1.json'
PRIOR_HASH = '3676aa17727aaeae6a2e199628ded4cb087c37b5bb86bfc2cf410f843ef62ace'
BOUNDARIES = 'a_reference/fixtures/c1b1_half_ulp_boundaries_v1.json'
BOUNDARIES_HASH = '5874f229e5f87783c90713b6c0342ddf1e2290ae73753c02e3527624e928fd1f'
SHELL = 18
# max |t(t-h)(t-2h)| on [0,2h] is 2h^3/(3 sqrt 3); W3 is a rational upper bound.
W3 = F(38491, 100000)
# max |t(t-1)(t-2)(t-3)| on [0,3] is exactly 1 (u=t^2-3t, u(u+2) >= -1).
W4 = F(1)
EXACT_BLOCK = 4
MAX_CANDIDATES_PER_INTERVAL = 1 << 20
MAX_CROSSINGS_PER_BLOCK = 1 << 20
DYADIC_BITS = 256


def _require(condition, message):
    if not condition:
        raise O.NotCertified(message)


def _ceil(x):
    return -((-x.numerator)//x.denominator)


def _floor(x):
    return x.numerator//x.denominator


def at(poly, n):
    value = 0
    for k in range(max(poly, default=0), -1, -1):
        value = value*n+poly.get(k, 0)
    return value


def _derivative(poly):
    return {k-1: k*c for k, c in poly.items() if k}


def _multiply(a, b):
    out = {}
    for i, x in a.items():
        for j, y in b.items():
            out[i+j] = out.get(i+j, 0)+x*y
    return {k: c for k, c in out.items() if c}


def _combine(a, b, scale):
    out = dict(a)
    for k, c in b.items():
        out[k] = out.get(k, 0)+scale*c
    return {k: c for k, c in out.items() if c}


def _shift(poly, a):
    """Exact Taylor shift: returns r with r(t) = poly(a+t)."""
    coeffs = [poly.get(k, 0) for k in range(max(poly, default=0)+1)]
    for i in range(len(coeffs)):
        for j in range(len(coeffs)-2, i-1, -1):
            coeffs[j] += a*coeffs[j+1]
    return {k: c for k, c in enumerate(coeffs) if c}


class Target:
    """psi = P/Q - 1/2 with integer P, Q; Q must have positive coefficients."""

    def __init__(self, p, q, kmax=4):
        _require(all(type(c) is int for c in (*p.values(), *q.values())), 'integer P and Q required')
        _require(q and all(c > 0 for c in q.values()), 'positive Q coefficients required')
        self.p, self.q = dict(p), dict(q)
        # (P/Q)^(k) = N_k/Q^(k+1),  N_{k+1} = N_k' Q - (k+1) N_k Q'
        self.numerators = [dict(p)]
        dq = _derivative(q)
        for k in range(kmax):
            nk = self.numerators[-1]
            self.numerators.append(_combine(_multiply(_derivative(nk), q), _multiply(nk, dq), -(k+1)))

    def value(self, n):
        pn, qn = at(self.p, n), at(self.q, n)
        return F(2*pn-qn, 2*qn)

    def distance(self, n):
        """Exact dist(P/Q, Z+1/2) = |(2P mod 2Q) - Q| / (2Q)."""
        pn, qn = at(self.p, n), at(self.q, n)
        _require(qn > 0, 'positive denominator required')
        return F(abs(2*pn % (2*qn)-qn), 2*qn)


def bernstein_controls(poly, a, width, degree):
    """d! times the exact Bernstein controls of poly(a+t), t in [0,width], elevated to `degree`.

    b_i = sum_k C(i,k)/C(d,k) c_k w^k; multiplying by d! keeps integers.
    """
    _require(type(width) is int and width > 0, 'positive integer width required')
    shifted = _shift(poly, a)
    _require(max(shifted, default=0) <= degree, 'degree elevation below polynomial degree')
    c = [shifted.get(k, 0)*width**k for k in range(degree+1)]
    weight = [factorial(k)*factorial(degree-k) for k in range(degree+1)]
    return [sum(comb(i, k)*weight[k]*c[k] for k in range(i+1)) for i in range(degree+1)]


def derivative_bound(target, k, a, b):
    """sup |psi^(k)| = sup |N_k / Q^(k+1)| on [a,b].

    With all denominator controls positive, N/D is a weighted mean of the
    control ratios, so max_i |n_i|/d_i bounds it on the whole interval.
    """
    _require(k >= 1 and 0 < a < b, 'positive interval and derivative order >= 1 required')
    den = {0: 1}
    for _ in range(k+1):
        den = _multiply(den, target.q)
    degree = max(max(target.numerators[k], default=0), max(den))
    num_c = bernstein_controls(target.numerators[k], a, b-a, degree)
    den_c = bernstein_controls(den, a, b-a, degree)
    _require(min(den_c) > 0, 'denominator controls not positive')
    return max(F(abs(x), y) for x, y in zip(num_c, den_c))


def interpolation_error(degree, bound, length):
    """Rigorous |psi - q| on a block of `length` from sup|psi^(degree+1)| <= bound."""
    if degree == 1:
        return bound*F(length)**2/8
    if degree == 2:
        _require(length % 2 == 0, 'quadratic nodes need an even block length')
        return bound*W3*F(length//2)**3/6
    if degree == 3:
        _require(length % 3 == 0, 'cubic nodes need a block length divisible by three')
        return bound*W4*F(length//3)**4/24
    raise O.NotCertified('unsupported degree')


def _first(lo, hi, predicate, guess=None):
    """Smallest t in [lo,hi] with predicate true (predicate monotone false->true); hi+1 if none.

    `guess` only speeds up the exact bracket search; the answer does not depend on it.
    """
    if guess is not None:
        g = min(max(guess, lo), hi)
        step = 1
        if predicate(g):
            hi = g-1
            while g-step >= lo and predicate(g-step):
                hi, step = g-step-1, 2*step
            lo = max(lo, g-step)
        else:
            lo = g+1
            while g+step <= hi and not predicate(g+step):
                lo, step = g+step+1, 2*step
            hi = min(hi, g+step)
    while lo <= hi:
        mid = (lo+hi)//2
        if predicate(mid):
            hi = mid-1
        else:
            lo = mid+1
    return lo


def dyadic_up(x, bits=None):
    """Smallest multiple of 2^-bits that is >= x (a larger threshold keeps the search complete)."""
    bits = DYADIC_BITS if bits is None else bits
    return F(-((-x.numerator << bits)//x.denominator), 1 << bits)


def _root_guess(e0, c1, c2, length):
    """Float estimate of t with e0 + c1 t + c2 t^2 = 0; None when not finite."""
    try:
        e0, c1, c2 = float(e0), float(c1), float(c2)
        t = -e0/c1
        for _ in range(3):
            t -= (e0+t*(c1+t*c2))/(c1+2*c2*t)
        return int(t) if t == t and abs(t) <= 4*length+4 else None
    except (OverflowError, ZeroDivisionError):
        return None


def _interval(a, t_lo, t_hi, length):
    t_lo, t_hi = max(t_lo, 0), min(t_hi, length)
    if t_lo > t_hi:
        return None
    _require(t_hi-t_lo < MAX_CANDIDATES_PER_INTERVAL, 'candidate interval exceeds work limit')
    return (a+t_lo, a+t_hi)


def exact_block(target, a, b, tau):
    """Direct exact evaluation of every input: no approximation at all."""
    return {'kind': 'exact', 'a': a, 'b': b, 'crossings': None, 'delta': F(0),
            'intervals': [(n, n) for n in range(a, b+1) if target.distance(n) <= tau]}


def affine_block(target, a, b, tau, bound):
    length = b-a
    delta = interpolation_error(1, bound, length)
    limit = tau+delta
    y0, y1 = target.value(a), target.value(b)
    slope = (y1-y0)/length
    _require(slope != 0, 'constant block')
    intervals = []
    first, last = _ceil(min(y0, y1)-limit), _floor(max(y0, y1)+limit)
    _require(last-first < MAX_CROSSINGS_PER_BLOCK, 'crossing work limit exceeded')
    for m in range(first, last+1):
        u, v = (m-limit-y0)/slope, (m+limit-y0)/slope
        found = _interval(a, _ceil(min(u, v)), _floor(max(u, v)), length)
        if found:
            intervals.append(found)
    return {'kind': 'affine', 'a': a, 'b': b, 'crossings': last-first+1, 'delta': delta, 'intervals': intervals}


def quadratic_block(target, a, b, tau, bound):
    """None when the interpolant is not strictly monotone (caller splits)."""
    length = b-a
    h = length//2
    delta = interpolation_error(2, bound, length)
    limit = dyadic_up(tau+delta)
    y0, y1, y2 = target.value(a), target.value(a+h), target.value(b)
    c2 = (y2-2*y1+y0)/(2*h*h)
    c1 = (y1-y0)/h-c2*h
    if c1 == 0 or (c1 > 0) != (c1+2*c2*length > 0) or c1+2*c2*length == 0:
        return None
    increasing = c1 > 0
    scale = lcm(y0.denominator, c1.denominator, c2.denominator)
    k0, k1, k2 = y0*scale, c1*scale, c2*scale
    k0, k1, k2 = k0.numerator, k1.numerator, k2.numerator

    def at_least(y):   # q(t) >= y, integer arithmetic
        return lambda t: (k0+t*(k1+t*k2))*y.denominator >= y.numerator*scale

    def at_most(y):
        return lambda t: (k0+t*(k1+t*k2))*y.denominator <= y.numerator*scale
    intervals = []
    first, last = _ceil(min(y0, y2)-limit), _floor(max(y0, y2)+limit)
    _require(last-first < MAX_CROSSINGS_PER_BLOCK, 'crossing work limit exceeded')
    for m in range(first, last+1):
        low, high = m-limit, m+limit
        g_low, g_high = _root_guess(y0-low, c1, c2, length), _root_guess(y0-high, c1, c2, length)
        if increasing:
            t_lo = _first(0, length, at_least(low), g_low)
            t_hi = _first(0, length, lambda t: not at_most(high)(t), g_high)-1
        else:
            t_lo = _first(0, length, at_most(high), g_high)
            t_hi = _first(0, length, lambda t: not at_least(low)(t), g_low)-1
        found = _interval(a, t_lo, t_hi, length)
        if found:
            intervals.append(found)
    return {'kind': 'quadratic', 'a': a, 'b': b, 'crossings': last-first+1, 'delta': delta,
            'threshold': limit, 'intervals': intervals}


def search_block(target, a, b, tau, bound, degree):
    """Candidate intervals for [a,b]; non-monotone quadratics split, tiny blocks go exact."""
    if b-a < EXACT_BLOCK:
        return [exact_block(target, a, b, tau)]
    if degree == 1:
        return [affine_block(target, a, b, tau, bound)]
    _require(degree == 2, 'block search implemented for degrees 1 and 2 only')
    if (b-a) % 2:
        return search_block(target, a, b-1, tau, bound, degree)+[exact_block(target, b, b, tau)]
    found = quadratic_block(target, a, b, tau, bound)
    if found is not None:
        return [found]
    mid = a+(b-a)//2
    return search_block(target, a, mid, tau, bound, degree)+search_block(target, mid+1, b, tau, bound, degree)


def superblock_ranges(lo, hi, points, superblocks):
    """Contiguous ranges of whole blocks (each block has `points` inputs) covering [lo,hi]."""
    _require(points >= 1 and lo <= hi and superblocks >= 1, 'invalid partition')
    count = -(-(hi-lo+1)//points)
    per = -(-count//superblocks)
    return [(lo+s*points, min(lo+(s+per)*points-1, hi)) for s in range(0, count, per)]


def run_superblock(target, a0, b0, tau, degree, points):
    """Disjoint blocks [a, a+points-1] over [a0,b0]; one derivative bound for the range."""
    started = time.perf_counter()
    bound = derivative_bound(target, degree+1, a0, b0) if b0 > a0 else F(0)
    results = []
    for a in range(a0, b0+1, points):
        results.extend(search_block(target, a, min(a+points-1, b0), tau, bound, degree))
    intervals = merged(iv for r in results for iv in r['intervals'])
    record = [(r['kind'], r['a'], r['b'], r['crossings'], tuple(r['intervals'])) for r in results]
    return {'superblock': (a0, b0), 'blocks': -(-(b0-a0+1)//points), 'derivative_bound': bound,
            'max_delta': max(r['delta'] for r in results),
            'pieces': len(results), 'exact_pieces': sum(r['kind'] == 'exact' for r in results),
            'crossings': sum(r['crossings'] or 0 for r in results),
            'candidate_intervals': intervals,
            'candidate_count': sum(b-a+1 for a, b in intervals),
            'record_sha256': sha256(json.dumps(D.serial(record), separators=(',', ':')).encode()).hexdigest(),
            'seconds': time.perf_counter()-started}


def search(target, lo, hi, tau, degree, points, superblocks):
    """Serial block search over [lo,hi]."""
    return [run_superblock(target, a0, b0, tau, degree, points)
            for a0, b0 in superblock_ranges(lo, hi, points, superblocks)]


def merged(intervals):
    """Union of closed integer intervals as sorted disjoint intervals."""
    out = []
    for a, b in sorted(tuple(x) for x in intervals):
        if out and a <= out[-1][1]+1:
            out[-1] = (out[-1][0], max(out[-1][1], b))
        else:
            out.append((a, b))
    return out


def recheck(target, rows, tau):
    """Exact P/Q evaluation of every candidate; hazards are dist <= tau."""
    hazards, checked = [], 0
    for a, b in merged(iv for row in rows for iv in row['candidate_intervals']):
        for n in range(a, b+1):
                checked += 1
                d = target.distance(n)
                if d <= tau:
                    hazards.append({'n': n, 'distance_ulps': d})
    return {'exact_recheck_count': checked, 'hazards': hazards,
            'false_positive_count': checked-len(hazards)}


def load_shell(shell=SHELL):
    for name, digest in ((PRIOR, PRIOR_HASH), (BOUNDARIES, BOUNDARIES_HASH)):
        data = (ROOT/name).read_bytes().replace(b'\r\n', b'\n')
        _require(sha256(data).hexdigest() == digest, 'pinned prior fixture changed')
    prior = json.loads((ROOT/PRIOR).read_bytes())
    group = [g for g in prior['groups'] if g['shell_index'] == shell]
    _require(len(group) == 1, 'shell obligation missing')
    guard = group[0]['guard']
    p, q, _, _ = S.normal_form()
    domain = group[0]['domain']
    return Target(p, q), domain['lo'], domain['hi'], F(guard['abs_guard_ulps']), guard
