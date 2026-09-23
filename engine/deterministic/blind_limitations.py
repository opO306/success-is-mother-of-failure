"""B's own account of *why* a question ended the way it did -- computed from
B's own claims, never copied from the answer key.

The answer key (`ground_truth/benchmark/`) records why each scenario is hard
(language / observation / intervention limits). Handing those reasons to B
would be an answer leak. Instead B works out what it can from its own
hypotheses, and the evaluator later checks whether B's diagnosis agrees
with the key (the evaluator-side scorer, outside `engine`).

What B can diagnose today, stated exactly:

    observation_horizon   every tied pair would split if B could observe
                          longer -- found by simulating its own claims at
                          horizons beyond the world's limit (no A run)
    not_diagnosable       no tied pair splits at any longer horizon B checked;
                          more time would not help, and B's vocabulary has no
                          way to ask what else would (its claims only name
                          variables it can already pin, so "if I could pin
                          one more variable" is not a question it can pose)
    mixed                 some tied pairs split with more time, some do not
    vocabulary_exhausted  every statable claim was contradicted
    budget_exhausted      the discovery budget ran out with splittable pairs
    none                  solved -- nothing to explain

B-facing: imports only `blind_hypothesis`, `blind_hypothesis_generator`,
`blind_prediction_materializer` and `blind_session` (checked transitively by
the loop's dependency test).
"""
from __future__ import annotations

from dataclasses import dataclass

from .blind_hypothesis import predict_target
from .blind_hypothesis_generator import BlindQuestion
from .blind_prediction_materializer import BlindExperimentPlan
from .blind_session import BlindControlDescriptor, BlindWorldDescriptor

FORMAT = "blind-limitations-v1"
DEFAULT_EXTRA_HORIZONS = 3

OBSERVATION_HORIZON = "observation_horizon"
NOT_DIAGNOSABLE = "not_diagnosable"
MIXED = "mixed"
VOCABULARY_EXHAUSTED = "vocabulary_exhausted"
BUDGET_EXHAUSTED = "budget_exhausted"
NONE = "none"


@dataclass(frozen=True)
class PairAssessment:
    hypothesis_ids: tuple[str, str]
    separable_at_horizon: int | None

    def canonical(self) -> dict[str, object]:
        return {"hypothesis_ids": list(self.hypothesis_ids), "separable_at_horizon": self.separable_at_horizon}


@dataclass(frozen=True)
class LimitationAssessment:
    target_observable_id: str
    diagnosis: str
    pairs: tuple[PairAssessment, ...]
    checked_up_to_horizon: int
    format: str = FORMAT

    def canonical(self) -> dict[str, object]:
        return {"checked_up_to_horizon": self.checked_up_to_horizon, "diagnosis": self.diagnosis,
                "format": self.format, "pairs": [p.canonical() for p in self.pairs],
                "target_observable_id": self.target_observable_id}


def _first_splitting_horizon(claim_a, claim_b, interventions, first: int, last: int, baseline: bool) -> int | None:
    for horizon in range(first, last + 1):
        if any(predict_target(claim_a, pinned, horizon, baseline) != predict_target(claim_b, pinned, horizon, baseline)
               for pinned in interventions):
            return horizon
    return None


def assess_limitation(question: BlindQuestion, verdict: str, tied_pairs: tuple[tuple[str, str], ...],
                      world: BlindWorldDescriptor, controls: tuple[BlindControlDescriptor, ...],
                      plan: BlindExperimentPlan, baseline: bool = False,
                      extra_horizons: int = DEFAULT_EXTRA_HORIZONS) -> LimitationAssessment:
    """`verdict` is the loop's per-question verdict (SOLVED / INSEPARABLE /
    NO_SURVIVOR / OPEN). Longer horizons are checked under the same
    interventions B already planned -- only the observation time changes."""
    last = world.ticks + extra_horizons
    if verdict == "SOLVED":
        return LimitationAssessment(question.target_observable_id, NONE, (), world.ticks)
    if verdict == "NO_SURVIVOR":
        return LimitationAssessment(question.target_observable_id, VOCABULARY_EXHAUSTED, (), world.ticks)
    if verdict == "OPEN":
        return LimitationAssessment(question.target_observable_id, BUDGET_EXHAUSTED, (), world.ticks)
    variable_of = {c.alias_control_id: c.alias_variable_id for c in controls}
    interventions = []
    for candidate in plan.candidates:
        pinned = {variable_of[cid]: bool(value) for cid, value in candidate.control_values}
        if pinned not in interventions:
            interventions.append(pinned)
    claims = {claim.claim_id: claim for claim in question.claims}
    pairs = tuple(PairAssessment((a, b), _first_splitting_horizon(claims[a], claims[b], interventions,
                                                                  world.ticks + 1, last, baseline))
                  for a, b in tied_pairs)
    splittable = [p.separable_at_horizon is not None for p in pairs]
    diagnosis = OBSERVATION_HORIZON if all(splittable) else NOT_DIAGNOSABLE if not any(splittable) else MIXED
    return LimitationAssessment(question.target_observable_id, diagnosis, pairs, last)
