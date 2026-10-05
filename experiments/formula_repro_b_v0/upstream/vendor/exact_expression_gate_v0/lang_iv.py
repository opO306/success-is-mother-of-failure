"""Interval (mpmath.iv) transcription of the frozen C1-A Lang 2024 dV/dR with retardation ON.

Same formula and the same exact published constants as a_reference/ar2_lang2024.py (read-only import of
the constants). Accepts interval R. Cross-checked against ar2_lang2024.enclose in the tests.
"""

from __future__ import annotations

from fractions import Fraction as Q
from math import factorial

from mpmath import iv

import a_reference.ar2_lang2024 as L


def c(x: Q):
    x = Q(x)
    return iv.mpf(x.numerator) / iv.mpf(x.denominator)


def _poly(coefs, R):
    return sum((c(a) * R ** i for i, a in coefs.items()), iv.mpf(0))


def _poly_deriv(coefs, R):
    return sum((c(i * a) * R ** (i - 1) for i, a in coefs.items() if i), iv.mpf(0))


def _g(R):
    num = 1 + sum((c(a) * R ** (m + 1) for m, a in enumerate(L.RET_A)), iv.mpf(0))
    den = 1 + sum((c(b) * R ** (m + 1) for m, b in enumerate(L.RET_B)), iv.mpf(0))
    dnum = sum((c((m + 1) * a) * R ** m for m, a in enumerate(L.RET_A)), iv.mpf(0))
    dden = sum((c((m + 1) * b) * R ** m for m, b in enumerate(L.RET_B)), iv.mpf(0))
    return num / den, (dnum * den - num * dden) / (den * den)


def _component_deriv(name, R):
    short, (eta, C, kadd) = L.COMPONENTS[name]
    out = iv.mpf(0)
    for alpha, coefs in short.values():
        e = iv.exp(-c(alpha) * R)
        out = out + e * (_poly_deriv(coefs, R) - c(alpha) * _poly(coefs, R))
    x = c(eta) * R
    ex = iv.exp(-x)
    kmin = min(C)
    for k, cc in C.items():
        n = 2 * k + kadd
        t = ex * sum((x ** i / factorial(i) for i in range(n + 1)), iv.mpf(0))
        f, f_minus_1 = 1 - t, -t
        dD = ex * (x ** n / factorial(n)) * c(eta)
        if k == kmin and name == "BO":
            g, dg = _g(R)
            D, dD = f_minus_1 + g, dD + dg
        elif k == kmin and name == "REL":
            D = f_minus_1
        else:
            D = f
        out = out - c(cc) * (dD / R ** (2 * k) - D * (2 * k) / R ** (2 * k + 1))
    return out


def dVdR(R):
    return sum((_component_deriv(n, R) for n in L.COMPONENTS), iv.mpf(0))


def G_of_R2(R2):
    """G = F/R = -dV/dR / R at R = sqrt(R2) (force on j from i is h * G * (r_j - r_i))."""
    R = iv.sqrt(R2)
    return -dVdR(R) / R
