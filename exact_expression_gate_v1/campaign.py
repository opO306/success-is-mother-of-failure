"""Run the sealed Exact Expression Gate V1.

    python -m exact_expression_gate_v1.campaign --out runs/exact_expression_gate_v1_<date> [--quick] [--workers 6]

Every job (scenario, path, workload) runs in its own fresh process and writes <scenario>__<path>__<workload>.json
as soon as it finishes; a failure writes .ERROR.txt and never stops the other jobs. A sealed (non-quick) run
refuses to start when the sealed sources differ from the committed ones.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import multiprocessing as mp
import platform
import subprocess
import sys
import time
import traceback
from fractions import Fraction as Q
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SEALED = ["exact_expression_gate_v1/" + f for f in
          ("__init__.py", "common.py", "dag.py", "stream.py", "paths.py", "campaign.py", "checker.py", "protocol.json")] + \
         ["exact_expression_gate_v0/lang_iv.py", "a_reference/ar2_lang2024.py"]


def lf_sha256(path):
    return hashlib.sha256(Path(path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def q3(*xs):
    return tuple(Q(x) for x in xs)


def scenarios():
    from .common import MASS, DT
    return {
        "F_free": ([q3(0, 0, 0)], [q3(14, 3, -2)]),
        "A2_bound": ([q3("-71/20", 0, 0), q3("71/20", 0, 0)], [q3(1, -3, 0), q3(-1, 3, 0)]),
        "A3_low": ([q3(0, 0, 0), q3(25, 0, 0), q3(0, 25, 0)], [q3(2, 1, 0), q3(-1, 2, 0), q3(-1, -3, 0)]),
        "A3_high": ([q3(0, 0, 0), q3("71/10", 0, 0), q3("71/20", "6149/1000", 0)],
                    [q3(3, 0, "1/2"), q3("-3/2", "13/5", 0), q3("-3/2", "-13/5", "-1/2")]),
        "H_halfway": ([(Q(1, 1 << 49) - DT / MASS, Q(0), Q(0))], [q3(1, 0, 0)]),
        "D_zero": ([q3(0, 0, 0), q3(0, 0, 0)], [q3(0, 0, 0), q3(0, 0, 0)]),
    }


PHYSICAL = ["F_free", "A2_bound", "A3_low", "A3_high"]
CONTROL = ["H_halfway", "D_zero"]
PATHS = ["A", "B", "C", "CS", "CX"]


def query_sets(proto, quick):
    if quick:
        return {"cold": [[3], [5]], "warm": [[3, 5]], "every": [[1, 2, 3, 4, 5]], "control": [[1]]}
    out = {}
    for w, spec in proto["workloads"].items():
        if "steps" in spec:
            a, b = spec["steps"]
            out[w] = [list(range(a, b + 1))]
        else:
            out[w] = spec["query_sets"]
    return out


def job_list():
    jobs = [(s, p, w) for s in PHYSICAL for p in PATHS for w in ("cold", "warm", "every")]
    jobs += [(s, p, "control") for s in CONTROL for p in PATHS]
    weight_s = {"A3_high": 3, "A3_low": 3, "A2_bound": 1, "F_free": 0.01, "H_halfway": 0.001, "D_zero": 0.001}

    def weight(j):
        s, p, w = j
        return weight_s[s] * (3 if (p, w) == ("C", "every") else (0.1 if w == "every" else 1))
    return sorted(jobs, key=weight, reverse=True)


def rss():
    try:
        import psutil
        mi = psutil.Process().memory_info()
        return mi.rss, getattr(mi, "peak_wset", None)
    except ImportError:
        return None, None


def peak_rss():
    cur, peak = rss()
    if peak is not None:
        return peak
    try:
        import resource
        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
    except ImportError:
        return cur


def run_job(args):
    name, path, workload, sets, grid, out, seal_hash, proto_hash = args
    from .paths import run_workload
    base, _ = rss()
    t0 = time.perf_counter()
    stem = f"{name}__{path}__{workload}"
    try:
        q0, p0 = scenarios()[name]
        rec = run_workload(path, q0, p0, sets, grid)
        doc = {"scenario": name, "path": path, "workload": workload, "seal_sha256": seal_hash,
               "protocol_sha256": proto_hash, "record": rec,
               "memory": {"rss_after_imports": base, "peak_rss": peak_rss()},
               "job_wall_s": time.perf_counter() - t0}
        Path(out, stem + ".json").write_text(json.dumps(doc, indent=0), encoding="utf-8")
        return f"done {stem} cpu={rec['total']['cpu_s']:.1f}s"
    except Exception:
        Path(out, stem + ".ERROR.txt").write_text(traceback.format_exc(), encoding="utf-8")
        return f"FAILED {stem}"


def git(*a):
    return subprocess.run(["git", *a], capture_output=True, text=True, cwd=ROOT).stdout.strip()


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--workers", type=int, default=6)
    a = ap.parse_args(argv)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    proto = json.loads((HERE / "protocol.json").read_text(encoding="utf-8"))
    dirty = git("status", "--porcelain", "--", *SEALED)
    if dirty and not a.quick:
        sys.exit(f"sealed sources differ from HEAD; refusing a sealed run:\n{dirty}")
    import mpmath
    try:
        import psutil
        psv = psutil.__version__
    except ImportError:
        psv = None
    sets = query_sets(proto, a.quick)
    seal = {"quick": a.quick, "git_head_at_start": git("rev-parse", "HEAD"), "sealed_sources_dirty": bool(dirty),
            "python": platform.python_version(), "mpmath": mpmath.__version__, "psutil": psv,
            "platform": platform.platform(), "processor": platform.processor(), "cpu_count": mp.cpu_count(),
            "workers": a.workers, "query_sets": sets,
            "source_sha256_lf": {s: lf_sha256(ROOT / s) for s in SEALED}}
    seal_text = json.dumps(seal, indent=1)
    (out / "execution_seal.json").write_text(seal_text, encoding="utf-8")
    seal_hash = hashlib.sha256(seal_text.encode()).hexdigest()
    proto_hash = lf_sha256(HERE / "protocol.json")
    jobs = [(s, p, w, sets[w], proto["precision_grid"], str(out), seal_hash, proto_hash) for s, p, w in job_list()]
    t0 = time.perf_counter()
    print(time.strftime("%H:%M:%S"), f"start {len(jobs)} jobs, {a.workers} workers", flush=True)
    with mp.get_context("spawn").Pool(a.workers, maxtasksperchild=1) as pool:
        for i, msg in enumerate(pool.imap_unordered(run_job, jobs, chunksize=1), 1):
            print(time.strftime("%H:%M:%S"), f"[{i}/{len(jobs)}] {msg} (elapsed {time.perf_counter() - t0:.0f}s)",
                  flush=True)
    (out / "campaign_done.json").write_text(json.dumps({"wall_s": time.perf_counter() - t0}), encoding="utf-8")


if __name__ == "__main__":
    main()
