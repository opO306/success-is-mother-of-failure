from pathlib import Path

import pytest

from engine.deterministic import (
    BondCountPrediction,
    BoundaryCandidate,
    CausalHypothesis,
    CausalHypothesisSet,
    ControlDefinition,
    ExplorationBudgetExceeded,
    ExplorationPlan,
    HeatCellRoleTarget,
    ParticleRoleTarget,
    RealCausalAExecutor,
    ResearchJournal,
    SweepDimension,
    bind_control,
    generate_candidates,
    load_causal_world_spec,
    observe,
    rebuild_hypothesis_graph,
    rebuild_memory_index,
    rebuild_research_state,
    record_hypothesis_set,
    run_exploration,
    verify_journal,
)

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "worlds" / "deterministic_bond_cycle_v1.json"

HEAT_CONTROL = ControlDefinition(
    "causal.control.local_heat_energy", HeatCellRoleTarget("local_heat_source", 10, 10, "energy"),
    "causal.heat.energy",
)


def test_generate_candidates_is_a_deterministic_full_factorial() -> None:
    plan = ExplorationPlan("P-1", "digest", ("H1",), (SweepDimension("axis.a", (1, 2)),
                                                       SweepDimension("axis.b", ("x", "y"))), "full_factorial", 10)
    first = generate_candidates(plan)
    second = generate_candidates(plan)

    assert len(first) == 4
    assert first == second  # identical plan replay -> identical candidate ids


def test_plan_over_budget_is_rejected_not_truncated() -> None:
    plan = ExplorationPlan("P-1", "digest", ("H1",), (SweepDimension("axis.a", tuple(range(100))),),
                          "full_factorial", 10)
    with pytest.raises(ExplorationBudgetExceeded):
        generate_candidates(plan)


def test_control_binding_resolves_role_to_heat_cell() -> None:
    spec = load_causal_world_spec(EXAMPLE)
    binding = bind_control(HEAT_CONTROL, spec)
    assert binding.role == "local_heat_source"
    assert binding.resolved_identity == "10,10"


def test_particle_role_target_rejects_ambiguous_match() -> None:
    spec = load_causal_world_spec(EXAMPLE)
    target = ParticleRoleTarget("either_collider", 9, 10, "E", "kinetic_energy")  # matches particle 1 only
    assert target.resolve(spec) == 1
    bad_target = ParticleRoleTarget("nobody", 0, 0, "N", "kinetic_energy")
    with pytest.raises(ValueError, match="matched no particle"):
        bad_target.resolve(spec)


def test_broad_explorer_preserves_illegal_candidates_as_compilation_failures(tmp_path: Path) -> None:
    journal = ResearchJournal.create(tmp_path / "journal.jsonl")
    executor = RealCausalAExecutor()
    base_spec = load_causal_world_spec(EXAMPLE)
    observation = observe(journal, base_spec, "sweeping heat, including an illegal negative value")

    h1 = CausalHypothesis("H1", "claim", (), (BondCountPrediction(2, 0),), (), "untested")
    record_hypothesis_set(journal, CausalHypothesisSet(base_spec.digest, (h1,)))

    plan = ExplorationPlan(
        "P-illegal", base_spec.digest, ("H1",),
        (SweepDimension(HEAT_CONTROL.control_id, (-1, 2)),), "full_factorial", 10,
    )
    outcome = run_exploration(
        journal, executor, plan, base_spec, {HEAT_CONTROL.control_id: HEAT_CONTROL},
        {"H1": (BondCountPrediction(2, 0),)}, observation.observation_id,
    )

    assert len(outcome.compilation_failures) == 1
    failure = outcome.compilation_failures[0]
    assert dict(failure.control_values)[HEAT_CONTROL.control_id] == -1
    assert "heat.energy" in failure.reason

    # the legal candidate (heat=2) still produced evidence despite the other one failing
    assert len(outcome.evidence) == 1
    assert outcome.coverage.executed_count == 1
    assert outcome.coverage.invalid_count == 1


def test_broad_explorer_finds_the_heat_break_boundary_and_survives_reopen(tmp_path: Path) -> None:
    journal_path = tmp_path / "journal.jsonl"
    journal = ResearchJournal.create(journal_path)
    executor = RealCausalAExecutor()

    base_spec = load_causal_world_spec(EXAMPLE)
    observation = observe(journal, base_spec, "sweeping local heat energy at the bond site")

    # Deliberately too broad: "any local heat breaks the bond by tick 2" --
    # true for heat>=2 (break_heat=2) but false at heat=1, so the sweep
    # exercises both the supports and contradicts paths, not just one.
    h1 = CausalHypothesis(
        "H1", "any local heat present breaks the bond by tick 2", ("bond_present", "heat>0"),
        (BondCountPrediction(2, 0),), (), "untested",
    )
    record_hypothesis_set(journal, CausalHypothesisSet(base_spec.digest, (h1,)))

    plan = ExplorationPlan(
        "P-heat-sweep", base_spec.digest, ("H1",),
        (SweepDimension(HEAT_CONTROL.control_id, (0, 1, 2, 3, 4)),), "full_factorial", 10,
    )
    outcome = run_exploration(
        journal, executor, plan, base_spec, {HEAT_CONTROL.control_id: HEAT_CONTROL},
        {"H1": (BondCountPrediction(2, 0),)}, observation.observation_id,
    )

    assert len(outcome.candidates) == 5
    assert outcome.compilation_failures == ()
    assert outcome.coverage.executed_count == 5
    assert outcome.coverage.axis_coverage[HEAT_CONTROL.control_id] == (5, 5)

    # heat=0,1 keep the bond (H1 contradicted); heat=2,3,4 break it (H1 supported).
    relations = {dict(c.control_values)[HEAT_CONTROL.control_id]: r.relation
                for c in outcome.candidates for r in outcome.evidence if r.arm_id == c.candidate_id}
    assert relations[0] == "contradicts"
    assert relations[1] == "contradicts"
    assert relations[2] == "supports"
    assert relations[3] == "supports"
    assert relations[4] == "supports"

    assert len(outcome.boundary_candidates) == 1
    boundary = outcome.boundary_candidates[0]
    assert isinstance(boundary, BoundaryCandidate)
    assert boundary.axis == HEAT_CONTROL.control_id
    assert boundary.left_value == 1 and boundary.left_relation == "contradicts"
    assert boundary.right_value == 2 and boundary.right_relation == "supports"

    state_before_close = rebuild_research_state(journal_path)
    assert state_before_close.hypothesis_evidence_status["H1"] == "conditional"

    memory_before_close = rebuild_memory_index(journal_path)
    graph_before_close = rebuild_hypothesis_graph(journal_path)
    journal.close()

    assert verify_journal(journal_path)["valid"] is True

    reopened_state = rebuild_research_state(journal_path)
    reopened_memory = rebuild_memory_index(journal_path)
    reopened_graph = rebuild_hypothesis_graph(journal_path)

    assert reopened_state == state_before_close
    assert reopened_memory.digest == memory_before_close.digest
    assert reopened_graph.digest == graph_before_close.digest
    assert len(reopened_memory.evidence) == 5
