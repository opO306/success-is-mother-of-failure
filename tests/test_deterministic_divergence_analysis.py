import pytest

from engine.deterministic import (
    KernelPhase,
    TraceSnapshot,
    compare_snapshot_sequences,
)
from engine.deterministic.divergence_analysis import InterventionRecord


def _snap(tick: int, phase: KernelPhase, **values) -> TraceSnapshot:
    return TraceSnapshot(tick, phase, values)


def test_compare_rejects_mismatched_tick_phase_coverage() -> None:
    left = (_snap(0, KernelPhase.PRE_TICK, a={"x": 1}),)
    right = (_snap(0, KernelPhase.POST_TICK, a={"x": 1}),)
    with pytest.raises(ValueError, match="same \\(tick, phase\\) pairs"):
        compare_snapshot_sequences("L", "R", left, right)


def test_no_events_when_traces_are_identical() -> None:
    left = (_snap(0, KernelPhase.PRE_TICK, a={"x": 1}),)
    right = (_snap(0, KernelPhase.PRE_TICK, a={"x": 1}),)
    chain = compare_snapshot_sequences("L", "R", left, right)
    assert chain.events == ()
    assert chain.first_response is None


def test_set_once_intervention_persists_then_becomes_endogenous() -> None:
    left = (
        _snap(0, KernelPhase.PRE_TICK, heat={"energy": 1}),
        _snap(1, KernelPhase.PRE_TICK, heat={"energy": 1}),
        _snap(1, KernelPhase.POST_TICK, heat={"energy": 1}),
    )
    right = (
        _snap(0, KernelPhase.PRE_TICK, heat={"energy": 2}),
        _snap(1, KernelPhase.PRE_TICK, heat={"energy": 2}),
        _snap(1, KernelPhase.POST_TICK, heat={"energy": 0}),  # A consumed it
    )
    interventions = (InterventionRecord("heat", "energy", 1, 2, 0, "SET_ONCE"),)
    chain = compare_snapshot_sequences("L", "R", left, right, interventions)

    origins = {(e.tick, e.phase): e.origin for e in chain.events}
    assert origins[(0, KernelPhase.PRE_TICK)] == "DIRECT_INTERVENTION"
    assert origins[(1, KernelPhase.PRE_TICK)] == "INTERVENTION_PERSISTED"
    assert origins[(1, KernelPhase.POST_TICK)] == "ENDOGENOUS_RESPONSE"
    assert chain.first_response.tick == 1
    assert chain.first_response.phase == KernelPhase.POST_TICK


def test_clamp_intervention_stays_maintained_and_never_becomes_first_response() -> None:
    left = (
        _snap(0, KernelPhase.PRE_TICK, heat={"energy": 1}, other={"v": 5}),
        _snap(1, KernelPhase.PRE_TICK, heat={"energy": 1}, other={"v": 5}),
        _snap(1, KernelPhase.POST_TICK, heat={"energy": 1}, other={"v": 9}),
    )
    right = (
        _snap(0, KernelPhase.PRE_TICK, heat={"energy": 2}, other={"v": 5}),
        _snap(1, KernelPhase.PRE_TICK, heat={"energy": 2}, other={"v": 5}),
        _snap(1, KernelPhase.POST_TICK, heat={"energy": 2}, other={"v": 3}),
    )
    interventions = (InterventionRecord("heat", "energy", 1, 2, 0, "CLAMP"),)
    chain = compare_snapshot_sequences("L", "R", left, right, interventions)

    origins = {(e.tick, e.phase, e.role): e.origin for e in chain.events}
    assert origins[(0, KernelPhase.PRE_TICK, "heat")] == "DIRECT_INTERVENTION"
    assert origins[(1, KernelPhase.PRE_TICK, "heat")] == "INTERVENTION_MAINTAINED"
    assert origins[(1, KernelPhase.POST_TICK, "heat")] == "INTERVENTION_MAINTAINED"
    assert origins[(1, KernelPhase.POST_TICK, "other")] == "ENDOGENOUS_RESPONSE"
    assert chain.first_response.role == "other"


def test_intervention_record_rejects_unsupported_mode() -> None:
    with pytest.raises(ValueError, match="unsupported intervention mode"):
        InterventionRecord("heat", "energy", 1, 2, 0, "TELEPORT")
