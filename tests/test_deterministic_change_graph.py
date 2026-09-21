import inspect
import json
from dataclasses import replace
from pathlib import Path

import pytest

from engine.deterministic import (
    ChangeGraphAdapter,
    CognitiveMapAdapter,
    PrivateTraceWriter,
    build_approved_change_view,
    build_change_graph,
    evaluate_change_graph_claims,
    evaluate_cognitive_map_claims,
    load_environment_world_spec,
    make_change_graph_challenge,
    make_cognitive_map_challenge,
    trace_environment_run,
)
import engine.deterministic.change_graph as change_graph_module

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "worlds" / "deterministic_environment_v1.json"


def _source_trace(tmp_path: Path):
    spec = load_environment_world_spec(EXAMPLE); run_dir = tmp_path / "raw-private"
    writer = PrivateTraceWriter(run_dir, "raw-private")
    final = trace_environment_run(spec, writer); writer.close(spec.digest, final.digest)
    return spec, run_dir, final


def _queries():
    return (
        {"query_id": "digest", "kind": "reconstructed_state_digest"},
        {"query_id": "local", "kind": "local_state", "point": [4, 4], "solute_kinds": 2},
        {"query_id": "last-cells", "kind": "last_change", "path": "$.cells"},
        {"query_id": "cost", "kind": "graph_cost"},
    )


def test_broker_returns_path_free_verified_delta_view(tmp_path: Path) -> None:
    spec, run_dir, final = _source_trace(tmp_path)
    view = build_approved_change_view(run_dir, spec, 8)
    rendered = json.dumps(view.canonical(), sort_keys=True)

    assert str(run_dir) not in rendered
    assert "raw_vault_path" in view.hidden_content
    assert "B_records" in view.hidden_content
    assert len(view.events) == 64
    assert view.target_tick == 8
    assert view.events[-1].after_digest == final.digest


def test_change_graph_reconstructs_final_state_without_a_transition(tmp_path: Path) -> None:
    spec, run_dir, final = _source_trace(tmp_path)
    graph = build_change_graph(build_approved_change_view(run_dir, spec, 8))

    assert graph.reconstructed_state_digest == final.digest
    assert len(graph.nodes) == 64
    assert graph.nodes[-1].parent_event_ids
    assert graph.last_change("$.cells") is not None
    assert graph.delta_operation_count > 0


def test_change_graph_adapter_claims_are_verified_by_private_trace(tmp_path: Path) -> None:
    spec, run_dir, final = _source_trace(tmp_path); view = build_approved_change_view(run_dir, spec, 8)
    challenge = make_change_graph_challenge(view, _queries()); adapter = ChangeGraphAdapter()
    claims = adapter.respond(challenge, view)
    evaluation = evaluate_change_graph_claims(challenge, claims, run_dir, spec)
    by_id = {item.claim_id: item for item in claims.claims}

    assert evaluation.complete_match is True
    assert len(evaluation.verified_claim_ids) == 4
    assert by_id["digest"].payload["answer"]["state_digest"] == final.digest
    assert by_id["last-cells"].payload["answer"]["event_id"].startswith("a-stage-")
    assert by_id["cost"].payload["answer"]["nodes"] == 64


def test_private_evaluator_falsifies_wrong_reconstruction(tmp_path: Path) -> None:
    spec, run_dir, _ = _source_trace(tmp_path); view = build_approved_change_view(run_dir, spec, 8)
    challenge = make_change_graph_challenge(view, _queries()); claims = ChangeGraphAdapter().respond(challenge, view)
    changed = list(claims.claims); index = next(i for i, item in enumerate(changed) if item.claim_id == "digest")
    changed[index] = replace(changed[index], payload={**changed[index].payload,
                                                      "answer": {"state_digest": "wrong", "target_tick": 8}})
    evaluation = evaluate_change_graph_claims(challenge, replace(claims, claims=tuple(changed)), run_dir, spec)

    assert evaluation.falsified_claim_ids == ("digest",)


def test_approved_view_tampering_is_detected_before_graph_use(tmp_path: Path) -> None:
    spec, run_dir, _ = _source_trace(tmp_path); view = build_approved_change_view(run_dir, spec, 8)
    event = next(item for item in view.events if item.delta); changed_delta = list(event.delta)
    changed_delta[0] = {**changed_delta[0], "after": 999}
    bad_event = replace(event, delta=tuple(changed_delta))
    index = view.events.index(event)
    bad_view = replace(view, events=view.events[:index] + (bad_event,) + view.events[index + 1:])

    with pytest.raises(ValueError, match="after digest mismatch"):
        build_change_graph(bad_view)


def test_change_graph_and_cognitive_map_are_distinct_candidates(tmp_path: Path) -> None:
    spec, run_dir, _ = _source_trace(tmp_path); view = build_approved_change_view(run_dir, spec, 8)
    change = ChangeGraphAdapter()
    cognitive = CognitiveMapAdapter()

    assert change.manifest.internal_representation != cognitive.manifest.internal_representation
    assert change.manifest.accepted_observation_views != cognitive.manifest.accepted_observation_views
    assert "reconstruct_state" in change.manifest.capabilities
    assert "answer_shortest_path" in cognitive.manifest.capabilities


def test_change_graph_adapter_never_calls_a_transition_or_forecast() -> None:
    source = inspect.getsource(change_graph_module)

    assert "step_environment_world" not in source
    assert "run_environment_world" not in source
    assert "forecast_environment_world" not in source
    assert "import random" not in source
