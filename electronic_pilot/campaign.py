"""Sequential fresh-process campaign, with an immutable pre-run input seal."""
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
from pathlib import Path


def worker(job, output):
    import resource
    from electronic_pilot.solver import solve, atom_energy
    try:
        if job["kind"] == "atom":
            start = time.perf_counter()
            row = dict(kind="atom", basis=job["basis"],
                       energy_hartree=atom_energy(job["basis"], job.get("ghost_distance")),
                       ghost_distance=job.get("ghost_distance"),
                       wall_seconds=time.perf_counter()-start)
        else:
            r = job["R"]
            row = solve([[0, 0, -r/2], [0, 0, r/2]], job["basis"],
                        crosscheck=job.get("crosscheck", False), artifact=job["artifact"])
            row["kind"] = "curve"
        row["process_peak_rss_bytes"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
        row["memory_scope"] = "fresh Linux worker process high-water RSS; imports/solve/artifact included"
    except Exception as exc:
        row = dict(status="FAILED_PRESERVED", job=job, error=repr(exc), traceback=traceback.format_exc())
    Path(output).write_text(json.dumps(row, indent=2, allow_nan=False)+"\n", encoding="utf-8")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--protocol", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--sanity", action="store_true")
    args = p.parse_args()
    root = Path(args.output)
    root.mkdir(parents=True, exist_ok=False)
    spec = json.loads(Path(args.protocol).read_text(encoding="utf-8"))
    sources = {str(x): hashlib.sha256(x.read_bytes()).hexdigest()
               for x in Path(__file__).parent.glob("*.py")}
    from pyscf import gto
    basis = {b: gto.basis.load(b, "H") for b in spec["bases"]}
    seal = dict(protocol=spec, protocol_sha256=hashlib.sha256(Path(args.protocol).read_bytes()).hexdigest(),
                sources=sources, hydrogen_basis_data=basis,
                packages=subprocess.check_output([sys.executable, "-m", "pip", "freeze"], text=True),
                python=sys.version, platform=platform.platform(), cpu=platform.processor(),
                git_start=subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
                mode="sanity" if args.sanity else "full", utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    (root/"seal.json").write_text(json.dumps(seal, indent=2)+"\n", encoding="utf-8")
    jobs = []
    grid = spec["sanity_R_bohr"] if args.sanity else spec["R_grid_bohr"]
    for b in spec["bases"]:
        jobs.append(dict(kind="atom", basis=b))
        if not args.sanity:
            for r in spec["ghost_R_bohr"]:
                jobs.append(dict(kind="atom", basis=b, ghost_distance=r))
        for r in grid:
            jobs.append(dict(kind="curve", basis=b, R=r, crosscheck=r in spec["crosscheck_R_bohr"],
                             artifact=str(root/f"{b}_{r:g}.npz")))
    started = time.perf_counter()
    rows = []
    for k, job in enumerate(jobs):
        out = root/f"point_{k:04d}.json"
        process = mp.get_context("spawn").Process(target=worker, args=(job, str(out)))
        start = time.perf_counter()
        process.start()
        process.join()
        if process.exitcode != 0 or not out.exists():
            raise RuntimeError(f"STOP: worker {k} exit={process.exitcode}; logs retained")
        row = json.loads(out.read_text(encoding="utf-8"))
        row["worker_wall_with_startup_seconds"] = time.perf_counter()-start
        rows.append(row)
        (root/"results.json").write_text(json.dumps(dict(seal_sha256=hashlib.sha256((root/"seal.json").read_bytes()).hexdigest(),
                                                       rows=rows, wall_seconds=time.perf_counter()-started), indent=2)+"\n", encoding="utf-8")
        print(k+1, "/", len(jobs), job["basis"], job.get("R", "atom"), row.get("total_energy_hartree", row.get("energy_hartree")), flush=True)
        if row.get("status") == "FAILED_PRESERVED" and not spec.get("continue_independent_points_after_refusal", False):
            raise RuntimeError(f"STOP: failed point {k}; no automatic retry")


if __name__ == "__main__":
    main()
