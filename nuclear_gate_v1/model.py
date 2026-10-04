"""Shin-Metiu 1D model: potentials, grids, adiabatic electronic states.

H = -1/(2M) d2/dR2 - 1/2 d2/dx2 + V(x, R)
V(x, R) = 1/|L/2 - R| + 1/|L/2 + R|
          - f(|R - x|, Rf) - f(|x - L/2|, Rr) - f(|x + L/2|, Rl)
f(r, c) = erf(r / c) / r,  f(0, c) = 2 / (sqrt(pi) c)

Model form: S. Shin and H. Metiu, J. Chem. Phys. 102, 9285 (1995).
Parameters are sealed in protocol.json; this module does not choose them.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.linalg import eigh
from scipy.special import erf

SQRT_PI = np.sqrt(np.pi)


@dataclass(frozen=True)
class Params:
    L: float
    Rf: float
    Rl: float
    Rr: float
    M: float


@dataclass(frozen=True)
class Grid:
    lo: float
    hi: float
    n: int

    @property
    def points(self) -> np.ndarray:
        return self.lo + (self.hi - self.lo) * np.arange(self.n) / self.n

    @property
    def step(self) -> float:
        return (self.hi - self.lo) / self.n

    @property
    def k(self) -> np.ndarray:
        return 2.0 * np.pi * np.fft.fftfreq(self.n, d=self.step)


def soft(r: np.ndarray, c: float) -> np.ndarray:
    """erf(r/c)/r with the analytic limit at r = 0."""
    r = np.asarray(r, dtype=float)
    small = r < 1e-6
    safe = np.where(small, 1.0, r)
    series = (2.0 / (SQRT_PI * c)) * (1.0 - r * r / (3.0 * c * c))
    return np.where(small, series, erf(safe / c) / safe)


def soft_deriv(r: np.ndarray, c: float) -> np.ndarray:
    """d/dr [erf(r/c)/r]; odd-order series near r = 0 (value -> 0)."""
    r = np.asarray(r, dtype=float)
    small = r < 1e-4
    safe = np.where(small, 1.0, r)
    exact = ((2.0 / (SQRT_PI * c)) * np.exp(-(safe / c) ** 2) * safe - erf(safe / c)) / (safe * safe)
    series = -(4.0 / (3.0 * SQRT_PI * c**3)) * r
    return np.where(small, series, exact)


def nuclear_repulsion(R: np.ndarray, p: Params) -> np.ndarray:
    h = p.L / 2.0
    return 1.0 / np.abs(h - R) + 1.0 / np.abs(h + R)


def nuclear_repulsion_deriv(R: np.ndarray, p: Params) -> np.ndarray:
    h = p.L / 2.0
    return 1.0 / (h - R) ** 2 - 1.0 / (h + R) ** 2


def electron_potential(x: np.ndarray, R: np.ndarray, p: Params) -> np.ndarray:
    """Electron-ion attraction only (broadcasts x against R)."""
    h = p.L / 2.0
    return -soft(np.abs(R - x), p.Rf) - soft(np.abs(x - h), p.Rr) - soft(np.abs(x + h), p.Rl)


def potential(x: np.ndarray, R: np.ndarray, p: Params) -> np.ndarray:
    return nuclear_repulsion(R, p) + electron_potential(x, R, p)


def dV_dR(x: np.ndarray, R: np.ndarray, p: Params) -> np.ndarray:
    """Partial derivative of V(x, R) with respect to the moving nucleus R."""
    d = R - x
    return nuclear_repulsion_deriv(R, p) - soft_deriv(np.abs(d), p.Rf) * np.sign(d)


def kinetic_matrix(g: Grid, mass: float) -> np.ndarray:
    """Dense Fourier (periodic sinc) kinetic matrix, identical to split-operator T."""
    eye = np.eye(g.n)
    t = np.fft.ifft((g.k**2 / (2.0 * mass))[:, None] * np.fft.fft(eye, axis=0), axis=0)
    t = 0.5 * (t + t.conj().T)
    return t.real


def adiabatic_states(R_values: np.ndarray, xg: Grid, p: Params, nstates: int):
    """Electronic eigenpairs at each R. Vectors are L2-normalised on the grid
    (sum |c|^2 dx = 1) with a continuity sign convention."""
    x = xg.points
    T = kinetic_matrix(xg, 1.0)
    energies = np.empty((len(R_values), nstates))
    vectors = np.empty((len(R_values), nstates, xg.n))
    prev = None
    for i, R in enumerate(R_values):
        H = T + np.diag(potential(x, R, p))
        w, v = eigh(H, subset_by_index=[0, nstates - 1])
        v = v.T / np.sqrt(xg.step)
        if prev is None:
            for k in range(nstates):
                if v[k].sum() < 0:
                    v[k] = -v[k]
        else:
            for k in range(nstates):
                if np.dot(v[k], prev[k]) < 0:
                    v[k] = -v[k]
        energies[i] = w
        vectors[i] = v
        prev = v
    return energies, vectors
