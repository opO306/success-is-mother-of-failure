import pytest

from engine.deterministic import KernelPhase, TraceSnapshot
from engine.deterministic.causal_timeline import (
    build_cross_role_timeline,
    extract_state_changes,
    normalize_moments,
)


def _snap(seq, tick, phase, digest, **values):
    return TraceSnapshot(tick, phase, values, digest, seq)


def test_normalize_moments_merges_same_digest_adjacent_snapshots() -> None:
    snapshots = (
        _snap(0, 1, KernelPhase.POST_TICK, "AAA", a={"x": 1}),
        _snap(1, 1, KernelPhase.PRE_TICK, "AAA", a={"x": 1}),
        _snap(2, 1, KernelPhase.AFTER_BOND_BREAK_PHASE, "BBB", a={"x": 2}),
    )
    normalized = normalize_moments(snapshots)
    assert len(normalized) == 2
    assert normalized[0].observation_seq == 1  # later-in-call-order snapshot kept as representative
    assert normalized[1].observation_seq == 2


def test_normalize_moments_never_merges_different_digests_even_if_fields_match() -> None:
    snapshots = (
        _snap(0, 1, KernelPhase.POST_TICK, "AAA", a={"x": 1}),
        _snap(1, 1, KernelPhase.PRE_TICK, "BBB", a={"x": 1}),  # same watched field, different full state
    )
    normalized = normalize_moments(snapshots)
    assert len(normalized) == 2


def test_normalize_moments_never_merges_snapshots_with_empty_digest() -> None:
    snapshots = (
        _snap(0, 1, KernelPhase.POST_TICK, "", a={"x": 1}),
        _snap(1, 1, KernelPhase.PRE_TICK, "", a={"x": 1}),
    )
    normalized = normalize_moments(snapshots)
    assert len(normalized) == 2


def test_extract_state_changes_ignores_the_first_observation_and_stationary_values() -> None:
    snapshots = (
        _snap(0, 0, KernelPhase.PRE_TICK, "S0", a={"x": 1}),
        _snap(1, 0, KernelPhase.AFTER_BOND_BREAK_PHASE, "S0", a={"x": 1}),  # unchanged, merges with S0
        _snap(2, 1, KernelPhase.POST_TICK, "S1", a={"x": 2}),  # real change
    )
    events = extract_state_changes(snapshots)
    assert len(events) == 1
    assert events[0].before == 1 and events[0].after == 2


def test_extract_state_changes_orders_by_observation_seq_not_tick() -> None:
    # Deliberately out-of-tick-order sequence numbers, mirroring the measured
    # kernel behavior where a POST_TICK observation precedes a same-tick-numbered PRE_TICK.
    snapshots = (
        _snap(5, 2, KernelPhase.POST_TICK, "S0", a={"x": 1}),
        _snap(6, 2, KernelPhase.PRE_TICK, "S0", a={"x": 1}),
        _snap(7, 2, KernelPhase.AFTER_BOND_BREAK_PHASE, "S1", a={"x": 9}),
    )
    events = extract_state_changes(snapshots)
    assert len(events) == 1
    assert events[0].observation_seq == 7


def test_build_cross_role_timeline_groups_same_seq_changes_together() -> None:
    from engine.deterministic.causal_timeline import StateChangeEvent
    e1 = StateChangeEvent(3, 1, KernelPhase.AFTER_BOND_BREAK_PHASE, "role_a", "field_a", 1, 2)
    e2 = StateChangeEvent(3, 1, KernelPhase.AFTER_BOND_BREAK_PHASE, "role_b", "field_b", 3, 4)
    e3 = StateChangeEvent(5, 2, KernelPhase.POST_TICK, "role_a", "field_a", 2, 9)
    timeline = build_cross_role_timeline((e1, e2, e3))

    assert len(timeline) == 2
    assert timeline[0].observation_seq == 3
    assert {c.role for c in timeline[0].changes} == {"role_a", "role_b"}
    assert timeline[1].observation_seq == 5


def test_atomic_change_group_rejects_mismatched_seq() -> None:
    from engine.deterministic.causal_timeline import AtomicChangeGroup, StateChangeEvent
    e1 = StateChangeEvent(3, 1, KernelPhase.AFTER_BOND_BREAK_PHASE, "role_a", "field_a", 1, 2)
    e2 = StateChangeEvent(4, 1, KernelPhase.AFTER_BOND_BREAK_PHASE, "role_b", "field_b", 3, 4)
    with pytest.raises(ValueError, match="share the group's observation_seq"):
        AtomicChangeGroup(3, 1, KernelPhase.AFTER_BOND_BREAK_PHASE, (e1, e2))
