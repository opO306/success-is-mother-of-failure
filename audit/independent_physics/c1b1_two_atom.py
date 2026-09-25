"""Independent audit for C1-B1 (two 40Ar atoms): classical reference solutions and conserved quantities.

Imports neither a_reference, a_numeric nor engine (tests enforce it). The potential is the audit's own Lang 2024
model (parameters parsed from the published Fortran, ar2_lang2024.Model), the masses are typed here from the
designer's 11th verdict. Everything is mpmath quadrature at high precision -- strong independent checks, not
proofs.

Relative motion of two equal masses m: reduced mass mu = m/2, relative momentum P = p_j (with p_i = -p_j).
  Q(r)            = 2 mu (E - V(r)) - L^2 / r^2            (radial momentum squared)
  sweep angle     = 2 * int_{r0}^{R} (L / r^2) / sqrt(Q) dr   (polar angle swept from R in to r0 and back to R)
  sojourn time    = 2 * int_{r0}^{R} mu / sqrt(Q) dr
  deflection      chi = pi - sweep(R -> infinity)
  radial period   T = 2 * int_{r-}^{r+} mu / sqrt(2 mu (E - V)) dr      (L = 0 bound motion)
Endpoint singularities are removed by r = r0 + u^2 (and r = r+ - u^2).
"""
from __future__ import annotations

from fractions import Fraction

import mpmath

from audit.independent_physics.ar2_lang2024 import Model, parse_fortran

AR40_MASS_ME = Fraction("39.9623831237") / Fraction("5.485799090441e-4")   # NIST 40Ar / CODATA 2022 m_e in u
DPS = 30


def _bisect(f, lo, hi, iters=None):
    """Root of f in [lo, hi], f(lo) and f(hi) of opposite sign (plain bisection: slow, always converges).
    Iterations follow the working precision (the bracket shrinks below 10^-dps). Returns the bracket end
    where f > 0 -- the allowed side."""
    iters = iters or int(3.33 * mpmath.mp.dps) + 40
    flo = f(lo)
    for _ in range(iters):
        mid = (lo + hi) / 2
        if (f(mid) > 0) == (flo > 0):
            lo, flo = mid, f(mid)
        else:
            hi = mid
    return lo if flo > 0 else hi


def _endpoint_root(h, u, d1, d2, near):
    """sqrt(h(u^2)) / u for a radicand h that vanishes at u = 0 with h'(0) = d1 > 0 (h ~ d1 u^2 + d2 u^4 / 2).
    For u^2 below `near` the Taylor form is used -- at u = 0 exactly it is the analytic limit sqrt(d1);
    elsewhere the radicand is evaluated directly."""
    if u * u < near:
        return mpmath.sqrt(d1 + d2 * u * u / 2)
    x = h(u * u)
    if x <= 0:
        raise ArithmeticError(f"radicand {x} <= 0 at u = {u} above the Taylor threshold")
    return mpmath.sqrt(x) / u


