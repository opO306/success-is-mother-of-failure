"""ADAPTIVE_EXECUTION_V1 adapters (protocol 'modules', 'gpu_status_classes', 'service.gpu_serialization').

validate_plan re-checks every plan against the environment and the correctness profile with its own code before
execution: a plan the selector got wrong is refused here, not executed.

CPU: one fresh process per pass running the unchanged experiments/w5_placement_v1/run.py (ExecutionPlan ->
multiatom_parallel_v1.run.run_serial / e2_pair_parallel_v1.run.run_parallel).
GPU: one dedicated worker process owns one gpu_long_trajectory_v1.long.LongExecutor (subclassed only to add up the
device timings) and serves one request at a time; the support-set widening of support.ExtPV.upload happens only inside
it. T = 1000: long.long_pass. T = 100: gpu_short_trajectory_v1.traj.hybrid_trajectory with the same executor and the
pass record built by long.readout from the T = 100 checkpoint state. No frozen file or module global is changed.
"""

from __future__ import annotations

import json
import multiprocessing as mp
import os
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

from experiments.adaptive_execution_v1.profiles import CORRECTNESS

ROOT = Path(__file__).resolve().parents[2]
SHIM = ROOT / "experiments/experience_start_p_v2/linux_shim"
OUTCOME_KEYS = ("outcome", "completed_steps", "stop", "stop_step", "cells", "endpoints_key", "endpoints_scaled")


# ---------------------------------------------------------------------------
# plan re-check (own code; does not call the selector)
# ---------------------------------------------------------------------------
def validate_plan(plan, N, T, env, gate100_passed):
    """List of violations (empty = executable)."""
    v = []
    if plan.env_id != env["env_id"]:
        v.append("ENV_ID_MISMATCH")
    if plan.evaluator != CORRECTNESS["CPU_E2"]["evaluator"]:
        v.append("EVALUATOR")
    if not (isinstance(plan.p, int) and 64 <= plan.p <= 1024):
        v.append("P_RANGE")
    if plan.backend == "GPU_HYBRID":
        g = CORRECTNESS["GPU_V1"]
        gpu = env.get("gpu")
        if not gpu:
            v.append("NO_GPU")
        elif gpu.get("arch") not in g["verified_arch"]:
            v.append("GPU_ARCH")
        if (env["mpmath_version"], env["mpmath_backend"]) not in g["verified_mpmath"]:
            v.append("GPU_MPMATH")
        if dict(env["contracts"]["gpu_sources"]) != dict(g["gpu_sources"]):
            v.append("GPU_SOURCES")
        if plan.p not in g["support_p"]:
            v.append("GPU_P")
        if N not in g["domain_N"].get(T, ()):
            v.append("GPU_DOMAIN")
        if T == 100 and not gate100_passed:
            v.append("GPU_T100_NOT_CONNECTED")
        if plan.gpu_block != g["block"]:
            v.append("GPU_BLOCK")
        return v
    allowed = set(env["allowed_cpus"])
    cpus = [plan.main_cpu, *plan.worker_cpus]
    if any(c not in allowed for c in cpus):
        v.append("CPU_NOT_ALLOWED")
    core = {c: env["core_of_cpu"].get(str(c)) for c in cpus}
    wc = [core[c] for c in plan.worker_cpus]
    if None in core.values():
        v.append("CORE_UNKNOWN")
    if len(set(wc)) != len(wc):
        v.append("WORKERS_SHARE_A_CORE")
    if plan.backend == "CPU_SERIAL":
        if plan.worker_count or plan.worker_cpus:
            v.append("SERIAL_WITH_WORKERS")
        used = 1
    elif plan.backend == "CPU_PARALLEL":
        if plan.worker_count != len(plan.worker_cpus) or plan.worker_count not in (3, 4, 6):
            v.append("WORKER_COUNT")
        if plan.worker_count == 6:
            if plan.main_cpu != plan.worker_cpus[-1]:
                v.append("W6_MAIN_NOT_ON_WORKER6")
        elif core[plan.main_cpu] in wc:
            v.append("MAIN_SHARES_A_WORKER_CORE")
        used = len({core[c] for c in cpus})
    else:
        v.append(f"BACKEND:{plan.backend}")
        used = 0
    q = env.get("cpu_quota")
    if q is not None and used > int(q):
        v.append("OVER_QUOTA")
    return v


