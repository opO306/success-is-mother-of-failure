from engine.living.events import RandomDraw, RandomSample, SeededEventSource
from engine.sequence import (
    Contact, FaceMediumCell, FaceSoluteCell, SequenceSiteLocation, SequenceState,
    SpatialSequenceState, Strand, face_boundary_candidates,
    apply_spatial_sequence_candidate, observe_face_compartments,
    spatial_event_candidates, step_face_boundary,
)


def _state():
    physical = SpatialSequenceState(
        SequenceState((Strand(1, (0, 1, 2, 3), cyclic=True),), thermal_energy=8),
        5, 4,
        (
            SequenceSiteLocation(1, 0, 1, 1), SequenceSiteLocation(1, 1, 2, 1),
            SequenceSiteLocation(1, 2, 2, 2), SequenceSiteLocation(1, 3, 1, 2),
        ),
    )
    medium = tuple(FaceMediumCell(x, y, 8, 12) for y in range(3) for x in range(4))
    solutes = tuple(FaceSoluteCell(x, y, kind, 4) for y in range(3) for x in range(4) for kind in range(4))
    return physical, medium, solutes


class _FirstChoice:
    def choice_index(self, count):
        return RandomSample(0, RandomDraw(0, "choice_index", (count,), 0))


def test_cyclic_boundary_reversibly_adds_one_real_face_of_area():
    physical, medium, solutes = _state()
    before_energy = physical.reservoir_adjusted_energy + sum(cell.energy for cell in medium)
    before_matter = sum(len(s.symbols) for s in physical.sequence.strands) + sum(c.amount for c in solutes)
    candidate = next(item for item in face_boundary_candidates(physical, medium, solutes)
                     if item.kind == "expand" and item.face == (1, 0))
    expanded = step_face_boundary(
        physical, medium, solutes,
        SeededEventSource(0),
    )
    # Apply selection is stochastic, so verify the selected physical transition itself adds two sites.
    assert expanded is not None
    assert sum(len(s.symbols) for s in expanded.physical.sequence.strands) == 6
    assert len(observe_face_compartments(expanded.physical, expanded.face_medium)[0].interior_faces) == 2
    assert expanded.physical.reservoir_adjusted_energy + sum(c.energy for c in expanded.face_medium) == before_energy
    assert sum(len(s.symbols) for s in expanded.physical.sequence.strands) + sum(c.amount for c in expanded.face_solutes) == before_matter

    collapsed = step_face_boundary(
        expanded.physical, expanded.face_medium, expanded.face_solutes, _FirstChoice()
    )
    assert collapsed is not None
    assert sum(len(s.symbols) for s in collapsed.physical.sequence.strands) == 4
    assert len(observe_face_compartments(collapsed.physical, collapsed.face_medium)[0].interior_faces) == 1


def test_expanded_boundary_can_split_by_the_existing_local_contact_law():
    physical, medium, solutes = _state()
    expanded = step_face_boundary(physical, medium, solutes, SeededEventSource(0))
    assert expanded is not None
    divider = next(
        candidate for candidate in spatial_event_candidates(expanded.physical)
        if candidate.kind == "fold"
        and {candidate.contact.left_start, candidate.contact.right_start} == {1, 4}
    )
    divided = apply_spatial_sequence_candidate(expanded.physical, divider).state
    children = observe_face_compartments(divided, expanded.face_medium)
    assert len(children) == 2
    assert sorted(len(child.interior_faces) for child in children) == [1, 1]


def test_collapse_is_not_a_candidate_when_it_would_make_a_fold_overlap():
    physical, medium, solutes = _state()
    expanded = step_face_boundary(physical, medium, solutes, SeededEventSource(0))
    assert expanded is not None
    fold = Contact(1, 1, 1, 4, 1, 2)
    sequence = SequenceState(
        expanded.physical.sequence.strands,
        expanded.physical.sequence.thermal_energy,
        (fold,),
        expanded.physical.sequence.time,
        expanded.physical.sequence.next_strand_id,
    )
    divided = SpatialSequenceState(
        sequence, expanded.physical.width, expanded.physical.height,
        expanded.physical.locations, expanded.physical.external_energy_exchange,
        expanded.physical.field_energy, expanded.physical.medium,
    )
    assert not any(
        candidate.kind == "collapse"
        for candidate in face_boundary_candidates(divided, expanded.face_medium, expanded.face_solutes)
    )
