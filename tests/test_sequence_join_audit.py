from audit_join_bottlenecks import STAGES, readiness_stage
from engine.sequence import Contact, SequenceState, Strand, event_candidates, join_readiness, parse_symbols


def _ready_state(thermal_energy: int = 12) -> SequenceState:
    return SequenceState(
        (Strand(1, parse_symbols("TT")), Strand(2, (0,)), Strand(3, (0,))),
        thermal_energy,
        contacts=(Contact(1, 0, 2, 0, 1, 2), Contact(1, 1, 3, 0, 1, 2)),
    )


def test_join_readiness_matches_actual_candidate_count() -> None:
    state = _ready_state()
    readiness = join_readiness(state)

    assert readiness.energy_available
    assert readiness.external_contacts == 2
    assert readiness.shared_template_arrangements == 1
    assert readiness.distinct_fragment_arrangements == 1
    assert readiness.exclusive_fragment_arrangements == 1
    assert readiness.fully_bound_arrangements == 1
    assert readiness.adjacent_arrangements == 1
    assert readiness.available_join_candidates == sum(
        candidate.kind == "join" for candidate in event_candidates(state)
    )
    assert STAGES[readiness_stage(readiness)] == "join_candidate_available"


def test_energy_gate_is_reported_without_erasing_geometric_readiness() -> None:
    readiness = join_readiness(_ready_state(thermal_energy=1))

    assert not readiness.energy_available
    assert readiness.adjacent_arrangements == 1
    assert readiness.available_join_candidates == 0
    assert STAGES[readiness_stage(readiness)] == "energy_unavailable"


def test_one_external_contact_stops_at_the_contact_count_gate() -> None:
    state = SequenceState(
        (Strand(1, parse_symbols("TT")), Strand(2, (0,))),
        thermal_energy=8,
        contacts=(Contact(1, 0, 2, 0, 1, 2),),
    )
    readiness = join_readiness(state)

    assert readiness.external_contacts == 1
    assert readiness.available_join_candidates == 0
    assert STAGES[readiness_stage(readiness)] == "fewer_than_two_external_contacts"
