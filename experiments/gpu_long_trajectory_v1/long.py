"""GPU_LONG_TRAJECTORY_V1 runner and GPU P2 service (GPU side; the checker never imports it).

LongExecutor = GPU_ONE_STEP_V1 GpuForceExecutor semantics on the support layer's ExtPV, with counters (model uploads,
allocations, force evaluations) and the device precision echo of every force (atom record word 2).
long_pass runs one fixed-p pass (T = 1000) with force reuse, per-step digests (GPU_SHORT_TRAJECTORY_V1 traj digest
code), checkpoint endpoints and the pass record by the unchanged multiatom_parallel_v1.run._readout.
run_service is experience_start_p_v2.service.run_request's loop: first p = start p, every later p from the unchanged
precision_pilot_a1.policies.next_p('P2', ...); every pass from the original (q0, p0); a p outside the GPU support set
runs on the CPU E2 serial path (stream.run, unchanged) at exactly that p. Faults (tests only) follow protocol.json.
"""

from __future__ import annotations

import time

from experiments.gpu_force_feasibility_v1 import gpu_host as GH
from experiments.gpu_long_trajectory_v1 import support as SUP
from experiments.gpu_one_step_v1 import one_step as OS
from experiments.gpu_pair_vector_v1 import pv_host as PH
from experiments.gpu_short_trajectory_v1 import traj as TR

T = 1000
CHECKS = (0, 1, 2, 5, 10, 20, 50, 100, 200, 250, 500, 750, 900, 950, 990, 999, 1000)
FS = 500
ZERO = OS.ZERO
MAX_PASSES = 24
STOP_OUTCOMES = {"DOMAIN_VIOLATED_PROVEN": "STOP_DOMAIN_VIOLATED_PROVEN", "OUT_OF_RANGE": "STOP_OUT_OF_RANGE"}


class LongExecutor(OS.GpuForceExecutor):
    def __init__(self, lib, block=32, grid=0):                  # noqa: super().__init__ would build a plain PV
        t0 = time.perf_counter()
        self.pv = SUP.ExtPV(lib)
        self.init = {"executor_create_ms": (time.perf_counter() - t0) * 1000, "context_ms": self.pv.setup["context_ms"]}
        self.block, self.grid, self.p = block, grid, None
        self.uploads = self.allocs = self.evals = 0
        self.echo = set()
        self.last_prepare = {}

    def prepare(self, p, N, upload_p=None):
        up = upload_p or p
        t0 = time.perf_counter()
        re_up = self.pv.p != up
        if re_up:
            self.uploads += 1
        if self.pv.N != N:
            self.allocs += 1
        mem = super().prepare(p, N, upload_p)
        self.last_prepare = {"prepare_ms": (time.perf_counter() - t0) * 1000, "model_reupload": re_up,
                             "model_trace_ms": self.pv.setup.get("model_trace_ms") if re_up else 0.0,
                             "model_upload_ms": self.pv.setup.get("model_upload_ms") if re_up else 0.0}
        return mem

    def force(self, q, N, fault=0, g0fault=0, wl=16, block=None, grid=None):
        """GpuForceExecutor.force (same calls, same slow path) + the device precision echo of every atom record."""
        self.evals += 1
        block = block or self.block
        grid = self.grid if grid is None else grid
        t0 = time.perf_counter()
        try:
            pos = PH.encode_positions(q)
        except GH.Refused as e:
            return str(e).split(":")[0], None, None, {}
        t1 = time.perf_counter()
        _, _, atoms, tm = self.pv.run_state(pos, N, 4, block, grid, fault, g0fault, wl)
        t2 = time.perf_counter()
        dec = PH.decode_atoms(atoms, N)
        t3 = time.perf_counter()
        self.echo.update(x[2] for x in dec)
        tm.update(encode_ms=(t1 - t0) * 1000, device_call_ms=(t2 - t1) * 1000, decode_ms=(t3 - t2) * 1000,
                  force_total_ms=(t3 - t0) * 1000)
        if all(x[3] == "PROVEN" for x in dec):
            return "OK", None, [[dec[3 * a + k][4] for k in range(3)] for a in range(N)], tm
        P = N * (N - 1) // 2
        _, comp, _, _ = self.pv.run_state(pos, N, 2, block, grid, fault, g0fault, wl)
        for st, pid, _ in PH.decode_compact(comp, P):
            if st != "PROVEN":
                kind = {"VIOLATED": "DOMAIN_STOP_VIOLATED", "UNPROVEN": "DOMAIN_STOP_UNPROVEN"}.get(st, st)
                return kind, pid, None, tm
        return "REFUSED_DEVICE_PRECISION", None, None, tm


