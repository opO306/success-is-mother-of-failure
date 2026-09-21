import json
from pathlib import Path

import pytest

from engine.deterministic import EnvironmentWorldSpec, load_environment_world_spec

ROOT = Path(__file__).resolve().parents[1]
V1 = ROOT / "worlds" / "deterministic_environment_v1.json"
V2 = ROOT / "worlds" / "deterministic_geochemical_cycle_v2.json"


def _raw_v2(): return json.loads(V2.read_text(encoding="utf-8"))


def test_environment_v2_round_trips_with_stable_digest() -> None:
    first = load_environment_world_spec(V2)
    second = EnvironmentWorldSpec.from_mapping(first.canonical())

    assert first == second
    assert first.digest == second.digest
    assert first.format == "deterministic-environment-world-spec-v2"
    assert first.law.max_carried_solute_per_water == 1
    assert first.law.mineral_conversion_energy == 1


def test_environment_v1_canonical_digest_is_preserved() -> None:
    spec = load_environment_world_spec(V1)

    assert spec.digest == "87bfc511c0b7995a37b3bde03d840947e5fbd6579c1e91f9968630dbd454ff1a"
    assert "max_carried_solute_per_water" not in spec.canonical()["law"]


def test_environment_v2_rejects_unknown_mineral_channel() -> None:
    raw = _raw_v2(); raw["law"]["mineral_solute_kind"] = raw["solute_kinds"]
    with pytest.raises(ValueError, match="existing solute channel"):
        EnvironmentWorldSpec.from_mapping(raw)


def test_environment_v2_rejects_overlapping_thermal_regimes() -> None:
    raw = _raw_v2(); raw["law"]["dissolve_heat_at_least"] = raw["law"]["precipitate_heat_at_most"]
    with pytest.raises(ValueError, match="must exceed"):
        EnvironmentWorldSpec.from_mapping(raw)


def test_environment_v2_rejects_free_active_conversion() -> None:
    raw = _raw_v2(); raw["law"]["mineral_conversion_energy"] = 0
    with pytest.raises(ValueError, match="positive stored energy"):
        EnvironmentWorldSpec.from_mapping(raw)
