"""G7.3b-3: turn B's own claims into predictions G6d can rank experiments by.

Three pieces, all B-facing (no import of `blind_evaluator`,
`blind_synthetic_executor`, `synthetic_runtime`, or `ground_truth`, checked
transitively by `tests/test_deterministic_blind_hypothesis.py`):

  * `BlindExperimentPlan` -- the experiments B itself proposes: every way of
    setting each public control to 1, 0, or leaving it free, except leaving
    all of them free (that is the observational baseline, not an
    intervention, and `InterventionalPrediction` requires at least one
    pinned control). Leaving a control free is not optional: a mediator can
    only show itself when it is *not* pinned, so a plan that always pins
    every control could never separate "c -> m -> t" from "m -> t".
    Every candidate compiles to a `BlindCandidateSpec` -- never a real spec
    -- which G7.3a's `SyntheticBlindAExecutor` can already run.
  * `BlindPredictionMaterializer.materialize` -- one `CausalHypothesis` per
    claim in a `BlindQuestion`, whose `predictions` are one
    `InterventionalPrediction` per planned candidate: "under these pinned
    controls, the target observable at the final tick will be X".
  * `InterventionalPredictionProvider` -- a `CandidatePredictionProvider`
    that looks those predictions back up by candidate, which is the exact
    shape `experiment_designer.rank_discriminating_candidates` consumes.

Nothing here runs the world, reads a result, or updates a hypothesis --
that loop is G7.3c.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from itertools import product
from typing import Mapping

from .blind_execution import BlindCandidateSpec
from .blind_hypothesis import predict_target
from .blind_hypothesis_generator import BlindQuestion, validate_blind_interface
from .blind_session import BlindControlDescriptor, BlindObservableDescriptor, BlindWorldDescriptor
from .causal_hypothesis import CausalHypothesis, CausalHypothesisSet
from .exploration_space import ExplorationBudgetExceeded, ExplorationCandidate
from .interventional_prediction import InterventionalPrediction
from .research_observable_prediction import ObservablePrediction
from .research_world import ResearchWorldSpec

FORMAT = "blind-prediction-materializer-v1"

DEFAULT_MAX_CANDIDATES = 729  # 3**6: every setting of six controls

_FREE = None
_CONTROL_SETTINGS = (1, 0, _FREE)


def _digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _sorted_pairs(control_values: tuple[tuple[str, object], ...]) -> tuple[tuple[str, object], ...]:
    return tuple(sorted(control_values))


@dataclass(frozen=True)
class BlindExperimentPlan:
    """B's own candidate experiments for one alias world, and their blind specs."""
    plan_id: str
    candidates: tuple[ExplorationCandidate, ...]
    compiled_specs: Mapping[str, ResearchWorldSpec]


class InterventionalPredictionProvider:
    """Serves each hypothesis's `InterventionalPrediction` for a candidate,
    matched on the candidate's exact pinned control values.

    A hypothesis with no prediction for a candidate raises instead of
    returning `()`: G6d compares prediction tuples with `!=`, so an empty
    tuple would score as a disagreement with every hypothesis that did
    predict something -- a coverage gap masquerading as evidence.
    """

    def __init__(self, hypothesis_set: CausalHypothesisSet) -> None:
        self._by_hypothesis: dict[str, dict[tuple[tuple[str, object], ...], tuple[object, ...]]] = {}
        for hypothesis in hypothesis_set.hypotheses:
            table: dict[tuple[tuple[str, object], ...], list[object]] = {}
            for prediction in hypothesis.predictions:
                if isinstance(prediction, InterventionalPrediction):
                    table.setdefault(_sorted_pairs(prediction.control_values), []).append(prediction.prediction)
            self._by_hypothesis[hypothesis.hypothesis_id] = {key: tuple(value) for key, value in table.items()}

    def predictions_for(self, candidate: ExplorationCandidate,
                        compiled_spec: ResearchWorldSpec) -> Mapping[str, tuple[object, ...]]:
        key = _sorted_pairs(candidate.control_values)
        result: dict[str, tuple[object, ...]] = {}
        for hypothesis_id, table in sorted(self._by_hypothesis.items()):
            if key not in table:
                raise ValueError(f"hypothesis {hypothesis_id} makes no prediction for candidate "
                                 f"{candidate.candidate_id}")
            result[hypothesis_id] = table[key]
        return result


@dataclass(frozen=True)
class BlindPredictionMaterializer:
    baseline: bool = False
    max_candidates: int = DEFAULT_MAX_CANDIDATES

    def plan(self, world: BlindWorldDescriptor,
             controls: tuple[BlindControlDescriptor, ...],
             observables: tuple[BlindObservableDescriptor, ...]) -> BlindExperimentPlan:
        validate_blind_interface(world, controls, observables)
        control_ids = tuple(sorted(c.alias_control_id for c in controls))
        requested = len(_CONTROL_SETTINGS) ** len(control_ids) - 1
        if requested > self.max_candidates:
            raise ExplorationBudgetExceeded(requested, self.max_candidates)
        plan_id = f"BPLAN-{_digest({'alias_world_id': world.alias_world_id, 'controls': list(control_ids)})[:16]}"
        candidates: list[ExplorationCandidate] = []
        for settings in product(_CONTROL_SETTINGS, repeat=len(control_ids)):
            control_values = tuple((cid, value) for cid, value in zip(control_ids, settings) if value is not _FREE)
            if not control_values:
                continue
            candidate_id = f"BCAND-{_digest({'control_values': control_values, 'plan_id': plan_id})[:16]}"
            candidates.append(ExplorationCandidate(candidate_id, plan_id, control_values))
        compiled = {c.candidate_id: BlindCandidateSpec(world.alias_world_id, c.candidate_id, c.control_values,
                                                       ticks=world.ticks)
                    for c in candidates}
        return BlindExperimentPlan(plan_id, tuple(candidates), compiled)

    def materialize(self, question: BlindQuestion, world: BlindWorldDescriptor,
                    controls: tuple[BlindControlDescriptor, ...],
                    observables: tuple[BlindObservableDescriptor, ...],
                    plan: BlindExperimentPlan) -> CausalHypothesisSet:
        validate_blind_interface(world, controls, observables)
        if not isinstance(question, BlindQuestion):
            raise TypeError(f"question must be a BlindQuestion, got {type(question).__name__}")
        target = [o for o in observables if o.alias_observable_id == question.target_observable_id]
        if len(target) != 1 or target[0].alias_variable_id != question.target_variable_id:
            raise ValueError("question does not name one of this world's observables")
        variable_of = {c.alias_control_id: c.alias_variable_id for c in controls}
        conditions = (f"alias_world:{world.alias_world_id}", f"baseline:{str(self.baseline).lower()}",
                      f"observed_at_tick:{world.ticks}")
        hypotheses = []
        for claim in question.claims:
            predictions = []
            for candidate in plan.candidates:
                pinned = {variable_of[cid]: bool(value) for cid, value in candidate.control_values}
                expected = predict_target(claim, pinned, self.baseline)
                predictions.append(InterventionalPrediction(
                    candidate.control_values,
                    ObservablePrediction(world.ticks, question.target_observable_id, expected)))
            hypotheses.append(CausalHypothesis(
                hypothesis_id=claim.claim_id, statement=claim.statement(),
                applicability_conditions=conditions, predictions=tuple(predictions),
                evidence=(), status="untested"))
        subject = _digest({"alias_world_id": world.alias_world_id, "format": FORMAT,
                           "target_observable_id": question.target_observable_id})
        return CausalHypothesisSet(subject, tuple(hypotheses))
