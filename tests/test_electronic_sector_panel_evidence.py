"""Actual frozen panel correspondence and semantic fault injections."""
import copy
import json
from pathlib import Path

import pytest

from electronic_pilot.sector_panel.checker import valid, panel

ROOT = Path(__file__).parents[1]/"docs/active/electronic_sector_panel_v1"
SEAL = json.loads((ROOT/"desktop_seal.json").read_text(encoding="utf-8"))
RESULT = json.loads((ROOT/"desktop_results.json").read_text(encoding="utf-8"))
SPEC = SEAL["protocol"]


def row():
    return copy.deepcopy(next(x for x in RESULT["rows"] if x["case_key"] == "pair_singlet_1.4"))


def test_actual_panel_and_charge_negative_test():
    verdict = panel(RESULT, SPEC)
    assert all(verdict[x] == "PASS" for x in ("P1", "P2", "P3", "P5"))
    assert verdict["complete"] and verdict["all_rows_valid"]
    assert RESULT["control_gate"] == "PASS"
    assert RESULT["protected_bytes_unchanged"] and RESULT["source_bytes_unchanged"]
    assert SEAL["basis"]["original_coefficients_exact_match"]
    assert all(x["same_AO"] for x in verdict["comparisons"])


@pytest.mark.parametrize("key,value", [("electrons", 1), ("sector", "triplet"), ("derived_charge_e", 1),
    ("basis_size", 27), ("ci_dimension", 378), ("matrix_dimension", 378), ("multiplicity", 3),
    ("accepted", False), ("matrix_asymmetry", 1e-5), ("orthonormalization_error", 1e-5),
    ("eigen_residual_l2", 1e-5), ("vector_norm_error", 1e-5), ("electronic_energy_hartree", float("nan")),
    ("total_energy_hartree", 0), ("nuclear_repulsion_hartree", 0), ("backend_charge_e", 1),
    ("backend_multiplicity", 3)])
def test_semantic_mutations_are_rejected(key, value):
    mutated = row()
    mutated[key] = value
    assert not valid(mutated, SPEC["cases"][mutated["case_key"]], SPEC)


def test_geometry_integrals_missing_and_duplicates_detected():
    changed = row(); changed["backend_positions_bohr"][0][2] += .01
    assert not valid(changed, SPEC["cases"][changed["case_key"]], SPEC)
    changed = row(); changed["overlap_eigenvalues"].pop()
    assert not valid(changed, SPEC["cases"][changed["case_key"]], SPEC)
    changed = copy.deepcopy(RESULT)
    target = next(x for x in changed["rows"] if x["case_key"] == "pair_doublet_1.4")
    target["AO_sha256"]["h"] = "0"*64
    assert panel(changed, SPEC)["P1"] == "UNRESOLVED"
    assert panel({"rows": RESULT["rows"][:-1]}, SPEC)["complete"] is False
    assert panel({"rows": RESULT["rows"]+[RESULT["rows"][0]]}, SPEC)["all_rows_valid"] is False


def test_shared_integral_action_all_spaces_full_and_exchange_parity():
    checks = json.loads((ROOT/"action_check_v1.json").read_text(encoding="utf-8"))
    assert checks["status"] == "PASS" and len(checks["rows"]) == 18
    assert all(x["artifact_hash_match"] and x["passed"] for x in checks["rows"])
    assert all(x["exchange_parity_error"] == 0 for x in checks["rows"])
