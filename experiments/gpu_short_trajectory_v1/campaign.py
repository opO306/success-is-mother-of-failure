"""GPU_SHORT_TRAJECTORY_V1 campaign (protocol.json).

    python -m experiments.gpu_short_trajectory_v1.campaign --out DIR --phase s10|s100|perf

s10: build + env + every main trajectory T = 10 with blocks 32 / 64 / 128 / 256, every probe, the refusal run.
s100: every main trajectory T = 100 (block 32). perf: warm (5 alternating) and cold (3 alternating, fresh processes)
CPU_W6 vs GPU_HYBRID trajectories, T = 100, from the FCC_N initial state. The launcher runs the independent checker
between the phases and stops when it is not EVIDENCE OK.
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

from experiments.gpu_pair_vector_v1 import pv_host as PH
from experiments.gpu_short_trajectory_v1 import traj as TR

ROOT = Path(__file__).resolve().parents[2]
PROTO = json.loads((Path(__file__).with_name("protocol.json")).read_text(encoding="utf-8"))
BUNDLE = ROOT / "docs/active/gpu_short_trajectory_v1/bundle.json.gz"
BUNDLE_SHA = (ROOT / "docs/active/gpu_short_trajectory_v1/bundle.json.gz.sha256").read_text(encoding="utf-8").strip()
BLOCKS = (32, 64, 128, 256)
WARM_REPS, COLD_REPS, PERF_T = 5, 3, 100
SEALED = [f"experiments/gpu_short_trajectory_v1/{f}" for f in
          ("protocol.json", "samples.py", "traj.py", "campaign.py", "checker.py", "analyze.py")] + \
         ["docs/active/gpu_short_trajectory_v1/bundle.json.gz", "docs/active/gpu_short_trajectory_v1/bundle.json.gz.sha256",
          "experiments/gpu_one_step_v1/one_step.py", "experiments/gpu_one_step_v1/campaign.py",
          "experiments/gpu_pair_vector_v1/pv1.cu", "experiments/gpu_pair_vector_v1/pv_host.py",
          "experiments/gpu_pair_vector_v1/campaign.py", "experiments/gpu_force_feasibility_v1/g0.cu",
          "experiments/gpu_force_feasibility_v1/gpu_host.py", "experiments/gpu_force_feasibility_v1/compile_plan.py",
          "experiments/rewrite_pilot_a3/rwforce.py", "exact_expression_gate_v1/stream.py",
          "exact_expression_gate_v1/common.py", "experiments/e2_pair_parallel_v1/run.py"]


def git(*a):
    return subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
                          errors="replace").stdout.strip()


def lf(p):
    return hashlib.sha256(Path(p).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def load_bundle():
    raw = BUNDLE.read_bytes()
    if hashlib.sha256(raw).hexdigest() != BUNDLE_SHA:
        raise SystemExit("trajectory bundle hash differs from the sealed value")
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


def run_one(ex, out_dir, t, T, block, grid=0, fault=0, pvfault=0, g0fault=0, wl=16, upload_p=None, p=None, kind=None,
            tag=""):
    p = p or t["p"]
    t0 = time.perf_counter()
    rec = TR.hybrid_trajectory(ex, TR.dec(t["q0"]), TR.dec(t["p0"]), p, T, fault, pvfault, g0fault, wl, block, grid,
                               upload_p, ref_steps=t["steps"])
    rec.update(traj_id=t["id"] if kind != "REFUSAL" else f"REFUSAL_p{p}", kind=kind or t["kind"], block=block,
               grid=grid, fault=fault, pvfault=pvfault, g0fault=g0fault, work_limbs=wl, upload_p=upload_p or p,
               device=ex.pv.device, memory=ex.pv.mem, wall_ms=(time.perf_counter() - t0) * 1000,
               plan=PH.plan_record(block, grid, t["N"], "CANONICAL_PER_ATOM_COMPONENT", upload_p or p))
    stem = f"{rec['traj_id']}__T{T}__b{block}_g{grid}" + "".join(
        f"__{k}{v}" for k, v in (("f", fault), ("v", pvfault), ("g", g0fault)) if v) + \
        (f"__wl{wl}" if wl != 16 else "") + (f"__up{upload_p}" if upload_p else "") + tag
    d = out_dir / "runs"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{stem}.json.gz").write_bytes(gzip.compress(json.dumps(rec).encode(), mtime=0))
    return rec


def _say(t, T, r):
    print(f"{t['id']} T{T} b{r['block']}: {r['status']} stop {r['stop_state']} pair {r['stop_pair']} completed "
          f"{r['completed_steps']} evals {r['force_evals']} dump {r['dump'] and r['dump']['s']} "
          f"{r['wall_ms']:.0f} ms", flush=True)


def phase_s10(ex, out, b):
    for t in b["main"]:
        for block in BLOCKS:
            r = run_one(ex, out, t, 10, block)
        _say(t, 10, r)
    for t in b["probes"]:
        _say(t, 10, run_one(ex, out, t, 10, 32))
    r = run_one(ex, out, b["main"][0], 10, 32, p=100, kind="REFUSAL")
    print("refusal run:", r["status"], flush=True)


def phase_s100(ex, out, b):
    for t in b["main"]:
        _say(t, 100, run_one(ex, out, t, 100, 32))


# ---------------------------------------------------------------------------
# performance
# ---------------------------------------------------------------------------
def _med(xs):
    return sorted(xs)[len(xs) // 2]


def _ref_final(t):
    f = t["full"]["100"]
    return {"state": TR.state_dg(TR.dec(f["q"]), TR.dec(f["p_mom"])), "force": TR.dg("F", TR.dec(f["F"]))}


def _cold(path, lib, t, out):
    sf = out / f"cold_state_{t['id']}.json"
    sf.write_text(json.dumps({"q0": t["q0"], "p0": t["p0"]}), encoding="utf-8")
    t0 = time.perf_counter()
    pr = subprocess.run([sys.executable, "-m", "experiments.gpu_short_trajectory_v1.traj", "cold", path, str(lib),
                         str(t["N"]), str(t["p"]), str(PERF_T), str(sf)], cwd=ROOT, capture_output=True, text=True)
    wall = (time.perf_counter() - t0) * 1000
    line = next((x for x in pr.stdout.splitlines() if x.startswith("COLD_RESULT ")), None)
    if line is None:
        raise RuntimeError(f"cold {path} failed: {pr.stdout[-2000:]} {pr.stderr[-3000:]}")
    res = json.loads(line[len("COLD_RESULT "):])
    res["subprocess_wall_ms"] = wall
    return res


def perf(lib, out, b):
    from experiments.gpu_one_step_v1.campaign import snapshot
    from experiments.gpu_one_step_v1 import one_step as OS
    from experiments.gpu_pair_vector_v1.campaign import W6E2
    res = {"rows": []}
    for cond in PROTO["performance"]["conditions (sealed)"]:
        N, p = cond["N"], cond["p"]
        t = next(x for x in b["main"] if (x["N"], x["p"], x["start_step"]) == (N, p, 0))
        q0, p0, ref = TR.dec(t["q0"]), TR.dec(t["p0"]), _ref_final(t)
        c = OS.lifted(p)
        snap = snapshot()
        ex = TR.TrajExecutor(lib, block=32)
        ex.prepare(p, N)
        w6 = W6E2(N, p)
        TR.gpu_warm_trajectory(ex, q0, p0, p, 2, c)                       # warm-up, discarded
        TR.w6_warm_trajectory(w6, q0, p0, p, 2, c)
        G, W, equal = [], [], []
        for r in range(WARM_REPS):
            for path in (("w6", "gpu") if r % 2 == 0 else ("gpu", "w6")):
                if path == "gpu":
                    acc, o = TR.gpu_warm_trajectory(ex, q0, p0, p, PERF_T, c)
                    G.append(acc)
                else:
                    acc, o = TR.w6_warm_trajectory(w6, q0, p0, p, PERF_T, c)
                    W.append(acc)
                equal.append(TR.final_digests(o) == ref)
            print(f"  N{N} p{p} warm rep {r}: GPU {G[-1]['total_ms']:.0f} W6 {W[-1]['total_ms']:.0f} ms", flush=True)
        w6.close()
        ex.pv.lib.pv_free()
        CG, CW = [], []
        for r in range(COLD_REPS):
            for path in (("w6", "gpu") if r % 2 == 0 else ("gpu", "w6")):
                x = _cold(path, lib, t, out)
                (CG if path == "gpu" else CW).append(x)
                equal.append({"state": x["state"], "force": x["force"]} == ref)
            print(f"  N{N} p{p} cold rep {r}: GPU {CG[-1]['cold_total_ms']:.0f} W6 {CW[-1]['cold_total_ms']:.0f} ms",
                  flush=True)
        gm = {k: _med([x[k] for x in G]) for k in G[0]}
        wm = {k: _med([x[k] for x in W]) for k in W[0]}
        ratio = gm["total_ms"] / wm["total_ms"]
        cg, cw = _med([x["cold_total_ms"] for x in CG]), _med([x["cold_total_ms"] for x in CW])
        cls = "GPU_WIN" if ratio <= 0.97 else "CPU_WIN" if ratio >= 1.03 else "TIE"
        row = {**cond, "T": PERF_T, "pairs": N * (N - 1) // 2, "load": snap, "class": cls, "ratio_warm": ratio,
               "ratio_cold": cg / cw, "gpu_warm_ms": gm["total_ms"], "w6_warm_ms": wm["total_ms"],
               "gpu_cold_ms": cg, "w6_cold_ms": cw, "gpu_warm_per_step_ms": gm["total_ms"] / PERF_T,
               "w6_warm_per_step_ms": wm["total_ms"] / PERF_T, "gpu_breakdown": gm, "w6_breakdown": wm,
               "gpu_warm_all": [x["total_ms"] for x in G], "w6_warm_all": [x["total_ms"] for x in W],
               "gpu_cold_all": CG, "w6_cold_all": CW, "final_states_equal_reference": all(equal),
               "plan": PH.plan_record(32, 0, N, "CANONICAL_PER_ATOM_COMPONENT", p)}
        res["rows"].append(row)
        print(f"perf N{N} p{p}: warm GPU {gm['total_ms']:.0f} ms | W6 {wm['total_ms']:.0f} ms -> {ratio:.3f} {cls} | "
              f"cold GPU {cg:.0f} W6 {cw:.0f} | equal {all(equal)} | load {snap['other_total_pct']}% {snap['loadavg']}",
              flush=True)
        (out / "perf.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--phase", required=True, choices=("s10", "s100", "perf"))
    a = ap.parse_args()
    out = Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    lib, arch, log = PH.build(out / "build")
    if a.phase == "s10":
        (out / "env.json").write_text(json.dumps(env(lib, arch), indent=1), encoding="utf-8")
    b = load_bundle()
    if a.phase == "perf":
        perf(lib, out, b)
    else:
        ex = TR.TrajExecutor(lib, block=32)
        print("device", ex.pv.device, flush=True)
        (phase_s10 if a.phase == "s10" else phase_s100)(ex, out, b)
        ex.pv.lib.pv_free()
    print("finished", a.phase, flush=True)


if __name__ == "__main__":
    main()
