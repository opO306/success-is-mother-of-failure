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

Every final hypothesis carries its evidence: one `EvidenceReference` per
experiment it was tested in -- `supports` when its sealed prediction held
(consistent, never "confirmed"), `refutes` when it failed -- each pointing
by digest at the `result_compared` journal entry that recorded it. A
rejected hypothesis's last evidence is the experiment that refuted it; a
later reader can walk from any conclusion back to the observations behind it.

Before the final seal, every question gets a `limitation_assessed` journal
entry: B's own diagnosis of why it ended where it did
(`blind_limitations.py`), computed from its own claims -- never from the
answer key, which only grades that diagnosis afterwards.

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

G8 (grammar v2) adds three things, in this order within a run:

  1. Look first. Before any hypothesis is materialized, B runs one
     observation-only arm -- nothing pinned, declared as observation-only in
     the journal before it runs, never sealed or scored -- and takes each
     visible variable's tick-0 value as its initial value. Unforced visible
     variables then start where B *saw* them, not at an assumed False.
  2. Surprise. When an experiment leaves a question with no live hypothesis,
     B journals an `anomaly_recorded` entry naming the experiment.
  3. Notice. Right then, B scans every run it has observed for a DELAYED
     pattern about that target (`blind_noticing.py`). Each pattern found
     joins the question's live hypotheses (`hypothesis_noticed`, with the
     arms it was derived from) and is tested only by experiments run after
     it -- the data it was fitted to never counts as its evidence. A noticed
     hypothesis that no later experiment tested is a *proposal*: it never
     makes a question SOLVED, and the question's diagnosis says so
     (`proposal_untested`).

G9 adds a tool phase after validation. If a question still holds an
untested noticed idea, or a tie, B composes a press/release experiment from
the primitive "hold this control at 1/0 at tick t" (`blind_tools.py`),
trying tools it already has before searching for a new one. Tool
experiments are sealed, executed, compared and journaled exactly like
planned ones; a search that finds nothing is journaled as
`tool_search_failed`. Tools that were used are reported in the outcome
(`tools_used`) so a later run can be handed them as its toolbox.

B-facing: never imports `blind_evaluator`, `blind_synthetic_executor`,
`synthetic_runtime`, or `ground_truth` (checked transitively by
`tests/test_deterministic_blind_research_loop.py`).
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace

from .blind_execution import BlindCandidateSpec, BlindRun
from .blind_hypothesis_generator import BlindHypothesisGenerator, BlindQuestion
from .blind_limitations import assess_limitation
from .blind_noticing import notice_delayed_relations
from .blind_tools import DEFAULT_MAX_TOOL_EXPERIMENTS, Tool, design_tool_experiment
from .blind_prediction_materializer import (
    BlindExperimentPlan, BlindPredictionMaterializer, InterventionalPredictionProvider,
    check_prediction_at_horizon, observation_horizon,
)
from .blind_protocol import EVENT_OBSERVATION_ONLY_DECLARED, FinalDiscoverySeal, seal_final_discovery
from .blind_session import BlindControlDescriptor, BlindObservableDescriptor, BlindWorldDescriptor
from .causal_executor import AExecutor
from .causal_experiment import PredictionSeal
from .blind_hypothesis import predict_target
from .causal_hypothesis import CausalHypothesis, CausalHypothesisSet
from .experiment_designer import DiscriminatingCandidate, rank_discriminating_candidates, select_next_experiment
from .evidence import EvidenceReference
from .research_journal import ResearchJournal
from .research_observable_prediction import ObservablePrediction
from .research_loop import execute_through_a, seal_predictions

