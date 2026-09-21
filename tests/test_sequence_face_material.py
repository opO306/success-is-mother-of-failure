from engine.living.events import SeededEventSource
from engine.sequence import (
    EnergySource, FaceMaterialLaw, FaceMediumCell, FaceSoluteCell, NonlivingWorldState,
    SequenceSiteLocation, SequenceState, SpatialEnergyLaw, SpatialSequenceState,
    Strand, apply_face_material_candidate, face_material_candidates,
    run_nonliving_world, step_face_material,
)


def _state():
    physical = SpatialSequenceState(
        SequenceState((Strand(1, (0,)),), thermal_energy=0), 3, 3,
        (SequenceSiteLocation(1, 0, 1, 1),),
    )
    medium = tuple(FaceMediumCell(x, y, 8, 4) for y in range(2) for x in range(2))
    solutes = tuple(FaceSoluteCell(x, y, kind, 4) for y in range(2) for x in range(2) for kind in range(4))
    return physical, medium, solutes


def test_condensation_moves_one_kind_and_activation_energy_without_creation():
    physical, medium, solutes = _state()
    law = FaceMaterialLaw()
    candidate = next(item for item in face_material_candidates(physical, medium, solutes, law)
                     if item.kind == "condense" and item.symbol == 3)
    before_energy = physical.reservoir_adjusted_energy + sum(cell.energy for cell in medium)
    result = apply_face_material_candidate(physical, medium, solutes, candidate, law)

    assert sum(len(s.symbols) for s in result.physical.sequence.strands) == 2
    assert sum(cell.amount for cell in result.face_solutes if cell.kind == 3) == 15
    assert sum(s.symbols.count(3) for s in result.physical.sequence.strands) == 1
    assert result.physical.reservoir_adjusted_energy + sum(cell.energy for cell in result.face_medium) == before_energy


def test_every_condensed_singleton_can_physically_dissolve_back():
    physical, medium, solutes = _state()
    law = FaceMaterialLaw()
    condensed = step_face_material(physical, medium, solutes, SeededEventSource(4), law)
    assert condensed is not None
    created = max(strand.strand_id for strand in condensed.physical.sequence.strands)
    dissolve = next(item for item in face_material_candidates(
        condensed.physical, condensed.face_medium, condensed.face_solutes, law
    ) if item.kind == "dissolve" and item.strand_id == created)
    restored = apply_face_material_candidate(
        condensed.physical, condensed.face_medium, condensed.face_solutes, dissolve, law
    )
    assert sum(len(s.symbols) for s in restored.physical.sequence.strands) == 1
    for kind in range(4):
        assert sum(cell.amount for cell in restored.face_solutes if cell.kind == kind) == 16


def test_affinity_biases_copying_but_keeps_mismatch_candidates_possible():
    physical, medium, solutes = _state()
    candidates = [item for item in face_material_candidates(physical, medium, solutes, FaceMaterialLaw())
                  if item.kind == "condense" and (item.x, item.y) == (1, 0)]
    weights = {item.symbol: item.weight for item in candidates}
    assert set(weights) == {0, 1, 2, 3}
    assert weights[3] > weights[1] == weights[2] == weights[0]


def test_integrated_run_conserves_each_kind_across_solution_and_sequence():
    physical, medium, solutes = _state()
    initial = NonlivingWorldState(physical, face_medium=medium, face_solutes=solutes)
    experiment = run_nonliving_world(
        initial, SeededEventSource(44), SpatialEnergyLaw(1000, (EnergySource(0, 0, 1),)), 300,
        material_law=FaceMaterialLaw(interval=2),
    )
    final = experiment.final_state
    for kind in range(4):
        before = sum(cell.amount for cell in solutes if cell.kind == kind) + physical.sequence.strands[0].symbols.count(kind)
        after = sum(cell.amount for cell in final.face_solutes if cell.kind == kind) + sum(
            strand.symbols.count(kind) for strand in final.physical.sequence.strands
        )
        assert after == before
    assert final.reservoir_adjusted_energy == initial.reservoir_adjusted_energy
    assert any(name.startswith("sequence.face_material_") for name, _ in experiment.event_counts)


