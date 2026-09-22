"""G6c-2/G6c-3.1: the hidden rules' actual behavior, the private
world_id/world_revision -> rule binding (synthetic_runtime.py), the
public_observables checkpoint boundary, and SyntheticAExecutor's
compatibility contract (same shape as RealCausalAExecutor's, G6a.1).
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

from engine.deterministic.causal_executor import ExecutionResult
from engine.deterministic.research_world import WorldCompatibilityError
from engine.deterministic.synthetic_executor import SyntheticAExecutor
from engine.deterministic.synthetic_kernel import RULE_S01, RULE_S02, RULE_S03, run_synthetic_world
from engine.deterministic.synthetic_runtime import resolve_rule
from engine.deterministic.synthetic_spec import SyntheticClamp, SyntheticWorldSpec

ROOT = Path(__file__).resolve().parents[1]


def _spec(world_id: str, world_revision: str, variables: tuple[str, ...], initial: dict[str, bool],
         controls: tuple[str, ...], observables: tuple[str, ...], ticks: int,
         clamps: tuple[SyntheticClamp, ...] = ()) -> SyntheticWorldSpec:
    return SyntheticWorldSpec(
        world_id=world_id, world_revision=world_revision, variables=variables,
        initial_values=tuple(sorted(initial.items())), clamps=clamps,
        public_controls=controls, public_observables=observables, ticks=ticks,
    )


def _s01(**overrides) -> SyntheticWorldSpec:
    defaults = dict(world_id="WORLD-S01", world_revision="R-7F93C2", variables=("x1", "x3"),
                    initial={"x1": False, "x3": False}, controls=("x1",), observables=("x1", "x3"), ticks=1)
    defaults.update(overrides)
    return _spec(**defaults)


def _s02(**overrides) -> SyntheticWorldSpec:
    defaults = dict(world_id="WORLD-S02", world_revision="R-A18D40", variables=("x1", "x2", "x3"),
                    initial={"x1": False, "x2": False, "x3": False},
                    controls=("x1", "x2"), observables=("x1", "x2", "x3"), ticks=1)
    defaults.update(overrides)
    return _spec(**defaults)


def _s03(**overrides) -> SyntheticWorldSpec:
    defaults = dict(world_id="WORLD-S03", world_revision="R-51E8B7", variables=("x1", "x2", "x3"),
                    initial={"x1": False, "x2": False, "x3": False},
                    controls=("x1", "x2"), observables=("x1", "x2", "x3"), ticks=2)
    defaults.update(overrides)
    return _spec(**defaults)


# ---------------------------------------------------------------------------
# RULE_S01: x3 := x1 (exhaustive over the 2 cases)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("x1", [False, True])
def test_rule_s01_truth_table(x1: bool) -> None:
    spec = _s01(initial={"x1": x1, "x3": False})
    run = run_synthetic_world(spec, RULE_S01)
    assert run.checkpoint_at(1).value_of("x3") is x1


# ---------------------------------------------------------------------------
# RULE_S02: x3 := x1 AND x2 (exhaustive over the 4 cases)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("x1,x2,expected", [
    (False, False, False), (True, False, False), (False, True, False), (True, True, True),
])
def test_rule_s02_truth_table(x1: bool, x2: bool, expected: bool) -> None:
    spec = _s02(initial={"x1": x1, "x2": x2, "x3": False})
    run = run_synthetic_world(spec, RULE_S02)
    assert run.checkpoint_at(1).value_of("x3") is expected


# ---------------------------------------------------------------------------
# RULE_S03: ordinary x2 := x1, x3 := x2; and clamp-based intervention on x2.
# ---------------------------------------------------------------------------

def test_rule_s03_signal_propagates_over_two_ticks_when_unclamped() -> None:
    spec = _s03(initial={"x1": True, "x2": False, "x3": False})
    run = run_synthetic_world(spec, RULE_S03)
    assert run.checkpoint_at(0).value_of("x2") is False
    assert run.checkpoint_at(1).value_of("x2") is True   # x2 caught up to x1
    assert run.checkpoint_at(1).value_of("x3") is False  # x3 has not caught up yet
    assert run.checkpoint_at(2).value_of("x3") is True   # x3 now reflects x2


def test_rule_s03_clamping_x2_off_blocks_x1_effect_on_x3() -> None:
    """The mediator-defining check: pin x2, vary x1, x3 must not move."""
    clamp = (SyntheticClamp("x2", "OFF"),)
    spec_x1_false = _s03(initial={"x1": False, "x2": False, "x3": False}, clamps=clamp)
    spec_x1_true = _s03(initial={"x1": True, "x2": False, "x3": False}, clamps=clamp)
    run_false = run_synthetic_world(spec_x1_false, RULE_S03)
    run_true = run_synthetic_world(spec_x1_true, RULE_S03)
    assert run_false.checkpoint_at(2).value_of("x3") == run_true.checkpoint_at(2).value_of("x3") is False


def test_rule_s03_clamping_x2_on_drives_x3_independent_of_x1() -> None:
    """The other half: forcing x2 on, with x1 off, still drives x3 -- proving
    x2 (not x1) is what x3 actually tracks."""
    clamp = (SyntheticClamp("x2", "ON"),)
    spec = _s03(initial={"x1": False, "x2": False, "x3": False}, clamps=clamp)
    run = run_synthetic_world(spec, RULE_S03)
    assert run.checkpoint_at(2).value_of("x3") is True


def test_rule_s03_clamp_is_reapplied_every_tick_not_just_the_first() -> None:
    """If the clamp only applied to tick 0, the hidden rule would overwrite
    x2 back to following x1 by tick 1 -- this world would then look
    identical to the unclamped case, and the mediator check above would be
    meaningless. Confirms the clamp actually persists."""
    clamp = (SyntheticClamp("x2", "OFF"),)
    spec = _s03(initial={"x1": True, "x2": False, "x3": False}, ticks=3, clamps=clamp)
    run = run_synthetic_world(spec, RULE_S03)
    for tick in range(4):
        assert run.checkpoint_at(tick).value_of("x2") is False


# ---------------------------------------------------------------------------
# G6c-3.1.A: public_observables boundary survives execution, not just tick 0.
# ---------------------------------------------------------------------------

def test_checkpoints_never_carry_a_non_public_variable() -> None:
    """x2 is a real variable RULE_S03 computes every tick, but this spec
    never declares it a public observable -- no checkpoint may expose it,
    even though initial_observation would already have hidden it at tick 0.
    This is the exact gap G6c-3 left open: a private variable was reachable
    at any later tick just by naming it in an ObservablePrediction."""
    spec = _s03(observables=("x1", "x3"))  # x2 deliberately NOT public
    run = run_synthetic_world(spec, RULE_S03)
    for checkpoint in run.checkpoints:
        assert checkpoint.value_of("x2") is None
        assert set(name for name, _ in checkpoint.values) <= {"x1", "x3"}


def test_checkpoints_carry_every_public_observable() -> None:
    spec = _s03(observables=("x1", "x2", "x3"))
    run = run_synthetic_world(spec, RULE_S03)
    for checkpoint in run.checkpoints:
        assert set(name for name, _ in checkpoint.values) == {"x1", "x2", "x3"}


# ---------------------------------------------------------------------------
# G6c-3.1.B/C: synthetic_runtime.py -- the private world_id/world_revision -> rule binding.
# ---------------------------------------------------------------------------

def test_resolve_rule_finds_each_bound_world() -> None:
    assert resolve_rule("WORLD-S01", "R-7F93C2") is RULE_S01
    assert resolve_rule("WORLD-S02", "R-A18D40") is RULE_S02
    assert resolve_rule("WORLD-S03", "R-51E8B7") is RULE_S03


def test_resolve_rule_rejects_an_unbound_world_id() -> None:
    with pytest.raises(WorldCompatibilityError, match="WORLD-DOES-NOT-EXIST"):
        resolve_rule("WORLD-DOES-NOT-EXIST", "R-7F93C2")


def test_resolve_rule_rejects_a_known_world_with_the_wrong_revision() -> None:
    """A revision mismatch must fail exactly like an unknown world_id --
    the reproducibility guarantee this field exists for (synthetic_spec.py's
    docstring) is meaningless if a stale/wrong revision is accepted anyway."""
    with pytest.raises(WorldCompatibilityError, match="WORLD-S01"):
        resolve_rule("WORLD-S01", "R-WRONG-REVISION")


# ---------------------------------------------------------------------------
# G6c-3.2: sealed rule fingerprints -- world_revision alone is a promise kept
# by discipline; _SEALED_FINGERPRINTS makes an undisclosed rule-behavior
# change (without minting a new revision) fail at import time instead.
# ---------------------------------------------------------------------------

def test_synthetic_runtime_imports_cleanly_meaning_current_rules_match_their_sealed_fingerprints() -> None:
    """_verify_sealed_fingerprints() runs at import time (synthetic_runtime.py
    module level) -- successfully importing the module already proves every
    bound rule's current source matches what was sealed for its revision.
    Making that assertion explicit here (rather than relying on collection
    not exploding) documents what the import's success actually means."""
    import engine.deterministic.synthetic_runtime as runtime_module
    for key, binding in runtime_module._BINDINGS.items():
        assert runtime_module._fingerprint(binding.rule) == runtime_module._SEALED_FINGERPRINTS[key]


