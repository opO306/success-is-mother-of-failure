"""Standard-library post-acquisition judge; no evaluator/contract imports."""
import math


def valid(row, case, spec):
    m = 14*(len(case["nuclei"])+len(case["ghost_centers_bohr"]))
    ne, spin = case["electrons"], case["sector"]
    d = m if ne == 1 else m*(m+(1 if spin == "singlet" else -1))//2
    q = sum(n["Z"] for n in case["nuclei"])-ne
    if (row.get("input") != case or not row.get("accepted") or row.get("failure_stage") is not None or
            row.get("basis_size") != m or row.get("ci_dimension") != d or row.get("matrix_dimension") != d or
            row.get("electrons") != ne or row.get("sector") != spin or row.get("derived_charge_e") != q or
            row.get("multiplicity") != {"doublet": 2, "singlet": 1, "triplet": 3}[spin] or not row.get("spherical")):
        return False
    limits = {"orthonormalization_error": spec["orthogonality_tolerance"], "transformed_h_asymmetry": spec["hermiticity_tolerance"],
              "matrix_asymmetry": spec["hermiticity_tolerance"], "AO_s_asymmetry": spec["hermiticity_tolerance"],
              "AO_h_asymmetry": spec["hermiticity_tolerance"], "eigen_residual_l2": spec["residual_tolerance"],
              "vector_norm_error": spec["norm_tolerance"]}
    for k, limit in limits.items():
        x = row.get(k)
        if type(x) not in (float, int) or not math.isfinite(x) or x < 0 or x > limit:
            return False
    for key in ("AO_eri_symmetry", "transformed_eri_symmetry"):
        values = row.get(key, {})
        if set(values) != {"ij", "kl", "pair"} or any(not math.isfinite(x) or x < 0 or x > spec["hermiticity_tolerance"] for x in values.values()):
            return False
    w = row.get("overlap_eigenvalues", [])
    if len(w) != m or any(not math.isfinite(x) for x in w) or w != sorted(w) or w[0] <= spec["overlap_floor"]:
        return False
    e, nn, total = (row.get(k) for k in ("electronic_energy_hartree", "nuclear_repulsion_hartree", "total_energy_hartree"))
    if any(type(x) not in (int, float) or not math.isfinite(x) for x in (e, nn, total)):
        return False
    nuclei = case["nuclei"]
    expected_nn = sum(n["Z"]*b["Z"]/math.dist(n["position_bohr"], b["position_bohr"]) for k, n in enumerate(nuclei) for b in nuclei[k+1:])
    if abs(nn-expected_nn) > spec["bookkeeping_tolerance"] or abs(total-e-nn) > spec["bookkeeping_tolerance"]:
        return False
    if "backend_positions_bohr" in row and (row["backend_positions_bohr"] != [n["position_bohr"] for n in nuclei]+case["ghost_centers_bohr"] or
            row.get("backend_charge_e") != q or row.get("backend_multiplicity") != row["multiplicity"] or
            abs(row.get("backend_nuclear_repulsion_hartree", math.inf)-nn) > spec["bookkeeping_tolerance"]):
        return False
    return True


def panel(result, spec):
    rows = result["rows"]
    by_key = {r.get("case_key"): r for r in rows}
    complete = len(rows) == len(spec["cases"]) and set(by_key) == set(spec["cases"])
    all_valid = complete and all(valid(by_key[k], c, spec) for k, c in spec["cases"].items())
    comparisons = []
    for group in spec["same_geometry_groups"]:
        selected = [by_key.get(k, {}) for k in group]
        ok = all(valid(row, spec["cases"][key], spec) for key, row in zip(group, selected))
        same_ao = ok and selected[0]["AO_sha256"] == selected[1]["AO_sha256"] == selected[2]["AO_sha256"]
        differences = [abs(selected[0]["total_energy_hartree"]-selected[1]["total_energy_hartree"]),
                       abs(selected[1]["total_energy_hartree"]-selected[2]["total_energy_hartree"])] if ok else [None, None]
        comparisons.append(dict(keys=group, valid=ok, same_AO=same_ao, electron_energy_difference=differences[0], spin_energy_difference=differences[1]))
    p1 = all(c["same_AO"] and c["electron_energy_difference"] > spec["sector_difference_floor"] for c in comparisons)
    p2 = all(c["same_AO"] for c in comparisons) and all(c["spin_energy_difference"] > spec["sector_difference_floor"] for c in comparisons[:-1])
    # Large-R degeneracy is allowed, and is evidence of the fragment direction.
    asymptotic = []
    atom = by_key.get("atom", {})
    atom_ok = valid(atom, spec["cases"]["atom"], spec)
    for sector, factor in (("doublet", 1), ("singlet", 2), ("triplet", 2)):
        far, near = by_key.get(f"pair_{sector}_20", {}), by_key.get(f"pair_{sector}_4", {})
        ok = atom_ok and valid(far, spec["cases"][f"pair_{sector}_20"], spec) and valid(near, spec["cases"][f"pair_{sector}_4"], spec)
        error = far["total_energy_hartree"]-factor*atom["total_energy_hartree"] if ok else None
        near_error = near["total_energy_hartree"]-factor*atom["total_energy_hartree"] if ok else None
        asymptotic.append(dict(sector=sector, fragment_factor=factor, finite_R20_error_hartree=error, R4_error_hartree=near_error,
                               passed=ok and abs(error) <= spec["asymptotic_tolerance"] and abs(error) < abs(near_error)))
    ghost = by_key.get("ghost_20", {})
    ghost_ok = atom_ok and valid(ghost, spec["cases"]["ghost_20"], spec)
    ghost_difference = ghost["total_energy_hartree"]-atom["total_energy_hartree"] if ghost_ok else None
    p5 = all(x["passed"] for x in asymptotic) and ghost_ok and abs(ghost_difference) <= spec["ghost_far_tolerance"]
    verdict = dict(P1="PASS" if p1 else "UNRESOLVED", P2="PASS" if p2 else "UNRESOLVED",
                   P3="PASS" if all_valid else "UNRESOLVED", P4="SOURCE_REVIEW_REQUIRED",
                   P5="PASS" if p5 else "UNRESOLVED", complete=complete, all_rows_valid=all_valid,
                   comparisons=comparisons, asymptotic=asymptotic, ghost_R20_difference=ghost_difference,
                   scope="static finite-basis author numerical check; not certification")
    return verdict
