"""G7.3b-1: the vocabulary a blind B session may use to state a causal claim.

This module fixes *what a claim can say*, not which claims get made (that is
`blind_hypothesis_generator.py`) and not what a claim predicts for a given
experiment in `ResearchPrediction` form (that is
`blind_prediction_materializer.py`). A `BlindCausalClaim` names only alias
variable ids -- there is no field that could hold a real variable name,
world id, or rule id, and nothing in this module imports `blind_evaluator`,
`blind_synthetic_executor`, `synthetic_runtime`, or `ground_truth`.

Why claims are a separate type from `CausalHypothesis`: a `CausalHypothesis`
must already hold a non-empty `predictions` tuple at construction, and
predictions depend on which experiments B plans to run. A claim is the
structural statement ("V1 -> V3") that exists *before* any experiment plan;
the materializer turns one claim into one `CausalHypothesis` once the plan
is known.

Every claim is a *complete* structural equation for one target variable,
not a bare edge. "V1 does not affect V3" on its own says what V3 does *not*
depend on, but not what value V3 takes -- and G6d's
`rank_discriminating_candidates` compares per-candidate predicted values,
not contrasts between two runs. So each kind below commits to a value for
the target under every intervention:

    NO_EFFECT      t := baseline                     (nothing B controls moves t)
    DIRECT         t := c
    INVERTED       t := NOT c
    CONDITIONAL    t := c AND g                      (c moves t only while g holds)
    DISJUNCTIVE    t := c OR g
    MEDIATED       t := m,  m := c  (m controllable) (c moves t only through m)

INVERTED and DISJUNCTIVE are deliberate additions beyond the four kinds
first sketched for G7.3b (DIRECT/NO_EFFECT/CONDITIONAL/MEDIATED). Those four
happen to line up one-to-one with the three benchmark worlds' true
structures (direct / AND-gate / chain) plus a null -- a vocabulary that is
exactly the answer menu turns "B found the right structure" into "B picked
from a list of the right structures". The two extra kinds are the nearest
competing forms (a negated edge; an OR instead of an AND) so that a correct
final answer has to beat structurally similar wrong ones. This is a partial
mitigation, not a proof the vocabulary is answer-neutral: it was still
written by someone who knows the three worlds.

Declared modeling assumptions (B's prior, not facts about any world):

  * Interface: pinning a control to 1/0 pins its variable to True/False for
    the whole run; leaving it out of `control_values` leaves the variable to
    the world. This is `BlindCandidateSpec`'s public contract.
  * Baseline: a variable no pinned control and no modeled mechanism
    determines takes `baseline` (default False). Real worlds whose unforced
    variables sit at True contradict every claim at once -- that is a model
    class failure G7.3c must report, not something to tune away.
  * Steady state: claims are timeless equations evaluated at the final tick.
    A world whose causal chain is longer than its tick count shows lag this
    vocabulary cannot express -- and it does not fail loudly. Measured on
    WORLD-S03 (x1 -> x2 -> x3) observed at tick 1: every candidate is
    explained by the *wrong* claim "x2 -> x3", which survives alone, because
    an unpinned x2 has not yet picked up x1 by tick 1 and so looks like a
    baseline-False root. Pinned by a test in
    `tests/test_deterministic_blind_hypothesis.py` so the limitation cannot
    be forgotten.
  * Only controllable causes and controllable mediators appear. A cause B
    cannot pin can never be separated from NO_EFFECT by any experiment, and
    a mediator B cannot pin makes MEDIATED observationally identical to
    DIRECT on the target -- both would be permanent ties in G6d, not
    hypotheses B could ever test.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Mapping

FORMAT = "blind-causal-claim-v1"

NO_EFFECT = "NO_EFFECT"
DIRECT = "DIRECT"
INVERTED = "INVERTED"
CONDITIONAL = "CONDITIONAL"
DISJUNCTIVE = "DISJUNCTIVE"
MEDIATED = "MEDIATED"

BLIND_HYPOTHESIS_KINDS = (NO_EFFECT, DIRECT, INVERTED, CONDITIONAL, DISJUNCTIVE, MEDIATED)

_CAUSE_COUNT = {NO_EFFECT: 0, DIRECT: 1, INVERTED: 1, CONDITIONAL: 2, DISJUNCTIVE: 2, MEDIATED: 1}


def _digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _text(value: object, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{context} must be non-empty text")
    return value


@dataclass(frozen=True)
class BlindCausalClaim:
    """One complete structural equation for `target_variable_id`, in alias terms.

    `cause_variable_ids` is sorted for the two-cause kinds: `c AND g` and
    `g AND c` predict identically under every intervention, so storing both
    orders would only give G6d a pair of hypotheses it can never separate.
    """
    kind: str
    target_variable_id: str
    cause_variable_ids: tuple[str, ...] = ()
    mediator_variable_id: str | None = None
    format: str = FORMAT

    def __post_init__(self) -> None:
        if self.kind not in BLIND_HYPOTHESIS_KINDS:
            raise ValueError(f"unsupported blind hypothesis kind {self.kind!r}")
        _text(self.target_variable_id, "target_variable_id")
        if not isinstance(self.cause_variable_ids, tuple):
            raise ValueError("cause_variable_ids must be a tuple")
        for cause in self.cause_variable_ids:
            _text(cause, "cause_variable_ids entry")
        if len(self.cause_variable_ids) != _CAUSE_COUNT[self.kind]:
            raise ValueError(f"{self.kind} takes exactly {_CAUSE_COUNT[self.kind]} cause(s)")
        if len(set(self.cause_variable_ids)) != len(self.cause_variable_ids):
            raise ValueError("cause_variable_ids must not repeat")
        if list(self.cause_variable_ids) != sorted(self.cause_variable_ids):
            raise ValueError("cause_variable_ids must be sorted")
        if self.target_variable_id in self.cause_variable_ids:
            raise ValueError("a variable cannot be its own cause")
        if (self.kind == MEDIATED) != (self.mediator_variable_id is not None):
            raise ValueError("mediator_variable_id is required for MEDIATED and forbidden otherwise")
        if self.mediator_variable_id is not None:
            _text(self.mediator_variable_id, "mediator_variable_id")
            if self.mediator_variable_id == self.target_variable_id or \
                    self.mediator_variable_id in self.cause_variable_ids:
                raise ValueError("mediator must differ from target and cause")

    def variable_ids(self) -> tuple[str, ...]:
        """Every alias variable id this claim names."""
        extra = (self.mediator_variable_id,) if self.mediator_variable_id is not None else ()
        return (self.target_variable_id, *self.cause_variable_ids, *extra)

    @property
    def digest(self) -> str:
        return _digest(self.canonical())

    @property
    def claim_id(self) -> str:
        return f"BH-{self.digest[:16]}"

    def canonical(self) -> dict[str, object]:
        return {
            "cause_variable_ids": list(self.cause_variable_ids),
            "format": self.format,
            "kind": self.kind,
            "mediator_variable_id": self.mediator_variable_id,
            "target_variable_id": self.target_variable_id,
        }

    def statement(self) -> str:
        t, causes, m = self.target_variable_id, self.cause_variable_ids, self.mediator_variable_id
        if self.kind == NO_EFFECT:
            return f"no controllable variable affects {t}"
        if self.kind == DIRECT:
            return f"{causes[0]} -> {t}"
        if self.kind == INVERTED:
            return f"NOT {causes[0]} -> {t}"
        if self.kind == CONDITIONAL:
            return f"{causes[0]} AND {causes[1]} -> {t}"
        if self.kind == DISJUNCTIVE:
            return f"{causes[0]} OR {causes[1]} -> {t}"
        return f"{causes[0]} -> {m} -> {t}"


def predict_target(claim: BlindCausalClaim, pinned: Mapping[str, bool], baseline: bool = False) -> bool:
    """The target's value under `pinned` (alias variable id -> forced value),
    according to `claim` alone. See the module docstring for the baseline
    and steady-state assumptions this encodes."""
    if claim.target_variable_id in pinned:
        return pinned[claim.target_variable_id]

    def value(variable_id: str) -> bool:
        return pinned.get(variable_id, baseline)

    causes = claim.cause_variable_ids
    if claim.kind == NO_EFFECT:
        return baseline
    if claim.kind == DIRECT:
        return value(causes[0])
    if claim.kind == INVERTED:
        return not value(causes[0])
    if claim.kind == CONDITIONAL:
        return value(causes[0]) and value(causes[1])
    if claim.kind == DISJUNCTIVE:
        return value(causes[0]) or value(causes[1])
    mediator = claim.mediator_variable_id
    return pinned[mediator] if mediator in pinned else value(causes[0])