def readout(N, p, completed, stop_kind, stop_state, q, pm):
    """The pass record exactly as multiatom_parallel_v1.run._readout from stream.run's fields."""
    import exact_expression_gate_v1.common as K
    from mpmath import iv

    from experiments.multiatom_parallel_v1.run import _readout
    r = {"completed_steps": completed, "stop": stop_kind, "stop_step": stop_state, "read": None}
    if stop_kind is None:
        iv.prec = p
        qv = [iv.make_mpf(x) for row in q for x in row]
        pv = [iv.make_mpf(x) for row in pm for x in row]
        try:
            r["read"] = (K.decide(qv, pv), K.endpoints_key(qv + pv))
        except K.OutOfRange:
            r.update(stop="OUT_OF_RANGE", stop_step=completed)
    return _readout(r, N)


def long_pass(ex, q0, p0, p, fault=0, block=None, grid=None, upload_p=None, ref_steps=None, fs=FS, record_p=None):
    """One fixed-p pass of T steps from (q0, p0)."""
    N = len(q0)
    block = block or ex.block
    t_start = time.perf_counter()
    rec = {"N": N, "requested_p": record_p or p, "backend": "GPU", "echo_q0": TR.enc(q0), "echo_p0": TR.enc(p0),
           "steps": [], "full": {}, "pass_record": None, "status": None, "stop_state": None, "stop_pair": None,
           "completed_steps": 0, "force_evals": 0, "uploads_in_pass": 0, "allocs_in_pass": 0, "dump": None,
           "device_p": None, "device_p_echo": [], "block": block, "grid": grid or 0, "fault": fault, "work_limbs": 16}
    try:
        ex.prepare(p, N, upload_p)
    except GH.Refused as e:
        rec["status"] = str(e).split(":")[0]
        return rec
    rec["prepare"] = dict(ex.last_prepare)
    rec["device_p"] = record_p or ex.pv.p                       # fault 14 / 15 lie through record_p
    c = OS.lifted(p)
    u0, a0, e0 = ex.uploads, ex.allocs, ex.evals
    ex.echo = set()
    zeros = [[ZERO] * 3 for _ in range(N)]

    def evaluate(q):
        st, pid, F, _ = ex.force(q, N, 0, 0, 16, block, grid)
        return st, pid, F

    def dump_if_first(step, vecs):
        if rec["dump"] is None and ref_steps is not None and step["s"] < len(ref_steps) and \
                any(step.get(k) != ref_steps[step["s"]].get(k) for k in step if k != "s"):
            rec["dump"] = {"s": step["s"], **{k: TR.enc(v) for k, v in vecs.items()}}

    def finish(q, pm, stop_kind, stop_state):
        rec["pass_record"] = readout(N, p, rec["completed_steps"], stop_kind, stop_state, q, pm)
        rec["pass_record"]["effective_p"] = rec["device_p"]
        rec.update(force_evals=ex.evals - e0, uploads_in_pass=ex.uploads - u0, allocs_in_pass=ex.allocs - a0,
                   device_p_echo=sorted(ex.echo), loop_ms=(time.perf_counter() - t_start) * 1000)
        return rec

    t_loop = time.perf_counter()
    st, pid, F = evaluate(q0)
    if st != "OK":
        rec.update(status=st, stop_state=0, stop_pair=pid)
        return finish(q0, p0, st.replace("DOMAIN_STOP_", ""), 0)
    q, pm, F_prev = q0, p0, None
    rec["full"]["0"] = {"q": TR.enc(q), "p_mom": TR.enc(pm), "F": TR.enc(F)}
    labels = [s for s in range(T) if not (fault == 3 and s == fs)]
    stopped = None
    for s in labels:
        F_use = F_prev if (fault == 1 and s == fs) else F
        ph = OS.kick(pm, F_use, p)
        q1 = OS.drift(q, pm if (fault == 5 and s == fs) else ph, p, c)
        if fault == 7 and s == fs:
            q1 = TR._bump(q1, 0)
        if fault == 2 and s == fs:
            st, pid, F1 = "OK", None, F_use
        else:
            st, pid, F1 = evaluate(q if (fault == 6 and s == fs) else q1)
        step = {"s": s, "F_s": TR.dg("F", F_use), "p_half": TR.dg("P", ph), "q1": TR.dg("Q", q1)}
        if st != "OK":
            if fault == 10:
                stopped = stopped or (st, s + 1, pid)
                F1 = zeros
            else:
                rec["steps"].append(step)
                dump_if_first(step, {"F_s": F_use, "p_half": ph, "q1": q1})
                rec.update(status=st, stop_state=s + 1, stop_pair=pid + (1 if fault == 11 else 0), completed_steps=s)
                return finish(q1, ph, st.replace("DOMAIN_STOP_", ""), s + 1)
        if fault == 9 and s == fs:
            F1 = TR._bump(F1, 0)
        if fault == 18 and block != 32 and s >= fs:
            F1 = TR._bump(F1, N - 1)
        p1 = ph if (fault == 4 and s == fs) else OS.kick(ph, F1, p)
        if fault == 8 and s == fs:
            p1 = TR._bump(p1, 0)
        step.update(F1=TR.dg("F", F1), p1=TR.dg("P", p1), state=TR.state_dg(q1, p1), force=TR.dg("F", F1))
        rec["steps"].append(step)
        dump_if_first(step, {"F_s": F_use, "p_half": ph, "q1": q1, "F1": F1, "p1": p1})
        if s + 1 in CHECKS:
            rec["full"][str(s + 1)] = {"q": TR.enc(q1), "p_mom": TR.enc(p1), "F": TR.enc(F1)}
        F_prev = F_use
        q, pm, F = q1, p1, F1
        rec["completed_steps"] = s + 1
    rec["trajectory_ms"] = (time.perf_counter() - t_loop) * 1000
    if stopped:
        rec.update(status=stopped[0], stop_state=stopped[1], stop_pair=stopped[2])
    else:
        rec["status"] = "OK"
    return finish(q, pm, None, None)


