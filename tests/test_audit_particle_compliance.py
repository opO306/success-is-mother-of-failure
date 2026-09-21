"""Particles must obey their rules, not merely keep the totals.

The environment checks cover water, heat, vapour and minerals. Particles run
on a different contract — bond rules, collision energies, port limits, one
cell of travel per tick — and until now nothing verified it.

Every violation exercised below leaves the material counts, the total energy
and the momentum exactly as it found them, because those are precisely what
the kernel already guards. A particle can teleport across the grid, bond with
a rule the world never declared, or break a bond without the heat its rule
demands, and every conservation check still passes.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from audit.independent_compliance import (
    ParticleRuleError,
    check_particle_transition,
    check_trace_compliance,
    read_particle_rules,
    read_particles,
)
from engine.deterministic import (
    PrivateTraceWriter,
    initial_causal_state,
    load_causal_world_spec,
    load_environment_world_spec,
    step_causal_world,
    trace_environment_run,
)
from engine.deterministic.causal_kernel import chains

ROOT = Path(__file__).resolve().parents[1]
WORLDS = ROOT / "worlds"
POLYMER = WORLDS / "deterministic_polymer_chain_v2.json"
BOND_RULE = "kind0-facing-bond-v2"

ENVIRONMENT_WORLDS = (
    "deterministic_environment_v1.json",
    "deterministic_geochemical_cycle_v2.json",
    "deterministic_open_water_cycle_v3.json",
    "deterministic_physical_flux_v4.json",
)


def _rules(**overrides):
    document = json.loads(POLYMER.read_text(encoding="utf-8"))
    document.update(overrides)
    return read_particle_rules(document)


def _particle(particle_id: int, x: int, y: int, direction: str = "E",
              energy: int = 0, kind: int = 0) -> dict:
    return {"particle_id": particle_id, "kind": kind, "x": x, "y": y,
            "direction": direction, "orientation": direction, "kinetic_energy": energy}


def _snapshot(particles, bonds=(), heat=()) -> dict:
    return {"causal": {"particles": list(particles), "bonds": list(bonds),
                       "heat": list(heat), "tick": 0}}


def _bond(left: int, right: int, x: int, y: int, stored: int = 4,
          rule_id: str = BOND_RULE) -> dict:
    return {"left_id": left, "right_id": right, "rule_id": rule_id,
            "stored_energy": stored, "x": x, "y": y}


def _codes(before: dict, after: dict, rules=None) -> set[str]:
    rules = rules or _rules()
    return {code for code, _, _ in
            check_particle_transition(rules, read_particles(before), read_particles(after))}


# --- honest runs comply -----------------------------------------------------

@pytest.mark.parametrize("world", ENVIRONMENT_WORLDS)
def test_recorded_worlds_obey_their_particle_rules(tmp_path: Path, world: str) -> None:
    document = json.loads((WORLDS / world).read_text(encoding="utf-8"))
    spec = load_environment_world_spec(WORLDS / world)
    run_dir = tmp_path / world
    writer = PrivateTraceWriter(run_dir, world)
    final_state = trace_environment_run(spec, writer)
    writer.close(spec.digest, final_state.digest)

    report = check_trace_compliance(run_dir, document)
    assert report.findings == []


def test_a_released_particle_may_step_the_tick_it_is_freed() -> None:
    """Breaking runs before streaming, so a freed particle moves the same tick.

    Reading that as "a bonded particle moved" was this checker's own first
    mistake; the bond is gone by the time streaming happens.
    """
    before = _snapshot([_particle(1, 10, 10, "E"), _particle(2, 10, 10, "W")],
                       [_bond(1, 2, 10, 10)], [{"x": 10, "y": 10, "energy": 6}])
    after = _snapshot([_particle(1, 9, 10, "W", 3), _particle(2, 11, 10, "E", 3)])
    assert _codes(before, after) == set()


def test_the_polymer_world_complies_under_its_own_rules() -> None:
    spec = load_causal_world_spec(POLYMER)
    state = initial_causal_state(spec)
    snapshots = [{"causal": state.canonical()}]
    for _ in range(spec.ticks):
        state = step_causal_world(spec, state)
        snapshots.append({"causal": state.canonical()})

    assert max((len(members) for members in chains(state.bonds).values()), default=1) >= 3

    rules = read_particle_rules(json.loads(POLYMER.read_text(encoding="utf-8")))
    for before, after in zip(snapshots, snapshots[1:]):
        assert check_particle_transition(rules, read_particles(before),
                                         read_particles(after)) == []


def test_v2_behaviour_is_a_violation_when_the_world_declares_v1() -> None:
    """The format is the contract: chains are permitted only where declared."""
    spec = load_causal_world_spec(POLYMER)
    state = initial_causal_state(spec)
    snapshots = [{"causal": state.canonical()}]
    for _ in range(spec.ticks):
        state = step_causal_world(spec, state)
        snapshots.append({"causal": state.canonical()})

    document = json.loads(POLYMER.read_text(encoding="utf-8"))
    document["format"] = "deterministic-causal-world-spec-v1"
    rules = read_particle_rules(document)

    found = []
    for before, after in zip(snapshots, snapshots[1:]):
        found += check_particle_transition(rules, read_particles(before), read_particles(after))
    codes = {code for code, _, _ in found}

    assert "more_bonds_than_declared_ports" in codes
    assert "bonded_particle_carries_motion" in codes


# --- violations that conserve perfectly -------------------------------------

def test_catches_a_particle_crossing_two_cells_in_one_tick() -> None:
    before = _snapshot([_particle(1, 5, 5, "E", 2)])
    after = _snapshot([_particle(1, 7, 5, "E", 2)])
    assert "particle_moved_more_than_one_cell" in _codes(before, after)


def test_catches_a_particle_moving_off_its_heading() -> None:
    before = _snapshot([_particle(1, 5, 5, "E", 2)])
    after = _snapshot([_particle(1, 5, 6, "E", 2)])
    assert "particle_moved_off_its_heading" in _codes(before, after)


def test_catches_a_motionless_particle_that_moved() -> None:
    before = _snapshot([_particle(1, 5, 5, "E", 0)])
    after = _snapshot([_particle(1, 6, 5, "E", 0)])
    assert "still_particle_moved" in _codes(before, after)


def test_catches_a_bond_formed_under_a_rule_the_world_never_declared() -> None:
    before = _snapshot([_particle(1, 5, 5, "E", 2), _particle(2, 5, 5, "W", 2)])
    after = _snapshot([_particle(1, 5, 5, "E"), _particle(2, 5, 5, "W")],
                      [_bond(1, 2, 5, 5, rule_id="invented-rule")])
    assert "bond_without_a_declared_rule" in _codes(before, after)


def test_catches_a_bond_between_particles_in_different_cells() -> None:
    before = _snapshot([_particle(1, 5, 5, "E", 2), _particle(2, 9, 9, "W", 2)])
    after = _snapshot([_particle(1, 5, 5, "E"), _particle(2, 9, 9, "W")],
                      [_bond(1, 2, 5, 5)])
    assert "bond_across_separate_cells" in _codes(before, after)


def test_catches_a_bond_below_its_declared_collision_energy() -> None:
    before = _snapshot([_particle(1, 5, 5, "E", 1), _particle(2, 5, 5, "W", 1)])
    after = _snapshot([_particle(1, 5, 5, "E"), _particle(2, 5, 5, "W")],
                      [_bond(1, 2, 5, 5, stored=2)])
    assert "bond_below_minimum_collision_energy" in _codes(before, after)


def test_catches_a_bond_that_broke_without_the_heat_its_rule_requires() -> None:
    before = _snapshot([_particle(1, 5, 5, "E"), _particle(2, 5, 5, "W")],
                       [_bond(1, 2, 5, 5)])
    after = _snapshot([_particle(1, 5, 5, "W", 2), _particle(2, 5, 5, "E", 2)])
    assert "bond_broke_without_the_heat_its_rule_requires" in _codes(before, after)


def test_a_bond_that_broke_with_enough_heat_is_not_reported() -> None:
    before = _snapshot([_particle(1, 5, 5, "E"), _particle(2, 5, 5, "W")],
                       [_bond(1, 2, 5, 5)], [{"x": 5, "y": 5, "energy": 6}])
    after = _snapshot([_particle(1, 4, 5, "W", 3), _particle(2, 6, 5, "E", 3)],
                      (), [{"x": 5, "y": 5, "energy": 4}])
    assert "bond_broke_without_the_heat_its_rule_requires" not in _codes(before, after)


def test_catches_a_chain_whose_members_drifted_apart() -> None:
    before = _snapshot([_particle(1, 5, 5, "E"), _particle(2, 5, 5, "W")],
                       [_bond(1, 2, 5, 5)])
    after = _snapshot([_particle(1, 5, 5, "E"), _particle(2, 6, 5, "W")],
                      [_bond(1, 2, 5, 5)])
    assert "chain_members_in_different_cells" in _codes(before, after)


def test_catches_a_particle_that_appeared_or_vanished() -> None:
    before = _snapshot([_particle(1, 5, 5, "E", 2), _particle(2, 6, 6, "W", 2)])
    after = _snapshot([_particle(1, 5, 5, "E", 2)])
    assert "particle_roster_changed" in _codes(before, after)


def test_catches_more_bonds_than_the_material_declares_ports() -> None:
    rules = _rules(materials=[{"kind": 0, "mass": 1, "ports": 1}])
    before = _snapshot([_particle(i, 5, 5, "E") for i in (1, 2, 3)],
                       [_bond(1, 2, 5, 5)])
    after = _snapshot([_particle(i, 5, 5, "E") for i in (1, 2, 3)],
                      [_bond(1, 2, 5, 5), _bond(2, 3, 5, 5)])
    assert "more_bonds_than_declared_ports" in _codes(before, after, rules)


def test_catches_a_chain_recording_motion_on_several_members() -> None:
    before = _snapshot([_particle(1, 5, 5, "E"), _particle(2, 5, 5, "W")],
                       [_bond(1, 2, 5, 5)])
    after = _snapshot([_particle(1, 5, 5, "E", 3), _particle(2, 5, 5, "W", 3)],
                      [_bond(1, 2, 5, 5)])
    assert "chain_records_motion_on_several_members" in _codes(before, after)


def test_these_violations_all_pass_the_conservation_check() -> None:
    """Why this checker exists: conservation cannot see any of them.

    Each pair below keeps the particle counts, the accounted energy and the
    material inventory identical, so the recount is satisfied. Only the
    particle rules tell them apart from a legal tick.
    """
    from audit.independent_conservation import read_parameters, recount

    document = {"format": "deterministic-environment-world-spec-v1",
                "solute_kinds": 0, "law": {},
                "causal_world": json.loads(POLYMER.read_text(encoding="utf-8"))}
    parameters = read_parameters(document)
    rules = read_particle_rules(document)

    def _with_cells(snapshot: dict) -> dict:
        return {**snapshot, "cells": [], "energy_supplied": 0, "energy_removed": 0}

    cases = [
        ("teleport",
         _snapshot([_particle(1, 5, 5, "E", 2)]),
         _snapshot([_particle(1, 7, 5, "E", 2)])),
        ("sideways",
         _snapshot([_particle(1, 5, 5, "E", 2)]),
         _snapshot([_particle(1, 5, 6, "E", 2)])),
        ("undeclared rule",
         _snapshot([_particle(1, 5, 5, "E", 2), _particle(2, 5, 5, "W", 2)]),
         _snapshot([_particle(1, 5, 5, "E"), _particle(2, 5, 5, "W")],
                   [_bond(1, 2, 5, 5, rule_id="invented-rule")])),
        ("break without heat",
         _snapshot([_particle(1, 5, 5, "E"), _particle(2, 5, 5, "W")],
                   [_bond(1, 2, 5, 5)]),
         _snapshot([_particle(1, 5, 5, "W", 2), _particle(2, 5, 5, "E", 2)])),
    ]

    for name, before, after in cases:
        first = recount(_with_cells(before), parameters)
        second = recount(_with_cells(after), parameters)
        assert first.particle_counts == second.particle_counts, name
        assert first.energy_accounted == second.energy_accounted, name
        assert first.material_inventory == second.material_inventory, name

        violations = check_particle_transition(rules, read_particles(before),
                                               read_particles(after))
        assert violations, f"{name} should have been caught by the particle rules"


# --- the rule reader on its own ---------------------------------------------

def test_particle_rules_come_from_the_specification() -> None:
    document = json.loads(POLYMER.read_text(encoding="utf-8"))
    rules = read_particle_rules(document)

    assert rules.width == document["causal_world"]["kernel"]["width"] \
        if "causal_world" in document else rules.width == document["kernel"]["width"]
    assert rules.ports == {0: 4}
    assert rules.masses == {0: 1}
    assert rules.chains_may_move is True
    assert rules.port_limit(0) == 4


def test_a_v1_world_caps_every_material_at_one_port() -> None:
    document = json.loads(POLYMER.read_text(encoding="utf-8"))
    document["format"] = "deterministic-causal-world-spec-v1"
    rules = read_particle_rules(document)

    assert rules.chains_may_move is False
    assert rules.port_limit(0) == 1, "ports are only honoured where chains are declared"


def test_steps_counts_a_wrapped_move_as_one() -> None:
    rules = _rules()
    assert rules.steps((0, 0), (0, 0)) == 0
    assert rules.steps((0, 0), (1, 0)) == 1
    assert rules.steps((0, 0), (rules.width - 1, 0)) == 1, "west of column 0 wraps"
    assert rules.steps((0, 0), (2, 0)) == -1
    assert rules.steps((0, 0), (1, 1)) == -1, "diagonal is not one step"


def test_a_bond_rule_matches_either_role_order() -> None:
    rules = _rules()
    rule = rules.rule(BOND_RULE)
    assert rule is not None
    assert rule.accepts(0, "E", 0, "W") is True
    assert rule.accepts(0, "W", 0, "E") is True, "role order must not matter"
    assert rule.accepts(0, "E", 0, "E") is False


def test_reading_rules_from_a_document_without_a_causal_world_fails() -> None:
    with pytest.raises(ParticleRuleError):
        read_particle_rules({"causal_world": "not a mapping"})
