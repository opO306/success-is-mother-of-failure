"""Experiment portfolios and sealed predictions for the B0 research loop.

An arm distinguishes three specs on purpose: `intended_spec` (what B meant to
test), `submitted_spec` (what was actually handed to the executor), and
whatever `ExecutionResult.executed_spec_digest` reports back. If any of the
three digests differ, that is process drift worth an `AccidentRecord` --
independent of whether the *result* was also surprising (an `AnomalyRecord`).
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Mapping

from .causal_spec import CausalWorldSpec

FORMAT = "causal-experiment-v1"


def _digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _text(value: str, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{context} must be non-empty text")
    return value


def _texts(values: tuple[str, ...], context: str, allow_empty: bool = True) -> tuple[str, ...]:
    if not isinstance(values, tuple):
        raise ValueError(f"{context} must be a tuple")
    result = tuple(_text(value, context) for value in values)
    if not allow_empty and not result:
        raise ValueError(f"{context} cannot be empty")
    if len(set(result)) != len(result):
        raise ValueError(f"{context} values must be unique")
    return result


@dataclass(frozen=True)
class CausalExperimentArm:
    """One concrete world to run, naming which physical dimension it varies.

    `intended_spec` and `submitted_spec` are compared by digest at seal time;
    the research loop compares `submitted_spec.digest` against whatever the
    executor reports as `executed_spec_digest` after the run. Three points of
    possible drift, each meaningful on its own: intent-vs-submission is an
    experiment-preparation accident, submission-vs-execution is an executor
    problem.
    """
    arm_id: str
    dimension: str
    intended_spec: CausalWorldSpec
    submitted_spec: CausalWorldSpec
    resolves_hypothesis_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        _text(self.arm_id, "arm_id")
        _text(self.dimension, "dimension")
        _texts(self.resolves_hypothesis_ids, "resolves_hypothesis_ids", allow_empty=False)

    @property
    def intent_matches_submission(self) -> bool:
        return self.intended_spec.digest == self.submitted_spec.digest

    def canonical(self) -> dict[str, object]:
        return {
            "arm_id": self.arm_id, "dimension": self.dimension,
            "intended_spec_digest": self.intended_spec.digest,
            "resolves_hypothesis_ids": list(self.resolves_hypothesis_ids),
            "submitted_spec_digest": self.submitted_spec.digest,
        }


@dataclass(frozen=True)
class CausalExperimentPortfolio:
    """A set of arms probing several physical dimensions at once, not one experiment.

    `coverage` records which declared dimensions this portfolio actually
    varies, so "how many arms ran" never substitutes for "how many distinct
    physical axes were tested" -- see docs/README/04 on why breadth of
    conditions matters more than experiment count.
    """
    portfolio_id: str
    target_hypothesis_ids: tuple[str, ...]
    arms: tuple[CausalExperimentArm, ...]
    coverage: Mapping[str, bool]

    def __post_init__(self) -> None:
        _text(self.portfolio_id, "portfolio_id")
        _texts(self.target_hypothesis_ids, "target_hypothesis_ids", allow_empty=False)
        arm_ids = [item.arm_id for item in self.arms]
        if not arm_ids or len(set(arm_ids)) != len(arm_ids):
            raise ValueError("arm ids must be unique and non-empty")
        declared = {item.dimension for item in self.arms}
        if set(self.coverage) != declared:
            raise ValueError("coverage keys must match exactly the arms' declared dimensions")

    @property
    def digest(self) -> str:
        return _digest(self.canonical())

    def canonical(self) -> dict[str, object]:
        return {
            "arms": [x.canonical() for x in self.arms],
            "coverage": dict(sorted(self.coverage.items())), "format": FORMAT,
            "portfolio_id": self.portfolio_id,
            "target_hypothesis_ids": list(self.target_hypothesis_ids),
        }


@dataclass(frozen=True)
class PredictionSeal:
    """What each hypothesis predicts for one arm, fixed before execution.

    `sealed_at_seq` names the journal sequence number the seal was appended
    at, not a wall-clock time: the research property that matters is "this
    came before the execution record in the journal", which a sequence number
    guarantees and a timestamp does not (clock skew, retries, replay).
    """
    seal_id: str
    arm_id: str
    sealed_at_seq: int
    predictions_by_hypothesis: Mapping[str, tuple[object, ...]]

    def __post_init__(self) -> None:
        _text(self.seal_id, "seal_id")
        _text(self.arm_id, "arm_id")
        if isinstance(self.sealed_at_seq, bool) or not isinstance(self.sealed_at_seq, int) or self.sealed_at_seq < 0:
            raise ValueError("sealed_at_seq must be a nonnegative integer")
        if not self.predictions_by_hypothesis:
            raise ValueError("a seal must predict for at least one hypothesis")
        for hypothesis_id, predictions in self.predictions_by_hypothesis.items():
            _text(hypothesis_id, "predictions_by_hypothesis key")
            if not predictions:
                raise ValueError(f"hypothesis {hypothesis_id!r} has no sealed predictions")

    @property
    def digest(self) -> str:
        return _digest(self.canonical())

    def canonical(self) -> dict[str, object]:
        return {
            "arm_id": self.arm_id, "format": FORMAT,
            "predictions_by_hypothesis": {
                hypothesis_id: [item.canonical() for item in predictions]
                for hypothesis_id, predictions in sorted(self.predictions_by_hypothesis.items())
            },
            "seal_id": self.seal_id, "sealed_at_seq": self.sealed_at_seq,
        }
