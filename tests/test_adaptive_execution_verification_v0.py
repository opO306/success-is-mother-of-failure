"""Offline fault/boundary tests. No trajectories, GPU, hardware collection or network."""
import ast
import copy
import hashlib
import json
import shutil
from pathlib import Path

import pytest

from experiments.adaptive_execution_verification_v0 import collector, exploration, manager, selector, shutdown, verifier
from experiments.adaptive_execution_verification_v0 import offline
from experiments.adaptive_execution_verification_v0.journal import ExperienceJournal
from experiments.adaptive_execution_verification_v0.common import ROOT, canonical, digest, exclusive_json, read


@pytest.fixture(scope="module")
def evidence():
    candidate = collector.collect()
    receipt = verifier.verify(ROOT, candidate)
    assert receipt["verdict"] == "VERIFIED", receipt["errors"]
    return candidate, receipt


def admitted(candidate, receipt):
    return manager.admit(candidate, receipt, trusted_receipt_sha256=digest(receipt),
                         trusted_verifier_sha256=receipt["verifier_sha256"],
                         trusted_protocol_sha256=receipt["protocol_sha256"],
                         trusted_manifest_sha256=receipt["manifest_sha256"])


def test_historical_panel_and_honest_scope(evidence):
    candidate, receipt = evidence
    assert receipt["n_services"] == 35
    assert len(candidate["rows"]) == 7
    assert receipt["scope"] == "HISTORICAL_SESSION_EXECUTION_COST_ONLY"
    assert receipt["formula_independence"] == "UNRESOLVED_SHARED_RWFORCE"
    gaps = collector.knowledge_gaps(candidate)
    assert gaps["choice_assessment"] == "VALID_CORRECT_BUT_COST_INFORMATION_INCOMPLETE"
    assert "independent RwForce formula validation" in gaps["unknown"]


def test_experience_transitions_and_refusals_are_preserved(tmp_path, evidence):
    candidate, receipt = evidence
    journal = ExperienceJournal(tmp_path)
    with pytest.raises(ValueError, match="INVALID_CANDIDATE_TRANSITION"):
        journal.candidate(candidate)
    journal.unknown(["historical session costs"])
    journal.candidate(candidate)
    refused = dict(receipt, verdict="REFUSED", errors=["insufficient evidence"])
    journal.receipt(refused, trusted_receipt_sha256=digest(refused))
    assert journal.history()[-1]["state"] == "CANDIDATE"
    profile = admitted(candidate, receipt)
    with pytest.raises(ValueError, match="VERIFIED_REQUIRES"):
        journal.verified(profile, trusted_profile_sha256=digest(profile))
    journal.receipt(receipt, trusted_receipt_sha256=digest(receipt))
    journal.verified(profile, trusted_profile_sha256=digest(profile))
    assert [event["state"] for event in journal.history()] == ["UNKNOWN", "CANDIDATE", "CANDIDATE", "CANDIDATE", "VERIFIED"]
    assert journal.history()[2]["payload"]["verification_receipt"]["verdict"] == "REFUSED"


@pytest.mark.parametrize("fault", ["cpu", "wall", "p", "env", "result", "state", "delete_repeat"])
def test_candidate_forgery_is_refused(evidence, fault):
    candidate = copy.deepcopy(evidence[0])
    row = candidate["rows"][0]
    if fault == "cpu":
        row["observations"][0]["cpu_ns"] = 1
    elif fault == "wall":
        row["observations"][0]["wall_ns"] = -1
    elif fault == "p":
        row["scope"]["p"] = 162
    elif fault == "env":
        row["scope"]["env_id"] = "other"
    elif fault == "result":
        row["observations"][0]["result_sha256"] = "0" * 64
    elif fault == "state":
        candidate["state"] = "VERIFIED"
    else:
        row["observations"].pop()
    receipt = verifier.verify(ROOT, candidate)
    assert receipt["verdict"] == "REFUSED"
    assert "CANDIDATE_REDERIVATION_MISMATCH" in receipt["errors"]


