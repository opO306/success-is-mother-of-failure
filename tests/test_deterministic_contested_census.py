"""The detector must find where an id decides, and stay quiet where physics does.

Principle 3 of `LOCAL_INTERACTION_PRINCIPLES_V1.md` says an undetermined
outcome is a missing state variable, not a tie to break. These tests pin the
evidence that the kernel breaks it today, and pin the detector against both
kinds of failure: missing a real contest, and inventing one.

The proof that the kernel actually breaks the principle lives in
`test_known_defects_causal_kernel.py`, which records defects on purpose.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from engine.deterministic import contested_causal_world, load_causal_world_spec
from engine.deterministic.causal_kernel import CausalWorldState, PhysicalBond
from engine.deterministic.causal_spec import (
    BondRuleSpec,
    CausalKernelSpec,
    CausalMaterialSpec,
    CausalParticleSpec,
    CausalWorldSpec,
)
from engine.deterministic.contested_census import _contested_in

RULE = BondRuleSpec("ew", 0, 0, "E", "W", 3, 2, "W", "E")


def _spec(ticks: int = 4) -> CausalWorldSpec:
    return CausalWorldSpec(
        "contested-fixture",
        CausalKernelSpec(16, 16, "wrap", "integer", True,
                         ("break_existing_bonds", "stream_free_particles",
                          "resolve_local_collisions")),
        (CausalMaterialSpec(0, 1, 4),), (), (), (RULE,), ticks, 1,
        "deterministic-causal-world-spec-v2")


def _twin_member_state(first: int, second: int, arrival: int) -> CausalWorldState:
    """A bonded pair whose members are physically indistinguishable.

    Same cell, same kind, same orientation, same energy, same free ports. An
    arrival that matches the rule matches *both* of them, so the physics does
    not say which one takes it.
    """
    particles = (
        CausalParticleSpec(first, 0, 10, 10, "W", "W", 0),
        CausalParticleSpec(second, 0, 10, 10, "W", "W", 0),
        CausalParticleSpec(arrival, 0, 10, 10, "E", "E", 3),
    )
    bonds = (PhysicalBond(min(first, second), max(first, second), "ew", 4, 10, 10),)
    return CausalWorldState(0, particles, (), bonds, {0: 4}, True)


def test_two_identical_members_are_reported_as_contested():
    found = _contested_in(_spec(), _twin_member_state(1, 2, 3))
    kinds = [item.kind for item in found]
    assert "several_ports_accept_one_arrival" in kinds
    moment = next(i for i in found if i.kind == "several_ports_accept_one_arrival")
    assert moment.candidates == (1, 2)


def test_three_free_particles_in_one_cell_are_reported():
    state = CausalWorldState(0, (
        CausalParticleSpec(1, 0, 8, 8, "E", "E", 1),
        CausalParticleSpec(2, 0, 8, 8, "W", "W", 1),
        CausalParticleSpec(3, 0, 8, 8, "S", "S", 1),
    ), (), (), {0: 4}, True)
    found = _contested_in(_spec(), state)
    moment = next(i for i in found if i.kind == "three_or_more_free_in_one_cell")
    assert moment.candidates == (1, 2, 3)


def test_a_pair_in_one_cell_is_not_contested():
    """Two bodies are what the kernel already resolves; that is not ambiguity."""
    state = CausalWorldState(0, (
        CausalParticleSpec(1, 0, 8, 8, "E", "E", 2),
        CausalParticleSpec(2, 0, 8, 8, "W", "W", 2),
    ), (), (), {0: 4}, True)
    assert _contested_in(_spec(), state) == []


def test_one_acceptable_port_is_not_contested():
    """Only one member matches the rule, so the physics does decide."""
    particles = (
        CausalParticleSpec(1, 0, 10, 10, "E", "E", 0),
        CausalParticleSpec(2, 0, 10, 10, "W", "W", 0),
        CausalParticleSpec(3, 0, 10, 10, "E", "E", 3),
    )
    bonds = (PhysicalBond(1, 2, "ew", 4, 10, 10),)
    state = CausalWorldState(0, particles, (), bonds, {0: 4}, True)
    found = [i for i in _contested_in(_spec(), state)
             if i.kind == "several_ports_accept_one_arrival"]
    assert found == []


def test_a_full_port_is_not_offered_as_a_candidate():
    """A member with no free port cannot be in contention for the arrival."""
    particles = (
        CausalParticleSpec(1, 0, 10, 10, "W", "W", 0),
        CausalParticleSpec(2, 0, 10, 10, "W", "W", 0),
        CausalParticleSpec(3, 0, 10, 10, "E", "E", 3),
    )
    bonds = (PhysicalBond(1, 2, "ew", 4, 10, 10),)
    state = CausalWorldState(0, particles, (), bonds, {0: 1}, True)
    found = [i for i in _contested_in(_spec(), state)
             if i.kind == "several_ports_accept_one_arrival"]
    assert found == []


def test_an_arrival_below_the_energy_threshold_is_not_contested():
    """Ambiguity needs two lawful outcomes; an unlawful one is not an option."""
    particles = (
        CausalParticleSpec(1, 0, 10, 10, "W", "W", 0),
        CausalParticleSpec(2, 0, 10, 10, "W", "W", 0),
        CausalParticleSpec(3, 0, 10, 10, "E", "E", 1),   # below minimum 3
    )
    bonds = (PhysicalBond(1, 2, "ew", 4, 10, 10),)
    state = CausalWorldState(0, particles, (), bonds, {0: 4}, True)
    found = [i for i in _contested_in(_spec(), state)
             if i.kind == "several_ports_accept_one_arrival"]
    assert found == []


def test_detector_changes_no_outcome(tmp_path):
    """Counting must not disturb what it counts (constitution art. 3)."""
    world = {
        "format": "deterministic-causal-world-spec-v2", "world_id": "probe",
        "kernel": {"width": 16, "height": 16, "boundary": "wrap",
                   "arithmetic": "integer", "deterministic": True,
                   "tick_order": ["break_existing_bonds", "stream_free_particles",
                                  "resolve_local_collisions"]},
        "materials": [{"kind": 0, "mass": 1, "ports": 4}],
        "particles": [
            {"particle_id": 1, "kind": 0, "x": 9, "y": 10, "direction": "E",
             "orientation": "E", "kinetic_energy": 2},
            {"particle_id": 2, "kind": 0, "x": 11, "y": 10, "direction": "W",
             "orientation": "W", "kinetic_energy": 2},
        ],
        "heat": [], "bond_rules": [{
            "rule_id": "ew", "event": "local_reversible_bond", "locality": "same_cell",
            "conserves": ["material", "energy", "momentum"],
            "left_kind": 0, "right_kind": 0, "left_orientation": "E",
            "right_orientation": "W", "minimum_collision_energy": 3,
            "break_heat": 2, "release_left": "W", "release_right": "E"}],
        "execution": {"ticks": 6}, "observer": {"hash_interval": 1}}
    path = tmp_path / "w.json"
    path.write_text(json.dumps(world), encoding="utf-8")
    spec = load_causal_world_spec(path)

    from engine.deterministic import initial_causal_state, step_causal_world
    state = initial_causal_state(spec)
    for _ in range(spec.ticks):
        state = step_causal_world(spec, state)
    before = state.digest

    contested_causal_world(spec)

    again = initial_causal_state(spec)
    for _ in range(spec.ticks):
        again = step_causal_world(spec, again)
    assert again.digest == before


@pytest.mark.parametrize("name", [
    "deterministic_bond_cycle_v1.json",
    "deterministic_polymer_chain_v2.json",
])
def test_shipped_worlds_report_no_contested_moment(name):
    """The shipped worlds are hand-placed, so nothing is left undetermined.

    This is not reassurance about the kernel -- it records that these two
    worlds cannot exercise the ambiguity, which is why the evidence above is
    built by hand instead.
    """
    census = contested_causal_world(load_causal_world_spec(Path("worlds") / name))
    assert census.moments == ()