FORMAT = "blind-research-loop-v3"

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
    limitation: dict[str, object]
    proposed_hypothesis_ids: tuple[str, ...] = ()

    def canonical(self) -> dict[str, object]:
        return {"inseparable_pairs": [list(p) for p in self.inseparable_pairs],
                "limitation": self.limitation,
                "proposed_hypothesis_ids": list(self.proposed_hypothesis_ids),
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
    observation_arm_ids: tuple[str, ...] = ()
    initial_values: tuple[tuple[str, bool], ...] = ()
    tool_arm_ids: tuple[str, ...] = ()
    tools_used: tuple[dict, ...] = ()
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
                "initial_values": [list(pair) for pair in self.initial_values],
                "observation_arm_ids": list(self.observation_arm_ids),
                "tool_arm_ids": list(self.tool_arm_ids), "tools_used": [dict(t) for t in self.tools_used],
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
    observe_first: bool = True,
    notice: bool = True,
    toolbox: tuple[Tool, ...] = (),
    max_tool_experiments: int = DEFAULT_MAX_TOOL_EXPERIMENTS,
) -> BlindResearchOutcome:
    """Run the loop to a stop and seal the final answer into `journal`.

    `executor` is assembled by the harness (e.g. `SyntheticBlindAExecutor`)
    and handed in -- this function never sees what is behind it.
    `max_experiments` bounds discovery; `max_validation_experiments` bounds
    validation (None = every planned experiment discovery did not run).
    `observe_first` / `notice` switch off the two G8 behaviours, for
    comparison against the grammar-v1 loop.
    """
    for name, value in (("max_experiments", max_experiments),
                        ("max_validation_experiments", max_validation_experiments)):
        if value is not None and (isinstance(value, bool) or not isinstance(value, int) or value < 0):
            raise ValueError(f"{name} must be a nonnegative integer or None")
    space = generator.generate(world, controls, observables)
    plan = materializer.plan(world, controls, observables)
    questions = list(space.questions)
    variable_of = {c.alias_control_id: c.alias_variable_id for c in controls}
    variable_of_observable = {o.alias_observable_id: o.alias_variable_id for o in observables}
    observed: list[tuple[str, dict[str, bool], BlindRun]] = []
    observation_arms: list[str] = []
    initial: dict[str, bool] | None = None
    termination = COMPLETE

    if observe_first:
        arm_id = "BOBS-" + _digest({"alias_world_id": world.alias_world_id, "plan_id": plan.plan_id})[:16]
        spec = BlindCandidateSpec(world.alias_world_id, arm_id, (), ticks=1)
        journal.append(EVENT_OBSERVATION_ONLY_DECLARED, arm_id,
                       {"reason": "initial_values", "horizon": spec.ticks})
        result = execute_through_a(journal, executor, arm_id, spec)
        observation_arms.append(arm_id)
        if result.status != "success":
            termination = HARNESS_FAILURE
        else:
            journal.append("observation_recorded", arm_id, {"run": result.run.canonical()})
            observed.append((arm_id, {}, result.run))
            tick0 = result.run.checkpoint_at(0)
            initial = {variable_of_observable[oid]: value for oid, value in tick0.observables
                       if oid in variable_of_observable}

    sets = [materializer.materialize(q, world, controls, observables, plan, initial) for q in questions]
    for question, hypothesis_set in zip(questions, sets):
        journal.append("hypothesis_set_created", hypothesis_set.subject_digest,
                       {"hypothesis_set": hypothesis_set.canonical(),
                        "target_observable_id": question.target_observable_id})

    live = [frozenset(h.hypothesis_id for h in s.hypotheses) for s in sets]
    noticed: set[str] = set()
    executed: list[str] = []
    candidate_by_id = {c.candidate_id: c for c in plan.candidates}
    budget = len(plan.candidates) if max_experiments is None else max_experiments
    evidence: dict[str, list[EvidenceReference]] = {h.hypothesis_id: [] for s in sets for h in s.hypotheses}

    def surprise_and_notice(index: int, candidate_id: str) -> None:
        question = questions[index]
        journal.append("anomaly_recorded", question.target_observable_id,
                       {"arm_id": candidate_id, "kind": "all_hypotheses_refuted",
                        "target_observable_id": question.target_observable_id})
        if not notice:
            return
        claims = notice_delayed_relations(question, world, controls, observables,
                                          [(pinned, run) for _arm, pinned, run in observed])
        if not claims:
            return
        derived_from = [arm for arm, _pinned, _run in observed]
        new_hypotheses = []
        for claim in claims:
            hypothesis = materializer.materialize_claim(claim, question.target_observable_id, world, controls,
                                                        plan, initial, origin="noticed")
            journal.append("hypothesis_noticed", hypothesis.hypothesis_id,
                           {"derived_from": derived_from, "hypothesis": hypothesis.canonical(),
                            "target_observable_id": question.target_observable_id, "trigger_arm": candidate_id})
            new_hypotheses.append(hypothesis)
            evidence[hypothesis.hypothesis_id] = []
            noticed.add(hypothesis.hypothesis_id)
        questions[index] = BlindQuestion(question.target_observable_id, question.target_variable_id,
                                         question.claims + claims)
        sets[index] = CausalHypothesisSet(sets[index].subject_digest, sets[index].hypotheses + tuple(new_hypotheses))
        live[index] = live[index] | frozenset(h.hypothesis_id for h in new_hypotheses)

    def seal_execute_compare(arm_id: str, spec: BlindCandidateSpec, sealed: dict[str, tuple[object, ...]],
                             pinned_for_noticing: dict[str, bool]) -> bool:
        """The protocol every executed experiment follows, planned or tool:
        seal -> execute -> record observation -> compare -> reject -> react
        to surprise. False if the harness failed."""
        seal_predictions(journal, PredictionSeal(f"SEAL-{arm_id}", arm_id, journal.next_sequence, sealed))
        result = execute_through_a(journal, executor, arm_id, spec)
        if result.status != "success":
            return False
        # `execution_completed` holds only the run's digest; the observed
        # values themselves must be journaled too, or nothing downstream
        # (a data store, a later learned B) can recover what was actually
        # seen. Alias-only by construction (`BlindRun`).
        journal.append("observation_recorded", arm_id, {"run": result.run.canonical()})
        observed.append((arm_id, pinned_for_noticing, result.run))
        comparisons = {hid: all(check_prediction_at_horizon(spec, p, result.run) for p in predictions)
                       for hid, predictions in sorted(sealed.items())}
        compared = journal.append("result_compared", arm_id, {"held": comparisons})
        for hid, held in comparisons.items():
            evidence[hid].append(EvidenceReference(
                arm_id, "supports" if held else "refutes", compared.record_digest,
                "prediction_held" if held else "prediction_failed"))
        for index, alive in enumerate(live):
            rejected = sorted(hid for hid in alive if not comparisons[hid])
            for hid in rejected:
                journal.append("hypothesis_status_changed", hid, {"arm_id": arm_id, "status": _REJECTED})
            live[index] = alive - frozenset(rejected)
            if alive and not live[index]:
                surprise_and_notice(index, arm_id)
        return True

    def run_one(candidate_id: str, phase: str) -> bool:
        """Log why, then run one planned experiment. False if the harness failed."""
        candidate = candidate_by_id[candidate_id]
        spec = plan.compiled_specs[candidate_id]
        assert isinstance(spec, BlindCandidateSpec)
        expected = _expected_splits(questions, sets, live, plan, candidate_id)
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
        executed.append(candidate_id)
        return seal_execute_compare(candidate_id, spec, sealed,
                                    {variable_of[cid]: bool(v) for cid, v in candidate.control_values})

    # Discovery: G6d picks whatever splits the most live pairs.
    while termination == COMPLETE:
        chosen = _select(tuple(sets), tuple(live), plan, frozenset(executed))
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

    # Tools: when planned experiments are used up and a question still holds
    # an untested idea or a tie, compose a press experiment (G9).
    tool_arms: list[str] = []
    tools_used: list[dict] = []
    known_tools: list[Tool] = list(toolbox)
    already_run: set[tuple[str, str]] = set()
    for _attempt in range(max_tool_experiments if termination == COMPLETE else 0):
        needing, experiment = [], None
        for index, question in enumerate(questions):
            proposals = sorted(h for h in live[index] if h in noticed and not evidence[h])
            tested = sorted(h for h in live[index] if h not in proposals)
            if not proposals and len(tested) < 2:
                continue
            needing.append(index)
            claims = {claim.claim_id: claim for claim in question.claims}
            # Rank each untested idea's rivals (claims already refuted here)
            # by how many planned experiments they agreed with it on.
            by_id = {h.hypothesis_id: h for h in sets[index].hypotheses}
            refuted = sorted(set(claims) - live[index])
            rivals = {}
            for hid in proposals:
                agreement = {r: sum(1 for a, b in zip(by_id[hid].predictions, by_id[r].predictions) if a == b)
                             for r in refuted}
                rivals[hid] = sorted(refuted, key=lambda r: (-agreement[r], r))
            experiment = design_tool_experiment(index, question.target_variable_id, tested, proposals, claims,
                                                world, controls, initial, materializer.baseline,
                                                tuple(known_tools), frozenset(already_run), rivals)
            if experiment is not None:
                break
        if not needing:
            break
        if experiment is None:
            for index in needing:
                journal.append("tool_search_failed", questions[index].target_observable_id,
                               {"reason": "no_informative_press_pattern",
                                "target_observable_id": questions[index].target_observable_id})
            break
        tool = experiment.tool
        journal.append("tool_reused" if experiment.reused else "tool_designed", tool.tool_id, {
            "arm_id": experiment.arm_id, "control_id": experiment.control_id,
            "expected_split_pairs": experiment.expected_split_pairs,
            "risky_for_proposals": experiment.risky_for_proposals,
            "severity_against_refuted": experiment.severity_against_refuted,
            "target_observable_id": questions[experiment.question_index].target_observable_id,
            "tool": tool.canonical()})
        claims_by_id = {claim.claim_id: claim for question in questions for claim in question.claims}
        sealed = {}
        for index, alive in enumerate(live):
            for hid in sorted(alive):
                value = predict_target(claims_by_id[hid], {}, tool.horizon, materializer.baseline, initial,
                                       experiment.schedule)
                sealed[hid] = (ObservablePrediction(tool.horizon, questions[index].target_observable_id, value),)
        tool_arms.append(experiment.arm_id)
        already_run.add((tool.tool_id, experiment.control_id))
        if not seal_execute_compare(experiment.arm_id, experiment.spec, sealed, {}):
            termination = HARNESS_FAILURE
            break
        if tool not in known_tools:
            known_tools.append(tool)
        tools_used.append({"arm_id": experiment.arm_id, "control_id": experiment.control_id,
                           "reused": experiment.reused, "tool": tool.canonical(), "tool_id": tool.tool_id})

    return _finish(world, controls, tuple(questions), tuple(sets), tuple(live), plan, tuple(executed),
                   discovery_count, validated_fully, termination, journal, evidence, materializer.baseline,
                   frozenset(noticed), tuple(observation_arms), initial, tuple(tool_arms), tuple(tools_used))


