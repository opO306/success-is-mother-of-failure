"""Classical nuclei on the ground surface, transmission integrated over the
Wigner density on a uniform phase-space grid (independent trajectories)."""

from __future__ import annotations

import time

import numpy as np

from nuclear_gate_v1.dynamics import Scenario, TimeSpec

SPAN = 7.0


def run_bocl_exact(table, M: float, ts: TimeSpec, sc: Scenario, n: int):
    t0w, t0c = time.perf_counter(), time.process_time()
    sR, sP = sc.sigma / 2.0, 1.0 / sc.sigma
    zr = np.linspace(-SPAN, SPAN, n)
    w1 = np.exp(-0.5 * zr**2)
    R = (sc.R0 + sR * zr)[:, None] * np.ones(n)[None, :]
    P = np.ones(n)[:, None] * (sc.P0 + sP * zr)[None, :]
    W = (w1[:, None] * w1[None, :]).ravel()
    W = W / W.sum()
    R, P = R.ravel(), P.ravel()
    V0 = lambda r: table.E(r)[:, 0]
    G0 = lambda r: table.G(r)[:, 0]
    E_init = P**2 / (2 * M) + V0(R)
    above = float(np.sum(W[E_init > float(table.E(np.array([sc.R_b]))[0, 0])]))
    alive = np.ones(R.size, bool)
    F = -G0(R)
    for _ in range(ts.nsteps):
        Ph = P + 0.5 * ts.dt * F
        R = R + ts.dt * Ph / M
        out = (R < table.lo) | (R > table.hi)
        if out.any():
            alive &= ~out
            R = np.clip(R, table.lo, table.hi)
        F = -G0(R)
        P = Ph + 0.5 * ts.dt * F
    T = float(np.sum(W[alive & (R > sc.R_b)]))
    lost = float(np.sum(W[~alive]))
    return {"method": "BOCL_exact", "n": n, "transmission": T, "wigner_mass_above_barrier": above,
            "weight_left_table": lost,
            "cost": {"wall_s": time.perf_counter() - t0w, "cpu_s": time.process_time() - t0c},
            "state_values": int(2 * R.size)}
