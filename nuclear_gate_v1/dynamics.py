"""Four nuclear treatments on the Shin-Metiu model. Producer side only:
returns raw observables. Verdicts are computed by checker.py, which does
not import this module."""

from __future__ import annotations

import time
from dataclasses import dataclass

import numpy as np
import scipy.fft as sfft
from numpy.polynomial.hermite_e import hermegauss
from scipy.interpolate import CubicSpline

from .model import Grid, Params, adiabatic_states, dV_dR, potential

FFT_WORKERS = 8
E_EDGE = 28.0
R_EDGE = 8.6


@dataclass(frozen=True)
class Scenario:
    name: str
    R0: float
    P0: float
    sigma: float
    R_b: float | None  # transmission divider (S2) or None


@dataclass(frozen=True)
class TimeSpec:
    dt: float
    t_final: float
    sample_every: float

    @property
    def nsteps(self) -> int:
        return int(round(self.t_final / self.dt))

    @property
    def steps_per_sample(self) -> int:
        return int(round(self.sample_every / self.dt))


def nuclear_packet(R: np.ndarray, sc: Scenario, dR: float) -> np.ndarray:
    chi = np.exp(-((R - sc.R0) ** 2) / sc.sigma**2) * np.exp(1j * sc.P0 * R)
    return chi / np.sqrt(np.sum(np.abs(chi) ** 2) * dR)


def _clock():
    return time.perf_counter(), time.process_time()


def _elapsed(start):
    w, c = _clock()
    return {"wall_s": w - start[0], "cpu_s": c - start[1]}


# ---------------------------------------------------------------- Q
def run_q(p: Params, Rg: Grid, xg: Grid, ts: TimeSpec, sc: Scenario, nstates: int, adiabatic=None):
    """Nucleus + electron both quantum: 2D split-operator (Strang)."""
    start = _clock()
    R, x = Rg.points, xg.points
    dR, dx = Rg.step, xg.step
    if adiabatic is None:
        adiabatic = adiabatic_states(R, xg, p, nstates)
    _, phi = adiabatic  # (nR, nstates, nx)
    V = potential(x[None, :], R[:, None], p)
    TR = (Rg.k**2 / (2.0 * p.M))[:, None]
    Tx = (xg.k**2 / 2.0)[None, :]
    Tk = TR + Tx
    expV = np.exp(-0.5j * ts.dt * V)
    expT = np.exp(-1j * ts.dt * Tk)
    psi = nuclear_packet(R, sc, dR)[:, None] * phi[:, 0, :]
    psi = psi / np.sqrt(np.sum(np.abs(psi) ** 2) * dR * dx)
    ncell = psi.size
    xmask_edge = np.abs(x) > E_EDGE
    Rmask_edge = np.abs(R) > R_EDGE
    samples = []

    def sample(t):
        dens = np.abs(psi) ** 2
        norm = dens.sum() * dR * dx
        pk = sfft.fft2(psi, workers=FFT_WORKERS)
        ekin = np.sum(np.abs(pk) ** 2 * Tk) / ncell * dR * dx
        epot = np.sum(dens * V) * dR * dx
        c = np.einsum("rkx,rx->rk", phi, psi) * dx  # (nR, nstates)
        rho_tot = dens.sum(axis=1) * dx
        rho0 = np.abs(c[:, 0]) ** 2
        rho_exc = rho_tot - rho0
        P0 = rho0.sum() * dR
        Pexc = rho_exc.sum() * dR
        s = {
            "t": t,
            "norm": float(norm),
            "energy": float((ekin + epot) / norm),
            "P_states": [float(np.sum(np.abs(c[:, k]) ** 2) * dR) for k in range(nstates)],
            "P_exc": float(Pexc / norm),
            "R_mean_0": float(np.sum(R * rho0) / rho0.sum()),
            "R_mean_exc": float(np.sum(R * rho_exc) / rho_exc.sum()) if Pexc > 1e-12 else None,
            "electron_right": float(dens[:, x > 0].sum() * dR * dx / norm),
            "electron_edge": float(dens[:, xmask_edge].sum() * dR * dx),
            "nuclear_edge": float(dens[Rmask_edge, :].sum() * dR * dx),
        }
        if sc.R_b is not None:
            s["transmission"] = float(dens[R > sc.R_b, :].sum() * dR * dx / norm)
        samples.append(s)

    sample(0.0)
    for step in range(1, ts.nsteps + 1):
        psi *= expV
        psi = sfft.ifft2(expT * sfft.fft2(psi, workers=FFT_WORKERS), workers=FFT_WORKERS)
        psi *= expV
        if step % ts.steps_per_sample == 0:
            sample(step * ts.dt)
    return {"method": "Q", "samples": samples, "cost": _elapsed(start),
            "state_values": int(psi.size), "grid": [Rg.n, xg.n], "dt": ts.dt}