def cpu_pass(N, p, cpu=0):
    """CPU E2 serial fallback at exactly p: the unchanged multiatom_parallel_v1.run.run_serial (the V2 reference mode;
    it pins this process to `cpu`, restored afterwards)."""
    import psutil

    from experiments.multiatom_parallel_v1.run import run_serial
    me = psutil.Process()
    aff = me.cpu_affinity()
    t0 = time.perf_counter()
    try:
        rec = run_serial("rw:R1+R2", N, T, p, cpu)
    finally:
        me.cpu_affinity(aff)
    q0, p0 = initial(N, p)
    return {"N": N, "requested_p": p, "backend": "CPU_E2_FALLBACK", "effective_p": rec["effective_p"],
            "pass_record": rec, "echo_q0": TR.enc(q0), "echo_p0": TR.enc(p0), "fault": 0, "work_limbs": 16,
            "loop_ms": (time.perf_counter() - t0) * 1000}


def initial(N, p):
    from mpmath import iv

    import exact_expression_gate_v0.lang_iv as LI
    from experiments.multiatom_parallel_v1 import scenarios as SC
    iv.prec = p
    q0, p0 = SC.initial(N)
    return [[LI.c(x)._mpi_ for x in r] for r in q0], [[LI.c(x)._mpi_ for x in r] for r in p0]


