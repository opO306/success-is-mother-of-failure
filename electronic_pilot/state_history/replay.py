"""Sealed stored Hamiltonian/eigenstate environment reproduction only."""
import argparse
import hashlib
import json
import platform
import sys
from pathlib import Path

import numpy as np
import scipy

from .core import experiment, validate_input
from .checker import check


def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser();p.add_argument("--input",required=True);p.add_argument("--output",required=True)
    args=p.parse_args();root=Path(args.input);out=Path(args.output);out.mkdir(parents=True,exist_ok=False)
    manifest=json.loads((root/"manifest.json").read_text(encoding="utf-8"))
    if any(sha(root/name)!=v for name,v in manifest["files"].items()): raise ValueError("REFUSED: transferred input changed")
    sources={name:sha(Path(__file__).parent/name) for name in manifest["source_sha256"]}
    if sources!=manifest["source_sha256"]: raise ValueError("REFUSED: source mismatch")
    spec=manifest["protocol"];validate_input(spec["case"])
    with np.load(root/"eigenstates.npz") as z: data={k:z[k].copy() for k in z.files}
    arrays,summary=experiment(data["s"],data["h"],data["dipoles"],data["energies"],data["eigenvectors"],spec)
    data.update(arrays);summary["input"]=spec["case"];summary["checker"]=check(data,summary,spec)
    old=json.loads((root/"desktop_results.json").read_text(encoding="utf-8"))
    summary.update(status=summary["checker"]["status"],host=platform.node(),platform=platform.platform(),python=sys.version,
                   versions={"numpy":np.__version__,"scipy":scipy.__version__},source_sha256=sources,
                   input_manifest_sha256=sha(root/"manifest.json"),scope="SAVED_HAMILTONIAN_EIGENVECTORS_ENVIRONMENT_REPRODUCTION_NOT_PHYSICS_AUDIT",
                   desktop_dipole_difference_max=float(np.max(np.abs(np.array(summary["dipole_z_differences"])-old["dipole_z_differences"]))),
                   desktop_density_metric_difference_max=float(np.max(np.abs(np.array(summary["density_kernel_max_differences"])-old["density_kernel_max_differences"]))))
    np.savez_compressed(out/"experiment.npz",**data)
    with (out/"results.json").open("x",encoding="utf-8") as f:json.dump(summary,f,indent=2,allow_nan=False)
    print(json.dumps({k:summary[k] for k in ["status","host","desktop_dipole_difference_max","desktop_density_metric_difference_max"]},indent=2))


if __name__ == "__main__": main()
