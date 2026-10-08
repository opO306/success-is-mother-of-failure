"""TEST_ONLY flow/fault tests; synthetic costs, pinned old outputs, no physics/GPU/network."""
import ast
import copy
import hashlib
import json
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from experiments.adaptive_execution_learning_v1 import collector, inspector, manager, selector, value
from experiments.adaptive_execution_learning_v1.core import ROOT, canonical, digest, read, write_new, Ledger, check_frozen
from experiments.adaptive_execution_learning_v1.synthetic import panel


@pytest.fixture
def authority():
    # Provision both identities BEFORE executor ingest. Never ship a production private key.
    judge, ruler = Ed25519PrivateKey.generate(), Ed25519PrivateKey.generate()
    public = lambda key: key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()
    roots = manager.TrustRoots(public(judge), public(ruler),
                               digest(read(ROOT / "experiments/adaptive_execution_learning_v1/protocol.json")),
                               hashlib.sha256(Path(inspector.__file__).read_bytes()).hexdigest())
    return judge, ruler, roots


def setup_flow(tmp_path, authority, *, session="NEW_SYNTHETIC_A", N=12, costs=None):
    judge, ruler, roots = authority
    reg = manager.Registry(tmp_path / "manager", roots)
    before = reg.begin_request("WALL_MIN")
    paths = panel(tmp_path / "raw", session=session, N=N, costs=costs)
    ingest = collector.Ingest(tmp_path / "executor")
    candidate = ingest.collect(paths)
    receipt = inspector.inspect_and_sign(candidate, judge)
    ingest.record_receipt(candidate, receipt)
    profile = reg.admit(candidate, receipt)
    ingest.mark_verified(candidate, profile, reg)
    return reg, ingest, candidate, receipt, profile, before


def approval(ruler, reg, profile_id, goal="WALL_MIN", decision_id="d1"):
    body = {"schema": "ael1-activation", "mode": "TEST_ONLY", "profile_id": profile_id,
            "goal": goal, "predecessor": reg.version(), "decision_id": decision_id, "reason": "explicit test manager approval"}
    return {"body": body, "signature": ruler.sign(b"AEL1_ACTIVATION\0" + canonical(body)).hex()}


def test_preservation_and_old_panel():
    check_frozen()
    from experiments.adaptive_execution_verification_v0 import collector as old_c, verifier as old_v
    candidate = old_c.collect()
    receipt = old_v.verify(ROOT, candidate)
    assert receipt["verdict"] == "VERIFIED" and receipt["n_services"] == 35
    assert len(candidate["rows"]) == 7


def test_new_session_candidate_and_missing_information(tmp_path):
    ingest = collector.Ingest(tmp_path / "executor")
    paths = panel(tmp_path / "raw", session="NEW_SYNTHETIC")
    candidate = ingest.collect(paths)
    assert candidate["state"] == "CANDIDATE"
    assert candidate["scope"]["session_id"] == "NEW_SYNTHETIC"
    history = ingest.history()
    assert [event["payload"]["state"] for event in history] == ["UNKNOWN", "CANDIDATE"]
    gap = collector.gaps(candidate, candidate["scope"], ["CPU_SERIAL", "GPU_HYBRID"], [])
    assert gap["state"] == "UNKNOWN" and "GPU_HYBRID" in gap["unknown_methods"]
    assert gap["choice_assessment"] == "VALID_CORRECT_BUT_COST_INFORMATION_INCOMPLETE"
    record = read(paths[0])
    assert record["initial_state"] and record["choice_reason"] and record["correctness_evidence"]
    assert record["measurement_kind"] == "SYNTHETIC_TEST_ONLY"


def test_learning_next_request_and_both_objectives(tmp_path, authority):
    reg, ingest, candidate, receipt, profile, before = setup_flow(tmp_path, authority)
    assert receipt["body"]["verdict"] == "VERIFIED"
    assert receipt["body"]["formula_independence"] == "UNRESOLVED_SHARED_RWFORCE"
    assert ingest.history()[-1]["payload"]["state"] == "VERIFIED"
    eligible = ["CPU_SERIAL", "CPU_PARALLEL/W6", "GPU_HYBRID"]
    assert selector.choose(candidate["scope"], before, eligible)["method"] == "LEGACY_V1"
    reg.activate(approval(authority[1], reg, profile["id"], "WALL_MIN", "wall"))
    wall = reg.begin_request("WALL_MIN")
    assert selector.choose(candidate["scope"], wall, eligible)["method"] == "GPU_HYBRID"
    assert selector.choose(candidate["scope"], before, eligible)["method"] == "LEGACY_V1"
    # CPU profile is NOT silently activated by WALL approval.
    assert selector.choose(candidate["scope"], reg.begin_request("CPU_MIN"), eligible)["method"] == "LEGACY_V1"
    reg.activate(approval(authority[1], reg, profile["id"], "CPU_MIN", "cpu"))
    assert selector.choose(candidate["scope"], reg.begin_request("CPU_MIN"), eligible)["method"] == "GPU_HYBRID"
    reg.activate(approval(authority[1], reg, "LEGACY", "WALL_MIN", "rollback"))
    assert selector.choose(candidate["scope"], reg.begin_request("WALL_MIN"), eligible)["method"] == "LEGACY_V1"
    assert selector.choose(candidate["scope"], wall, eligible)["method"] == "GPU_HYBRID"


