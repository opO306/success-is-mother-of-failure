import pytest

from engine.deterministic import (
    BondCountPrediction,
    CausalHypothesis,
    CausalHypothesisSet,
    ConservationPrediction,
    EvidenceReference,
    MomentumPrediction,
    RationalWeight,
)


def _evidence() -> tuple[EvidenceReference, ...]:
    return (EvidenceReference("E1", "supports", "deadbeef", "some run"),)


def test_causal_hypothesis_rejects_unsupported_status() -> None:
    with pytest.raises(ValueError, match="status"):
        CausalHypothesis("H1", "claim", (), (BondCountPrediction(1, 0),), _evidence(), "true")


def test_causal_hypothesis_requires_at_least_one_prediction() -> None:
    with pytest.raises(ValueError, match="predictions"):
        CausalHypothesis("H1", "claim", (), (), _evidence(), "untested")


def test_causal_hypothesis_digest_is_stable_across_equal_construction() -> None:
    first = CausalHypothesis("H1", "claim", ("m=0",), (ConservationPrediction(1, 6),), _evidence(), "untested")
    second = CausalHypothesis("H1", "claim", ("m=0",), (ConservationPrediction(1, 6),), _evidence(), "untested")

    assert first.digest == second.digest


def test_causal_hypothesis_digest_changes_with_status() -> None:
    base = CausalHypothesis("H1", "claim", ("m=0",), (MomentumPrediction(1, (0, 0)),), _evidence(), "untested")
    updated = CausalHypothesis("H1", "claim", ("m=0",), (MomentumPrediction(1, (0, 0)),), _evidence(), "supported")

    assert base.digest != updated.digest


def test_causal_hypothesis_set_rejects_duplicate_ids() -> None:
    h1 = CausalHypothesis("H1", "a", (), (BondCountPrediction(1, 0),), _evidence(), "untested")
    h2 = CausalHypothesis("H1", "b", (), (BondCountPrediction(1, 1),), _evidence(), "untested")
    with pytest.raises(ValueError, match="unique"):
        CausalHypothesisSet("subject", (h1, h2))


def test_momentum_prediction_rejects_non_pair() -> None:
    with pytest.raises(ValueError, match="pair"):
        MomentumPrediction(1, (0, 0, 0))


def test_rational_weight_still_requires_evidence_from_hypotheses_module() -> None:
    with pytest.raises(ValueError, match="evidence provenance"):
        RationalWeight(1, 2, ())