def test_original_source_mutation_detected(tmp_path, evidence):
    # Copy only the exact sealed inputs. No fixture regeneration or computation.
    here = ROOT / "experiments/adaptive_execution_verification_v0"
    manifest = read(here / "source_manifest.json")
    for relative in list(manifest["files"]) + [
        "experiments/adaptive_execution_verification_v0/protocol.json",
        "experiments/adaptive_execution_verification_v0/protocol_seal.json",
        "experiments/adaptive_execution_verification_v0/source_manifest.json",
        "docs/active/ADAPTIVE_EXECUTION_VERIFICATION_V0_DESIGN.md",
    ]:
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, destination)
    source = tmp_path / next(path for path in manifest["files"] if "/services/" in path)
    with source.open("ab") as stream:
        stream.write(b"tampered")
    receipt = verifier.verify(tmp_path, evidence[0])
    assert receipt["verdict"] == "REFUSED"
    assert receipt["errors"][0].startswith("SOURCE_SEAL_MISMATCH:")


def test_manager_requires_separate_pins(evidence):
    candidate, receipt = evidence
    with pytest.raises(ValueError, match="UNTRUSTED_RECEIPT"):
        manager.admit(candidate, receipt, trusted_receipt_sha256="wrong", trusted_verifier_sha256="wrong",
                      trusted_protocol_sha256="wrong", trusted_manifest_sha256="wrong")
    mutated = copy.deepcopy(candidate)
    mutated["rows"].pop()
    with pytest.raises(ValueError, match="CANDIDATE_BINDING_MISMATCH"):
        admitted(mutated, receipt)
    rejected = dict(receipt, verdict="REFUSED")
    with pytest.raises(ValueError, match="VERIFICATION_NOT_PASSED"):
        admitted(candidate, rejected)


def test_next_request_activation_and_rollback(tmp_path, evidence):
    profile = admitted(*evidence)
    registry = manager.Registry(tmp_path)
    prior = registry.begin_request()
    assert prior.version == manager.LEGACY
    registry.activate(profile, reason="reviewed offline receipt", trusted_profile_sha256=digest(profile))
    active = registry.begin_request()
    scope_r1 = next(row["scope"] for row in profile["rows"] if row["scope"]["N"] == 12)
    scope_r7 = next(row["scope"] for row in profile["rows"] if row["scope"]["N"] == 14)
    allowed = {"CPU_SERIAL", "CPU_PARALLEL/W6", "GPU_HYBRID"}
    assert selector.recommend(scope_r1, "CPU_MIN", active, eligible_backends=allowed)["backend"] == "GPU_HYBRID"
    assert selector.recommend(scope_r7, "WALL_MIN", active, eligible_backends=allowed)["backend"] == "CPU_PARALLEL/W6"
    assert selector.recommend(scope_r1, "CPU_MIN", prior, eligible_backends=allowed)["decision"] == "USE_LEGACY"
    registry.activate(reason="rollback")
    after = registry.begin_request()
    assert after.version == manager.LEGACY
    assert selector.recommend(scope_r1, "CPU_MIN", active, eligible_backends=allowed)["backend"] == "GPU_HYBRID"
    assert len(registry.events()) == 2
    assert len(list((tmp_path / "profiles").glob("*.json"))) == 1


def test_candidate_and_unpinned_profile_cannot_activate(tmp_path, evidence):
    registry = manager.Registry(tmp_path)
    with pytest.raises(ValueError, match="CANDIDATE_CANNOT_ACTIVATE"):
        registry.activate(evidence[0], reason="forged")
    with pytest.raises(ValueError, match="UNTRUSTED_PROFILE"):
        registry.activate(admitted(*evidence), reason="no manager handoff")
    assert registry.begin_request().version == manager.LEGACY


