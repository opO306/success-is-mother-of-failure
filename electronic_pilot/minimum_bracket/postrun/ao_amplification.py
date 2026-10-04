"""Post-diagnostic scalar contraction of saved independent AO, no energy.

Reuse the historical separately tested MPFR antisymmetry diagnostic only;
never call its AO generator, coordinates, matrix builder, worker or solver.
No correction is applied to any candidate matrix.
"""
import argparse
import hashlib
import json
import time
from pathlib import Path

import numpy as np


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--points", nargs="+", required=True)
    p.add_argument("--output", required=True)
    args = p.parse_args()
    output = Path(args.output)
    output.mkdir(exist_ok=False)
    paths = [Path(x) for x in args.points]
    old_source = Path("electronic_pilot/numerical_cause/high_precision.py")
    seal = dict(scope="post-diagnostic worst saved coupling; no new AO, no eigensolve, no energy, no matrix correction",
                decimal_digits=[60, 80],
                source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                historical_MP_diagnostic_sha256=hashlib.sha256(old_source.read_bytes()).hexdigest(),
                input_artifact_sha256={str(x): hashlib.sha256((x/"matrices.npz").read_bytes()).hexdigest() for x in paths})
    with (output/"seal.json").open("x", encoding="utf-8") as f:
        json.dump(seal, f, indent=2)
    from electronic_pilot.numerical_cause.high_precision import propagated_asymmetry
    import gmpy2 as gp
    rows, started = [], time.perf_counter()
    for point in paths:
        row = json.loads((point/"result.json").read_text())
        with np.load(point/"matrices.npz") as data:
            s, h, g, c = data["s"], data["h_ao"], data["eri_ao"], data["c"]
            eri = data["eri"]
            i, j = np.triu_indices(len(s))
            # Since raw h is exactly symmetric for these records, it cannot
            # contribute an antisymmetric coupling. Scan the Coulomb part.
            if np.max(np.abs(h-h.T)) != 0:
                raise ValueError("this narrow scan requires symmetric independent h AO")
            norm = np.sqrt(np.longdouble(2)*(1+(i == j).astype(int)))
            matrix = (eri[i[:,None], i[None,:], j[:,None], j[None,:]]
                      + eri[i[:,None], j[None,:], j[:,None], i[None,:]]
                      + eri[j[:,None], i[None,:], i[:,None], j[None,:]]
                      + eri[j[:,None], j[None,:], i[:,None], i[None,:]])
            matrix /= norm[:,None]*norm[None,:]
            difference = matrix-matrix.T
            a, b = np.unravel_index(np.abs(difference).argmax(), difference.shape)
            measured = float(difference[a,b])
            if abs(abs(measured)-row["singlet_asymmetry"]) > 1e-13:
                raise ValueError("independent worst-coupling scan disagrees with saved diagnostic")
            result = dict(coordinate_path=row.get("coordinate_path", "cholesky"), R_bohr=row["R_bohr"],
                          pair_a=[int(i[a]),int(j[a])], pair_b=[int(i[b]),int(j[b])],
                          measured_signed_asymmetry=measured, energy_calculated=False, precision={})
            for digits in (60, 80):
                value = propagated_asymmetry(s,h,g,c,result["pair_a"],result["pair_b"],digits,False)
                with gp.context(gp.get_context(),precision=value["bits"]):
                    remainder = str(gp.mpfr(measured)-gp.mpfr(value["total"]))
                result["precision"][str(digits)] = dict(**value, measured_minus_propagated=remainder)
                print(result["coordinate_path"],digits,value["total"],flush=True)
            rows.append(result)
    with (output/"results.json").open("x", encoding="utf-8") as f:
        json.dump(dict(rows=rows, wall_seconds=time.perf_counter()-started,
                       interpretation="binary64 independent AO component at fixed C; scalar multiprecision is NOT higher-precision AO or a full matrix bound"),f,indent=2)


if __name__ == "__main__":
    main()
