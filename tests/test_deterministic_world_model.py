import inspect
from dataclasses import replace
from pathlib import Path

import pytest

from engine.deterministic import (
    evaluate_forecast,
    forecast_world,
    load_causal_world_spec,
    run_causal_world,
)
import engine.deterministic.world_model as world_model_module

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "worlds" / "deterministic_bond_cycle_v1.json"


def test_world_model_builds_a_machine_readable_causal_rule_map() -> None:
    spec = load_causal_world_spec(EXAMPLE)

    forecast = forecast_world(spec)

    assert len(forecast.rule_map) == 1
    rule = forecast.rule_map[0]
    assert rule.locality == "same_cell"
    assert rule.event == "local_reversible_bond"
    assert rule.conserves == ("material", "energy", "momentum")
    assert "total_kinetic>=4" in rule.requirements
    assert "local_heat_for_break>=2" in rule.requirements


def test_world_model_foresees_bond_formation_and_local_heat_breaking() -> None:
    spec = load_causal_world_spec(EXAMPLE)

    forecast = forecast_world(spec, 4)

    first_kinds = {item["kind"] for item in forecast.steps[0].predicted_events}
    second_kinds = {item["kind"] for item in forecast.steps[1].predicted_events}
    assert {"bond_formed", "particle_moved", "particle_kinetic_changed"} <= first_kinds
    assert {"bond_broken", "particle_moved", "particle_kinetic_changed", "local_heat_changed"} <= second_kinds
    assert all(step.total_energy == 6 for step in forecast.steps)
    assert all(step.momentum == (0, 0) for step in forecast.steps)


def test_exact_v0_forecast_matches_actual_a1_checkpoints() -> None:
    spec = load_causal_world_spec(EXAMPLE)
    forecast = forecast_world(spec)
    run = run_causal_world(spec)

    evaluation = evaluate_forecast(forecast, run)

    assert evaluation.complete_match is True
    assert evaluation.compared_ticks == (1, 2, 3, 4)
    assert evaluation.matched_ticks == evaluation.compared_ticks
    assert evaluation.mismatches == ()


def test_evaluation_exposes_wrong_spec_and_wrong_state_hash() -> None:
    spec = load_causal_world_spec(EXAMPLE)
    forecast = forecast_world(spec)
    run = run_causal_world(spec)

    wrong_spec = evaluate_forecast(forecast, replace(run, spec_digest="wrong"))
    checkpoints = list(run.checkpoints)
    checkpoints[1] = replace(checkpoints[1], state_digest="wrong")
    wrong_state = evaluate_forecast(forecast, replace(run, checkpoints=tuple(checkpoints)))

    assert wrong_spec.complete_match is False
    assert wrong_spec.spec_matches is False
    assert wrong_state.complete_match is False
    assert wrong_state.mismatches[0]["tick"] == 1


def test_world_model_refuses_to_claim_more_than_ten_ticks() -> None:
    spec = load_causal_world_spec(EXAMPLE)

    with pytest.raises(ValueError, match="zero through 10"):
        forecast_world(spec, 11)


def test_forecast_is_read_only_and_reproducible() -> None:
    spec = load_causal_world_spec(EXAMPLE)
    before = spec.digest

    first = forecast_world(spec)
    second = forecast_world(spec)

    assert spec.digest == before
    assert first == second
    assert first.digest == second.digest
    assert first.model_kind == "exact-read-only-a1-clone"


def test_world_model_has_no_random_interface() -> None:
    source = inspect.getsource(world_model_module)

    assert "import random" not in source
    assert "choice_index" not in source
    assert "SeededEventSource" not in source
    assert "seed" not in inspect.signature(forecast_world).parameters
