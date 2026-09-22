import pytest

from engine.deterministic import (
    DomainEvidence,
    HypothesisEdge,
    derive_effective_status,
    derive_evidence_status,
    derive_hypothesis_assessment,
    derive_lifecycle_status,
)


def _evidence(evidence_id: str, hypothesis_id: str, domain_id: str, relation: str,
             valid: bool = True, invalid_reason: str | None = None) -> DomainEvidence:
    return DomainEvidence(evidence_id, hypothesis_id, domain_id, "ARM", "PS", relation,
                          ("OBS-1",), "sd", "sd", valid, invalid_reason)


def test_no_evidence_is_untested() -> None:
    assert derive_evidence_status(()) == "untested"


def test_support_only_is_supported() -> None:
    evidence = (_evidence("E1", "H1", "D1", "supports"),)
    assert derive_evidence_status(evidence) == "supported"


def test_contradiction_only_is_contradicted_in_domain() -> None:
    evidence = (_evidence("E1", "H1", "D1", "contradicts"),)
    assert derive_evidence_status(evidence) == "contradicted_in_domain"


def test_support_and_contradiction_in_different_domains_is_conditional() -> None:
    evidence = (_evidence("E1", "H1", "D1", "supports"), _evidence("E2", "H1", "D2", "contradicts"))
    assert derive_evidence_status(evidence) == "conditional"


def test_underspecified_only_is_underspecified() -> None:
    evidence = (_evidence("E1", "H1", "D1", "underspecified"),)
    assert derive_evidence_status(evidence) == "underspecified"


def test_invalid_accident_evidence_is_ignored() -> None:
    evidence = (_evidence("E1", "H1", "D1", "contradicts", valid=False, invalid_reason="experiment_accident"),)
    assert derive_evidence_status(evidence) == "untested"


def test_lifecycle_defaults_to_active() -> None:
    assert derive_lifecycle_status("H1", ()) == "active"


def test_lifecycle_superseded_by_edge() -> None:
    edge = HypothesisEdge("HE-1", "H2", "H1", "superseded_by", ())
    assert derive_lifecycle_status("H1", (edge,)) == "superseded"


def test_lifecycle_incompatible_edge_applies_to_either_side() -> None:
    edge = HypothesisEdge("HE-1", "H1", "H2", "incompatible_with", ())
    assert derive_lifecycle_status("H1", (edge,)) == "incompatible"
    assert derive_lifecycle_status("H2", (edge,)) == "incompatible"


def test_effective_status_prefers_lifecycle_over_evidence() -> None:
    assert derive_effective_status("supported", "superseded") == "superseded"
    assert derive_effective_status("supported", "incompatible") == "incompatible"
    assert derive_effective_status("supported", "active") == "supported"


def test_derive_hypothesis_assessment_aggregates_domains() -> None:
    evidence = (
        _evidence("E1", "H1", "D1", "supports"),
        _evidence("E2", "H1", "D2", "contradicts"),
        _evidence("E3", "H1", "D3", "underspecified"),
    )
    assessment = derive_hypothesis_assessment("H1", evidence, (), ())

    assert assessment.evidence_status == "conditional"
    assert assessment.lifecycle_status == "active"
    assert assessment.effective_status == "conditional"
    assert assessment.supporting_domain_ids == ("D1",)
    assert assessment.contradicting_domain_ids == ("D2",)
    assert assessment.underspecified_domain_ids == ("D3",)
