from engine.living.events import SeededEventSource, WorldEvent
from engine.sequence import (
    CompartmentLineageTracker,
    Contact,
    EnergySource,
    FaceMaterialLaw,
    FaceMediumCell,
    FaceSoluteCell,
    NonlivingWorldState,
    SequenceSiteLocation,
    SequenceState,
    SpatialEnergyLaw,
    SpatialSequenceState,
    Strand,
    apply_face_material_candidate,
    face_material_candidates,
    step_nonliving_world,
)


def _boundary(divided: bool) -> SpatialSequenceState:
    strand = Strand(1, (1, 0, 1, 2, 3, 2), cyclic=True)
    contact = (Contact(1, 1, 1, 4, 1, 2),) if divided else ()
    return SpatialSequenceState(
        SequenceState((strand,), thermal_energy=10, contacts=contact),
        3,
        2,
        (
            SequenceSiteLocation(1, 0, 0, 0),
            SequenceSiteLocation(1, 1, 1, 0),
            SequenceSiteLocation(1, 2, 2, 0),
            SequenceSiteLocation(1, 3, 2, 1),
            SequenceSiteLocation(1, 4, 1, 1),
            SequenceSiteLocation(1, 5, 0, 1),
        ),
    )


def _world(divided: bool) -> NonlivingWorldState:
    return NonlivingWorldState(
        _boundary(divided),
        face_medium=(FaceMediumCell(0, 0, 4, 1), FaceMediumCell(1, 0, 6, 2)),
        face_solutes=(FaceSoluteCell(0, 0, 0, 3), FaceSoluteCell(1, 0, 0, 7)),
    )


def test_tracker_records_parent_children_and_local_contents_on_split() -> None:
    before, after = _world(False), _world(True)
    tracker = CompartmentLineageTracker(before)
    before_hash, after_hash = before.state_hash(), after.state_hash()

    tracker.observe(1, before, after)

    assert before.state_hash() == before_hash
    assert after.state_hash() == after_hash
    assert len(tracker.events) == 1
    event = tracker.events[0]
    assert event.kind == "split"
    assert len(event.parents) == 1 and len(event.children) == 2
    assert sorted(dict(child.solutes_by_kind)[0] for child in event.children) == [3, 7]
    assert all([item.strand_id for item in child.boundary_strands] == [1] for child in event.children)
    assert event.parents[0].compartment_id not in {
        child.compartment_id for child in event.children
    }


def test_tracker_records_two_parents_and_one_child_on_merge() -> None:
    before, after = _world(True), _world(False)
    tracker = CompartmentLineageTracker(before)

    tracker.observe(1, before, after)

    event = tracker.events[0]
    assert event.kind == "merge"
    assert len(event.parents) == 2 and len(event.children) == 1
    assert dict(event.children[0].solutes_by_kind)[0] == 10


def _template_world() -> NonlivingWorldState:
    physical = SpatialSequenceState(
        SequenceState((Strand(1, (0, 1, 2, 3)), Strand(2, (3,))), thermal_energy=8),
        6,
        3,
        (
            SequenceSiteLocation(1, 0, 1, 1),
            SequenceSiteLocation(1, 1, 2, 1),
            SequenceSiteLocation(1, 2, 3, 1),
            SequenceSiteLocation(1, 3, 4, 1),
            SequenceSiteLocation(2, 0, 1, 0),
        ),
    )
    medium = tuple(FaceMediumCell(x, y, 8, 20) for y in range(2) for x in range(5))
    solutes = tuple(
        FaceSoluteCell(x, y, kind, 8)
        for y in range(2) for x in range(5) for kind in range(4)
    )
    return NonlivingWorldState(physical, face_medium=medium, face_solutes=solutes)


