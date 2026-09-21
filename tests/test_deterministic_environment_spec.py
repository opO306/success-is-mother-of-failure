import json
from pathlib import Path

import pytest

from engine.deterministic import EnvironmentWorldSpec, load_environment_world_spec

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "worlds" / "deterministic_environment_v1.json"


def _raw(): return json.loads(EXAMPLE.read_text(encoding="utf-8"))


def test_environment_spec_round_trips_with_stable_digest() -> None:
    first = load_environment_world_spec(EXAMPLE)
    second = EnvironmentWorldSpec.from_mapping(first.canonical())

    assert first == second
    assert first.digest == second.digest
    assert first.solute_kinds == 2


def test_environment_spec_requires_even_grid_and_fixed_phases() -> None:
    raw = _raw(); raw["causal_world"]["kernel"]["width"] = 31
    with pytest.raises(ValueError, match="even grid"):
        EnvironmentWorldSpec.from_mapping(raw)

    raw = _raw(); raw["law"]["phase_order"].reverse()
    with pytest.raises(ValueError, match="four declared"):
        EnvironmentWorldSpec.from_mapping(raw)


def test_environment_spec_rejects_nonlocal_or_duplicate_barriers() -> None:
    raw = _raw(); raw["blocked_edges"][0]["second"] = [24, 20]
    with pytest.raises(ValueError, match="neighbors"):
        EnvironmentWorldSpec.from_mapping(raw)

    raw = _raw(); raw["blocked_edges"].append(raw["blocked_edges"][0].copy())
    with pytest.raises(ValueError, match="unique"):
        EnvironmentWorldSpec.from_mapping(raw)


def test_environment_spec_requires_every_solute_channel() -> None:
    raw = _raw(); raw["cells"][0]["solutes"] = [4]
    with pytest.raises(ValueError, match="one amount per solute"):
        EnvironmentWorldSpec.from_mapping(raw)
