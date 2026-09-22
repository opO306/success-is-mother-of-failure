"""G6c-1: SyntheticWorldSpec/SyntheticCheckpoint/SyntheticRun -- the smallest
A-compatible world, and the leakage check that keeps it independent of
ground_truth/.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

from engine.deterministic.synthetic_spec import (
    SyntheticCheckpoint,
    SyntheticClamp,
    SyntheticRun,
    SyntheticWorldSpec,
)

ROOT = Path(__file__).resolve().parents[1]


def _minimal_spec(world_id: str = "WORLD-S01", rule_id: str = "RULE-S01") -> SyntheticWorldSpec:
    return SyntheticWorldSpec(
        world_id=world_id, rule_id=rule_id, variables=("x1", "x3"),
        initial_values=(("x1", False), ("x3", False)), clamps=(),
        public_controls=("x1",), public_observables=("x1", "x3"), ticks=1,
    )


def test_minimal_spec_round_trips_through_canonical_and_from_mapping() -> None:
    spec = _minimal_spec()
    rebuilt = SyntheticWorldSpec.from_mapping(spec.canonical())
    assert rebuilt.digest == spec.digest
    assert rebuilt.canonical() == spec.canonical()


def test_digest_changes_when_a_clamp_changes() -> None:
    free_spec = _minimal_spec()
    clamped_spec = SyntheticWorldSpec(
        world_id="WORLD-S01", rule_id="RULE-S01", variables=("x1", "x3"),
        initial_values=(("x1", False), ("x3", False)), clamps=(SyntheticClamp("x1", "ON"),),
        public_controls=("x1",), public_observables=("x1", "x3"), ticks=1,
    )
    assert free_spec.digest != clamped_spec.digest


def test_digest_is_stable_regardless_of_construction_order() -> None:
    a = SyntheticWorldSpec(
        world_id="WORLD-S02", rule_id="RULE-S02", variables=("x1", "x2", "x3"),
        initial_values=(("x1", False), ("x2", True), ("x3", False)),
        clamps=(SyntheticClamp("x2", "ON"), SyntheticClamp("x1", "OFF")),
        public_controls=("x1", "x2"), public_observables=("x1", "x2", "x3"), ticks=1,
    )
    b = SyntheticWorldSpec(
        world_id="WORLD-S02", rule_id="RULE-S02", variables=("x3", "x2", "x1"),
        initial_values=(("x3", False), ("x1", False), ("x2", True)),
        clamps=(SyntheticClamp("x1", "OFF"), SyntheticClamp("x2", "ON")),
        public_controls=("x2", "x1"), public_observables=("x3", "x1", "x2"), ticks=1,
    )
    assert a.digest == b.digest


def test_clamp_for_returns_free_when_unclamped() -> None:
    spec = _minimal_spec()
    assert spec.clamp_for("x1") == "FREE"


def test_clamp_for_returns_the_declared_mode() -> None:
    spec = SyntheticWorldSpec(
        world_id="WORLD-S01", rule_id="RULE-S01", variables=("x1", "x3"),
        initial_values=(("x1", False), ("x3", False)), clamps=(SyntheticClamp("x1", "ON"),),
        public_controls=("x1",), public_observables=("x1", "x3"), ticks=1,
    )
    assert spec.clamp_for("x1") == "ON"


def test_rejects_initial_values_missing_a_declared_variable() -> None:
    with pytest.raises(ValueError, match="initial_values"):
        SyntheticWorldSpec(
            world_id="W", rule_id="R", variables=("x1", "x2"),
            initial_values=(("x1", False),), clamps=(),
            public_controls=("x1",), public_observables=("x1",), ticks=1,
        )


def test_rejects_a_clamp_on_a_non_public_control() -> None:
    with pytest.raises(ValueError, match="public control"):
        SyntheticWorldSpec(
            world_id="W", rule_id="R", variables=("x1", "x2"),
            initial_values=(("x1", False), ("x2", False)), clamps=(SyntheticClamp("x2", "ON"),),
            public_controls=("x1",), public_observables=("x1", "x2"), ticks=1,
        )


def test_rejects_a_public_observable_not_in_variables() -> None:
    with pytest.raises(ValueError, match="public_observables"):
        SyntheticWorldSpec(
            world_id="W", rule_id="R", variables=("x1",),
            initial_values=(("x1", False),), clamps=(),
            public_controls=("x1",), public_observables=("x1", "x99"), ticks=1,
        )


def test_from_mapping_rejects_unknown_top_level_field() -> None:
    raw = _minimal_spec().canonical()
    raw["mediator_active"] = True  # exactly the kind of leaking field name this guards against
    with pytest.raises(ValueError, match="unknown synthetic world spec fields"):
        SyntheticWorldSpec.from_mapping(raw)


def test_checkpoint_value_of_reads_a_declared_variable() -> None:
    checkpoint = SyntheticCheckpoint(0, (("x1", True), ("x3", False)))
    assert checkpoint.value_of("x1") is True
    assert checkpoint.value_of("x3") is False
    assert checkpoint.value_of("x99") is None


def test_checkpoint_rejects_a_repeated_variable() -> None:
    with pytest.raises(ValueError, match="not repeat"):
        SyntheticCheckpoint(0, (("x1", True), ("x1", False)))


def test_run_requires_strictly_increasing_ticks() -> None:
    with pytest.raises(ValueError, match="strictly increasing"):
        SyntheticRun("WORLD-S01", "digest", (SyntheticCheckpoint(1, (("x1", True),)),
                                              SyntheticCheckpoint(0, (("x1", False),))))


def test_run_checkpoint_at_finds_the_right_tick() -> None:
    run = SyntheticRun("WORLD-S01", "digest", (
        SyntheticCheckpoint(0, (("x1", False),)), SyntheticCheckpoint(1, (("x1", True),))))
    assert run.checkpoint_at(1).value_of("x1") is True
    assert run.checkpoint_at(99) is None


def test_run_digest_is_deterministic() -> None:
    run_a = SyntheticRun("WORLD-S01", "digest", (SyntheticCheckpoint(0, (("x1", True),)),))
    run_b = SyntheticRun("WORLD-S01", "digest", (SyntheticCheckpoint(0, (("x1", True),)),))
    assert run_a.digest == run_b.digest


# ---------------------------------------------------------------------------
# Independence from ground_truth/: neither side may import the other.
# ---------------------------------------------------------------------------

def _imported_module_names(source: str) -> set[str]:
    tree = ast.parse(source)
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def test_synthetic_spec_module_does_not_import_ground_truth() -> None:
    path = ROOT / "engine" / "deterministic" / "synthetic_spec.py"
    imported = _imported_module_names(path.read_text(encoding="utf-8"))
    assert not any(name == "ground_truth" or name.startswith("ground_truth.") for name in imported)
