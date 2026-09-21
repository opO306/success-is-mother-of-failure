import copy
import json
from pathlib import Path

import pytest

from engine.deterministic import DeterministicWorldSpec, load_world_spec


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "worlds" / "deterministic_collision_smoke_v1.json"


def _raw() -> dict:
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


def test_b0_example_loads_and_has_a_stable_digest() -> None:
    first = load_world_spec(EXAMPLE)
    second = DeterministicWorldSpec.from_mapping(_raw())

    assert first == second
    assert first.digest == second.digest
    assert first.kernel.deterministic is True
    assert first.execution.ticks == 128
    assert len(first.initial_particles) == 4


def test_b0_rejects_unknown_fields_instead_of_hiding_new_physics() -> None:
    raw = _raw()
    raw["kernel"]["lucky_growth"] = 10

    with pytest.raises(ValueError, match="keys differ"):
        DeterministicWorldSpec.from_mapping(raw)


def test_b0_rejects_high_level_fitness_and_life_commands() -> None:
    raw = _raw()
    raw["fitness"] = 1
    with pytest.raises(ValueError, match="forbidden high-level field"):
        DeterministicWorldSpec.from_mapping(raw)

    raw = _raw()
    raw["world_id"] = "MAKE_LIFE"
    with pytest.raises(ValueError, match="forbidden high-level command"):
        DeterministicWorldSpec.from_mapping(raw)


def test_b0_rejects_random_seed_and_floating_point_state() -> None:
    raw = _raw()
    raw["execution"]["seed"] = 4
    with pytest.raises(ValueError, match="keys differ"):
        DeterministicWorldSpec.from_mapping(raw)

    raw = _raw()
    raw["materials"][0]["mass"] = 1.5
    with pytest.raises(ValueError, match="floating point is forbidden"):
        DeterministicWorldSpec.from_mapping(raw)


def test_b0_rejects_duplicate_channels_and_unknown_materials() -> None:
    raw = _raw()
    raw["initial_particles"].append(copy.deepcopy(raw["initial_particles"][0]))
    with pytest.raises(ValueError, match="duplicate"):
        DeterministicWorldSpec.from_mapping(raw)

    raw = _raw()
    raw["initial_particles"][0]["kind"] = 99
    with pytest.raises(ValueError, match="unknown material"):
        DeterministicWorldSpec.from_mapping(raw)
