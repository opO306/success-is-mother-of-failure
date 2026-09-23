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

Every claim is a *complete* update rule for one target variable, not a
bare edge. "V1 does not affect V3" on its own says what V3 does *not*
depend on, but not what value V3 takes -- and G6d's
`rank_discriminating_candidates` compares per-candidate predicted values,
not contrasts between two runs. So each kind commits to the target's value
at tick k+1 from the state at tick k (G7.3b-4 temporal semantics):

    NO_EFFECT      t' := t                            (nothing B controls moves t)
    DIRECT         t' := c
    INVERTED       t' := NOT c
    CONDITIONAL    t' := c AND g                      (c moves t only while g holds)
    DISJUNCTIVE    t' := c OR g
    MEDIATED       t' := m,  m' := c  (m controllable) (c moves t only through m)

(primed = next tick). Variables a claim does not model keep their value.

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
  * Time (G7.3b-4, replacing the earlier steady-state assumption):
      - tick 0 is the initial state: pinned variables at their pinned value,
        every other variable at `baseline`;
      - every tick, all modeled variables update *simultaneously* from the
        previous tick's state -- a change never chains through two
        variables within one tick (x1 -> x2 -> x3 needs 2 ticks to reach
        x3), then pinned variables are re-pinned;
      - a prediction is a value at one exact tick (the experiment's
        observation horizon) and may only be compared with an observation
        at that same tick.
    This is the public tick rule of the A world B studies, not a per-edge
    delay: every edge takes exactly one tick. Per-edge delays, stochastic
    delay, and continuous time are out of scope. The steady-state version
    this replaces made WORLD-S03 (a 2-step chain) observed at tick 1 leave
    the *wrong* claim "x2 -> x3" surviving alone; under tick semantics the
    right claim and "x2 -> x3" predict identically at tick 1 and both
    survive -- an honest tie that only a 2-tick observation can break.
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


def _check_horizon(horizon: object) -> int:
    if isinstance(horizon, bool) or not isinstance(horizon, int) or horizon < 0:
        raise ValueError("horizon must be a nonnegative integer")
    return horizon


def simulate_claim(claim: BlindCausalClaim, pinned: Mapping[str, bool], horizon: int,
                   baseline: bool = False) -> tuple[Mapping[str, bool], ...]:
    """The state of `claim`'s variables at ticks 0..horizon, under `pinned`
    (alias variable id -> forced value), by B's own reading of its own claim
    -- never by running A. See the module docstring's time rules."""
    _check_horizon(horizon)
    state = {v: pinned.get(v, baseline) for v in claim.variable_ids()}
    trajectory = [dict(state)]
    target, causes = claim.target_variable_id, claim.cause_variable_ids
    for _ in range(horizon):
        previous = state
        state = dict(previous)
        if claim.kind == DIRECT:
            state[target] = previous[causes[0]]
        elif claim.kind == INVERTED:
            state[target] = not previous[causes[0]]
        elif claim.kind == CONDITIONAL:
            state[target] = previous[causes[0]] and previous[causes[1]]
        elif claim.kind == DISJUNCTIVE:
            state[target] = previous[causes[0]] or previous[causes[1]]
        elif claim.kind == MEDIATED:
            state[claim.mediator_variable_id] = previous[causes[0]]
            state[target] = previous[claim.mediator_variable_id]
        for variable_id in state:
            if variable_id in pinned:
                state[variable_id] = pinned[variable_id]
        trajectory.append(dict(state))
    return tuple(trajectory)


def predict_target(claim: BlindCausalClaim, pinned: Mapping[str, bool], horizon: int,
                   baseline: bool = False) -> bool:
    """The target's value at exactly tick `horizon`, according to `claim` alone."""
    return simulate_claim(claim, pinned, horizon, baseline)[horizon][claim.target_variable_id]
