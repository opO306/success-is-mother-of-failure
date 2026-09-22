from pathlib import Path

import pytest

from engine.deterministic import load_causal_world_spec
from engine.deterministic.role_resolver import (
    resolve_bond_rule_role,
    resolve_heat_cell_role,
    resolve_particle_role,
)

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "worlds" / "deterministic_bond_cycle_v1.json"


def test_resolve_particle_role_matches_exactly_one() -> None:
    spec = load_causal_world_spec(EXAMPLE)
    assert resolve_particle_role(spec, "left_collider", 9, 10, "E") == 1
    assert resolve_particle_role(spec, "right_collider", 11, 10, "W") == 2


def test_resolve_particle_role_raises_on_no_match() -> None:
    spec = load_causal_world_spec(EXAMPLE)
    with pytest.raises(ValueError, match="matched no particle"):
        resolve_particle_role(spec, "nobody", 0, 0, "N")


def test_resolve_particle_role_raises_on_ambiguous_match() -> None:
    # A causal v1/v2 spec cannot legally declare two particles sharing
    # (kind, x, y, direction) -- `CausalWorldSpec.from_mapping` already
    # rejects that as a "directional material channel" collision. Build the
    # frozen dataclass directly (bypassing that spec-level validation) to
    # exercise resolve_particle_role's own ambiguity guard in isolation.
    from dataclasses import replace
    spec = load_causal_world_spec(EXAMPLE)
    duplicate_particle = replace(spec.particles[0], particle_id=99)
    duplicated = replace(spec, particles=spec.particles + (duplicate_particle,))
    with pytest.raises(ValueError, match="ambiguous"):
        resolve_particle_role(duplicated, "left_collider", 9, 10, "E")


def test_resolve_heat_cell_role_always_resolves() -> None:
    spec = load_causal_world_spec(EXAMPLE)
    assert resolve_heat_cell_role(spec, "local_heat_source", 10, 10) == (10, 10)


def test_resolve_bond_rule_role_raises_when_missing() -> None:
    spec = load_causal_world_spec(EXAMPLE)
    assert resolve_bond_rule_role(spec, "bond_under_test", "kind0-facing-bond-v1") == "kind0-facing-bond-v1"
    with pytest.raises(ValueError, match="not found"):
        resolve_bond_rule_role(spec, "bond_under_test", "no-such-rule")
