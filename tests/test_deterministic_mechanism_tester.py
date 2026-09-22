import json
from pathlib import Path

import pytest

from engine.deterministic import (
    BondRuleRoleTarget,
    BondTraceSubject,
    CausalWorldSpec,
    ControlDefinition,
    DiscriminatingPrediction,
    HeatCellTraceSubject,
    InterventionDefinition,
    MechanismTestPlan,
    ParticleTraceSubject,
    ResearchJournal,
    TraceSpec,
    check_plan_feasibility,
    load_causal_world_spec,
    read_journal,
    run_mechanism_test,
    verify_journal,
)

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "worlds" / "deterministic_bond_cycle_v1.json"

BREAK_HEAT_CONTROL = ControlDefinition(
    "causal.control.break_heat", BondRuleRoleTarget("bond_under_test", "kind0-facing-bond-v1", "break_heat"),
    "causal.bond.break_heat",
)
NONEXISTENT_CONTROL = ControlDefinition(
    "causal.control.nonexistent_rule", BondRuleRoleTarget("bond_under_test", "no-such-rule", "break_heat"),
    "causal.bond.break_heat",
)

TRACE_SPEC = TraceSpec("T-mechanism", (
    HeatCellTraceSubject("heated_cell", 10, 10, ("energy",)),
    ParticleTraceSubject("particle_a", 9, 10, "E", ("kinetic_energy",)),
    ParticleTraceSubject("particle_b", 11, 10, "W", ("kinetic_energy",)),
    BondTraceSubject("target_bond", "particle_a", "particle_b", ("exists",)),
), 0, 2)


def _spec_with_heat(energy: int, world_id: str) -> CausalWorldSpec:
    raw = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    raw["heat"] = [{"x": 10, "y": 10, "energy": energy}] if energy else []
    raw["world_id"] = world_id
    return CausalWorldSpec.from_mapping(raw)


def _bond_outcome(snapshots) -> str:
    from engine.deterministic import KernelPhase
    final = next(s for s in snapshots if s.tick == 2 and s.phase == KernelPhase.POST_TICK)
    return "bond_breaks" if not final.values["target_bond"]["exists"] else "bond_survives"


def test_feasibility_available_for_break_heat_intervention() -> None:
    base_spec = _spec_with_heat(2, "heat-2-base")
    intervention = InterventionDefinition("causal.control.break_heat", BREAK_HEAT_CONTROL, "SET_ONCE", 4)
    plan = MechanismTestPlan(
        "P-1", "MECH-break-rule", ("MECH-particle-state",), (intervention,),
        (DiscriminatingPrediction("MECH-break-rule", "bond_survives"),
         DiscriminatingPrediction("MECH-particle-state", "bond_breaks")),
        ("particle_a", "particle_b"),
    )
    feasibility = check_plan_feasibility(base_spec, {"causal.control.break_heat": BREAK_HEAT_CONTROL}, plan)
    assert feasibility.status == "AVAILABLE"
    assert feasibility.resulting_spec_digest is not None


def test_feasibility_invalid_for_unregistered_control() -> None:
    base_spec = _spec_with_heat(2, "heat-2-base")
    intervention = InterventionDefinition("causal.control.nonexistent_rule", NONEXISTENT_CONTROL, "SET_ONCE", 4)
    plan = MechanismTestPlan(
        "P-1", "MECH-break-rule", ("MECH-particle-state",), (intervention,),
        (DiscriminatingPrediction("MECH-break-rule", "bond_survives"),
         DiscriminatingPrediction("MECH-particle-state", "bond_breaks")),
        (),
    )
    feasibility = check_plan_feasibility(
        base_spec, {"causal.control.nonexistent_rule": NONEXISTENT_CONTROL}, plan,
    )
    assert feasibility.status == "INVALID"


