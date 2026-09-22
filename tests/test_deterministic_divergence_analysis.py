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
    assert [c.role for c in chain.first_response.changes] == ["heat"]


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
    assert [c.role for c in chain.first_response.changes] == ["other"]


def test_intervention_record_rejects_unsupported_mode() -> None:
    with pytest.raises(ValueError, match="unsupported intervention mode"):
        InterventionRecord("heat", "energy", 1, 2, 0, "TELEPORT")


def test_first_response_moment_groups_simultaneous_changes_never_picks_one() -> None:
    """Several fields responding at the same (tick, phase) must be preserved together --
    never collapsed to a single "first" field by alphabetical (role, field) order.
    """
    left = (
        _snap(0, KernelPhase.PRE_TICK, heat={"energy": 1}, particle_a={"kinetic_energy": 2},
             target_bond={"exists": True}),
        _snap(1, KernelPhase.AFTER_BOND_BREAK_PHASE, heat={"energy": 1}, particle_a={"kinetic_energy": 2},
             target_bond={"exists": True}),
    )
    right = (
        _snap(0, KernelPhase.PRE_TICK, heat={"energy": 2}, particle_a={"kinetic_energy": 2},
             target_bond={"exists": True}),
        _snap(1, KernelPhase.AFTER_BOND_BREAK_PHASE, heat={"energy": 0}, particle_a={"kinetic_energy": 3},
             target_bond={"exists": False}),
    )
    interventions = (InterventionRecord("heat", "energy", 1, 2, 0, "SET_ONCE"),)
    chain = compare_snapshot_sequences("L", "R", left, right, interventions)

    assert chain.first_response is not None
    assert chain.first_response.tick == 1
    assert chain.first_response.phase == KernelPhase.AFTER_BOND_BREAK_PHASE
    responding_roles = {c.role for c in chain.first_response.changes}
    assert responding_roles == {"heat", "particle_a", "target_bond"}


def test_first_response_moment_rejects_mismatched_tick_phase_changes() -> None:
    from engine.deterministic.divergence_analysis import DivergenceEvent, FirstResponseMoment
    e1 = DivergenceEvent(1, KernelPhase.AFTER_BOND_BREAK_PHASE, "a", "x", 1, 2, "STATE", "ENDOGENOUS_RESPONSE")
    e2 = DivergenceEvent(2, KernelPhase.POST_TICK, "b", "y", 1, 2, "STATE", "ENDOGENOUS_RESPONSE")
    with pytest.raises(ValueError, match="share its \\(tick, phase\\)"):
        FirstResponseMoment(1, KernelPhase.AFTER_BOND_BREAK_PHASE, (e1, e2))
