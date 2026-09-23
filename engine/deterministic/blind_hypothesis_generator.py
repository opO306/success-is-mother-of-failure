"""G7.3b-2: B builds its own space of competing causal claims from the
public blind interface alone.

Input is exactly three B-facing values -- `BlindWorldDescriptor`, the
world's `BlindControlDescriptor`s, and its `BlindObservableDescriptor`s --
and nothing else. The descriptor by itself is not enough: it exposes only
bare alias strings (`public_controls`/`public_observables`), and the
`alias_variable_id` link saying "this control and that observable are the
same variable" lives only on the per-control/per-observable descriptors
(G7.1 alias-model repair). A generator given only the descriptor could not
tell which variables it can pin, so it takes both, and checks they describe
the same world rather than trusting the caller.

What this module never receives, by type: `SyntheticWorldSpec`,
`BlindTranslationManifest`, `SyntheticResearchAdapter`, any real run. It
imports nothing from `blind_evaluator`, `blind_synthetic_executor`,
`synthetic_runtime`, or `ground_truth` -- see
`tests/test_deterministic_blind_hypothesis.py`'s transitive dependency test,
which follows every import from this module down, not just its direct ones.

The generator is not trying to guess the answer. It enumerates every claim
the G7.3b-1 vocabulary (`blind_hypothesis.py`) can state about each
observable, restricted to causes B can actually pin, and stops. One
question per target observable: hypotheses about different targets predict
different observables, so putting them in one competing set would make G6d
count every cross-target pair as a "disagreement" no experiment resolves.

Enumeration is ordered by sorted alias ids only, never by set/dict
iteration order, so the same interface yields the same space in any process
(the tests check this across different PYTHONHASHSEED values).
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from itertools import combinations, permutations

from .blind_hypothesis import (
    CONDITIONAL, DIRECT, DISJUNCTIVE, INVERTED, MEDIATED, NO_EFFECT, BlindCausalClaim,
)
from .blind_session import BlindControlDescriptor, BlindObservableDescriptor, BlindWorldDescriptor

FORMAT = "blind-hypothesis-space-v1"

DEFAULT_MAX_CLAIMS_PER_QUESTION = 256


def _digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class HypothesisSpaceBudgetExceeded(ValueError):
    """Raised instead of truncating: a silently cut hypothesis space would
    make "B never considered the right claim" indistinguishable from "B
    considered it and ruled it out"."""

    def __init__(self, target_observable_id: str, requested: int, budget: int) -> None:
        super().__init__(f"question on {target_observable_id} needs {requested} claims, over the budget of {budget}")
        self.target_observable_id = target_observable_id
        self.requested = requested
        self.budget = budget


@dataclass(frozen=True)
class BlindQuestion:
    """"What determines this observable?" and every claim B holds open about it."""
    target_observable_id: str
    target_variable_id: str
    claims: tuple[BlindCausalClaim, ...]

    def __post_init__(self) -> None:
        if len(self.claims) < 2:
            raise ValueError("a question needs at least two competing claims")
        ids = [claim.claim_id for claim in self.claims]
        if len(set(ids)) != len(ids):
            raise ValueError("claims must be unique")
        if any(claim.target_variable_id != self.target_variable_id for claim in self.claims):
            raise ValueError("every claim in a question must be about its target variable")

    def canonical(self) -> dict[str, object]:
        return {"claims": [claim.canonical() for claim in self.claims],
                "target_observable_id": self.target_observable_id,
                "target_variable_id": self.target_variable_id}


@dataclass(frozen=True)
class BlindHypothesisSpace:
    """Every question B can pose about one alias world.

    `untestable_observable_ids` lists observables no pinnable variable
    could possibly affect (only NO_EFFECT is statable) -- recorded rather
    than dropped, so "B asked nothing about O3" is visible as a consequence
    of the interface, not an omission.
    """
    alias_world_id: str
    questions: tuple[BlindQuestion, ...]
    untestable_observable_ids: tuple[str, ...]
    format: str = FORMAT

    @property
    def digest(self) -> str:
        return _digest(self.canonical())

    def canonical(self) -> dict[str, object]:
        return {"alias_world_id": self.alias_world_id, "format": self.format,
                "questions": [question.canonical() for question in self.questions],
                "untestable_observable_ids": list(self.untestable_observable_ids)}


