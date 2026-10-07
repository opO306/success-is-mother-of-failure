"""GPU_ONE_STEP_V1 campaign (protocol.json): build -> one-step correctness for every bundle state (layouts) ->
performance: steady step and INIT, CPU_W6 vs GPU_HYBRID, alternating order, load snapshots.

    python -m experiments.gpu_one_step_v1.campaign --out DIR [--no-perf]
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

from experiments.gpu_force_feasibility_v1.dyadic import decode_iv
from experiments.gpu_one_step_v1 import one_step as OS
from experiments.gpu_pair_vector_v1 import pv_host as PH

ROOT = Path(__file__).resolve().parents[2]
PROTO = json.loads((Path(__file__).with_name("protocol.json")).read_text(encoding="utf-8"))
BUNDLE = ROOT / "docs/active/gpu_one_step_v1/states.json.gz"
BUNDLE_SHA = (ROOT / "docs/active/gpu_one_step_v1/states.json.gz.sha256").read_text(encoding="utf-8").strip()
BLOCKS = (32, 64, 128, 256)
SEALED = [f"experiments/gpu_one_step_v1/{f}" for f in
          ("protocol.json", "samples.py", "one_step.py", "campaign.py", "checker.py", "analyze.py")] + \
         ["docs/active/gpu_one_step_v1/states.json.gz", "docs/active/gpu_one_step_v1/states.json.gz.sha256",
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
        raise SystemExit("one-step bundle hash differs from the sealed value")
    return json.loads(gzip.decompress(raw))


def states(b):
    return [("main", x) for x in b["main"]] + [("test", x) for x in b["test_only"]]


def dec(rows):
    return [[decode_iv(e) for e in r] for r in rows]


def env(lib, arch, log):
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


def run_one(ex, out_dir, kind, st, block, grid=0, fault=0, pvfault=0, g0fault=0, wl=16, upload_p=None):
    t0 = time.perf_counter()
    rec = OS.hybrid_step(ex, dec(st["q"]), dec(st["p_mom"]), st["p"], fault, pvfault, g0fault, wl, block, grid, upload_p)
    rec.update(state_kind=kind, state_id=st["id"], role=st.get("role", "MAIN"), block=block, grid=grid, fault=fault,
               pvfault=pvfault, g0fault=g0fault, work_limbs=wl, upload_p=upload_p or st["p"], device=ex.pv.device,
               memory=ex.pv.mem, wall_ms=(time.perf_counter() - t0) * 1000,
               plan=PH.plan_record(block, grid, st["N"], "CANONICAL_PER_ATOM_COMPONENT", upload_p or st["p"]))
    stem = f"{kind}{st['id']}__b{block}_g{grid}" + "".join(f"__{k}{v}" for k, v in
                                                            (("f", fault), ("v", pvfault), ("g", g0fault)) if v) + \
        (f"__wl{wl}" if wl != 16 else "") + (f"__up{upload_p}" if upload_p else "")
    d = out_dir / "runs"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{stem}.json.gz").write_bytes(gzip.compress(json.dumps(rec).encode(), mtime=0))
    return rec


def correctness(ex, out_dir, sts):
    for idx, (kind, st) in enumerate(sts):
        lay = [(b, 0) for b in BLOCKS] if kind == "main" else [(32, 0)]
        if kind == "main" and idx < 2:
            lay += [(32, 1), (32, 7)]
        for block, grid in lay:
            r = run_one(ex, out_dir, kind, st, block, grid)
        print(f"state {kind}{st['id']} N{st['N']} p{st['p']} {st.get('role', 'MAIN')}: {r['status']} {r['stop_stage']} "
              f"{r['stop_pair']} decide {str(r['decide'])[:20]} ({len(lay)} layouts)", flush=True)


# ---------------------------------------------------------------------------
# performance
# ---------------------------------------------------------------------------
def snapshot():
    import psutil

    from experiments.e2_pair_parallel_v1.campaign import contamination
    me = psutil.Process()
    own = {me.pid} | {c.pid for c in me.children(recursive=True)}
    procs = [pr for pr in psutil.process_iter(["pid", "name"]) if pr.pid not in own and pr.pid != 0]
    for pr in procs:
        try:
            pr.cpu_percent(None)
        except psutil.Error:
            pass
    time.sleep(1.0)
    rows = []
    for pr in procs:
        try:
            v = pr.cpu_percent(None)
            if v > 0:
                rows.append((pr.info["name"], pr.pid, round(v, 1)))
        except psutil.Error:
            pass
    rows.sort(key=lambda x: -x[2])
    la = Path("/proc/loadavg").read_text().split()[:3] if Path("/proc/loadavg").exists() else None
    return {**contamination(rows), "rows": rows[:10], "loadavg": la}


def perf_state(b, cond):
    from mpmath import iv

    import exact_expression_gate_v0.lang_iv as LI
    from experiments.multiatom_parallel_v1 import scenarios as SC
    N, p = cond["N"], cond["p"]
    if cond["state"].startswith("bundle"):
        s = int(cond["state"].split("s=")[1])
        st = next(x for x in b["main"] if (x["N"], x["p"], x["step"]) == (N, p, s))
        return dec(st["q"]), dec(st["p_mom"]), f"bundle state {st['id']}"
    iv.prec = p
    q0, p0 = SC.initial(N)
    return [[LI.c(x)._mpi_ for x in r] for r in q0], [[LI.c(x)._mpi_ for x in r] for r in p0], "FCC_N initial state"


def _med(xs):
    return sorted(xs)[len(xs) // 2]


def perf(lib, out_dir, b, reps=5):
    from experiments.gpu_pair_vector_v1.campaign import W6E2
    res = {"rows": []}
    for cond in PROTO["performance"]["conditions (sealed)"]:
        N, p = cond["N"], cond["p"]
        q, pm, src = perf_state(b, cond)
        c = OS.lifted(p)
        snap = snapshot()
        # INIT (GPU): a fresh executor = context + model upload + allocation + F(q0)
        t0 = time.perf_counter()
        ex = OS.GpuForceExecutor(lib, block=32)
        t1 = time.perf_counter()
        ex.prepare(p, N)
        t2 = time.perf_counter()
        st, _, Fg, tf = ex.force(q, N)
        t3 = time.perf_counter()
        g_init = {"executor_create_ms": (t1 - t0) * 1000, "context_ms": ex.init["context_ms"],
                  "model_upload_and_alloc_ms": (t2 - t1) * 1000, "initial_F0_ms": (t3 - t2) * 1000,
                  "init_total_ms": (t3 - t0) * 1000, "memory": ex.pv.mem}
        # INIT (CPU W6): worker spawn + F(q0)
        t0 = time.perf_counter()
        w6 = W6E2(N, p)
        t1 = time.perf_counter()
        _, Fw = w6.forces(q)
        t2 = time.perf_counter()
        w_init = {"spawn_ms": (t1 - t0) * 1000, "initial_F0_ms": (t2 - t1) * 1000, "init_total_ms": (t2 - t0) * 1000}
        G, W, same = [], [], []
        for r in range(reps + 1):                               # repetition 0 = warm-up, discarded
            order = ("gpu", "w6") if r % 2 == 0 else ("w6", "gpu")
            outs = {}
            for path in order:
                if path == "gpu":
                    m, outs["gpu"] = OS.gpu_steady_step(ex, q, pm, Fg, p, c)
                    (G if r else []).append(m)
                else:
                    m, outs["w6"] = OS.w6_steady_step(w6, q, pm, Fw, p, c)
                    (W if r else []).append(m)
            same.append(outs["gpu"] == outs["w6"] and Fg == Fw)
        w6.close()
        ex.pv.lib.pv_free()
        gm = {k: _med([x[k] for x in G]) for k in G[0] if k != "status"}
        wm = {k: _med([x[k] for x in W]) for k in W[0]}
        ratio = gm["total_ms"] / wm["total_ms"]
        cls = "GPU_WIN" if ratio <= 0.97 else "CPU_WIN" if ratio >= 1.03 else "TIE"
        row = {**cond, "source": src, "pairs": N * (N - 1) // 2, "load": snap, "gpu_init": g_init, "w6_init": w_init,
               "gpu_steady": gm, "w6_steady": wm, "gpu_steady_all": [x["total_ms"] for x in G],
               "w6_steady_all": [x["total_ms"] for x in W], "ratio_gpu_over_w6": ratio, "class": cls,
               "states_equal_gpu_w6_every_rep": all(same),
               "plan": PH.plan_record(32, 0, N, "CANONICAL_PER_ATOM_COMPONENT", p)}
        res["rows"].append(row)
        print(f"perf N{N} p{p}: steady GPU {gm['total_ms']:.1f} ms (force {gm['force_total_ms']:.1f}) | W6 "
              f"{wm['total_ms']:.1f} ms -> {ratio:.3f} {cls} | equal {all(same)} | init GPU {g_init['init_total_ms']:.0f} "
              f"W6 {w_init['init_total_ms']:.0f} | load {snap['other_total_pct']}% {snap['loadavg']}", flush=True)
    (out_dir / "perf.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--no-perf", action="store_true")
    a = ap.parse_args()
    out = Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    lib, arch, log = PH.build(out / "build")
    (out / "env.json").write_text(json.dumps(env(lib, arch, log), indent=1), encoding="utf-8")
    b = load_bundle()
    ex = OS.GpuForceExecutor(lib, block=32)
    print("device", ex.pv.device, flush=True)
    correctness(ex, out, states(b))
    ex.pv.lib.pv_free()
    if not a.no_perf:
        perf(lib, out, b)
    print("finished", flush=True)


if __name__ == "__main__":
    main()
