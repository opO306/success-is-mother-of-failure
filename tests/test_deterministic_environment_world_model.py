import inspect
from dataclasses import replace
from pathlib import Path

import pytest

from engine.deterministic import (
    build_environment_rule_map,
    evaluate_environment_forecast,
    forecast_environment_world,
    load_environment_world_spec,
    run_environment_world,
)
import engine.deterministic.environment_world_model as environment_model_module

ROOT = Path(__file__).resolve().parents[1]
V1 = ROOT / "worlds" / "deterministic_environment_v1.json"
V2 = ROOT / "worlds" / "deterministic_geochemical_cycle_v2.json"


def test_environment_model_builds_machine_readable_rule_map() -> None:
    rules = build_environment_rule_map(load_environment_world_spec(V2))
    events = {rule.event for rule in rules}

    assert {
        "local_heat_transfer", "downhill_water_transfer", "local_solute_diffusion",
        "water_coupled_solute_transport", "local_mineral_dissolution", "local_mineral_precipitation",
    } <= events
    dissolution = next(rule for rule in rules if rule.event == "local_mineral_dissolution")
    assert dissolution.locality == "same_cell"
    assert dissolution.conserves == ("material_inventory", "energy")
    assert "local heat -> dissolved chemical storage" in dissolution.effects


def test_environment_model_explains_local_field_changes() -> None:
    forecast = forecast_environment_world(load_environment_world_spec(V2), 6)
    kinds = {event["kind"] for step in forecast.steps for event in step.predicted_events}

    assert "local_water_changed" in kinds
    assert "local_solute_changed" in kinds
    assert "mineral_dissolved" in kinds
    assert "mineral_precipitated" in kinds
    assert "local_heat_changed" in kinds


def test_environment_forecast_records_raw_and_conserved_accounts() -> None:
    forecast = forecast_environment_world(load_environment_world_spec(V2))

    assert all(step.conserved_resources == {"water": 12, "material_inventory": [10, 2]}
               for step in forecast.steps)
    assert all(step.total_energy == 12 for step in forecast.steps)
    assert forecast.steps[-1].resources["mineral"] == 5
    assert forecast.steps[-1].resources["solutes"] == [5, 2]


def test_exact_environment_forecast_matches_actual_a2_1_checkpoints() -> None:
    spec = load_environment_world_spec(V2)
    forecast = forecast_environment_world(spec)
    run = run_environment_world(spec)

    evaluation = evaluate_environment_forecast(forecast, run)

    assert evaluation.complete_match is True
    assert evaluation.compared_ticks == (1, 2, 3, 4, 5, 6)
    assert evaluation.matched_ticks == evaluation.compared_ticks
    assert evaluation.mismatches == ()


def test_environment_model_also_forecasts_preserved_a2_v1() -> None:
    spec = load_environment_world_spec(V1)
    evaluation = evaluate_environment_forecast(forecast_environment_world(spec), run_environment_world(spec))

    assert evaluation.complete_match is True
    assert evaluation.compared_ticks == tuple(range(1, 9))


def test_environment_evaluation_detects_wrong_spec_and_state_hash() -> None:
    spec = load_environment_world_spec(V2)
    forecast = forecast_environment_world(spec)
    run = run_environment_world(spec)

    wrong_spec = evaluate_environment_forecast(forecast, replace(run, spec_digest="wrong"))
    checkpoints = list(run.checkpoints)
    checkpoints[1] = replace(checkpoints[1], state_digest="wrong")
    wrong_state = evaluate_environment_forecast(forecast, replace(run, checkpoints=tuple(checkpoints)))

    assert wrong_spec.complete_match is False
    assert wrong_spec.spec_matches is False
    assert wrong_state.complete_match is False
    assert wrong_state.mismatches[0]["tick"] == 1


def test_environment_model_refuses_more_than_ten_ticks() -> None:
    spec = load_environment_world_spec(V2)

    with pytest.raises(ValueError, match="zero through 10"):
        forecast_environment_world(spec, 11)


def test_environment_forecast_is_read_only_and_reproducible() -> None:
    spec = load_environment_world_spec(V2); before = spec.digest

    first = forecast_environment_world(spec); second = forecast_environment_world(spec)

    assert spec.digest == before
    assert first == second
    assert first.digest == second.digest
    assert first.model_kind == "exact-read-only-a2-environment-clone"


def test_environment_world_model_has_no_random_interface() -> None:
    source = inspect.getsource(environment_model_module)

    assert "import random" not in source
    assert "choice_index" not in source
    assert "SeededEventSource" not in source
    assert "seed" not in inspect.signature(forecast_environment_world).parameters
