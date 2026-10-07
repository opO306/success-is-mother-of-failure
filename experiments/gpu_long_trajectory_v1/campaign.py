"""GPU_LONG_TRAJECTORY_V1 campaign (protocol 'phases').

    python -m experiments.gpu_long_trajectory_v1.campaign --out DIR --phase gateP|fixed|service|perf

The launcher runs the independent checker after gateP / fixed / service and stops at the first verdict that is not
EVIDENCE OK. The service phase reads only DIR/gpu_support.json (written by the checker after gate P).
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path

from experiments.gpu_long_trajectory_v1 import long as LG
from experiments.gpu_pair_vector_v1 import pv_host as PH
from experiments.gpu_short_trajectory_v1 import traj as TR

ROOT = Path(__file__).resolve().parents[2]
BUNDLE = ROOT / "docs/active/gpu_long_trajectory_v1/bundle.json.gz"
BUNDLE_SHA = (ROOT / "docs/active/gpu_long_trajectory_v1/bundle.json.gz.sha256").read_text(encoding="utf-8").strip()
BLOCKS = (32, 64, 128, 256)
START_P = {"BASE64": 64, "FAMILY_MAX": 163}
WARM_REPS, SERVICE_REPS, COLD_REPS = 5, 3, 2
SEALED = [f"experiments/gpu_long_trajectory_v1/{f}" for f in
          ("protocol.json", "samples.py", "support.py", "long.py", "campaign.py", "checker.py", "analyze.py")] + \
         ["docs/active/gpu_long_trajectory_v1/bundle.json.gz", "docs/active/gpu_long_trajectory_v1/bundle.json.gz.sha256",
          "experiments/gpu_short_trajectory_v1/traj.py", "experiments/gpu_short_trajectory_v1/samples.py",
          "experiments/gpu_short_trajectory_v1/checker.py", "experiments/gpu_pair_vector_v1/checker.py",
          "experiments/gpu_one_step_v1/one_step.py", "experiments/gpu_pair_vector_v1/pv1.cu",
          "experiments/gpu_pair_vector_v1/pv_host.py", "experiments/gpu_pair_vector_v1/campaign.py",
          "experiments/gpu_force_feasibility_v1/g0.cu", "experiments/gpu_force_feasibility_v1/gpu_host.py",
          "experiments/gpu_force_feasibility_v1/compile_plan.py", "experiments/precision_pilot_a1/policies.py",
          "experiments/precision_pilot_a1/evaluator_adapter.py", "experiments/multiatom_parallel_v1/run.py",
          "exact_expression_gate_v1/stream.py", "exact_expression_gate_v1/common.py",
          "experiments/rewrite_pilot_a3/rwforce.py", "experiments/e2_pair_parallel_v1/run.py"]


def git(*a):
    return subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
                          errors="replace").stdout.strip()


def lf(p):
    return hashlib.sha256(Path(p).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def load_bundle():
    raw = BUNDLE.read_bytes()
    if hashlib.sha256(raw).hexdigest() != BUNDLE_SHA:
        raise SystemExit("long bundle hash differs from the sealed value")
    return json.loads(gzip.decompress(raw))


def env(lib, arch):
    import mpmath
    import mpmath.libmp
    smi = subprocess.run(["nvidia-smi", "--query-gpu=name,driver_version,memory.total,compute_cap", "--format=csv,noheader"],
                         capture_output=True, text=True).stdout.strip()
    return {"head": git("rev-parse", "HEAD"), "branch": git("branch", "--show-current"),
            "status_porcelain": git("status", "--porcelain", "--untracked-files=no"),
            "sealed_sources_dirty": bool(git("status", "--porcelain", "--", *SEALED)),
            "source_sha256_lf": {x: lf(ROOT / x) for x in SEALED}, "python": sys.version, "platform": sys.platform,
            "host": platform.node(), "mpmath": mpmath.__version__, "mpmath_backend": mpmath.libmp.BACKEND,
            "nvidia_smi": smi, "arch": arch, "lib_sha256": hashlib.sha256(Path(lib).read_bytes()).hexdigest(),
            "bundle_sha256": BUNDLE_SHA, "cpu_count": os.cpu_count(),
            "linux_clock_shim": os.environ.get("ESP2_LINUX_CLOCK"), "pythonpath": os.environ.get("PYTHONPATH")}


def _save(path, rec):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(gzip.compress(json.dumps(rec).encode(), mtime=0))


# ---------------------------------------------------------------------------
# gate P
# ---------------------------------------------------------------------------
def gate_p_one(ex, out, g, block, device_p=None, fault=None, tag=""):
    """One gate-P state: full pair records + atom records at the requested p (device_p: disguise faults only)."""
    p, N = g["p"], g["N"]
    meta = {"state_id": g["id"], "requested_p": p, "block": block, "fault": fault, "status": "OK"}
    try:
        if ex.pv.p != (device_p or p):
            ex.pv.upload(device_p or p)
        q = TR.dec(g["q"])
        pos = PH.encode_positions(q)
        full, comp, atoms, tm = ex.pv.run_state(pos, N, 1 | 4, block, 0, 0, 0, 16)
        rf, ra = bytes(full), bytes(atoms)
        meta.update(device_p=p if fault else ex.pv.p, timing_ms=tm, plan=PH.plan_record(block, 0, N, "CANONICAL_PER_ATOM_COMPONENT", p))
    except LG.GH.Refused as e:
        rf = ra = b""
        meta.update(status=str(e).split(":")[0], device_p=None)
    d = out / "gateP"
    d.mkdir(parents=True, exist_ok=True)
    stem = f"{g['id']}__b{block}{tag}"
    (d / f"{stem}.full.gz").write_bytes(gzip.compress(rf, mtime=0))
    (d / f"{stem}.atoms.gz").write_bytes(gzip.compress(ra, mtime=0))
    (d / f"{stem}.json").write_text(json.dumps(meta), encoding="utf-8")
    return meta


def phase_gate_p(ex, out, b):
    for g in b["gate_P_states"]:
        for block in (32, 128):
            m = gate_p_one(ex, out, g, block)
        print(f"gateP {g['id']} {g['role']}: {m['status']} device p {m['device_p']}", flush=True)


# ---------------------------------------------------------------------------
# fixed-p passes
# ---------------------------------------------------------------------------
def fixed_one(ex, out, t, block, fault=0, tag=""):
    q0, p0 = TR.dec(t["q0"]), TR.dec(t["p0"])
    t0 = time.perf_counter()
    rec = LG.long_pass(ex, q0, p0, t["p"], fault=fault, block=block, ref_steps=t["steps"])
    rec.update(kind="FIXED", traj_id=t["id"], wall_ms=(time.perf_counter() - t0) * 1000, device=ex.pv.device,
               memory=ex.pv.mem)
    _save(out / "runs" / f"{t['id']}__b{block}{('__f%d' % fault) if fault else ''}{tag}.json.gz", rec)
    print(f"fixed {t['id']} b{block}: {rec['status']} stop {rec['stop_state']} pair {rec['stop_pair']} completed "
          f"{rec['completed_steps']} evals {rec['force_evals']} outcome {rec['pass_record']['outcome']} dump "
          f"{rec['dump'] and rec['dump']['s']} {rec['wall_ms'] / 1000:.1f} s", flush=True)
    return rec


def phase_fixed(ex, out, b):
    tr = {(t["N"], t["p"]): t for t in b["trajectories"]}
    for N in (12, 16):
        for block in BLOCKS:
            fixed_one(ex, out, tr[(N, 163)], block)
    fixed_one(ex, out, tr[(40, 109)], 32)
    for N in (12, 16):
        fixed_one(ex, out, tr[(N, 64)], 32)


# ---------------------------------------------------------------------------
# services
# ---------------------------------------------------------------------------
def load_support(out):
    f = out / "gpu_support.json"
    if not f.exists():
        raise SystemExit("gpu_support.json missing: the gate-P checker must run first")
    s = json.loads(f.read_text(encoding="utf-8"))
    if s.get("gate_verdict") != "EVIDENCE OK":
        raise SystemExit("gate P not EVIDENCE OK")
    return set(s["GPU_SUPPORTED_P"])


def ref_steps(b, N):
    return {t["p"]: t["steps"] for t in b["trajectories"] if t["N"] == N}


def service_one(ex, out, b, N, policy, support, fault=0, demonstration=False, tag="", **kw):
    s = LG.run_service(ex, N, policy, START_P[policy], support, fault=fault, ref_steps=ref_steps(b, N),
                       demonstration=demonstration, **kw)
    name = f"N{N}_{policy}" + ("__demo_no73" if demonstration else "") + (f"__f{fault}" if fault else "") + tag
    _save(out / "services" / f"{name}.json.gz", s)
    print(f"service {name}: {s['status']} seq {s['p_sequence']} backends {[x['backend'] for x in s['passes']]} "
          f"label {s['execution_label']} {s['service_wall_ms'] / 1000:.1f} s", flush=True)
    return s


def phase_service(ex, out, b):
    support = load_support(out)
    for N in (12, 16):
        for policy in START_P:
            service_one(ex, out, b, N, policy, support)
    service_one(ex, out, b, 12, "BASE64", support - {73}, demonstration=True)


# ---------------------------------------------------------------------------
# performance
# ---------------------------------------------------------------------------
def _med(xs):
    return sorted(xs)[len(xs) // 2]


def _perf_pass_gpu(ex, N, p):
    """A timed GPU pass without digests: prepare (re-upload when p changes) + initial F + up to T steps + readout."""
    from experiments.gpu_one_step_v1 import one_step as OS
    q0, p0 = LG.initial(N, p)
    t0 = time.perf_counter()
    ex.prepare(p, N)
    prep = dict(ex.last_prepare)
    c = OS.lifted(p)
    st, pid, F, _ = ex.force(q0, N)
    q, pm, done, stop = q0, p0, 0, None
    if st != "OK":
        stop = (st, 0)
    else:
        for s in range(LG.T):
            ph = OS.kick(pm, F, p)
            q1 = OS.drift(q, ph, p, c)
            st, pid, F, _ = ex.force(q1, N)
            if st != "OK":
                stop = (st, s + 1)
                q, pm = q1, ph
                break
            pm = OS.kick(ph, F, p)
            q, done = q1, s + 1
    rec = LG.readout(N, p, done, stop and stop[0].replace("DOMAIN_STOP_", ""), stop and stop[1], q, pm)
    return rec, {"wall_ms": (time.perf_counter() - t0) * 1000, **prep}


def _perf_pass_w6(N, p):
    """A timed CPU W6 pass (V2 behaviour: workers spawned for this p): spawn + initial F + steps + readout."""
    from exact_expression_gate_v1 import common as K
    from experiments.gpu_one_step_v1 import one_step as OS
    from experiments.gpu_pair_vector_v1.campaign import W6E2
    q0, p0 = LG.initial(N, p)
    t0 = time.perf_counter()
    w6 = W6E2(N, p)
    spawn = (time.perf_counter() - t0) * 1000
    c = OS.lifted(p)
    q, pm, done, stop = q0, p0, 0, None
    try:
        _, F = w6.forces(q0)
        for s in range(LG.T):
            ph = OS.kick(pm, F, p)
            q1 = OS.drift(q, ph, p, c)
            try:
                _, F = w6.forces(q1)
            except K.DomainStop as e:
                stop = (e.kind, s + 1)
                q, pm = q1, ph
                break
            pm = OS.kick(ph, F, p)
            q, done = q1, s + 1
    except K.DomainStop as e:
        stop = (e.kind, 0)
    rec = LG.readout(N, p, done, stop and stop[0], stop and stop[1], q, pm)
    wall = (time.perf_counter() - t0) * 1000
    w6.close()
    return rec, {"wall_ms": wall, "spawn_ms": spawn}


def _service_timed(N, policy, run_pass):
    from experiments.precision_pilot_a1 import policies as POL
    hist, passes = [], []
    t0 = time.perf_counter()
    p = START_P[policy]
    while p is not None and p != "CAP" and len(hist) < LG.MAX_PASSES:
        rec, tm = run_pass(N, p)
        passes.append({"p": p, "outcome": rec["outcome"], "completed_steps": rec["completed_steps"],
                       "cells": rec["cells"], "endpoints_key": rec["endpoints_key"], **tm})
        hist.append({"requested_p": p, "outcome": rec["outcome"], "completed_steps": rec["completed_steps"],
                     "endpoints_scaled": rec.get("endpoints_scaled")})
        p = POL.next_p("P2", None, hist, LG.T)
    total = (time.perf_counter() - t0) * 1000
    return {"total_ms": total, "passes": passes, "p_sequence": [x["p"] for x in passes],
            "failed_pass_ms": sum(x["wall_ms"] for x in passes[:-1]), "final_pass_ms": passes[-1]["wall_ms"]}


def _cold(lib, N, policy):
    t0 = time.perf_counter()
    pr = subprocess.run([sys.executable, "-m", "experiments.gpu_long_trajectory_v1.campaign", "--cold", str(lib), str(N),
                         policy], cwd=ROOT, capture_output=True, text=True)
    line = next((x for x in pr.stdout.splitlines() if x.startswith("COLD_RESULT ")), None)
    if line is None:
        raise RuntimeError(f"cold failed: {pr.stdout[-1500:]} {pr.stderr[-3000:]}")
    res = json.loads(line[len("COLD_RESULT "):])
    res["subprocess_wall_ms"] = (time.perf_counter() - t0) * 1000
    return res


def cold_main(lib, N, policy):
    t0 = time.perf_counter()
    ex = LG.LongExecutor(lib, block=32)
    t1 = time.perf_counter()
    s = _service_timed(N, policy, lambda n, p: _perf_pass_gpu(ex, n, p))
    print("COLD_RESULT " + json.dumps({"cold_total_ms": (time.perf_counter() - t0) * 1000,
                                       "executor_create_ms": (t1 - t0) * 1000, "context_ms": ex.init["context_ms"],
                                       **s}, default=str), flush=True)


def perf(lib, out, b):
    from experiments.gpu_one_step_v1 import one_step as OS
    from experiments.gpu_one_step_v1.campaign import snapshot
    from experiments.gpu_pair_vector_v1.campaign import W6E2
    res = {"fixed": [], "services": [], "cold": []}
    tr = {(t["N"], t["p"]): t for t in b["trajectories"]}
    corr = {}
    for f in (out / "services").glob("N*_*.json.gz"):
        s = json.loads(gzip.decompress(f.read_bytes()))
        if not s.get("demonstration") and not s.get("fault"):
            corr[(s["N"], s["policy"])] = s
    equal = []
    # fixed p163 T1000 (warm)
    for N in (12, 16):
        t = tr[(N, 163)]
        q0, p0 = TR.dec(t["q0"]), TR.dec(t["p0"])
        f = t["full"]["1000"]
        ref = {"state": TR.state_dg(TR.dec(f["q"]), TR.dec(f["p_mom"])), "force": TR.dg("F", TR.dec(f["F"]))}
        c = OS.lifted(163)
        snap = snapshot()
        ex = LG.LongExecutor(lib, block=32)
        ex.prepare(163, N)
        w6 = W6E2(N, 163)
        TR.gpu_warm_trajectory(ex, q0, p0, 163, 2, c)
        TR.w6_warm_trajectory(w6, q0, p0, 163, 2, c)
        G, W = [], []
        for r in range(WARM_REPS):
            for path in (("w6", "gpu") if r % 2 == 0 else ("gpu", "w6")):
                if path == "gpu":
                    acc, o = TR.gpu_warm_trajectory(ex, q0, p0, 163, LG.T, c)
                    G.append(acc)
                else:
                    acc, o = TR.w6_warm_trajectory(w6, q0, p0, 163, LG.T, c)
                    W.append(acc)
                equal.append(TR.final_digests(o) == ref)
            print(f"  fixed N{N} rep {r}: GPU {G[-1]['total_ms']:.0f} W6 {W[-1]['total_ms']:.0f} ms", flush=True)
        w6.close()
        ex.pv.lib.pv_free()
        gm = {k: _med([x[k] for x in G]) for k in G[0]}
        wm = {k: _med([x[k] for x in W]) for k in W[0]}
        ratio = gm["total_ms"] / wm["total_ms"]
        cls = "GPU_WIN" if ratio <= 0.97 else "CPU_WIN" if ratio >= 1.03 else "TIE"
        res["fixed"].append({"N": N, "p": 163, "T": LG.T, "gpu_ms": gm["total_ms"], "w6_ms": wm["total_ms"], "ratio": ratio,
                             "class": cls, "gpu_all": [x["total_ms"] for x in G], "w6_all": [x["total_ms"] for x in W],
                             "gpu_breakdown": gm, "w6_breakdown": wm, "load": snap})
        print(f"perf fixed N{N} p163 T1000: GPU {gm['total_ms']:.0f} W6 {wm['total_ms']:.0f} -> {ratio:.3f} {cls} | load "
              f"{snap['other_total_pct']}% {snap['loadavg']}", flush=True)
        (out / "perf.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    # service totals (GPU service vs CPU W6 service)
    ex = LG.LongExecutor(lib, block=32)
    for N in (12, 16):
        for policy in START_P:
            snap = snapshot()
            G, W = [], []
            for r in range(SERVICE_REPS):
                for path in (("cpu", "gpu") if r % 2 == 0 else ("gpu", "cpu")):
                    if path == "gpu":
                        G.append(_service_timed(N, policy, lambda n, p: _perf_pass_gpu(ex, n, p)))
                    else:
                        W.append(_service_timed(N, policy, _perf_pass_w6))
            want = corr.get((N, policy))
            for x in G + W:
                same = want is not None and x["p_sequence"] == want["p_sequence"] and \
                    [(y["outcome"], y["completed_steps"], y["cells"], y["endpoints_key"]) for y in x["passes"]] == \
                    [(y["pass_record"]["outcome"], y["pass_record"]["completed_steps"], y["pass_record"]["cells"],
                      y["pass_record"]["endpoints_key"]) for y in want["passes"]]
                equal.append(same)
            row = {"N": N, "policy": policy, "p_sequence": G[0]["p_sequence"],
                   "gpu_total_ms": _med([x["total_ms"] for x in G]), "cpu_total_ms": _med([x["total_ms"] for x in W]),
                   "gpu_all": G, "cpu_all": W, "load": snap}
            row["ratio"] = row["gpu_total_ms"] / row["cpu_total_ms"]
            res["services"].append(row)
            print(f"perf service N{N} {policy}: GPU {row['gpu_total_ms']:.0f} CPU_W6 {row['cpu_total_ms']:.0f} ms seq "
                  f"{row['p_sequence']} ratio {row['ratio']:.3f}", flush=True)
            (out / "perf.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    ex.pv.lib.pv_free()
    for N in (12, 16):
        for policy in START_P:
            for _ in range(COLD_REPS):
                x = _cold(lib, N, policy)
                res["cold"].append({"N": N, "policy": policy, **x})
                print(f"cold N{N} {policy}: {x['cold_total_ms']:.0f} ms (context {x['context_ms']:.0f}) seq "
                      f"{x['p_sequence']}", flush=True)
    res["outcomes_equal_correctness"] = all(equal)
    (out / "perf.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    return res


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--cold":
        cold_main(sys.argv[2], int(sys.argv[3]), sys.argv[4])
        return
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--phase", required=True, choices=("gateP", "fixed", "service", "perf"))
    a = ap.parse_args()
    out = Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    lib, arch, log = PH.build(out / "build")
    if a.phase == "gateP":
        (out / "env.json").write_text(json.dumps(env(lib, arch), indent=1), encoding="utf-8")
    b = load_bundle()
    if a.phase == "perf":
        perf(lib, out, b)
    else:
        ex = LG.LongExecutor(lib, block=32)
        print("device", ex.pv.device, flush=True)
        {"gateP": phase_gate_p, "fixed": phase_fixed, "service": phase_service}[a.phase](ex, out, b)
        ex.pv.lib.pv_free()
    print("finished", a.phase, flush=True)


if __name__ == "__main__":
    main()
