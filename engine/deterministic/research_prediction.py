"""G3-G5: where a candidate's sealed predictions come from.

`broad_explorer.run_exploration` always used the *same* `predictions_for_hypothesis`
mapping for every candidate in a sweep -- fine for physical A, where B0.1/B0.2
hand-written experiments always tested one fixed hypothesis's predictions
against many control values. It stops being fine once a candidate's own
control values determine what the correct prediction even is (GT-2's
`x1=OFF -> y=OFF` vs `x1=ON -> y=ON` is two different predictions, not one
prediction checked at two points) -- that need is deferred past this
session's G3-G5 scope (see CURRENT_STATE.md), but the seam is added now so
`run_exploration`'s existing behavior can be expressed as the special case
"every candidate gets the same predictions" rather than hardcoded as the
only possible behavior.

Nothing here changes `CausalPrediction` itself -- `StaticPredictionProvider`
hands back exactly the same physical prediction objects
(`BondCountPrediction` etc.) callers already construct by hand. Generalizing
prediction *content* to a world-agnostic vocabulary is later work (G6+).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping, Protocol, runtime_checkable

from .exploration_space import ExplorationCandidate
from .research_world import ResearchWorldSpec


@runtime_checkable
class CandidatePredictionProvider(Protocol):
    """What predictions a candidate's sealed prediction set should contain, per hypothesis."""

    def predictions_for(self, candidate: ExplorationCandidate,
                        compiled_spec: ResearchWorldSpec) -> Mapping[str, tuple[object, ...]]: ...


@dataclass(frozen=True)
class StaticPredictionProvider:
    """Every candidate gets the same predictions -- `run_exploration`'s behavior before G3-G5."""
    predictions: Mapping[str, tuple[object, ...]]

    def predictions_for(self, candidate: ExplorationCandidate,
                        compiled_spec: ResearchWorldSpec) -> Mapping[str, tuple[object, ...]]:
        return self.predictions


class FunctionalPredictionProvider:
    """Predictions computed per candidate, from its own compiled spec.

    For a benchmark harness that knows (or is testing) what a candidate's
    control values should predict -- e.g. GT-2's per-value truth table.
    Constructing predictions this way from the answer is still caller-supplied
    knowledge, same discipline as `StaticPredictionProvider`: this module
    generates no hypotheses and knows no ground truth of its own.
    """

    def __init__(self, function: Callable[[ExplorationCandidate, ResearchWorldSpec],
                                          Mapping[str, tuple[object, ...]]]) -> None:
        self._function = function

    def predictions_for(self, candidate: ExplorationCandidate,
                        compiled_spec: ResearchWorldSpec) -> Mapping[str, tuple[object, ...]]:
        return self._function(candidate, compiled_spec)
