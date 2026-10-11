"""Canonical C1-B1 start states, independently re-implemented from the documented rule (T7, survey_only).

Rule (c1b1-canonical-state-v1, as documented in the O-1 input seal and the canonical-state module docstring; read,
NOT imported): relative position (R0, 0, 0), atoms at -+R0/2 on x, nominal energy E = e De, impact parameter b:
    Pt = round(b sqrt(2 mu E) / R0)                 on the FX(96,80) momentum grid
    Pr = round(-sqrt(2 mu (E - V(R0)) - Pt^2))        from the STORED Pt
    p_j = (Pr, Pt, 0), p_i = -p_j;  round = nearest, ties to even
Pt is decided in exact rational arithmetic. Pr needs V(R0), which is not rational: it is evaluated with the
independent Lang parser at 200 digits and the rounding refuses (Undecided) within 1e-40 units of a tie.
Raw layout (as the O-1 input seal): r_i(3) p_i(3) r_j(3) p_j(3); positions in 2^-48, momenta in 2^-80.
"""
from fractions import Fraction as Q
from math import isqrt

import mpmath as mm

from c1b1_o1 import model

MU = Q(model.MASS) / 2
DE = Q(model.DE)
R0 = 20
FP, FM = 48, 80


class Undecided(ValueError):
    pass


def round_sqrt(x):
    """Nearest integer to sqrt(x) for a rational x >= 0, ties to even, exact."""
    x = Q(x)
    if x < 0:
        raise ValueError('negative')
    n = isqrt(x.numerator // x.denominator)        # floor(sqrt(x))
    t = Q(2 * n + 1, 2) ** 2
    if x > t:
        return n + 1
    if x < t:
        return n
    return n if n % 2 == 0 else n + 1


def canonical_raw(e, b2, V):
    """Raw 12-integer state for E = e De and b^2 = b2 (exact rationals); V is a callable (mpf) potential."""
    E = Q(e) * DE
    pt = round_sqrt(Q(b2) * 2 * MU * E / R0 ** 2 * Q(2) ** (2 * FM))
    with mm.workdps(200):
        mu = mm.mpf(MU.numerator) / MU.denominator
        Em = mm.mpf(E.numerator) / E.denominator
        T = (2 * mu * (Em - V(mm.mpf(R0)))) * mm.mpf(2) ** (2 * FM) - pt * pt
        if T <= 0:
            raise ValueError('no inbound radial momentum')
        s = mm.sqrt(T)
        if abs(s - mm.floor(s) - mm.mpf('0.5')) < mm.mpf('1e-40'):
            raise Undecided('radial momentum rounding at a tie')
        pr = -int(mm.nint(s))
    half = (R0 // 2) << FP
    return [-half, 0, 0, -pr, -pt, 0, half, 0, 0, pr, pt, 0]


def relative(raw):
    """(q, p) of the relative coordinate as exact mpf: q = r_j - r_i (2^-48), p = p_j (2^-80); p_i = -p_j required."""
    if [-x for x in raw[0:3]] != raw[6:9] or [-x for x in raw[3:6]] != raw[9:12] or raw[2] or raw[5]:
        raise ValueError('not a centred planar state (r_i = -r_j, p_i = -p_j, z = 0)')
    with mm.workdps(60):                           # raw momenta are ~2^82: exact needs > 53 bits
        q = [mm.ldexp(mm.mpf(raw[6 + k] - raw[k]), -FP) for k in range(2)]
        p = [mm.ldexp(mm.mpf(raw[9 + k]), -FM) for k in range(2)]
        if any(int(mm.ldexp(x, FP)) != raw[6 + k] - raw[k] for k, x in enumerate(q)) or \
                any(int(mm.ldexp(x, FM)) != raw[9 + k] for k, x in enumerate(p)):
            raise ValueError('raw state not exact in mpf')
    return q, p
