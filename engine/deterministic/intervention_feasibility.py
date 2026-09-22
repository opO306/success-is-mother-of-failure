"""Whether a requested intervention can be legally and unambiguously carried out -- nothing more.

This module answers exactly one question: *can* A be made to do this,
through its existing public control surface? It never asks whether doing so
would be a *good* experiment (that is `ExperimentUtility`, a separate,
later concern) -- conflating the two would let a technically-executable but
uninformative intervention look "ready" in the same sense as a genuinely
discriminating one.

The four outcomes are deliberately distinct failure *reasons*, not degrees
of confidence:

- `INVALID`: the request itself is malformed -- an unregistered control,
  a value outside what the control's target field accepts, or a spec that
  fails `CausalWorldSpec` validation once applied.
- `AMBIGUOUS`: the request's role resolves to more than one subject in the
  base spec, or names an intervention two different controls could equally
  express with no way to prefer one.
- `UNAVAILABLE`: the request is meaningful and would be legal if A exposed
  the right lever, but no existing `ControlDefinition` can independently
  address it -- e.g. suppressing bond removal while keeping heat
  consumption from the same atomic kernel phase.
- `AVAILABLE`: every requested control resolves to exactly one subject, and
  applying all of them together produces a spec that passes validation.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from .causal_spec import CausalWorldSpec
from .exploration_control import ControlDefinition, apply_control

FORMAT = "intervention-feasibility-v1"
FEASIBILITY_STATUSES = frozenset({"AVAILABLE", "UNAVAILABLE", "AMBIGUOUS", "INVALID"})


def _digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _text(value: str, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{context} must be non-empty text")
    return value


@dataclass(frozen=True)
class InterventionFeasibility:
    """The result of checking whether `control_values` can be applied to `base_spec_digest`.

    `resulting_spec_digest` is populated only when `status == "AVAILABLE"`.
    """
    base_spec_digest: str
    control_values: tuple[tuple[str, object], ...]
    status: str
    reason: str
    resulting_spec_digest: str | None = None

    def __post_init__(self) -> None:
        _text(self.base_spec_digest, "base_spec_digest")
        _text(self.reason, "reason")
        if self.status not in FEASIBILITY_STATUSES:
            raise ValueError(f"unsupported feasibility status {self.status!r}")
        if self.status == "AVAILABLE" and not self.resulting_spec_digest:
            raise ValueError("an AVAILABLE feasibility result must carry resulting_spec_digest")
        if self.status != "AVAILABLE" and self.resulting_spec_digest is not None:
            raise ValueError("only an AVAILABLE feasibility result may carry resulting_spec_digest")

    def canonical(self) -> dict[str, object]:
        return {"base_spec_digest": self.base_spec_digest, "control_values": [list(p) for p in self.control_values],
                "format": FORMAT, "reason": self.reason, "resulting_spec_digest": self.resulting_spec_digest,
                "status": self.status}


def assess_intervention_feasibility(
    base_spec: CausalWorldSpec, controls: dict[str, ControlDefinition],
    control_values: tuple[tuple[str, object], ...],
) -> InterventionFeasibility:
    """Attempt to apply every `(control_id, value)` pair to `base_spec` and classify the outcome.

    Never raises: every failure mode this module recognizes is reported as
    a status/reason pair instead, so a caller can journal an infeasible
    request exactly as informatively as a feasible one.
    """
    control_ids = [control_id for control_id, _ in control_values]
    if len(set(control_ids)) != len(control_ids):
        return InterventionFeasibility(base_spec.digest, control_values, "AMBIGUOUS",
                                       "the same control is named more than once in this request")
    unregistered = [control_id for control_id in control_ids if control_id not in controls]
    if unregistered:
        return InterventionFeasibility(base_spec.digest, control_values, "INVALID",
                                       f"unregistered control id(s): {sorted(unregistered)}")

    spec = base_spec
    try:
        for control_id, value in control_values:
            control = controls[control_id]
            control.target.resolve(base_spec)  # raises on 0 or >1 matches
            spec = apply_control(spec, control, value)
        spec = CausalWorldSpec.from_mapping(spec.canonical())
    except ValueError as exc:
        message = str(exc)
        if "ambiguous" in message or "matched" in message and "particles" in message:
            return InterventionFeasibility(base_spec.digest, control_values, "AMBIGUOUS", message)
        return InterventionFeasibility(base_spec.digest, control_values, "INVALID", message)

    return InterventionFeasibility(base_spec.digest, control_values, "AVAILABLE",
                                   "every requested control resolved uniquely and the resulting spec is valid",
                                   spec.digest)
