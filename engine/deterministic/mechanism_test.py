"""B0.5 core types: turning a MechanismCandidate into an executed, discriminating intervention.

`InterventionDefinition` builds on `exploration_control.ControlDefinition`
rather than inventing a second mutation system: a `ControlDefinition` says
"this value can be turned"; an `InterventionDefinition` says "in this
mechanism experiment, turn it to this value, this way". Only operations A's
existing `apply_control` can express (`SET_ONCE`, `CLAMP`, `PULSE`, matching
`divergence_analysis.InterventionRecord`'s modes) are legal -- B0.5 never
invents a physical operation ("remove", "disable") that has no
`apply_control` counterpart.

A `MechanismTestPlan` is only worth running when its competing mechanisms
predict *different* outcomes (docs/README section 56's information-value
principle): `DiscriminatingPrediction` records each mechanism's prediction
explicitly so that requirement is checkable, not assumed.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from .exploration_control import ControlDefinition

FORMAT = "mechanism-test-v1"
INTERVENTION_OPERATIONS = frozenset({"SET_ONCE", "CLAMP", "PULSE"})
EVIDENCE_RELATIONS = frozenset({"SUPPORTS", "CONTRADICTS", "INCONCLUSIVE"})


def _digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _text(value: str, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{context} must be non-empty text")
    return value


def _texts(values: tuple[str, ...], context: str, allow_empty: bool = False) -> tuple[str, ...]:
    if not isinstance(values, tuple):
        raise ValueError(f"{context} must be a tuple")
    result = tuple(_text(value, context) for value in values)
    if not allow_empty and not result:
        raise ValueError(f"{context} cannot be empty")
    if len(set(result)) != len(result):
        raise ValueError(f"{context} values must be unique")
    return result


@dataclass(frozen=True, order=True)
class InterventionDefinition:
    """One control, deliberately set for one mechanism experiment.

    Distinct from `ControlDefinition` (which only says a value *can* be
    turned): this says it *is* turned, to `value`, under `operation`, in the
    arm this experiment builds.
    """
    control_id: str
    control: ControlDefinition
    operation: str
    value: object

    def __post_init__(self) -> None:
        _text(self.control_id, "control_id")
        if self.operation not in INTERVENTION_OPERATIONS:
            raise ValueError(f"unsupported intervention operation {self.operation!r}")
        if self.control.control_id != self.control_id:
            raise ValueError("control_id must match the wrapped ControlDefinition's own control_id")

    def canonical(self) -> dict[str, object]:
        return {"control_id": self.control_id, "format": FORMAT, "operation": self.operation, "value": self.value}


@dataclass(frozen=True, order=True)
class DiscriminatingPrediction:
    """What one mechanism candidate predicts the outcome will be, sealed before execution.

    A `MechanismTestPlan` with fewer than two distinct `outcome_prediction`
    values across its predictions is not discriminating -- see
    `plan_is_discriminating`.
    """
    mechanism_candidate_id: str
    outcome_prediction: str

    def __post_init__(self) -> None:
        _text(self.mechanism_candidate_id, "mechanism_candidate_id")
        _text(self.outcome_prediction, "outcome_prediction")

    def canonical(self) -> dict[str, object]:
        return {"mechanism_candidate_id": self.mechanism_candidate_id, "outcome_prediction": self.outcome_prediction}


@dataclass(frozen=True)
class MechanismTestPlan:
    """Which mechanisms this test tries to discriminate, and how.

    `controls_held_constant` names domains/roles the caller declares are
    unchanged between baseline and intervention -- documentation of intent,
    not itself re-verified here (the actual baseline/contrast specs carry
    that guarantee structurally, by construction).
    """
    plan_id: str
    target_mechanism_id: str
    competing_mechanism_ids: tuple[str, ...]
    interventions: tuple[InterventionDefinition, ...]
    predictions: tuple[DiscriminatingPrediction, ...]
    controls_held_constant: tuple[str, ...]

    def __post_init__(self) -> None:
        _text(self.plan_id, "plan_id")
        _text(self.target_mechanism_id, "target_mechanism_id")
        _texts(self.competing_mechanism_ids, "competing_mechanism_ids")
        if not self.interventions:
            raise ValueError("a mechanism test plan needs at least one intervention")
        mechanism_ids = {self.target_mechanism_id} | set(self.competing_mechanism_ids)
        predicted_ids = {p.mechanism_candidate_id for p in self.predictions}
        if predicted_ids != mechanism_ids:
            raise ValueError("every target and competing mechanism must have exactly one prediction")

    @property
    def is_discriminating(self) -> bool:
        """True only if the plan's mechanisms do not all predict the same outcome."""
        return len({p.outcome_prediction for p in self.predictions}) > 1

    @property
    def digest(self) -> str:
        return _digest(self.canonical())

    def canonical(self) -> dict[str, object]:
        return {"competing_mechanism_ids": list(self.competing_mechanism_ids),
                "controls_held_constant": list(self.controls_held_constant), "format": FORMAT,
                "interventions": [x.canonical() for x in sorted(self.interventions)], "plan_id": self.plan_id,
                "predictions": [x.canonical() for x in sorted(self.predictions,
                                                              key=lambda p: p.mechanism_candidate_id)],
                "target_mechanism_id": self.target_mechanism_id}


