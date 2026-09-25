"""Independent audit of the C1-A Ar-Ar reference evaluator (Lang, Przybytek, Lesiuk 2024).

Imports neither a_reference, a_numeric nor engine (tests enforce it). Three independent routes:
  * parameters are PARSED from the published Fortran source (S2_ar2_pot.f90), not typed by hand;
  * V(R) is enclosed with mpmath interval arithmetic, written separately from the reference;
  * dV/dR is obtained by high-precision NUMERICAL differentiation of a point evaluation of V --
    a different route from the reference's analytic derivative.
"""
from __future__ import annotations

import re
from fractions import Fraction
from pathlib import Path

import mpmath

from audit.independent_numeric.oracle import MAX_MAG, SIGN, _interval, value

FORTRAN = Path(r"D:\reference\ar2_lang2024\S2_ar2_pot.f90")


def _numbers(block: str) -> list[str]:
    return re.findall(r"[-+]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][-+]?\d+)?(?=_prec)", block)


def parse_fortran(path: Path = FORTRAN) -> dict:
    """{name: [decimal strings in source order]} for every real parameter of the module."""
    lines = [re.sub(r"!.*", "", line) for line in path.read_text(encoding="utf-8").splitlines()]  # drop comments
    text = re.sub(r"&[ \t]*\n", " ", "\n".join(lines))                                           # join continuations
    out = {}
    for m in re.finditer(r"real\(prec\),parameter\s*::\s*(\w+)(?:\([^)]*\))?\s*=\s*(.*)", text):
        name, rhs = m.group(1), m.group(2)
        if name in ("EXPTHR",):
            continue
        out[name] = _numbers(rhs.split("],[")[0] if "reshape" in rhs else rhs)
    return out


class Model:
    """The Lang 2024 formula, evaluated in mpmath (interval or point) from parsed parameters."""

    def __init__(self, params: dict):
        self.p = params

    def _short(self, ctx, R, comp, imin):
        alpha = [ctx.mpf(s) for s in self.p[f"alpha_{comp}"]]
        a = [ctx.mpf(s) for s in self.p[f"a_{comp}"]]
        per_j = len(a) // len(alpha)          # column-major: a(Imin:Imax, j)
        total = 0
        for j, al in enumerate(alpha):
            poly = sum(a[j * per_j + t] * R ** (imin + t) for t in range(per_j))
            total += ctx.exp(-al * R) * poly
        return total

    @staticmethod
    def _f(ctx, n, x):
        return 1 - ctx.exp(-x) * sum(x ** i / ctx.factorial(i) for i in range(n + 1))

    def _long(self, ctx, R, comp, kmin, kadd, ret_kind):
        eta = ctx.mpf(self.p[f"eta_{comp}"][0])
        C = [ctx.mpf(s) for s in self.p[f"C_{comp}"]]
        total = 0
        for t, c in enumerate(C):
            k = kmin + t
            n = 2 * k + kadd
            f = self._f(ctx, n, eta * R)
            if t == 0 and ret_kind == "g":
                D = self._g(ctx, R) + (f - 1)
            elif t == 0 and ret_kind == "shift":
                D = f - 1
            else:
                D = f
            total -= c * D / R ** (2 * k)
        return total

    def _g(self, ctx, R):
        A = [ctx.mpf(s) for s in self.p["A"]]
        B = [ctx.mpf(s) for s in self.p["B"]]
        num = 1 + sum(A[m] * R ** (m + 1) for m in range(len(A)))
        den = 1 + sum(B[m] * R ** (m + 1) for m in range(len(B)))
        return num / den

    def V(self, ctx, R, retardation=True):
        return (self._short(ctx, R, "BO", -1) + self._short(ctx, R, "REL", 0) + self._short(ctx, R, "QED", 0)
                + self._long(ctx, R, "BO", 3, 1, "g" if retardation else None)
                + self._long(ctx, R, "REL", 2, 0, "shift" if retardation else None)
                + self._long(ctx, R, "QED", 3, 0, None))

    def component(self, ctx, R, comp):
        imin, kmin, kadd = {"BO": (-1, 3, 1), "REL": (0, 2, 0), "QED": (0, 3, 0)}[comp]
        return self._short(ctx, R, comp, imin) + self._long(ctx, R, comp, kmin, kadd, None)

    def sigma(self, ctx, R):
        def one(name):
            v = [ctx.mpf(s) for s in self.p[name]]         # (exponent, coefficient) pairs
            out = ctx.exp(-v[0] * R) * v[1]
            for i in range(1, len(v) // 2):
                out += ctx.exp(-v[2 * i] * R * R) * v[2 * i + 1]
            return out
        return ctx.sqrt(one("aS_BO") ** 2 + one("aS_REL") ** 2)


def _exact(raw) -> Fraction:
    sign, man, exp, _ = raw
    v = Fraction(man) * Fraction(2) ** exp
    return -v if sign else v


def enclose(model: Model, quantity: str, R: Fraction, prec: int, retardation=True):
    mpmath.iv.prec = prec
    Rv = mpmath.iv.mpf(R.numerator) / mpmath.iv.mpf(R.denominator)
    if quantity == "V":
        x = model.V(mpmath.iv, Rv, retardation)
    elif quantity == "sigma":
        x = model.sigma(mpmath.iv, Rv)
    elif quantity in ("V+sigma", "V-sigma"):
        v, s = model.V(mpmath.iv, Rv, retardation), model.sigma(mpmath.iv, Rv)
        x = v + s if quantity == "V+sigma" else v - s
    else:
        x = model.component(mpmath.iv, Rv, quantity)
    lo, hi = x._mpi_
    return _exact(lo), _exact(hi)


def judge_b64(model: Model, quantity: str, R: Fraction, result: int, retardation=True, max_prec=2048):
    """None if `result` is the correctly rounded binary64 value of the quantity at R; else a reason."""
    prec = 160
    while prec <= max_prec:
        a, b = enclose(model, quantity, R, prec, retardation)
        neg = result >> 63
        if neg:
            a, b = -b, -a
        m = result & ~SIGN
        if m > MAX_MAG:
            return "non-finite result"
        lo, hi = _interval(m)
        if lo < a and b < hi:
            return None
        if b <= lo or a >= hi or (a <= 0 <= b and False):
            return f"outside the rounding interval ({float(value(result)):.17g})"
        prec *= 2
    return "undecided at max precision"


def dVdR_numeric(model: Model, R: Fraction, dps: int = 80, retardation=True) -> Fraction:
    """-dV/dR by mpmath's numerical differentiation at `dps` digits (NOT interval-rigorous;
    its error is far below binary64 resolution at these settings)."""
    mpmath.mp.dps = dps
    Rm = mpmath.mpf(R.numerator) / R.denominator
    F = -mpmath.diff(lambda r: model.V(mpmath.mp, r, retardation), Rm)
    man, exp = mpmath.mpf(F).man_exp              # man_exp drops the sign: restore it explicitly
    v = Fraction(abs(man)) * Fraction(2) ** exp
    return -v if F < 0 else v