def _finish(world, controls, questions, sets, live, plan, executed, discovery_count, validated_fully, termination,
            journal, evidence, baseline, noticed, observation_arms, initial, tool_arms=(), tools_used=()
            ) -> BlindResearchOutcome:
    outcomes: list[QuestionOutcome] = []
    final_hypotheses: list[CausalHypothesis] = []
    unresolved: list[str] = []
    for question, hypothesis_set, alive in zip(questions, sets, live):
        # A noticed hypothesis no later experiment tested is a proposal, not
        # an answer: it cannot make a question SOLVED or INSEPARABLE.
        proposals = frozenset(h for h in alive if h in noticed and not evidence[h])
        tested = alive - proposals
        tied = _tied_pairs(hypothesis_set, tested, plan) if len(tested) >= 2 else ()
        verdict = _verdict(tested, tied)
        all_ids = [h.hypothesis_id for h in hypothesis_set.hypotheses]
        limitation = assess_limitation(question, verdict, tied if verdict == INSEPARABLE else (), world,
                                       controls, plan, baseline).canonical()
        if proposals and verdict == NO_SURVIVOR:
            limitation = {**limitation, "diagnosis": "proposal_untested"}
        journal.append("limitation_assessed", question.target_observable_id, limitation)
        outcomes.append(QuestionOutcome(
            question.target_observable_id, verdict,
            tuple(sorted(tested)), tuple(sorted(set(all_ids) - alive)),
            tied if verdict == INSEPARABLE else (), limitation, tuple(sorted(proposals))))
        for hypothesis in hypothesis_set.hypotheses:
            hid = hypothesis.hypothesis_id
            if hid not in alive:
                status = _REJECTED
            elif hid in proposals or not executed:
                status = "untested"
                unresolved.append(hid)
            elif verdict == SOLVED:
                status = "supported"
            else:
                status = "underspecified"
                unresolved.append(hid)
            final_hypotheses.append(replace(hypothesis, status=status, evidence=tuple(evidence[hid])))
    final_set = CausalHypothesisSet(
        _digest({"alias_world_id": world.alias_world_id, "format": FORMAT,
                 "questions": [s.subject_digest for s in sets]}),
        tuple(final_hypotheses))
    seal = seal_final_discovery(journal, world.alias_world_id, final_set, tuple(unresolved))
    return BlindResearchOutcome(world.alias_world_id, termination, tuple(outcomes), executed, discovery_count,
                                validated_fully, len(plan.candidates), final_set, seal, observation_arms,
                                tuple(sorted((initial or {}).items())), tool_arms, tools_used)
