"""G7.3b-3/G7.3b-4: turn B's own claims into predictions G6d can rank
experiments by -- with the observation time as part of every experiment.

All B-facing (no import of `blind_evaluator`, `blind_synthetic_executor`,
`synthetic_runtime`, or `ground_truth`, checked transitively by
`tests/test_deterministic_blind_hypothesis.py`):

  * `BlindExperimentPlan` -- the experiments B itself proposes: every
    (intervention, observation horizon) pair. An intervention is every way
    of setting each public control to 1, 0, or leaving it free, except
    leaving all of them free (that is the observational baseline, not an
    intervention, and `InterventionalPrediction` requires at least one
    pinned control). Leaving a control free is not optional: a mediator can
    only show itself when it is *not* pinned. The horizon is
    1..`world.ticks` (the longest run the harness allows): "set x1, read x3
    after 1 tick" and "... after 2 ticks" are different experiments
    (G7.3b-4). Every candidate compiles to a `BlindCandidateSpec` -- never a
    real spec -- whose `ticks` *is* its horizon: the one place the horizon
    lives, so what gets executed and what gets predicted cannot drift apart.
  * `BlindPredictionMaterializer.materialize` -- one `CausalHypothesis` per
    claim in a `BlindQuestion`, whose `predictions` are one
    `InterventionalPrediction` per planned candidate: "under these pinned
    controls, the target observable at tick <horizon> will be X", computed
    by B simulating its own claim tick by tick
    (`blind_hypothesis.simulate_claim`) -- never by running A.
  * `InterventionalPredictionProvider` -- a `CandidatePredictionProvider`
    keyed on (pinned controls, horizon), the shape
    `experiment_designer.rank_discriminating_candidates` consumes.
  * `observation_horizon` -- G6d's tie-break cost: at equal discriminating
    power the shorter observation wins, so B does not habitually run the
    longest experiment available.
  * `check_prediction_at_horizon` -- the only sanctioned way to compare a
    prediction with a blind result: it refuses a tick-2 prediction against
    a tick-1 observation, and a run that did not stop at its horizon.
  * `inseparable_pairs` -- hypothesis pairs no planned experiment separates
    (e.g. a 2-step chain vs. its last edge when the harness allows only
    1-tick runs). An honest tie G7.3c must carry, not break by elimination.

Nothing here runs the world, reads a result for learning, or updates a
hypothesis -- that loop is G7.3c.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from itertools import product
from typing import Mapping

from .blind_execution import BlindCandidateSpec, BlindRun
from .blind_hypothesis import BlindCausalClaim, predict_target
from .blind_hypothesis_generator import BlindQuestion, validate_blind_interface
from .blind_session import BlindControlDescriptor, BlindObservableDescriptor, BlindWorldDescriptor
from .causal_hypothesis import CausalHypothesis, CausalHypothesisSet
from .exploration_space import ExplorationBudgetExceeded, ExplorationCandidate
from .interventional_prediction import InterventionalPrediction
from .research_observable_prediction import ObservablePrediction
from .research_world import ResearchWorldSpec

FORMAT = "blind-prediction-materializer-v2"

DEFAULT_MAX_CANDIDATES = 2187  # (3**6) * 3: six controls, horizons 1..3

_FREE = None
_CONTROL_SETTINGS = (1, 0, _FREE)


def _digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _sorted_pairs(control_values: tuple[tuple[str, object], ...]) -> tuple[tuple[str, object], ...]:
    return tuple(sorted(control_values))


@dataclass(frozen=True)
class BlindExperimentPlan:
    """B's own candidate experiments for one alias world, and their blind
    specs -- each spec's `ticks` is that candidate's observation horizon."""
    plan_id: str
    candidates: tuple[ExplorationCandidate, ...]
    compiled_specs: Mapping[str, ResearchWorldSpec]


def observation_horizon(spec: ResearchWorldSpec) -> int:
    """How many ticks a blind candidate runs before it is observed."""
    if not isinstance(spec, BlindCandidateSpec):
        raise TypeError(f"observation horizon is defined for BlindCandidateSpec, got {type(spec).__name__}")
    return spec.ticks


class InterventionalPredictionProvider:
    """Serves each hypothesis's `InterventionalPrediction` for a candidate,
    matched on its exact pinned control values *and* its observation horizon
    (the compiled spec's `ticks`). Matching on control values alone would
    hand G6d a tick-2 prediction for a tick-1 experiment.

    A hypothesis with no prediction for a (candidate, horizon) raises
    instead of returning `()` or a filler value: G6d compares prediction
    tuples with `!=`, so a filler would score as evidence -- a coverage gap
    masquerading as disagreement (or agreement).
    """

    def __init__(self, hypothesis_set: CausalHypothesisSet) -> None:
        self._by_hypothesis: dict[str, dict[tuple[object, ...], tuple[object, ...]]] = {}
        for hypothesis in hypothesis_set.hypotheses:
            table: dict[tuple[object, ...], list[object]] = {}
            for prediction in hypothesis.predictions:
                if isinstance(prediction, InterventionalPrediction):
                    key = (_sorted_pairs(prediction.control_values), prediction.prediction.tick)
                    table.setdefault(key, []).append(prediction.prediction)
            self._by_hypothesis[hypothesis.hypothesis_id] = {key: tuple(value) for key, value in table.items()}

    def predictions_for(self, candidate: ExplorationCandidate,
                        compiled_spec: ResearchWorldSpec) -> Mapping[str, tuple[object, ...]]:
        key = (_sorted_pairs(candidate.control_values), observation_horizon(compiled_spec))
        result: dict[str, tuple[object, ...]] = {}
        for hypothesis_id, table in sorted(self._by_hypothesis.items()):
            if key not in table:
                raise ValueError(f"hypothesis {hypothesis_id} makes no prediction for candidate "
                                 f"{candidate.candidate_id} at horizon {key[1]}")
            result[hypothesis_id] = table[key]
        return result


def check_prediction_at_horizon(candidate_spec: BlindCandidateSpec, prediction: ObservablePrediction,
                                run: BlindRun) -> bool:
    """Whether `prediction` held in `run`, refusing any cross-horizon comparison.

    Raises `ValueError` if the prediction is not about this candidate's
    horizon, if the run did not end exactly at that horizon (an executor
    that ignored the horizon), or if the observable is missing -- each of
    those would otherwise silently turn "observed at the wrong time" into
    "the hypothesis is wrong".
    """
    if not isinstance(candidate_spec, BlindCandidateSpec) or not isinstance(run, BlindRun):
        raise TypeError("check_prediction_at_horizon compares a BlindCandidateSpec's prediction with a BlindRun")
    horizon = candidate_spec.ticks
    if prediction.tick != horizon:
        raise ValueError(f"prediction is for tick {prediction.tick}, experiment observes tick {horizon}")
    if run.checkpoints[-1].tick != horizon:
        raise ValueError(f"run ended at tick {run.checkpoints[-1].tick}, experiment asked for {horizon}")
    observed = run.checkpoint_at(horizon).value_of(prediction.observable_id)
    if observed is None:
        raise ValueError(f"observable {prediction.observable_id} missing at tick {horizon}")
    return observed == prediction.expected_value


def inseparable_pairs(hypothesis_set: CausalHypothesisSet,
                      plan: BlindExperimentPlan) -> tuple[tuple[str, str], ...]:
    """Hypothesis-id pairs that predict identically on every planned
    experiment -- computed from B's own predictions only."""
    provider = InterventionalPredictionProvider(hypothesis_set)
    rows = [provider.predictions_for(c, plan.compiled_specs[c.candidate_id]) for c in plan.candidates]
    ids = sorted(h.hypothesis_id for h in hypothesis_set.hypotheses)
    return tuple((a, b) for i, a in enumerate(ids) for b in ids[i + 1:]
                 if all(row[a] == row[b] for row in rows))


@dataclass(frozen=True)
class BlindPredictionMaterializer:
    baseline: bool = False
    max_candidates: int = DEFAULT_MAX_CANDIDATES

    def plan(self, world: BlindWorldDescriptor,
             controls: tuple[BlindControlDescriptor, ...],
             observables: tuple[BlindObservableDescriptor, ...]) -> BlindExperimentPlan:
        validate_blind_interface(world, controls, observables)
        control_ids = tuple(sorted(c.alias_control_id for c in controls))
        horizons = tuple(range(1, world.ticks + 1))
        requested = (len(_CONTROL_SETTINGS) ** len(control_ids) - 1) * len(horizons)
        if requested > self.max_candidates:
            raise ExplorationBudgetExceeded(requested, self.max_candidates)
        plan_id = f"BPLAN-{_digest({'alias_world_id': world.alias_world_id, 'controls': list(control_ids)})[:16]}"
        candidates: list[ExplorationCandidate] = []
        compiled: dict[str, ResearchWorldSpec] = {}
        for settings in product(_CONTROL_SETTINGS, repeat=len(control_ids)):
            control_values = tuple((cid, value) for cid, value in zip(control_ids, settings) if value is not _FREE)
            if not control_values:
                continue
            for horizon in horizons:
                candidate_id = "BCAND-" + _digest({"control_values": control_values, "horizon": horizon,
                                                   "plan_id": plan_id})[:16]
                candidates.append(ExplorationCandidate(candidate_id, plan_id, control_values))
                compiled[candidate_id] = BlindCandidateSpec(world.alias_world_id, candidate_id, control_values,
                                                            ticks=horizon)
        return BlindExperimentPlan(plan_id, tuple(candidates), compiled)

    def materialize(self, question: BlindQuestion, world: BlindWorldDescriptor,
                    controls: tuple[BlindControlDescriptor, ...],
                    observables: tuple[BlindObservableDescriptor, ...],
                    plan: BlindExperimentPlan, initial: Mapping[str, bool] | None = None) -> CausalHypothesisSet:
        """`initial` (grammar v2): B's observed tick-0 value of each visible
        unforced variable. Without it every unforced variable is assumed to
        start at `baseline` -- the grammar-v1 behaviour."""
        validate_blind_interface(world, controls, observables)
        if not isinstance(question, BlindQuestion):
            raise TypeError(f"question must be a BlindQuestion, got {type(question).__name__}")
        target = [o for o in observables if o.alias_observable_id == question.target_observable_id]
        if len(target) != 1 or target[0].alias_variable_id != question.target_variable_id:
            raise ValueError("question does not name one of this world's observables")
        hypotheses = tuple(self.materialize_claim(claim, question.target_observable_id, world, controls, plan, initial)
                           for claim in question.claims)
        subject = _digest({"alias_world_id": world.alias_world_id, "format": FORMAT,
                           "target_observable_id": question.target_observable_id})
        return CausalHypothesisSet(subject, hypotheses)

    def materialize_claim(self, claim: BlindCausalClaim, target_observable_id: str, world: BlindWorldDescriptor,
                          controls: tuple[BlindControlDescriptor, ...], plan: BlindExperimentPlan,
                          initial: Mapping[str, bool] | None = None, origin: str = "enumerated") -> CausalHypothesis:
        """One claim -> one `CausalHypothesis` over every planned experiment.
        `origin` is "enumerated" (the generator's up-front menu) or "noticed"
        (proposed by B from its own observations after a surprise)."""
        variable_of = {c.alias_control_id: c.alias_variable_id for c in controls}
        conditions = [f"alias_world:{world.alias_world_id}", f"baseline:{str(self.baseline).lower()}",
                      "time:one_tick_per_edge"]
        if initial is not None:
            conditions.append("initial:observed")
        if origin == "noticed":
            conditions.append("origin:noticed")
        predictions = []
        for candidate in plan.candidates:
            horizon = observation_horizon(plan.compiled_specs[candidate.candidate_id])
            pinned = {variable_of[cid]: bool(value) for cid, value in candidate.control_values}
            expected = predict_target(claim, pinned, horizon, self.baseline, initial)
            predictions.append(InterventionalPrediction(
                candidate.control_values, ObservablePrediction(horizon, target_observable_id, expected)))
        return CausalHypothesis(
            hypothesis_id=claim.claim_id, statement=claim.statement(),
            applicability_conditions=tuple(conditions), predictions=tuple(predictions),
            evidence=(), status="untested")
