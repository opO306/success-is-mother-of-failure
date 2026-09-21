from dataclasses import fields

import pytest

from engine.living import (
    BodyIntent,
    BoundaryPhenotype,
    Founder,
    Genome,
    MatterPool,
    alive,
    body_tick,
    found_world,
    internal_signals,
)
from engine.living.foundation import AbioticWorld


def _boundary(**changes):
    values = {
        "capacities": (10.0, 8.0),
        "inward_limits": (2.0, 1.0),
        "outward_limits": (1.5, 1.0),
        "passive_loss": (0.0, 0.0),
        "targets": (5.0, 4.0),
        "maintenance": (1.0, 0.5),
        "motion_cost": (0.5, 0.0),
        "max_displacement": 2.0,
        "damage_from_total_shortfall": 0.25,
        "failure_damage": 1.0,
    }
    values.update(changes)
    return BoundaryPhenotype(**values)


def _state(boundary=None, reserves=(2.0, 2.0)):
    founder = Founder(1, Genome(), reserves, boundary or _boundary(), (1.0, 1.0), (0.0, 0.0))
    world = found_world(AbioticWorld("t", "c", "m"), [founder])
    return world.living[1]


def _totals(state, ambient):
    return tuple(a + b for a, b in zip(state.reserves, ambient.amounts))


def test_exchange_is_limited_by_body_environment_and_capacity_and_conserves_channels():
    state = _state(reserves=(9.5, 2.0))
    ambient = MatterPool([10.0, 0.25])
    before = _totals(state, ambient)

    result = body_tick(state, ambient, BodyIntent((99.0, 99.0), (0.0, 0.0)))

    assert result.exchange.active_flux == (0.5, 0.25)
    assert _totals(state, ambient) == pytest.approx(before)
    assert all(amount <= cap for amount, cap in zip(state.reserves, state.boundary.capacities))


def test_internal_need_is_a_signal_not_a_forced_action():
    state = _state(reserves=(0.2, 2.0))
    ambient = MatterPool([10.0, 10.0])
    assert internal_signals(state)[0] > 0

    result = body_tick(state, ambient, BodyIntent((-1.0, 0.0), (0.0, 0.0)))

    assert result.exchange.active_flux[0] < 0
    assert result.maintenance.shortfall[0] == pytest.approx(1.0)
    assert state.damage > 0


def test_motion_pays_from_reserves_and_is_limited_without_assigning_a_species():
    state = _state(reserves=(0.5, 2.0))
    ambient = MatterPool([0.0, 0.0])
    before = _totals(state, ambient)

    result = body_tick(state, ambient, BodyIntent((0.0, 0.0), (3.0, 4.0)))

    assert result.motion.requested_distance == 5.0
    assert result.motion.actual_distance == 1.0
    assert state.position == pytest.approx([0.6, 0.8])
    assert result.motion.spent == (0.5, 0.0)
    assert _totals(state, ambient) == pytest.approx(before)


def test_a_body_with_no_displacement_capacity_stays_put_but_uses_the_same_interface():
    state = _state(_boundary(max_displacement=0.0), reserves=(2.0, 2.0))
    ambient = MatterPool([0.0, 0.0])

    result = body_tick(state, ambient, BodyIntent((0.0, 0.0), (4.0, -2.0)))

    assert result.motion.actual_distance == 0.0
    assert state.position == [0.0, 0.0]


def test_repeated_upkeep_failure_can_end_a_lineage_without_rescue():
    state = _state(_boundary(damage_from_total_shortfall=0.6), reserves=(0.0, 0.0))
    ambient = MatterPool([0.0, 0.0])

    body_tick(state, ambient, BodyIntent((0.0, 0.0), (0.0, 0.0)))
    assert alive(state)
    body_tick(state, ambient, BodyIntent((0.0, 0.0), (0.0, 0.0)))
    assert not alive(state)
    assert state.age_ticks == 2


def test_body_boundary_and_intent_have_no_taxonomic_or_food_labels():
    forbidden = {"species", "lineage", "kind", "diet", "prey", "food", "plant", "animal", "human"}
    assert {field.name for field in fields(BoundaryPhenotype)}.isdisjoint(forbidden)
    assert {field.name for field in fields(BodyIntent)}.isdisjoint(forbidden)


def test_invalid_body_vectors_are_rejected_before_a_run_starts():
    with pytest.raises(ValueError, match="same width"):
        _boundary(inward_limits=(1.0,))
    with pytest.raises(ValueError, match="capacities"):
        Founder(1, Genome(), (11.0, 1.0), _boundary(), (1.0, 1.0))
