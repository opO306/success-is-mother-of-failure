"""GPU_SHORT_TRAJECTORY_V1 runner (GPU side; the checker never imports it).

hybrid_trajectory runs T KDK steps with GPU forces (GPU_ONE_STEP_V1 GpuForceExecutor, unchanged, counted by a thin
subclass) and the CPU kicks / drift of one_step (unchanged). F_{s+1} of step s is reused as F_s of step s + 1: T + 1
force evaluations. Per step it records the protocol digests of F_s, p_half, q1, F1, p1, state and force (the runner's
own implementation of the digest rule), the full state at the checkpoint indices, and, at the first step whose
digests differ from the bundle's CPU digests, a dump of all five vectors. Faults (tests only) follow protocol.json.

Performance: gpu_warm_trajectory / w6_warm_trajectory (no digests inside the clock) and the cold entry point

    python -m experiments.gpu_short_trajectory_v1.traj cold gpu|w6 LIB N P T STATE.json
"""

from __future__ import annotations

import hashlib
import json
import sys
import time

from experiments.gpu_force_feasibility_v1 import gpu_host as GH
from experiments.gpu_force_feasibility_v1.dyadic import decode_iv, encode_iv
from experiments.gpu_one_step_v1 import one_step as OS

CHECKS = {10: (0, 1, 2, 5, 10), 100: (0, 1, 2, 5, 10, 20, 50, 100)}
PREC_SWITCH = {109: 128, 163: 192}
ZERO = OS.ZERO


class TrajExecutor(OS.GpuForceExecutor):
    """GpuForceExecutor + counters (model uploads, allocations, force evaluations) and refusals as statuses."""

    def __init__(self, lib, block=32, grid=0):
        super().__init__(lib, block, grid)
        self.uploads = self.allocs = self.evals = 0

    def prepare(self, p, N, upload_p=None):
        if self.pv.p != (upload_p or p):
            self.uploads += 1
        if self.pv.N != N:
            self.allocs += 1
        return super().prepare(p, N, upload_p)

    def force(self, q, N, fault=0, g0fault=0, wl=16, block=None, grid=None):
        self.evals += 1
        try:
            return super().force(q, N, fault, g0fault, wl, block, grid)
        except GH.Refused as e:
            return str(e).split(":")[0], None, None, {}


# ---------------------------------------------------------------------------
# digests (protocol 'digests'; the runner's own implementation)
# ---------------------------------------------------------------------------
def _t(m):
    s, man, e, bc = m
    return "0.0.0.0" if not man else f"{s}.{man:x}.{e}.{bc}"


def _items(X, order):
    if order == "atom":
        return (end for r in X for x in r for end in x)
    return (end for k in range(3) for r in X for end in r[k])          # fault 14: component-major


def _text(label, X, order):
    return f"{label}:{len(X)}:" + ",".join(_t(e) for e in _items(X, order))


def dg(label, X, order="atom"):
    return hashlib.sha256(_text(label, X, order).encode()).hexdigest()


def state_dg(q, pm, order="atom"):
    return hashlib.sha256((_text("Q", q, order) + "|" + _text("P", pm, order)).encode()).hexdigest()


def enc(rows):
    return None if rows is None else [[encode_iv(x) for x in r] for r in rows]


def dec(rows):
    return [[decode_iv(e) for e in r] for r in rows]


def _bump(X, a, k=0):
    """Atom a, component k: upper endpoint + one unit in the last place (faults 10, 11, 12, 15)."""
    X = [list(r) for r in X]
    lo, hi = X[a][k]
    X[a][k] = (lo, OS._ulp(hi))
    return X


def _read(q, pm, p):
    import exact_expression_gate_v1.common as K
    from mpmath import iv
    iv.prec = p
    qv = [iv.make_mpf(x) for r in q for x in r]
    pv = [iv.make_mpf(x) for r in pm for x in r]
    key = K.endpoints_key(qv + pv)
    try:
        cells = K.decide(qv, pv)
        d = "UNDECIDED_AT_PRECISION" if cells is None else cells
    except K.OutOfRange:
        d = "OUT_OF_RANGE"
    return {"decide": d, "endpoints_key": key}


