import pytest

from engine.deterministic import (
    CAUSAL_AXIS_REGISTRY,
    ExactConstraint,
    IntegerRangeConstraint,
    ResearchDomain,
    SetConstraint,
)


def test_domain_overlap_and_intersection_on_ranges() -> None:
    d1 = ResearchDomain("D1", (IntegerRangeConstraint("causal.collision.left_energy", 1, 5),))
    d2 = ResearchDomain("D2", (IntegerRangeConstraint("causal.collision.left_energy", 4, 8),))

    assert d1.overlaps(d2)
    intersection = d1.intersection(d2)
    assert intersection.constraints == (IntegerRangeConstraint("causal.collision.left_energy", 4, 5),)


def test_domain_disjoint_when_exact_values_differ() -> None:
    d1 = ResearchDomain("D1", (ExactConstraint("causal.collision.left_kind", 0),))
    d2 = ResearchDomain("D2", (ExactConstraint("causal.collision.left_kind", 1),))

    assert not d1.overlaps(d2)
    assert d1.intersection(d2) is None


def test_domain_disjoint_axes_always_overlap() -> None:
    d1 = ResearchDomain("D1", (ExactConstraint("causal.collision.left_kind", 0),))
    d2 = ResearchDomain("D2", (ExactConstraint("causal.material.kind", 1),))

    assert d1.overlaps(d2)


def test_domain_contains_narrower_domain() -> None:
    wide = ResearchDomain("D1", (IntegerRangeConstraint("causal.collision.left_energy", 1, 10),))
    narrow = ResearchDomain("D2", (IntegerRangeConstraint("causal.collision.left_energy", 3, 5),))

    assert wide.contains(narrow)
    assert not narrow.contains(wide)


def test_domain_matches_a_concrete_point() -> None:
    domain = ResearchDomain("D1", (
        ExactConstraint("causal.collision.left_kind", 0),
        IntegerRangeConstraint("causal.collision.left_energy", 1, 5),
    ))

    assert domain.matches({"causal.collision.left_kind": 0, "causal.collision.left_energy": 3})
    assert not domain.matches({"causal.collision.left_kind": 1, "causal.collision.left_energy": 3})
    assert not domain.matches({"causal.collision.left_kind": 0})


def test_domain_rejects_duplicate_axis_constraints() -> None:
    with pytest.raises(ValueError, match="at most one constraint per axis"):
        ResearchDomain("D1", (
            ExactConstraint("causal.collision.left_kind", 0),
            ExactConstraint("causal.collision.left_kind", 1),
        ))


def test_set_constraint_overlap_with_range() -> None:
    d1 = ResearchDomain("D1", (SetConstraint("causal.collision.left_energy", (1, 2, 9)),))
    d2 = ResearchDomain("D2", (IntegerRangeConstraint("causal.collision.left_energy", 5, 10),))

    assert d1.overlaps(d2)
    intersection = d1.intersection(d2)
    assert intersection.constraints == (SetConstraint("causal.collision.left_energy", (9,)),)


def test_domain_validate_against_registry_rejects_unknown_axis() -> None:
    domain = ResearchDomain("D1", (ExactConstraint("not.a.real.axis", 1),))
    with pytest.raises(ValueError, match="unregistered research axis"):
        domain.validate_against(CAUSAL_AXIS_REGISTRY)


def test_domain_digest_is_stable_regardless_of_constraint_order() -> None:
    a = ResearchDomain("D1", (
        ExactConstraint("causal.collision.left_kind", 0),
        IntegerRangeConstraint("causal.collision.left_energy", 1, 5),
    ))
    b = ResearchDomain("D1", (
        IntegerRangeConstraint("causal.collision.left_energy", 1, 5),
        ExactConstraint("causal.collision.left_kind", 0),
    ))
    assert a.digest == b.digest
