"""Evidence integrity tests, not a James-Coolidge solver or physics validation."""
import hashlib
import json
from decimal import Decimal
from pathlib import Path

import pytest
from electronic_pilot.frontend_reference_v0.audit import verify

EVIDENCE = Path("docs/active/h2_representation_pilot1/evidence")


def read(name):
    return json.loads((EVIDENCE/name).read_text(encoding="utf8"))


def test_feasibility_STOP_does_not_become_accuracy_failure_or_success():
    record = read("feasibility.json")
    assert record["status"] == "REPRESENTATION_PILOT1_FEASIBILITY_UNRESOLVED"
    assert record["STOP"] and not record["source_archive_acquired"]
    assert not record["compiled"] and not record["source_audited"]
    assert record["local_source_hash"] is None
    assert record["B_numerical_runs"] == 0
    assert not record["B_solver_implemented"]
    assert record["R04_target"] == "NOT_EVALUATED_FEASIBILITY_STOP"
    assert record["execution_contract"]["status"] == "NOT_SEALED_FEASIBILITY_BLOCKED"
    for key in ("small_medium_large", "P1_P2_P3", "native_guards",
                "lowest_root_check", "nonlinear_optimization_contract"):
        assert record["execution_contract"][key] is None
    assert record["old_audit"]["QZ44"] == "NUMERICAL FAIL"
    assert record["certification"] == "NOT_CERTIFIED"
    assert record["production"] == "NOT_PRODUCTION_APPROVED"


@pytest.mark.parametrize("arm", ["QZ", "V5Z"])
def test_historical_comparator_bytes_match_parent_inventory(arm):
    source = json.loads(Path(
        "docs/active/h2_adversarial_v0/evidence/raw_inventory.json"
    ).read_text(encoding="utf8"))
    expected = source["files"][f"runs/h2_adversarial_v0/cardinal_v0/{arm}/result.json"]
    data = (EVIDENCE/f"historical_{arm}_result.json").read_bytes()
    assert len(data) == expected["bytes"]
    assert hashlib.sha256(data).hexdigest() == expected["sha256"]
    provenance = next(x for x in read("historical_provenance.json")["copies"]
                      if x["arm"] == f"A-{arm}")
    assert provenance["sha256"] == expected["sha256"]
    assert not provenance["fresh_run"]


def test_cost_comparison_retains_unmeasured_and_unexecuted_values():
    cost = read("cost_comparison.json")
    assert cost["status"] == "COST_COMPARISON_NOT_COMPARABLE"
    assert cost["main_Gaussian_accuracy_comparator"] == "A-V5Z"
    assert Decimal(cost["physical_target_absolute_hartree"]) == Decimal("0.001")
    rows = {row["arm"]: row for row in cost["rows"]}
    assert set(rows) == {"A-QZ", "A-V5Z", "B-SMALL", "B-MEDIUM", "B-LARGE"}
    for name in ("QZ", "V5Z"):
        row = rows[f"A-{name}"]; old = read(f"historical_{name}_result.json")
        assert not row["fresh_run"]
        assert row["cost_label"] == "NOT SAME-RUN COST COMPARISON"
        assert row["whole_process_wall_seconds"] is None
        assert row["historical_computation_wall_seconds"] == old["runtime_seconds"]
        assert row["peak_rss_kib_process_highwater"] == old["peak_rss_kib"]
        assert not row["all_MO_accuracy_certified"]
        assert row["integral_generation_seconds"] is None
        assert row["failed_retry_seconds"] is None
    for name in ("SMALL", "MEDIUM", "LARGE"):
        row = rows[f"B-{name}"]
        assert row["execution"] == "NOT_EXECUTED_FEASIBILITY_STOP"
        for key in ("BO_energy_hartree", "basis_functions", "Hamiltonian_dimension",
                    "whole_process_wall_seconds", "peak_memory_MiB",
                    "required_guards_passed", "physical_target_met"):
            assert row[key] is None
    assert Decimal(rows["A-QZ"]["historical_signed_reference_difference_hartree"]) > Decimal(".001")
    assert abs(Decimal(rows["A-V5Z"]["historical_signed_reference_difference_hartree"])) < Decimal(".001")


def test_physical_quantity_and_license_claims_do_not_overreach():
    feasibility = read("feasibility.json")
    physics = feasibility["physical_contract"]
    assert physics["charges"] == [1, 1] and physics["electrons"] == 2
    assert physics["fixed_nuclei"] and physics["nonrelativistic_Coulomb"]
    assert physics["H2SOLV_paper_Hamiltonian_already_includes_nuclear_repulsion"]
    assert physics["double_addition_of_1_over_R_forbidden"]
    assert "UNVERIFIED" in physics["actual_B_input_numeric_parsing"]
    assert "R^(-sum(n)-3)" in feasibility["representation_paper"]["overall_R_scaling"]
    license_record = feasibility["license"]
    assert license_record["identified"]
    assert not license_record["third_party_code_redistributed"]
    assert not license_record["commercial_or_proprietary_permission_assumed"]
    assert not license_record["OSI_permissive_assumed"]
    assert not feasibility["nonlinear_parameters"]["reference_in_objective"]
    assert not feasibility["nonlinear_parameters"]["literature_result_or_seed_used"]


def test_access_failures_and_evidence_origin_are_preserved():
    acquisition = read("source_access_attempts.json")
    assert acquisition["three_unsuccessful_access_routes_then_STOP"]
    assert not acquisition["authentication_bypass_attempted"]
    assert len(acquisition["routes"]) == 3
    assert all(not route["source_archive_acquired"] for route in acquisition["routes"])
    assert acquisition["routes"][-1]["HTTP"] == 401
    assert "transcribed" in acquisition["routes"][-1]["evidence_origin"]
    snapshots = read("primary_metadata_acquisition.json")["records"]
    assert len(snapshots) == 4
    assert all(row["status"] == 200 for row in snapshots)
    assert all(row["evidence_origin"] == "fresh HTTP response bytes" for row in snapshots)
    protection = read("parent_protection.json")
    assert protection["checked_bindings_before"] == protection["checked_bindings_after"] == 1269
    assert protection["parent_tracked_status_after"] == ""


def test_final_seal_detects_corrupted_evidence(tmp_path):
    seal = read("final_seal.json")
    assert verify(seal["bound_sha256"], Path("."), Path(".")) >= 15
    key = "worktree:docs/active/h2_representation_pilot1/evidence/feasibility.json"
    original = EVIDENCE/"feasibility.json"
    copied = tmp_path/key.split(":", 1)[1]
    copied.parent.mkdir(parents=True)
    copied.write_bytes(original.read_bytes())
    assert verify({key: seal["bound_sha256"][key]}, tmp_path, tmp_path) == 1
    copied.write_bytes(copied.read_bytes()+b"\nCORRUPTED")
    with pytest.raises(ValueError, match="BYTE DRIFT"):
        verify({key: seal["bound_sha256"][key]}, tmp_path, tmp_path)
