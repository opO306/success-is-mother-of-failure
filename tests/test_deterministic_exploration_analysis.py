from engine.deterministic import (
    BoundaryCandidate,
    IsolatedCaseCandidate,
    compute_coverage,
    find_boundary_candidates,
    find_isolated_cases,
)


def test_find_boundary_candidates_only_flags_adjacent_disagreements() -> None:
    points = ((1, "contradicts"), (2, "contradicts"), (3, "supports"), (4, "supports"), (5, "supports"))
    boundaries = find_boundary_candidates("axis.energy", points)

    assert boundaries == (BoundaryCandidate("axis.energy", 2, "contradicts", 3, "supports"),)


def test_find_boundary_candidates_reports_gap_between_tested_points_only() -> None:
    # only 2 and 5 were tested; 3 and 4 were never run.
    points = ((2, "contradicts"), (5, "supports"))
    boundaries = find_boundary_candidates("axis.energy", points)

    assert boundaries == (BoundaryCandidate("axis.energy", 2, "contradicts", 5, "supports"),)


def test_find_boundary_candidates_empty_when_no_disagreement() -> None:
    points = ((1, "supports"), (2, "supports"), (3, "supports"))
    assert find_boundary_candidates("axis.energy", points) == ()


def test_find_isolated_cases_flags_minority_within_a_matched_group() -> None:
    candidates = (
        ("C1", ("m0",), "supports"),
        ("C2", ("m0",), "supports"),
        ("C3", ("m0",), "contradicts"),  # the odd one out, holding the other axis fixed at m0
    )
    isolated = find_isolated_cases(candidates)

    assert len(isolated) == 1
    assert isolated[0] == IsolatedCaseCandidate("C3", "contradicts", "supports", 3, 1)


def test_find_isolated_cases_ignores_groups_too_small_to_call_a_minority() -> None:
    candidates = (("C1", ("m0",), "supports"), ("C2", ("m0",), "contradicts"))
    assert find_isolated_cases(candidates) == ()


def test_compute_coverage_reports_exact_integer_ratios() -> None:
    dimensions = {"axis.energy": (1, 2, 3), "axis.material": (0, 1)}
    tested = {"axis.energy": {1, 2, 3}, "axis.material": {0}}
    report = compute_coverage("P-1", dimensions, 6, tested, 5, 1)

    assert report.axis_coverage == {"axis.energy": (3, 3), "axis.material": (1, 2)}
    assert report.executed_count == 5
    assert report.invalid_count == 1
    assert report.planned_count == 6