# ---------------------------------------------------------------- BOQ
def run_boq(p: Params, Rg: Grid, xg: Grid, ts: TimeSpec, sc: Scenario, adiabatic):
    """Nucleus quantum on the ground adiabatic surface only (no diagonal correction)."""
    start = _clock()
    R, x = Rg.points, xg.points
    dR, dx = Rg.step, xg.step
    E, phi = adiabatic
    V0 = E[:, 0]
    eright = (np.abs(phi[:, 0, :]) ** 2)[:, x > 0].sum(axis=1) * dx
    T = Rg.k**2 / (2.0 * p.M)
    expV = np.exp(-0.5j * ts.dt * V0)
    expT = np.exp(-1j * ts.dt * T)
    chi = nuclear_packet(R, sc, dR)
    Rmask_edge = np.abs(R) > R_EDGE
    samples = []

    def sample(t):
        dens = np.abs(chi) ** 2
        norm = dens.sum() * dR
        ck = np.fft.fft(chi)
        ekin = np.sum(np.abs(ck) ** 2 * T) / R.size * dR
        s = {
            "t": t,
            "norm": float(norm),
            "energy": float((ekin + np.sum(dens * V0) * dR) / norm),
            "P_exc": 0.0,
            "R_mean_0": float(np.sum(R * dens) / dens.sum()),
            "R_mean_exc": None,
            "electron_right": float(np.sum(dens * eright) * dR / norm),
            "electron_edge": float(np.sum(dens * (np.abs(phi[:, 0, :]) ** 2)[:, np.abs(x) > E_EDGE].sum(axis=1) * dx) * dR),
            "nuclear_edge": float(dens[Rmask_edge].sum() * dR),
        }
        if sc.R_b is not None:
            s["transmission"] = float(dens[R > sc.R_b].sum() * dR / norm)
        samples.append(s)

    sample(0.0)
    for step in range(1, ts.nsteps + 1):
        chi *= expV
        chi = np.fft.ifft(expT * np.fft.fft(chi))
        chi *= expV
        if step % ts.steps_per_sample == 0:
            sample(step * ts.dt)
    return {"method": "BOQ", "samples": samples, "cost": _elapsed(start),
            "state_values": int(chi.size), "grid": [Rg.n], "dt": ts.dt,
            "structural": {"P_exc": "ABSENT_BY_CONSTRUCTION", "branch_separation": "ABSENT_BY_CONSTRUCTION"}}


# ---------------------------------------------------------------- classical ensembles
def wigner_nodes(sc: Scenario, n: int):
    """Deterministic Gauss-Hermite product quadrature of the Wigner function of
    |chi|^2 ~ exp(-2(R-R0)^2/sigma^2): position std sigma/2, momentum std 1/sigma."""
    z, w = hermegauss(n)
    w = w / w.sum()
    sR, sP = sc.sigma / 2.0, 1.0 / sc.sigma
    Rn = (sc.R0 + sR * z)[:, None] * np.ones(n)[None, :]
    Pn = np.ones(n)[:, None] * (sc.P0 + sP * z)[None, :]
    W = w[:, None] * w[None, :]
    return Rn.ravel(), Pn.ravel(), W.ravel()


def _ground_at(Rvals, xg: Grid, p: Params, nstates: int):
    return adiabatic_states(np.asarray(Rvals), xg, p, nstates)


def _final_classical(Rf, psi, W, xg, p, nstates, sc, x):
    """Exact adiabatic projections at final positions (per trajectory eigensolve)."""
    E, phi = _ground_at(Rf, xg, p, nstates)  # sign continuity irrelevant for |.|^2
    dx = xg.step
    if psi is None:
        P0 = np.ones_like(Rf)
        eright = (np.abs(phi[:, 0, :]) ** 2)[:, x > 0].sum(axis=1) * dx
    else:
        P0 = np.abs(np.einsum("ix,ix->i", phi[:, 0, :], psi) * dx) ** 2
        eright = (np.abs(psi) ** 2)[:, x > 0].sum(axis=1) * dx
    Pexc = 1.0 - P0
    out = {
        "P_exc": float(np.sum(W * Pexc)),
        "R_mean_0": float(np.sum(W * P0 * Rf) / np.sum(W * P0)),
        "R_mean_exc": float(np.sum(W * Pexc * Rf) / np.sum(W * Pexc)) if np.sum(W * Pexc) > 1e-12 else None,
        "electron_right": float(np.sum(W * eright)),
    }
    if sc.R_b is not None:
        out["transmission"] = float(np.sum(W[Rf > sc.R_b]))
    return out


