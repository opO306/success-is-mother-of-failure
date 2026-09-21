import json
from pathlib import Path

import pytest

from engine.deterministic import (
    CognitiveMapAdapter,
    PrivateTraceWriter,
    TracePolicy,
    evaluate_cognitive_map_claims,
    load_environment_world_spec,
    make_cognitive_map_challenge,
    run_environment_world,
    trace_b_exchange,
    trace_environment_run,
    verify_trace,
)

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "worlds" / "deterministic_environment_v1.json"


def _build_trace(tmp_path: Path):
    spec = load_environment_world_spec(EXAMPLE); run_dir = tmp_path / "private-run"
    writer = PrivateTraceWriter(run_dir, "private-run")
    final_state = trace_environment_run(spec, writer)
    queries = ({"query_id": "path", "kind": "shortest_path", "start": [20, 20], "goal": [21, 20]},)
    challenge = make_cognitive_map_challenge(spec, queries); adapter = CognitiveMapAdapter()
    claims = adapter.respond(challenge, spec); evaluation = evaluate_cognitive_map_claims(challenge, claims, spec)
    trace_b_exchange(writer, adapter.manifest, challenge, claims, evaluation)
    manifest = writer.close(spec.digest, final_state.digest)
    return spec, run_dir, final_state, manifest


def test_full_trace_records_every_tick_and_every_stage(tmp_path: Path) -> None:
    spec, run_dir, final_state, manifest = _build_trace(tmp_path)
    records = [json.loads(line) for line in (run_dir / "records.jsonl").read_text(encoding="utf-8").splitlines()]

    tick_starts = [x for x in records if x["kind"] == "tick_start"]
    tick_commits = [x for x in records if x["kind"] == "tick_commit"]
    stages = [x for x in records if x["kind"] == "stage_commit"]
    assert len(tick_starts) == len(tick_commits) == spec.causal_world.ticks == 8
    assert len(stages) == spec.causal_world.ticks * 8
    assert all("full_snapshot" in item["payload"] for item in tick_starts + tick_commits)
    assert all("after_snapshot" in item["payload"] and "delta" in item["payload"] for item in stages)
    assert tick_commits[-1]["payload"]["state_digest"] == final_state.digest == manifest["final_state_digest"]


def test_trace_is_nonintervening_and_fully_verifiable(tmp_path: Path) -> None:
    spec, run_dir, traced, manifest = _build_trace(tmp_path)
    ordinary = run_environment_world(spec).final_state
    verification = verify_trace(run_dir)

    assert traced == ordinary
    assert verification["valid"] is True
    assert verification["record_count"] == manifest["record_count"]
    assert tuple(verification["tick_digests"]) == tuple(range(1, 9))


def test_raw_vault_path_is_not_disclosed_to_b_messages(tmp_path: Path) -> None:
    _, run_dir, _, manifest = _build_trace(tmp_path)
    text = (run_dir / "records.jsonl").read_text(encoding="utf-8")
    b_records = [json.loads(line) for line in text.splitlines() if json.loads(line)["stream"] == "B"]

    assert str(run_dir) not in json.dumps(b_records)
    observation = next(item for item in b_records if item["kind"] == "observation_contract")
    assert observation["payload"]["raw_trace_path_disclosed"] is False
    assert manifest["access_policy"]["raw_visible_to_brains"] is False
    assert manifest["access_policy"]["automatic_deletion"] is False


def test_trace_keeps_all_b_boundary_actions(tmp_path: Path) -> None:
    _, run_dir, _, _ = _build_trace(tmp_path)
    records = [json.loads(line) for line in (run_dir / "records.jsonl").read_text(encoding="utf-8").splitlines()]
    kinds = [item["kind"] for item in records if item["stream"] == "B"]

    assert kinds == ["capability_manifest", "observation_contract", "claim_submitted",
                     "claim_set_commit", "boundary_evaluation"]


def test_hash_chain_detects_tampering(tmp_path: Path) -> None:
    _, run_dir, _, _ = _build_trace(tmp_path)
    path = run_dir / "records.jsonl"; lines = path.read_text(encoding="utf-8").splitlines()
    changed = json.loads(lines[3]); changed["payload"]["delta_count"] += 1
    lines[3] = json.dumps(changed, sort_keys=True, separators=(",", ":"))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="record hash mismatch"):
        verify_trace(run_dir)


def test_policy_defaults_to_maximum_private_evidence() -> None:
    policy = TracePolicy()

    assert policy.access == "owner-and-fixed-verifier"
    assert policy.raw_visible_to_brains is False
    assert policy.tick_snapshots == "every-tick"
    assert policy.stage_snapshots == "every-stage"
    assert policy.deltas == "lossless"
    assert policy.automatic_deletion is False
