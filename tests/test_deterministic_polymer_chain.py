"""Chains longer than two, built by collisions rather than declared.

Under v1 a bond could only form when two free particles met head-on with
their momenta cancelling to zero. A standing pair had no motion to cancel
against, so nothing could ever join it: two was the ceiling, and no rule
said so — it fell out of the arithmetic.

v2 lets a particle hold as many bonds as the `ports` its material already
declares, and lets a bonded group carry motion as one body. An arriving
particle is absorbed and the chain takes up the momentum it brought: more
mass moving slower. Nothing here instructs the world to build a polymer;
growth is what the collision rules now permit, or fail to.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from engine.deterministic import (
    CausalWorldSpec,
    initial_causal_state,
    load_causal_world_spec,
    run_causal_world,
    step_causal_world,
)
from engine.deterministic.causal_kernel import chains, port_limits

ROOT = Path(__file__).resolve().parents[1]
POLYMER = ROOT / "worlds" / "deterministic_polymer_chain_v2.json"
BOND_V1 = ROOT / "worlds" / "deterministic_bond_cycle_v1.json"


def _longest_chain(state) -> int:
    grouped = chains(state.bonds)
    return max((len(members) for members in grouped.values()), default=1)


def _advance(spec, ticks: int):
    state = initial_causal_state(spec)
    history = [state]
    for _ in range(ticks):
        state = step_causal_world(spec, state)
        history.append(state)
    return history


# --- v1 is untouched --------------------------------------------------------

def test_v1_still_refuses_a_second_bond_on_one_particle() -> None:
    """The old rule survives exactly, so existing runs reproduce."""
    spec = load_causal_world_spec(BOND_V1)
    assert port_limits(spec) == {0: 1}, "a v1 world caps every material at one bond"

    history = _advance(spec, spec.ticks)
    assert max(_longest_chain(state) for state in history) == 2


def test_v1_worlds_keep_their_digest() -> None:
    spec = load_causal_world_spec(BOND_V1)
    first, second = run_causal_world(spec), run_causal_world(spec)
    assert first.digest == second.digest
    assert first.final_state.digest == second.final_state.digest


# --- v2 permits what v1 could not -------------------------------------------

def test_v2_honours_the_ports_its_materials_declare() -> None:
    spec = load_causal_world_spec(POLYMER)
    assert port_limits(spec) == {0: 4}


def test_a_third_particle_joins_a_standing_pair(tmp_path: Path) -> None:
    spec = load_causal_world_spec(POLYMER)
    history = _advance(spec, spec.ticks)

    lengths = [_longest_chain(state) for state in history]
    assert max(lengths) >= 3, f"no chain reached three: {lengths}"
    assert lengths.index(2) < lengths.index(3), "the pair must form before it grows"


def test_growth_conserves_energy_and_momentum_every_tick() -> None:
    """The point of absorbing rather than cancelling: the totals still hold."""
    spec = load_causal_world_spec(POLYMER)
    state = initial_causal_state(spec)
    energy, momentum, counts = (state.total_energy(), state.momentum(spec),
                                state.material_counts())

    for _ in range(spec.ticks):
        state = step_causal_world(spec, state)
        assert state.total_energy() == energy
        assert state.momentum(spec) == momentum
        assert state.material_counts() == counts


def test_a_grown_chain_travels_as_one_body() -> None:
    """Every member moves together, at the speed the whole mass now carries."""
    spec = load_causal_world_spec(POLYMER)
    history = _advance(spec, spec.ticks)

    grown = next(state for state in history if _longest_chain(state) >= 3)
    members = max(chains(grown.bonds).values(), key=len)
    by_id = {item.particle_id: item for item in grown.particles}
    places = {(by_id[item].x, by_id[item].y) for item in members}
    assert len(places) == 1, "a chain occupies one cell"

    later = history[history.index(grown) + 1]
    by_later = {item.particle_id: item for item in later.particles}
    moved = {(by_later[item].x, by_later[item].y) for item in members}
    assert len(moved) == 1, "the chain stayed together"
    assert moved != places, "the chain carried its momentum forward"


def test_a_travelling_chain_keeps_its_motion_on_one_member() -> None:
    """Copying the velocity onto every member would double-count the energy."""
    spec = load_causal_world_spec(POLYMER)
    for state in _advance(spec, spec.ticks):
        for members in set(chains(state.bonds).values()):
            by_id = {item.particle_id: item for item in state.particles}
            holders = [item for item in members if by_id[item].kinetic_energy]
            assert len(holders) <= 1
            if holders:
                assert holders[0] == min(members)


def test_momentum_counts_the_whole_chain_mass() -> None:
    spec = load_causal_world_spec(POLYMER)
    grown = next(state for state in _advance(spec, spec.ticks)
                 if _longest_chain(state) >= 3)
    members = max(chains(grown.bonds).values(), key=len)
    by_id = {item.particle_id: item for item in grown.particles}
    holder = by_id[min(members)]
    masses = {item.kind: item.mass for item in spec.materials}

    expected = sum(masses[by_id[item].kind] for item in members) * holder.kinetic_energy
    assert abs(grown.momentum(spec)[0]) == expected


# --- the limits are real, not decorative ------------------------------------

def _polymer_document(**particle_changes) -> dict:
    document = json.loads(POLYMER.read_text(encoding="utf-8"))
    document.update(particle_changes)
    return document


def test_growth_is_refused_when_no_integer_velocity_exists() -> None:
    """A collision needing a fractional speed does not happen at all.

    The arriving particle carries momentum 4 onto a chain of mass 2; the
    joined body of mass 3 would have to travel at 4/3. In an integer world
    that encounter simply does not bond — a real outcome, not a rounding.
    """
    document = _polymer_document(particles=[
        {"particle_id": 1, "kind": 0, "x": 9, "y": 10, "direction": "E",
         "orientation": "E", "kinetic_energy": 2},
        {"particle_id": 2, "kind": 0, "x": 11, "y": 10, "direction": "W",
         "orientation": "W", "kinetic_energy": 2},
        {"particle_id": 3, "kind": 0, "x": 6, "y": 10, "direction": "E",
         "orientation": "E", "kinetic_energy": 4},
    ])
    document["bond_rules"][0]["minimum_collision_energy"] = 3
    spec = CausalWorldSpec.from_mapping(document)

    assert max(_longest_chain(state) for state in _advance(spec, 8)) == 2


def test_growth_is_refused_below_the_declared_collision_energy() -> None:
    document = _polymer_document()
    document["bond_rules"][0]["minimum_collision_energy"] = 99
    spec = CausalWorldSpec.from_mapping(document)

    assert max(_longest_chain(state) for state in _advance(spec, 8)) == 1


def test_a_single_port_material_cannot_form_a_chain() -> None:
    """`ports` is the declared limit, and v2 enforces it rather than ignoring it."""
    document = _polymer_document()
    document["materials"] = [{"kind": 0, "mass": 1, "ports": 1}]
    spec = CausalWorldSpec.from_mapping(document)
    assert port_limits(spec) == {0: 1}

    assert max(_longest_chain(state) for state in _advance(spec, 8)) == 2


def test_the_world_is_reproducible() -> None:
    spec = load_causal_world_spec(POLYMER)
    first, second = run_causal_world(spec), run_causal_world(spec)
    assert first.digest == second.digest


def test_the_independent_ledger_follows_a_travelling_chain() -> None:
    """The audit must track the new physics, not the physics it was written for.

    A recount that still skipped every bonded particle would read a moving
    chain as motionless and silently disagree with the engine from the tick
    growth first happens — which is what it did before chains could travel.
    """
    from audit.independent_conservation import read_parameters, recount

    spec = load_causal_world_spec(POLYMER)
    document = {"format": "deterministic-environment-world-spec-v1",
                "solute_kinds": 0, "law": {},
                "causal_world": json.loads(POLYMER.read_text(encoding="utf-8"))}
    parameters = read_parameters(document)

    for state in _advance(spec, spec.ticks):
        snapshot = {"causal": state.canonical(), "cells": [],
                    "energy_supplied": 0, "energy_removed": 0}
        ledger = recount(snapshot, parameters)
        assert ledger.momentum == state.momentum(spec)
        assert ledger.energy_internal == state.total_energy()


def test_port_limits_are_not_part_of_state_identity() -> None:
    """Two states with the same particles are the same state.

    The limits are a rule the world is run under, not something the state
    carries, so they must stay out of equality and out of the digest.
    """
    spec = load_causal_world_spec(POLYMER)
    state = initial_causal_state(spec)
    relaxed = type(state)(state.tick, state.particles, state.heat, state.bonds,
                          {0: 9}, state.chains_may_move)

    assert relaxed == state
    assert relaxed.digest == state.digest
