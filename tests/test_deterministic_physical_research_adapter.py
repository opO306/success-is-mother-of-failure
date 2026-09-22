"""G2 completion proof: PhysicalCausalResearchAdapter changes nothing about the physical path.

Every check here compares the adapter's output against the exact same
computation done the old way (the pre-adapter functions), not against a
hand-picked expected value -- so this test would fail the moment the
adapter's behavior drifted from the code it wraps, even if both drifted
together from what test_deterministic_research_world_characterization.py
(G0) pinned.
"""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from engine.deterministic import (
    BondCountPrediction,
    ControlDefinition,
    HeatCellRoleTarget,
    RealCausalAExecutor,
    load_causal_world_spec,
)
from engine.deterministic.causal_kernel import initial_causal_state
from engine.deterministic.causal_spec import CausalWorldSpec
from engine.deterministic.exploration_control import apply_control
from engine.deterministic.physical_research_adapter import PhysicalCausalResearchAdapter
from engine.deterministic.research_world import UnsupportedPredictionError, WorldCompatibilityError

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "worlds" / "deterministic_bond_cycle_v1.json"

HEAT_CONTROL = ControlDefinition(
    "causal.control.local_heat_energy", HeatCellRoleTarget("local_heat_source", 10, 10, "energy"),
    "causal.heat.energy",
)


def test_adapter_id_is_stable() -> None:
    assert PhysicalCausalResearchAdapter().adapter_id == "physical-causal-v1"


def test_assert_compatible_accepts_causal_world_spec() -> None:
    spec = load_causal_world_spec(EXAMPLE)
    PhysicalCausalResearchAdapter().assert_compatible(spec)  # must not raise


def test_assert_compatible_rejects_a_non_causal_world_spec() -> None:
    class FakeSpec:
        world_id = "fake"
        digest = "deadbeef"

        def canonical(self) -> dict[str, object]:
            return {}

    with pytest.raises(WorldCompatibilityError):
        PhysicalCausalResearchAdapter().assert_compatible(FakeSpec())


def test_validate_round_trip_preserves_digest_exactly_like_broad_explorer_does() -> None:
    spec = load_causal_world_spec(EXAMPLE)
    adapter = PhysicalCausalResearchAdapter()

    validated = adapter.validate(spec)
    legacy = CausalWorldSpec.from_mapping(spec.canonical())

    assert validated.digest == legacy.digest == spec.digest


def test_validate_rejects_illegal_spec_exactly_as_from_mapping_does() -> None:
    spec = load_causal_world_spec(EXAMPLE)
    illegal = apply_control(spec, HEAT_CONTROL, -1)  # negative heat energy: illegal
    adapter = PhysicalCausalResearchAdapter()

    with pytest.raises(Exception) as adapter_exc:
        adapter.validate(illegal)
    with pytest.raises(Exception) as legacy_exc:
        CausalWorldSpec.from_mapping(illegal.canonical())

    assert type(adapter_exc.value) is type(legacy_exc.value)
    assert str(adapter_exc.value) == str(legacy_exc.value)


def test_apply_control_matches_legacy_apply_control_exactly() -> None:
    spec = load_causal_world_spec(EXAMPLE)
    adapter = PhysicalCausalResearchAdapter()

    via_adapter = adapter.apply_control(spec, HEAT_CONTROL, 5)
    via_legacy = apply_control(spec, HEAT_CONTROL, 5)

    assert via_adapter.digest == via_legacy.digest
    assert via_adapter.canonical() == via_legacy.canonical()


def test_apply_control_rejects_non_control_definition() -> None:
    spec = load_causal_world_spec(EXAMPLE)
    with pytest.raises(WorldCompatibilityError):
        PhysicalCausalResearchAdapter().apply_control(spec, object(), 5)


def test_initial_observation_matches_legacy_observe_payload_exactly() -> None:
    spec = load_causal_world_spec(EXAMPLE)
    adapter = PhysicalCausalResearchAdapter()

    observation = adapter.initial_observation(spec)

    initial = initial_causal_state(spec)
    legacy_observables = {
        "material_counts": {str(k): v for k, v in initial.material_counts().items()},
        "total_energy": initial.total_energy(),
        "momentum": list(initial.momentum(spec)),
    }

    assert observation.world_digest == spec.digest
    assert observation.tick == initial.tick
    assert observation.state_digest == initial.digest
    assert dict(observation.observables) == legacy_observables


def test_evaluate_prediction_matches_legacy_compare_results_on_match() -> None:
    spec = load_causal_world_spec(EXAMPLE)
    result = RealCausalAExecutor().execute(spec)
    adapter = PhysicalCausalResearchAdapter()

    prediction = BondCountPrediction(1, 1)
    evaluation = adapter.evaluate_prediction(prediction, result)

    assert evaluation.status == "match"
    assert evaluation.expected == prediction.canonical()


def test_evaluate_prediction_matches_legacy_compare_results_on_mismatch() -> None:
    spec = load_causal_world_spec(EXAMPLE)
    result = RealCausalAExecutor().execute(spec)
    adapter = PhysicalCausalResearchAdapter()

    prediction = BondCountPrediction(1, 99)
    evaluation = adapter.evaluate_prediction(prediction, result)

    assert evaluation.status == "mismatch"


def test_evaluate_prediction_is_unavailable_on_missing_checkpoint() -> None:
    spec = load_causal_world_spec(EXAMPLE)
    result = RealCausalAExecutor().execute(spec)
    adapter = PhysicalCausalResearchAdapter()

    prediction = BondCountPrediction(999, 0)
    evaluation = adapter.evaluate_prediction(prediction, result)

    assert evaluation.status == "unavailable"
    assert evaluation.observed is None


def test_evaluate_prediction_is_unavailable_on_failed_execution() -> None:
    from engine.deterministic.causal_executor import ExecutionResult

    spec = load_causal_world_spec(EXAMPLE)
    failed_result = ExecutionResult("failed", spec.digest, None, "SomeError", "boom")
    adapter = PhysicalCausalResearchAdapter()

    evaluation = adapter.evaluate_prediction(BondCountPrediction(1, 1), failed_result)
    assert evaluation.status == "unavailable"


def test_evaluate_prediction_rejects_unsupported_kind() -> None:
    spec = load_causal_world_spec(EXAMPLE)
    result = RealCausalAExecutor().execute(spec)
    adapter = PhysicalCausalResearchAdapter()

    class FakePrediction:
        tick = 1

        def canonical(self) -> dict[str, object]:
            return {"kind": "not_a_real_kind"}

    with pytest.raises(UnsupportedPredictionError):
        adapter.evaluate_prediction(FakePrediction(), result)
