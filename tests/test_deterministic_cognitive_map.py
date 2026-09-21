import inspect
from dataclasses import replace
from pathlib import Path

from engine.deterministic import (
    CognitiveMapAdapter,
    build_cognitive_map,
    evaluate_cognitive_map_claims,
    initial_environment_state,
    load_environment_world_spec,
    make_cognitive_map_challenge,
)
import engine.deterministic.cognitive_map as cognitive_map_module

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "worlds" / "deterministic_environment_v1.json"


def _queries():
    return (
        {"query_id": "local-source", "kind": "local_state", "point": [4, 4]},
        {"query_id": "blocked-shortest", "kind": "shortest_path", "start": [20, 20], "goal": [21, 20]},
        {"query_id": "blocked-two", "kind": "reachable_within", "start": [20, 20], "goal": [21, 20], "max_steps": 2},
        {"query_id": "blocked-three", "kind": "reachable_within", "start": [20, 20], "goal": [21, 20], "max_steps": 3},
        {"query_id": "wrapped-neighbor", "kind": "shortest_path", "start": [0, 0], "goal": [31, 0]},
    )


def test_sparse_cognitive_map_keeps_relevant_state_and_topology() -> None:
    spec = load_environment_world_spec(EXAMPLE); state = initial_environment_state(spec)
    cognitive_map = build_cognitive_map(spec, state)

    assert cognitive_map.full_cell_count == 1024
    assert cognitive_map.stored_cell_count == 7
    assert cognitive_map.source_state_digest == state.digest
    assert cognitive_map.cell((4, 4), spec.solute_kinds).water == 6
    assert cognitive_map.cell((0, 0), spec.solute_kinds).water == 0
    assert cognitive_map.blocked_edges == (((20, 20), (21, 20)),)


def test_cognitive_map_answers_state_path_and_reachability_queries() -> None:
    spec = load_environment_world_spec(EXAMPLE); challenge = make_cognitive_map_challenge(spec, _queries())
    claims = CognitiveMapAdapter().respond(challenge, spec)
    evaluation = evaluate_cognitive_map_claims(challenge, claims, spec)
    by_id = {claim.claim_id: claim for claim in claims.claims}

    assert evaluation.complete_match is True
    assert len(evaluation.verified_claim_ids) == 5
    assert by_id["blocked-shortest"].payload["answer"]["steps"] == 3
    assert by_id["blocked-two"].payload["answer"]["reachable"] is False
    assert by_id["blocked-three"].payload["answer"]["reachable"] is True
    assert by_id["wrapped-neighbor"].payload["answer"]["steps"] == 1


def test_external_evaluator_accepts_different_minimum_path() -> None:
    spec = load_environment_world_spec(EXAMPLE); challenge = make_cognitive_map_challenge(spec, _queries())
    claims = CognitiveMapAdapter().respond(challenge, spec); changed = list(claims.claims)
    index = next(i for i, claim in enumerate(changed) if claim.claim_id == "blocked-shortest")
    alternate = [[20, 20], [20, 21], [21, 21], [21, 20]]
    changed[index] = replace(changed[index], payload={**changed[index].payload,
                                                      "answer": {"path": alternate, "steps": 3}})
    alternate_claims = replace(claims, claims=tuple(changed))

    evaluation = evaluate_cognitive_map_claims(challenge, alternate_claims, spec)

    assert "blocked-shortest" in evaluation.verified_claim_ids
    assert evaluation.complete_match is True


def test_external_evaluator_rejects_valid_but_nonminimum_path() -> None:
    spec = load_environment_world_spec(EXAMPLE); challenge = make_cognitive_map_challenge(spec, _queries())
    claims = CognitiveMapAdapter().respond(challenge, spec); changed = list(claims.claims)
    index = next(i for i, claim in enumerate(changed) if claim.claim_id == "blocked-shortest")
    detour = [[20, 20], [20, 21], [20, 22], [21, 22], [21, 21], [21, 20]]
    changed[index] = replace(changed[index], payload={**changed[index].payload,
                                                      "answer": {"path": detour, "steps": 5}})

    evaluation = evaluate_cognitive_map_claims(challenge, replace(claims, claims=tuple(changed)), spec)

    assert evaluation.falsified_claim_ids == ("blocked-shortest",)
    assert evaluation.findings[0]["minimum_steps"] == 3


def test_cognitive_map_challenge_and_response_are_read_only_and_reproducible() -> None:
    spec = load_environment_world_spec(EXAMPLE); before = spec.digest
    first_challenge = make_cognitive_map_challenge(spec, _queries())
    second_challenge = make_cognitive_map_challenge(spec, _queries())
    adapter = CognitiveMapAdapter(); first = adapter.respond(first_challenge, spec); second = adapter.respond(second_challenge, spec)

    assert spec.digest == before
    assert first_challenge == second_challenge
    assert first == second
    assert first.digest == second.digest
    assert adapter.manifest.internal_representation == "private sparse topology and relevant-state map"


def test_cognitive_map_does_not_call_a_transition_or_forecast() -> None:
    source = inspect.getsource(cognitive_map_module)

    assert "step_environment_world" not in source
    assert "forecast_environment_world" not in source
    assert "run_environment_world" not in source
    assert "import random" not in source
