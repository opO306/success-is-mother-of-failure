"""Independent full-product action, sharing saved AO/transformed integrals.

No matrix-builder import. This is an author assembly check, not AO audit.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


def action(h, g, vector, energy, electrons, sector):
    m = len(h)
    if electrons == 1:
        if len(vector) != m:
            raise ValueError("invalid one-electron dimension")
        wave = vector.astype(np.longdouble)
        applied = h@wave
        parity = 0.0
    else:
        wave = np.zeros((m, m), dtype=np.longdouble)
        k = 0
        for i in range(m):
            for j in range(i if sector == "singlet" else i+1, m):
                value = np.longdouble(vector[k])
                if i == j:
                    wave[i, j] = value
                else:
                    wave[i, j] = value/np.sqrt(np.longdouble(2))
                    wave[j, i] = wave[i, j]*(1 if sector == "singlet" else -1)
                k += 1
        if k != len(vector):
            raise ValueError("invalid two-electron dimension")
        applied = h@wave+wave@h.T+np.einsum("acbd,cd->ab", g, wave, optimize=False)
        parity = float(np.max(np.abs(wave.T-(1 if sector == "singlet" else -1)*wave)))
    residual = applied-np.longdouble(energy)*wave
    return dict(product_residual_l2=float(np.sqrt(np.sum(residual*residual))),
                norm_error=float(abs(np.sum(wave*wave)-1)), exchange_parity_error=parity,
                rayleigh_hartree=float(np.sum(wave*applied)))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--capture", required=True)
    p.add_argument("--output", required=True)
    args = p.parse_args()
    root = Path(args.capture)
    spec = json.loads((root/"seal.json").read_text(encoding="utf-8"))["protocol"]
    rows = json.loads((root/"results.json").read_text(encoding="utf-8"))["rows"]
    checks = []
    for row in rows:
        path = root/row["case_key"]/"matrices.npz"
        record = dict(case_key=row["case_key"], accepted=row["accepted"],
                      artifact_hash_match=hashlib.sha256(path.read_bytes()).hexdigest() == row["artifact_sha256"])
        if row["accepted"]:
            with np.load(path) as data:
                record.update(action(data["h"], data["eri"], data["vector"], row["electronic_energy_hartree"], row["electrons"], row["sector"]))
                record["C_min_singular_value"] = float(np.linalg.svd(data["c"], compute_uv=False)[-1])
            record["passed"] = record["artifact_hash_match"] and record["C_min_singular_value"] > 0 and record["product_residual_l2"] <= spec["residual_tolerance"] and record["norm_error"] <= spec["norm_tolerance"] and record["exchange_parity_error"] <= spec["norm_tolerance"] and abs(record["rayleigh_hartree"]-row["electronic_energy_hartree"]) <= spec["control_energy_tolerance"]
        else:
            record["passed"] = record["artifact_hash_match"] and row["electronic_energy_hartree"] is None and row["total_energy_hartree"] is None
        checks.append(record)
    with Path(args.output).open("x", encoding="utf-8") as f:
        json.dump(dict(status="PASS" if all(x["passed"] for x in checks) else "FAIL", rows=checks,
                       source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()), f, indent=2)
    print("action checks", len(checks), all(x["passed"] for x in checks))


if __name__ == "__main__":
    main()
