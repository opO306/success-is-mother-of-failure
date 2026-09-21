import inspect
import json
from dataclasses import replace
from pathlib import Path

import pytest

from engine.deterministic import (
    AttachmentDescriptor,
    BrainAdapter,
    CapabilityManifest,
    Claim,
    ClaimSet,
    EvidenceBridge,
    ExactOracleAdapter,
    evaluate_state_digest_claims,
    load_causal_world_spec,
    load_environment_world_spec,
    make_prediction_challenge,
    run_causal_world,
    run_environment_world,
)
import engine.deterministic.b_language as b_language_module
import engine.deterministic.brain_adapter as adapter_module

ROOT = Path(__file__).resolve().parents[1]
CAUSAL = ROOT / "worlds" / "deterministic_bond_cycle_v1.json"
ENVIRONMENT = ROOT / "worlds" / "deterministic_physical_flux_v4.json"
SCHEMA = ROOT / "schemas" / "b_language_boundary_v1.schema.json"


def test_schema_defines_external_boundary_not_reasoning_trace() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))

    assert schema["$schema"].endswith("2020-12/schema")
    assert {"capability_manifest", "observation_contract", "claim_set", "boundary_evaluation"} <= set(schema["$defs"])
    assert "does not prescribe internal representations or reasoning traces" in schema["description"]
    assert "reasoning_trace" not in SCHEMA.read_text(encoding="utf-8")


def test_different_internal_representations_share_only_boundary_capabilities() -> None:
    graph = CapabilityManifest("graph", "causal-graph", "1", ("answer_reachability",),
                               ("event_stream",), "private graph", True)
    latent = CapabilityManifest("latent", "jepa-like", "1", ("predict_query",),
                                ("local_windows",), "private opaque latent", False)

    assert graph.internal_representation != latent.internal_representation
    assert graph.accepted_observation_views != latent.accepted_observation_views
    assert graph.canonical()["format"] == latent.canonical()["format"]


def test_opaque_latent_claim_does_not_need_world_state_or_causal_map() -> None:
    manifest = CapabilityManifest("novel", "unknown-future-model", "1", ("propose_question",),
                                  ("raw_checkpoint",), "uninterpreted private state", False)
    claim = Claim("question-1", "novel_testable_question", "hypothesis", "subject", {"question": "does flux reverse?"})
    attachment = AttachmentDescriptor("private_latent", "latent-digest", "future-format")
    claim_set = ClaimSet("challenge", manifest.digest, (claim,), (), (attachment,))

    rendered = json.dumps(claim_set.canonical(), sort_keys=True)
    assert "WorldState" not in rendered
    assert "CausalMap" not in rendered
    assert claim_set.claims[0].claim_kind == "novel_testable_question"


def test_testable_claim_requires_external_evidence_bridge() -> None:
    claim = Claim("prediction", "anything", "approximate", "subject", {"value": 1})

    with pytest.raises(ValueError, match="needs an evidence bridge"):
        ClaimSet("challenge", "manifest", (claim,), ())


def test_boundary_payload_rejects_floating_point_but_accepts_integer_ratio() -> None:
    with pytest.raises(ValueError, match="floating point"):
        Claim("bad", "prediction", "approximate", "subject", {"probability": 0.5})

    claim = Claim("good", "prediction", "approximate", "subject", {"ratio": {"numerator": 1, "denominator": 2}})
    assert claim.payload["ratio"]["denominator"] == 2


def test_exact_adapter_matches_causal_world_without_prescribing_method() -> None:
    spec = load_causal_world_spec(CAUSAL); challenge = make_prediction_challenge(spec)
    adapter = ExactOracleAdapter(); before = spec.digest
    claims = adapter.respond(challenge, spec)
    evaluation = evaluate_state_digest_claims(challenge, claims, run_causal_world(spec))

    assert isinstance(adapter, BrainAdapter)
    assert evaluation.complete_match is True
    assert evaluation.verified_claim_ids == ("tick-1-state", "tick-2-state", "tick-3-state", "tick-4-state")
    assert adapter.manifest.internal_representation == "private sealed A-transition clone"
    assert "actual_future_checkpoints" in challenge.hidden_fields
    assert spec.digest == before


def test_exact_adapter_matches_environment_world() -> None:
    spec = load_environment_world_spec(ENVIRONMENT); challenge = make_prediction_challenge(spec)
    adapter = ExactOracleAdapter(); first = adapter.respond(challenge, spec); second = adapter.respond(challenge, spec)
    evaluation = evaluate_state_digest_claims(challenge, first, run_environment_world(spec))

    assert evaluation.complete_match is True
    assert first == second
    assert first.digest == second.digest
    assert len(first.claims) == 4


def test_boundary_evaluation_falsifies_wrong_answer_without_changing_run() -> None:
    spec = load_causal_world_spec(CAUSAL); challenge = make_prediction_challenge(spec)
    claims = ExactOracleAdapter().respond(challenge, spec); run = run_causal_world(spec); before = run.digest
    bad_claims = list(claims.claims)
    bad_claims[0] = replace(bad_claims[0], payload={**bad_claims[0].payload, "state_digest": "wrong"})
    bad_set = replace(claims, claims=tuple(bad_claims))

    evaluation = evaluate_state_digest_claims(challenge, bad_set, run)

    assert evaluation.complete_match is False
    assert evaluation.falsified_claim_ids == ("tick-1-state",)
    assert run.digest == before


def test_exact_adapter_rejects_mismatched_challenge() -> None:
    first = load_causal_world_spec(CAUSAL); second = load_environment_world_spec(ENVIRONMENT)
    challenge = make_prediction_challenge(first)

    with pytest.raises(ValueError, match="spec digest"):
        ExactOracleAdapter().respond(challenge, second)


def test_boundary_and_adapter_have_no_random_interface() -> None:
    source = inspect.getsource(b_language_module) + inspect.getsource(adapter_module)

    assert "import random" not in source
    assert "SeededEventSource" not in source
    assert "choice_index" not in source
