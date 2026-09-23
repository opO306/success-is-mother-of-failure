"""G6d: choosing which not-yet-run candidate to try next, from disagreement
among B's own live hypotheses -- not from any answer key.

This module adds no new causal-inference machinery. Everything it needs
already exists: `exploration_space.generate_candidates` already enumerates
a plan's full Cartesian product, and `CandidatePredictionProvider.predictions_for`
already returns `Mapping[hypothesis_id, tuple[prediction, ...]]` -- "what
does each live hypothesis predict for this candidate" was already the shape
of that return value (see `research_prediction.py`), so ranking candidates
by how much their hypotheses disagree is a thin read of data the research
loop already produces, not a new inference engine.

`ground_truth/`, `synthetic_runtime.py`, and any real `world_id`/`world_revision`
are never imported here and never need to be: this module only ever sees
candidates, compiled specs, and hypothesis-keyed prediction mappings, all of
which are already caller-supplied by the time `rank_discriminating_candidates`
runs. See `tests/test_deterministic_experiment_designer.py`'s leakage check.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping

from .exploration_space import ExplorationCandidate
from .research_prediction import CandidatePredictionProvider
from .research_world import ResearchWorldSpec

FORMAT = "experiment-designer-v1"


@dataclass(frozen=True, order=True)
class DiscriminatingCandidate:
    """One candidate, scored by how much its live hypotheses disagree.

    `disagreement_pair_count` counts hypothesis *pairs* whose predictions
    differ, not the number of distinct prediction values -- with 4
    hypotheses split 3-1 vs split 2-2 on the same candidate, both produce
    exactly 2 distinct prediction values, but the 2-2 split is the more
    informative experiment (it separates twice as many pairs). Counting
    pairs, not distinct values, is what makes the ranking prefer it.

    `order=True` sorts by field order (`candidate_id` first) for a stable
    tiebreak-by-id if ever compared directly; `rank_discriminating_candidates`
    itself sorts explicitly by (-disagreement_pair_count, candidate_id) so it
    does not depend on this dataclass's own ordering.
    """
    candidate_id: str
    disagreement_pair_count: int
    predictions_by_hypothesis: Mapping[str, tuple[object, ...]]

    def canonical(self) -> dict[str, object]:
        return {
            "candidate_id": self.candidate_id,
            "disagreement_pair_count": self.disagreement_pair_count,
            "format": FORMAT,
            "predictions_by_hypothesis": {
                hypothesis_id: [repr(p) for p in predictions]
                for hypothesis_id, predictions in sorted(self.predictions_by_hypothesis.items())
            },
        }


def _disagreement_pair_count(predictions_by_hypothesis: Mapping[str, tuple[object, ...]]) -> int:
    """Number of hypothesis pairs (Hi, Hj), i < j, whose prediction tuples
    differ under `==` -- deliberately pairwise rather than via a `set()` of
    predictions, so this never requires prediction objects to be hashable
    (frozen dataclasses are, but nothing in this module's contract should
    depend on that)."""
    items = sorted(predictions_by_hypothesis.items())
    count = 0
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            if items[i][1] != items[j][1]:
                count += 1
    return count


def rank_discriminating_candidates(
    candidates: tuple[ExplorationCandidate, ...],
    compiled_specs: Mapping[str, ResearchWorldSpec],
    prediction_provider: CandidatePredictionProvider,
    cost: Callable[[ResearchWorldSpec], int] | None = None,
) -> tuple[DiscriminatingCandidate, ...]:
    """Score every candidate that has a compiled spec, sorted by
    `disagreement_pair_count` descending, then by `cost(spec)` ascending
    when a `cost` is given, then by `candidate_id` ascending (a
    deterministic order independent of dict/set iteration).

    `cost` exists for G7.3b-4: blind candidates carry an observation horizon,
    and at equal discriminating power the shorter observation should win --
    otherwise B would drift toward always running the longest experiment
    available for no evidential gain. Without `cost` the order is exactly
    what it was before, for every existing caller.

    A candidate absent from `compiled_specs` (its control values failed to
    compile -- a `CandidateCompilationFailure` at the caller's level) is
    silently skipped: it was never a legally-formed experiment, so it is
    not a candidate this module can meaningfully score, the same
    "uncompilable is not research data" discipline `broad_explorer.py`
    already applies.

    Candidates with `disagreement_pair_count == 0` are included, not
    dropped -- "no live hypothesis disagrees here" is itself a fact a
    caller (or `select_next_experiment`) may need to see explicitly rather
    than infer from an empty list that could otherwise mean anything.
    """
    scored: list[tuple[DiscriminatingCandidate, int]] = []
    for candidate in candidates:
        spec = compiled_specs.get(candidate.candidate_id)
        if spec is None:
            continue
        predictions_by_hypothesis = prediction_provider.predictions_for(candidate, spec)
        scored.append((DiscriminatingCandidate(
            candidate.candidate_id,
            _disagreement_pair_count(predictions_by_hypothesis),
            predictions_by_hypothesis,
        ), cost(spec) if cost is not None else 0))
    ordered = sorted(scored, key=lambda pair: (-pair[0].disagreement_pair_count, pair[1], pair[0].candidate_id))
    return tuple(item for item, _cost in ordered)


def select_next_experiment(
    ranked: tuple[DiscriminatingCandidate, ...],
    already_executed_candidate_ids: frozenset[str],
) -> DiscriminatingCandidate | None:
    """The highest-ranked not-yet-run candidate that at least one pair of
    live hypotheses actually disagrees on.

    A candidate with `disagreement_pair_count == 0` is never returned, even
    if it is the only not-yet-run candidate left: running it would produce
    no evidence that could favor one live hypothesis over another, so
    selecting it would blur `EXPLORATION_FAILURE` into "B ran something,
    just not something useful" instead of the honest "no discriminating,
    not-yet-run candidate exists" that `None` reports here.
    """
    for candidate in ranked:
        if candidate.disagreement_pair_count <= 0:
            continue
        if candidate.candidate_id in already_executed_candidate_ids:
            continue
        return candidate
    return None
