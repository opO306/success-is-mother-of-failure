import pytest

from engine.deterministic import (
    MISSING_LINK_HYPOTHESIS_STATUSES,
    MISSING_LINK_KINDS,
    MissingLinkHypothesis,
    MissingLinkInvestigation,
    MissingLinkResult,
)


def test_investigation_requires_all_fields() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        MissingLinkInvestigation("", "N1", "N2", "D1", "v1")


def test_hypothesis_rejects_unsupported_kind() -> None:
    with pytest.raises(ValueError, match="unsupported missing link hypothesis kind"):
        MissingLinkHypothesis("MLH-1", "ML-1", "MAGIC", {})


def test_hypothesis_rejects_unsupported_status() -> None:
    with pytest.raises(ValueError, match="unsupported hypothesis status"):
        MissingLinkHypothesis("MLH-1", "ML-1", "DIRECT_RELATION", {}, "ETERNAL_TRUTH")


def test_all_eight_kinds_are_defined() -> None:
    assert MISSING_LINK_KINDS == {
        "EXISTING_EVIDENCE_MISSED", "OBSERVATION_GAP", "EXISTING_STATE_MEDIATOR", "DERIVED_RELATION",
        "CONDITIONAL_RELATION", "DIRECT_RELATION", "PARENT_RELATION_WRONG", "UNKNOWN",
    }


def test_result_rejects_unsupported_status() -> None:
    with pytest.raises(ValueError, match="unsupported missing link status"):
        MissingLinkResult("ML-1", "TRUE_MISSING_CAUSE", (), "reason")


def test_result_accepts_documented_statuses() -> None:
    result = MissingLinkResult("ML-1", "UNRESOLVED", ("MLH-1",), "no new evidence yet")
    assert result.canonical()["status"] == "UNRESOLVED"
