import pytest

from engine.deterministic import (
    ObservationBudgetExceeded,
    ObservationRequest,
    default_observation_budget,
    empty_investigation_history,
)


def test_request_rejects_end_before_start() -> None:
    with pytest.raises(ValueError, match="at least start_tick"):
        ObservationRequest("OR-1", "ML-1", "bond", "stored_energy", 5, 2, "reason", "effect")


def test_request_rejects_span_over_budget() -> None:
    request = ObservationRequest("OR-1", "ML-1", "bond", "stored_energy", 0, 20, "reason", "effect")
    with pytest.raises(ObservationBudgetExceeded):
        request.validate_against_budget(default_observation_budget())


def test_fingerprint_is_deterministic_and_identity_based() -> None:
    r1 = ObservationRequest("OR-1", "ML-1", "bond", "stored_energy", 0, 2, "reason a", "effect a")
    r2 = ObservationRequest("OR-2", "ML-1", "bond", "stored_energy", 0, 2, "reason b", "effect b")
    # Different request_id/reason/expected_effect, same identifying fields -> same fingerprint
    assert r1.fingerprint == r2.fingerprint


def test_history_tracks_seen_fingerprints_without_duplication() -> None:
    history = empty_investigation_history()
    request = ObservationRequest("OR-1", "ML-1", "bond", "stored_energy", 0, 2, "reason", "effect")
    assert not history.has_been_requested(request.fingerprint)

    updated = history.with_fingerprint(request.fingerprint)
    assert updated.has_been_requested(request.fingerprint)
    assert updated.with_fingerprint(request.fingerprint) is updated  # idempotent, no duplicate entries
