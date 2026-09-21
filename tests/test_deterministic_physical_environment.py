import json
from pathlib import Path

import pytest

from engine.deterministic import (
    EnvironmentWorldSpec,
    evaluate_environment_forecast,
    forecast_environment_world,
    initial_environment_state,
    load_environment_world_spec,
    run_environment_world,
    run_physical_environment_scaling_audit,
    step_environment_world,
)

ROOT = Path(__file__).resolve().parents[1]
V1 = ROOT / "worlds" / "deterministic_environment_v1.json"
V2 = ROOT / "worlds" / "deterministic_geochemical_cycle_v2.json"
V3 = ROOT / "worlds" / "deterministic_open_water_cycle_v3.json"
V4 = ROOT / "worlds" / "deterministic_physical_flux_v4.json"


def _raw(): return json.loads(V4.read_text(encoding="utf-8"))

def _cells(state): return {(x.x, x.y): x for x in state.cells}


def test_physical_flux_v4_round_trips() -> None:
    first = load_environment_world_spec(V4)
    second = EnvironmentWorldSpec.from_mapping(first.canonical())

    assert first == second
    assert first.digest == second.digest
    assert first.physical_scale is not None
    assert {first.physical_scale.tick_fraction(channel) for channel in
            ("heat", "water_surface", "solute", "vapor")} == {__import__("fractions").Fraction(1, 4)}


def test_v4_rejects_missing_or_unstable_flux_channel() -> None:
    raw = _raw(); raw["physical_scale"]["flux_laws"].pop()
    with pytest.raises(ValueError, match="exactly the four"):
        EnvironmentWorldSpec.from_mapping(raw)

    raw = _raw(); raw["physical_scale"]["flux_laws"][0]["diffusivity"]["denominator_fs"] = 1
    with pytest.raises(ValueError, match="stability bound"):
        EnvironmentWorldSpec.from_mapping(raw)


def test_v4_rejects_unsupported_unit_labels() -> None:
    raw = _raw(); raw["physical_scale"]["units"]["cell_length_unit"] = "meter"
    with pytest.raises(ValueError, match="unsupported unit labels"):
        EnvironmentWorldSpec.from_mapping(raw)


def test_v4_water_carries_source_concentration_proportionally() -> None:
    raw = _raw(); raw["causal_world"]["execution"]["ticks"] = 1; raw["causal_world"]["heat"] = []
    raw["law"]["max_heat_transfer"] = 0; raw["law"]["max_solute_transfer"] = 0
    raw["law"]["max_vapor_transfer"] = 0
    raw["cells"] = [
        {"x": 4, "y": 4, "elevation": 0, "water": 8, "vapor": 0, "mineral": 0, "solutes": [8, 0]},
        {"x": 5, "y": 4, "elevation": 0, "water": 0, "vapor": 0, "mineral": 0, "solutes": [0, 0]},
    ]
    raw["blocked_edges"] = [
        {"first": [4, 4], "second": [3, 4]}, {"first": [4, 4], "second": [4, 3]},
        {"first": [4, 4], "second": [4, 5]}, {"first": [5, 4], "second": [6, 4]},
        {"first": [5, 4], "second": [5, 3]}, {"first": [5, 4], "second": [5, 5]},
    ]
    spec = EnvironmentWorldSpec.from_mapping(raw)

    result = step_environment_world(spec, initial_environment_state(spec)); cells = _cells(result)

    assert (cells[(4, 4)].water, cells[(5, 4)].water) == (6, 2)
    assert (cells[(4, 4)].solutes[0], cells[(5, 4)].solutes[0]) == (6, 2)


def test_all_physical_transport_channels_preserve_amount_and_reduce_difference() -> None:
    audit = run_physical_environment_scaling_audit()

    assert audit.all_channels_candidate is True
    assert {x.channel for x in audit.channels} == {"heat", "water_surface", "solute", "vapor"}
    assert all(x.status == "candidate-converging" for x in audit.channels)
    assert all({o.initial_physical_amount for o in x.observations} == {65536} for x in audit.channels)
    assert all({o.final_physical_amount for o in x.observations} == {65536} for x in audit.channels)
    assert all(x.successive_differences[1] <= x.successive_differences[0] for x in audit.channels)


def test_v4_b_model_matches_actual_run() -> None:
    spec = load_environment_world_spec(V4)
    evaluation = evaluate_environment_forecast(forecast_environment_world(spec), run_environment_world(spec))

    assert evaluation.complete_match is True
    assert evaluation.compared_ticks == (1, 2, 3, 4)


def test_v4_run_is_deterministic() -> None:
    spec = load_environment_world_spec(V4); expected = run_environment_world(spec)

    assert all(run_environment_world(spec) == expected for _ in range(25))


def test_v1_v2_v3_digests_remain_unchanged() -> None:
    expected = (
        (V1, "87bfc511c0b7995a37b3bde03d840947e5fbd6579c1e91f9968630dbd454ff1a",
             "e37f773f6b13a8245943c76562493ccfa8c6f25ee88e9a40fd629f190f623c7a"),
        (V2, "c1ba4a7dfcf8f13e2bb612eb1e804c546b685b11108a23204ae5845316078527",
             "a87ef61545ac170235292fa94895e490bd343e16027b671632523fa39e29692a"),
        (V3, "24731d251c870b3c1106484cbc6c51949890a53965b1c860cd6a692f7b04a422",
             "ba0ffc7041c153c961117d043e27f61689e922fa3bf3808e06f90b9ff65f54bb"),
    )
    for path, spec_digest, run_digest in expected:
        spec = load_environment_world_spec(path)
        assert spec.digest == spec_digest
        assert run_environment_world(spec).digest == run_digest
