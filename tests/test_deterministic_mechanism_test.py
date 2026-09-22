import pytest

from engine.deterministic import (
    BondRuleRoleTarget,
    ControlDefinition,
    DiscriminatingPrediction,
    InterventionDefinition,
    MechanismEvidence,
    MechanismTestPlan,
    MechanismTestResult,
    evaluate_mechanism_test,
)

CONTROL = ControlDefinition("c.break_heat", BondRuleRoleTarget("bond_under_test", "kind0-facing-bond-v1", "break_heat"),
                            "causal.bond.break_heat")


def test_intervention_definition_rejects_mismatched_control_id() -> None:
    with pytest.raises(ValueError, match="must match"):
        InterventionDefinition("c.other", CONTROL, "SET_ONCE", 4)


def test_intervention_definition_rejects_unsupported_operation() -> None:
    with pytest.raises(ValueError, match="unsupported intervention operation"):
        InterventionDefinition("c.break_heat", CONTROL, "TELEPORT", 4)


def test_plan_requires_a_prediction_for_every_mechanism() -> None:
    intervention = InterventionDefinition("c.break_heat", CONTROL, "SET_ONCE", 4)
    with pytest.raises(ValueError, match="exactly one prediction"):
        MechanismTestPlan("P-1", "MECH-A", ("MECH-B",), (intervention,),
                          (DiscriminatingPrediction("MECH-A", "x"),), ())


def test_plan_requires_at_least_one_intervention() -> None:
    with pytest.raises(ValueError, match="at least one intervention"):
        MechanismTestPlan("P-1", "MECH-A", ("MECH-B",), (), (DiscriminatingPrediction("MECH-A", "x"),
                                                             DiscriminatingPrediction("MECH-B", "y")), ())


def test_is_discriminating_true_only_when_predictions_differ() -> None:
    intervention = InterventionDefinition("c.break_heat", CONTROL, "SET_ONCE", 4)
    discriminating = MechanismTestPlan("P-1", "MECH-A", ("MECH-B",), (intervention,),
                                       (DiscriminatingPrediction("MECH-A", "x"),
                                        DiscriminatingPrediction("MECH-B", "y")), ())
    non_discriminating = MechanismTestPlan("P-2", "MECH-A", ("MECH-B",), (intervention,),
                                           (DiscriminatingPrediction("MECH-A", "x"),
                                            DiscriminatingPrediction("MECH-B", "x")), ())
    assert discriminating.is_discriminating is True
    assert non_discriminating.is_discriminating is False


def test_evaluate_marks_inconclusive_when_execution_failed() -> None:
    intervention = InterventionDefinition("c.break_heat", CONTROL, "SET_ONCE", 4)
    plan = MechanismTestPlan("P-1", "MECH-A", ("MECH-B",), (intervention,),
                             (DiscriminatingPrediction("MECH-A", "x"), DiscriminatingPrediction("MECH-B", "y")), ())
    result = MechanismTestResult("P-1", "bd", "id", "x", "x", "failed", "success")
    evidence = evaluate_mechanism_test(plan, result)
    assert all(e.relation == "INCONCLUSIVE" for e in evidence)


def test_evaluate_supports_and_contradicts_by_matching_prediction() -> None:
    intervention = InterventionDefinition("c.break_heat", CONTROL, "SET_ONCE", 4)
    plan = MechanismTestPlan("P-1", "MECH-A", ("MECH-B",), (intervention,),
                             (DiscriminatingPrediction("MECH-A", "survives"),
                              DiscriminatingPrediction("MECH-B", "breaks")), ())
    result = MechanismTestResult("P-1", "bd", "id", "breaks", "survives", "success", "success")
    evidence = {e.mechanism_candidate_id: e.relation for e in evaluate_mechanism_test(plan, result)}
    assert evidence == {"MECH-A": "SUPPORTS", "MECH-B": "CONTRADICTS"}


def test_mechanism_evidence_rejects_unsupported_relation() -> None:
    with pytest.raises(ValueError, match="unsupported mechanism evidence relation"):
        MechanismEvidence("MECH-A", "P-1", "MAYBE", "reason")
