"""Independent checker for the ④-4c-5 hard-case search survey.

Does not import c1b1_hard_case_search. It rebuilds P/Q from the frozen
component identity, its own derivative numerators, Bernstein ratio bounds with
the existing Fraction Bernstein routine, the block partition, and each
crossing boundary with an exact quadratic-root method (not the generator's
bracket search). Every candidate and brute-force input is evaluated exactly.

Scope: completeness of the candidate set for the rational-gap guard only.
It certifies no region, impulse, trajectory or ④-4b status.
"""
from fractions import Fraction as F
from math import comb, isqrt, lcm

from a_reference import c1b1_family_checker as K
from a_reference import c1b1_quotient_gap_survey as QG
from a_reference import c1b1_outer_bootstrap as O

VERSION = 'c1b1-hard-case-checker-v1'
EXACT_BLOCK = 4
DYADIC_BITS = 256
SCOPE = 'rational_gap_candidate_completeness_only'


def _require(condition, message):
    if not condition:
        raise O.NotCertified(message)


def _value(poly, n):
    degree = max(poly, default=0)
    total = 0
    for k in range(degree, -1, -1):
        total = total*n+poly.get(k, 0)
    return total


def _mul(a, b):
    out = {}
    for i in a:
        for j in b:
            out[i+j] = out.get(i+j, 0)+a[i]*b[j]
    return {k: v for k, v in out.items() if v}


def _shift(poly, a):
    """r(t) = poly(a+t) by the binomial expansion."""
    out = {}
    for k, c in poly.items():
        for j in range(k+1):
            out[j] = out.get(j, 0)+c*comb(k, j)*a**(k-j)
    return {k: v for k, v in out.items() if v}


class Rational:
    """psi = P/Q - 1/2 for integer polynomials, Q with positive coefficients."""

    def __init__(self, p, q, orders=4):
        _require(all(v > 0 for v in q.values()), 'positive Q coefficients required')
        self.p, self.q = dict(p), dict(q)
        dq = {k-1: k*v for k, v in q.items() if k}
        self.num = {0: dict(p)}
        for k in range(1, orders+1):
            prev = self.num[k-1]
            dprev = {j-1: j*v for j, v in prev.items() if j}
            a, b = _mul(dprev, q), _mul(prev, dq)
            self.num[k] = {j: a.get(j, 0)-k*b.get(j, 0) for j in set(a) | set(b) if a.get(j, 0)-k*b.get(j, 0)}

    def psi(self, n):
        pn, qn = _value(self.p, n), _value(self.q, n)
        return F(2*pn-qn, 2*qn)

    def half_distance(self, n):
        """dist(P/Q, Z+1/2) exactly, from the nearest odd multiple of Q/2."""
        pn, qn = _value(self.p, n), _value(self.q, n)
        _require(qn > 0, 'positive denominator required')
        k = pn//qn                            # P/Q in [k, k+1): nearest half-integer is k+1/2
        return F(abs(2*pn-(2*k+1)*qn), 2*qn)


def frozen_target():
    p, q, _, _ = K.frozen_identity()
    return Rational(p, q)


def ratio_bound(target, order, a, b):
    den = {0: 1}
    for _ in range(order+1):
        den = _mul(den, target.q)
    num = target.num[order]
    degree = max(max(num), max(den))
    nc = QG.bernstein(_shift(num, a), b-a, degree)
    dc = QG.bernstein(_shift(den, a), b-a, degree)
    _require(min(dc) > 0, 'denominator controls not positive')
    return max(abs(x)/y for x, y in zip(nc, dc))


def error_bound(degree, bound, length):
    if degree == 1:
        return bound*length*length/F(8)
    _require(degree == 2 and length % 2 == 0, 'unsupported interpolation')
    w3 = F(38491, 100000)
    _require(27*w3*w3 >= 4, 'W3 is not an upper bound of 2/(3 sqrt 3)')
    return bound*w3*F(length, 2)**3/6