def validate_blind_interface(
    world: BlindWorldDescriptor,
    controls: tuple[BlindControlDescriptor, ...],
    observables: tuple[BlindObservableDescriptor, ...],
) -> None:
    """Reject anything that is not the blind interface of one world.

    Type checks are explicit (`TypeError`) so a real `SyntheticWorldSpec`
    handed in by mistake fails loudly here instead of half-working through
    duck typing -- both have `public_controls`/`public_observables`.
    """
    if not isinstance(world, BlindWorldDescriptor):
        raise TypeError(f"world must be a BlindWorldDescriptor, got {type(world).__name__}")
    if not isinstance(controls, tuple) or not all(isinstance(c, BlindControlDescriptor) for c in controls):
        raise TypeError("controls must be a tuple of BlindControlDescriptor")
    if not isinstance(observables, tuple) or not all(isinstance(o, BlindObservableDescriptor) for o in observables):
        raise TypeError("observables must be a tuple of BlindObservableDescriptor")
    if sorted(c.alias_control_id for c in controls) != sorted(world.public_controls):
        raise ValueError("control descriptors do not match the world's public controls")
    if sorted(o.alias_observable_id for o in observables) != sorted(world.public_observables):
        raise ValueError("observable descriptors do not match the world's public observables")
    known = set(world.variables)
    for item in (*controls, *observables):
        if item.alias_variable_id not in known:
            raise ValueError(f"descriptor names variable {item.alias_variable_id!r}, not declared by this world")
    pinned_variables = [c.alias_variable_id for c in controls]
    if len(set(pinned_variables)) != len(pinned_variables):
        raise ValueError("two controls pin the same variable; pinning semantics would be ambiguous")


def _claims_for(target: str, pinnable: tuple[str, ...]) -> tuple[BlindCausalClaim, ...]:
    causes = tuple(v for v in pinnable if v != target)
    claims = [BlindCausalClaim(NO_EFFECT, target)]
    for cause in causes:
        claims.append(BlindCausalClaim(DIRECT, target, (cause,)))
        claims.append(BlindCausalClaim(INVERTED, target, (cause,)))
    for pair in combinations(causes, 2):
        claims.append(BlindCausalClaim(CONDITIONAL, target, pair))
        claims.append(BlindCausalClaim(DISJUNCTIVE, target, pair))
    for cause, mediator in permutations(causes, 2):
        claims.append(BlindCausalClaim(MEDIATED, target, (cause,), mediator))
    return tuple(claims)


@dataclass(frozen=True)
class BlindHypothesisGenerator:
    max_claims_per_question: int = DEFAULT_MAX_CLAIMS_PER_QUESTION

    def generate(
        self,
        world: BlindWorldDescriptor,
        controls: tuple[BlindControlDescriptor, ...],
        observables: tuple[BlindObservableDescriptor, ...],
    ) -> BlindHypothesisSpace:
        validate_blind_interface(world, controls, observables)
        pinnable = tuple(sorted(c.alias_variable_id for c in controls))
        questions: list[BlindQuestion] = []
        untestable: list[str] = []
        for observable in sorted(observables, key=lambda o: o.alias_observable_id):
            claims = _claims_for(observable.alias_variable_id, pinnable)
            if len(claims) > self.max_claims_per_question:
                raise HypothesisSpaceBudgetExceeded(observable.alias_observable_id, len(claims),
                                                    self.max_claims_per_question)
            if len(claims) < 2:
                untestable.append(observable.alias_observable_id)
                continue
            questions.append(BlindQuestion(observable.alias_observable_id, observable.alias_variable_id, claims))
        return BlindHypothesisSpace(world.alias_world_id, tuple(questions), tuple(untestable))
