import inspect
import json
from dataclasses import replace
from pathlib import Path

from engine.deterministic import (
    CausalWorldSpec,
    HeatCellSpec,
    initial_causal_state,
    load_causal_world_spec,
    run_causal_world,
    step_causal_world,
)
import engine.deterministic.causal_kernel as causal_kernel

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "worlds" / "deterministic_bond_cycle_v1.json"


def _spec(raw=None):
    return CausalWorldSpec.from_mapping(raw or json.loads(EXAMPLE.read_text(encoding="utf-8")))


def test_particles_bond_from_collision_then_local_heat_breaks_the_bond() -> None:
    spec = _spec(); initial = initial_causal_state(spec)

    bonded = step_causal_world(spec, initial)
    separated = step_causal_world(spec, bonded)

    assert len(bonded.bonds) == 1
    assert bonded.bonds[0].stored_energy == 4
    assert all(item.kinetic_energy == 0 for item in bonded.particles)
    assert bonded.total_energy() == initial.total_energy() == 6
    assert len(separated.bonds) == 0
    assert [item.kinetic_energy for item in separated.particles] == [3, 3]
    assert separated.heat == ()
    assert {(item.x, item.direction) for item in separated.particles} == {(9, "W"), (11, "E")}
    assert separated.total_energy() == initial.total_energy()
    assert separated.momentum(spec) == initial.momentum(spec) == (0, 0)


def test_heat_elsewhere_cannot_break_a_bond() -> None:
    raw = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    raw["heat"] = [{"x": 0, "y": 0, "energy": 2}]
    spec = _spec(raw)

    bonded = step_causal_world(spec, initial_causal_state(spec))
    still_bonded = step_causal_world(spec, bonded)

    assert len(still_bonded.bonds) == 1
    assert still_bonded.heat == (HeatCellSpec(0, 0, 2),)


def test_two_distant_collisions_form_bonds_in_the_same_tick() -> None:
    raw = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    raw["particles"].extend([
        {"particle_id": 3, "kind": 0, "x": 19, "y": 20, "direction": "E", "orientation": "E", "kinetic_energy": 2},
        {"particle_id": 4, "kind": 0, "x": 21, "y": 20, "direction": "W", "orientation": "W", "kinetic_energy": 2},
    ])
    raw["heat"].append({"x": 20, "y": 20, "energy": 2})
    spec = _spec(raw)

    result = step_causal_world(spec, initial_causal_state(spec))

    assert len(result.bonds) == 2
    assert {(bond.x, bond.y) for bond in result.bonds} == {(10, 10), (20, 20)}


def _physical_without_ids(state):
    particles = sorted((p.kind, p.x, p.y, p.direction, p.orientation, p.kinetic_energy) for p in state.particles)
    bonds = sorted((b.rule_id, b.stored_energy, b.x, b.y) for b in state.bonds)
    return particles, bonds, state.heat


def test_particle_labels_do_not_change_physical_history() -> None:
    original = _spec(); raw = original.canonical()
    raw["particles"][0]["particle_id"], raw["particles"][1]["particle_id"] = 102, 101
    relabeled = _spec(raw)

    first = run_causal_world(original)
    second = run_causal_world(relabeled)

    assert _physical_without_ids(first.final_state) == _physical_without_ids(second.final_state)


def test_same_causal_world_repeats_bit_identically() -> None:
    spec = _spec(); expected = run_causal_world(spec)

    assert all(run_causal_world(spec) == expected for _ in range(100))
    assert len({run_causal_world(spec).digest for _ in range(100)}) == 1


def test_every_tick_preserves_material_energy_and_momentum() -> None:
    spec = _spec(); state = initial_causal_state(spec)
    counts, energy, momentum = state.material_counts(), state.total_energy(), state.momentum(spec)

    for _ in range(spec.ticks):
        state = step_causal_world(spec, state)
        assert state.material_counts() == counts
        assert state.total_energy() == energy
        assert state.momentum(spec) == momentum


def test_causal_kernel_has_no_random_interface() -> None:
    source = inspect.getsource(causal_kernel)

    assert "import random" not in source
    assert "choice_index" not in source
    assert "SeededEventSource" not in source
    assert "seed" not in inspect.signature(step_causal_world).parameters
