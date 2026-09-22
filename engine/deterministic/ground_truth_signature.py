"""G7.0: does B's own hypothesis language have room to express what
GT-2/GT-3/GT-M1 actually mean, before B is ever tested against them blind?

Nothing here executes a `SyntheticWorldSpec`, touches `ground_truth/`'s
`step()` functions, or knows any real `world_id`/`world_revision` --
S01/S02/S03's finite control spaces are small enough (2, 4, 4 combinations)
that a `GroundTruthSignature`'s `StructuralObligation`s can be checked
against a `CausalHypothesisSet`'s own claimed predictions alone, the same
exhaustive-enumeration discipline `ground_truth/world3_conditional.py` etc.
already use for their own self-audits (`_EXPECTED_TABLE`).

A `StructuralObligation.check` never reads a hypothesis's `hypothesis_id`,
`statement`, or any other label -- doing so would let a hypothesis pass by
being named "conditional" rather than by actually predicting the
conditional truth table. Every obligation here computes a real boolean
relationship from `ConditionedPrediction`s the hypothesis set itself
supplies (what it predicts an observable will be, under specific control
values) and compares that relationship structurally.

`ConditionedPrediction` exists because `CausalHypothesis.predictions` is a
static `tuple[CausalPrediction, ...]` with no method to compute a
prediction from arbitrary control values (see `causal_hypothesis.py`) --
for the small, enumerable worlds this Gate covers, a hypothesis instead
states its predictions for every control combination it wants to claim,
each tagged with the control values it holds under. This is expressive
enough for G7.0/G7.4's structural obligations without adding any new
inference machinery to `CausalHypothesis` itself.

This module does not run B, does not execute A, and does not construct a
`BlindWorldDescriptor`/alias/permutation of any kind -- see CURRENT_STATE.md
for why G7.0 is scoped to exactly this question and nothing past it.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping

from .causal_hypothesis import CausalHypothesisSet
from .research_observable_prediction import ObservablePrediction

FORMAT = "ground-truth-signature-v1"


def _text(value: object, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{context} must be non-empty text")
    return value


@dataclass(frozen=True, order=True)
class ConditionedPrediction:
    """What one hypothesis claims an observable will be, under specific
    control values -- the missing "under what intervention" context a bare
    `ObservablePrediction` does not carry on its own."""
    control_values: tuple[tuple[str, object], ...]
    prediction: ObservablePrediction

    def __post_init__(self) -> None:
        if not isinstance(self.control_values, tuple) or not self.control_values:
            raise ValueError("control_values must be a non-empty tuple")
        names = [name for name, _ in self.control_values]
        if len(set(names)) != len(names):
            raise ValueError("control_values must not name the same control twice")

    def canonical(self) -> dict[str, object]:
        return {"control_values": [list(pair) for pair in sorted(self.control_values)],
               "format": FORMAT, "prediction": self.prediction.canonical()}


def conditioned_predictions(hypothesis_set: CausalHypothesisSet) -> tuple[ConditionedPrediction, ...]:
    """Every `ConditionedPrediction` any hypothesis in the set carries in its
    `predictions` tuple -- entries of any other `CausalPrediction` kind
    (physical A's `StateDigestPrediction` etc.) are silently skipped, since
    this Gate never mixes physical and synthetic prediction vocabularies in
    one set."""
    result: list[ConditionedPrediction] = []
    for hypothesis in hypothesis_set.hypotheses:
        for item in hypothesis.predictions:
            if isinstance(item, ConditionedPrediction):
                result.append(item)
    return tuple(result)


def _predicted_value(predictions: tuple[ConditionedPrediction, ...], tick: int, observable_id: str,
                     control_values: tuple[tuple[str, object], ...]) -> bool | None:
    """The value the hypothesis set predicts for `observable_id` at `tick`
    under exactly `control_values` -- `None` if no `ConditionedPrediction`
    covers that exact combination (an unresolved case, never assumed False
    or True)."""
    wanted = tuple(sorted(control_values))
    for item in predictions:
        if (tuple(sorted(item.control_values)) == wanted and item.prediction.tick == tick
                and item.prediction.observable_id == observable_id):
            return item.prediction.expected_value
    return None


@dataclass(frozen=True)
class StructuralObligation:
    """One causal property a `CausalHypothesisSet` must structurally imply
    -- `check` computes a real boolean relationship from the set's own
    `ConditionedPrediction`s, never from a hypothesis's name or label."""
    obligation_id: str
    check: Callable[[CausalHypothesisSet], bool]

    def __post_init__(self) -> None:
        _text(self.obligation_id, "obligation_id")


@dataclass(frozen=True)
class GroundTruthSignature:
    """A GT world's intended causal structure, expressed as executable
    interventional properties -- evaluator-only. `real_world_id` is never
    passed to, or derived from, anything B-facing; see `synthetic_spec.py`'s
    threat model and G7's blind-boundary design (G7.1, not yet built)."""
    real_world_id: str
    structural_obligations: tuple[StructuralObligation, ...]

    def __post_init__(self) -> None:
        _text(self.real_world_id, "real_world_id")
        if not self.structural_obligations:
            raise ValueError("structural_obligations must be non-empty")
        ids = [item.obligation_id for item in self.structural_obligations]
        if len(set(ids)) != len(ids):
            raise ValueError("obligation_id values must be unique")

    def evaluate(self, hypothesis_set: CausalHypothesisSet) -> Mapping[str, bool]:
        return {item.obligation_id: item.check(hypothesis_set) for item in self.structural_obligations}


# ---------------------------------------------------------------------------
# GT-2 (WORLD-S01): direct effect, x1 -> x3, no mediator.
# ---------------------------------------------------------------------------

def _s01_x1_change_moves_x3(hypothesis_set: CausalHypothesisSet) -> bool:
    predictions = conditioned_predictions(hypothesis_set)
    x3_x1_off = _predicted_value(predictions, 1, "x3", (("x1", False),))
    x3_x1_on = _predicted_value(predictions, 1, "x3", (("x1", True),))
    if x3_x1_off is None or x3_x1_on is None:
        return False
    return x3_x1_off != x3_x1_on


def _gt2_signature() -> GroundTruthSignature:
    return GroundTruthSignature("GT-2", (
        StructuralObligation("gt2.x1_change_moves_x3", _s01_x1_change_moves_x3),
    ))


# ---------------------------------------------------------------------------
# GT-3 (WORLD-S02): x2 gates x1's effect on x3; x1 never changes x2.
# ---------------------------------------------------------------------------

def _s02_gate_off_blocks_effect(hypothesis_set: CausalHypothesisSet) -> bool:
    predictions = conditioned_predictions(hypothesis_set)
    x3_off = _predicted_value(predictions, 1, "x3", (("x1", False), ("x2", False)))
    x3_on = _predicted_value(predictions, 1, "x3", (("x1", True), ("x2", False)))
    if x3_off is None or x3_on is None:
        return False
    return x3_off == x3_on


def _s02_gate_on_lets_effect_through(hypothesis_set: CausalHypothesisSet) -> bool:
    predictions = conditioned_predictions(hypothesis_set)
    x3_off = _predicted_value(predictions, 1, "x3", (("x1", False), ("x2", True)))
    x3_on = _predicted_value(predictions, 1, "x3", (("x1", True), ("x2", True)))
    if x3_off is None or x3_on is None:
        return False
    return x3_off != x3_on


def _s02_x1_never_changes_x2(hypothesis_set: CausalHypothesisSet) -> bool:
    predictions = conditioned_predictions(hypothesis_set)
    x2_x1_off = _predicted_value(predictions, 1, "x2", (("x1", False), ("x2", False)))
    x2_x1_on = _predicted_value(predictions, 1, "x2", (("x1", True), ("x2", False)))
    if x2_x1_off is None or x2_x1_on is None:
        return False
    return x2_x1_off == x2_x1_on


def _gt3_signature() -> GroundTruthSignature:
    return GroundTruthSignature("GT-3", (
        StructuralObligation("gt3.gate_off_blocks_effect", _s02_gate_off_blocks_effect),
        StructuralObligation("gt3.gate_on_lets_effect_through", _s02_gate_on_lets_effect_through),
        StructuralObligation("gt3.x1_never_changes_x2", _s02_x1_never_changes_x2),
    ))


# ---------------------------------------------------------------------------
# GT-M1 (WORLD-S03): x1 -> x2 -> x3, x2 independently controllable.
# ---------------------------------------------------------------------------

def _s03_x1_alone_changes_x2(hypothesis_set: CausalHypothesisSet) -> bool:
    predictions = conditioned_predictions(hypothesis_set)
    x2_x1_off = _predicted_value(predictions, 1, "x2", (("x1", False),))
    x2_x1_on = _predicted_value(predictions, 1, "x2", (("x1", True),))
    if x2_x1_off is None or x2_x1_on is None:
        return False
    return x2_x1_off != x2_x1_on


def _s03_x2_alone_changes_x3(hypothesis_set: CausalHypothesisSet) -> bool:
    predictions = conditioned_predictions(hypothesis_set)
    x3_x2_off = _predicted_value(predictions, 2, "x3", (("x1", True), ("x2", False)))
    x3_x2_on = _predicted_value(predictions, 2, "x3", (("x1", True), ("x2", True)))
    if x3_x2_off is None or x3_x2_on is None:
        return False
    return x3_x2_off != x3_x2_on


def _s03_pinning_x2_severs_x1_effect_on_x3(hypothesis_set: CausalHypothesisSet) -> bool:
    predictions = conditioned_predictions(hypothesis_set)
    for pin_value in (False, True):
        x3_x1_off = _predicted_value(predictions, 2, "x3", (("x1", False), ("x2", pin_value)))
        x3_x1_on = _predicted_value(predictions, 2, "x3", (("x1", True), ("x2", pin_value)))
        if x3_x1_off is None or x3_x1_on is None:
            return False
        if x3_x1_off != x3_x1_on:
            return False
    return True


def _gt_m1_signature() -> GroundTruthSignature:
    return GroundTruthSignature("GT-M1", (
        StructuralObligation("gtm1.x1_alone_changes_x2", _s03_x1_alone_changes_x2),
        StructuralObligation("gtm1.x2_alone_changes_x3", _s03_x2_alone_changes_x3),
        StructuralObligation("gtm1.pinning_x2_severs_x1_effect_on_x3", _s03_pinning_x2_severs_x1_effect_on_x3),
    ))


_SIGNATURES: Mapping[str, GroundTruthSignature] = {
    "GT-2": _gt2_signature(),
    "GT-3": _gt3_signature(),
    "GT-M1": _gt_m1_signature(),
}


def ground_truth_signature_for(real_world_id: str) -> GroundTruthSignature:
    try:
        return _SIGNATURES[real_world_id]
    except KeyError:
        raise ValueError(f"no GroundTruthSignature is registered for {real_world_id!r}") from None
