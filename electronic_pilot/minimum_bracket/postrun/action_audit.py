"""Independent full-product Hamiltonian action, no singlet assembly imports.

This shares the saved integrals. It checks assembly/vector correspondence,
not AO accuracy, external audit approval, or a formally certified lowest root.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


def action(h, g, vector, energy):
    n = len(h)
    i, j = np.triu_indices(n)
    if len(vector) != len(i):
        raise ValueError("full singlet vector dimension mismatch")
    wave = np.zeros((n, n), dtype=np.longdouble)
    for coefficient, a, b in zip(vector, i, j):
        if a == b:
            wave[a, b] = coefficient
        else:
            wave[a, b] = wave[b, a] = np.longdouble(coefficient)/np.sqrt(np.longdouble(2))
    applied = h@wave+wave@h.T+np.einsum("acbd,cd->ab", g, wave, optimize=False)
    residual = applied-np.longdouble(energy)*wave
    return dict(full_product_residual_l2=float(np.sqrt(np.sum(residual*residual))),
                wave_norm_error=float(abs(np.sum(wave*wave)-1)),
                rayleigh_energy_hartree=float(np.sum(wave*applied)),
                full_product_dimension=n*n, singlet_vector_dimension=len(vector))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--stages", nargs="+", required=True)
    p.add_argument("--output", required=True)
    args = p.parse_args()
    rows = []
    for stage in args.stages:
        root = Path(stage)
        seal = json.loads((root/"seal.json").read_text())
        for result_file in sorted(root.glob("point_*/result.json")):
            row = json.loads(result_file.read_text())
            artifact = result_file.with_name("matrices.npz")
            digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
            record = dict(stage=root.name, R_bohr=row["R_bohr"],
                          artifact_hash_match=digest == row["artifact_sha256"], accepted=row["accepted"])
            if row["accepted"]:
                with np.load(artifact) as data:
                    record.update(action(data["h"], data["eri"], data["singlet_vector"], row["electronic_energy_hartree"]))
                    record["full_AO_dimension"] = len(data["s"])
                    record["C_min_singular_value"] = float(np.linalg.svd(data["c"], compute_uv=False)[-1])
                spec = seal["protocol"]
                record["passed"] = (record["artifact_hash_match"] and record["full_AO_dimension"] == 60
                                    and record["C_min_singular_value"] > 0
                                    and record["full_product_residual_l2"] <= spec["eigen_residual_max_l2_hartree"]
                                    and record["wave_norm_error"] <= spec["vector_norm_error_max"]
                                    and abs(record["rayleigh_energy_hartree"]-row["electronic_energy_hartree"]) <= spec["same_problem_energy_abs_hartree"])
            else:
                record["refusal_null_energy_preserved"] = row["electronic_energy_hartree"] is None and row["total_energy_hartree"] is None
                record["passed"] = record["artifact_hash_match"] and record["refusal_null_energy_preserved"]
            rows.append(record)
    result = dict(status="PASS" if all(x["passed"] for x in rows) else "FAIL", rows=rows,
                  source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  note="independent matrix-action formula on saved candidate integrals; author check, not external AO audit or certification")
    with Path(args.output).open("x", encoding="utf-8") as f:
        json.dump(result, f, indent=2, allow_nan=False)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
