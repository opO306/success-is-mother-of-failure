"""GPU_PAIR_VECTOR_V1 campaign (protocol.json): build -> gate A + B correctness on every bundle state in 12 layouts ->
performance (CPU_W6_E2, GPU_A_PAIR_VECTOR, GPU_B_ATOM_REDUCE) on the sealed combinations -> block sweep.

    python -m experiments.gpu_pair_vector_v1.campaign --out DIR [--no-perf] [--cold LIB P]
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
from fractions import Fraction as Q
from pathlib import Path

from experiments.gpu_force_feasibility_v1.dyadic import decode_iv
from experiments.gpu_pair_vector_v1 import pv_host as PH

ROOT = Path(__file__).resolve().parents[2]
PROTO = json.loads((Path(__file__).with_name("protocol.json")).read_text(encoding="utf-8"))
BUNDLE = ROOT / "docs/active/gpu_pair_vector_v1/states.json.gz"
BUNDLE_SHA = (ROOT / "docs/active/gpu_pair_vector_v1/states.json.gz.sha256").read_text(encoding="utf-8").strip()
LAYOUTS = [(b, g) for b in (32, 64, 128, 256) for g in (1, 7, 0)]
SEALED = [f"experiments/gpu_pair_vector_v1/{f}" for f in
          ("protocol.json", "samples.py", "pv1.cu", "pv_host.py", "campaign.py", "checker.py", "analyze.py")] + \
         ["docs/active/gpu_pair_vector_v1/states.json.gz", "docs/active/gpu_pair_vector_v1/states.json.gz.sha256",
          "experiments/gpu_force_feasibility_v1/g0.cu", "experiments/gpu_force_feasibility_v1/gpu_host.py",
          "experiments/gpu_force_feasibility_v1/compile_plan.py", "experiments/gpu_force_feasibility_v1/dyadic.py",
          "experiments/rewrite_pilot_a3/rwforce.py", "exact_expression_gate_v1/stream.py",
          "exact_expression_gate_v1/common.py", "experiments/e2_pair_parallel_v1/run.py", "a_numeric_native/harness.py"]


def git(*a):
    return subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
                          errors="replace").stdout.strip()


def lf(p):
    return hashlib.sha256(Path(p).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def load_bundle():
    raw = BUNDLE.read_bytes()
    if hashlib.sha256(raw).hexdigest() != BUNDLE_SHA:
        raise SystemExit("state bundle hash differs from the sealed value")
    return json.loads(gzip.decompress(raw))


def all_states(b):
    return [("main", x) for x in b["main"]] + [("test", x) for x in b["test_only"]]


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
            "ptxas": [ln.strip() for ln in log.splitlines() if "Used" in ln and "registers" in ln][:8]}


def run_state(pv, out_dir, kind, st, block, grid, fault=0, g0fault=0, wl=16, tamper=None):
    """One gate-A+B run of one state; raw device words saved. tamper (tests only): drop_pair, swap_pairs, swap_atoms,
    p_altered."""
    p_state = st["p"]
    p_dev = 128 if tamper == "p_altered" else p_state            # fault 13
    if pv.p != p_dev:
        pv.upload(p_dev)
    N = st["N"]
    P = N * (N - 1) // 2
    q = [[decode_iv(e) for e in row] for row in st["q"]]
    pos = PH.encode_positions(q)
    t0 = time.perf_counter()
    full, comp, atoms, tm = pv.run_state(pos, N, 1 | 4, block, grid, fault, g0fault, wl)
    wall = (time.perf_counter() - t0) * 1000
    echo = bytes(pv.echo_positions())
    rf, ra = bytes(full), bytes(atoms)
    wf, wa = PH.WORDS_FULL * 4, PH.WORDS_ATOM * 4
    if tamper == "drop_pair":                                      # fault 7
        rf = rf[:-wf]
    if tamper == "swap_pairs" and P >= 2:                          # fault 8
        rf = rf[wf:2 * wf] + rf[:wf] + rf[2 * wf:]
    if tamper == "swap_atoms":                                     # fault 12
        rf, ra = rf, ra[3 * wa:6 * wa] + ra[:3 * wa] + ra[6 * wa:]
    meta = {"state_kind": kind, "state_id": st["id"], "role": st.get("role", "MAIN"), "N": N, "p": p_state,
            "p_uploaded": p_dev, "block": block, "grid_arg": grid, "fault": fault, "g0fault": g0fault, "work_limbs": wl,
            "tamper": tamper, "device": pv.device, "plan": PH.plan_record(block, grid, N, "CANONICAL_PER_ATOM_COMPONENT", p_dev),
            "timing_ms": {**tm, "wall_ms": wall}, "memory": pv.mem,
            "full_sha256": hashlib.sha256(rf).hexdigest(), "atoms_sha256": hashlib.sha256(ra).hexdigest(),
            "positions_sha256": hashlib.sha256(bytes(pos)).hexdigest(), "echo_sha256": hashlib.sha256(echo).hexdigest()}
    stem = f"{kind}{st['id']}__b{block}_g{grid}" + (f"__f{fault}" if fault else "") + (f"__g{g0fault}" if g0fault else "") + \
        (f"__{tamper}" if tamper else "")
    d = out_dir / "runs"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{stem}.full.gz").write_bytes(gzip.compress(rf, mtime=0))
    (d / f"{stem}.atoms.gz").write_bytes(gzip.compress(ra, mtime=0))
    (d / f"{stem}.echo.gz").write_bytes(gzip.compress(echo, mtime=0))
    (d / f"{stem}.json").write_text(json.dumps(meta), encoding="utf-8")
    return meta


def correctness(pv, out_dir, states, layouts=LAYOUTS, **kw):
    metas = []
    for kind, st in states:
        lay = layouts if kind == "main" else [(128, 0)]
        for block, grid in lay:
            m = run_state(pv, out_dir, kind, st, block, grid, **kw)
            metas.append(m)
        t = m["timing_ms"]
        print(f"state {kind}{st['id']} N{st['N']} p{st['p']}: {len(lay)} layouts; last k_G {t['k_G_ms']:.1f} ms", flush=True)
    return metas


# ---------------------------------------------------------------------------
# performance
# ---------------------------------------------------------------------------
class W6E2:
    """The validated E2 pair path: unchanged e2_pair_parallel_v1.run._pair_worker processes, canonical blocks, the
    main reducing in canonical order exactly as run_parallel's forces()."""
    CPUS = (1, 2, 3, 4, 5, 0)

    def __init__(self, N, p):
        import multiprocessing as mp

        import psutil

        from experiments.e2_pair_parallel_v1 import run as E2
        from experiments.multiatom_parallel_v1 import scenarios as SC
        try:
            psutil.Process().cpu_affinity([0])
        except Exception:
            pass
        ctx = mp.get_context("spawn")
        self.blocks = SC.pair_blocks(N, len(self.CPUS))
        t0 = time.perf_counter()
        self.pipes = [ctx.Pipe() for _ in self.CPUS]
        self.procs = [ctx.Process(target=E2._pair_worker, args=(b, c, p, self.blocks[w], "rw:R1+R2"))
                      for w, ((a, b), c) in enumerate(zip(self.pipes, self.CPUS))]
        for pr in self.procs:
            pr.start()
        self.hello = [a.recv() for a, b in self.pipes]
        self.spawn_ms = (time.perf_counter() - t0) * 1000
        self.N, self.p = N, p

    def forces(self, q_raw):
        from mpmath import iv

        import exact_expression_gate_v0.lang_iv as LI
        from exact_expression_gate_v1 import common as K
        iv.prec = self.p
        zero, make, n = LI.c(Q(0)), iv.make_mpf, self.N
        t0 = time.perf_counter()
        for a, b in self.pipes:
            a.send(q_raw)
        F = [[zero] * 3 for _ in range(n)]
        for bidx, (a, b) in enumerate(self.pipes):
            res = a.recv()
            for (i, j), (st, tt) in zip(self.blocks[bidx], res):
                if st != K.PROVEN:
                    raise K.DomainStop(st, None)
                for k in range(3):
                    t = make(tt[k])
                    F[j][k] = F[j][k] + t
                    F[i][k] = F[i][k] - t
        return (time.perf_counter() - t0) * 1000, [[x._mpi_ for x in r] for r in F]

    def close(self):
        for a, b in self.pipes:
            a.send(None)
        for a, b in self.pipes:
            a.recv()
        for pr in self.procs:
            pr.join(timeout=30)


