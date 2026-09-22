"""G7.0: Oracle Expressibility -- before B is ever tested blind, confirm the
current hypothesis language and GroundTruthSignature can (a) express the
correct causal structure for S01/S02/S03 and pass it, and (b) reject
representative wrong structures, including both under-models (missing a
real effect) and over-models (claiming an effect that does not exist).

Every fixture below is a real, production `CausalHypothesis` holding only
`InterventionalPrediction` (`interventional_prediction.py`) -- the same
prediction kind any live B research session would construct. An earlier
draft used an evaluator-only `ConditionedPrediction` wrapper defined inside
`ground_truth_signature.py` itself, which proved "an evaluator-only type
can express GT-2/3/M1," not "B's own hypothesis language can" -- see
`interventional_prediction.py`'s docstring for the representation-repair
history.

No blind session, no alias, no ExperimentDesigner, and no execution against
a SyntheticWorldSpec appears anywhere in this file -- this Gate only asks
whether the scoring harness itself is valid. If any of these tests fails,
the verdict is HARNESS_INVALID territory (the evaluator or the hypothesis
language needs fixing), never INFERENCE_FAILURE -- B has not been run yet.
"""
from __future__ import annotations

from engine.deterministic.causal_hypothesis import CausalHypothesis, CausalHypothesisSet
from engine.deterministic.ground_truth_signature import ground_truth_signature_for
from engine.deterministic.interventional_prediction import InterventionalPrediction
from engine.deterministic.research_observable_prediction import ObservablePrediction


def _hypothesis(hypothesis_id: str, predictions: tuple[InterventionalPrediction, ...]) -> CausalHypothesis:
    """Builds a real, production `CausalHypothesis` -- `predictions` holds
    only `InterventionalPrediction`, the same kind any live B research
    session would hold, never an evaluator-only wrapper."""
    return CausalHypothesis(
        hypothesis_id=hypothesis_id, statement=f"hand-authored theory {hypothesis_id}",
        applicability_conditions=("oracle-test",), predictions=predictions,
        evidence=(), status="untested",
    )


def _set(*hypotheses: CausalHypothesis) -> CausalHypothesisSet:
    return CausalHypothesisSet(subject_digest="oracle-subject", hypotheses=hypotheses)


def _all_pass(hypothesis_set: CausalHypothesisSet, real_world_id: str) -> bool:
    signature = ground_truth_signature_for(real_world_id)
    return all(signature.evaluate(hypothesis_set).values())


# ---------------------------------------------------------------------------
# S01 / GT-2: direct effect, no mediator.
# ---------------------------------------------------------------------------

def test_s01_correct_direct_theory_passes() -> None:
    correct = _hypothesis("H-direct", (
        InterventionalPrediction((("x1", False),), ObservablePrediction(1, "x3", False)),
        InterventionalPrediction((("x1", True),), ObservablePrediction(1, "x3", True)),
    ))
    assert _all_pass(_set(correct), "GT-2")


def test_s01_constant_theory_fails() -> None:
    """Representative wrong answer: x3 never changes regardless of x1 --
    no effect claimed at all."""
    wrong = _hypothesis("H-constant", (
        InterventionalPrediction((("x1", False),), ObservablePrediction(1, "x3", False)),
        InterventionalPrediction((("x1", True),), ObservablePrediction(1, "x3", False)),
    ))
    assert not _all_pass(_set(wrong), "GT-2")


# ---------------------------------------------------------------------------
# S02 / GT-3: x2 gates x1's effect on x3; x1 never changes x2.
# ---------------------------------------------------------------------------

def _s02_correct() -> CausalHypothesis:
    return _hypothesis("H-gated", (
        InterventionalPrediction((("x1", False), ("x2", False)), ObservablePrediction(1, "x3", False)),
        InterventionalPrediction((("x1", True), ("x2", False)), ObservablePrediction(1, "x3", False)),
        InterventionalPrediction((("x1", False), ("x2", True)), ObservablePrediction(1, "x3", False)),
        InterventionalPrediction((("x1", True), ("x2", True)), ObservablePrediction(1, "x3", True)),
        # x1 never moves x2, at either level of x2 held fixed by its own clamp.
        InterventionalPrediction((("x1", False), ("x2", False)), ObservablePrediction(1, "x2", False)),
        InterventionalPrediction((("x1", True), ("x2", False)), ObservablePrediction(1, "x2", False)),
    ))


def test_s02_correct_conditional_theory_passes() -> None:
    assert _all_pass(_set(_s02_correct()), "GT-3")