def _template_state():
    physical = SpatialSequenceState(
        SequenceState((Strand(1, (0, 1, 2, 3)), Strand(2, (3,))), thermal_energy=8),
        6, 3,
        (
            SequenceSiteLocation(1, 0, 1, 1), SequenceSiteLocation(1, 1, 2, 1),
            SequenceSiteLocation(1, 2, 3, 1), SequenceSiteLocation(1, 3, 4, 1),
            SequenceSiteLocation(2, 0, 1, 0),
        ),
    )
    medium = tuple(FaceMediumCell(x, y, 8, 20) for y in range(2) for x in range(5))
    solutes = tuple(FaceSoluteCell(x, y, kind, 8) for y in range(2) for x in range(5) for kind in range(4))
    return physical, medium, solutes


def test_template_extension_builds_a_separate_sequence_one_local_site_at_a_time():
    physical, medium, solutes = _template_state()
    law = FaceMaterialLaw()
    baseline_energy = physical.reservoir_adjusted_energy + sum(cell.energy for cell in medium)
    copied = [3]
    for expected_template_index in (1, 2, 3):
        options = [candidate for candidate in face_material_candidates(physical, medium, solutes, law)
                   if candidate.kind == "extend" and candidate.strand_id == 2
                   and candidate.template_index == expected_template_index and candidate.end == 1]
        assert {candidate.symbol for candidate in options} == {0, 1, 2, 3}
        selected = max(options, key=lambda candidate: candidate.weight)
        result = apply_face_material_candidate(physical, medium, solutes, selected, law)
        physical, medium, solutes = result.physical, result.face_medium, result.face_solutes
        copied.append(selected.symbol)

    assert tuple(copied) == (3, 2, 1, 0)
    assert next(strand.symbols for strand in physical.sequence.strands if strand.strand_id == 2) == tuple(copied)
    assert len([contact for contact in physical.sequence.contacts if contact.left_id != contact.right_id]) == 3
    assert physical.reservoir_adjusted_energy + sum(cell.energy for cell in medium) == baseline_energy


def test_extended_sequence_can_erode_and_disappear_without_rescue():
    physical, medium, solutes = _template_state()
    law = FaceMaterialLaw()
    extension = next(candidate for candidate in face_material_candidates(physical, medium, solutes, law)
                     if candidate.kind == "extend" and candidate.strand_id == 2)
    grown = apply_face_material_candidate(physical, medium, solutes, extension, law)
    erode = next(candidate for candidate in face_material_candidates(
        grown.physical, grown.face_medium, grown.face_solutes, law
    ) if candidate.kind == "erode" and candidate.strand_id == 2)
    shortened = apply_face_material_candidate(
        grown.physical, grown.face_medium, grown.face_solutes, erode, law
    )
    dissolve = next(candidate for candidate in face_material_candidates(
        shortened.physical, shortened.face_medium, shortened.face_solutes, law
    ) if candidate.kind == "dissolve" and candidate.strand_id == 2)
    gone = apply_face_material_candidate(
        shortened.physical, shortened.face_medium, shortened.face_solutes, dissolve, law
    )
    assert all(strand.strand_id != 2 for strand in gone.physical.sequence.strands)


def test_single_site_copy_can_grow_from_either_end_and_prepend_remaps_locations():
    physical, medium, solutes = _template_state()
    law = FaceMaterialLaw()
    prepend = max(
        (candidate for candidate in face_material_candidates(physical, medium, solutes, law)
         if candidate.kind == "extend" and candidate.strand_id == 2 and candidate.end == -1),
        key=lambda candidate: candidate.weight,
    )
    result = apply_face_material_candidate(physical, medium, solutes, prepend, law)
    daughter = next(strand for strand in result.physical.sequence.strands if strand.strand_id == 2)
    daughter_locations = [item for item in result.physical.locations if item.strand_id == 2]
    assert len(daughter.symbols) == 2
    assert [item.site_index for item in daughter_locations] == [0, 1]
    assert result.physical.sequence.contacts