def test_verify_bindings_catches_a_silent_rule_behavior_change() -> None:
    """Calls the real production verifier, verify_bindings, directly --
    not a re-implementation of its comparison logic. Re-deriving the
    mismatch check here (as an earlier draft of this test did) would let a
    real regression in verify_bindings itself (e.g. someone reducing it to
    a no-op) pass unnoticed, since the test would keep asserting against
    its own separate copy of the logic rather than the function actually
    guarding import time."""
    import engine.deterministic.synthetic_runtime as runtime_module

    def _mutated_rule_s01(values):
        return {"x1": values["x1"], "x3": not values["x1"]}  # behavior silently changed

    tampered_bindings = {
        ("WORLD-S01", "R-7F93C2"): runtime_module.SyntheticWorldBinding(
            "WORLD-S01", "R-7F93C2", _mutated_rule_s01),
    }
    with pytest.raises(WorldCompatibilityError, match="WORLD-S01"):
        runtime_module.verify_bindings(tampered_bindings, runtime_module._SEALED_FINGERPRINTS)


def test_verify_bindings_accepts_matching_bindings() -> None:
    """The positive case, also against the real function: today's actual
    _BINDINGS/_SEALED_FINGERPRINTS must not raise -- redundant with the
    module having imported successfully, but explicit here as the direct
    counterpart to the tampered case above."""
    import engine.deterministic.synthetic_runtime as runtime_module
    runtime_module.verify_bindings(runtime_module._BINDINGS, runtime_module._SEALED_FINGERPRINTS)