def test_scope_and_eligibility_fail_closed(evidence):
    profile = admitted(*evidence)
    active = manager.RequestSnapshot(digest(profile), canonical(profile))
    scope = next(row["scope"] for row in profile["rows"] if row["scope"]["N"] == 12)
    other = dict(scope, evidence_session="NEW_PHYSICAL_HOST_SESSION")
    assert selector.recommend(other, "CPU_MIN", active, eligible_backends={"CPU_SERIAL", "GPU_HYBRID"})["decision"] == "USE_LEGACY"
    assert selector.recommend(scope, "CPU_MIN", active, eligible_backends={"CPU_SERIAL"})["backend"] == "CPU_SERIAL"
    assert selector.recommend(scope, "CPU_MIN", active, eligible_backends={"GPU_HYBRID"})["decision"] == "USE_LEGACY"
    changed = dict(scope, p=162)
    assert selector.recommend(changed, "WALL_MIN", active, eligible_backends={"CPU_SERIAL"})["decision"] == "USE_LEGACY"


def test_immutable_observations_and_exclusive_outputs(tmp_path, evidence):
    candidate, receipt = copy.deepcopy(evidence)
    profile = admitted(candidate, receipt)
    candidate["rows"][0]["scope"]["N"] = 999
    assert profile["rows"][0]["scope"]["N"] != 999
    target = tmp_path / "receipt.json"
    exclusive_json(target, receipt)
    with pytest.raises(FileExistsError):
        exclusive_json(target, dict(receipt, verdict="VERIFIED"))


def test_activation_chain_tampering_detected(tmp_path):
    registry = manager.Registry(tmp_path)
    registry.activate(reason="explicit legacy")
    path = tmp_path / "event_000000.json"
    record = read(path)
    record["reason"] = "modified"
    path.write_bytes(canonical(record))
    with pytest.raises(ValueError, match="ACTIVATION_CHAIN_INVALID"):
        registry.begin_request()


def test_exploration_requires_information_and_never_launches():
    missing = exploration.assess("CPU_MIN", risk="LOW", eligible=True)
    assert missing["decision"] == "DEFER_INFORMATION_NEEDED"
    assert "reuse_count" in missing["missing"]
    proposed = exploration.assess("CPU_MIN", 20, 10, 80, 30, "LOW", True)
    assert proposed["decision"] == "PROPOSE" and proposed["net_gain_lower_ns"] == 90
    assert proposed["launch"] is False
    assert exploration.assess("WALL_MIN", 10, 1, 10, 10, "LOW", True)["decision"] == "DEFER"
    assert exploration.assess("WALL_MIN", risk="MISMATCH")["decision"] == "STOP"


def test_remote_runner_requires_explicit_bound_authorization(tmp_path, monkeypatch):
    path = tmp_path / "authorization.json"
    ticket = {"gate": "ADAPTIVE_EXECUTION_VERIFICATION_V0", "scope": "OFFLINE_ONLY",
              "explicit_user_approval": False, "approval_reference": "", "instance_id": "123",
              "code_seal_sha256": "sealed", "new_trajectories": 0, "gpu_calls": 0}
    path.write_bytes(canonical(ticket))
    monkeypatch.setattr(offline.platform, "system", lambda: "Linux")
    monkeypatch.setenv("CONTAINER_ID", "123")
    with pytest.raises(ValueError, match="MISSING_USER_APPROVAL"):
        offline.authorize(path, expected_code_seal_sha256="sealed")
    ticket.update(explicit_user_approval=True, approval_reference="TEST_ONLY simulated user approval")
    path.write_bytes(canonical(ticket))
    assert offline.authorize(path, expected_code_seal_sha256="sealed")["scope"] == "OFFLINE_ONLY"
    monkeypatch.setenv("CONTAINER_ID", "999")
    with pytest.raises(ValueError, match="INSTANCE_ID_MISMATCH"):
        offline.authorize(path, expected_code_seal_sha256="sealed")
    monkeypatch.setattr(offline.platform, "system", lambda: "Windows")
    with pytest.raises(ValueError, match="NON_APPROVED_EXECUTION_SURFACE"):
        offline.authorize(path, expected_code_seal_sha256="sealed")


