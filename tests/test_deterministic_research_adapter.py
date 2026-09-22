"""G1: existing ControlDefinition must satisfy ResearchControlDefinition with zero code changes.

Also pins WorldObservation/PredictionEvaluation's own canonical shape and
validation, independent of any adapter -- adapters are tested against these
in test_deterministic_physical_research_adapter.py.
"""
from __future__ import annotations

import pytest

from engine.deterministic import ControlDefinition, HeatCellRoleTarget
from engine.deterministic.research_adapter import (
    PredictionEvaluation,
    ResearchControlDefinition,
    WorldObservation,
)

HEAT_CONTROL = ControlDefinition(
    "causal.control.local_heat_energy", HeatCellRoleTarget("local_heat_source", 10, 10, "energy"),
    "causal.heat.energy",
)


def test_control_definition_satisfies_research_control_definition_protocol_unmodified() -> None:
    assert isinstance(HEAT_CONTROL, ResearchControlDefinition)
    assert HEAT_CONTROL.control_id == "causal.control.local_heat_energy"
    assert HEAT_CONTROL.research_axis == "causal.heat.energy"
    assert isinstance(HEAT_CONTROL.canonical(), dict)


def test_world_observation_canonical_shape() -> None:
    obs = WorldObservation("digest-abc", 0, {"total_energy": 6, "momentum": [0, 0]}, "state-digest-xyz")
    canonical = obs.canonical()
    assert canonical == {
        "observables": {"momentum": [0, 0], "total_energy": 6},
        "state_digest": "state-digest-xyz",
        "tick": 0,
        "world_digest": "digest-abc",
    }


def test_prediction_evaluation_rejects_unknown_status() -> None:
    with pytest.raises(ValueError, match="unsupported prediction evaluation status"):
        PredictionEvaluation("nonsense", expected=1, observed=1)


@pytest.mark.parametrize("status", ["match", "mismatch", "unavailable"])
def test_prediction_evaluation_accepts_known_statuses(status: str) -> None:
    evaluation = PredictionEvaluation(status, expected=1, observed=2, reason="example")
    assert evaluation.canonical()["status"] == status
