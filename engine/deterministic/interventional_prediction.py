"""G7.0 representation repair: a prediction B can actually hold, conditioned
on the intervention it was made under.

Before this module existed, `CausalHypothesis.predictions` (`causal_hypothesis.py`)
was a static `tuple[CausalPrediction, ...]` with no way to say *which*
control values a given prediction applies to -- a hypothesis could claim
"x3 will be True" but not "x3 will be True *when x1=1, x2=0*" and a
different value under a different intervention. `ground_truth_signature.py`
first tried to close this gap with an evaluator-only `ConditionedPrediction`
wrapper, injected into `predictions` only because the tuple's element type
is not runtime-checked -- that made G7.0 prove "an evaluator-only type can
express GT-2/3/M1," not "B's own hypothesis language can." This module is
the real fix: `InterventionalPrediction` is a production prediction kind, a
sibling of `ObservablePrediction` in exactly the same sense (see that
module's own docstring on kind-dispatch, physical A's five kinds untouched),
constructible and held by any `CausalHypothesis` a real research session
produces -- not confined to test fixtures or evaluator code.

It carries no ground-truth information of any kind (no `real_world_id`, no
answer-revealing labels) -- it is exactly as anonymous as `ObservablePrediction`
itself, and it is intended to be reused unchanged by G7.5's held-out
intervention query: "what does your final theory predict under this
intervention" is answered by looking up an `InterventionalPrediction`,
not by inventing a second representation later.
"""
from __future__ import annotations

from dataclasses import dataclass

from .research_observable_prediction import ObservablePrediction

FORMAT = "interventional-prediction-v1"


@dataclass(frozen=True, order=True)
class InterventionalPrediction:
    """What a hypothesis predicts an observable will be, under a stated
    intervention -- `control_values` names the exact control-value
    combination this prediction holds under; a hypothesis that predicts
    differently under a different intervention holds a separate
    `InterventionalPrediction` for each one."""
    control_values: tuple[tuple[str, object], ...]
    prediction: ObservablePrediction

    def __post_init__(self) -> None:
        if not isinstance(self.control_values, tuple) or not self.control_values:
            raise ValueError("control_values must be a non-empty tuple")
        names = [name for name, _ in self.control_values]
        if len(set(names)) != len(names):
            raise ValueError("control_values must not name the same control twice")
        if not isinstance(self.prediction, ObservablePrediction):
            raise ValueError("prediction must be an ObservablePrediction")

    def canonical(self) -> dict[str, object]:
        return {"control_values": [list(pair) for pair in sorted(self.control_values)],
               "format": FORMAT, "kind": "interventional", "prediction": self.prediction.canonical()}
