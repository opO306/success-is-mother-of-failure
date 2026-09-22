from pathlib import Path

import pytest

from engine.deterministic import (
    BondRuleRoleTarget,
    ControlDefinition,
    HeatCellRoleTarget,
    ParticleRoleTarget,
    apply_control,
    bind_control,
    load_causal_world_spec,
    run_causal_world,
)

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "worlds" / "deterministic_bond_cycle_v1.json"


def test_particle_role_target_rejects_unsupported_field() -> None:
    with pytest.raises(ValueError, match="unsupported particle control field"):
        ParticleRoleTarget("left_collider", 9, 10, "E", "mass")


def test_heat_cell_role_target_rejects_unsupported_field() -> None:
    with pytest.raises(ValueError, match="unsupported heat control field"):
        HeatCellRoleTarget("local_heat_source", 10, 10, "temperature")


def test_bond_rule_role_target_resolves_and_rejects_missing_rule() -> None:
    spec = load_causal_world_spec(EXAMPLE)
    target = BondRuleRoleTarget("bond_under_test", "kind0-facing-bond-v1", "break_heat")
    assert target.resolve(spec) == "kind0-facing-bond-v1"

    missing = BondRuleRoleTarget("bond_under_test", "no-such-rule", "break_heat")
    with pytest.raises(ValueError, match="not found"):
        missing.resolve(spec)


def test_apply_control_mutates_particle_energy_without_touching_others() -> None:
    spec = load_causal_world_spec(EXAMPLE)
    control = ControlDefinition("c.left_energy", ParticleRoleTarget("left_collider", 9, 10, "E", "kinetic_energy"),
                                "causal.collision.left_energy")
    mutated = apply_control(spec, control, 9)

    left = next(p for p in mutated.particles if p.x == 9 and p.y == 10)
    right = next(p for p in mutated.particles if p.x == 11 and p.y == 10)
    assert left.kinetic_energy == 9
    assert right.kinetic_energy == 2  # untouched


def test_apply_control_removing_all_heat_produces_a_legal_zero_heat_spec() -> None:
    spec = load_causal_world_spec(EXAMPLE)
    control = ControlDefinition("c.heat", HeatCellRoleTarget("local_heat_source", 10, 10, "energy"),
                                "causal.heat.energy")
    mutated = apply_control(spec, control, 0)

    assert mutated.heat == ()
    run = run_causal_world(mutated)
    assert run.checkpoints[-1].bonds == 1  # no heat, bond survives to the last tick


def test_apply_control_bond_rule_break_heat() -> None:
    spec = load_causal_world_spec(EXAMPLE)
    control = ControlDefinition("c.break_heat", BondRuleRoleTarget("bond_under_test", "kind0-facing-bond-v1", "break_heat"),
                                "causal.bond.break_heat")
    mutated = apply_control(spec, control, 100)

    rule = next(r for r in mutated.bond_rules if r.rule_id == "kind0-facing-bond-v1")
    assert rule.break_heat == 100
