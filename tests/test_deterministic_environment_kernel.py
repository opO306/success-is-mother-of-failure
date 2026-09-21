import inspect
import json
from pathlib import Path

from engine.deterministic import (
    initial_environment_state,
    load_environment_world_spec,
    run_environment_world,
    step_environment_world,
)
import engine.deterministic.environment_kernel as environment_kernel

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "worlds" / "deterministic_environment_v1.json"


def _spec(): return load_environment_world_spec(EXAMPLE)


def _cells(state): return {(x.x, x.y): x for x in state.cells}


def _heat(state): return {(x.x, x.y): x.energy for x in state.causal.heat}


def test_environment_tick_conserves_energy_water_mineral_and_solutes() -> None:
    spec = _spec(); state = initial_environment_state(spec)
    resources = state.resource_totals(spec.solute_kinds); energy = state.causal.total_energy()

    for _ in range(spec.causal_world.ticks):
        state = step_environment_world(spec, state)
        assert state.resource_totals(spec.solute_kinds) == resources
        assert state.causal.total_energy() == energy


def test_heat_and_downhill_water_move_without_randomness() -> None:
    raw = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    raw["causal_world"]["particles"] = []
    raw["causal_world"]["bond_rules"] = []
    raw["causal_world"]["heat"] = [{"x": 4, "y": 4, "energy": 6}]
    raw["causal_world"]["execution"]["ticks"] = 1
    raw["cells"] = [
        {"x": 4, "y": 4, "elevation": 2, "water": 6, "mineral": 0, "solutes": [4, 0]},
        {"x": 5, "y": 4, "elevation": 0, "water": 2, "mineral": 0, "solutes": [0, 4]},
    ]
    raw["blocked_edges"] = [
        {"first": [4, 4], "second": [3, 4]}, {"first": [4, 4], "second": [4, 3]},
        {"first": [4, 4], "second": [4, 5]}, {"first": [5, 4], "second": [6, 4]},
        {"first": [5, 4], "second": [5, 3]}, {"first": [5, 4], "second": [5, 5]},
    ]
    from engine.deterministic import EnvironmentWorldSpec
    spec = EnvironmentWorldSpec.from_mapping(raw)
    initial = initial_environment_state(spec)
    result = step_environment_world(spec, initial)
    before, after = _cells(initial), _cells(result)

    assert _heat(result) != _heat(initial)
    assert after[(4, 4)].water == before[(4, 4)].water - 1
    assert after[(5, 4)].water == before[(5, 4)].water + 1
    assert sum(_heat(result).values()) == sum(_heat(initial).values())


def test_mineral_is_immobile_in_environment_v1() -> None:
    spec = _spec(); result = run_environment_world(spec)
    initial = {(x.x, x.y): x.mineral for x in result.initial_state.cells if x.mineral}
    final = {(x.x, x.y): x.mineral for x in result.final_state.cells if x.mineral}

    assert final == initial


def test_blocked_edge_prevents_direct_solute_exchange() -> None:
    spec = _spec(); result = step_environment_world(spec, initial_environment_state(spec)); cells = _cells(result)

    assert cells[(21, 20)].solutes == (0, 0)


def test_two_distant_heat_regions_both_change_in_one_tick() -> None:
    raw = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    raw["causal_world"]["particles"] = []
    raw["causal_world"]["bond_rules"] = []
    raw["causal_world"]["heat"] = [{"x": 2, "y": 2, "energy": 8}, {"x": 18, "y": 18, "energy": 8}]
    raw["causal_world"]["execution"]["ticks"] = 1
    raw["cells"] = []
    raw["blocked_edges"] = []
    from engine.deterministic import EnvironmentWorldSpec
    spec = EnvironmentWorldSpec.from_mapping(raw)

    result = step_environment_world(spec, initial_environment_state(spec)); heat = _heat(result)

    assert heat[(2, 2)] < 8
    assert heat[(18, 18)] < 8
    first_neighbors = sorted(heat.get(point, 0) for point in ((1, 2), (3, 2), (2, 1), (2, 3)))
    second_neighbors = sorted(heat.get(point, 0) for point in ((17, 18), (19, 18), (18, 17), (18, 19)))
    assert first_neighbors == second_neighbors


def test_environment_run_is_bit_identical_one_hundred_times() -> None:
    spec = _spec(); expected = run_environment_world(spec)

    assert all(run_environment_world(spec) == expected for _ in range(100))
    assert len({run_environment_world(spec).digest for _ in range(100)}) == 1


def test_environment_kernel_has_no_random_interface() -> None:
    source = inspect.getsource(environment_kernel)

    assert "import random" not in source
    assert "choice_index" not in source
    assert "SeededEventSource" not in source
    assert "seed" not in inspect.signature(step_environment_world).parameters