def dyadic_ceiling(x):
    return F(-((-x.numerator << DYADIC_BITS)//x.denominator), 1 << DYADIC_BITS)


def blocks(lo, hi, points, superblocks):
    count = -(-(hi-lo+1)//points)
    per = -(-count//superblocks)
    ranges, start = [], lo
    while start <= hi:
        end = min(start+per*points-1, hi)
        ranges.append((start, end))
        start = end+1
    _require(ranges[0][0] == lo and ranges[-1][1] == hi and
             all(x[1]+1 == y[0] for x, y in zip(ranges, ranges[1:])), 'superblock cover broken')
    return ranges


def _first_true(pred, length, poly):
    """First t in [0,length] with monotone pred; root located by exact integer sqrt."""
    if pred(0):
        return 0
    if not pred(length):
        return length+1
    a2, a1, a0 = poly
    if a2 == 0:
        guess = -a0//a1 if a1 else 0
    else:
        disc = a1*a1-4*a2*a0
        roots = []
        if disc >= 0:
            s = isqrt(disc)
            for sign in (-1, 1):
                roots.append((-a1+sign*s)//(2*a2))
        inside = [r for r in roots if -2 <= r <= length+2]
        guess = inside[0] if inside else length//2
    t = min(max(guess, 1), length)
    steps = 0
    while t > 0 and pred(t-1):
        t, steps = t-1, steps+1
        if steps > 64:
            return _bisect(pred, 0, t)
    while not pred(t):
        t, steps = t+1, steps+1
        if steps > 64:
            return _bisect(pred, t, length)
    return t


def _bisect(pred, lo, hi):
    while lo < hi:
        mid = (lo+hi)//2
        if pred(mid):
            hi = mid
        else:
            lo = mid+1
    return lo


def _quadratic(target, a, b, tau, bound):
    length, h = b-a, (b-a)//2
    limit = dyadic_ceiling(tau+error_bound(2, bound, length))
    v0, v1, v2 = target.psi(a), target.psi(a+h), target.psi(b)
    s2 = (v2-2*v1+v0)/(2*h*h)
    s1 = (v1-v0)/h-s2*h
    d0, d1 = s1, s1+2*s2*length
    if d0 == 0 or d1 == 0 or (d0 > 0) != (d1 > 0):
        return None
    den = lcm(v0.denominator, s1.denominator, s2.denominator)
    i0, i1, i2 = int(v0*den), int(s1*den), int(s2*den)
    up = d0 > 0
    out = []
    lo_m = -((-(min(v0, v2)-limit).numerator)//(min(v0, v2)-limit).denominator)
    hi_m = (max(v0, v2)+limit).numerator//(max(v0, v2)+limit).denominator
    for m in range(lo_m, hi_m+1):
        y_lo, y_hi = m-limit, m+limit
        # scaled polynomial sign tests: q(t) >= y  <=>  i2 t^2 + i1 t + i0 - y*den >= 0
        c_lo = (i0*y_lo.denominator-y_lo.numerator*den, y_lo.denominator)
        c_hi = (i0*y_hi.denominator-y_hi.numerator*den, y_hi.denominator)

        def ge(c):
            return lambda t: (i2*t*t+i1*t)*c[1]+c[0] >= 0

        def gt(c):
            return lambda t: (i2*t*t+i1*t)*c[1]+c[0] > 0
        poly_lo = (i2*c_lo[1], i1*c_lo[1], c_lo[0])
        poly_hi = (i2*c_hi[1], i1*c_hi[1], c_hi[0])
        if up:
            t0 = _first_true(ge(c_lo), length, poly_lo)
            t1 = _first_true(gt(c_hi), length, poly_hi)-1
        else:
            t0 = _first_true(lambda t: not gt(c_hi)(t), length, poly_hi)
            t1 = _first_true(lambda t: not ge(c_lo)(t), length, poly_lo)-1
        t0, t1 = max(t0, 0), min(t1, length)
        if t0 <= t1:
            out.append((a+t0, a+t1))
    return hi_m-lo_m+1, out


def _affine(target, a, b, tau, bound):
    length = b-a
    limit = tau+error_bound(1, bound, length)
    v0, v1 = target.psi(a), target.psi(b)
    rate = (v1-v0)/length
    _require(rate != 0, 'constant block')
    lo_v, hi_v = min(v0, v1)-limit, max(v0, v1)+limit
    lo_m = -((-lo_v.numerator)//lo_v.denominator)
    hi_m = hi_v.numerator//hi_v.denominator
    out = []
    for m in range(lo_m, hi_m+1):
        ends = sorted(((m-limit-v0)/rate, (m+limit-v0)/rate))
        t0 = max(0, -((-ends[0].numerator)//ends[0].denominator))
        t1 = min(length, ends[1].numerator//ends[1].denominator)
        if t0 <= t1:
            out.append((a+t0, a+t1))
    return hi_m-lo_m+1, out


def _pieces(target, a, b, tau, bound, degree):
    if b-a < EXACT_BLOCK:
        return 0, [(n, n) for n in range(a, b+1) if target.half_distance(n) <= tau]
    if degree == 1:
        return _affine(target, a, b, tau, bound)
    if (b-a) % 2:
        c, iv = _pieces(target, a, b-1, tau, bound, degree)
        return c, iv+([(b, b)] if target.half_distance(b) <= tau else [])
    found = _quadratic(target, a, b, tau, bound)
    if found is not None:
        return found
    mid = a+(b-a)//2
    c1, i1 = _pieces(target, a, mid, tau, bound, degree)
    c2, i2 = _pieces(target, mid+1, b, tau, bound, degree)
    return c1+c2, i1+i2


def superblock(target, a0, b0, tau, degree, points):
    bound = ratio_bound(target, degree+1, a0, b0) if b0 > a0 else F(0)
    crossings, intervals = 0, set()
    for a in range(a0, b0+1, points):
        c, iv = _pieces(target, a, min(a+points-1, b0), tau, bound, degree)
        crossings += c
        intervals.update(iv)
    return {'superblock': (a0, b0), 'derivative_bound': bound, 'crossings': crossings,
            'candidate_intervals': merged(intervals)}


def verify_rows(target, lo, hi, tau, degree, points, superblocks, rows):
    """Recompute every superblock and compare with the generator's claims."""
    ranges = blocks(lo, hi, points, superblocks)
    _require([tuple(r['superblock']) for r in rows] == ranges, 'superblock partition mismatch')
    for row, (a0, b0) in zip(rows, ranges):
        mine = superblock(target, a0, b0, tau, degree, points)
        _require(F(row['derivative_bound']) >= mine['derivative_bound'], 'claimed derivative bound too small')
        _require(row['crossings'] == mine['crossings'], 'crossing count mismatch')
        _require([tuple(x) for x in row['candidate_intervals']] == mine['candidate_intervals'],
                 'candidate set mismatch')
    return recheck(target, rows, tau)


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
    hazards, count = [], 0
    for a, b in merged(iv for row in rows for iv in row['candidate_intervals']):
        for n in range(a, b+1):
                count += 1
                d = target.half_distance(n)
                if d <= tau:
                    hazards.append((n, d))
    return {'scope': SCOPE, 'exact_recheck_count': count, 'hazards': hazards,
            'false_positive_count': count-len(hazards)}


def brute_force(target, lo, hi, tau):
    return {n for n in range(lo, hi+1) if target.half_distance(n) <= tau}


def compare_with_brute_force(target, lo, hi, tau, candidate_intervals):
    truth = brute_force(target, lo, hi, tau)
    found = {n for a, b in candidate_intervals for n in range(a, b+1)}
    return {'inputs': hi-lo+1, 'hazards': len(truth), 'candidates': len(found),
            'missed': len(truth-found), 'false_positives': len(found-truth)}
