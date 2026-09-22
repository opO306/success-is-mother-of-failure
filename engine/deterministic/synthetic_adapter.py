"""G6c-3: the `ResearchWorldAdapter` for `SyntheticWorldSpec` -- same shape as
`PhysicalCausalResearchAdapter`, evaluating `ObservablePrediction` instead of
physical A's five kind-dispatch predictions.
"""
from __future__ import annotations

from dataclasses import dataclass, replace

from .causal_executor import ExecutionResult
from .research_adapter import PredictionEvaluation, WorldObservation
from .research_axis import AxisDefinition, AxisRegistry
from .research_observable_prediction import ObservablePrediction
from .research_world import (
    InvalidControlValueError,
    ResearchWorldSpec,
    UnsupportedPredictionError,
    WorldCompatibilityError,
)
from .synthetic_spec import SyntheticClamp, SyntheticRun, SyntheticWorldSpec

# `_point_domain` (broad_explorer.py) validates every candidate's constraint
# axes against an AxisRegistry -- CAUSAL_AXIS_REGISTRY only knows physical
# A's axes, so a synthetic sweep needs its own. Extend this tuple (never
# reuse an id) as more synthetic variables need controls.
SYNTHETIC_AXIS_REGISTRY = AxisRegistry((
    AxisDefinition("axis.synthetic.x1", "integer", ("eq", "set"), "spec", "synthetic_variable_v1"),
    AxisDefinition("axis.synthetic.x2", "integer", ("eq", "set"), "spec", "synthetic_variable_v1"),
    AxisDefinition("axis.synthetic.x3", "integer", ("eq", "set"), "spec", "synthetic_variable_v1"),
))


@dataclass(frozen=True, order=True)
class SyntheticControlDefinition:
    """The synthetic-world analogue of `exploration_control.ControlDefinition`.

    `variable_id` names which of the spec's own variables this control
    clamps -- always a member of `public_controls`, never a raw internal
    detail like a rule id. `control_id`/`research_axis` are anonymous
    identifiers (`CTRL-X1`, `axis.synthetic.x1`), matching the "no leaking
    names" rule the whole synthetic-world package follows.
    """
    control_id: str
    research_axis: str
    variable_id: str

    def canonical(self) -> dict[str, object]:
        return {"control_id": self.control_id, "research_axis": self.research_axis,
                "variable_id": self.variable_id}


_CONTROL_VALUE_TO_MODE = {1: "ON", 0: "OFF", None: "FREE"}


def _assert_synthetic_world_spec(spec: ResearchWorldSpec) -> SyntheticWorldSpec:
    if not isinstance(spec, SyntheticWorldSpec):
        raise WorldCompatibilityError(
            f"SyntheticResearchAdapter requires a SyntheticWorldSpec, got {type(spec).__name__}")
    return spec


class SyntheticResearchAdapter:
    """The `ResearchWorldAdapter` for `SyntheticWorldSpec` -- the only adapter for synthetic A."""

    adapter_id = "synthetic-research-v1"

    def assert_compatible(self, spec: ResearchWorldSpec) -> None:
        _assert_synthetic_world_spec(spec)

    def validate(self, spec: ResearchWorldSpec) -> ResearchWorldSpec:
        synthetic_spec = _assert_synthetic_world_spec(spec)
        return SyntheticWorldSpec.from_mapping(synthetic_spec.canonical())

    def apply_control(self, spec: ResearchWorldSpec, control: SyntheticControlDefinition,
                      value: object) -> ResearchWorldSpec:
        """`value` is `0`/`1`/`None` -- `int`, not `bool`, so this can be swept
        via `SweepDimension` (`exploration_space.py` rejects `bool` values
        outright, matching the physical adapter's own controls, which are
        all `int`-valued too)."""
        synthetic_spec = _assert_synthetic_world_spec(spec)
        if not isinstance(control, SyntheticControlDefinition):
            raise WorldCompatibilityError(
                f"SyntheticResearchAdapter requires a SyntheticControlDefinition, got {type(control).__name__}")
        if isinstance(value, bool) or value not in _CONTROL_VALUE_TO_MODE:
            raise InvalidControlValueError(
                f"control {control.control_id!r} only accepts 0/1/None, got {value!r}")
        mode = _CONTROL_VALUE_TO_MODE[value]
        remaining = tuple(c for c in synthetic_spec.clamps if c.variable_id != control.variable_id)
        clamps = remaining if mode == "FREE" else remaining + (SyntheticClamp(control.variable_id, mode),)
        return replace(synthetic_spec, clamps=tuple(sorted(clamps)))

    def initial_observation(self, spec: ResearchWorldSpec) -> WorldObservation:
        synthetic_spec = _assert_synthetic_world_spec(spec)
        clamped_initial = {name: value for name, value in synthetic_spec.initial_values}
        for control in synthetic_spec.public_controls:
            mode = synthetic_spec.clamp_for(control)
            if mode == "ON":
                clamped_initial[control] = True
            elif mode == "OFF":
                clamped_initial[control] = False
        observables = {name: clamped_initial[name] for name in synthetic_spec.public_observables}
        return WorldObservation(synthetic_spec.digest, 0, observables, synthetic_spec.digest)

    def evaluate_prediction(self, prediction: object, result: ExecutionResult) -> PredictionEvaluation:
        if not isinstance(prediction, ObservablePrediction):
            raise UnsupportedPredictionError(
                f"SyntheticResearchAdapter cannot evaluate prediction type {type(prediction).__name__}")
        expected = prediction.canonical()
        if result.run is None:
            return PredictionEvaluation("unavailable", expected, None, reason="execution failed")
        # A non-SyntheticRun (e.g. a physical CausalRun reaching this adapter
        # through mismatched wiring) has no checkpoint_at, so without this
        # check it would fail with a bare AttributeError -- made explicit
        # instead, same discipline as PhysicalCausalResearchAdapter's
        # isinstance(result.run, CausalRun) check (G6a.1).
        if not isinstance(result.run, SyntheticRun):
            raise WorldCompatibilityError(
                f"SyntheticResearchAdapter requires a SyntheticRun, got {type(result.run).__name__}")
        checkpoint = result.run.checkpoint_at(prediction.tick)
        if checkpoint is None:
            return PredictionEvaluation("unavailable", expected, None,
                                        reason=f"no checkpoint at tick {prediction.tick}")
        observed_value = checkpoint.value_of(prediction.observable_id)
        if observed_value is None:
            raise UnsupportedPredictionError(
                f"observable {prediction.observable_id!r} is not a variable in this world's checkpoints")
        observed = {"expected_value": observed_value, "kind": "observable_value",
                   "observable_id": prediction.observable_id, "tick": prediction.tick}
        if observed == expected:
            return PredictionEvaluation("match", expected, observed)
        return PredictionEvaluation("mismatch", expected, observed)
