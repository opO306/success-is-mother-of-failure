"""Campaign driver. Every run is a fresh python process; runs are sequential (no concurrency) so timings are not
shared-load measurements. Each run writes its own JSON at once (a partial campaign survives).

    python -m experiments.state_object_event_pilot_v0.campaign part_a --out DIR
    python -m experiments.state_object_event_pilot_v0.campaign part_b_stage1 --out DIR
    python -m experiments.state_object_event_pilot_v0.campaign part_b_stage2 --out DIR
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PKG = "experiments.state_object_event_pilot_v0"
REPS = 3

SEALED_A = ["experiments/state_object_event_pilot_v0/" + f for f in
            ("__init__.py", "world_retention.py", "object_port.py", "pair_state.py", "campaign.py", "protocol.json")] + \
           ["a_reference/c1b1_two_atom.py", "a_reference/ar2_lang2024.py", "a_numeric/profiles.py", "a_numeric/exp.py"]
SEALED_B = ["experiments/state_object_event_pilot_v0/" + f for f in
            ("__init__.py", "event_lineage.py", "derivative_certificate.py", "campaign.py", "protocol.json")] + \
           ["exact_expression_gate_v1/stream.py", "exact_expression_gate_v1/common.py", "exact_expression_gate_v0/lang_iv.py",
            "a_reference/ar2_lang2024.py", "a_reference/c1b1_energy_bound.py", "a_reference/c1b1_outer_bound.py",
            "a_reference/c1b1_outer_bootstrap.py"]


def lf_sha(path):
    return hashlib.sha256(Path(path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True).stdout.strip()


def seal(out, sources, extra):
    dirty = git("status", "--porcelain", "--", *sources)
    doc = {"head": git("rev-parse", "HEAD"), "sealed_sources_dirty": bool(dirty), "dirty_detail": dirty,
           "protocol_sha256_lf": lf_sha(HERE / "protocol.json"),
           "source_sha256_lf": {s: lf_sha(ROOT / s) for s in sources}, "python": sys.version,
           "started": time.strftime("%Y-%m-%d %H:%M:%S"), **extra}
    (out / "execution_seal.json").write_text(json.dumps(doc, indent=1), encoding="utf-8")
    return doc


def log(out, msg):
    line = time.strftime("%H:%M:%S ") + msg
    print(line, flush=True)
    with open(out / "campaign.log", "a", encoding="utf-8") as f:
        f.write(line + "\n")


def run_worker(out, module, args, name):
    path = out / f"{name}.json"
    if path.exists():
        log(out, f"skip existing {name}")
        return
    t = time.perf_counter()
    p = subprocess.run([sys.executable, "-m", f"{PKG}.{module}", *args, "--out", str(path)], cwd=ROOT,
                       capture_output=True, text=True)
    if p.returncode != 0:
        (out / f"{name}.ERROR.txt").write_text(p.stdout + "\n" + p.stderr, encoding="utf-8")
        log(out, f"ERROR {name} rc={p.returncode}")
    else:
        log(out, f"done {name} ({time.perf_counter() - t:.1f}s)")


def part_a_jobs():
    from .world_retention import CASES, ORIGINS
    jobs = []
    for case in CASES:
        modes = ["WORLD_ONLY", "OBSERVER_HISTORY", "PORT"] + (["PAIR"] if case == "A2_sym" else [])
        for mode in modes:
            jobs.append((case, mode))
    return jobs


def part_a(out):
    seal(out, SEALED_A, {"part": "A", "reps": REPS, "jobs": part_a_jobs()})
    log(out, f"PART A: {len(part_a_jobs())} (case, mode) x ({REPS} timing + 1 memory) runs, sequential")
    for rep in range(REPS):                          # interleaved: rep-major, so slow drift hits every mode alike
        for case, mode in part_a_jobs():
            run_worker(out, "world_retention", ["--case", case, "--mode", mode], f"A__{case}__{mode}__t{rep}")
    for case, mode in part_a_jobs():
        run_worker(out, "world_retention", ["--case", case, "--mode", mode, "--memory"], f"A__{case}__{mode}__mem")
    log(out, "PART A finished")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=["part_a", "part_b_stage1", "part_b_stage2"])
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    if a.what == "part_a":
        part_a(out)
    else:
        from . import campaign_b
        campaign_b.run(a.what, out)


if __name__ == "__main__":
    main()
