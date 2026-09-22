import pytest

from engine.deterministic import AtomicPhaseEvent, CausalCondition, CausalNode, KernelPhase, PathEvidenceBundle


def test_causal_node_rejects_unsupported_type() -> None:
    with pytest.raises(ValueError, match="unsupported causal node type"):
        CausalNode("bogus", "role_a", "field_a", "D1")


def test_causal_node_id_is_deterministic_and_domain_sensitive() -> None:
    a = CausalNode("state", "role_a", "field_a", "D1")
    b = CausalNode("state", "role_a", "field_a", "D1")
    c = CausalNode("state", "role_a", "field_a", "D2")
    assert a.node_id == b.node_id
    assert a.node_id != c.node_id


def test_causal_condition_requires_at_least_one_axis() -> None:
    with pytest.raises(ValueError, match="cannot be empty"):
        CausalCondition("C1", "heat >= break_heat", ())


def test_atomic_phase_event_rejects_empty_effects() -> None:
    with pytest.raises(ValueError, match="cannot be empty"):
        AtomicPhaseEvent(0, 1, KernelPhase.AFTER_BOND_BREAK_PHASE, ())


def test_atomic_phase_event_id_is_deterministic() -> None:
    a = AtomicPhaseEvent(3, 1, KernelPhase.AFTER_BOND_BREAK_PHASE, ("N1", "N2"))
    b = AtomicPhaseEvent(3, 1, KernelPhase.AFTER_BOND_BREAK_PHASE, ("N2", "N1"))  # order-insensitive
    assert a.event_id == b.event_id


def test_path_evidence_bundle_requires_some_evidence() -> None:
    with pytest.raises(ValueError, match="at least one observation or intervention"):
        PathEvidenceBundle((), ())


def test_path_evidence_bundle_accepts_intervention_only() -> None:
    bundle = PathEvidenceBundle((), ("MECH-1",))
    assert bundle.canonical()["intervention_evidence_ids"] == ["MECH-1"]