def perf_state(b, comb):
    """Position intervals for a sealed performance combination."""
    from mpmath import iv

    import exact_expression_gate_v0.lang_iv as LI
    from experiments.multiatom_parallel_v1 import scenarios as SC
    N, p = comb["N"], comb["p"]
    if comb["state"].startswith("bundle"):
        step = int(comb["state"].split("step ")[1])
        st = next(x for x in b["main"] if (x["N"], x["p"], x["step"]) == (N, p, step))
        return [[decode_iv(e) for e in row] for row in st["q"]], f"bundle state {st['id']}"
    iv.prec = p
    q0, _ = SC.initial(N)
    return [[LI.c(x)._mpi_ for x in row] for row in q0], "FCC_N initial state lifted at p"


def _med(xs):
    return sorted(xs)[len(xs) // 2]


def gpu_paths(pv, q, N, p, block=128, reps=5):
    if pv.p != p:
        pv.upload(p)
    P = N * (N - 1) // 2
    A, B, Fa, Fb = [], [], None, None
    for r in range(reps + 1):
        t0 = time.perf_counter()
        pos = PH.encode_positions(q)
        t1 = time.perf_counter()
        _, comp, _, tm = pv.run_state(pos, N, 2, block)
        t2 = time.perf_counter()
        pairs = PH.decode_compact(comp, P)
        t3 = time.perf_counter()
        st, first, F = PH.host_reduce(N, pairs, p)
        t4 = time.perf_counter()
        A.append({**tm, "encode_ms": (t1 - t0) * 1000, "device_call_ms": (t2 - t1) * 1000, "decode_ms": (t3 - t2) * 1000,
                  "host_reduce_ms": (t4 - t3) * 1000, "total_to_pairs_ms": (t3 - t0) * 1000,
                  "total_to_forces_ms": (t4 - t0) * 1000})
        Fa = F
        t0 = time.perf_counter()
        pos = PH.encode_positions(q)
        t1 = time.perf_counter()
        _, _, atoms, tm = pv.run_state(pos, N, 4, block)
        t2 = time.perf_counter()
        dec = PH.decode_atoms(atoms, N)
        t3 = time.perf_counter()
        B.append({**tm, "encode_ms": (t1 - t0) * 1000, "device_call_ms": (t2 - t1) * 1000, "decode_ms": (t3 - t2) * 1000,
                  "total_ms": (t3 - t0) * 1000})
        Fb = [[dec[3 * a + k][4] for k in range(3)] for a in range(N)]
    A, B = A[1:], B[1:]
    return ({k: _med([x[k] for x in A]) for k in A[0]}, {k: _med([x[k] for x in B]) for k in B[0]},
            [x["total_to_forces_ms"] for x in A], [x["total_ms"] for x in B], Fa, Fb)


def perf(lib, out_dir, b, reps_cpu=3):
    res = {"label": "one force evaluation per state (no KDK)", "rows": [], "sweep": [], "memory_table": PH.memory_table()}
    pv = PH.PV(lib)
    for comb in PROTO["performance"]["combinations (sealed; information value over a full cartesian product)"]:
        N, p = comb["N"], comb["p"]
        q, src = perf_state(b, comb)
        a, bb, a_all, b_all, Fa, Fb = gpu_paths(pv, q, N, p)
        w6 = W6E2(N, p)
        wt, Fw = [], None
        for _ in range(reps_cpu):
            ms, Fw = w6.forces(q)
            wt.append(ms)
        w6.close()
        row = {**comb, "source": src, "pairs": N * (N - 1) // 2, "gpu_A": a, "gpu_B": bb, "gpu_A_all": a_all,
               "gpu_B_all": b_all, "cpu_w6_ms": _med(wt), "cpu_w6_all": wt, "w6_spawn_ms": w6.spawn_ms,
               "memory": pv.mem, "F_equal_A_W6": Fa == Fw, "F_equal_B_W6": Fb == Fw,
               "plan_A": PH.plan_record(128, 0, N, "NONE", p), "plan_B": PH.plan_record(128, 0, N, "CANONICAL_PER_ATOM_COMPONENT", p)}
        res["rows"].append(row)
        print(f"perf N{N} p{p}: W6 {row['cpu_w6_ms']:.0f} ms | A {a['total_to_forces_ms']:.1f} (decode {a['decode_ms']:.1f}, "
              f"host reduce {a['host_reduce_ms']:.1f}) | B {bb['total_ms']:.1f} (kernels {bb['k_dr2_ms'] + bb['k_G_ms'] + bb['k_J_ms'] + bb['k_reduce_ms']:.1f}) "
              f"| equal A {row['F_equal_A_W6']} B {row['F_equal_B_W6']}", flush=True)
        if N in (64, 128) and p == 109:
            outs = set()
            for block in (32, 64, 128, 256):
                pv.upload(p)
                ts, ats = [], None
                for r in range(6):
                    t0 = time.perf_counter()
                    _, _, atoms, tm = pv.run_state(PH.encode_positions(q), N, 4, block)
                    ts.append({**tm, "wall_ms": (time.perf_counter() - t0) * 1000})
                    ats = bytes(atoms)
                ts = ts[1:]
                outs.add(hashlib.sha256(ats).hexdigest())
                res["sweep"].append({"N": N, "p": p, "plan": PH.plan_record(block, 0, N, "CANONICAL_PER_ATOM_COMPONENT", p),
                                     "kernels_ms": _med([t["k_dr2_ms"] + t["k_G_ms"] + t["k_J_ms"] + t["k_reduce_ms"] for t in ts]),
                                     "k_G_ms": _med([t["k_G_ms"] for t in ts]), "k_reduce_ms": _med([t["k_reduce_ms"] for t in ts]),
                                     "wall_ms": _med([t["wall_ms"] for t in ts]), "atoms_sha256": hashlib.sha256(ats).hexdigest()})
            res["sweep"].append({"N": N, "p": p, "outputs_identical_across_blocks": len(outs) == 1})
    for p in (109, 163):
        r = subprocess.run([sys.executable, "-m", "experiments.gpu_pair_vector_v1.campaign", "--cold", str(lib), str(p)],
                           cwd=ROOT, capture_output=True, text=True)
        res.setdefault("cold", {})[str(p)] = json.loads(r.stdout.strip().splitlines()[-1]) if r.returncode == 0 else \
            {"error": r.stderr[-800:]}
    res["setup"] = pv.setup
    (out_dir / "perf.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    return res


def cold_main(lib, p):
    t0 = time.perf_counter()
    pv = PH.PV(lib)
    t1 = time.perf_counter()
    pv.upload(p)
    b = load_bundle()
    comb = {"N": 64, "p": p, "state": "FCC_N initial"} if p == 163 else {"N": 64, "p": p, "state": "bundle N=64 step 50"}
    q, _ = perf_state(b, comb)
    t2 = time.perf_counter()
    pos = PH.encode_positions(q)
    _, _, atoms, tm = pv.run_state(pos, 64, 4)
    PH.decode_atoms(atoms, 64)
    t3 = time.perf_counter()
    print(json.dumps({"p": p, "N": 64, "init_ms": (t1 - t0) * 1000, "setup": pv.setup, "mem": pv.mem,
                      "first_state_B_ms": (t3 - t2) * 1000, "first_state_timing": tm}))


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
    lib, arch, log = PH.build(out / "build")
    (out / "env.json").write_text(json.dumps(env(lib, arch, log), indent=1), encoding="utf-8")
    b = load_bundle()
    pv = PH.PV(lib)
    print("device", pv.device, flush=True)
    correctness(pv, out, all_states(b))
    pv.lib.pv_free()
    if not a.no_perf:
        perf(lib, out, b)
    print("finished", flush=True)


if __name__ == "__main__":
    main()
