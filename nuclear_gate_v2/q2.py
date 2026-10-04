"""Full quantum reference for V2: V1 split-operator plus the coherence indicator
and the total mean nuclear position time series."""

from __future__ import annotations

import time

import numpy as np
import scipy.fft as sfft

from nuclear_gate_v1.dynamics import Scenario, TimeSpec, nuclear_packet
from nuclear_gate_v1.model import Grid, Params, potential

FFT_WORKERS = 4
E_EDGE = 28.0
R_EDGE = 8.6


def run_q2(p: Params, Rg: Grid, xg: Grid, ts: TimeSpec, sc: Scenario, adiabatic):
    t0w, t0c = time.perf_counter(), time.process_time()
    R, x = Rg.points, xg.points
    dR, dx = Rg.step, xg.step
    _, phi = adiabatic
    ns = phi.shape[1]
    V = potential(x[None, :], R[:, None], p)
    Tk = (Rg.k**2 / (2.0 * p.M))[:, None] + (xg.k**2 / 2.0)[None, :]
    expV = np.exp(-0.5j * ts.dt * V)
    expT = np.exp(-1j * ts.dt * Tk)
    psi = nuclear_packet(R, sc, dR)[:, None] * phi[:, 0, :]
    psi = psi / np.sqrt(np.sum(np.abs(psi) ** 2) * dR * dx)
    ncell = psi.size
    xe, Re = np.abs(x) > E_EDGE, np.abs(R) > R_EDGE
    samples = []

    def sample(t):
        dens = np.abs(psi) ** 2
        norm = dens.sum() * dR * dx
        pk = sfft.fft2(psi, workers=FFT_WORKERS)
        ekin = np.sum(np.abs(pk) ** 2 * Tk) / ncell * dR * dx
        epot = np.sum(dens * V) * dR * dx
        c = np.einsum("rkx,rx->rk", phi, psi) * dx
        rho = dens.sum(axis=1) * dx
        rho0 = np.abs(c[:, 0]) ** 2
        rho1 = np.abs(c[:, 1]) ** 2
        rexc = rho - rho0
        ok = rho > 1e-12
        D = np.sum(rho0[ok] * rho1[ok] / rho[ok]) * dR
        Pexc = rexc.sum() * dR
        s = {
            "t": t,
            "norm": float(norm),
            "energy": float((ekin + epot) / norm),
            "P_states": [float(np.sum(np.abs(c[:, k]) ** 2) * dR) for k in range(ns)],
            "P_exc": float(Pexc / norm),
            "R_mean": float(np.sum(R * rho) / rho.sum()),
            "R_mean_0": float(np.sum(R * rho0) / rho0.sum()),
            "R_mean_exc": float(np.sum(R * rexc) / rexc.sum()) if Pexc > 1e-12 else None,
            "electron_right": float(dens[:, x > 0].sum() * dR * dx / norm),
            "coherence_indicator": float(D / norm),
            "electron_edge": float(dens[:, xe].sum() * dR * dx),
            "nuclear_edge": float(dens[Re, :].sum() * dR * dx),
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
    return {"method": "Q", "samples": samples,
            "cost": {"wall_s": time.perf_counter() - t0w, "cpu_s": time.process_time() - t0c},
            "state_values": int(psi.size), "grid": [Rg.n, xg.n], "dt": ts.dt}
