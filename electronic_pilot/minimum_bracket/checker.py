"""Standard-library control/bracket judge, never imports the evaluator."""
import math


def valid(row, spec):
    if not row.get("accepted") or row.get("failure_stage") is not None:
        return False
    if (row.get("basis") != spec["basis"] or row.get("basis_size") != spec["basis_size"]
            or row.get("singlet_dimension") != spec["singlet_dimension"]
            or row.get("electrons") != 2 or row.get("sector") != spec["sector"]
            or row.get("charge") != 0 or row.get("multiplicity") != 1 or not row.get("spherical")):
        return False
    r = row.get("R_bohr")
    if not isinstance(r, (float, int)) or not math.isfinite(r) or r <= 0:
        return False
    if row.get("positions_bohr") != [[0.0, 0.0, -r/2], [0.0, 0.0, r/2]]:
        return False
    checks = [("orthonormalization_error", spec["orthonormalization_max_norm"]),
              ("transformed_h_asymmetry", spec["hermitian_max_asymmetry"]),
              ("singlet_asymmetry", spec["hermitian_max_asymmetry"]),
              ("eigen_residual_l2", spec["eigen_residual_max_l2_hartree"]),
              ("vector_norm_error", spec["vector_norm_error_max"])]
    if any(not isinstance(row.get(k), (float, int)) or not math.isfinite(row[k])
           or row[k] < 0 or row[k] > limit for k, limit in checks):
        return False
    if any(not math.isfinite(x) or x < 0 or x > spec["hermitian_max_asymmetry"]
           for x in row.get("transformed_eri_symmetry", {}).values()):
        return False
    if set(row.get("transformed_eri_symmetry", {})) != {"ij_swap_max", "kl_swap_max", "pair_swap_max"}:
        return False
    spectrum = row.get("overlap_eigenvalues", [])
    if len(spectrum) != spec["basis_size"] or any(not math.isfinite(x) for x in spectrum):
        return False
    if spectrum != sorted(spectrum) or spectrum[0] <= spec["overlap_min_eigenvalue_floor"]:
        return False
    e, nn, total = (row.get(k) for k in ("electronic_energy_hartree", "nuclear_repulsion_hartree", "total_energy_hartree"))
    if any(not isinstance(x, (float, int)) or not math.isfinite(x) for x in (e, nn, total)):
        return False
    return (abs(nn-1/r) <= spec["same_problem_nuclear_repulsion_abs_hartree"]
            and abs(total-(e+nn)) <= spec["same_problem_nuclear_repulsion_abs_hartree"])


def controls(rows, historical, spec):
    expected = set(spec["controls_bohr"])
    if len(rows) != len(expected) or {r.get("R_bohr") for r in rows} != expected:
        return dict(status="FAIL", reason="incomplete_or_duplicate_controls", comparisons=[])
    comparisons = []
    for row in rows:
        old = next(x for x in historical["rows"] if x["basis"] == spec["basis"] and x["R_bohr"] == row["R_bohr"])
        # Original archived solver accepted these controls before this gate.
        baseline = old["original"]
        diag = old["paths"][0]
        delta = abs(row["total_energy_hartree"]-baseline["energy"]) if valid(row, spec) else None
        spectrum = (max(abs(a-b) for a, b in zip(row["overlap_eigenvalues"], diag["overlap_eigenvalues"]))
                    if valid(row, spec) else None)
        passed = bool(baseline["accepted"] and delta is not None
                      and delta <= spec["same_problem_energy_abs_hartree"]
                      and spectrum <= spec["same_problem_overlap_spectrum_abs"])
        comparisons.append(dict(R_bohr=row["R_bohr"], passed=passed,
                                energy_abs_difference_hartree=delta,
                                overlap_spectrum_max_abs_difference=spectrum))
    return dict(status="PASS" if all(x["passed"] for x in comparisons) else "FAIL", comparisons=comparisons,
                note="same finite-basis numerical controls; not a formal certificate")


def bracket(rows, control_verdict, spec):
    if control_verdict.get("status") != "PASS":
        return dict(status="UNRESOLVED", reason="control_gate_failed")
    required = spec["sampled_bracket_bohr"]
    selected = [x for x in rows if x.get("R_bohr") in required]
    if len(selected) != 3 or {x["R_bohr"] for x in selected} != set(required) or not all(valid(x, spec) for x in selected):
        return dict(status="UNRESOLVED", reason="missing_duplicate_or_invalid_neighbor")
    energy = {x["R_bohr"]: x["total_energy_hartree"] for x in selected}
    left, center, right = required
    passed = energy[center] < energy[left] and energy[center] < energy[right]
    return dict(status="PASS" if passed else "NO_SAMPLED_MINIMUM_AT_1_4",
                energies_hartree={str(r): energy[r] for r in required},
                E13_minus_E14_hartree=energy[left]-energy[center],
                E15_minus_E14_hartree=energy[right]-energy[center],
                claim="R=1.4 sampled local minimum on sealed three-point cc-pVQZ grid" if passed else None,
                evidence_grade="NUMERICALLY_VALIDATED_NOT_CERTIFIED")
