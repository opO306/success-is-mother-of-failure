"""Immutable stage folders for same-basis investigations; fresh worker per R."""
from __future__ import annotations

import argparse
import hashlib
import importlib.machinery
import importlib.util
import json
import multiprocessing as mp
import platform
import subprocess
import sys
import time
import traceback
from pathlib import Path


def original_module():
    path = "docs/active/h2_static_pilot_v2/solver_executed.py.txt"
    loader = importlib.machinery.SourceFileLoader("h2_archived_solver", path)
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def worker(job, output, stage):
    import resource
    from .core import ao_data, inspect_path, coordinate_equivalence, symmetry
    try:
        basis, r = job["basis"], job["R"]
        mol, s, h, eri = ao_data(basis, r)
        row = dict(basis=basis, R_bohr=r, paths=[], AO_symmetry=symmetry(eri),
                   AO_h_asymmetry=float(abs(h-h.T).max()), AO_s_asymmetry=float(abs(s-s.T).max()))
        if stage in ("controls", "reproduce"):
            try:
                old = original_module().solve([[0, 0, -r/2], [0, 0, r/2]], basis)
                row["original"] = dict(accepted=True, energy=old["total_energy_hartree"])
            except Exception as exc:
                row["original"] = dict(accepted=False, error=repr(exc), traceback=traceback.format_exc())
        if stage == "reproduce":
            paths, backends = ["symmetric"], ["original_outcore"]
        elif stage == "curve":
            paths, backends = [job["path"]], [job["backend"]]
        else:
            paths, backends = ["symmetric", "cholesky", "generalized_h"], ["original_outcore", "common_ao_incore"]
        coord = {}
        for path in paths:
            for backend in backends:
                artifact = str(Path(output).with_name(Path(output).stem+"_"+path+"_"+backend+".npz")) if stage == "curve" else None
                record, c = inspect_path(mol, s, h, eri, path, backend, artifact=artifact)
                record.update(kind="curve", basis=basis, R_bohr=r, electrons=2, sector="singlet")
                row["paths"].append(record)
                coord[path] = c
        row["coordinate_equivalence"] = {p:coordinate_equivalence(s, coord["symmetric"], c)
                                            for p,c in coord.items()} if "symmetric" in coord else {}
        row["process_peak_rss_bytes"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
    except Exception as exc:
        row = dict(job=job, status="IMPLEMENTATION_ERROR_PRESERVED", error=repr(exc), traceback=traceback.format_exc())
    Path(output).write_text(json.dumps(row, indent=2, allow_nan=False)+"\n", encoding="utf-8")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--stage", required=True, choices=("controls", "reproduce", "compare", "curve"))
    p.add_argument("--output", required=True)
    p.add_argument("--selection")
    args = p.parse_args()
    root = Path(args.output)
    root.mkdir(parents=True, exist_ok=False)
    protocol_path = Path(__file__).with_name("protocol.json")
    spec = json.loads(protocol_path.read_text())
    parent = json.loads(Path(spec["parent_protocol"]).read_text())
    sources = {str(x):hashlib.sha256(x.read_bytes()).hexdigest() for x in Path(__file__).parent.glob("*") if x.is_file()}
    protected = {str(x):hashlib.sha256(x.read_bytes()).hexdigest() for x in Path("electronic_pilot").glob("*.py")}
    protected.update({str(x):hashlib.sha256(x.read_bytes()).hexdigest() for x in Path("docs/active/h2_static_pilot_v2").iterdir() if x.is_file()})
    seal = dict(protocol=spec, parent_protocol=parent, source_sha256=sources, protected_sha256=protected,
                archived_source_sha256=hashlib.sha256(Path(spec["parent_executed_source"]).read_bytes()).hexdigest(),
                git_start=subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
                stage=args.stage, python=sys.version, platform=platform.platform(),
                packages=subprocess.check_output([sys.executable, "-m", "pip", "freeze"], text=True))
    if args.stage == "curve":
        selection = json.loads(Path(args.selection).read_text())
        seal["selection"] = selection
        seal["selection_sha256"] = hashlib.sha256(Path(args.selection).read_bytes()).hexdigest()
        jobs = [dict(basis="cc-pVQZ", R=r, path=selection["path"], backend=selection["backend"]) for r in parent["R_grid_bohr"]]
    else:
        panel = spec["controls" if args.stage == "controls" else "reproduction"]
        jobs = [dict(basis=b, R=r) for b,grid in panel.items() for r in grid]
    from pyscf import gto
    seal["hydrogen_basis_data"] = {b:gto.basis.load(b,"H") for b in parent["bases"]}
    (root/"seal.json").write_text(json.dumps(seal, indent=2)+"\n", encoding="utf-8")
    rows, started = [], time.perf_counter()
    for k,job in enumerate(jobs):
        output = root/f"point_{k:03d}.json"
        process = mp.get_context("spawn").Process(target=worker, args=(job,str(output),args.stage))
        process.start()
        process.join()
        if process.exitcode != 0 or not output.exists():
            raise RuntimeError(f"worker exit {process.exitcode}; no retry")
        row = json.loads(output.read_text())
        rows.append(row)
        (root/"results.json").write_text(json.dumps(dict(rows=rows, wall_seconds=time.perf_counter()-started), indent=2)+"\n", encoding="utf-8")
        print(k+1,len(jobs),job,[(x["path"],x["backend"],x["accepted"],x["failure_stage"]) for x in row.get("paths",[])],flush=True)
        if row.get("status") == "IMPLEMENTATION_ERROR_PRESERVED":
            raise RuntimeError("implementation error; stop and diagnose")


if __name__ == "__main__":
    main()
