"""Candidate multiparticle rounding laws P, T, C on exact (or enclosed) pair impulses.

Units: one grid unit u of the momentum profile. Values are Fractions in units of u.
pairs: dict {(i, j): A} with A the exact impulse on j (and -A on i), one component.
Results are tuples of integers (per-atom dp in units of u) or the string "STOP".
"""

from __future__ import annotations

from fractions import Fraction as Q


def rhe(x: Q) -> int:
    """Round half to even; odd-symmetric (same rule as a_numeric FixedPoint)."""
    x = Q(x)
    n, d = x.numerator, x.denominator
    sign = -1 if n < 0 else 1
    q, r = divmod(abs(n), d)
    if 2 * r > d or (2 * r == d and q & 1):
        q += 1
    return sign * q


def totals(n: int, pairs: dict) -> list:
    a = [Q(0)] * n
    for (i, j), A in pairs.items():
        a[j] += A
        a[i] -= A
    return a


def law_P(n: int, pairs: dict):
    dp = [0] * n
    for (i, j), A in pairs.items():
        J = rhe(A)
        dp[j] += J
        dp[i] -= J
    return tuple(dp)


def law_T(n: int, pairs: dict):
    return tuple(rhe(x) for x in totals(n, pairs))


def hamilton(t: list, a: list):
    """Largest-remainder correction so that sum(t) == 0; STOP on a tie at the cut."""
    D = sum(t)
    if D == 0:
        return tuple(t)
    s = 1 if D > 0 else -1
    keys = sorted((s * (ti - ai) for ti, ai in zip(t, a)), reverse=True)
    k = abs(D)
    cut = keys[k - 1]
    if k < len(keys) and keys[k] == cut:
        return "STOP"
    out = list(t)
    for idx, (ti, ai) in enumerate(zip(t, a)):
        if s * (ti - ai) >= cut:
            out[idx] -= s
    return tuple(out)


def law_C(n: int, pairs: dict):
    a = totals(n, pairs)
    return hamilton([rhe(x) for x in a], a)


LAWS = {"P": law_P, "T": law_T, "C": law_C}