# ---------------------------------------------------------------------------
# CPU passes
# ---------------------------------------------------------------------------
def _child_env():
    e = dict(os.environ)
    paths = [str(ROOT)]
    if sys.platform.startswith("linux"):
        e["ESP2_LINUX_CLOCK"] = "1"
        paths.insert(0, str(SHIM))
    old = e.get("PYTHONPATH")
    e["PYTHONPATH"] = os.pathsep.join(paths + ([old] if old else []))
    return e


def cpu_pass(plan, N, T, workdir=None, executed_plan=None):
    """One pass in a fresh process. executed_plan (tests only, fault F13) runs another plan than the selected one."""
    ep = (executed_plan or plan).execution_plan()
    with tempfile.TemporaryDirectory(dir=workdir) as td:
        pf, of = Path(td) / "plan.json", Path(td) / "out.json"
        pf.write_text(ep.to_json(), encoding="utf-8")
        t0 = time.perf_counter()
        r = subprocess.run([sys.executable, "-m", "experiments.w5_placement_v1.run", str(pf), str(N), str(T), str(of)],
                           cwd=ROOT, env=_child_env(), capture_output=True, text=True)
        wall = time.perf_counter() - t0
        if r.returncode != 0 or not of.exists():
            return {"backend": plan.backend, "status_class": "CPU_RUNNER_ERROR", "requested_p": plan.p,
                    "error": (r.stderr or "")[-3000:], "wall_s": wall, "cpu_s": None}
        rec = json.loads(of.read_text(encoding="utf-8"))
    cpu = rec["main_cpu_s"] + sum(rec.get("worker_cpu_s") or [])
    runner = {k: rec.get(k) for k in ("plan", "mode", "evaluator", "effective_p", "initial_sha256", "affinity",
                                      "main_affinity", "worker_cpus", "block_sizes", "main_cpu_s", "worker_cpu_s",
                                      "loop_wall_s", "spawn_wall_s", "ready_wall_s", "main_wall_s",
                                      "main_peak_wset_mb", "workers_exited", "force_swap_restored")}
    runner["worker_affinity"] = [h.get("affinity") for h in rec.get("worker_hello") or []]
    out = {"backend": plan.backend, "status_class": "OK", "requested_p": plan.p, "effective_p": rec["effective_p"],
           "initial_sha256": rec["initial_sha256"], "wall_s": wall, "cpu_s": cpu, "gpu": None, "runner": runner}
    out.update({k: rec.get(k) for k in OUTCOME_KEYS})
    out["executed_placement_ok"] = executed_matches(plan, runner)
    return out


def executed_matches(plan, runner):
    """The runner's recorded plan and affinities equal the selected plan."""
    rp = runner.get("plan") or {}
    if (rp.get("backend"), rp.get("worker_count"), rp.get("main_cpu"), list(rp.get("worker_cpus") or []),
            rp.get("precision")) != (plan.backend, plan.worker_count, plan.main_cpu, list(plan.worker_cpus), plan.p):
        return False
    if plan.backend == "CPU_SERIAL":
        return runner.get("affinity") == [plan.main_cpu]
    return runner.get("main_affinity") == [plan.main_cpu] and \
        runner.get("worker_affinity") == [[c] for c in plan.worker_cpus]


# ---------------------------------------------------------------------------
# GPU worker process
# ---------------------------------------------------------------------------
TIMING_KEYS = ("encode_ms", "device_call_ms", "decode_ms", "force_total_ms", "h2d_ms", "k_dr2_ms", "k_G_ms", "k_J_ms",
               "k_reduce_ms", "d2h_atoms_ms")


