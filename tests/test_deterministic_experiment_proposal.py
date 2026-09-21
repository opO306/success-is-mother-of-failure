import inspect
import json
from dataclasses import replace
from pathlib import Path

import pytest

from engine.deterministic import (
    EnvironmentWorldSpec,
    ExperimentProposalAdapter,
    PrivateTraceWriter,
    TheoryRevisionAdapter,
    TheoryVersion,
    build_residual_pattern,
    collect_omitted_component_residual,
    make_experiment_proposal_challenge,
    make_theory_revision_challenge,
    require_experiment_authorization,
    review_experiment_proposal,
    trace_environment_run,
)

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "worlds" / "deterministic_open_water_cycle_v3.json"


def _revision_context(tmp_path: Path):
    raw_base = json.loads(BASE.read_text(encoding="utf-8")); theory = TheoryVersion(
        "limited-no-vapor-v1", None, ("heat", "water", "mineral", "solute"), ("local-transport",))
    residuals = []; training_specs = []
    for index in range(4):
        raw = json.loads(json.dumps(raw_base)); raw["causal_world"]["world_id"] = f"training-{index}"
        raw["causal_world"]["execution"]["ticks"] = 2; raw["cells"][1]["vapor"] = 4 + index * 2
        spec = EnvironmentWorldSpec.from_mapping(raw); training_specs.append(spec.digest)
        run_dir = tmp_path / f"world-{index}"; writer = PrivateTraceWriter(run_dir, f"world-{index}")
        final = trace_environment_run(spec, writer); writer.close(spec.digest, final.digest)
        residuals.append(collect_omitted_component_residual(run_dir, f"world-{index}", spec, theory,
                                                            "vapor", 0, 1))
    pattern = build_residual_pattern(tuple(residuals), 3)
    revision_challenge = make_theory_revision_challenge(pattern, theory)
    _, revisions = TheoryRevisionAdapter().respond(revision_challenge, pattern, theory)
    challenge = make_experiment_proposal_challenge(pattern, revisions, theory)
    adapter = ExperimentProposalAdapter(); claims, proposal = adapter.respond(
        challenge, pattern, revisions, theory, raw_base)
    return raw_base, theory, pattern, revisions, tuple(training_specs), challenge, adapter, claims, proposal


def test_proposal_contains_trace_control_and_unseen_no_action_worlds(tmp_path: Path) -> None:
    _, _, _, _, training, _, _, _, proposal = _revision_context(tmp_path)
    by_id = {item.arm_id: item for item in proposal.arms}

    assert tuple(by_id) == ("trace-audit-control", "zero-vapor-control", "heldout-vapor-5", "heldout-vapor-13")
    assert all(item.no_action_control for item in proposal.arms)
    assert by_id["trace-audit-control"].sealed_spec is None
    assert by_id["zero-vapor-control"].tick_budget == 2
    heldout = {item.spec_digest for item in proposal.arms if item.spec_digest}
    assert not heldout & set(training)
    assert len(heldout) == 3


def test_every_revision_candidate_has_a_distinguishing_arm(tmp_path: Path) -> None:
    _, _, _, revisions, training, challenge, _, claims, proposal = _revision_context(tmp_path)
    boundary, review = review_experiment_proposal(challenge, claims, proposal, revisions, training)

    assert review.governance_valid is True
    assert review.missing_revision_ids == ()
    assert set(review.covered_revision_ids) == {item.proposal_id for item in revisions.proposals}
    assert review.scientific_status == "not-run"
    assert boundary.verified_claim_ids == ()
    assert boundary.untested_claim_ids == ("held-out-experiment-proposal",)


def test_execution_is_blocked_until_separate_explicit_approval(tmp_path: Path) -> None:
    *_, proposal = _revision_context(tmp_path)

    assert proposal.approval_status == "pending-user-approval"
    assert proposal.execution_allowed is False
    assert proposal.approval_required is True
    assert proposal.automatic_execution is False
    with pytest.raises(PermissionError, match="pending explicit user approval"):
        require_experiment_authorization(proposal)


def test_tampered_execution_permission_fails_governance_review(tmp_path: Path) -> None:
    _, _, _, revisions, training, challenge, _, claims, proposal = _revision_context(tmp_path)
    tampered = replace(proposal, execution_allowed=True)
    boundary, review = review_experiment_proposal(challenge, claims, tampered, revisions, training)

    assert review.governance_valid is False
    assert review.execution_blocked_pending_approval is False
    assert boundary.falsified_claim_ids == ("held-out-experiment-proposal",)


def test_proposal_is_reproducible_and_does_not_modify_parent(tmp_path: Path) -> None:
    raw, theory, pattern, revisions, _, challenge, adapter, first_claims, first = _revision_context(tmp_path)
    before = theory.digest; second_claims, second = adapter.respond(challenge, pattern, revisions, theory, raw)

    assert first == second
    assert first.digest == second.digest
    assert first_claims == second_claims
    assert theory.digest == before
    assert first.approval_status == "pending-user-approval"
    assert first.execution_allowed is False


def test_experiment_adapter_does_not_execute_a() -> None:
    source = inspect.getsource(ExperimentProposalAdapter.respond)

    assert "step_environment_world" not in source
    assert "run_environment_world" not in source
    assert "trace_environment_run" not in source
