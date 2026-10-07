"""G0 campaign (protocol.json): build -> correctness runs on the sealed bundle in every layout -> test-only runs ->
performance (CPU_SERIAL_E2, CPU_W6_E2, GPU_E2_G0) on the same host.

    python -m experiments.gpu_force_feasibility_v1.campaign --out DIR [--no-perf]
Evidence: DIR/runs/<subset>__b<block>_g<grid>.json (+ .bin.gz raw device output words), DIR/perf.json, DIR/env.json.
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

from experiments.gpu_force_feasibility_v1 import gpu_host as GH
from experiments.gpu_force_feasibility_v1.dyadic import decode_iv

ROOT = Path(__file__).resolve().parents[2]
PROTO = json.loads((Path(__file__).with_name("protocol.json")).read_text(encoding="utf-8"))
BUNDLE = ROOT / "docs/active/gpu_force_feasibility_v1/samples.json.gz"
BUNDLE_SHA = (ROOT / "docs/active/gpu_force_feasibility_v1/samples.json.gz.sha256").read_text(encoding="utf-8").strip()
BLOCKS = (32, 64, 128, 256)
GRIDS = (1, 7, 0)                      # 0 = ceil(n / block)
BATCHES = (128, 512, 780, 2016, 2048, 8192, 32768)
SEALED = [f"experiments/gpu_force_feasibility_v1/{f}" for f in
          ("protocol.json", "dyadic.py", "samples.py", "compile_plan.py", "g0.cu", "gpu_host.py", "campaign.py",
           "checker.py", "analyze.py")] + \
         ["docs/active/gpu_force_feasibility_v1/samples.json.gz", "docs/active/gpu_force_feasibility_v1/samples.json.gz.sha256",
          "experiments/rewrite_pilot_a3/rwforce.py", "experiments/rewrite_pilot_a3/rules.py",
          "experiments/rewrite_pilot_a3/adapter.py", "exact_expression_gate_v0/lang_iv.py",
          "exact_expression_gate_v1/common.py", "a_numeric_native/harness.py"]


def git(*a):
    return subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
                          errors="replace").stdout.strip()


def lf(p):
    return hashlib.sha256(Path(p).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def load_bundle():
    raw = BUNDLE.read_bytes()
    if hashlib.sha256(raw).hexdigest() != BUNDLE_SHA:
        raise SystemExit("sample bundle hash differs from the sealed value")
    return json.loads(gzip.decompress(raw))


def subsets(b):
    """name -> (p, [sample ids], [raw R^2]) in bundle order."""
    out = {}
    for p in (109, 163):
        xs = [x for x in b["main"] if x["p"] == p]
        out[f"main_p{p}"] = (p, [x["id"] for x in xs], [decode_iv(x["r2"]) for x in xs])
    for role, tag in (("TEST_ONLY_PRECISION", "test"), ("TEST_ONLY_DOMAIN_PROBE", "probe")):
        for p in sorted({x["p"] for x in b["test_only"] if x["role"] == role}):
            xs = [x for x in b["test_only"] if x["role"] == role and x["p"] == p]
            out[f"{tag}_p{p}"] = (p, [x["id"] for x in xs], [decode_iv(x["r2"]) for x in xs])
    return out


def env(lib, arch, log):
    smi = subprocess.run(["nvidia-smi", "--query-gpu=name,driver_version,memory.total,compute_cap", "--format=csv,noheader"],
                         capture_output=True, text=True).stdout.strip()
    import mpmath
    import mpmath.libmp
    return {"head": git("rev-parse", "HEAD"), "branch": git("branch", "--show-current"),
            "status_porcelain": git("status", "--porcelain", "--untracked-files=no"),
            "sealed_sources_dirty": bool(git("status", "--porcelain", "--", *SEALED)),
            "source_sha256_lf": {x: lf(ROOT / x) for x in SEALED}, "python": sys.version, "platform": sys.platform,
            "host": platform.node(), "mpmath": mpmath.__version__, "mpmath_backend": mpmath.libmp.BACKEND,
            "nvidia_smi": smi, "arch": arch, "lib_sha256": hashlib.sha256(Path(lib).read_bytes()).hexdigest(),
            "bundle_sha256": BUNDLE_SHA, "cpu_count": os.cpu_count(),
            "ptxas": [ln for ln in log.splitlines() if "g0_kernel" in ln or "stack" in ln.lower() and "bytes" in ln][:6]}


def run_one(g, out_dir, name, p, ids, ivs, block, grid, fault=0, wl=GH.DL, tamper=None):
    """One device run of a subset; writes meta + raw output words. tamper (tests only): 'input', 'drop', 'swap'."""
    if g.p != p:
        g.upload(p)
    t0 = time.perf_counter()
    buf = GH.encode_batch(ivs)
    if tamper == "input":                                 # fault 11: one H2D limb altered by the host
        buf[5] ^= 1
    out, tm = g.run_encoded(buf, len(ivs), block, grid, fault, wl)
    raw = bytes(out)
    n_out = len(ivs)
    if tamper == "drop":                                  # fault 9: one pair's output dropped
        raw, n_out = raw[:-GH.WORDS_OUT * 4], n_out - 1
    if tamper == "swap":                                  # fault 12: two outputs swapped
        w = GH.WORDS_OUT * 4
        raw = raw[w:2 * w] + raw[:w] + raw[2 * w:]
    grid_used = grid if grid > 0 else (len(ivs) + block - 1) // block
    meta = {"subset": name, "p": p, "sample_ids": ids, "n_in": len(ivs), "n_out": n_out, "block": block, "grid_arg": grid,
            "grid_used": grid_used, "fault": fault, "work_limbs": wl, "tamper": tamper, "device": g.device,
            "timing_ms": {**tm, "wall_ms": (time.perf_counter() - t0) * 1000},
            "out_sha256": hashlib.sha256(raw).hexdigest(), "words_per_output": GH.WORDS_OUT}
    stem = f"{name}__b{block}_g{grid}" + (f"__f{fault}" if fault else "") + (f"__{tamper}" if tamper else "")
    (out_dir / "runs").mkdir(parents=True, exist_ok=True)
    (out_dir / "runs" / f"{stem}.bin.gz").write_bytes(gzip.compress(raw, mtime=0))
    (out_dir / "runs" / f"{stem}.json").write_text(json.dumps(meta), encoding="utf-8")
    return meta


def correctness(g, out_dir, subs, fault=0, wl=GH.DL, layouts=None, names=None):
    metas = []
    for name, (p, ids, ivs) in subs.items():
        if names and name not in names:
            continue
        lay = layouts or ([(b, gr) for b in BLOCKS for gr in GRIDS] if name.startswith("main") else [(128, 0)])
        for block, grid in lay:
            m = run_one(g, out_dir, name, p, ids, ivs, block, grid, fault, wl)
            metas.append(m)
            print(f"run {name} b{block} g{grid}: n {m['n_in']} kernel {m['timing_ms']['kernel_ms']:.1f} ms", flush=True)
    return metas


# ---------------------------------------------------------------------------
# performance (same host; THROUGHPUT_PROBE batches built by repeating the main samples of that p in bundle order)
# ---------------------------------------------------------------------------
def _batch(ivs, n):
    return [ivs[i % len(ivs)] for i in range(n)]


def _w6_worker(conn, cpu, p):
    import psutil
    from mpmath import iv
    try:
        psutil.Process().cpu_affinity([cpu])
    except Exception:
        pass
    from experiments.gpu_force_feasibility_v1.samples import make_force
    f = make_force(p)
    iv.prec = p
    make = iv.make_mpf
    conn.send("ready")
    while True:
        m = conn.recv()
        if m is None:
            break
        conn.send([f(make(x))._mpi_ for x in m])


def cpu_serial(p, batch):
    from mpmath import iv

    from experiments.gpu_force_feasibility_v1.samples import make_force
    f = make_force(p)
    iv.prec = p
    make = iv.make_mpf
    t0 = time.perf_counter()
    out = [f(make(x))._mpi_ for x in batch]
    return (time.perf_counter() - t0) * 1000, out


class W6:
    CPUS = (1, 2, 3, 4, 5, 0)

    def __init__(self, p):
        import multiprocessing as mp

        import psutil
        try:
            psutil.Process().cpu_affinity([0])
        except Exception:
            pass
        ctx = mp.get_context("spawn")
        t0 = time.perf_counter()
        self.pipes = [ctx.Pipe() for _ in self.CPUS]
        self.procs = [ctx.Process(target=_w6_worker, args=(b, c, p)) for (a, b), c in zip(self.pipes, self.CPUS)]
        for pr in self.procs:
            pr.start()
        for a, b in self.pipes:
            a.recv()
        self.spawn_ms = (time.perf_counter() - t0) * 1000

    def run(self, batch):
        n, W = len(batch), len(self.CPUS)
        cuts = [n * k // W for k in range(W + 1)]
        t0 = time.perf_counter()
        for k, (a, b) in enumerate(self.pipes):
            a.send(batch[cuts[k]:cuts[k + 1]])
        out = []
        for a, b in self.pipes:
            out += a.recv()
        return (time.perf_counter() - t0) * 1000, out

    def close(self):
        for a, b in self.pipes:
            a.send(None)
        for pr in self.procs:
            pr.join()


def _digest(xs):
    return hashlib.sha256(json.dumps([[list(map(str, a)), list(map(str, b))] for a, b in xs]).encode()).hexdigest()


def perf(lib, out_dir, subs, reps_gpu=5, reps_cpu=3, batches=BATCHES):
    res = {"batches": list(batches), "label": "THROUGHPUT_PROBE", "rows": []}
    for p in (109, 163):
        _, _, ivs = subs[f"main_p{p}"]
        # cold: a fresh process measures context + alloc + model upload + the first batch (2016 pairs)
        r = subprocess.run([sys.executable, "-m", "experiments.gpu_force_feasibility_v1.campaign", "--cold", str(lib),
                            str(p)], cwd=ROOT, capture_output=True, text=True)
        cold = json.loads(r.stdout.strip().splitlines()[-1]) if r.returncode == 0 else {"error": r.stderr[-800:]}
        g = GH.G0(lib)
        g.upload(p)
        g.alloc(max(batches))
        w6 = W6(p)
        for n in batches:
            batch = _batch(ivs, n)
            gt, gres = [], None
            for _ in range(reps_gpu + 1):                     # first call after a size change is discarded (warm-up)
                rr, tm, _ = g.evaluate(batch)
                gt.append(tm)
                gres = rr
            gt = gt[1:]
            st, sres = [], None
            for _ in range(reps_cpu):
                ms, sres = cpu_serial(p, batch)
                st.append(ms)
            wt, wres = [], None
            for _ in range(reps_cpu):
                ms, wres = w6.run(batch)
                wt.append(ms)
            g_ok = [x[3] for x in gres]
            row = {"p": p, "pairs": n, "N_equiv": round((2 * n) ** 0.5, 1),
                   "gpu_ms": {k: sorted(t[k] for t in gt)[len(gt) // 2] for k in gt[0]},
                   "gpu_total_ms_all": [t["total_ms"] for t in gt],
                   "cpu_serial_ms": sorted(st)[len(st) // 2], "cpu_serial_ms_all": st,
                   "cpu_w6_ms": sorted(wt)[len(wt) // 2], "cpu_w6_ms_all": wt,
                   "gpu_status_ok": sum(x[0] == "OK" for x in gres),
                   "results_equal_gpu_serial": g_ok == sres, "results_equal_w6_serial": wres == sres,
                   "digest_serial": _digest(sres)}
            res["rows"].append(row)
            print(f"perf p{p} n{n}: gpu {row['gpu_ms']['total_ms']:.1f} ms (kernel {row['gpu_ms']['kernel_ms']:.1f}) "
                  f"serial {row['cpu_serial_ms']:.0f} w6 {row['cpu_w6_ms']:.0f} equal {row['results_equal_gpu_serial']}",
                  flush=True)
        res.setdefault("w6_spawn_ms", {})[str(p)] = w6.spawn_ms
        res.setdefault("cold", {})[str(p)] = cold
        res.setdefault("setup", {})[str(p)] = g.setup
        w6.close()
        g.lib.g0_free()
    (out_dir / "perf.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    return res


def cold_main(lib, p):
    t0 = time.perf_counter()
    g = GH.G0(lib)
    t1 = time.perf_counter()
    g.upload(p)
    g.alloc(2016)
    t2 = time.perf_counter()
    subs = subsets(load_bundle())
    batch = _batch(subs[f"main_p{p}"][2], 2016)
    t3 = time.perf_counter()
    _, tm, _ = g.evaluate(batch)
    t4 = time.perf_counter()
    print(json.dumps({"p": p, "pairs": 2016, "init_ms": (t1 - t0) * 1000, "setup": g.setup,
                      "upload_alloc_ms": (t2 - t1) * 1000, "first_batch": tm, "first_batch_wall_ms": (t4 - t3) * 1000,
                      "cold_total_ms_excl_bundle_load": (t1 - t0 + t2 - t1 + t4 - t3) * 1000}))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    ap.add_argument("--no-perf", action="store_true")
    ap.add_argument("--cold", nargs=2)
    a = ap.parse_args()
    if a.cold:
        cold_main(a.cold[0], int(a.cold[1]))
        return
    out = Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    lib, arch, log = GH.build(out / "build")
    (out / "env.json").write_text(json.dumps(env(lib, arch, log), indent=1), encoding="utf-8")
    subs = subsets(load_bundle())
    g = GH.G0(lib)
    print("device", g.device, g.setup, flush=True)
    correctness(g, out, subs)
    g.lib.g0_free()
    del g
    if not a.no_perf:
        perf(lib, out, subs)
    print("finished", flush=True)


if __name__ == "__main__":
    main()