def test_s02_unconditional_direct_only_theory_fails() -> None:
    """Under-model: claims x1 always determines x3, ignoring x2 entirely --
    the representative wrong answer the design doc names explicitly."""
    wrong = _hypothesis("H-always", (
        InterventionalPrediction((("x1", False), ("x2", False)), ObservablePrediction(1, "x3", False)),
        InterventionalPrediction((("x1", True), ("x2", False)), ObservablePrediction(1, "x3", True)),
        InterventionalPrediction((("x1", False), ("x2", True)), ObservablePrediction(1, "x3", False)),
        InterventionalPrediction((("x1", True), ("x2", True)), ObservablePrediction(1, "x3", True)),
    ))
    assert not _all_pass(_set(wrong), "GT-3")


def test_s02_false_x1_to_x2_edge_theory_fails() -> None:
    """Over-model: correctly predicts x3, but also (wrongly) claims x1
    moves x2 -- an extra edge that does not exist. Confirms the evaluator
    catches an over-model, not only an under-model."""
    wrong = _hypothesis("H-gated-plus-false-edge", (
        InterventionalPrediction((("x1", False), ("x2", False)), ObservablePrediction(1, "x3", False)),
        InterventionalPrediction((("x1", True), ("x2", False)), ObservablePrediction(1, "x3", False)),
        InterventionalPrediction((("x1", False), ("x2", True)), ObservablePrediction(1, "x3", False)),
        InterventionalPrediction((("x1", True), ("x2", True)), ObservablePrediction(1, "x3", True)),
        # Falsely claims x1 flips x2.
        InterventionalPrediction((("x1", False), ("x2", False)), ObservablePrediction(1, "x2", False)),
        InterventionalPrediction((("x1", True), ("x2", False)), ObservablePrediction(1, "x2", True)),
    ))
    assert not _all_pass(_set(wrong), "GT-3")


# ---------------------------------------------------------------------------
# S03 / GT-M1: x1 -> x2 -> x3, x2 independently controllable, no direct x1->x3.
# ---------------------------------------------------------------------------

def _s03_correct() -> CausalHypothesis:
    return _hypothesis("H-mediator", (
        # x1 alone (x2 unclamped, tick 1) determines x2.
        InterventionalPrediction((("x1", False),), ObservablePrediction(1, "x2", False)),
        InterventionalPrediction((("x1", True),), ObservablePrediction(1, "x2", True)),
        # x2 alone (clamped, x1 fixed True) determines x3 at tick 2.
        InterventionalPrediction((("x1", True), ("x2", False)), ObservablePrediction(2, "x3", False)),
        InterventionalPrediction((("x1", True), ("x2", True)), ObservablePrediction(2, "x3", True)),
        # Pinning x2 at either value severs x1's effect on x3.
        InterventionalPrediction((("x1", False), ("x2", False)), ObservablePrediction(2, "x3", False)),
        InterventionalPrediction((("x1", False), ("x2", True)), ObservablePrediction(2, "x3", True)),
    ))


def test_s03_correct_mediator_theory_passes() -> None:
    assert _all_pass(_set(_s03_correct()), "GT-M1")


def test_s03_missing_mediator_theory_fails() -> None:
    """Under-model: claims x2 has no effect on x3 at all (x3 pinned to a
    stray depends-only-on-x1-directly reading) -- misses the mediator
    entirely."""
    wrong = _hypothesis("H-no-mediator-effect", (
        InterventionalPrediction((("x1", False),), ObservablePrediction(1, "x2", False)),
        InterventionalPrediction((("x1", True),), ObservablePrediction(1, "x2", True)),
        # x2 claimed to have NO effect on x3 -- both same value.
        InterventionalPrediction((("x1", True), ("x2", False)), ObservablePrediction(2, "x3", False)),
        InterventionalPrediction((("x1", True), ("x2", True)), ObservablePrediction(2, "x3", False)),
        InterventionalPrediction((("x1", False), ("x2", False)), ObservablePrediction(2, "x3", False)),
        InterventionalPrediction((("x1", False), ("x2", True)), ObservablePrediction(2, "x3", False)),
    ))
    assert not _all_pass(_set(wrong), "GT-M1")


def test_s03_false_direct_edge_theory_fails() -> None:
    """Over-model: correctly predicts x1->x2 and x2->x3, but ALSO claims a
    direct x1->x3 edge survives even with x2 pinned -- pinning x2 does not
    sever x1's apparent effect on x3 in this (wrong) theory."""
    wrong = _hypothesis("H-mediator-plus-false-direct-edge", (
        InterventionalPrediction((("x1", False),), ObservablePrediction(1, "x2", False)),
        InterventionalPrediction((("x1", True),), ObservablePrediction(1, "x2", True)),
        InterventionalPrediction((("x1", True), ("x2", False)), ObservablePrediction(2, "x3", False)),
        InterventionalPrediction((("x1", True), ("x2", True)), ObservablePrediction(2, "x3", True)),
        # Falsely claims x1 still moves x3 even with x2 pinned at False.
        InterventionalPrediction((("x1", False), ("x2", False)), ObservablePrediction(2, "x3", True)),
        InterventionalPrediction((("x1", False), ("x2", True)), ObservablePrediction(2, "x3", True)),
    ))
    assert not _all_pass(_set(wrong), "GT-M1")


