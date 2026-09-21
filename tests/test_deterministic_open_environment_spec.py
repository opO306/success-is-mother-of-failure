import json
from pathlib import Path

import pytest

from engine.deterministic import EnvironmentWorldSpec, load_environment_world_spec

ROOT = Path(__file__).resolve().parents[1]
V1 = ROOT / "worlds" / "deterministic_environment_v1.json"
V2 = ROOT / "worlds" / "deterministic_geochemical_cycle_v2.json"
V3 = ROOT / "worlds" / "deterministic_open_water_cycle_v3.json"


def _raw(): return json.loads(V3.read_text(encoding="utf-8"))


def test_open_environment_v3_round_trips_with_stable_digest() -> None:
    first = load_environment_world_spec(V3)
    second = EnvironmentWorldSpec.from_mapping(first.canonical())

    assert first == second
    assert first.digest == second.digest
    assert first.format == "deterministic-environment-world-spec-v3"
    assert first.cells[0].vapor == 0
    assert len(first.energy_boundaries) == 2


def test_open_extension_preserves_v1_and_v2_spec_digests() -> None:
    assert load_environment_world_spec(V1).digest == "87bfc511c0b7995a37b3bde03d840947e5fbd6579c1e91f9968630dbd454ff1a"
    assert load_environment_world_spec(V2).digest == "c1ba4a7dfcf8f13e2bb612eb1e804c546b685b11108a23204ae5845316078527"


def test_v3_rejects_overlapping_phase_thresholds() -> None:
    raw = _raw(); raw["law"]["evaporation_heat_at_least"] = raw["law"]["condensation_heat_at_most"]
    with pytest.raises(ValueError, match="must exceed"):
        EnvironmentWorldSpec.from_mapping(raw)


def test_v3_rejects_free_active_phase_change() -> None:
    raw = _raw(); raw["law"]["vaporization_energy"] = 0
    with pytest.raises(ValueError, match="positive latent energy"):
        EnvironmentWorldSpec.from_mapping(raw)


def test_v3_rejects_boundary_that_supplies_and_removes_together() -> None:
    raw = _raw(); raw["energy_boundaries"][0]["output_per_tick"] = 1
    with pytest.raises(ValueError, match="cannot supply and remove"):
        EnvironmentWorldSpec.from_mapping(raw)


def test_v3_rejects_duplicate_energy_boundary_locations() -> None:
    raw = _raw(); raw["energy_boundaries"][1]["x"] = 4; raw["energy_boundaries"][1]["y"] = 4
    with pytest.raises(ValueError, match="locations must be unique"):
        EnvironmentWorldSpec.from_mapping(raw)
