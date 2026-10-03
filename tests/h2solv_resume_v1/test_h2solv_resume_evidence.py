"""Byte provenance and STOP evidence only; no solver/physics validation."""
import hashlib
import json
from pathlib import Path

import pytest

from electronic_pilot.frontend_reference_v0.audit import verify


ROOT = Path(__file__).resolve().parents[2]
AREA = ROOT / "docs/active/h2_representation_pilot1_resume_v1"
EV = AREA / "evidence"


def read(name):
    return json.loads((EV / name).read_text(encoding="utf8"))


def test_archive_inventory_matches_designer_hashes_and_required_files():
    record = read("archive_manifest.json")
    assert record["status"] == "H2SOLV_ARCHIVE_PROVENANCE_PASS"
    assert record["zip_sha256"] == "3a2756179b4f74abe450b5383fd9d8c656501cc5e39b39af74de42ffcd4d615d"
    assert record["inner_sha256"] == "a0f2967b1d110e88fd929f3effd1b8616a6e4fcb0477a988cb564952814a86db"
    inventory = {r["path"]: r for r in record["inventory"]}
    assert len(inventory) == 20
    assert inventory["h2solv/f/h2solv.f"]["sha256"] == "aa109cbd47cf5dcd2db57ce3da67bdaf69e22dfd9023e1219328e21413703d2d"
    assert len([p for p in inventory if "/input/" in p]) == 5
    assert len([p for p in inventory if "/output/" in p]) == 5
    assert not record["source_redistribution"]


def test_failure_is_build_failure_and_does_not_invent_vendor_mismatch():
    result = read("results.json")
    assert result["build_attempts"] == 1 and result["build_exit"] == 2
    assert "BUILD_ENVIRONMENT_DIFFERENCE" in result["statuses"]
    assert "STOP" in result["statuses"]
    assert "NOT_CERTIFIED" in result["statuses"]
    assert "NOT_PRODUCTION_APPROVED" in result["statuses"]
    assert not result["linked_executable"]
    assert result["vendor_examples_executed"] == 0
    assert result["vendor_examples_reproduced"] is None
    assert not result["vendor_mismatch_measured"]
    assert result["R04_B1_runs"] == result["R04_B2_runs"] == 0
    assert not result["B2_implemented"]
    assert result["cost_comparison"] == "COST_COMPARISON_NOT_COMPARABLE"
    assert not result["h2solv_is_ground_truth"] and not result["pushed"]
    log = (EV / "build.log").read_text(encoding="utf8")
    assert "undefined reference" in log and "mpfr_set" in log
    assert "collect2: error: ld returned 1 exit status" in log


def test_reproduction_contract_was_bound_before_build_and_is_not_certification():
    data = (EV / "vendor_protocol.json").read_bytes()
    expected = (EV / "vendor_protocol.sha256").read_text().strip()
    assert hashlib.sha256(data).hexdigest() == expected
    assert read("build_result.json")["protocol_sha256"] == expected
    plan = json.loads(data)
    assert plan["build_command"] == ["make"]
    assert len(plan["examples_order"]) == 5
    assert not plan["original_source_edit_allowed"]
    assert not plan["scientific_correctness_from_examples"]


def test_original_and_historical_bytes_unchanged():
    record = read("preservation.json")
    assert record["archive_files_checked_per_copy"] == 20
    assert record["copies"] == 2
    assert not record["vendor_byte_mismatches"]
    assert record["historical_bindings"] == 22
    assert not record["historical_mismatches"]
    for name, digest in record["historical_sha256"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest
    assert not record["source_modified"] and not record["makefile_modified"]


def test_partial_review_and_unexecuted_rebuild_remain_explicit():
    audit = read("source_audit.json")
    assert audit["grade"] == "STATIC_SOURCE_REVIEW_PARTIAL"
    assert not audit["whole_source_read"]
    assert not audit["integral_recurrence_independently_proved"]
    assert not audit["B2_agent_spawned"]
    result = read("results.json")
    retry = result["next_experiment_not_executed"]
    assert retry["fresh_directory_required"] and not retry["source_edits"]
    assert retry["README_static_link_configuration"]
    assert result["cause_grade"] == "SUPPORTED_LINK_ORDER_HYPOTHESIS_NOT_REBUILD_VERIFIED"
    assert result["B1_sizes_and_ladders"] == "NOT_SEALED_VENDOR_GATE_STOP"


def test_final_byte_seal():
    bindings = read("final_seal.json")["bound_sha256"]
    assert verify(bindings, ROOT, ROOT) >= 25


@pytest.mark.parametrize("mutation", ["corrupt", "missing"])
def test_byte_seal_rejects_fault_injected_failure_evidence(tmp_path, mutation):
    key = "worktree:docs/active/h2_representation_pilot1_resume_v1/evidence/build_result.json"
    expected = read("final_seal.json")["bound_sha256"][key]
    copy = tmp_path / key.split(":", 1)[1]
    copy.parent.mkdir(parents=True)
    copy.write_bytes((EV / "build_result.json").read_bytes())
    assert verify({key: expected}, tmp_path, tmp_path) == 1
    if mutation == "corrupt":
        copy.write_bytes(copy.read_bytes() + b"CORRUPTED")
    else:
        copy.unlink()
    with pytest.raises((ValueError, FileNotFoundError)):
        verify({key: expected}, tmp_path, tmp_path)