# ---------------------------------------------------------------------------
# Per-obligation isolation: a representative wrong answer that violates
# ALL relevant obligations at once (as above) cannot tell a caller whether
# each individual obligation is actually load-bearing, or whether a broken
# obligation (e.g. one hardcoded to always return True) would be masked by
# another, still-correct obligation also failing. Each test below breaks
# exactly one obligation and confirms `signature.evaluate()` reports that
# one obligation_id as False while every other obligation for the same
# world still reports True.
# ---------------------------------------------------------------------------

def test_gt3_gate_off_obligation_is_individually_load_bearing() -> None:
    """Correct everywhere except: x3 changes with x1 even when x2=OFF --
    violates gate_off_blocks_effect only."""
    wrong = _hypothesis("H-gate-off-broken", (
        InterventionalPrediction((("x1", False), ("x2", False)), ObservablePrediction(1, "x3", False)),
        InterventionalPrediction((("x1", True), ("x2", False)), ObservablePrediction(1, "x3", True)),   # broken
        InterventionalPrediction((("x1", False), ("x2", True)), ObservablePrediction(1, "x3", False)),
        InterventionalPrediction((("x1", True), ("x2", True)), ObservablePrediction(1, "x3", True)),
        InterventionalPrediction((("x1", False), ("x2", False)), ObservablePrediction(1, "x2", False)),
        InterventionalPrediction((("x1", True), ("x2", False)), ObservablePrediction(1, "x2", False)),
    ))
    results = ground_truth_signature_for("GT-3").evaluate(_set(wrong))
    assert results["gt3.gate_off_blocks_effect"] is False
    assert results["gt3.gate_on_lets_effect_through"] is True
    assert results["gt3.x1_never_changes_x2"] is True


def test_gt3_gate_on_obligation_is_individually_load_bearing() -> None:
    """Correct everywhere except: x3 does not change with x1 when x2=ON --
    violates gate_on_lets_effect_through only."""
    wrong = _hypothesis("H-gate-on-broken", (
        InterventionalPrediction((("x1", False), ("x2", False)), ObservablePrediction(1, "x3", False)),
        InterventionalPrediction((("x1", True), ("x2", False)), ObservablePrediction(1, "x3", False)),
        InterventionalPrediction((("x1", False), ("x2", True)), ObservablePrediction(1, "x3", False)),
        InterventionalPrediction((("x1", True), ("x2", True)), ObservablePrediction(1, "x3", False)),   # broken
        InterventionalPrediction((("x1", False), ("x2", False)), ObservablePrediction(1, "x2", False)),
        InterventionalPrediction((("x1", True), ("x2", False)), ObservablePrediction(1, "x2", False)),
    ))
    results = ground_truth_signature_for("GT-3").evaluate(_set(wrong))
    assert results["gt3.gate_off_blocks_effect"] is True
    assert results["gt3.gate_on_lets_effect_through"] is False
    assert results["gt3.x1_never_changes_x2"] is True


def test_gt3_x1_never_changes_x2_obligation_is_individually_load_bearing() -> None:
    """Correct everywhere except: x1 is claimed to flip x2 -- violates
    x1_never_changes_x2 only."""
    wrong = _hypothesis("H-false-x1-to-x2-only", _s02_correct().predictions[:4] + (
        InterventionalPrediction((("x1", False), ("x2", False)), ObservablePrediction(1, "x2", False)),
        InterventionalPrediction((("x1", True), ("x2", False)), ObservablePrediction(1, "x2", True)),   # broken
    ))
    results = ground_truth_signature_for("GT-3").evaluate(_set(wrong))
    assert results["gt3.gate_off_blocks_effect"] is True
    assert results["gt3.gate_on_lets_effect_through"] is True
    assert results["gt3.x1_never_changes_x2"] is False


def test_gt_m1_x1_alone_changes_x2_obligation_is_individually_load_bearing() -> None:
    correct = _s03_correct().predictions
    wrong = _hypothesis("H-broken-x1-to-x2", (
        InterventionalPrediction((("x1", False),), ObservablePrediction(1, "x2", False)),
        InterventionalPrediction((("x1", True),), ObservablePrediction(1, "x2", False)),   # broken: no longer differs
        *correct[2:],
    ))
    results = ground_truth_signature_for("GT-M1").evaluate(_set(wrong))
    assert results["gtm1.x1_alone_changes_x2"] is False
    assert results["gtm1.x2_alone_changes_x3"] is True
    assert results["gtm1.pinning_x2_severs_x1_effect_on_x3"] is True


