"""The census must count chances, and must report zero when there are none.

A counter that always finds an opportunity is as useless as one that never
does. These tests pin both directions: hand-built states whose counts are
known by inspection, and worlds where a precondition is genuinely absent.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from engine.deterministic import (
    census_causal_world,
    load_causal_world_spec,
    render_census,
)
from engine.deterministic.causal_kernel import initial_causal_state, step_causal_world
from engine.deterministic.precondition_census import _census

WORLDS = Path("worlds")


def _world(particles, *, ticks=6, width=16, height=16, heat=(), minimum=3, ports=4):
    return {
        "format": "deterministic-causal-world-spec-v2",
        "world_id": "census-fixture",
        "kernel": {
            "width": width, "height": height, "boundary": "wrap",
            "arithmetic": "integer", "deterministic": True,
            "tick_order": ["break_existing_bonds", "stream_free_particles",
                           "resolve_local_collisions"],
        },
        "materials": [{"kind": 0, "mass": 1, "ports": ports}],
        "particles": list(particles),
        "heat": list(heat),
        "bond_rules": [{
            "rule_id": "k0", "event": "local_reversible_bond", "locality": "same_cell",
            "conserves": ["material", "energy", "momentum"],
            "left_kind": 0, "right_kind": 0,
            "left_orientation": "E", "right_orientation": "W",
            "minimum_collision_energy": minimum, "break_heat": 2,
            "release_left": "W", "release_right": "E",
        }],
        "execution": {"ticks": ticks},
        "observer": {"hash_interval": 1},
    }


def _particle(pid, x, y, direction, energy):
    return {"particle_id": pid, "kind": 0, "x": x, "y": y,
            "direction": direction, "orientation": direction,
            "kinetic_energy": energy}


def _spec(tmp_path, world):
    path = tmp_path / "world.json"
    path.write_text(json.dumps(world), encoding="utf-8")
    return load_causal_world_spec(path)


def test_three_converging_particles_are_counted_as_crowding(tmp_path):
    """Three arriving in one cell is a chance, even though the kernel skips it."""
    spec = _spec(tmp_path, _world([
        _particle(1, 7, 8, "E", 1),
        _particle(2, 9, 8, "W", 1),
        _particle(3, 8, 7, "S", 1),
    ], ticks=4))
    census = census_causal_world(spec)
    assert census.ticks_with_three_or_more_free == 1
    assert census.peak_cell_crowding == 1


def test_two_particles_never_count_as_crowding(tmp_path):
    """A pair is what the kernel already resolves; it is not a third body."""
    spec = _spec(tmp_path, _world([
        _particle(1, 7, 8, "E", 2),
        _particle(2, 9, 8, "W", 2),
    ], ticks=4))
    census = census_causal_world(spec)
    assert census.ticks_with_three_or_more_free == 0
    assert "catalyst-needs-three-bodies-in-one-cell" in census.blocked()


def test_crowding_counter_does_not_fire_on_a_bonded_pair(tmp_path):
    """Bonded members share a cell by definition; only free bodies crowd it.

    Without this the counter would report a chance every time a chain of
    three sat still, and a catalyst rule built on that reading would never
    find the free third body it actually needs.
    """
    spec = _spec(tmp_path, _world([
        _particle(1, 9, 10, "E", 2),
        _particle(2, 11, 10, "W", 2),
        _particle(3, 7, 10, "E", 3),
    ], ticks=6))
    census = census_causal_world(spec)
    assert census.peak_longest_chain == 3
    assert census.ticks_with_three_or_more_free == 0


def test_a_lone_pair_blocks_all_but_the_template_precondition(tmp_path):
    """A pair that bonds and stops does offer a standing chain with ports free.

    That is the one bundle-4 chance the simplest world already supplies: the
    material declares four ports and only one is spent. Everything else --
    a third body, a fourth member, a second chain -- stays out of reach.
    """
    spec = _spec(tmp_path, _world([
        _particle(1, 7, 8, "E", 2),
        _particle(2, 9, 8, "W", 2),
    ], ticks=4))
    census = census_causal_world(spec)
    assert census.ticks_with_standing_free_port > 0
    assert set(census.blocked()) == {
        "catalyst-needs-three-bodies-in-one-cell",
        "polymer-needs-chain-of-four",
        "division-needs-two-chains-at-once",
    }


def test_a_pair_with_one_port_each_blocks_the_template_precondition(tmp_path):
    """With every port spent, the bonded pair has nothing left to attach to."""
    spec = _spec(tmp_path, _world([
        _particle(1, 7, 8, "E", 2),
        _particle(2, 9, 8, "W", 2),
    ], ticks=4, ports=1))
    census = census_causal_world(spec)
    assert census.ticks_with_standing_free_port == 0
    assert "template-needs-standing-chain-with-free-port" in census.blocked()


def test_two_separate_pairs_unblock_only_division(tmp_path):
    """Two chains at once is a different chance from a long chain.

    Both counters read off the same bonds, so a census that conflated them
    would call this world ready for polymers as well.
    """
    spec = _spec(tmp_path, _world([
        _particle(1, 7, 4, "E", 2), _particle(2, 9, 4, "W", 2),
        _particle(3, 7, 12, "E", 2), _particle(4, 9, 12, "W", 2),
    ], ticks=4))
    census = census_causal_world(spec)
    assert census.peak_coexisting_chains == 2
    assert census.peak_longest_chain == 2
    blocked = census.blocked()
    assert "division-needs-two-chains-at-once" not in blocked
    assert "polymer-needs-chain-of-four" in blocked


def test_travelling_chain_is_not_offered_as_a_template(tmp_path):
    """A chain carrying motion is moving on, not standing to be copied."""
    spec = _spec(tmp_path, _world([
        _particle(1, 9, 10, "E", 2),
        _particle(2, 11, 10, "W", 2),
        _particle(3, 7, 10, "E", 3),
    ], ticks=6))
    state = initial_causal_state(spec)
    for _ in range(4):
        state = step_causal_world(spec, state)
    row = _census(spec, state)
    anchor = min(min(b.left_id, b.right_id) for b in state.bonds)
    holder = next(p for p in state.particles if p.particle_id == anchor)
    assert holder.kinetic_energy > 0          # the chain is under way
    assert row.standing_chains_with_free_port == 0


def test_census_adds_no_rule_and_changes_no_outcome(tmp_path):
    """Counting must not disturb the world it counts (constitution art. 3)."""
    world = _world([
        _particle(1, 9, 10, "E", 2),
        _particle(2, 11, 10, "W", 2),
        _particle(3, 7, 10, "E", 3),
    ], ticks=6)
    spec = _spec(tmp_path, world)

    state = initial_causal_state(spec)
    for _ in range(spec.ticks):
        state = step_causal_world(spec, state)
    unobserved = state.digest

    census_causal_world(spec)
    again = initial_causal_state(spec)
    for _ in range(spec.ticks):
        again = step_causal_world(spec, again)
    assert again.digest == unobserved


def test_census_is_reproducible(tmp_path):
    spec = _spec(tmp_path, _world([
        _particle(1, 7, 8, "E", 2),
        _particle(2, 9, 8, "W", 2),
    ], ticks=4))
    assert render_census(census_causal_world(spec)) == render_census(census_causal_world(spec))


@pytest.mark.parametrize("name", [
    "deterministic_bond_cycle_v1.json",
    "deterministic_polymer_chain_v2.json",
])
def test_shipped_worlds_block_the_catalyst_precondition(name):
    """The finding this module exists to record, pinned against regression.

    Neither shipped world ever puts three free particles in one cell, so a
    catalyst rule added today would have no occasion to fire. If a future
    world changes that, this test should fail and be updated deliberately.
    """
    census = census_causal_world(load_causal_world_spec(WORLDS / name))
    assert census.ticks_with_three_or_more_free == 0
    assert "catalyst-needs-three-bodies-in-one-cell" in census.blocked()