# ---------------------------------------------------------------------------
# the hybrid trajectory
# ---------------------------------------------------------------------------
def hybrid_trajectory(ex, q0, p0, p, T, fault=0, pvfault=0, g0fault=0, wl=16, block=None, grid=None, upload_p=None,
                      ref_steps=None, fs=3):
    N = len(q0)
    block = block or ex.block
    order = "component" if fault == 14 else "atom"
    rec = {"N": N, "p": p, "T": T, "echo_q0": enc(q0), "echo_p0": enc(p0), "steps": [], "full": {}, "read": None,
           "status": None, "stop_state": None, "stop_pair": None, "completed_steps": 0, "force_evals": 0,
           "uploads_in_traj": 0, "allocs_in_traj": 0, "dump": None}
    try:
        ex.prepare(p, N, upload_p)
    except GH.Refused as e:
        rec["status"] = str(e).split(":")[0]
        return rec
    c = OS.lifted(p)
    u0, a0, e0 = ex.uploads, ex.allocs, ex.evals
    checks = CHECKS[10] if T <= 10 else CHECKS[100]
    zeros = [[ZERO] * 3 for _ in range(N)]

    def evaluate(q, state):
        wl_ = 8 if (fault == 16 and state == fs + 1) else wl
        st, pid, F, _ = ex.force(q, N, pvfault, g0fault, wl_, block, grid)
        if fault == 16 and F is None and st.startswith("REFUSED"):
            st, pid, F = "OK", None, zeros                                 # a refusal reported as a normal force
        return st, pid, F

    def finish():
        rec.update(force_evals=ex.evals - e0, uploads_in_traj=ex.uploads - u0, allocs_in_traj=ex.allocs - a0)
        return rec

    def dump_if_first(step, vecs):
        if rec["dump"] is None and ref_steps is not None and step["s"] < len(ref_steps) and \
                any(step.get(k) != ref_steps[step["s"]].get(k) for k in step if k != "s"):
            rec["dump"] = {"s": step["s"], **{k: enc(v) for k, v in vecs.items()}}

    st, pid, F = evaluate(q0, 0)
    if st != "OK":
        rec.update(status=st, stop_state=0, stop_pair=pid)
        return finish()
    q, pm, F_prev = q0, p0, None
    rec["full"]["0"] = {"q": enc(q), "p_mom": enc(pm), "F": enc(F)}
    labels = [s for s in range(T) if not (fault == 4 and s == 5)]
    stopped = None
    for s in labels:
        F_use = F_prev if (fault == 1 and s == fs) else F
        if fault == 2 and s > 0:
            _, _, F_use = evaluate(q, s)                                   # F_s recomputed instead of reused
        ph = OS.kick(pm, F_use, p)
        if fault == 6 and s == fs:
            ph = OS.kick(ph, F_use, p)
        q1 = OS.drift(q, pm if (fault == 7 and s == fs) else ph, p, c)
        if fault == 10 and s == fs:
            q1 = _bump(q1, 0)
        if fault == 9 and s == 5:
            ex.prepare(p, N, PREC_SWITCH[p])                               # the GPU program at another precision
        if fault == 3 and s == fs:
            st, pid, F1 = "OK", None, F_use                                # the force computation is missing
        else:
            st, pid, F1 = evaluate(q if (fault == 8 and s == fs) else q1, s + 1)
        step = {"s": s, "F_s": dg("F", F_use, order), "p_half": dg("P", ph, order), "q1": dg("Q", q1, order)}
        if st != "OK":
            if fault == 13:                                                # continuing after a domain stop
                stopped = stopped or (st, s + 1, pid)
                F1 = zeros
            else:
                rec["steps"].append(step)
                dump_if_first(step, {"F_s": F_use, "p_half": ph, "q1": q1})
                rec.update(status=st, stop_state=s + 1, stop_pair=pid, completed_steps=s)
                return finish()
        if fault == 12 and s == fs:
            F1 = _bump(F1, 0)
        if fault == 15 and block != 32 and s >= 2:
            F1 = _bump(F1, N - 1)
        p1 = ph if (fault == 5 and s == fs) else OS.kick(ph, F1, p)
        if fault == 11 and s == fs:
            p1 = _bump(p1, 0)
        step.update(F1=dg("F", F1, order), p1=dg("P", p1, order), state=state_dg(q1, p1, order), force=dg("F", F1, order))
        rec["steps"].append(step)
        dump_if_first(step, {"F_s": F_use, "p_half": ph, "q1": q1, "F1": F1, "p1": p1})
        if s + 1 in checks:
            rec["full"][str(s + 1)] = {"q": enc(q1), "p_mom": enc(p1), "F": enc(F1)}
        F_prev = F_use
        q, pm, F = q1, p1, F1
        rec["completed_steps"] = s + 1
    if stopped:
        rec.update(status=stopped[0], stop_state=stopped[1], stop_pair=stopped[2])
    else:
        rec["status"] = "OK"
    rec["read"] = _read(q, pm, p)
    return finish()