def _worker_check(N, T, p):
    g = CORRECTNESS["GPU_V1"]
    why = []
    if p not in g["support_p"]:
        why.append("GPU_P")
    if N not in g["domain_N"].get(T, ()):
        why.append("GPU_DOMAIN")
    return why


def _gpu_pass(ex, msg):
    from experiments.gpu_long_trajectory_v1 import long as LG
    N, T, p, block = msg["N"], msg["T"], msg["p"], msg["block"]
    why = _worker_check(N, T, p)
    if why and not msg.get("fault_run_p"):
        return {"status": "REFUSED_BY_WORKER:" + ",".join(why)}
    run_p = msg.get("fault_run_p") or p                    # tests only (F3): another p on the device
    up = msg.get("fault_upload_p")                         # tests only (F4): the model at another p
    q0, p0 = LG.initial(N, run_p)
    if msg.get("fault_start"):                             # tests only (F7): a retry from a non-original state
        from experiments.gpu_short_trajectory_v1 import traj as TR
        q0, p0 = TR.dec(msg["fault_start"]["q"]), TR.dec(msg["fault_start"]["p_mom"])
    ex.acc = dict.fromkeys(TIMING_KEYS, 0.0)
    if T == 1000:
        rec = LG.long_pass(ex, q0, p0, run_p, block=block, upload_p=up, record_p=p if (up or run_p != p) else None)
        pr = rec.get("pass_record")
    else:
        from experiments.gpu_short_trajectory_v1 import traj as TR
        ex.echo = set()
        e0 = ex.evals
        rec = TR.hybrid_trajectory(ex, q0, p0, run_p, T, block=block, upload_p=up)
        rec["device_p"] = p if (up or run_p != p) else ex.pv.p
        rec["device_p_echo"] = sorted(ex.echo)
        rec["force_evals"] = ex.evals - e0
        st = rec.get("status")
        if st == "OK":
            f = rec["full"][str(T)]
            pr = LG.readout(N, run_p, rec["completed_steps"], None, None, TR.dec(f["q"]), TR.dec(f["p_mom"]))
        elif st and st.startswith("DOMAIN_STOP_"):
            pr = LG.readout(N, run_p, rec["completed_steps"], st.replace("DOMAIN_STOP_", ""), rec["stop_state"], None,
                            None)
        else:
            pr = None
        if pr is not None:
            pr["effective_p"] = rec["device_p"]
        rec["pass_record"] = pr
    rec["device_timing_ms"] = dict(ex.acc)
    return rec


def _gpu_worker_main(conn, lib):
    t0 = time.perf_counter()
    c0 = time.process_time()
    try:
        from experiments.gpu_long_trajectory_v1 import long as LG

        class TimedExecutor(LG.LongExecutor):
            def force(self, *a, **k):
                st, pid, F, tm = super().force(*a, **k)
                for key in TIMING_KEYS:
                    if key in tm:
                        self.acc[key] = self.acc.get(key, 0.0) + tm[key]
                return st, pid, F, tm

        ex = TimedExecutor(lib, block=CORRECTNESS["GPU_V1"]["block"])
        ex.acc = {}
        conn.send({"ready": True, "pid": os.getpid(), "startup_ms": (time.perf_counter() - t0) * 1000,
                   "startup_cpu_s": time.process_time() - c0, "init": dict(ex.init)})
    except Exception as e:                                  # noqa: BLE001 - reported, the service falls back
        conn.send({"ready": False, "error": repr(e)})
        return
    while True:
        msg = conn.recv()
        if msg is None:
            break
        c0, w0 = time.process_time(), time.perf_counter()
        try:
            if msg.get("fault_device_error"):
                raise RuntimeError("injected device error (tests only)")
            rec = _gpu_pass(ex, msg)
        except Exception as e:                              # noqa: BLE001
            rec = {"status": "DEVICE_ERROR", "error": repr(e)}
        rec["worker_cpu_s"] = time.process_time() - c0
        rec["worker_wall_s"] = time.perf_counter() - w0
        conn.send(rec)
    try:
        ex.pv.lib.pv_free()
    except Exception:                                       # noqa: BLE001
        pass


