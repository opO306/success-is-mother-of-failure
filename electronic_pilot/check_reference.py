"""Independent external-data comparison. Standard library only; no solver import.

Checks records, not wavefunctions or integral correctness. Numerical agreement
with the published calculation is not a formal certificate.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from decimal import Decimal as D
from pathlib import Path


def compare(results, protocol, reference):
    table = {D(x["R_bohr"]): x for x in reference}
    expected = {D(str(x)) for x in protocol["R_grid_bohr"]}
    if set(table) != expected:
        raise ValueError("reference coverage differs from sealed grid")
    curves, atoms, ghosts, refusals = {}, {}, [], {}
    for row in results["rows"]:
        if row.get("status") == "FAILED_PRESERVED":
            job = row["job"]
            if job["kind"] != "curve":
                raise ValueError("failed atomic reference; cannot compare")
            key = job["basis"], D(str(job["R"]))
            if key in refusals or key in curves:
                raise ValueError("duplicate refused point")
            refusals[key] = row
            continue
        b = row["basis"]
        if b not in protocol["bases"]:
            raise ValueError("unsupported basis in records")
        if row["kind"] == "atom":
            if row["ghost_distance"] is None:
                if b in atoms:
                    raise ValueError("duplicate atom")
                atoms[b] = D(str(row["energy_hartree"]))
            else:
                ghosts.append(row)
            continue
        r = D(str(row["R_bohr"]))
        key = b, r
        if key in curves or key in refusals:
            raise ValueError("duplicate curve point")
        if row["sector"] != "singlet" or row["electrons"] != 2:
            raise ValueError("wrong sector/electron count")
        for field in ("electronic_energy_hartree", "nuclear_repulsion_hartree", "total_energy_hartree", "eigen_residual_l2"):
            if not math.isfinite(row[field]):
                raise ValueError("nonfinite record")
        ee, nn, et = [D(str(row[x])) for x in ("electronic_energy_hartree", "nuclear_repulsion_hartree", "total_energy_hartree")]
        if r <= 0 or abs(nn-1/r) > D("5e-12") or abs(ee+nn-et) > D("5e-12"):
            raise ValueError("energy ownership/nuclear repulsion mismatch")
        if row["eigen_residual_l2"] > protocol["eigen_residual_max_l2_hartree"]:
            raise ValueError("solver convergence failure")
        curves[key] = row
    if set(atoms) != set(protocol["bases"]):
        raise ValueError("missing atomic reference")
    if set(curves) | set(refusals) != {(b, r) for b in protocol["bases"] for r in expected}:
        raise ValueError("incomplete curve")
    summaries, errors = {}, []
    for b in protocol["bases"]:
        rows = [curves[b, r] for r in sorted(expected) if (b,r) in curves]
        if not rows:
            raise ValueError("no supported points for basis")
        energies = [D(str(x["total_energy_hartree"])) for x in rows]
        k = min(range(len(rows)), key=energies.__getitem__)
        local = (0 < k < len(rows)-1 and energies[k] < energies[k-1] and energies[k] < energies[k+1])
        bracket = [rows[k-1]["R_bohr"], rows[k+1]["R_bohr"]] if local else None
        tail = [float(D(str(curves[b, D(str(r))]["total_energy_hartree"]))-2*atoms[b]) for r in (10,12,16,20)]
        es = [D(str(x["total_energy_hartree"]))-D(table[D(str(x["R_bohr"]))]["total_energy_hartree"]) for x in rows]
        for row, err in zip(rows, es):
            errors.append(dict(basis=b, R_bohr=row["R_bohr"], signed_error_hartree=float(err)))
        summaries[b] = dict(sampled_min_R_bohr=rows[k]["R_bohr"] if local else None,
                            sampled_min_total_hartree=float(energies[k]) if local else None,
                            lowest_computed_R_bohr=rows[k]["R_bohr"], lowest_computed_total_hartree=float(energies[k]),
                            computed_points=len(rows), expected_points=len(expected),
                            refused_R_bohr=[float(r) for bb,r in refusals if bb==b],
                            sampled_min_bracket_bohr=bracket,
                            P1_sampled_minimum=bool(local and energies[k]<2*atoms[b]),
                            P1_status="SAMPLED_MINIMUM_FOUND" if local and energies[k]<2*atoms[b] else "UNRESOLVED",
                            minimum_note="sampled interior point only" if local else "lowest available point is at computed support boundary; minimum location/depth unresolved",
                            binding_to_same_basis_atoms_hartree=float(2*atoms[b]-energies[k]) if local else None,
                            binding_to_exact_atoms_hartree=float(-1-energies[k]) if local else None,
                            twice_H_energy_hartree=float(2*atoms[b]),
                            twice_H_basis_error_hartree=float(2*atoms[b]+1),
                            tail_R_bohr=[10,12,16,20], tail_minus_same_basis_atoms_hartree=tail,
                            P2_tail_decreases=all(abs(a)>abs(z) for a,z in zip(tail,tail[1:])),
                            P2_fragment_tolerance_pass=abs(tail[-1])<=protocol["criteria"]["P2_fragment_abs_E20_minus_2EH_max_hartree"],
                            curve_max_abs_error_hartree=float(max(map(abs,es))),
                            curve_rms_error_hartree=math.sqrt(sum(float(x)**2 for x in es)/len(es)),
                            max_abs_error_R_bohr=rows[max(range(len(es)),key=lambda i:abs(es[i]))]["R_bohr"],
                            basis_size=rows[0]["basis_size"], singlet_dimension=rows[0]["singlet_dimension"],
                            total_solve_wall_seconds=sum(x["wall_seconds"] for x in rows),
                            max_process_peak_rss_bytes=max(x["process_peak_rss_bytes"] for x in rows),
                            max_residual_l2=max(x["eigen_residual_l2"] for x in rows))
    q = summaries[protocol["comparison_basis"]]
    criteria = protocol["criteria"]
    # These constants belong only to postprocessing, from the paper abstract/Table I.
    ref_min_R, ref_min_E = D("1.4011"), D("-1.1744759314002167")
    q["P3_curve_tolerance_pass"] = q["computed_points"]==q["expected_points"] and q["curve_max_abs_error_hartree"] <= criteria["P3_curve_max_abs_error_hartree"]
    q["P3_computed_subset_tolerance_pass"] = q["curve_max_abs_error_hartree"] <= criteria["P3_curve_max_abs_error_hartree"]
    q["sampled_min_location_difference_bohr"] = float(D(str(q["sampled_min_R_bohr"]))-ref_min_R) if q["P1_sampled_minimum"] else None
    q["binding_depth_difference_hartree"] = float(D(str(q["binding_to_exact_atoms_hartree"]))-(-1-ref_min_E)) if q["P1_sampled_minimum"] else None
    q["P3_min_location_tolerance_pass"] = (abs(q["sampled_min_location_difference_bohr"]) <= criteria["P3_sampled_min_location_abs_difference_bohr"]) if q["P1_sampled_minimum"] else None
    q["P3_depth_tolerance_pass"] = (abs(q["binding_depth_difference_hartree"]) <= criteria["P3_binding_depth_abs_error_hartree"]) if q["P1_sampled_minimum"] else None
    ghost_diagnostics = [dict(basis=x["basis"], R_bohr=x["ghost_distance"],
                              atom_energy_change_hartree=float(D(str(x["energy_hartree"]))-atoms[x["basis"]])) for x in ghosts]
    return dict(status="NUMERICALLY_COMPARED_NOT_CERTIFIED", summaries=summaries, errors=errors,
                refused_points=[dict(basis=b,R_bohr=float(r),error=x["error"]) for (b,r),x in refusals.items()],
                ghost_basis_diagnostics=ghost_diagnostics,
                reference_missing_explicit_uncertainty_R_bohr=[16,20],
                independence="published exponential explicitly-correlated calculation distinct from Gaussian integral/dense solver; shared-integral FCI is secondary only")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", required=True)
    parser.add_argument("--protocol", required=True)
    parser.add_argument("--reference", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    paths = {key: Path(getattr(args,key)) for key in ("results","protocol","reference")}
    with paths["reference"].open(encoding="utf-8", newline="") as handle:
        ref = list(csv.DictReader(handle))
    out = compare(json.loads(paths["results"].read_text()), json.loads(paths["protocol"].read_text()), ref)
    out["input_sha256"] = {key:hashlib.sha256(x.read_bytes()).hexdigest() for key,x in paths.items()}
    Path(args.output).write_text(json.dumps(out,indent=2,allow_nan=False)+"\n",encoding="utf-8")


if __name__ == "__main__":
    main()