def test_new_session_can_reverse_cpu_preference(tmp_path, authority):
    costs = {"CPU_SERIAL": (100, 100), "CPU_PARALLEL/W6": (70, 400), "GPU_HYBRID": (30, 180)}
    reg, _, candidate, _, profile, _ = setup_flow(tmp_path, authority, costs=costs)
    for goal, expected in [("WALL_MIN", "GPU_HYBRID"), ("CPU_MIN", "CPU_SERIAL")]:
        reg.activate(approval(authority[1], reg, profile["id"], goal, goal))
        assert selector.choose(candidate["scope"], reg.begin_request(goal), list(costs))["method"] == expected


def test_two_profiles_rollback_to_previous_verified(tmp_path, authority):
    reg, _, candidate, _, profile, _ = setup_flow(tmp_path, authority)
    reg.activate(approval(authority[1], reg, profile["id"]))
    old = reg.begin_request("WALL_MIN")
    paths = panel(tmp_path / "raw_b", session="NEW_SYNTHETIC_B")
    ingest = collector.Ingest(tmp_path / "executor_b")
    newer = ingest.collect(paths)
    prof_b = reg.admit(newer, inspector.inspect_and_sign(newer, authority[0]))
    reg.activate(approval(authority[1], reg, prof_b["id"], decision_id="b"))
    reg.activate(approval(authority[1], reg, profile["id"], decision_id="back_a"))
    assert reg.begin_request("WALL_MIN").profile_bytes == old.profile_bytes
    assert selector.choose(newer["scope"], reg.begin_request("WALL_MIN"), ["CPU_SERIAL", "GPU_HYBRID"])["method"] == "LEGACY_V1"


@pytest.mark.parametrize("field", ["session_id", "environment", "initial_state_sha256", "p", "N"])
def test_no_scope_reuse(tmp_path, authority, field):
    reg, _, candidate, _, profile, _ = setup_flow(tmp_path, authority)
    reg.activate(approval(authority[1], reg, profile["id"]))
    scope = copy.deepcopy(candidate["scope"])
    scope[field] = "DIFFERENT" if field not in ("N", "p") else 14
    assert selector.choose(scope, reg.begin_request("WALL_MIN"), ["CPU_SERIAL", "GPU_HYBRID"])["method"] == "LEGACY_V1"


@pytest.mark.parametrize("fault", ["source_bytes", "candidate_time", "mixed_session", "mixed_machine", "duplicate", "missing_repeat", "cpu_accounting", "wall_accounting", "p", "initial", "result", "domain", "spread", "real_claim", "gpu_N14"])
def test_inspector_refuses_and_keeps_faults(tmp_path, authority, fault):
    paths = panel(tmp_path / "raw")
    ingest = collector.Ingest(tmp_path / "executor")
    if fault not in ("source_bytes", "candidate_time"):
        obj = read(paths[-1])
        if fault == "mixed_session": obj["scope"]["session_id"] = "OTHER"
        elif fault == "mixed_machine": obj["scope"]["environment"]["cpu_model"] = "OTHER"
        elif fault == "duplicate": obj["run_id"] = read(paths[-2])["run_id"]
        elif fault == "missing_repeat": paths = paths[:-1]
        elif fault == "cpu_accounting": obj["aggregate_cpu_ns"] += 1
        elif fault == "wall_accounting": obj["wall_ns"] = 1
        elif fault == "p": obj["precision"] = 162
        elif fault == "initial": obj["initial_state"]["test_corruption"] = True
        elif fault == "result": obj["result"]["completed_steps"] -= 1
        elif fault == "domain": obj["domain"] = "UNSUPPORTED"
        elif fault == "spread": obj["wall_ns"] *= 2
        elif fault == "real_claim": obj["measurement_kind"] = "OBSERVED_REAL"
        elif fault == "gpu_N14": obj["scope"]["N"] = 14
        if fault != "missing_repeat": paths[-1].write_bytes(canonical(obj))
    candidate = ingest.collect(paths)
    if fault == "source_bytes": paths[-1].write_bytes(paths[-1].read_bytes() + b" ")
    if fault == "candidate_time": candidate["rows"][0]["observations"][0]["wall_ns"] = 1
    receipt = inspector.inspect_and_sign(candidate, authority[0])
    ingest.record_receipt(candidate, receipt)
    assert receipt["body"]["verdict"] == "REFUSED"
    assert ingest.history()[-1]["payload"]["state"] == "CANDIDATE"
    assert all(path.exists() for path in paths)
    reg = manager.Registry(tmp_path / "manager", authority[2])
    with pytest.raises(ValueError): reg.admit(candidate, receipt)
    assert reg.rejections.history()
    assert not reg.profiles()


