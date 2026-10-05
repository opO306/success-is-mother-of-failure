"""Executor-side constants, measuring device and domain obligation for Exact Expression Gate V1.

The checker does not import this module; it carries its own copy of the device and the domain rule.

World semantics are those of V0: exact real state of the UNROUNDED KDK map (dt = 40, half kick 20, Ar40 mass of
C1-B1, frozen C1-A Lang 2024 force with retardation). The grid projection below is a TEST MEASUREMENT only and is
never fed back into the state.
"""

from __future__ import annotations

from fractions import Fraction as Q

from mpmath.libmp import finf, fnan, fninf, to_rational

import exact_expression_gate_v0.lang_iv as LI

MASS = Q("39.9623831237") / Q("5.485799090441e-4")      # equals a_reference.c1b1_two_atom.AR40_MASS_ME (tested)
DT = Q(40)
H = DT / 2
CDT = DT / MASS
POS_F, MOM_F = 48, 80
WORD = 96                                               # FX(96, f): signed raw, -(2^95) <= raw < 2^95
RAW_LO, RAW_HI = -(1 << (WORD - 1)), 1 << (WORD - 1)
# Domain of the reference force: ar2_lang2024 refuses R < r_min, so R >= r_min is inside (V0 used the stricter R > r_min).
R_MIN2 = Q(LI.L.R_MIN_BOHR) ** 2

DECIDED = "DECIDED"
UNDECIDED_AT_CAP = "UNDECIDED_AT_CAP"
REFUSED_DOMAIN = "REFUSED_DOMAIN"
OUT_OF_RANGE = "OUT_OF_RANGE"

PROVEN, UNPROVEN, VIOLATED = "PROVEN", "UNPROVEN", "VIOLATED"


class DomainStop(Exception):
    """Force undefined (VIOLATED) or not proven defined at this precision (UNPROVEN)."""

    def __init__(self, kind, where=None):
        super().__init__(f"{kind} at {where}")
        self.kind, self.where = kind, where


class OutOfRange(Exception):
    """A decided grid raw does not fit the signed 96-bit FX word of the measuring device."""


def endpoint(t):
    """Exact Fraction of an mpf endpoint tuple, or None if it is not finite."""
    if t in (finf, fninf, fnan):
        return None
    return Q(*to_rational(t))


def bounds(v):
    """(lo, hi) as exact Fractions (None for a non-finite end). v: Fraction or mpmath iv interval."""
    if isinstance(v, Q):
        return v, v
    return endpoint(v._mpi_[0]), endpoint(v._mpi_[1])


def rhe(x: Q) -> int:
    n, d = x.numerator, x.denominator
    sign = -1 if n < 0 else 1
    q, r = divmod(abs(n), d)
    if 2 * r > d or (2 * r == d and q & 1):
        q += 1
    return sign * q


def cell(v, frac_bits):
    """Grid raw of v if both ends round to the same raw (an exact Fraction always does), else None."""
    lo, hi = bounds(v)
    if lo is None or hi is None:
        return None
    a, b = rhe(lo * (1 << frac_bits)), rhe(hi * (1 << frac_bits))
    if a != b:
        return None
    if not RAW_LO <= a < RAW_HI:
        raise OutOfRange(a)
    return a


def decide(qv, pv):
    out = [cell(v, POS_F) for v in qv] + [cell(v, MOM_F) for v in pv]
    return None if any(x is None for x in out) else out


def domain(r2):
    """Three-way domain obligation of the force at squared distance r2 (Fraction or interval)."""
    lo, hi = bounds(r2)
    if lo is not None and lo >= R_MIN2:
        return PROVEN
    if hi is not None and hi < R_MIN2:
        return VIOLATED
    return UNPROVEN


def endpoints_key(vals):
    """Exact text of every endpoint, for bit-identity comparison between paths at the same precision."""
    parts = []
    for v in vals:
        if isinstance(v, Q):
            parts.append(f"Q{v.numerator}/{v.denominator}")
        else:
            parts.append(repr(v._mpi_))
    return "|".join(parts)
