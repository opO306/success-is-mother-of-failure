"""Same evaluator on sealed saved AO input; no new backend AO acquisition."""
import argparse
import hashlib
import json
import platform
import sys
from pathlib import Path

import numpy as np
import scipy

from .evaluator import solve_integrals


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True)
    p.add_argument("--output", required=True)
    args = p.parse_args()
    root, out = Path(args.input), Path(args.output)
    out.mkdir(parents=True, exist_ok=False)
    manifest = json.loads((root/"manifest.json").read_text(encoding="utf-8"))
    if any(sha(root/name) != digest for name, digest in manifest["files"].items()):
        raise ValueError("REFUSED: transferred input hash mismatch")
    here = Path(__file__).parent
    actual = {name: sha(here/name) for name in manifest["source_sha256"]}
    if actual != manifest["source_sha256"]:
        raise ValueError("REFUSED: same-source mismatch")
    records = []
    for key in manifest["keys"]:
        old = json.loads((root/(key+".json")).read_text(encoding="utf-8"))
        with np.load(root/(key+".npz")) as data:
            row = solve_integrals(old["input"], data["s"], data["h_ao"], data["eri_ao"], manifest["protocol"], out/(key+".npz"))
        difference = abs(row["total_energy_hartree"]-old["total_energy_hartree"]) if row["accepted"] and old["accepted"] else None
        records.append(dict(case_key=key, row=row, desktop_energy_difference=difference,
                            passed=difference is not None and difference <= manifest["protocol"]["dual_replay_tolerance"] and row["AO_sha256"] == old["AO_sha256"]))
    result = dict(scope="PARTIAL_SAVED_AO_ENVIRONMENT_REPLAY_NOT_FRESH_AO_NOT_PHYSICS_AUDIT",
                  host=platform.node(), python=sys.version, platform=platform.platform(),
                  versions={"numpy": np.__version__, "scipy": scipy.__version__},
                  longdouble_nmant=np.finfo(np.longdouble).nmant, source_sha256=actual,
                  input_manifest_sha256=sha(root/"manifest.json"), rows=records,
                  status="PASS" if all(x["passed"] for x in records) else "FAIL")
    with (out/"results.json").open("x", encoding="utf-8") as f:
        json.dump(result, f, indent=2, allow_nan=False)
    print(json.dumps({k: v for k, v in result.items() if k != "rows"}, indent=2))


if __name__ == "__main__":
    main()