def run_eh(p: Params, xg: Grid, ts: TimeSpec, sc: Scenario, nquad: int, nstates: int):
    """Ehrenfest: classical nuclei (deterministic Wigner quadrature), each with its
    own time-dependent electron wavefunction; force = -<psi|dV/dR|psi>."""
    start = _clock()
    x, dx = xg.points, xg.step
    Rn, Pn, W = wigner_nodes(sc, nquad)
    _, phi0 = _ground_at(Rn, xg, p, 1)
    psi = phi0[:, 0, :].astype(complex)
    Tx = xg.k**2 / 2.0
    expT = np.exp(-1j * ts.dt * Tx)[None, :]
    emask = np.abs(x) > E_EDGE

    def force(Rv, ps):
        return -np.sum(np.abs(ps) ** 2 * dV_dR(x[None, :], Rv[:, None], p), axis=1) * dx

    def e_el(Rv, ps):
        pk = np.fft.fft(ps, axis=1)
        kin = np.sum(np.abs(pk) ** 2 * Tx[None, :], axis=1) / x.size * dx
        return kin + np.sum(np.abs(ps) ** 2 * potential(x[None, :], Rv[:, None], p), axis=1) * dx

    R, P = Rn.copy(), Pn.copy()
    F = force(R, psi)
    samples = []

    def sample(t):
        E = P**2 / (2 * p.M) + e_el(R, psi)
        samples.append({
            "t": t,
            "energy": float(np.sum(W * E)),
            "max_traj_energy_dev": None,
            "norm": float(np.max(np.abs(np.sum(np.abs(psi) ** 2, axis=1) * dx - 1.0)) + 1.0),
            "electron_edge": float(np.sum(W * (np.abs(psi) ** 2)[:, emask].sum(axis=1) * dx)),
            "nuclear_edge": float(np.sum(W[np.abs(R) > R_EDGE])),
            "_E_traj": E,
        })

    sample(0.0)
    for step in range(1, ts.nsteps + 1):
        Ph = P + 0.5 * ts.dt * F
        Rnew = R + ts.dt * Ph / p.M
        Vm = potential(x[None, :], 0.5 * (R + Rnew)[:, None], p)
        eV = np.exp(-0.5j * ts.dt * Vm)
        psi = eV * psi
        psi = np.fft.ifft(expT * np.fft.fft(psi, axis=1), axis=1)
        psi = eV * psi
        R = Rnew
        F = force(R, psi)
        P = Ph + 0.5 * ts.dt * F
        if step % ts.steps_per_sample == 0:
            sample(step * ts.dt)
    E0 = samples[0]["_E_traj"]
    for s in samples:
        s["max_traj_energy_dev"] = float(np.max(np.abs(s["_E_traj"] - E0)))
        del s["_E_traj"]
    final = _final_classical(R, psi, W, xg, p, nstates, sc, x)
    samples[-1].update(final)
    return {"method": "EH", "nquad": nquad, "samples": samples, "cost": _elapsed(start),
            "state_values": int(psi.size + 2 * R.size), "dt": ts.dt}


def run_bocl(p: Params, Rg: Grid, xg: Grid, ts: TimeSpec, sc: Scenario, nquad: int,
             nstates: int, adiabatic):
    """Classical nuclei (same quadrature) on the ground adiabatic surface (cubic spline
    of the primary-grid energies). No electron dynamics."""
    start = _clock()
    x = xg.points
    V0 = CubicSpline(Rg.points, adiabatic[0][:, 0])
    dV0 = V0.derivative()
    Rn, Pn, W = wigner_nodes(sc, nquad)
    R, P = Rn.copy(), Pn.copy()
    lo, hi = Rg.points[0], Rg.points[-1]
    samples = []
    left_spline = False

    def sample(t):
        E = P**2 / (2 * p.M) + V0(R)
        samples.append({"t": t, "energy": float(np.sum(W * E)), "_E_traj": E,
                        "nuclear_edge": float(np.sum(W[np.abs(R) > R_EDGE])),
                        "electron_edge": 0.0, "norm": 1.0})

    sample(0.0)
    F = -dV0(R)
    for step in range(1, ts.nsteps + 1):
        Ph = P + 0.5 * ts.dt * F
        R = R + ts.dt * Ph / p.M
        if np.any(R < lo) or np.any(R > hi):
            left_spline = True
            break
        F = -dV0(R)
        P = Ph + 0.5 * ts.dt * F
        if step % ts.steps_per_sample == 0:
            sample(step * ts.dt)
    E0 = samples[0]["_E_traj"]
    for s in samples:
        s["max_traj_energy_dev"] = float(np.max(np.abs(s["_E_traj"] - E0)))
        del s["_E_traj"]
    out = {"method": "BOCL", "nquad": nquad, "samples": samples, "cost": _elapsed(start),
           "state_values": int(2 * R.size), "dt": ts.dt,
           "structural": {"P_exc": "ABSENT_BY_CONSTRUCTION", "branch_separation": "ABSENT_BY_CONSTRUCTION"}}
    if left_spline:
        out["domain_stop"] = "trajectory left the tabulated surface range"
        return out
    final = _final_classical(R, None, W, xg, p, nstates, sc, x)
    final["P_exc"] = 0.0
    final["R_mean_exc"] = None
    samples[-1].update(final)
    out["cost"] = _elapsed(start)
    return out
