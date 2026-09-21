import copy
import json
from pathlib import Path

import pytest

from engine.deterministic import CausalWorldSpec, load_causal_world_spec

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "worlds" / "deterministic_bond_cycle_v1.json"


def _raw():
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


def test_causal_spec_round_trips_with_a_stable_digest() -> None:
    first = load_causal_world_spec(EXAMPLE)
    second = CausalWorldSpec.from_mapping(first.canonical())

    assert first == second
    assert first.digest == second.digest
    assert first.bond_rules[0].canonical()["conserves"] == ["material", "energy", "momentum"]
    assert first.bond_rules[0].canonical()["locality"] == "same_cell"


def test_causal_spec_rejects_hidden_probability_and_high_level_goals() -> None:
    raw = _raw(); raw["bond_rules"][0]["probability"] = 50
    with pytest.raises(ValueError, match="keys differ"):
        CausalWorldSpec.from_mapping(raw)

    raw = _raw(); raw["fitness"] = 10
    with pytest.raises(ValueError, match="forbidden high-level field"):
        CausalWorldSpec.from_mapping(raw)


def test_causal_spec_rejects_false_conservation_claims() -> None:
    raw = _raw(); raw["bond_rules"][0]["conserves"] = ["material"]
    with pytest.raises(ValueError, match="conservation contract"):
        CausalWorldSpec.from_mapping(raw)


def test_causal_spec_rejects_odd_break_heat_and_unequal_masses() -> None:
    raw = _raw(); raw["bond_rules"][0]["break_heat"] = 1
    with pytest.raises(ValueError, match="break_heat"):
        CausalWorldSpec.from_mapping(raw)

    raw = _raw(); raw["materials"].append({"kind": 1, "mass": 2, "ports": 4})
    raw["bond_rules"][0]["right_kind"] = 1
    with pytest.raises(ValueError, match="equal masses"):
        CausalWorldSpec.from_mapping(raw)


def test_causal_spec_rejects_unknown_tick_order() -> None:
    raw = _raw(); raw["kernel"]["tick_order"].reverse()
    with pytest.raises(ValueError, match="three-phase tick order"):
        CausalWorldSpec.from_mapping(raw)