# ---------------------------------------------------------------------------
# performance
# ---------------------------------------------------------------------------
GPU_KEYS = ("encode_ms", "h2d_ms", "k_pair_G_J_ms", "k_reduce_ms", "d2h_ms", "decode_ms")


def _acc_gpu(acc, tm):
    acc["encode_ms"] += tm["encode_ms"]
    acc["h2d_ms"] += tm["h2d_ms"]
    acc["k_pair_G_J_ms"] += tm["k_dr2_ms"] + tm["k_G_ms"] + tm["k_J_ms"]
    acc["k_reduce_ms"] += tm["k_reduce_ms"]
    acc["d2h_ms"] += tm["d2h_atoms_ms"]
    acc["decode_ms"] += tm["decode_ms"]
    acc["force_total_ms"] += tm["force_total_ms"]


def _kdk_loop(force, q, pm, p, T, c, acc, on_force):
    t = time.perf_counter
    t0 = t()
    st, F, tm = force(q)
    on_force(acc, tm)
    acc["initial_F_ms"] = (t() - t0) * 1000
    for _ in range(T):
        a = t()
        ph = OS.kick(pm, F, p)
        b = t()
        q = OS.drift(q, ph, p, c)
        d = t()
        st, F, tm = force(q)
        e = t()
        if st != "OK":
            raise RuntimeError(f"performance trajectory stopped: {st}")
        pm = OS.kick(ph, F, p)
        f = t()
        acc["kicks_ms"] += (b - a) + (f - e)
        acc["drift_ms"] += d - b
        on_force(acc, tm)
    for k in ("kicks_ms", "drift_ms"):
        acc[k] *= 1000
    return q, pm, F


def gpu_warm_trajectory(ex, q0, p0, p, T, c):
    from collections import defaultdict
    acc = defaultdict(float)
    N = len(q0)

    def force(q):
        st, _, F, tm = ex.force(q, N)
        return st, F, tm
    t0 = time.perf_counter()
    out = _kdk_loop(force, q0, p0, p, T, c, acc, _acc_gpu)
    acc["total_ms"] = (time.perf_counter() - t0) * 1000
    return dict(acc), out


def w6_warm_trajectory(w6, q0, p0, p, T, c):
    from collections import defaultdict
    acc = defaultdict(float)

    def force(q):
        ms, F = w6.forces(q)
        return "OK", F, {"w6_forces_ms": ms}

    def on(acc, tm):
        acc["w6_forces_ms"] += tm["w6_forces_ms"]
    t0 = time.perf_counter()
    out = _kdk_loop(force, q0, p0, p, T, c, acc, on)
    acc["total_ms"] = (time.perf_counter() - t0) * 1000
    return dict(acc), out


def final_digests(out):
    q, pm, F = out
    return {"state": state_dg(q, pm), "force": dg("F", F)}


def cold_main(argv):
    """A fresh process: the clock starts before the executor (library load + CUDA context) / the worker spawn."""
    t_proc = time.perf_counter()
    path, lib, N, p, T, state_file = argv[0], argv[1], int(argv[2]), int(argv[3]), int(argv[4]), argv[5]
    st = json.loads(open(state_file, encoding="utf-8").read())
    q0, p0 = dec(st["q0"]), dec(st["p0"])
    c = OS.lifted(p)
    if path == "w6":
        from experiments.gpu_pair_vector_v1.campaign import W6E2
    t_ready = time.perf_counter()
    t0 = time.perf_counter()
    if path == "gpu":
        ex = TrajExecutor(lib, block=32)
        t1 = time.perf_counter()
        ex.prepare(p, N)
        t2 = time.perf_counter()
        acc, out = gpu_warm_trajectory(ex, q0, p0, p, T, c)
        setup = {"executor_create_ms": (t1 - t0) * 1000, "context_ms": ex.init["context_ms"],
                 "upload_and_alloc_ms": (t2 - t1) * 1000}
    else:
        w6 = W6E2(N, p)
        t1 = time.perf_counter()
        acc, out = w6_warm_trajectory(w6, q0, p0, p, T, c)
        setup = {"spawn_ms": (t1 - t0) * 1000}
    total = (time.perf_counter() - t0) * 1000
    if path == "w6":
        w6.close()
    print("COLD_RESULT " + json.dumps({"path": path, "cold_total_ms": total, "setup": setup, "trajectory": acc,
                                       "imports_and_state_ms": (t_ready - t_proc) * 1000, **final_digests(out)}),
          flush=True)


if __name__ == "__main__":
    if sys.argv[1] == "cold":
        cold_main(sys.argv[2:])
