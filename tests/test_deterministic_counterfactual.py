import inspect
from pathlib import Path

from engine.deterministic import (
    CounterfactualBranchAdapter,
    PrivateTraceWriter,
    build_approved_change_view,
    execute_counterfactual_plan,
    load_environment_world_spec,
    make_counterfactual_challenge,
    trace_environment_run,
)

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "worlds" / "deterministic_environment_v1.json"


def _make(tmp_path: Path):
    spec = load_environment_world_spec(EXAMPLE); source = tmp_path / "raw"
    writer = PrivateTraceWriter(source, "raw"); final = trace_environment_run(spec, writer)
    writer.close(spec.digest, final.digest)
    view = build_approved_change_view(source, spec, 7)
    challenge = make_counterfactual_challenge(view, spec); adapter = CounterfactualBranchAdapter(3)
    claims, plan = adapter.respond(challenge, view, spec)
    boundary, evaluation = execute_counterfactual_plan(challenge, claims, plan, view, spec)
    return spec, source, final, view, challenge, adapter, claims, plan, boundary, evaluation


def test_plan_preserves_control_action_design_and_every_branch(tmp_path: Path) -> None:
    _, _, _, _, _, _, claims, plan, _, evaluation = _make(tmp_path)

    assert tuple(item.branch_id for item in plan.branches) == (
        "control-no-action", "heat-pulse-small", "heat-pulse-large",
        "heat-pulse-far", "block-source-edge")
    assert {item.branch_kind for item in plan.branches} == {"control", "action", "design"}
    assert evaluation.control_present is True
    assert evaluation.all_branches_retained is True
    assert len(claims.claims) == len(plan.branches) == 5


def test_every_branch_gets_low_and_medium_but_exact_budget_is_three(tmp_path: Path) -> None:
    *_, plan, boundary, evaluation = _make(tmp_path)
    by_fidelity = {}
    for result in evaluation.fidelity_results: by_fidelity.setdefault(result.fidelity, []).append(result)

    assert len(by_fidelity["low"]) == 5
    assert len(by_fidelity["medium"]) == 5
    assert len(by_fidelity["exact"]) == 5
    assert evaluation.exact_branch_ids == ("control-no-action", "heat-pulse-large", "block-source-edge")
    assert evaluation.deferred_branch_ids == ("heat-pulse-small", "heat-pulse-far")
    assert sum(item.status == "completed" for item in by_fidelity["exact"]) == 3
    assert sum(item.status == "deferred_budget" for item in by_fidelity["exact"]) == 2
    assert boundary.verified_claim_ids == evaluation.exact_branch_ids
    assert boundary.untested_claim_ids == evaluation.deferred_branch_ids


def test_no_action_exact_branch_matches_observed_next_tick(tmp_path: Path) -> None:
    _, _, observed_final, _, _, _, _, _, _, evaluation = _make(tmp_path)
    exact = next(item for item in evaluation.fidelity_results
                 if item.branch_id == "control-no-action" and item.fidelity == "exact")

    assert exact.payload["final_state_digest"] == observed_final.digest


def test_intervention_energy_is_accounted_and_design_is_separate_spec(tmp_path: Path) -> None:
    spec, _, _, _, _, _, _, _, _, evaluation = _make(tmp_path)
    heat = next(item for item in evaluation.fidelity_results
                if item.branch_id == "heat-pulse-large" and item.fidelity == "exact")
    design = next(item for item in evaluation.fidelity_results
                  if item.branch_id == "block-source-edge" and item.fidelity == "exact")

    assert heat.payload["accounted_energy"] == 10
    assert heat.payload["spec_digest"] == spec.digest
    assert design.payload["spec_digest"] != spec.digest


def test_plan_has_no_aggregate_score_or_winner(tmp_path: Path) -> None:
    *_, plan, _, evaluation = _make(tmp_path)
    canonical = plan.canonical()

    assert "no aggregate score" in plan.ranking_policy
    assert canonical.get("score") is None
    assert canonical.get("winner") is None
    assert evaluation.canonical().get("winner") is None


def test_counterfactual_execution_is_reproducible_and_does_not_modify_source(tmp_path: Path) -> None:
    spec, _, _, view, challenge, adapter, claims, plan, _, first = _make(tmp_path)
    before = spec.digest
    second_boundary, second = execute_counterfactual_plan(challenge, claims, plan, view, spec)

    assert first == second
    assert first.digest == second.digest
    assert spec.digest == before
    assert second_boundary.claim_set_digest == claims.digest


def test_branch_adapter_only_proposes_and_does_not_call_exact_a() -> None:
    source = inspect.getsource(CounterfactualBranchAdapter.respond)

    assert "step_environment_world" not in source
    assert "run_environment_world" not in source
    assert "forecast_environment_world" not in source
