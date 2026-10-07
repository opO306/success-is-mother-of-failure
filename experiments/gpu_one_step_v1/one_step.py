"""GPU_ONE_STEP_V1 runner (GPU side; the checker never imports it).

GpuForceExecutor keeps the CUDA context, the uploaded model / constants for p and the device buffers for N
(GPU_PAIR_VECTOR_V1's pv_host.PV, unchanged) and evaluates forces F(q) with the GPU canonical atom reduction.
hybrid_step runs one KDK step: p_half = p0 + F0; q1 = q0 + p_half * cdt; F1 = F(q1); p1 = p_half + F1, the kicks and
the drift on the CPU with mpmath's interval primitives at p. Faults (tests only) are listed in protocol.json.
"""

from __future__ import annotations

import time

from mpmath.libmp import mpi_add, mpi_div, mpi_mul

from experiments.gpu_force_feasibility_v1.dyadic import encode_iv
from experiments.gpu_pair_vector_v1 import pv_host as PH

ZERO = ((0, 0, 0, 0), (0, 0, 0, 0))


def lifted(p):
    from fractions import Fraction as Q

    from mpmath import iv

    import exact_expression_gate_v0.lang_iv as LI
    from exact_expression_gate_v1 import common as K
    iv.prec = p
    return {"cdt": LI.c(K.CDT)._mpi_, "dt": LI.c(K.DT)._mpi_, "mass": LI.c(Q(K.MASS))._mpi_}


class GpuForceExecutor:
    def __init__(self, lib, block=32, grid=0):
        t0 = time.perf_counter()
        self.pv = PH.PV(lib)
        self.init = {"executor_create_ms": (time.perf_counter() - t0) * 1000, "context_ms": self.pv.setup["context_ms"]}
        self.block, self.grid, self.p = block, grid, None

    def prepare(self, p, N, upload_p=None):
        t0 = time.perf_counter()
        up = upload_p or p
        if self.pv.p != up:
            self.pv.upload(up)
            self.init["model_upload_total_ms"] = (time.perf_counter() - t0) * 1000
        t1 = time.perf_counter()
        mem = self.pv.alloc_n(N)
        self.init["alloc_call_ms"] = (time.perf_counter() - t1) * 1000
        self.p = p
        return mem

    def force(self, q, N, fault=0, g0fault=0, wl=16, block=None, grid=None):
        """F(q) -> (status, first_stop_pair, F or None, timing)."""
        block = block or self.block
        grid = self.grid if grid is None else grid
        t0 = time.perf_counter()
        pos = PH.encode_positions(q)
        t1 = time.perf_counter()
        _, _, atoms, tm = self.pv.run_state(pos, N, 4, block, grid, fault, g0fault, wl)
        t2 = time.perf_counter()
        dec = PH.decode_atoms(atoms, N)
        t3 = time.perf_counter()
        tm.update(encode_ms=(t1 - t0) * 1000, device_call_ms=(t2 - t1) * 1000, decode_ms=(t3 - t2) * 1000,
                  force_total_ms=(t3 - t0) * 1000)
        if all(x[3] == "PROVEN" for x in dec):
            return "OK", None, [[dec[3 * a + k][4] for k in range(3)] for a in range(N)], tm
        # a stop or a refusal: the first non-PROVEN pair in canonical order from the pair records (slow path)
        P = N * (N - 1) // 2
        _, comp, _, _ = self.pv.run_state(pos, N, 2, block, grid, fault, g0fault, wl)
        for st, pid, _ in PH.decode_compact(comp, P):
            if st != "PROVEN":
                kind = {"VIOLATED": "DOMAIN_STOP_VIOLATED", "UNPROVEN": "DOMAIN_STOP_UNPROVEN"}.get(st, st)
                return kind, pid, None, tm
        return "REFUSED_DEVICE_PRECISION", None, None, tm      # atom status set without a pair status: refuse


def _add(A, B, p):
    return [[mpi_add(A[a][k], B[a][k], p) for k in range(3)] for a in range(len(A))]


def kick(pm, F, p):
    return _add(pm, F, p)


def drift(q, pm, p, c, fault=0):
    if fault == 4:                                           # structure changed: q + (p * DT) / MASS
        return [[mpi_add(q[a][k], mpi_div(mpi_mul(pm[a][k], c["dt"], p), c["mass"], p), p) for k in range(3)]
                for a in range(len(q))]
    return [[mpi_add(q[a][k], mpi_mul(pm[a][k], c["cdt"], p), p) for k in range(3)] for a in range(len(q))]


def _ulp(x):
    """The next representable upper value of an endpoint's mantissa (fault 9 / 10: one ulp)."""
    s, m, e, bc = x
    if not m:
        return (0, 1, -200, 1)
    m2 = m + 1                                               # one unit in the last place of this mantissa
    while m2 and not m2 & 1:
        m2 >>= 1
        e += 1
    return (s, m2, e, m2.bit_length())


def enc(rows):
    return None if rows is None else [[encode_iv(x) for x in r] for r in rows]


