from pathlib import Path

import pytest

from engine.deterministic import (
    BondRuleRoleTarget,
    ControlDefinition,
    HeatCellRoleTarget,
    InterventionFeasibility,
    assess_intervention_feasibility,
    load_causal_world_spec,
)

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "worlds" / "deterministic_bond_cycle_v1.json"

HEAT_CONTROL = ControlDefinition("c.heat", HeatCellRoleTarget("local_heat_source", 10, 10, "energy"), "causal.heat.energy")
BREAK_HEAT_CONTROL = ControlDefinition(
    "c.break_heat", BondRuleRoleTarget("bond_under_test", "kind0-facing-bond-v1", "break_heat"), "causal.bond.break_heat",
)


def test_feasibility_result_requires_resulting_digest_only_when_available() -> None:
    with pytest.raises(ValueError, match="AVAILABLE feasibility result must carry"):
        InterventionFeasibility("digest", (("c.heat", 1),), "AVAILABLE", "reason")
    with pytest.raises(ValueError, match="only an AVAILABLE feasibility result may carry"):
        InterventionFeasibility("digest", (("c.heat", 1),), "INVALID", "reason", "some-digest")


def test_available_for_single_registered_control() -> None:
    spec = load_causal_world_spec(EXAMPLE)
    result = assess_intervention_feasibility(spec, {"c.heat": HEAT_CONTROL}, (("c.heat", 5),))
    assert result.status == "AVAILABLE"
    assert result.resulting_spec_digest is not None


def test_available_for_multiple_controls_applied_together() -> None:
    spec = load_causal_world_spec(EXAMPLE)
    controls = {"c.heat": HEAT_CONTROL, "c.break_heat": BREAK_HEAT_CONTROL}
    result = assess_intervention_feasibility(spec, controls, (("c.heat", 4), ("c.break_heat", 4)))
    assert result.status == "AVAILABLE"


def test_invalid_for_unregistered_control_id() -> None:
    spec = load_causal_world_spec(EXAMPLE)
    result = assess_intervention_feasibility(spec, {"c.heat": HEAT_CONTROL}, (("c.nonexistent", 1),))
    assert result.status == "INVALID"


def test_invalid_for_value_that_fails_spec_validation() -> None:
    spec = load_causal_world_spec(EXAMPLE)
    # negative heat energy is rejected by CausalWorldSpec.from_mapping
    result = assess_intervention_feasibility(spec, {"c.heat": HEAT_CONTROL}, (("c.heat", -1),))
    assert result.status == "INVALID"


def test_ambiguous_for_duplicate_control_id_in_one_request() -> None:
    spec = load_causal_world_spec(EXAMPLE)
    result = assess_intervention_feasibility(spec, {"c.heat": HEAT_CONTROL}, (("c.heat", 1), ("c.heat", 2)))
    assert result.status == "AMBIGUOUS"


def test_assess_never_raises_on_bad_bond_rule_target() -> None:
    spec = load_causal_world_spec(EXAMPLE)
    missing_rule_control = ControlDefinition(
        "c.break_heat", BondRuleRoleTarget("bond_under_test", "no-such-rule", "break_heat"), "causal.bond.break_heat",
    )
    result = assess_intervention_feasibility(spec, {"c.break_heat": missing_rule_control}, (("c.break_heat", 4),))
    assert result.status == "INVALID"