class FakeTransport:
    def __init__(self, state="stopped", returned_id="123", fail=False):
        self.state, self.returned_id, self.fail = state, returned_id, fail
        self.stops, self.reads = [], []

    def stop(self, instance_id):
        self.stops.append(instance_id)
        if self.fail:
            raise TimeoutError("transport timeout")

    def status(self, instance_id):
        self.reads.append(instance_id)
        return {"id": self.returned_id, "actual_status": self.state}


@pytest.mark.parametrize("trigger", ["COMPLETED", "FAILED", "DEADLINE"])
def test_stop_does_not_scan_ps_and_confirms_exact_instance(trigger):
    transport = FakeTransport()
    receipt = shutdown.stop_owned(shutdown.ExclusiveLease("123", "user approval", True), transport, trigger=trigger)
    assert receipt["status"] == "STOP_CONFIRMED"
    assert transport.stops == ["123"] and transport.reads == ["123"]
    assert receipt["paid_compute_allowed"] is False


def test_stop_failure_wrong_instance_and_no_lease():
    lease = shutdown.ExclusiveLease("123", "user approval", True)
    transport = FakeTransport(state="running", fail=True)
    receipt = shutdown.stop_owned(lease, transport, trigger="FAILED")
    assert receipt["status"] == "STOP_UNCONFIRMED"
    assert len(transport.stops) == 3 and len(transport.reads) == 6
    wrong = shutdown.stop_owned(lease, FakeTransport(returned_id="999"), trigger="COMPLETED")
    assert wrong["status"] == "REFUSED_INSTANCE_ID_MISMATCH"
    unavailable = FakeTransport()
    refused = shutdown.stop_owned(shutdown.ExclusiveLease("123", "", False), unavailable, trigger="DEADLINE")
    assert refused["status"] == "REFUSED_NO_EXCLUSIVE_LEASE" and unavailable.stops == []


def test_timeout_stop_still_confirms_delivered_request():
    transport = FakeTransport(fail=True)
    receipt = shutdown.stop_owned(shutdown.ExclusiveLease("123", "approved", True), transport, trigger="FAILED")
    assert receipt["status"] == "STOP_CONFIRMED"


def test_verifier_import_boundary_and_v1_cpu_min_preserved():
    here = ROOT / "experiments/adaptive_execution_verification_v0"
    tree = ast.parse((here / "verifier.py").read_text())
    imports = [node for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))]
    allowed = {"__future__", "gzip", "hashlib", "json", "decimal", "pathlib"}
    for node in imports:
        names = [alias.name for alias in node.names] if isinstance(node, ast.Import) else [node.module]
        assert all(name in allowed for name in names)
    v1 = (ROOT / "experiments/adaptive_execution_v1/selector.py").read_text()
    legacy_tree = ast.parse(v1)
    selection = next(node for node in legacy_tree.body if isinstance(node, ast.FunctionDef) and node.name == "select")
    cpu_rule = next(node for node in selection.body if isinstance(node, ast.If) and isinstance(node.test, ast.Compare)
                    and isinstance(node.test.left, ast.Name) and node.test.left.id == "goal"
                    and isinstance(node.test.comparators[0], ast.Constant)
                    and ast.literal_eval(node.test.comparators[0]) == "CPU_MIN")
    assert isinstance(cpu_rule.body[0], ast.Return)
    assert ast.literal_eval(cpu_rule.body[0].value.args[0]) == "SERIAL"
    assert "SEALED_CPU_MIN_RULE_SERIAL" in ast.unparse(cpu_rule)
