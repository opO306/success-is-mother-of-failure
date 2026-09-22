"""G6c-4: does WORLD-S01/S02/S03 actually have the causal structure the
answer key (`ground_truth/`) says it should?

This is the missing link between two things that, until now, were each
independently true but never checked against each other: `ground_truth/`
seals what direct/conditional/mediator structure GT-2/GT-3/GT-M1 *intend*,
and `synthetic_kernel.py` independently implements RULE_S01/S02/S03 as
"a world with that same structure, but B-researchable." Nothing before this
module ever confirmed the second thing actually has the structure the first
one names -- they could have silently diverged (a rule edited, a revision
not, or just a plain bug in one implementation) and every existing test
would still pass, because every existing test checks each side only
against itself.

What this deliberately does NOT do: compare tick values, tick counts, or
any other execution-shape detail. GT-M1 expresses A -> B -> C in one
`step()`; WORLD-S03 expresses it over two ticks (x2 follows x1 at tick 1,
x3 follows the now-clamped x2 at tick 2) because `run_synthetic_world` has
no single-tick "read the mediator after it updates" primitive the way a
hand-written step function does. Comparing tick-by-tick values would fail
for a reason that has nothing to do with whether the causal structure
matches. Instead, this compares only the three intervention-defined
properties each `ground_truth/` module already uses to characterize its
world:

    S01 <-> GT-2 (direct):      A change in x1 changes x3, with no third
                                 variable for a mediator to be.
    S02 <-> GT-3 (conditional): x2 gates whether x1 affects x3 (x1 moves x3
                                 only when x2 is on); x1 never changes x2.
    S03 <-> GT-M1 (mediator):   x1 alone (x2 free) changes x2; x2 alone
                                 (via clamp) changes x3; x1 varied while x2
                                 is clamped changes nothing in x3.

The mapping S01<->GT-2, S02<->GT-3, S03<->GT-M1 is fixed here, by this
test file, once -- not inferred from names. If this module ever fails,
the fault is in the benchmark world (WORLD-Sxx no longer has the structure
GT-2/3/M1 defines), not in any candidate B being graded against it: G7's
blind evaluation must not run until this passes.
"""
from __future__ import annotations

from dataclasses import replace

import pytest

from engine.deterministic.research_observable_prediction import ObservablePrediction
from engine.deterministic.synthetic_adapter import SyntheticControlDefinition, SyntheticResearchAdapter
from engine.deterministic.synthetic_executor import SyntheticAExecutor
from engine.deterministic.synthetic_spec import SyntheticWorldSpec

from ground_truth import audit_world2_direct, audit_world3_conditional, audit_world_m1_mediator

CTRL_X1 = SyntheticControlDefinition("CTRL-X1", "axis.synthetic.x1", "x1")
CTRL_X2 = SyntheticControlDefinition("CTRL-X2", "axis.synthetic.x2", "x2")

_ADAPTER = SyntheticResearchAdapter()
_EXECUTOR = SyntheticAExecutor()


def _x3_at_tick(spec: SyntheticWorldSpec, tick: int) -> bool:
    result = _EXECUTOR.execute(spec)
    assert result.status == "success", result.error_detail
    checkpoint = result.run.checkpoint_at(tick)
    assert checkpoint is not None
    value = checkpoint.value_of("x3")
    assert value is not None
    return value


def _clamp(spec: SyntheticWorldSpec, control: SyntheticControlDefinition, value: int | None) -> SyntheticWorldSpec:
    return _ADAPTER.apply_control(spec, control, value)


# ---------------------------------------------------------------------------
# WORLD-S01 <-> GT-2: direct, no mediator.
# ---------------------------------------------------------------------------

def _s01_spec(x1_initial: bool = False) -> SyntheticWorldSpec:
    return SyntheticWorldSpec(
        world_id="WORLD-S01", world_revision="R-7F93C2", variables=("x1", "x3"),
        initial_values=(("x1", x1_initial), ("x3", False)), clamps=(),
        public_controls=("x1",), public_observables=("x1", "x3"), ticks=1,
    )


def test_gt2_ground_truth_is_still_valid() -> None:
    """Guards against silently comparing WORLD-S01 to a broken answer key."""
    assert audit_world2_direct().verdict == "VALID"


def test_s01_x1_change_moves_x3_with_no_mediator_variable() -> None:
    x3_with_x1_off = _x3_at_tick(_clamp(_s01_spec(), CTRL_X1, 0), 1)
    x3_with_x1_on = _x3_at_tick(_clamp(_s01_spec(), CTRL_X1, 1), 1)
    assert x3_with_x1_off != x3_with_x1_on
    # "no mediator variable" is a structural fact about the spec itself,
    # not something a tick value could show: WORLD-S01 declares only x1/x3.
    assert _s01_spec().variables == ("x1", "x3")


