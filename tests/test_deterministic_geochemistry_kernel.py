import json
from pathlib import Path

from engine.deterministic import (
    EnvironmentWorldSpec,
    initial_environment_state,
    load_environment_world_spec,
    run_environment_world,
    step_environment_world,
)

ROOT = Path(__file__).resolve().parents[1]
V2 = ROOT / "worlds" / "deterministic_geochemical_cycle_v2.json"


def _raw(): return json.loads(V2.read_text(encoding="utf-8"))

def _cells(state): return {(x.x, x.y): x for x in state.cells}

def _heat(state, point): return {(x.x, x.y): x.energy for x in state.causal.heat}.get(point, 0)

def _isolated_pair_edges():
    return [
        {"first": [4, 4], "second": [3, 4]}, {"first": [4, 4], "second": [4, 3]},
        {"first": [4, 4], "second": [4, 5]}, {"first": [5, 4], "second": [6, 4]},
        {"first": [5, 4], "second": [5, 3]}, {"first": [5, 4], "second": [5, 5]},
    ]


def _disable_transport(raw):
    raw["law"]["max_heat_transfer"] = 0
    raw["law"]["max_water_transfer"] = 0
    raw["law"]["max_solute_transfer"] = 0
    raw["law"]["max_carried_solute_per_water"] = 0


def test_flow_carries_bounded_solute_to_the_neighbor() -> None:
    raw = _raw(); raw["causal_world"]["heat"] = []; raw["causal_world"]["execution"]["ticks"] = 1
    raw["law"]["max_solute_transfer"] = 0; raw["law"]["max_mineral_conversion"] = 0
    raw["cells"] = [
        {"x": 4, "y": 4, "elevation": 2, "water": 6, "mineral": 0, "solutes": [2, 0]},
        {"x": 5, "y": 4, "elevation": 0, "water": 2, "mineral": 0, "solutes": [0, 0]},
    ]
    raw["blocked_edges"] = _isolated_pair_edges()
    spec = EnvironmentWorldSpec.from_mapping(raw)

    result = step_environment_world(spec, initial_environment_state(spec)); cells = _cells(result)

    assert (cells[(4, 4)].water, cells[(5, 4)].water) == (5, 3)
    assert (cells[(4, 4)].solutes[0], cells[(5, 4)].solutes[0]) == (1, 1)


def test_hot_wet_cell_dissolves_one_local_mineral_unit() -> None:
    raw = _raw(); _disable_transport(raw); raw["causal_world"]["execution"]["ticks"] = 1
    raw["causal_world"]["heat"] = [{"x": 4, "y": 4, "energy": 4}]
    raw["cells"] = [{"x": 4, "y": 4, "elevation": 0, "water": 2, "mineral": 3, "solutes": [0, 0]}]
    spec = EnvironmentWorldSpec.from_mapping(raw); initial = initial_environment_state(spec)

    result = step_environment_world(spec, initial); cell = _cells(result)[(4, 4)]

    assert (cell.mineral, cell.solutes[0], _heat(result, (4, 4))) == (2, 1, 3)
    assert result.conserved_resources(spec) == initial.conserved_resources(spec)
    assert result.total_energy(spec) == initial.total_energy(spec) == 4


def test_cold_supersaturated_cell_precipitates_one_unit() -> None:
    raw = _raw(); _disable_transport(raw); raw["causal_world"]["execution"]["ticks"] = 1
    raw["causal_world"]["heat"] = []
    raw["cells"] = [{"x": 4, "y": 4, "elevation": 0, "water": 2, "mineral": 0, "solutes": [3, 0]}]
    spec = EnvironmentWorldSpec.from_mapping(raw); initial = initial_environment_state(spec)

    result = step_environment_world(spec, initial); cell = _cells(result)[(4, 4)]

    assert (cell.mineral, cell.solutes[0], _heat(result, (4, 4))) == (1, 2, 1)
    assert result.conserved_resources(spec) == initial.conserved_resources(spec)
    assert result.total_energy(spec) == initial.total_energy(spec) == 3


def test_geochemical_example_preserves_extended_inventory_and_energy() -> None:
    spec = load_environment_world_spec(V2); state = initial_environment_state(spec)
    inventory = state.conserved_resources(spec); energy = state.total_energy(spec)

    for _ in range(spec.causal_world.ticks):
        state = step_environment_world(spec, state)
        assert state.conserved_resources(spec) == inventory
        assert state.total_energy(spec) == energy

    assert inventory == {"water": 12, "material_inventory": [10, 2]}
    assert energy == 12


def test_geochemical_run_is_bit_identical() -> None:
    spec = load_environment_world_spec(V2); expected = run_environment_world(spec)

    assert all(run_environment_world(spec) == expected for _ in range(25))
    assert all(x.conserved_resources == {"water": 12, "material_inventory": [10, 2]}
               for x in expected.checkpoints)
