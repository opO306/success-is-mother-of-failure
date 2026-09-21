import inspect
import json
from pathlib import Path

from engine.deterministic import (
    EnvironmentWorldSpec,
    PrivateTraceWriter,
    TheoryRevisionAdapter,
    TheoryVersion,
    build_residual_pattern,
    collect_omitted_component_residual,
    make_theory_revision_challenge,
    review_theory_revision_set,
    trace_environment_run,
)
import engine.deterministic.theory_revision as revision_module

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "worlds" / "deterministic_open_water_cycle_v3.json"


def _campaign(tmp_path: Path, count: int = 4):
    raw_base = json.loads(BASE.read_text(encoding="utf-8")); theory = TheoryVersion(
        "limited-no-vapor-v1", None, ("heat", "water", "mineral", "solute"), ("local-transport",))
    residuals = []
    for index in range(count):
        raw = json.loads(json.dumps(raw_base)); raw["causal_world"]["world_id"] = f"vapor-residual-{index}"
        raw["causal_world"]["execution"]["ticks"] = 2
        raw["cells"][1]["vapor"] = 4 + index * 2
        spec = EnvironmentWorldSpec.from_mapping(raw); run_dir = tmp_path / f"world-{index}"
        writer = PrivateTraceWriter(run_dir, f"world-{index}"); final = trace_environment_run(spec, writer)
        writer.close(spec.digest, final.digest)
        residuals.append(collect_omitted_component_residual(run_dir, f"world-{index}", spec, theory,
                                                            "vapor", 0, 1))
    return theory, tuple(residuals)


def test_repeated_pattern_requires_distinct_runs_and_specs(tmp_path: Path) -> None:
    _, residuals = _campaign(tmp_path)
    pattern = build_residual_pattern(residuals, 3)

    assert pattern.repeated is True
    assert pattern.distinct_run_count == 4
    assert pattern.distinct_spec_count == 4
    assert pattern.component == "vapor"
    assert pattern.cause_tier == "state_omission"
    assert all(item.actual_changed_locations for item in residuals)


def test_one_residual_does_not_create_structural_revision(tmp_path: Path) -> None:
    theory, residuals = _campaign(tmp_path, 1)
    pattern = build_residual_pattern(residuals, 3)
    challenge = make_theory_revision_challenge(pattern, theory)
    claims, revisions = TheoryRevisionAdapter().respond(challenge, pattern, theory)

    assert pattern.repeated is False
    assert revisions.proposals == ()
    assert claims.claims == ()
    assert revisions.applied_proposal_id is None


def test_repeated_known_omission_creates_parallel_safe_candidates(tmp_path: Path) -> None:
    theory, residuals = _campaign(tmp_path); pattern = build_residual_pattern(residuals, 3)
    challenge = make_theory_revision_challenge(pattern, theory)
    claims, revisions = TheoryRevisionAdapter().respond(challenge, pattern, theory)
    kinds = {item.proposal_kind for item in revisions.proposals}

    assert kinds == {"observation_error_model", "add_observed_state_variable", "revise_transition_relation"}
    assert all(item.status == "candidate-not-applied" for item in revisions.proposals)
    assert revisions.applied_proposal_id is None
    assert "new_latent_variable" not in kinds
    assert len(claims.claims) == 3
    assert "no automatic application" in revisions.selection_policy


def test_review_keeps_parent_unchanged_and_science_untested(tmp_path: Path) -> None:
    theory, residuals = _campaign(tmp_path); before = theory.digest
    pattern = build_residual_pattern(residuals, 3); challenge = make_theory_revision_challenge(pattern, theory)
    claims, revisions = TheoryRevisionAdapter().respond(challenge, pattern, theory)
    boundary, review = review_theory_revision_set(challenge, claims, revisions, theory)

    assert theory.digest == before
    assert review.parent_unchanged is True
    assert len(review.governance_admissible_ids) == 3
    assert review.governance_rejected_ids == ()
    assert review.scientifically_verified_ids == ()
    assert review.scientifically_untested_ids == review.governance_admissible_ids
    assert boundary.verified_claim_ids == ()
    assert boundary.untested_claim_ids == review.governance_admissible_ids
    assert boundary.complete_match is False


def test_residual_and_revision_generation_are_reproducible(tmp_path: Path) -> None:
    theory, residuals = _campaign(tmp_path); first = build_residual_pattern(residuals, 3)
    second = build_residual_pattern(tuple(reversed(residuals)), 3)
    adapter = TheoryRevisionAdapter(); challenge = make_theory_revision_challenge(first, theory)
    first_claims, first_revisions = adapter.respond(challenge, first, theory)
    second_claims, second_revisions = adapter.respond(challenge, second, theory)

    assert first == second
    assert first.digest == second.digest
    assert first_claims == second_claims
    assert first_revisions == second_revisions


def test_theory_revision_adapter_does_not_call_a_or_apply_proposals() -> None:
    source = inspect.getsource(TheoryRevisionAdapter.respond)

    assert "step_environment_world" not in source
    assert "run_environment_world" not in source
    assert "forecast_environment_world" not in source
    assert "applied_proposal_id" not in source