def test_fingerprint_hashes_source_text_not_a_truth_table() -> None:
    """The fingerprint must be meaningless without the source itself -- if it
    were instead a hash of the rule's full input/output truth table, B could
    brute-force every possible boolean function of the same arity and match
    it against a leaked hash, defeating blindness. Confirmed here by showing
    two rules with the SAME truth table (x3 := x1, computed two different
    ways) get DIFFERENT fingerprints, because their source text differs."""
    import engine.deterministic.synthetic_runtime as runtime_module

    def rule_a(values):
        return {"x1": values["x1"], "x3": values["x1"]}

    def rule_b(values):
        x1 = values["x1"]
        return {"x1": x1, "x3": x1}

    # Same truth table (x3 always equals x1), deliberately different source.
    for case in (False, True):
        assert rule_a({"x1": case})["x3"] == rule_b({"x1": case})["x3"]
    assert runtime_module._fingerprint(rule_a) != runtime_module._fingerprint(rule_b)


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
    spec = _s01(initial={"x1": True, "x3": False})
    result = SyntheticAExecutor().execute(spec)
    assert isinstance(result, ExecutionResult)
    assert result.status == "success"
    assert result.run.checkpoint_at(1).value_of("x3") is True


def test_executor_raises_world_compatibility_error_for_an_unbound_world_not_a_failed_result() -> None:
    """G6c-3.1.C: an unbound (world_id, world_revision) is a configuration
    mistake -- resolve_rule is called before SyntheticAExecutor's own
    try/except, so this must raise directly, never come back as
    ExecutionResult(status="failed")."""
    spec = _s01(world_id="WORLD-NEVER-BOUND", world_revision="R-NOPE")
    with pytest.raises(WorldCompatibilityError):
        SyntheticAExecutor().execute(spec)


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


@pytest.mark.parametrize("filename", ["synthetic_kernel.py", "synthetic_executor.py", "synthetic_runtime.py"])
def test_synthetic_module_does_not_import_ground_truth(filename: str) -> None:
    path = ROOT / "engine" / "deterministic" / filename
    imported = _imported_module_names(path.read_text(encoding="utf-8"))
    assert not any(name == "ground_truth" or name.startswith("ground_truth.") for name in imported)
