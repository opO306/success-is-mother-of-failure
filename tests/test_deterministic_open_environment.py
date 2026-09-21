import json
from pathlib import Path

from engine.deterministic import (
    EnvironmentWorldSpec,
    build_environment_rule_map,
    evaluate_environment_forecast,
    forecast_environment_world,
    initial_environment_state,
    load_environment_world_spec,
    run_environment_world,
    step_environment_world,
)

ROOT = Path(__file__).resolve().parents[1]
V1 = ROOT / "worlds" / "deterministic_environment_v1.json"
V2 = ROOT / "worlds" / "deterministic_geochemical_cycle_v2.json"
V3 = ROOT / "worlds" / "deterministic_open_water_cycle_v3.json"


def _raw(): return json.loads(V3.read_text(encoding="utf-8"))

def _cells(state): return {(x.x, x.y): x for x in state.cells}

def _heat(state, point): return {(x.x, x.y): x.energy for x in state.causal.heat}.get(point, 0)

def _isolated_raw():
    raw = _raw()
    raw["causal_world"]["execution"]["ticks"] = 1
    raw["law"]["max_heat_transfer"] = 0
    raw["law"]["max_water_transfer"] = 0
    raw["law"]["max_solute_transfer"] = 0
    raw["law"]["max_carried_solute_per_water"] = 0
    raw["law"]["max_mineral_conversion"] = 0
    raw["law"]["max_vapor_transfer"] = 0
    raw["energy_boundaries"] = []
    raw["blocked_edges"] = []
    return raw


def test_evaporation_moves_heat_into_vapor_latent_storage() -> None:
    raw = _isolated_raw(); raw["causal_world"]["heat"] = [{"x": 4, "y": 4, "energy": 4}]
    raw["cells"] = [{"x": 4, "y": 4, "elevation": 0, "water": 2, "vapor": 0,
                     "mineral": 0, "solutes": [0, 0]}]
    spec = EnvironmentWorldSpec.from_mapping(raw); initial = initial_environment_state(spec)

    result = step_environment_world(spec, initial); cell = _cells(result)[(4, 4)]

    assert (cell.water, cell.vapor, _heat(result, (4, 4))) == (1, 1, 2)
    assert result.total_energy(spec) == initial.total_energy(spec) == 4
    assert result.conserved_resources(spec)["water"] == 2


def test_condensation_releases_vapor_latent_storage_as_heat() -> None:
    raw = _isolated_raw(); raw["causal_world"]["heat"] = []
    raw["cells"] = [{"x": 4, "y": 4, "elevation": 0, "water": 0, "vapor": 1,
                     "mineral": 0, "solutes": [0, 0]}]
    spec = EnvironmentWorldSpec.from_mapping(raw); initial = initial_environment_state(spec)

    result = step_environment_world(spec, initial); cell = _cells(result)[(4, 4)]

    assert (cell.water, cell.vapor, _heat(result, (4, 4))) == (1, 0, 2)
    assert result.total_energy(spec) == initial.total_energy(spec) == 2


def test_external_input_raises_internal_energy_and_balances_ledger() -> None:
    raw = _isolated_raw(); raw["law"]["max_water_phase_change"] = 0
    raw["causal_world"]["heat"] = []; raw["cells"] = []
    raw["energy_boundaries"] = [{"x": 3, "y": 3, "input_per_tick": 3, "output_per_tick": 0}]
    spec = EnvironmentWorldSpec.from_mapping(raw); initial = initial_environment_state(spec)

    result = step_environment_world(spec, initial)

    assert result.energy_account(spec) == {"internal": 3, "supplied": 3, "removed": 0, "accounted": 0}
    assert result.energy_account(spec)["accounted"] == initial.energy_account(spec)["accounted"]


def test_external_output_cannot_remove_more_than_local_heat() -> None:
    raw = _isolated_raw(); raw["law"]["max_water_phase_change"] = 0
    raw["causal_world"]["heat"] = [{"x": 3, "y": 3, "energy": 1}]; raw["cells"] = []
    raw["energy_boundaries"] = [{"x": 3, "y": 3, "input_per_tick": 0, "output_per_tick": 3}]
    spec = EnvironmentWorldSpec.from_mapping(raw)

    result = step_environment_world(spec, initial_environment_state(spec))

    assert _heat(result, (3, 3)) == 0
    assert result.energy_account(spec) == {"internal": 0, "supplied": 0, "removed": 1, "accounted": 1}


def test_open_example_preserves_water_material_and_accounted_energy() -> None:
    spec = load_environment_world_spec(V3); state = initial_environment_state(spec)
    resources = state.conserved_resources(spec); accounted = state.energy_account(spec)["accounted"]

    for _ in range(spec.causal_world.ticks):
        state = step_environment_world(spec, state)
        assert state.conserved_resources(spec) == resources
        assert state.energy_account(spec)["accounted"] == accounted

    assert resources == {"water": 8, "material_inventory": [2, 0]}
    assert state.energy_supplied == 24
    assert state.energy_removed == 2


def test_v1_and_v2_run_digests_remain_unchanged() -> None:
    assert run_environment_world(load_environment_world_spec(V1)).digest == "e37f773f6b13a8245943c76562493ccfa8c6f25ee88e9a40fd629f190f623c7a"
    assert run_environment_world(load_environment_world_spec(V2)).digest == "a87ef61545ac170235292fa94895e490bd343e16027b671632523fa39e29692a"


def test_b_model_forecasts_open_environment_exactly() -> None:
    spec = load_environment_world_spec(V3)
    forecast = forecast_environment_world(spec)
    evaluation = evaluate_environment_forecast(forecast, run_environment_world(spec))
    events = {rule.event for rule in build_environment_rule_map(spec)}
    predicted = {event["kind"] for step in forecast.steps for event in step.predicted_events}

    assert evaluation.complete_match is True
    assert evaluation.matched_ticks == (1, 2, 3, 4, 5, 6)
    assert {"local_vapor_diffusion", "external_energy_exchange", "local_evaporation", "local_condensation"} <= events
    assert {"local_vapor_changed", "external_energy_supplied", "external_energy_removed"} <= predicted
    assert all(step.energy_account["accounted"] == 10 for step in forecast.steps)


def test_open_environment_run_is_bit_identical() -> None:
    spec = load_environment_world_spec(V3); expected = run_environment_world(spec)

    assert all(run_environment_world(spec) == expected for _ in range(25))