def test_mechanism_test_plan_rejects_non_discriminating_predictions_are_still_constructible_but_flagged() -> None:
    intervention = InterventionDefinition("causal.control.break_heat", BREAK_HEAT_CONTROL, "SET_ONCE", 4)
    plan = MechanismTestPlan(
        "P-1", "MECH-A", ("MECH-B",), (intervention,),
        (DiscriminatingPrediction("MECH-A", "bond_breaks"), DiscriminatingPrediction("MECH-B", "bond_breaks")),
        (),
    )
    assert plan.is_discriminating is False


def test_break_heat_intervention_supports_break_rule_mechanism_over_particle_state(tmp_path: Path) -> None:
    """The confirmed end-to-end scenario: heat held at 2, only break_heat varied 2 -> 4.

    Ground truth established by direct measurement (not asserted blindly):
    heat=2/break_heat=2 breaks the bond by tick 2; heat=2/break_heat=4 keeps
    it, because tick 1's stored bond energy (4) plus the collision components
    never reaches the higher threshold. This discriminates "heat=2 alone
    determines the outcome" (MECH-particle-state, which would still predict
    a break) from "the heat/break_heat relation determines it"
    (MECH-break-rule, which predicts survival once break_heat exceeds what
    heat can supply).
    """
    journal = ResearchJournal.create(tmp_path / "journal.jsonl")
    base_spec = _spec_with_heat(2, "heat-2-base")
    controls = {"causal.control.break_heat": BREAK_HEAT_CONTROL}

    intervention = InterventionDefinition("causal.control.break_heat", BREAK_HEAT_CONTROL, "SET_ONCE", 4)
    plan = MechanismTestPlan(
        "P-break-rule-vs-particle-state", "MECH-break-rule", ("MECH-particle-state",), (intervention,),
        (DiscriminatingPrediction("MECH-break-rule", "bond_survives"),
         DiscriminatingPrediction("MECH-particle-state", "bond_breaks")),
        ("particle_a", "particle_b"),
    )

    result, evidence, feasibility = run_mechanism_test(journal, base_spec, controls, plan, TRACE_SPEC, _bond_outcome)

    assert feasibility.status == "AVAILABLE"
    assert result is not None
    assert result.baseline_outcome == "bond_breaks"
    assert result.intervention_outcome == "bond_survives"
    assert result.baseline_execution_status == "success"
    assert result.intervention_execution_status == "success"

    by_mechanism = {e.mechanism_candidate_id: e for e in evidence}
    assert by_mechanism["MECH-break-rule"].relation == "SUPPORTS"
    assert by_mechanism["MECH-particle-state"].relation == "CONTRADICTS"

    journal.close()
    assert verify_journal(journal.path)["valid"] is True
    event_types = [e.event_type for e in read_journal(journal.path)]
    assert event_types == [
        "mechanism_test_planned", "intervention_feasibility_checked", "mechanism_test_executed",
        "mechanism_evidence_recorded", "mechanism_evidence_recorded",
    ]


def test_infeasible_plan_never_touches_a_and_records_only_feasibility(tmp_path: Path) -> None:
    journal = ResearchJournal.create(tmp_path / "journal.jsonl")
    base_spec = _spec_with_heat(2, "heat-2-base")
    controls = {"causal.control.nonexistent_rule": NONEXISTENT_CONTROL}

    intervention = InterventionDefinition("causal.control.nonexistent_rule", NONEXISTENT_CONTROL, "SET_ONCE", 4)
    plan = MechanismTestPlan(
        "P-infeasible", "MECH-A", ("MECH-B",), (intervention,),
        (DiscriminatingPrediction("MECH-A", "bond_survives"), DiscriminatingPrediction("MECH-B", "bond_breaks")),
        (),
    )

    result, evidence, feasibility = run_mechanism_test(journal, base_spec, controls, plan, TRACE_SPEC, _bond_outcome)

    assert feasibility.status == "INVALID"
    assert result is None
    assert evidence == ()

    event_types = [e.event_type for e in read_journal(journal.path)]
    assert event_types == ["mechanism_test_planned", "intervention_feasibility_checked"]