def test_gt_m1_x2_alone_changes_x3_obligation_is_individually_load_bearing() -> None:
    """Correct everywhere except: x3 is False regardless of x2 (with x1
    pinned True or False) -- violates x2_alone_changes_x3 only. Both
    x2=True readings are set to the same (wrong) value so the pinning
    obligation -- which compares across x1, not across x2 -- still holds:
    pin=False gives x3=False both ways, pin=True gives x3=False both ways."""
    wrong = _hypothesis("H-broken-x2-to-x3", (
        InterventionalPrediction((("x1", False),), ObservablePrediction(1, "x2", False)),
        InterventionalPrediction((("x1", True),), ObservablePrediction(1, "x2", True)),
        InterventionalPrediction((("x1", True), ("x2", False)), ObservablePrediction(2, "x3", False)),
        InterventionalPrediction((("x1", True), ("x2", True)), ObservablePrediction(2, "x3", False)),   # broken
        InterventionalPrediction((("x1", False), ("x2", False)), ObservablePrediction(2, "x3", False)),
        InterventionalPrediction((("x1", False), ("x2", True)), ObservablePrediction(2, "x3", False)),   # kept consistent with the break above
    ))
    results = ground_truth_signature_for("GT-M1").evaluate(_set(wrong))
    assert results["gtm1.x1_alone_changes_x2"] is True
    assert results["gtm1.x2_alone_changes_x3"] is False
    assert results["gtm1.pinning_x2_severs_x1_effect_on_x3"] is True


def test_gt_m1_pinning_severs_effect_obligation_is_individually_load_bearing() -> None:
    """Correct everywhere except: with x2 pinned True, x1 still flips x3
    (True -> False here, vs x3=True at x1=True,x2=True) -- violates
    pinning_x2_severs_x1_effect_on_x3 only; x1_alone_changes_x2 and
    x2_alone_changes_x3 read disjoint (x1,x2) pairs and are untouched."""
    correct = _s03_correct().predictions
    wrong = _hypothesis("H-broken-pin", (
        *correct[:4],
        InterventionalPrediction((("x1", False), ("x2", False)), ObservablePrediction(2, "x3", False)),
        InterventionalPrediction((("x1", False), ("x2", True)), ObservablePrediction(2, "x3", False)),   # broken
    ))
    results = ground_truth_signature_for("GT-M1").evaluate(_set(wrong))
    assert results["gtm1.x1_alone_changes_x2"] is True
    assert results["gtm1.x2_alone_changes_x3"] is True
    assert results["gtm1.pinning_x2_severs_x1_effect_on_x3"] is False


# ---------------------------------------------------------------------------
# Unresolved case: a hypothesis set with no coverage of an obligation's
# required control-value combinations must not be scored as PASS by
# default -- an obligation can only pass on an affirmative structural match,
# never on missing data.
# ---------------------------------------------------------------------------

def test_missing_coverage_never_defaults_to_pass() -> None:
    sparse = _hypothesis("H-incomplete", (
        InterventionalPrediction((("x1", False),), ObservablePrediction(1, "x3", False)),
    ))
    assert not _all_pass(_set(sparse), "GT-2")


# ---------------------------------------------------------------------------
# G6c-4 <-> G7.0 obligation parity: the same three intervention properties
# G6c-4 already verified against the executed SyntheticWorldSpec must be
# exactly what G7.0's obligations check -- confirmed here by obligation_id
# count/shape, not by re-running the executor (G7.0 never executes A).
# ---------------------------------------------------------------------------

def test_gt2_signature_has_exactly_the_g6c4_direct_property() -> None:
    signature = ground_truth_signature_for("GT-2")
    assert {o.obligation_id for o in signature.structural_obligations} == {"gt2.x1_change_moves_x3"}


def test_gt3_signature_has_exactly_the_g6c4_conditional_properties() -> None:
    signature = ground_truth_signature_for("GT-3")
    assert {o.obligation_id for o in signature.structural_obligations} == {
        "gt3.gate_off_blocks_effect", "gt3.gate_on_lets_effect_through", "gt3.x1_never_changes_x2",
    }


def test_gt_m1_signature_has_exactly_the_g6c4_mediator_properties() -> None:
    signature = ground_truth_signature_for("GT-M1")
    assert {o.obligation_id for o in signature.structural_obligations} == {
        "gtm1.x1_alone_changes_x2", "gtm1.x2_alone_changes_x3", "gtm1.pinning_x2_severs_x1_effect_on_x3",
    }