def test_integrity_failure_stops_ingest(tmp_path, authority):
    reg, ingest, candidate, _, _, _ = setup_flow(tmp_path, authority)
    path = Path(candidate["sources"][0]["path"])
    path.write_bytes(path.read_bytes() + b" ")
    receipt = inspector.inspect_and_sign(candidate, authority[0])
    ingest.record_receipt(candidate, receipt)
    assert ingest.stopped()
    with pytest.raises(ValueError, match="STOP"):
        ingest.collect(panel(tmp_path / "next"))


@pytest.mark.parametrize("fault", ["unsigned", "forged_key", "modified_body", "wrong_verifier", "wrong_protocol", "wrong_candidate"])
def test_forged_inspector_approval_blocked(tmp_path, authority, fault):
    reg, _, candidate, receipt, _, _ = setup_flow(tmp_path, authority)
    attack = copy.deepcopy(receipt)
    if fault == "unsigned": attack["signature"] = ""
    elif fault == "forged_key": attack["signature"] = Ed25519PrivateKey.generate().sign(b"AEL1_RECEIPT\0" + canonical(attack["body"])).hex()
    elif fault == "modified_body": attack["body"]["rows"][0]["observations"][0]["wall_ns"] = 1
    else:
        attack["body"][{"wrong_verifier": "verifier_sha256", "wrong_protocol": "protocol_sha256", "wrong_candidate": "candidate_sha256"}[fault]] = "0" * 64
        attack["signature"] = authority[0].sign(b"AEL1_RECEIPT\0" + canonical(attack["body"])).hex()
    with pytest.raises(ValueError): reg.admit(candidate, attack)
    assert reg.rejections.history()[-1]["payload"]["operation"] == "ADMIT"


@pytest.mark.parametrize("fault", ["unsigned", "wrong_key", "profile", "predecessor", "goal", "production", "replay"])
def test_bad_manager_approval_blocked(tmp_path, authority, fault):
    reg, _, _, _, profile, _ = setup_flow(tmp_path, authority)
    ticket = approval(authority[1], reg, profile["id"])
    if fault == "unsigned": ticket["signature"] = ""
    elif fault == "wrong_key": ticket = approval(authority[0], reg, profile["id"])
    elif fault == "replay": reg.activate(ticket)
    else:
        field, val = {"profile": ("profile_id", "missing"), "predecessor": ("predecessor", "stale"),
                      "goal": ("goal", "ENERGY_MIN"), "production": ("mode", "PRODUCTION")}[fault]
        ticket["body"][field] = val
        ticket["signature"] = authority[1].sign(b"AEL1_ACTIVATION\0" + canonical(ticket["body"])).hex()
    prior = reg.version()
    with pytest.raises(ValueError): reg.activate(ticket)
    assert reg.version() == prior and reg.rejections.history()


def test_failed_rollback_stops_new_requests(tmp_path, authority):
    reg, _, _, _, profile, _ = setup_flow(tmp_path, authority)
    reg.activate(approval(authority[1], reg, profile["id"]))
    version = reg.version()
    ticket = approval(authority[1], reg, "missing_prior", decision_id="bad_rollback")
    with pytest.raises(ValueError): reg.rollback(ticket)
    assert reg.version() == version
    with pytest.raises(ValueError, match="STOP"): reg.begin_request("WALL_MIN")


