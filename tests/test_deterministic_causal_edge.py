import pytest

from engine.deterministic import CausalEdge, CausalPath, MissingLink, PathEvidenceBundle, derive_edge_status, path_status


def test_derive_edge_status_prefers_unresolved_over_support_when_contradicted() -> None:
    assert derive_edge_status(True, True, True, 1) == "UNRESOLVED"


def test_derive_edge_status_contradicted_when_no_support_at_all() -> None:
    assert derive_edge_status(False, False, True, 0) == "CONTRADICTED"


def test_derive_edge_status_strongly_supported_needs_three_independent_domains() -> None:
    assert derive_edge_status(True, True, False, 2) == "SUPPORTED"
    assert derive_edge_status(True, True, False, 3) == "STRONGLY_SUPPORTED"


def test_derive_edge_status_observation_only_is_proposed() -> None:
    assert derive_edge_status(True, False, False, 0) == "PROPOSED"


def test_derive_edge_status_requires_some_evidence() -> None:
    with pytest.raises(ValueError, match="at least observation or intervention"):
        derive_edge_status(False, False, False, 0)


def test_path_status_is_the_weakest_edge() -> None:
    assert path_status(("STRONGLY_SUPPORTED", "SUPPORTED", "UNRESOLVED")) == "UNRESOLVED"
    assert path_status(("STRONGLY_SUPPORTED", "SUPPORTED")) == "SUPPORTED"


def test_path_status_requires_at_least_one_edge() -> None:
    with pytest.raises(ValueError, match="at least one edge"):
        path_status(())


def test_causal_edge_rejects_unsupported_status() -> None:
    bundle = PathEvidenceBundle(("OBS-1",), ())
    with pytest.raises(ValueError, match="unsupported edge status"):
        CausalEdge("EDGE-1", "N1", "N2", None, bundle, "MAYBE")


def test_causal_path_requires_edges_or_missing_links() -> None:
    with pytest.raises(ValueError, match="at least one edge or missing link"):
        CausalPath("PATH-1", (), (), "PROPOSED")


def test_causal_path_allows_missing_links_alone() -> None:
    link = MissingLink("N1", "N2", "no evidence connects these")
    path = CausalPath("PATH-1", (), (link,), "UNRESOLVED")
    assert path.missing_links == (link,)
