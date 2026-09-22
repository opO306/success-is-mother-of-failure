"""G6c-2: the hidden rules' actual behavior, and SyntheticAExecutor's
compatibility contract (same shape as RealCausalAExecutor's, G6a.1).
"""
from __future__ import annotations

import ast
from pathlib import Path

from engine.deterministic.causal_executor import ExecutionResult
from engine.deterministic.research_world import WorldCompatibilityError
from engine.deterministic.synthetic_executor import SyntheticAExecutor
from engine.deterministic.synthetic_kernel import run_synthetic_world
from engine.deterministic.synthetic_spec import SyntheticClamp, SyntheticWorldSpec

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _spec(rule_id: str, variables: tuple[str, ...], initial: dict[str, bool],
         controls: tuple[str, ...], observables: tuple[str, ...], ticks: int,
         clamps: tuple[SyntheticClamp, ...] = ()) -> SyntheticWorldSpec:
    return SyntheticWorldSpec(
        world_id=f"WORLD-{rule_id}", rule_id=rule_id, variables=variables,
        initial_values=tuple(sorted(initial.items())), clamps=clamps,
        public_controls=controls, public_observables=observables, ticks=ticks,
    )


# ---------------------------------------------------------------------------
# RULE-S01: x3 := x1 (exhaustive over the 2 cases)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("x1", [False, True])
def test_rule_s01_truth_table(x1: bool) -> None:
    spec = _spec("RULE-S01", ("x1", "x3"), {"x1": x1, "x3": False}, ("x1",), ("x1", "x3"), 1)
    run = run_synthetic_world(spec)
    assert run.checkpoint_at(1).value_of("x3") is x1


# ---------------------------------------------------------------------------
# RULE-S02: x3 := x1 AND x2 (exhaustive over the 4 cases)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("x1,x2,expected", [
    (False, False, False), (True, False, False), (False, True, False), (True, True, True),
])
def test_rule_s02_truth_table(x1: bool, x2: bool, expected: bool) -> None:
    spec = _spec("RULE-S02", ("x1", "x2", "x3"), {"x1": x1, "x2": x2, "x3": False},
                 ("x1", "x2"), ("x1", "x2", "x3"), 1)
    run = run_synthetic_world(spec)
    assert run.checkpoint_at(1).value_of("x3") is expected


# ---------------------------------------------------------------------------
# RULE-S03: ordinary x2 := x1, x3 := x2; and clamp-based intervention on x2.
# ---------------------------------------------------------------------------

def test_rule_s03_signal_propagates_over_two_ticks_when_unclamped() -> None:
    spec = _spec("RULE-S03", ("x1", "x2", "x3"), {"x1": True, "x2": False, "x3": False},
                 ("x1", "x2"), ("x1", "x2", "x3"), 2)
    run = run_synthetic_world(spec)
    assert run.checkpoint_at(0).value_of("x2") is False
    assert run.checkpoint_at(1).value_of("x2") is True   # x2 caught up to x1
    assert run.checkpoint_at(1).value_of("x3") is False  # x3 has not caught up yet
    assert run.checkpoint_at(2).value_of("x3") is True   # x3 now reflects x2


def test_rule_s03_clamping_x2_off_blocks_x1_effect_on_x3() -> None:
    """The mediator-defining check: pin x2, vary x1, x3 must not move."""
    clamp = (SyntheticClamp("x2", "OFF"),)
    spec_x1_false = _spec("RULE-S03", ("x1", "x2", "x3"), {"x1": False, "x2": False, "x3": False},
                          ("x1", "x2"), ("x1", "x2", "x3"), 2, clamp)
    spec_x1_true = _spec("RULE-S03", ("x1", "x2", "x3"), {"x1": True, "x2": False, "x3": False},
                         ("x1", "x2"), ("x1", "x2", "x3"), 2, clamp)
    run_false = run_synthetic_world(spec_x1_false)
    run_true = run_synthetic_world(spec_x1_true)
    assert run_false.checkpoint_at(2).value_of("x3") == run_true.checkpoint_at(2).value_of("x3") is False


def test_rule_s03_clamping_x2_on_drives_x3_independent_of_x1() -> None:
    """The other half: forcing x2 on, with x1 off, still drives x3 -- proving
    x2 (not x1) is what x3 actually tracks."""
    clamp = (SyntheticClamp("x2", "ON"),)
    spec = _spec("RULE-S03", ("x1", "x2", "x3"), {"x1": False, "x2": False, "x3": False},
                ("x1", "x2"), ("x1", "x2", "x3"), 2, clamp)
    run = run_synthetic_world(spec)
    assert run.checkpoint_at(2).value_of("x3") is True


def test_rule_s03_clamp_is_reapplied_every_tick_not_just_the_first() -> None:
    """If the clamp only applied to tick 0, the hidden rule would overwrite
    x2 back to following x1 by tick 1 -- this world would then look
    identical to the unclamped case, and the mediator check above would be
    meaningless. Confirms the clamp actually persists."""
    clamp = (SyntheticClamp("x2", "OFF"),)
    spec = _spec("RULE-S03", ("x1", "x2", "x3"), {"x1": True, "x2": False, "x3": False},
                ("x1", "x2"), ("x1", "x2", "x3"), 3, clamp)
    run = run_synthetic_world(spec)
    for tick in range(4):
        assert run.checkpoint_at(tick).value_of("x2") is False


# ---------------------------------------------------------------------------
# SyntheticAExecutor
# ---------------------------------------------------------------------------

def test_executor_rejects_a_non_synthetic_spec() -> None:
    class _FakeSpec:
        world_id = "fake"

        @property
        def digest(self) -> str:
            return "fake-digest"

        def canonical(self) -> dict[str, object]:
            return {}

    with pytest.raises(WorldCompatibilityError, match="SyntheticWorldSpec"):
        SyntheticAExecutor().execute(_FakeSpec())


def test_executor_succeeds_for_a_legal_spec() -> None:
    spec = _spec("RULE-S01", ("x1", "x3"), {"x1": True, "x3": False}, ("x1",), ("x1", "x3"), 1)
    result = SyntheticAExecutor().execute(spec)
    assert isinstance(result, ExecutionResult)
    assert result.status == "success"
    assert result.run.checkpoint_at(1).value_of("x3") is True


def test_executor_reports_an_unknown_rule_id_as_a_failed_execution_not_a_crash() -> None:
    """An unrecognized rule_id inside an otherwise-legal spec is A failing
    internally, not a spec/executor mismatch -- must become
    ExecutionResult(status="failed"), never raise."""
    spec = _spec("RULE-DOES-NOT-EXIST", ("x1",), {"x1": False}, ("x1",), ("x1",), 1)
    result = SyntheticAExecutor().execute(spec)
    assert result.status == "failed"
    assert result.error_kind == "WorldCompatibilityError"


# ---------------------------------------------------------------------------
# Independence from ground_truth/
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


@pytest.mark.parametrize("filename", ["synthetic_kernel.py", "synthetic_executor.py"])
def test_synthetic_module_does_not_import_ground_truth(filename: str) -> None:
    path = ROOT / "engine" / "deterministic" / filename
    imported = _imported_module_names(path.read_text(encoding="utf-8"))
    assert not any(name == "ground_truth" or name.startswith("ground_truth.") for name in imported)
