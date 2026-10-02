"""Endpoint-identical integer primitives, C1-B1 Candidate B opt-in path.

There is no floating-point arithmetic here. A grid rounding operation is never
moved across another operation. Proof obligations are documented in PROOF.md.
"""
from __future__ import annotations
from fractions import Fraction as Q
from functools import lru_cache
from math import isqrt
import a_reference.ar2_lang2024 as L

FINGERPRINT = 'ada6153be05af3e582139fdc81b5697fffaf18d12f9f2de6e8d5ac2fdfe0839e'
if L.parameter_fingerprint() != FINGERPRINT:
    raise ImportError('Unexpected frozen C1-A parameters')
LN2_UPPER = Q(6932, 10000)


def _mul(a: tuple[int, int], b: tuple[int, int], M: int) -> tuple[int, int]:
    """Select exact extrema by signs; preserve the two final directed shifts."""
    al, ah = a
    bl, bh = b
    if al >= 0:
        if bl >= 0:
            low, high = al * bl, ah * bh
        elif bh <= 0:
            low, high = ah * bl, al * bh
        else:
            low, high = ah * bl, ah * bh
    elif ah <= 0:
        if bl >= 0:
            low, high = al * bh, ah * bl
        elif bh <= 0:
            low, high = ah * bh, al * bl
        else:
            low, high = al * bh, al * bl
    else:
        if bl >= 0:
            low, high = al * bh, ah * bh
        elif bh <= 0:
            low, high = ah * bl, al * bl
        else:
            low = min(al * bh, ah * bl)
            high = max(al * bl, ah * bh)
    return low >> M, -((-high) >> M)


def _add(a, b):
    return a[0] + b[0], a[1] + b[1]


def _neg(a):
    return -a[1], -a[0]


def _const(c: Q, M: int):
    n = c.numerator << M
    return n // c.denominator, -((-n) // c.denominator)


def _scale(a, c: Q):
    n, d = c.numerator, c.denominator
    if n >= 0:
        return (a[0] * n) // d, -((-(a[1] * n)) // d)
    return (a[1] * n) // d, -((-(a[0] * n)) // d)


def _div_small(a, d: int):
    return a[0] // d, -((-a[1]) // d)


def _div_pos(a, b, M):
    """Two divisions instead of eight, for an ordered denominator interval > 0."""
    if not 0 < b[0] <= b[1]:
        raise ValueError('division requires a positive ordered denominator')
    if a[0] >= 0:
        dl, dh = b[1], b[0]
    elif a[1] <= 0:
        dl, dh = b[0], b[1]
    else:
        dl = dh = b[0]
    return (a[0] << M) // dl, -((-(a[1] << M)) // dh)


def _taylor_side(Y: int, M: int, upper: bool) -> int:
    """Exactly one output of the reference Taylor program, not a new bound."""
    magnitude, negative = abs(Y), Y < 0
    one = 1 << M
    lower_term = upper_term = one
    total = one
    degree = 0
    while True:
        degree += 1
        lower_term = (lower_term * magnitude) // (degree << M)
        upper_term = -((-upper_term * magnitude) // (degree << M))
        if negative and degree & 1:
            total -= lower_term if upper else upper_term
        else:
            total += upper_term if upper else lower_term
        if upper_term <= 1:
            break
    margin = 2 * upper_term + 2
    return total + margin if upper else total - margin


def _exp_side(end: int, M: int, upper: bool) -> int:
    """Project only the required side of enc(end). The reduction k is unchanged."""
    k = max(0, end.bit_length() - M + 1) + 8
    # x = -end / 2**M, so x / 2**k * 2**M = -end / 2**k exactly.
    Y = -(end >> k) if upper else (-end) >> k
    value = _taylor_side(Y, M, upper)
    if not upper:
        value = max(value, 0)
        for _ in range(k):
            value = (value * value) >> M
    else:
        for _ in range(k):
            value = -((-value * value) >> M)
    return value


def _exp_neg(x, M):
    # The REF's precision-dependent shortcut is retained exactly, including >=.
    if x[0] * LN2_UPPER.denominator >= (M * LN2_UPPER.numerator) << M:
        return 0, 1
    return _exp_side(x[1], M, False), _exp_side(x[0], M, True)


@lru_cache(maxsize=8)
def _const_cache(M):
    """Bounded immutable-contract cache; same values/order as the reference."""
    comps = {}
    for name, (short, (eta, C, kadd)) in L.COMPONENTS.items():
        shorts = [(_const(alpha, M), alpha, dict(coefs)) for alpha, coefs in short.values()]
        comps[name] = (shorts, _const(eta, M), eta, kadd, C)
    return comps


def _raw_powers(x: int) -> dict[int, int]:
    """Exact, unscaled integer powers: 15 multiplications for 16 needed exponents."""
    p = {1: x, 2: x * x}
    p[4] = p[2] * p[2]
    for n in range(5, 18):
        p[n] = p[n - 1] * x
    return p


def _inverse_table(lo: int, hi: int, M: int):
    # In particular, this is NOT a recurrence of rounded reciprocal intervals.
    low_power = _raw_powers(lo)
    high_power = low_power if hi == lo else _raw_powers(hi)
    return {n: ((1 << (M * (n + 1))) // high_power[n],
                -((-(1 << (M * (n + 1)))) // low_power[n])) for n in low_power}


def _radius(R2: Q, M: int) -> tuple[int, int]:
    """Same floor/ceil sqrt enclosure using one isqrt rather than two."""
    quotient, remainder = divmod(R2.numerator << (2 * M), R2.denominator)
    low = isqrt(quotient)
    high = low + int(remainder != 0 or low * low != quotient)
    return low, high
