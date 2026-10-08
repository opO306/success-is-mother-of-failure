"""TEST_ONLY end-to-end demonstration with ephemeral independently keyed roles.

This harness provisions its own simulation roots. It cannot produce an operational
inspector approval or activate production. No private key is exported or persisted.
"""
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from . import collector, inspector, manager, selector, value
from .core import HERE, canonical, digest, protocol, raw_hash, write_new
from .synthetic import panel


def run_demo(directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    judge, ruler = Ed25519PrivateKey.generate(), Ed25519PrivateKey.generate()
    public = lambda key: key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()
    roots = manager.TrustRoots(public(judge), public(ruler), digest(protocol()), raw_hash(HERE / "inspector.py"))
    registry = manager.Registry(directory / "rule_manager", roots)
    ingest = collector.Ingest(directory / "executor")
    before = registry.begin_request("WALL_MIN")
    candidate = ingest.collect(panel(directory / "raw_new_session", session="DEMO_NEW_SYNTHETIC_SESSION"))
    write_new(directory / "candidate.json", candidate)
    write_new(directory / "gaps_before.json", collector.gaps(candidate, candidate["scope"], ["CPU_SERIAL", "CPU_PARALLEL/W6", "GPU_HYBRID"], []))
    receipt = inspector.inspect_and_sign(candidate, judge)
    write_new(directory / "inspector_receipt.json", receipt)
    ingest.record_receipt(candidate, receipt)
    profile = registry.admit(candidate, receipt)
    ingest.mark_verified(candidate, profile, registry)
    write_new(directory / "verified_test_profile.json", profile)
    write_new(directory / "gaps_after.json", collector.gaps(candidate, candidate["scope"], ["CPU_SERIAL", "CPU_PARALLEL/W6", "GPU_HYBRID"], [profile], registry=registry))
    def activate(target, goal, name, rollback=False):
        body = {"schema": "ael1-activation", "mode": "TEST_ONLY", "profile_id": target, "goal": goal,
                "predecessor": registry.version(), "decision_id": name, "reason": "TEST_ONLY simulated manager approval"}
        approval = {"body": body, "signature": ruler.sign(b"AEL1_ACTIVATION\0" + canonical(body)).hex()}
        (registry.rollback if rollback else registry.activate)(approval)
    methods = ["CPU_SERIAL", "CPU_PARALLEL/W6", "GPU_HYBRID"]
    predictions = {"before": selector.choose(candidate["scope"], before, methods)}
    activate(profile["id"], "WALL_MIN", "wall")
    current = registry.begin_request("WALL_MIN")
    predictions["after_wall"] = selector.choose(candidate["scope"], current, methods)
    predictions["in_flight_unchanged"] = selector.choose(candidate["scope"], before, methods)
    activate(profile["id"], "CPU_MIN", "cpu")
    predictions["after_cpu"] = selector.choose(candidate["scope"], registry.begin_request("CPU_MIN"), methods)
    activate("LEGACY", "WALL_MIN", "rollback", rollback=True)
    predictions["after_rollback"] = selector.choose(candidate["scope"], registry.begin_request("WALL_MIN"), methods)
    other_session = dict(candidate["scope"], session_id="UNMEASURED_OTHER_SESSION")
    predictions["other_session"] = selector.choose(other_session, current, methods)
    write_new(directory / "recommendations.json", predictions)
    write_new(directory / "value_assessment.json", value.assess(goal="CPU_MIN"))
    write_new(directory / "status.json", {"status": "SYNTHETIC_LEARNING_DEMONSTRATED", "mode": "TEST_ONLY",
                                          "real_session_cost_measured": False, "real_net_profit": "UNCONFIRMED",
                                          "production_activation": False, "formula_independence": "UNRESOLVED_SHARED_RWFORCE",
                                          "initial_state": "historical digest reference; full state reconstruction untested"})
