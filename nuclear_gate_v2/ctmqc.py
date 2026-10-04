"""CT-MQC and adiabatic-basis Ehrenfest (quantum momentum = 0) for 1D nuclei.

Equations and implementation choices: protocol.json "ct_implementation_choices".
hbar = 1. All trajectories are advanced together (coupled through the
quantum momentum). Deterministic: no random numbers anywhere.
"""

from __future__ import annotations

import time

import numpy as np

from nuclear_gate_v1.dynamics import Scenario, TimeSpec, wigner_nodes

R_EDGE = 8.6
POP_RESET = 0.995


def bandwidth(R, W):
    mean = np.sum(W * R)
    std = np.sqrt(np.sum(W * (R - mean) ** 2))
    neff = 1.0 / np.sum(W**2)
    return 1.06 * std * neff ** (-0.2)


def quantum_momentum(R, W, C, f):
    """Pairwise quantum momentum Q_lk^I (ns x ns per trajectory)."""
    h = bandwidth(R, W)
    diff = R[:, None] - R[None, :]  # R_I - R_J
    g = W[None, :] * np.exp(-0.5 * (diff / h) ** 2)  # w_J g_J(R_I) (common normaliser cancels)
    s = g.sum(axis=1)
    alpha = 0.5 * s / h**2 / s
    direct = 0.5 * np.sum(g * diff, axis=1) / h**2 / s
    pop = np.abs(C) ** 2
    ns = C.shape[1]
    Q = np.empty((R.size, ns, ns))
    lo, hi = R.min() - 3 * h, R.max() + 3 * h
    pairs_direct = 0
    for l in range(ns):
        Q[:, l, l] = direct
        for k in range(l + 1, ns):
            a = pop[:, l] * pop[:, k] * (f[:, k] - f[:, l])
            den = np.sum(W * a * alpha)
            if abs(den) < 1e-14:
                q = direct
                pairs_direct += 1
            else:
                R0 = np.sum(W * a * alpha * R) / den
                if R0 < lo or R0 > hi:
                    q = direct
                    pairs_direct += 1
                else:
                    q = alpha * (R - R0)
            Q[:, l, k] = q
            Q[:, k, l] = q
    return Q, pairs_direct


def deriv_C(C, e, d, v, Q, f, M):
    """dC/dt for all trajectories. C (N,ns), e (N,ns), d (N,ns,ns), v (N), Q (N,ns,ns), f (N,ns)."""
    out = -1j * e * C - v[:, None] * np.einsum("ilk,ik->il", d, C)
    if Q is not None:
        pop = np.abs(C) ** 2
        fdiff = f[:, :, None] - f[:, None, :]  # f_l - f_k
        out = out + (1.0 / M) * np.einsum("ik,ilk,ilk->il", pop, Q, fdiff) * C
    return out


def force(C, e, g, d, Q, f, M):
    pop = np.abs(C) ** 2
    F = -np.sum(pop * g, axis=1)
    rho = np.conj(C)[:, :, None] * C[:, None, :]  # C_l* C_k
    de = e[:, None, :] - e[:, :, None]  # e_k - e_l
    F = F - np.real(np.sum(rho * de * d, axis=(1, 2)))
    if Q is not None:
        fdiff = f[:, None, :] - f[:, :, None]  # f_k - f_l
        F = F - (2.0 / M) * np.einsum("il,ik,ilk,il,ilk->i", pop, pop, Q, f, fdiff)
    return F


def run(table, M: float, ts: TimeSpec, sc: Scenario, nquad: int, coupled: bool, R_g=None):
    """coupled=True: CT-MQC. coupled=False: Ehrenfest in the adiabatic basis."""
    t0w, t0c = time.perf_counter(), time.process_time()
    ns = table.ns
    R, P, W = wigner_nodes(sc, nquad)
    C = np.zeros((R.size, ns), complex)
    C[:, 0] = 1.0
    f = np.zeros((R.size, ns))
    dt = ts.dt
    samples = []
    direct_pairs = 0
    left_table = False

    def Qnow(R, C, f):
        nonlocal direct_pairs
        if not coupled:
            return None
        Q, nd = quantum_momentum(R, W, C, f)
        direct_pairs += nd
        return Q

    def sample(t):
        pop = np.abs(C) ** 2
        e = table.E(R)
        rt = table.RT(R)
        eright = np.real(np.einsum("ik,ikl,il->i", np.conj(C), rt, C))
        Eens = P**2 / (2 * M) + np.sum(pop * e, axis=1)
        Pexc = 1.0 - pop[:, 0]
        s = {
            "t": t,
            "energy": float(np.sum(W * Eens)),
            "_E": Eens,
            "P_exc": float(np.sum(W * Pexc)),
            "R_mean": float(np.sum(W * R)),
            "R_mean_0": float(np.sum(W * pop[:, 0] * R) / np.sum(W * pop[:, 0])),
            "R_mean_exc": float(np.sum(W * Pexc * R) / np.sum(W * Pexc)) if np.sum(W * Pexc) > 1e-12 else None,
            "electron_right": float(np.sum(W * eright)),
            "coherence_indicator": float(np.sum(W * pop[:, 0] * pop[:, 1])),
            "nuclear_edge": float(np.sum(W[np.abs(R) > R_EDGE])),
            "electron_edge": 0.0,
            "norm": float(np.max(np.abs(np.sum(pop, axis=1) - 1.0)) + 1.0),
        }
        if sc.R_b is not None:
            s["transmission"] = float(np.sum(W[R > sc.R_b]))
        samples.append(s)

    Q = Qnow(R, C, f)
    F = force(C, table.E(R), table.G(R), table.D(R), Q, f, M)
    sample(0.0)
    for step in range(1, ts.nsteps + 1):
        Ph = P + 0.5 * dt * F
        Rn = R + dt * Ph / M
        if np.any(Rn < table.lo) or np.any(Rn > table.hi):
            left_table = True
            break
        v = Ph / M

        def rhs(tau, Cc):
            Rt = R + (tau / dt) * (Rn - R)
            return deriv_C(Cc, table.E(Rt), table.D(Rt), v, Q, f, M)

        k1 = rhs(0.0, C)
        k2 = rhs(0.5 * dt, C + 0.5 * dt * k1)
        k3 = rhs(0.5 * dt, C + 0.5 * dt * k2)
        k4 = rhs(dt, C + dt * k3)
        C = C + (dt / 6.0) * (k1 + 2 * k2 + 2 * k3 + k4)
        f = f - table.G(0.5 * (R + Rn)) * dt
        R = Rn
        if coupled:
            pure = np.max(np.abs(C) ** 2, axis=1) > POP_RESET
            f[pure] = 0.0
        Q = Qnow(R, C, f)
        F = force(C, table.E(R), table.G(R), table.D(R), Q, f, M)
        P = Ph + 0.5 * dt * F
        if step % ts.steps_per_sample == 0:
            sample(step * dt)
    E0 = samples[0]["_E"]
    for s in samples:
        s["max_traj_energy_dev"] = float(np.max(np.abs(s["_E"] - E0)))
        del s["_E"]
    out = {"method": "CT" if coupled else "EHA", "nquad": nquad, "samples": samples,
           "cost": {"wall_s": time.perf_counter() - t0w, "cpu_s": time.process_time() - t0c},
           "state_values": int(C.size * 2 + f.size + 2 * R.size), "dt": dt,
           "direct_Q_pair_fallbacks": direct_pairs}
    if left_table:
        out["domain_stop"] = "trajectory left the tabulated range"
    return out
