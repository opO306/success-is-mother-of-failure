"""G7.3c: the autonomous blind research loop.

Closes G7.3a/G7.3b/G7.3b-4 into one cycle that runs without a person
choosing experiments in between:

    live hypotheses -> G6d ranks planned experiments by how many live pairs
    they split -> seal every live prediction for the chosen experiment
    (G7.2) -> run it through the harness-supplied `AExecutor` (G7.3a) ->
    compare only through `check_prediction_at_horizon` (G7.3b-4) -> mark
    contradicted hypotheses -> repeat (discovery phase) -> run the survivors
    through the planned experiments discovery skipped (validation phase) ->
    seal the final answer (`FinalDiscoverySeal`).

Every executed experiment is preceded in the journal by an
`experiment_candidate_ranked` entry: which phase chose it (discovery or
validation), its observation horizon, and how many live hypothesis pairs
B expected it to split, per question. Without this, a later reader could
see what B did but not what B expected, and "did that experiment inform as
much as B thought it would" -- the first question a metacognitive B asks of
its own history -- would be unanswerable.

Why a validation phase exists (measured while building this Gate, not
assumed): elimination stops the moment one hypothesis is left, so the
survivor may have been checked in a single experiment. In a world the
vocabulary cannot describe -- WORLD-S02 with x2 starting True, against the
baseline=False prior -- discovery alone ended with x2 "SOLVED" as
"x1 -> x2" after one experiment (x1=1, where that wrong claim happens to
predict right) and x3 tied between two wrong claims. The lone survivor of
a *closed* menu is not evidence the menu contained the answer. Validation
runs the not-yet-run planned experiments against every survivor; there,
the wrong claims are contradicted and both questions end NO_SURVIVOR.
Discovery and validation experiments are counted separately, so "B chose
experiments efficiently" and "B then checked its answer" stay two
separate, visible facts.

Allowed by RULES.md's G7.3c exception only for blind synthetic benchmark
worlds: this loop only ever submits `BlindCandidateSpec`s, which the
physical executor (`RealCausalAExecutor`) refuses outright.

What a question can end as (per target observable, after validation):

    SOLVED        exactly one hypothesis survives
    INSEPARABLE   2+ survive and no planned experiment splits any surviving
                  pair. Deliberately no separate EXHAUSTED: the world is
                  deterministic and the plan is enumerated in full, so an
                  executed experiment that splits a pair always removes at
                  least one side of it -- "used up every experiment with 2+
                  left" and "no experiment can split them" are the same
                  condition here. A separate code would be a path nothing
                  can reach.
    NO_SURVIVOR   every hypothesis was contradicted: the world is outside
                  what the vocabulary can say. Never collapsed into SOLVED
                  or INSEPARABLE.
    OPEN          still splittable, but the discovery budget ran out.

`validated_fully` says whether validation reached every planned
experiment; when it did not, a SOLVED/INSEPARABLE verdict has not been
checked against the whole plan.

Hypothesis status is per hypothesis, never "unresolved": in a
deterministic world one experiment either matches a prediction or does not.
"We cannot tell these apart" is a fact about a *set* of survivors, not
about one hypothesis. Statuses reuse `research_state.HYPOTHESIS_STATUSES`:
`contradicted_in_domain` for a rejected claim (rejected within the stated
domain -- alias world, baseline, one-tick edges -- not deleted, not
declared globally false), `supported` for the lone survivor of a solved
question (consistent with every experiment run, not "confirmed"),
`underspecified` for survivors of a tie or of an open question.

A result that cannot be compared (an observation at the wrong tick, a
missing observable) is a harness defect: `check_prediction_at_horizon`
raises and the loop stops rather than scoring it. A failed execution ends
the run as HARNESS_FAILURE.

B-facing: never imports `blind_evaluator`, `blind_synthetic_executor`,
`synthetic_runtime`, or `ground_truth` (checked transitively by
`tests/test_deterministic_blind_research_loop.py`).
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace

from .blind_execution import BlindCandidateSpec
from .blind_hypothesis_generator import BlindHypothesisGenerator
from .blind_prediction_materializer import (
    BlindExperimentPlan, BlindPredictionMaterializer, InterventionalPredictionProvider,
    check_prediction_at_horizon, observation_horizon,
)
from .blind_protocol import FinalDiscoverySeal, seal_final_discovery
from .blind_session import BlindControlDescriptor, BlindObservableDescriptor, BlindWorldDescriptor
from .causal_executor import AExecutor
from .causal_experiment import PredictionSeal
from .causal_hypothesis import CausalHypothesis, CausalHypothesisSet
from .experiment_designer import DiscriminatingCandidate, rank_discriminating_candidates, select_next_experiment
from .research_journal import ResearchJournal
from .research_loop import execute_through_a, seal_predictions

FORMAT = "blind-research-loop-v1"

SOLVED = "SOLVED"
INSEPARABLE = "INSEPARABLE"
NO_SURVIVOR = "NO_SURVIVOR"
OPEN = "OPEN"

COMPLETE = "COMPLETE"
LIMIT_REACHED = "LIMIT_REACHED"
HARNESS_FAILURE = "HARNESS_FAILURE"

_REJECTED = "contradicted_in_domain"

PHASE_DISCOVERY = "discovery"
PHASE_VALIDATION = "validation"


def _digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class QuestionOutcome:
    target_observable_id: str
    verdict: str
    surviving_hypothesis_ids: tuple[str, ...]
    rejected_hypothesis_ids: tuple[str, ...]
    inseparable_pairs: tuple[tuple[str, str], ...]

    def canonical(self) -> dict[str, object]:
        return {"inseparable_pairs": [list(p) for p in self.inseparable_pairs],
                "rejected_hypothesis_ids": list(self.rejected_hypothesis_ids),
                "surviving_hypothesis_ids": list(self.surviving_hypothesis_ids),
                "target_observable_id": self.target_observable_id, "verdict": self.verdict}


@dataclass(frozen=True)
class BlindResearchOutcome:
    """What B ends with -- not just a winner. Separates "found one" from
    "narrowed it to these and can go no further" from "none fit"."""
    alias_world_id: str
    termination: str
    questions: tuple[QuestionOutcome, ...]
    executed_candidate_ids: tuple[str, ...]
    discovery_experiment_count: int
    validated_fully: bool
    plan_size: int
    final_hypothesis_set: CausalHypothesisSet
    final_seal: FinalDiscoverySeal
    format: str = FORMAT

    @property
    def experiment_count(self) -> int:
        return len(self.executed_candidate_ids)

    @property
    def validation_experiment_count(self) -> int:
        return self.experiment_count - self.discovery_experiment_count

    def canonical(self) -> dict[str, object]:
        return {"alias_world_id": self.alias_world_id,
                "discovery_experiment_count": self.discovery_experiment_count,
                "executed_candidate_ids": list(self.executed_candidate_ids),
                "final_hypothesis_set_digest": self.final_hypothesis_set.digest,
                "final_seal": self.final_seal.canonical(), "format": self.format,
                "plan_size": self.plan_size, "questions": [q.canonical() for q in self.questions],
                "termination": self.termination, "validated_fully": self.validated_fully}


def _restricted(hypothesis_set: CausalHypothesisSet, live: frozenset[str]) -> CausalHypothesisSet:
    return CausalHypothesisSet(hypothesis_set.subject_digest,
                               tuple(h for h in hypothesis_set.hypotheses if h.hypothesis_id in live))


def _tied_pairs(hypothesis_set: CausalHypothesisSet, live: frozenset[str],
                plan: BlindExperimentPlan) -> tuple[tuple[str, str], ...]:
    """Live pairs that predict identically on every planned experiment.
    Plan-wide, not "among not-yet-run ones": a run experiment that split a
    live pair would already have removed one side of it (deterministic
    world), so a live pair that is still splittable is splittable only by
    experiments not yet run."""
    provider = InterventionalPredictionProvider(_restricted(hypothesis_set, live))
    rows = [provider.predictions_for(c, plan.compiled_specs[c.candidate_id]) for c in plan.candidates]
    ids = sorted(live)
    return tuple((a, b) for i, a in enumerate(ids) for b in ids[i + 1:] if all(r[a] == r[b] for r in rows))


def _verdict(live: frozenset[str], tied: tuple[tuple[str, str], ...]) -> str:
    if not live:
        return NO_SURVIVOR
    if len(live) == 1:
        return SOLVED
    n = len(live)
    return INSEPARABLE if len(tied) == n * (n - 1) // 2 else OPEN


def _expected_splits(questions, sets, live, plan: BlindExperimentPlan, candidate_id: str) -> dict[str, int]:
    """How many live hypothesis pairs, per question, this experiment is
    predicted to split -- from B's own sealed predictions, before the
    result exists. Journaled with every selection so a later reader (or a
    metacognitive B) can compare "expected to split N" with what the result
    actually removed."""
    candidate = next(c for c in plan.candidates if c.candidate_id == candidate_id)
    spec = plan.compiled_specs[candidate_id]
    counts: dict[str, int] = {}
    for question, hypothesis_set, alive in zip(questions, sets, live):
        if len(alive) < 2:
            continue
        row = InterventionalPredictionProvider(_restricted(hypothesis_set, alive)).predictions_for(candidate, spec)
        ids = sorted(row)
        counts[question.target_observable_id] = sum(
            1 for i, a in enumerate(ids) for b in ids[i + 1:] if row[a] != row[b])
    return counts


def _select(sets: tuple[CausalHypothesisSet, ...], live: tuple[frozenset[str], ...],
            plan: BlindExperimentPlan, executed: frozenset[str]) -> DiscriminatingCandidate | None:
    """G6d over every still-open question at once: a candidate's score is
    the sum of live pairs it splits across questions (pairs are only ever
    counted *within* a question -- hypotheses about different targets are
    never compared). Ties: shorter horizon, then candidate id."""
    totals: dict[str, int] = {c.candidate_id: 0 for c in plan.candidates}
    merged: dict[str, dict[str, tuple[object, ...]]] = {c.candidate_id: {} for c in plan.candidates}
    for hypothesis_set, alive in zip(sets, live):
        if len(alive) < 2:
            continue
        ranked = rank_discriminating_candidates(plan.candidates, plan.compiled_specs,
                                                InterventionalPredictionProvider(_restricted(hypothesis_set, alive)))
        for item in ranked:
            totals[item.candidate_id] += item.disagreement_pair_count
            merged[item.candidate_id].update(item.predictions_by_hypothesis)
    scored = [DiscriminatingCandidate(cid, totals[cid], merged[cid]) for cid in totals]
    ordered = tuple(sorted(scored, key=lambda d: (-d.disagreement_pair_count,
                                                  observation_horizon(plan.compiled_specs[d.candidate_id]),
                                                  d.candidate_id)))
    return select_next_experiment(ordered, executed)


def run_blind_research(
    world: BlindWorldDescriptor,
    controls: tuple[BlindControlDescriptor, ...],
    observables: tuple[BlindObservableDescriptor, ...],
    executor: AExecutor,
    journal: ResearchJournal,
    max_experiments: int | None = None,
    max_validation_experiments: int | None = None,
    generator: BlindHypothesisGenerator = BlindHypothesisGenerator(),
    materializer: BlindPredictionMaterializer = BlindPredictionMaterializer(),
) -> BlindResearchOutcome:
    """Run the loop to a stop and seal the final answer into `journal`.

    `executor` is assembled by the harness (e.g. `SyntheticBlindAExecutor`)
    and handed in -- this function never sees what is behind it.
    `max_experiments` bounds discovery; `max_validation_experiments` bounds
    validation (None = every planned experiment discovery did not run).
    """
    for name, value in (("max_experiments", max_experiments),
                        ("max_validation_experiments", max_validation_experiments)):
        if value is not None and (isinstance(value, bool) or not isinstance(value, int) or value < 0):
            raise ValueError(f"{name} must be a nonnegative integer or None")
    space = generator.generate(world, controls, observables)
    plan = materializer.plan(world, controls, observables)
    sets = tuple(materializer.materialize(q, world, controls, observables, plan) for q in space.questions)
    for question, hypothesis_set in zip(space.questions, sets):
        journal.append("hypothesis_set_created", hypothesis_set.subject_digest,
                       {"hypothesis_set": hypothesis_set.canonical(),
                        "target_observable_id": question.target_observable_id})

    live = [frozenset(h.hypothesis_id for h in s.hypotheses) for s in sets]
    executed: list[str] = []
    candidate_by_id = {c.candidate_id: c for c in plan.candidates}
    budget = len(plan.candidates) if max_experiments is None else max_experiments
    termination = COMPLETE

    def run_one(candidate_id: str, phase: str) -> bool:
        """Log why, seal, execute, compare, reject. False if the harness failed."""
        candidate = candidate_by_id[candidate_id]
        spec = plan.compiled_specs[candidate_id]
        assert isinstance(spec, BlindCandidateSpec)
        expected = _expected_splits(space.questions, sets, live, plan, candidate_id)
        journal.append("experiment_candidate_ranked", candidate_id, {
            "phase": phase, "horizon": observation_horizon(spec),
            "expected_split_pairs": sum(expected.values()),
            "expected_split_pairs_by_question": expected})
        # Seal every live hypothesis of every question -- one run observes
        # all targets, so all of them are tested by it, and all of them must
        # be on record before the result exists.
        sealed: dict[str, tuple[object, ...]] = {}
        for hypothesis_set, alive in zip(sets, live):
            if alive:
                sealed.update(InterventionalPredictionProvider(_restricted(hypothesis_set, alive))
                              .predictions_for(candidate, spec))
        seal_predictions(journal, PredictionSeal(f"SEAL-{candidate_id}", candidate_id,
                                                 journal.next_sequence, sealed))
        result = execute_through_a(journal, executor, candidate_id, spec)
        executed.append(candidate_id)
        if result.status != "success":
            return False
        # `execution_completed` holds only the run's digest; the observed
        # values themselves must be journaled too, or nothing downstream
        # (a data store, a later learned B) can recover what was actually
        # seen. Alias-only by construction (`BlindRun`).
        journal.append("observation_recorded", candidate_id, {"run": result.run.canonical()})
        comparisons = {hid: all(check_prediction_at_horizon(spec, p, result.run) for p in predictions)
                       for hid, predictions in sorted(sealed.items())}
        journal.append("result_compared", candidate_id, {"held": comparisons})
        for index, alive in enumerate(live):
            rejected = sorted(hid for hid in alive if not comparisons[hid])
            for hid in rejected:
                journal.append("hypothesis_status_changed", hid, {"arm_id": candidate_id, "status": _REJECTED})
            live[index] = alive - frozenset(rejected)
        return True

    # Discovery: G6d picks whatever splits the most live pairs.
    while True:
        chosen = _select(sets, tuple(live), plan, frozenset(executed))
        if chosen is None:
            break
        if len(executed) >= budget:
            termination = LIMIT_REACHED
            break
        if not run_one(chosen.candidate_id, PHASE_DISCOVERY):
            termination = HARNESS_FAILURE
            break
    discovery_count = len(executed)

    # Validation: every planned experiment discovery skipped, shortest
    # horizon first, against whatever survived. Skipped after a harness
    # failure (the executor is not trustworthy) or a budget stop (OPEN
    # questions are not finished, so there is no answer to validate yet).
    remaining = sorted((c for c in plan.candidates if c.candidate_id not in executed),
                       key=lambda c: (observation_horizon(plan.compiled_specs[c.candidate_id]), c.candidate_id))
    validation_budget = len(remaining) if max_validation_experiments is None else max_validation_experiments
    validated_fully = termination == COMPLETE and validation_budget >= len(remaining)
    if termination == COMPLETE:
        for candidate in remaining[:validation_budget]:
            if not any(live):
                break
            if not run_one(candidate.candidate_id, PHASE_VALIDATION):
                termination = HARNESS_FAILURE
                validated_fully = False
                break

    return _finish(world, space.questions, sets, tuple(live), plan, tuple(executed), discovery_count,
                   validated_fully, termination, journal)


def _finish(world, questions, sets, live, plan, executed, discovery_count, validated_fully, termination,
            journal) -> BlindResearchOutcome:
    outcomes: list[QuestionOutcome] = []
    final_hypotheses: list[CausalHypothesis] = []
    unresolved: list[str] = []
    for question, hypothesis_set, alive in zip(questions, sets, live):
        tied = _tied_pairs(hypothesis_set, alive, plan) if len(alive) >= 2 else ()
        verdict = _verdict(alive, tied)
        all_ids = [h.hypothesis_id for h in hypothesis_set.hypotheses]
        outcomes.append(QuestionOutcome(
            question.target_observable_id, verdict,
            tuple(sorted(alive)), tuple(sorted(set(all_ids) - alive)),
            tied if verdict == INSEPARABLE else ()))
        for hypothesis in hypothesis_set.hypotheses:
            if hypothesis.hypothesis_id not in alive:
                status = _REJECTED
            elif not executed:
                status = "untested"
            elif verdict == SOLVED:
                status = "supported"
            else:
                status = "underspecified"
                unresolved.append(hypothesis.hypothesis_id)
            final_hypotheses.append(replace(hypothesis, status=status))
    final_set = CausalHypothesisSet(
        _digest({"alias_world_id": world.alias_world_id, "format": FORMAT,
                 "questions": [s.subject_digest for s in sets]}),
        tuple(final_hypotheses))
    seal = seal_final_discovery(journal, world.alias_world_id, final_set, tuple(unresolved))
    return BlindResearchOutcome(world.alias_world_id, termination, tuple(outcomes), executed, discovery_count,
                                validated_fully, len(plan.candidates), final_set, seal)