@dataclass(frozen=True)
class MechanismTestResult:
    """Raw, uninterpreted outcome of running a `MechanismTestPlan`'s baseline and intervention arms.

    Deliberately carries no verdict: `baseline_outcome`/`intervention_outcome`
    are whatever observable the plan's predictions were phrased in terms of
    (e.g. `"bond_exists_at_tick_2"`), read off the executed runs. Turning
    this into support/contradiction for each mechanism is
    `evaluate_mechanism_test`'s job.
    """
    plan_id: str
    baseline_spec_digest: str
    intervention_spec_digest: str
    baseline_outcome: str
    intervention_outcome: str
    baseline_execution_status: str
    intervention_execution_status: str

    def __post_init__(self) -> None:
        for field_name in ("plan_id", "baseline_spec_digest", "intervention_spec_digest",
                          "baseline_outcome", "intervention_outcome",
                          "baseline_execution_status", "intervention_execution_status"):
            _text(getattr(self, field_name), field_name)

    def canonical(self) -> dict[str, object]:
        return {"baseline_execution_status": self.baseline_execution_status,
                "baseline_outcome": self.baseline_outcome, "baseline_spec_digest": self.baseline_spec_digest,
                "format": FORMAT, "intervention_execution_status": self.intervention_execution_status,
                "intervention_outcome": self.intervention_outcome,
                "intervention_spec_digest": self.intervention_spec_digest, "plan_id": self.plan_id}


@dataclass(frozen=True, order=True)
class MechanismEvidence:
    """One mechanism candidate's verdict from one `MechanismTestResult` -- never proof, only evidence.

    `SUPPORTS` means this test's observation matched what the mechanism
    predicted, nothing stronger: a single supporting test is evidence to
    accumulate, not a confirmed cause (docs/README section 3.2 on
    intervention over correlation still applies -- one intervention is one
    data point).
    """
    mechanism_candidate_id: str
    plan_id: str
    relation: str
    reason: str

    def __post_init__(self) -> None:
        _text(self.mechanism_candidate_id, "mechanism_candidate_id")
        _text(self.plan_id, "plan_id")
        _text(self.reason, "reason")
        if self.relation not in EVIDENCE_RELATIONS:
            raise ValueError(f"unsupported mechanism evidence relation {self.relation!r}")

    def canonical(self) -> dict[str, object]:
        return {"format": FORMAT, "mechanism_candidate_id": self.mechanism_candidate_id, "plan_id": self.plan_id,
                "reason": self.reason, "relation": self.relation}


def evaluate_mechanism_test(plan: MechanismTestPlan, result: MechanismTestResult) -> tuple[MechanismEvidence, ...]:
    """Compare each mechanism's sealed prediction against the actual intervention-arm outcome.

    A mechanism is `INCONCLUSIVE` if either arm's execution failed --
    nothing was actually checked. Otherwise `SUPPORTS` when the mechanism's
    prediction matches `result.intervention_outcome`, `CONTRADICTS` when it
    does not.
    """
    if result.baseline_execution_status != "success" or result.intervention_execution_status != "success":
        return tuple(
            MechanismEvidence(p.mechanism_candidate_id, plan.plan_id, "INCONCLUSIVE",
                              "one or both arms failed to execute; nothing was checked")
            for p in plan.predictions
        )
    evidence = []
    for prediction in plan.predictions:
        if prediction.outcome_prediction == result.intervention_outcome:
            evidence.append(MechanismEvidence(prediction.mechanism_candidate_id, plan.plan_id, "SUPPORTS",
                                              "predicted intervention-arm outcome matched the observed outcome"))
        else:
            evidence.append(MechanismEvidence(prediction.mechanism_candidate_id, plan.plan_id, "CONTRADICTS",
                                              "predicted intervention-arm outcome did not match the observed outcome"))
    return tuple(evidence)
