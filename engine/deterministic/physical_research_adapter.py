"""G2: wraps the real A0 physical causal kernel behind the `ResearchWorldAdapter` contract.

This module changes no behavior of the existing physical path. Every method
delegates to the existing function it stands in for:

    apply_control        -> exploration_control.apply_control (unmodified)
    validate              -> CausalWorldSpec.from_mapping(spec.canonical())
                              (the same round-trip broad_explorer.run_exploration
                              already does by hand to catch illegal candidates)
    initial_observation    -> the same fields research_loop.observe() has always
                              read: material_counts, total_energy, momentum,
                              state_digest, all off `initial_causal_state(spec)`
    evaluate_prediction    -> the same kind-dispatch research_loop._observed_value
                              /_predicted_value already implement

See `tests/test_deterministic_physical_research_adapter.py` for the
characterization-equivalence checks against
`tests/test_deterministic_research_world_characterization.py`'s G0 baseline.
"""
from __future__ import annotations

from .causal_executor import ExecutionResult
from .causal_kernel import initial_causal_state
from .causal_spec import CausalWorldSpec
from .exploration_control import ControlDefinition, apply_control
from .research_adapter import PredictionEvaluation, WorldObservation
from .research_world import ResearchWorldSpec, UnsupportedPredictionError, WorldCompatibilityError

_SUPPORTED_PREDICTION_KINDS = frozenset({"state_digest", "conservation", "momentum", "bond_count", "material_counts"})


def _assert_causal_world_spec(spec: ResearchWorldSpec) -> CausalWorldSpec:
    if not isinstance(spec, CausalWorldSpec):
        raise WorldCompatibilityError(
            f"PhysicalCausalResearchAdapter requires a CausalWorldSpec, got {type(spec).__name__}")
    return spec


def _predicted_value(prediction: object) -> object:
    return prediction.canonical()


def _observed_value(prediction: object, result: ExecutionResult) -> object | None:
    """Exactly `research_loop._observed_value`'s kind-dispatch, restated here
    rather than imported, so the adapter has no runtime dependency on
    `research_loop` (which will come to depend on adapters, not the other way
    around, once G3 lands)."""
    if result.run is None:
        return None
    kind = prediction.canonical()["kind"]
    if kind not in _SUPPORTED_PREDICTION_KINDS:
        raise UnsupportedPredictionError(f"PhysicalCausalResearchAdapter cannot evaluate prediction kind {kind!r}")
    checkpoints = {item.tick: item for item in result.run.checkpoints}
    checkpoint = checkpoints.get(prediction.tick)
    if checkpoint is None:
        return None
    if kind == "state_digest":
        return {"expected_digest": checkpoint.state_digest, "kind": "state_digest", "tick": prediction.tick}
    if kind == "conservation":
        return {"expected_total_energy": checkpoint.total_energy, "kind": "conservation", "tick": prediction.tick}
    if kind == "momentum":
        return {"expected_momentum": list(checkpoint.momentum), "kind": "momentum", "tick": prediction.tick}
    if kind == "bond_count":
        return {"expected_bond_count": checkpoint.bonds, "kind": "bond_count", "tick": prediction.tick}
    return {"expected_counts": {str(k): v for k, v in checkpoint.material_counts},
            "kind": "material_counts", "tick": prediction.tick}


class PhysicalCausalResearchAdapter:
    """The `ResearchWorldAdapter` for `CausalWorldSpec` -- the only adapter for A0 physics."""

    adapter_id = "physical-causal-v1"

    def assert_compatible(self, spec: ResearchWorldSpec) -> None:
        _assert_causal_world_spec(spec)

    def validate(self, spec: ResearchWorldSpec) -> ResearchWorldSpec:
        causal_spec = _assert_causal_world_spec(spec)
        return CausalWorldSpec.from_mapping(causal_spec.canonical())

    def apply_control(self, spec: ResearchWorldSpec, control: ControlDefinition, value: object) -> ResearchWorldSpec:
        causal_spec = _assert_causal_world_spec(spec)
        if not isinstance(control, ControlDefinition):
            raise WorldCompatibilityError(
                f"PhysicalCausalResearchAdapter requires a ControlDefinition, got {type(control).__name__}")
        return apply_control(causal_spec, control, value)

    def initial_observation(self, spec: ResearchWorldSpec) -> WorldObservation:
        causal_spec = _assert_causal_world_spec(spec)
        initial = initial_causal_state(causal_spec)
        observables = {
            "material_counts": {str(k): v for k, v in initial.material_counts().items()},
            "total_energy": initial.total_energy(),
            "momentum": list(initial.momentum(causal_spec)),
        }
        return WorldObservation(causal_spec.digest, initial.tick, observables, initial.digest)

    def evaluate_prediction(self, prediction: object, result: ExecutionResult) -> PredictionEvaluation:
        observed = _observed_value(prediction, result)
        expected = _predicted_value(prediction)
        if observed is None:
            return PredictionEvaluation("unavailable", expected, None,
                                        reason="execution failed or predicted tick has no checkpoint")
        if observed == expected:
            return PredictionEvaluation("match", expected, observed)
        return PredictionEvaluation("mismatch", expected, observed)
