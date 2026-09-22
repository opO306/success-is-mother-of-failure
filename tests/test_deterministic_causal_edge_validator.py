from engine.deterministic import CausalNode, ResearchDomain
from engine.deterministic.causal_edge_validator import can_chain, validate_relation


def test_validate_relation_rejects_self_loop() -> None:
    a = CausalNode("state", "role_a", "field_a", "D1")
    domain = ResearchDomain("D1", ())
    rejection = validate_relation(a, a, domain, domain, False, True)
    assert rejection is not None
    assert "itself" in rejection.reason


def test_validate_relation_rejects_same_atomic_event() -> None:
    a = CausalNode("state", "role_a", "field_a", "D1")
    b = CausalNode("state", "role_b", "field_b", "D1")
    domain = ResearchDomain("D1", ())
    rejection = validate_relation(a, b, domain, domain, True, True)
    assert rejection is not None
    assert "same" in rejection.reason


def test_validate_relation_rejects_missing_evidence() -> None:
    a = CausalNode("state", "role_a", "field_a", "D1")
    b = CausalNode("state", "role_b", "field_b", "D1")
    domain = ResearchDomain("D1", ())
    rejection = validate_relation(a, b, domain, domain, False, False)
    assert rejection is not None
    assert "evidence" in rejection.reason


def test_validate_relation_accepts_legal_relation() -> None:
    a = CausalNode("state", "role_a", "field_a", "D1")
    b = CausalNode("outcome", "role_b", "field_b", "D1")
    domain = ResearchDomain("D1", ())
    assert validate_relation(a, b, domain, domain, False, True) is None


def test_can_chain_accepts_same_middle_node_with_overlapping_domains() -> None:
    middle = CausalNode("state", "role_b", "field_b", "D1")
    domain = ResearchDomain("D1", ())
    assert can_chain(middle, middle, domain, domain) is None