def test_tracker_records_template_copy_and_mismatch_without_changing_physics() -> None:
    before = _template_world()
    candidate = max(
        (
            item for item in face_material_candidates(
                before.physical, before.face_medium, before.face_solutes, FaceMaterialLaw()
            )
            if item.kind == "extend" and item.strand_id == 2 and item.end == 1
            and item.symbol == next(
                strand.symbols[item.template_index]
                for strand in before.physical.sequence.strands
                if strand.strand_id == item.template_id
            )
        ),
        key=lambda item: item.weight,
    )
    result = apply_face_material_candidate(
        before.physical, before.face_medium, before.face_solutes, candidate, FaceMaterialLaw()
    )
    after = NonlivingWorldState(
        result.physical, face_medium=result.face_medium, face_solutes=result.face_solutes
    )
    tracker = CompartmentLineageTracker(before)
    original_digest = next(item.digest for item in tracker.strand_lineages if item.strand_id == 2)

    tracker.observe(1, before, after, (result.event,))

    copied = next(item for item in tracker.strand_lineages if item.strand_id == 2)
    assert result.event.payload()["result_strand_id"] == 2
    assert result.event.payload()["copy_match"] is True
    assert copied.copy_steps == 1
    assert copied.copy_mismatches == 0
    assert copied.digest != original_digest


def test_observer_does_not_consume_randomness_or_change_the_world() -> None:
    tracked = _world(False)
    plain = tracked
    tracked_source, plain_source = SeededEventSource(91), SeededEventSource(91)
    tracker = CompartmentLineageTracker(tracked)
    law = SpatialEnergyLaw(1000, (EnergySource(0, 0, 1),))

    for event_index in range(1, 101):
        before = tracked
        tracked_result = step_nonliving_world(tracked, tracked_source, law)
        plain_result = step_nonliving_world(plain, plain_source, law)
        tracked = tracked_result.state
        plain = plain_result.state
        tracker.observe(event_index, before, tracked, tracked_result.events)
        assert tracked_result.events == plain_result.events
        assert tracked_result.random_draw == plain_result.random_draw

    assert tracked == plain
    assert tracked.state_hash() == plain.state_hash()
    assert tracker.canonical()["format"] == "compartment-lineage-v1"



def _strand_world(strands, locations, next_strand_id):
    return NonlivingWorldState(SpatialSequenceState(
        SequenceState(tuple(strands), thermal_energy=10, next_strand_id=next_strand_id),
        5,
        4,
        tuple(locations),
    ))


def test_shared_copy_ancestry_is_not_counted_twice_after_cut_and_ligation() -> None:
    template = Strand(9, (2,))
    initial = _strand_world(
        (Strand(1, (0, 1)), template),
        (
            SequenceSiteLocation(1, 0, 0, 0),
            SequenceSiteLocation(1, 1, 1, 0),
            SequenceSiteLocation(9, 0, 4, 3),
        ),
        10,
    )
    extended = _strand_world(
        (Strand(1, (0, 1, 2)), template),
        (
            SequenceSiteLocation(1, 0, 0, 0),
            SequenceSiteLocation(1, 1, 1, 0),
            SequenceSiteLocation(1, 2, 2, 0),
            SequenceSiteLocation(9, 0, 4, 3),
        ),
        10,
    )
    cut = _strand_world(
        (Strand(2, (0,)), Strand(3, (1, 2)), template),
        (
            SequenceSiteLocation(2, 0, 0, 0),
            SequenceSiteLocation(3, 0, 1, 0),
            SequenceSiteLocation(3, 1, 2, 0),
            SequenceSiteLocation(9, 0, 4, 3),
        ),
        10,
    )
    joined = _strand_world(
        (Strand(4, (0, 1, 2)), template),
        (
            SequenceSiteLocation(4, 0, 0, 0),
            SequenceSiteLocation(4, 1, 1, 0),
            SequenceSiteLocation(4, 2, 2, 0),
            SequenceSiteLocation(9, 0, 4, 3),
        ),
        10,
    )
    tracker = CompartmentLineageTracker(initial)
    tracker.observe(1, initial, extended, (WorldEvent.create(1, "sequence.face_material_extend", {
        "result_strand_id": 1,
        "strand_id": 1,
        "template_id": 9,
        "template_index": 0,
        "template_symbol": 2,
        "kind": 2,
        "copy_match": True,
    }),))
    tracker.observe(2, extended, cut, (WorldEvent.create(2, "sequence.backbone_cleave", {
        "parent_strand_id": 1,
        "child_strand_ids": [2, 3],
        "cut_index": 1,
    }),))
    tracker.observe(3, cut, joined, (WorldEvent.create(3, "sequence.backbone_ligate", {
        "parent_strand_ids": [2, 3],
        "new_strand_id": 4,
    }),))

    lineage = next(item for item in tracker.strand_lineages if item.strand_id == 4)
    assert lineage.copy_event_ids == (1,)
    assert lineage.copy_steps == 1
