"""Tabulated adiabatic quantities for trajectory methods (cubic splines)."""

from __future__ import annotations

import numpy as np
from scipy.interpolate import CubicSpline

from nuclear_gate_v1.model import (Grid, Params, adiabatic_states, dV_dR, nuclear_repulsion,
                                   nuclear_repulsion_deriv)


def _matrix_elements(R_values, xg: Grid, p: Params, ns: int):
    E, phi = adiabatic_states(np.asarray(R_values), xg, p, ns)
    x, dx = xg.points, xg.step
    nR = len(R_values)
    grad = np.empty((nR, ns))
    d = np.zeros((nR, ns, ns))
    right = np.empty((nR, ns, ns))
    theta = (x > 0).astype(float)
    for i, R in enumerate(R_values):
        dV = dV_dR(x, np.full_like(x, R), p)
        ph = phi[i]
        W = (ph * dV[None, :]) @ ph.T * dx  # <phi_l|dV/dR|phi_k>
        grad[i] = np.diag(W)
        for l in range(ns):
            for k in range(ns):
                if l != k:
                    d[i, l, k] = W[l, k] / (E[i, k] - E[i, l])
        right[i] = (ph * theta[None, :]) @ ph.T * dx
    return E, grad, d, right


class AdiabaticTable:
    """Splines of e_k(R), de_k/dR, d_lk(R) and <phi_k|Theta(x)|phi_l>(R).

    The bare nuclear repulsion 1/|L/2-R| + 1/|L/2+R| (identical for every state) is
    removed before splining and added back analytically: it is known exactly and
    is the steepest part of the surfaces near the fixed ions."""

    def __init__(self, p: Params, xg: Grid, ns: int, Rtab: Grid):
        self.p, self.xg, self.ns = p, xg, ns
        R = Rtab.points
        self.lo, self.hi = R[0], R[-1]
        E, grad, d, right = _matrix_elements(R, xg, p, ns)
        rep, drep = nuclear_repulsion(R, p), nuclear_repulsion_deriv(R, p)
        self._E = CubicSpline(R, E - rep[:, None], axis=0)
        self._G = CubicSpline(R, grad - drep[:, None], axis=0)
        self.D = CubicSpline(R, d, axis=0)
        self.RT = CubicSpline(R, right, axis=0)
        self.R = R
        self.E_tab = E

    def E(self, R):
        R = np.asarray(R, dtype=float)
        return self._E(R) + nuclear_repulsion(R, self.p)[..., None]

    def G(self, R):
        R = np.asarray(R, dtype=float)
        return self._G(R) + nuclear_repulsion_deriv(R, self.p)[..., None]

    def validate(self, n: int = 64) -> dict:
        """Compare splines with direct eigensolves at off-grid points (sealed check)."""
        step = self.R[1] - self.R[0]
        pts = np.linspace(self.lo + 0.37 * step, self.hi - 0.63 * step, n)
        E, grad, d, _ = _matrix_elements(pts, self.xg, self.p, self.ns)
        e_err = float(np.max(np.abs(self.E(pts) - E)))
        d_err = float(np.max(np.abs(np.abs(self.D(pts)) - np.abs(d))))
        d_max = float(np.max(np.abs(d)))
        return {"energy_err": e_err, "coupling_err": d_err, "coupling_max": d_max,
                "pass": bool(e_err <= 1e-7 and d_err <= 1e-4 * d_max)}
