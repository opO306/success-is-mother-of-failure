import pytest

from engine.deterministic import ContradictionRecord, HypothesisDomainLink, HypothesisEdge, HypothesisGraph


def test_edge_cannot_join_a_hypothesis_to_itself() -> None:
    with pytest.raises(ValueError, match="cannot join a hypothesis to itself"):
        HypothesisEdge("HE-1", "H1", "H1", "derived_into", ())


def test_edge_rejects_unsupported_relation() -> None:
    with pytest.raises(ValueError, match="unsupported hypothesis edge relation"):
        HypothesisEdge("HE-1", "H1", "H2", "loves", ())


def test_domain_link_only_accepts_applicability_role() -> None:
    with pytest.raises(ValueError, match="role"):
        HypothesisDomainLink("H1", "D1", "something_else")


def test_contradiction_requires_both_evidence_sides() -> None:
    with pytest.raises(ValueError, match="at least one supporting and one contradicting"):
        ContradictionRecord("CON-1", "H1", "D1", (), ("E2",))


def test_graph_children_and_parents_are_symmetric() -> None:
    edge = HypothesisEdge("HE-1", "H1", "H2", "specialized_into", ("E1",))
    graph = HypothesisGraph((edge,), (), ())

    assert graph.children_of("H1") == (edge,)
    assert graph.parents_of("H2") == (edge,)
    assert graph.children_of("H2") == ()


def test_graph_is_superseded_true_only_via_explicit_edge() -> None:
    edge = HypothesisEdge("HE-1", "H2", "H1", "superseded_by", ())
    graph = HypothesisGraph((edge,), (), ())

    assert graph.is_superseded("H1") is True
    assert graph.is_superseded("H2") is False


def test_graph_domains_for_hypothesis() -> None:
    link = HypothesisDomainLink("H1", "D1", "applicability")
    graph = HypothesisGraph((), (link,), ())

    assert graph.domains_for("H1") == ("D1",)
    assert graph.domains_for("H2") == ()