# ---------------------------------------------------------------------------
# WORLD-S02 <-> GT-3: x2 gates x1's effect on x3; x1 never changes x2.
# ---------------------------------------------------------------------------

def _s02_spec() -> SyntheticWorldSpec:
    return SyntheticWorldSpec(
        world_id="WORLD-S02", world_revision="R-A18D40", variables=("x1", "x2", "x3"),
        initial_values=(("x1", False), ("x2", False), ("x3", False)), clamps=(),
        public_controls=("x1", "x2"), public_observables=("x1", "x2", "x3"), ticks=1,
    )


def test_gt3_ground_truth_is_still_valid() -> None:
    assert audit_world3_conditional().verdict == "VALID"


def test_s02_gate_off_blocks_x1_effect_on_x3() -> None:
    spec = _clamp(_s02_spec(), CTRL_X2, 0)
    x3_x1_off = _x3_at_tick(_clamp(spec, CTRL_X1, 0), 1)
    x3_x1_on = _x3_at_tick(_clamp(spec, CTRL_X1, 1), 1)
    assert x3_x1_off == x3_x1_on


def test_s02_gate_on_lets_x1_affect_x3() -> None:
    spec = _clamp(_s02_spec(), CTRL_X2, 1)
    x3_x1_off = _x3_at_tick(_clamp(spec, CTRL_X1, 0), 1)
    x3_x1_on = _x3_at_tick(_clamp(spec, CTRL_X1, 1), 1)
    assert x3_x1_off != x3_x1_on


def test_s02_x1_never_changes_x2() -> None:
    """x2 is a gate x1 passes around, not a mediator x1 passes through --
    this rules out A -> x2 -> x3 being mistaken for the intended
    A -[if x2]-> x3, the same distinction GT-3's own audit draws."""
    spec_x1_off = _s02_spec()
    spec_x1_on = replace(spec_x1_off, initial_values=(("x1", True), ("x2", False), ("x3", False)))

    def _x2_at_tick_1(spec: SyntheticWorldSpec) -> bool:
        result = _EXECUTOR.execute(spec)
        assert result.status == "success", result.error_detail
        return result.run.checkpoint_at(1).value_of("x2")

    assert _x2_at_tick_1(spec_x1_off) == _x2_at_tick_1(spec_x1_on)


# ---------------------------------------------------------------------------
# WORLD-S03 <-> GT-M1: x1 -> x2 -> x3, x2 independently controllable.
# ---------------------------------------------------------------------------

def _s03_spec(x1_initial: bool = False) -> SyntheticWorldSpec:
    return SyntheticWorldSpec(
        world_id="WORLD-S03", world_revision="R-51E8B7", variables=("x1", "x2", "x3"),
        initial_values=(("x1", x1_initial), ("x2", False), ("x3", False)), clamps=(),
        public_controls=("x1", "x2"), public_observables=("x1", "x2", "x3"), ticks=2,
    )


def test_gt_m1_ground_truth_is_still_valid() -> None:
    assert audit_world_m1_mediator().verdict == "VALID"


def test_s03_x1_alone_changes_x2_ordinary_evolution() -> None:
    """Intervention 1: with x2 left FREE, x1 drives x2 by tick 1 (mirrors
    GT-M1's ordinary-evolution check that mediator_active follows source_active)."""
    def _x2_at_tick_1(x1_initial: bool) -> bool:
        result = _EXECUTOR.execute(_s03_spec(x1_initial))
        assert result.status == "success", result.error_detail
        return result.run.checkpoint_at(1).value_of("x2")

    assert _x2_at_tick_1(False) != _x2_at_tick_1(True)


def test_s03_x2_alone_changes_x3_with_x1_held_fixed() -> None:
    """Intervention 2: pin x1 fixed, vary x2 via its own public control --
    x3 (tick 2) must move. Mirrors GT-M1's "B changes C, A held fixed"."""
    spec = _s03_spec(x1_initial=True)
    x3_x2_off = _x3_at_tick(_clamp(spec, CTRL_X2, 0), 2)
    x3_x2_on = _x3_at_tick(_clamp(spec, CTRL_X2, 1), 2)
    assert x3_x2_off != x3_x2_on


def test_s03_pinning_x2_severs_x1_effect_on_x3() -> None:
    """Intervention 3, the defining mediator check: with x2 pinned (either
    value), varying x1 must never move x3 -- mirrors GT-M1's
    "blocking B severs A's effect on C", the property forbidden_edges=
    (("source_active","outcome_active"),) exists to enforce there."""
    for pin_value in (0, 1):
        x3_x1_off = _x3_at_tick(_clamp(_s03_spec(False), CTRL_X2, pin_value), 2)
        x3_x1_on = _x3_at_tick(_clamp(_s03_spec(True), CTRL_X2, pin_value), 2)
        assert x3_x1_off == x3_x1_on, f"x1 leaked through to x3 with x2 pinned at {pin_value}"