class GpuWorker:
    """The one GPU worker of this service host; a lock serializes the requests."""

    def __init__(self, lib, timeout_s=300):
        ctx = mp.get_context("spawn")
        self.conn, child = ctx.Pipe()
        t0 = time.perf_counter()
        self.proc = ctx.Process(target=_gpu_worker_main, args=(child, str(lib)), daemon=True)
        self.proc.start()
        self.hello = {"ready": False, "error": "GPU worker did not start"}
        while time.perf_counter() - t0 < timeout_s:
            if self.conn.poll(0.5):
                self.hello = self.conn.recv()
                break
            if not self.proc.is_alive():
                self.hello = {"ready": False, "error": f"GPU worker exited ({self.proc.exitcode}) before ready"}
                break
        self.hello["spawn_to_ready_s"] = time.perf_counter() - t0
        self.lock = threading.Lock()
        self.log = []                                       # every response, in order (checker cross-check)

    @property
    def ready(self):
        return bool(self.hello.get("ready"))

    def run(self, N, T, p, block, request_id, **faults):
        with self.lock:
            t0 = time.perf_counter()
            try:
                if not self.proc.is_alive():
                    raise EOFError("GPU worker not alive")
                self.conn.send({"N": N, "T": T, "p": p, "block": block, **faults})
                rec = self.conn.recv()
            except (EOFError, OSError, BrokenPipeError) as e:
                rec = {"status": "DEVICE_ERROR", "error": repr(e)}
            wall = time.perf_counter() - t0
        self.log.append({"seq": len(self.log), "request_id": request_id, "N": N, "T": T, "p": p,
                         "status": rec.get("status"), "error": rec.get("error")})
        return rec, wall

    def close(self):
        try:
            self.conn.send(None)
            self.proc.join(timeout=30)
        except (OSError, BrokenPipeError):
            pass


def classify_gpu(rec, p):
    st = rec.get("status") or ""
    if st == "DEVICE_ERROR":
        return "DEVICE_ERROR"
    if st.startswith("REFUSED"):
        return "DEVICE_REFUSAL"
    if rec.get("pass_record") is None:
        return "DEVICE_ERROR"
    if rec.get("device_p") != p or rec.get("device_p_echo") != [p]:
        return "GPU_PRECISION_MISMATCH"
    return "OK"


def gpu_pass(worker, plan, N, T, request_id, keep_detail=True, **faults):
    from experiments.adaptive_execution_v1.experience import initial_state_digest
    rec, wall = worker.run(N, T, plan.p, plan.gpu_block, request_id, **faults)
    cls = classify_gpu(rec, plan.p)
    out = {"backend": "GPU_HYBRID", "status_class": cls, "requested_p": plan.p, "wall_s": wall,
           "cpu_s": rec.get("worker_cpu_s"), "initial_sha256": initial_state_digest(N), "runner": None,
           "gpu": {k: rec.get(k) for k in ("status", "error", "device_p", "device_p_echo", "force_evals",
                                            "uploads_in_pass", "uploads_in_traj", "allocs_in_pass", "allocs_in_traj",
                                            "completed_steps", "stop_state", "stop_pair", "prepare", "loop_ms",
                                            "device_timing_ms", "worker_wall_s", "echo_q0", "echo_p0", "block")}}
    if keep_detail:
        out["gpu_detail"] = {"steps": rec.get("steps"), "full": rec.get("full")}
    pr = rec.get("pass_record")
    if pr is not None:
        out["effective_p"] = pr.get("effective_p")
        out.update({k: pr.get(k) for k in OUTCOME_KEYS})
    if cls == "GPU_PRECISION_MISMATCH" and not faults.get("fault_hide_mismatch"):
        out["outcome"] = "INVALID_EVIDENCE"
    return out
