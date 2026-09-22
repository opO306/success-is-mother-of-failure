import pytest

from engine.deterministic import ObservableField, ObservationCatalog, assess_observation_feasibility, default_catalog


def test_catalog_rejects_duplicate_pairs() -> None:
    with pytest.raises(ValueError, match="unique"):
        ObservationCatalog((ObservableField("bond", "exists"), ObservableField("bond", "exists")))


def test_default_catalog_matches_trace_model_fields() -> None:
    catalog = default_catalog()
    assert catalog.contains("bond", "exists")
    assert catalog.contains("bond", "stored_energy")
    assert catalog.contains("heat_cell", "energy")
    assert catalog.contains("particle", "kinetic_energy")
    assert not catalog.contains("bond", "stress")


def test_assess_feasibility_invalid_for_unknown_role_kind() -> None:
    result = assess_observation_feasibility(default_catalog(), "spaceship", "velocity")
    assert result.status == "INVALID"


def test_assess_feasibility_available_and_unavailable() -> None:
    catalog = default_catalog()
    assert assess_observation_feasibility(catalog, "particle", "x").status == "AVAILABLE"
    assert assess_observation_feasibility(catalog, "particle", "mass").status == "UNAVAILABLE"