class Reference:
    def __init__(self, model: Model | None = None, dps: int = DPS):
        self.model = model or Model(parse_fortran())
        self.dps = dps

    def _mp(self, x):
        if isinstance(x, Fraction):
            return mpmath.mpf(x.numerator) / x.denominator
        return mpmath.mpf(x)

    def V(self, r):
        return self.model.V(mpmath.mp, r, True)

    def _dV(self, r, n):
        return mpmath.diff(self.V, r, n)

    def _near(self):
        return mpmath.mpf(10) ** (-(mpmath.mp.dps // 2) - 5)

    # --- scattering -------------------------------------------------------------------------------------
    def _Q(self, r, E, L, mu):
        return 2 * mu * (E - self.V(r)) - L * L / (r * r)

    def turning_point(self, E, L, R_start):
        """The largest r < R_start with Q(r) = 0 (the turning point reached coming in from R_start)."""
        mu = self._mp(AR40_MASS_ME) / 2
        hi = self._mp(R_start)
        if self._Q(hi, E, L, mu) <= 0:
            raise ValueError("no motion at the start radius")
        step = mpmath.mpf("0.05")
        lo = hi - step
        while self._Q(lo, E, L, mu) > 0:
            hi, lo = lo, lo - step
            if lo < 1:
                raise ValueError("no turning point above 1 bohr")
        return _bisect(lambda r: self._Q(r, E, L, mu), lo, hi)

    def sweep_and_time(self, E, L, R_start, to_infinity=False):
        """(swept polar angle, sojourn time) between R_start (or infinity) and the turning point, in and out.
        r = r0 + u^2; 2u / sqrt(Q) = 2 / (sqrt(Q)/u), whose u -> 0 limit 2 / sqrt(Q'(r0)) is used at the end."""
        with mpmath.workdps(self.dps):
            E, L, R_start = self._mp(E), self._mp(L), self._mp(R_start)
            mu = self._mp(AR40_MASS_ME) / 2
            r0 = self.turning_point(E, L, R_start)
            d1 = -2 * mu * self._dV(r0, 1) + 2 * L * L / r0 ** 3            # Q'(r0)
            d2 = -2 * mu * self._dV(r0, 2) - 6 * L * L / r0 ** 4            # Q''(r0)
            near = self._near()
            root = lambda u: _endpoint_root(lambda h: self._Q(r0 + h, E, L, mu), u, d1, d2, near)
            f_angle = lambda u: 2 * (L / (r0 + u * u) ** 2) / root(u)
            f_time = lambda u: 2 * mu / root(u)
            umax = mpmath.sqrt(R_start - r0)
            ang = 2 * mpmath.quad(f_angle, [0, umax / 4, umax])
            tim = 2 * mpmath.quad(f_time, [0, umax / 4, umax])
            if to_infinity:
                ang += 2 * mpmath.quad(lambda r: (L / (r * r)) / mpmath.sqrt(self._Q(r, E, L, mu)),
                                       [R_start, 4 * R_start, mpmath.inf])
            return ang, tim, r0

    def deflection(self, E, L):
        """chi = pi - total sweep from infinity to the turning point and back."""
        ang, _, _ = self.sweep_and_time(E, L, 40, to_infinity=True)
        return mpmath.pi - ang

    # --- bound radial motion, L = 0 --------------------------------------------------------------------
    def radial_period(self, E, r_inner):
        """T(E) for L = 0; r_inner = a point inside the well (V(r_inner) < E). Both endpoint limits analytic."""
        with mpmath.workdps(self.dps):
            E = self._mp(E)
            mu = self._mp(AR40_MASS_ME) / 2
            g = lambda r: E - self.V(r)
            lo, hi = self._mp(r_inner), self._mp(r_inner)
            while g(lo) > 0:                    # walk inward to V > E
                lo -= mpmath.mpf("0.05")
            r_minus = _bisect(g, lo, hi)
            hi = hi + mpmath.mpf("0.05")
            while g(hi) > 0:
                hi += mpmath.mpf("0.05")
            r_plus = _bisect(g, hi - mpmath.mpf("0.05"), hi)
            mid = (r_minus + r_plus) / 2
            a, b = mpmath.sqrt(mid - r_minus), mpmath.sqrt(r_plus - mid)
            near = self._near()
            # inner: 2 mu g(r- + h) ~ -2 mu V'(r-) h - mu V''(r-) h^2;  outer: 2 mu g(r+ - h) ~ 2 mu V'(r+) h - mu V''(r+) h^2
            d1i, d2i = -2 * mu * self._dV(r_minus, 1), -2 * mu * self._dV(r_minus, 2)
            d1o, d2o = 2 * mu * self._dV(r_plus, 1), -2 * mu * self._dV(r_plus, 2)
            inner = mpmath.quad(lambda u: 2 * mu / _endpoint_root(lambda h: 2 * mu * g(r_minus + h), u, d1i, d2i,
                                                                   near), [0, a])
            outer = mpmath.quad(lambda u: 2 * mu / _endpoint_root(lambda h: 2 * mu * g(r_plus - h), u, d1o, d2o,
                                                                   near), [0, b])
            return 2 * (inner + outer), r_minus, r_plus

    # --- conserved quantities from exact states ---------------------------------------------------------
    def conserved(self, positions, momenta):
        """(total momentum, total angular momentum, energy) for two atoms given as exact rational 3-vectors."""
        with mpmath.workdps(self.dps):
            m = self._mp(AR40_MASS_ME)
            P = [momenta[0][k] + momenta[1][k] for k in range(3)]
            Lv = [Fraction(0)] * 3
            for r, p in zip(positions, momenta):
                c = (r[1] * p[2] - r[2] * p[1], r[2] * p[0] - r[0] * p[2], r[0] * p[1] - r[1] * p[0])
                Lv = [a + b for a, b in zip(Lv, c)]
            K = sum((self._mp(x) ** 2 for p in momenta for x in p), mpmath.mpf(0)) / (2 * m)
            d = [positions[1][k] - positions[0][k] for k in range(3)]
            R = mpmath.sqrt(self._mp(sum((x * x for x in d), Fraction(0))))
            return P, Lv, K + self.V(R)