def _next_supported(p, support):
    return min(x for x in support if x > p)


def run_service(ex, N, policy, start_p, support, fault=0, block=None, ref_steps=None, demonstration=False,
                max_passes=MAX_PASSES):
    """GPU P2 service: first p = start_p, later p = P2 (unchanged); every pass from the original state."""
    from experiments.precision_pilot_a1 import policies as POL
    t0 = time.perf_counter()
    out = {"N": N, "T": T, "policy": policy, "start_p": start_p, "passes": [], "status": None, "final_p": None,
           "support_used": sorted(support), "demonstration": demonstration, "fault": fault}
    history, last_state = [], None
    while True:
        p = start_p if not history else POL.next_p("P2", None, history, T)
        if p not in (None, "CAP") and fault == 13 and history and history[-1]["outcome"] == "UNDECIDED_AT_PRECISION":
            p = _next_supported(p, support)                           # the P2 p altered (161 -> 163)
        if p is None:
            last = history[-1]["outcome"]
            out["status"] = "DECIDED" if last == "DECIDED" else STOP_OUTCOMES.get(last, f"FINAL_{last}")
            out["final_p"] = history[-1]["requested_p"]
            break
        if p == "CAP":
            out["status"] = "REFUSED_AT_CAP"
            break
        if len(history) >= max_passes:
            out["status"] = "REFUSED_PASS_LIMIT"
            break
        q0, p0 = initial(N, p)
        if fault == 12 and last_state is not None:
            q0, p0 = last_state                                       # retry from the failed pass's last state
        tp = time.perf_counter()
        if p in support:
            up = None
            if fault == 15 and len(history) == 1:
                up = history[-1]["requested_p"]                      # the model stays at the old p
            rec = long_pass(ex, q0, p0, p, block=block, upload_p=up, ref_steps=(ref_steps or {}).get(p),
                            record_p=p if up else None)
        elif fault == 14:
            rec = long_pass(ex, q0, p0, _next_supported(p, support), block=block, record_p=p,
                            ref_steps=(ref_steps or {}).get(p))
        else:
            rec = cpu_pass(N, p)
        rec["pass_wall_ms"] = (time.perf_counter() - tp) * 1000
        rec.update(index=len(history), p_source="decision" if not history else "P2", start="ORIGINAL_Q0_P0",
                   support_used=sorted(support), kind="SERVICE_PASS")
        rec["requested_p"] = p
        out["passes"].append(rec)
        pr = rec["pass_record"]
        history.append({"requested_p": p, "outcome": pr["outcome"], "completed_steps": pr["completed_steps"],
                        "endpoints_scaled": pr.get("endpoints_scaled")})
        last_state = rec.get("_last_state") or _last_state(rec)
    if fault == 16 and len(out["passes"]) > 1:
        out["passes"] = out["passes"][1:]                             # the failed pass deleted from the record
    if fault == 17 and out["passes"]:
        f = out["passes"][-1].get("full", {}).get("1000")
        if f:
            row = f["q"][0]
            lo, hi = row[0]
            s, h, e, bc = hi
            row[0] = [lo, [s, format(int(h, 16) + 2, "x"), e, bc]]
    backends = {x["backend"] for x in out["passes"]}
    out["execution_label"] = "GPU_FULL_RETRY" if backends == {"GPU"} else "GPU_WITH_CPU_PRECISION_FALLBACK"
    out["service_wall_ms"] = (time.perf_counter() - t0) * 1000
    out["p_sequence"] = [x["requested_p"] for x in out["passes"]]
    return out


def _last_state(rec):
    """The last checkpoint state of a pass (fault 12 only needs some non-original state)."""
    full = rec.get("full") or {}
    if not full:
        return None
    k = max(full, key=int)
    return TR.dec(full[k]["q"]), TR.dec(full[k]["p_mom"])