def hybrid_step(ex, q0, p0, p, fault=0, pvfault=0, g0fault=0, wl=16, block=None, grid=None, upload_p=None):
    """One KDK step with GPU forces; returns all checkpoints (encoded) and the outcome."""
    import exact_expression_gate_v1.common as K
    from mpmath import iv
    N = len(q0)
    q0 = [list(r) for r in q0]
    p0 = [list(r) for r in p0]
    if fault == 9:
        q0[0][0] = (q0[0][0][0], _ulp(q0[0][0][1]))
    if fault == 10:
        p0[0][0] = (p0[0][0][0], _ulp(p0[0][0][1]))
    ex.prepare(p, N, upload_p)
    c = lifted(p)
    rec = {"N": N, "p": p, "echo_q0": enc(q0), "echo_p0": enc(p0), "F0": None, "p_half": None, "q1": None, "F1": None,
           "p1": None, "status": None, "stop_stage": None, "stop_pair": None, "decide": None, "endpoints_key": None,
           "gpu_echo_q0": None, "gpu_echo_q1": None}
    wl_ = 8 if fault == 13 else wl
    st, pid, F0, t0 = ex.force(q0, N, pvfault, g0fault, wl_, block, grid)
    rec["gpu_echo_q0"] = _echo(ex, N)
    if fault == 13 and F0 is None:                            # a refusal reported as a completed force
        st, F0 = "OK", [[ZERO] * 3 for _ in range(N)]
    if st != "OK":
        rec.update(status=st, stop_stage="F0", stop_pair=pid)
        return rec
    if fault == 1:
        F0 = [list(r) for r in F0]
        F0[0][0] = ZERO
    rec["F0"] = enc(F0)
    if fault == 2:
        ph = [list(r) for r in p0]
    else:
        ph = kick(p0, F0, p)
        if fault == 3:
            ph = kick(ph, F0, p)
    rec["p_half"] = enc(ph)
    q1 = drift(q0, p0 if fault == 5 else ph, p, c, fault)
    rec["q1"] = enc(q1)
    st, pid, F1, t1 = ex.force(q0 if fault == 6 else q1, N, pvfault, g0fault, wl_, block, grid)
    rec["gpu_echo_q1"] = _echo(ex, N)
    if fault == 13 and F1 is None:
        st, F1 = "OK", [[ZERO] * 3 for _ in range(N)]
    if st != "OK":
        rec.update(status=st, stop_stage="F1", stop_pair=pid)
        if fault != 11:
            return rec
        F1 = [[ZERO] * 3 for _ in range(N)]                   # continuing after a stop (fault 11)
    if fault == 8:
        F1 = [list(r) for r in F1]
        F1[0], F1[1] = F1[1], F1[0]
    rec["F1"] = enc(F1)
    p1 = ph if fault == 7 else kick(ph, F1, p)
    rec["p1"] = enc(p1)
    if rec["status"] is None:
        rec["status"] = "OK"
    iv.prec = p
    qv = [iv.make_mpf(x) for r in q1 for x in r]
    pv = [iv.make_mpf(x) for r in p1 for x in r]
    rec["endpoints_key"] = K.endpoints_key(qv + pv)
    try:
        cells = K.decide(qv, pv)
        rec["decide"] = "UNDECIDED_AT_PRECISION" if cells is None else cells
    except K.OutOfRange:
        rec["decide"] = "OUT_OF_RANGE"
    return rec


def _echo(ex, N):
    from experiments.gpu_force_feasibility_v1 import gpu_host as GH
    buf = ex.pv.echo_positions()
    w = list(buf)
    return [[encode_iv((GH._mp_from(w[(3 * a + k) * 22:(3 * a + k) * 22 + 11]),
                        GH._mp_from(w[(3 * a + k) * 22 + 11:(3 * a + k) * 22 + 22]))) for k in range(3)] for a in range(N)]


def gpu_steady_step(ex, q, pm, F, p, c):
    """One steady step from (q, p, F_s): kick, drift, ONE GPU force, kick - with the breakdown."""
    N = len(q)
    t0 = time.perf_counter()
    ph = kick(pm, F, p)
    t1 = time.perf_counter()
    q1 = drift(q, ph, p, c)
    t2 = time.perf_counter()
    st, _, F1, tm = ex.force(q1, N)
    t3 = time.perf_counter()
    p1 = kick(ph, F1, p)
    t4 = time.perf_counter()
    return {"kick1_ms": (t1 - t0) * 1000, "drift_ms": (t2 - t1) * 1000, "encode_ms": tm["encode_ms"],
            "h2d_ms": tm["h2d_ms"], "k_pair_G_J_ms": tm["k_dr2_ms"] + tm["k_G_ms"] + tm["k_J_ms"],
            "k_reduce_ms": tm["k_reduce_ms"], "d2h_ms": tm["d2h_atoms_ms"], "decode_ms": tm["decode_ms"],
            "force_total_ms": (t3 - t2) * 1000, "kick2_ms": (t4 - t3) * 1000, "total_ms": (t4 - t0) * 1000,
            "status": st}, (q1, p1, F1)


def w6_steady_step(w6, q, pm, F, p, c):
    t0 = time.perf_counter()
    ph = kick(pm, F, p)
    t1 = time.perf_counter()
    q1 = drift(q, ph, p, c)
    t2 = time.perf_counter()
    ms, F1 = w6.forces(q1)
    t3 = time.perf_counter()
    p1 = kick(ph, F1, p)
    t4 = time.perf_counter()
    return {"kick1_ms": (t1 - t0) * 1000, "drift_ms": (t2 - t1) * 1000, "w6_forces_ms": ms,
            "force_total_ms": (t3 - t2) * 1000, "kick2_ms": (t4 - t3) * 1000, "total_ms": (t4 - t0) * 1000}, \
        (q1, p1, F1)