def test_profile_and_ledger_tamper_detected(tmp_path, authority):
    reg, _, _, _, profile, _ = setup_flow(tmp_path, authority)
    reg.activate(approval(authority[1], reg, profile["id"]))
    p = reg.directory / "profiles" / (profile["id"] + ".json")
    p.write_bytes(p.read_bytes() + b" ")
    with pytest.raises(ValueError, match="PROFILE_INTEGRITY"): reg.begin_request("WALL_MIN")
    ledger = Ledger(tmp_path / "ledger")
    ledger.append({"x": 1})
    ledger.append({"x": 2})
    event = read(ledger.directory / "event_000000.json")
    event["payload"]["x"] = 3
    (ledger.directory / "event_000000.json").write_bytes(canonical(event))
    with pytest.raises(ValueError, match="LEDGER_INTEGRITY"): ledger.history()


def test_n14_cpu_learning_never_enables_gpu(tmp_path, authority):
    reg, _, candidate, _, profile, _ = setup_flow(tmp_path, authority, N=14)
    reg.activate(approval(authority[1], reg, profile["id"]))
    methods = ["CPU_SERIAL", "CPU_PARALLEL/W6", "GPU_HYBRID"]
    assert selector.choose(candidate["scope"], reg.begin_request("WALL_MIN"), methods)["method"] == "CPU_PARALLEL/W6"
    gap = collector.gaps(candidate, candidate["scope"], methods, [profile])
    assert "GPU_HYBRID" in gap["unsupported_methods"]


def test_cost_proposal_is_not_authorization():
    facts = dict(goal="CPU_MIN", gain_lower_ns=10, reuse_count=100, measurement_upper_ns=100,
                 verification_upper_ns=100, learning_upper_ns=100, risk="LOW", correctness_eligible=True,
                 resource_allowance_ns=1000, resource_required_ns=300)
    assert value.assess(**facts)["status"] == "PROPOSE_ONLY"
    assert value.assess(**facts)["execution_authorized"] is False
    assert value.assess(**facts)["actual_net_profit"] == "UNCONFIRMED"
    for field in ["gain_lower_ns", "reuse_count", "verification_upper_ns", "learning_upper_ns", "risk", "resource_allowance_ns"]:
        missing = dict(facts); missing[field] = None
        assert value.assess(**missing)["status"] == "DEFER_INFORMATION_NEEDED"
    assert value.assess(**dict(facts, correctness_eligible=False))["status"] == "DEFER_RISK_OR_ELIGIBILITY"
    assert value.assess(**dict(facts, resource_allowance_ns=1))["status"] == "DEFER_BUDGET"
    assert value.assess(**dict(facts, reuse_count=1))["status"] == "DEFER_NO_NET_GAIN"
    assert value.assess(**dict(facts, risk="MISMATCH"))["status"] == "STOP"
    with pytest.raises(ValueError): value.assess(**dict(facts, gain_lower_ns=True))


def test_collector_cannot_self_promote(tmp_path):
    ingest = collector.Ingest(tmp_path / "executor")
    candidate = ingest.collect(panel(tmp_path / "raw"))
    with pytest.raises(ValueError): ingest.mark_verified(candidate, {"state": "VERIFIED"}, None)
    assert not hasattr(ingest, "activate") and not hasattr(ingest, "sign")


def test_inspector_import_boundary():
    tree = ast.parse(Path(inspector.__file__).read_text(encoding="utf-8"))
    imports = [node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
    imports += [name.name for node in ast.walk(tree) if isinstance(node, ast.Import) for name in node.names]
    assert not any(any(forbidden in name for forbidden in ["collector", "manager", "selector", "engine", "a_reference", "adaptive_execution_v1"]) for name in imports)


def test_offline_gate_refuses_local_and_unsigned_authorization(tmp_path, monkeypatch):
    from experiments.adaptive_execution_learning_v1 import offline
    ticket = {"gate": "ADAPTIVE_EXECUTION_LEARNING_V1", "scope": "OFFLINE_ONLY", "explicit_user_approval": True,
              "approval_reference": "test only", "instance_id": "123", "code_seal_sha256": "pin", "new_trajectories": 0, "gpu_calls": 0}
    path = tmp_path / "auth.json"; write_new(path, ticket)
    monkeypatch.setattr(offline.platform, "system", lambda: "Windows")
    with pytest.raises(ValueError, match="EXECUTION_SURFACE"): offline.authorize(path, "pin")
    monkeypatch.setattr(offline.platform, "system", lambda: "Linux")
    monkeypatch.setenv("CONTAINER_ID", "123")
    assert offline.authorize(path, "pin")["scope"] == "OFFLINE_ONLY"
    ticket["explicit_user_approval"] = False; path.write_bytes(canonical(ticket))
    with pytest.raises(ValueError, match="USER_APPROVAL"): offline.authorize(path, "pin")
