from engine.living.events import ReplayEventSource, SeededEventSource
from engine.sequence import (
    EnergySource, FaceChemistryLaw, FaceMediumCell, FaceReaction, FaceSoluteCell,
    FaceTransportLaw, NonlivingWorldState, SequenceSiteLocation, SequenceState,
    SpatialEnergyLaw, SpatialSequenceState, Strand, face_reaction_candidates,
    run_nonliving_world, step_face_chemistry, step_nonliving_world,
)


def _physical(symbol=3):
    return SpatialSequenceState(
        SequenceState((Strand(1, (symbol,)),), 8), 3, 3,
        (SequenceSiteLocation(1, 0, 1, 1),),
    )


def _law():
    return FaceChemistryLaw(1, (
        FaceReaction((1, 1, 0, 0), (0, 0, 1, 1), (0,)),
        FaceReaction((0, 0, 1, 1), (1, 1, 0, 0), (3,)),
    ))


def test_balanced_face_reaction_changes_kinds_without_changing_total_matter():
    physical = _physical()
    solutes = (FaceSoluteCell(0, 0, 0, 3), FaceSoluteCell(0, 0, 1, 3))
    result = step_face_chemistry(physical, solutes, SeededEventSource(3), _law())
    assert result is not None
    assert sum(cell.amount for cell in result.face_solutes) == 6
    assert {(cell.kind, cell.amount) for cell in result.face_solutes} == {(0, 2), (1, 2), (2, 1), (3, 1)}


def test_sequence_material_changes_reaction_frequency_not_possibility():
    solutes = tuple(FaceSoluteCell(0, 0, kind, 2) for kind in range(4))
    first = face_reaction_candidates(_physical(3), solutes, _law())
    second = face_reaction_candidates(_physical(0), solutes, _law())
    assert {item.reaction_index for item in first} == {0, 1}
    assert {item.reaction_index for item in second} == {0, 1}
    assert [item.weight for item in first] != [item.weight for item in second]


def test_integrated_auxiliary_random_draws_replay_exactly():
    physical = _physical()
    medium = tuple(FaceMediumCell(x, y, 4, 4) for y in range(2) for x in range(2))
    solutes = tuple(FaceSoluteCell(x, y, kind, 4) for y in range(2) for x in range(2) for kind in range(4))
    initial = NonlivingWorldState(physical, ordinary_events=1, face_medium=medium, face_solutes=solutes)
    energy = SpatialEnergyLaw(100, (EnergySource(0, 0, 1),))
    source = SeededEventSource(91)
    original = step_nonliving_world(initial, source, energy, chemistry_law=_law())
    replayed = step_nonliving_world(
        initial, ReplayEventSource(original.all_random_draws), energy, chemistry_law=_law()
    )
    assert replayed.state == original.state
    assert replayed.events == original.events


def test_chemistry_integrated_run_conserves_total_material_and_energy():
    physical = _physical()
    medium = tuple(FaceMediumCell(x, y, 4, 4) for y in range(2) for x in range(2))
    solutes = tuple(FaceSoluteCell(x, y, kind, 4) for y in range(2) for x in range(2) for kind in range(4))
    initial = NonlivingWorldState(physical, face_medium=medium, face_solutes=solutes)
    result = run_nonliving_world(
        initial, SeededEventSource(7), SpatialEnergyLaw(1000, (EnergySource(0, 0, 1),)),
        200, chemistry_law=_law(),
    )
    assert result.final_state.reservoir_adjusted_energy == initial.reservoir_adjusted_energy
    assert sum(cell.amount for cell in result.final_state.face_solutes) + sum(
        len(strand.symbols) for strand in result.final_state.physical.sequence.strands
    ) == 65
