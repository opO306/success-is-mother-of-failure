from engine.living.events import SeededEventSource, WorldEvent
from engine.sequence.face_chemistry import FaceChemistryLaw, FaceReaction
from engine.sequence.face_space import FaceMediumCell, FaceSoluteCell
from engine.sequence.nonliving_world import NonlivingWorldState, step_nonliving_world
from engine.sequence.observation import ExperimentObserver
from engine.sequence.spatial_sequence import EnergySource, SequenceSiteLocation, SpatialEnergyLaw, SpatialSequenceState
from engine.sequence.substrate import Contact, SequenceState, Strand


def _world(divided: bool = False) -> NonlivingWorldState:
    strand = Strand(1, (1, 0, 1, 2, 3, 2), cyclic=True)
    contact = (Contact(1, 1, 1, 4, 1, 2),) if divided else ()
    physical = SpatialSequenceState(
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
    return NonlivingWorldState(
        physical,
        face_medium=(FaceMediumCell(0, 0, 4, 1), FaceMediumCell(1, 0, 6, 2)),
        face_solutes=(FaceSoluteCell(0, 0, 0, 3), FaceSoluteCell(1, 0, 0, 7)),
    )


def test_observer_returns_none_and_cannot_change_supplied_states() -> None:
    before, after = _world(False), _world(True)
    before_hash, after_hash = before.state_hash(), after.state_hash()
    observer = ExperimentObserver(before, census_interval=1, ring_event_limit=5, post_trigger_steps=2)

    result = observer.observe(1, before, after)

    assert result is None
    assert before.state_hash() == before_hash
    assert after.state_hash() == after_hash
    assert observer.canonical()["format"] == "nonliving-observer-v1"


def test_full_observer_does_not_consume_randomness_or_change_physics() -> None:
    tracked = plain = _world(False)
    tracked_source, plain_source = SeededEventSource(412), SeededEventSource(412)
    observer = ExperimentObserver(tracked, census_interval=10, ring_event_limit=20, post_trigger_steps=2)
    law = SpatialEnergyLaw(1000, (EnergySource(0, 0, 1),))

    for event_index in range(1, 101):
        before = tracked
        tracked_result = step_nonliving_world(tracked, tracked_source, law)
        plain_result = step_nonliving_world(plain, plain_source, law)
        tracked, plain = tracked_result.state, plain_result.state
        observer.observe(event_index, before, tracked, tracked_result.events)
        assert tracked_result.events == plain_result.events
        assert tracked_result.all_random_draws == plain_result.all_random_draws

    assert tracked_source.draw_count == plain_source.draw_count
    assert tracked.state_hash() == plain.state_hash()
    assert observer.canonical()["integrity_violations"] == []


def test_split_records_inheritance_and_merges_adjacent_rare_windows() -> None:
    whole, divided = _world(False), _world(True)
    observer = ExperimentObserver(whole, census_interval=100, ring_event_limit=2, post_trigger_steps=2)
    first = WorldEvent.create(1, "probe.before", {"value": 1})
    observer.observe(1, whole, divided, (first,))
    second = WorldEvent.create(2, "probe.merge", {"value": 2})
    observer.observe(2, divided, whole, (second,))
    observer.observe(3, whole, whole, (WorldEvent.create(3, "probe.after", {"value": 3}),))
    observer.observe(4, whole, whole, (WorldEvent.create(4, "probe.done", {"value": 4}),))

    report = observer.canonical()
    inheritance = report["inheritance_events"][0]
    assert inheritance["kind"] == "split"
    assert len(inheritance["children"]) == 2
    assert inheritance["shared_strand_ids_across_children"] == [1]
    assert len(report["rare_event_captures"]) == 1
    capture = report["rare_event_captures"][0]
    assert [item["kind"] for item in capture["topologies"]] == ["split", "merge"]
    assert capture["before_events"][-1]["event_type"] == "probe.before"
    assert capture["after_events"][0]["event_type"] == "probe.merge"
    assert capture["remaining_steps"] == 0
    compact = observer.checkpoint_canonical()["rare_event_captures"][0]
    assert compact["before_event_count"] == len(capture["before_events"])
    assert compact["after_event_count"] == len(capture["after_events"])
    assert "before_events" not in compact and "after_events" not in compact


def test_reaction_activity_is_attributed_after_the_event_without_a_choice_source() -> None:
    state = _world(False)
    law = FaceChemistryLaw(1, (FaceReaction((1, 0, 0, 0), (0, 1, 0, 0), (0,)),))
    observer = ExperimentObserver(state, chemistry_law=law)
    event = WorldEvent.create(1, "sequence.face_reaction", {"face": [0, 0], "reaction_index": 0})

    observer.observe(1, state, state, (event,))

    report = observer.canonical()
    assert report["face_reactions"] == 1
    assert sum(item["catalytic_contribution"] for item in report["activity_by_lineage"].values()) > 0


def test_checkpoint_only_records_external_draw_count_and_state() -> None:
    state = _world(False)
    observer = ExperimentObserver(state)

    observer.checkpoint(25, state, 19)

    checkpoint = observer.canonical()["checkpoints"][0]
    assert checkpoint["event_index"] == 25
    assert checkpoint["draw_count"] == 19
    assert checkpoint["state_hash"] == state.state_hash()



def test_copy_event_survives_a_same_step_strand_id_change() -> None:
    template = Strand(9, (2,))
    before = NonlivingWorldState(SpatialSequenceState(
        SequenceState((Strand(1, (0, 1)), template), thermal_energy=10, next_strand_id=10),
        5,
        4,
        (
            SequenceSiteLocation(1, 0, 0, 0),
            SequenceSiteLocation(1, 1, 1, 0),
            SequenceSiteLocation(9, 0, 4, 3),
        ),
    ))
    after = NonlivingWorldState(SpatialSequenceState(
        SequenceState((Strand(2, (0,)), Strand(3, (1, 2)), template), thermal_energy=10, next_strand_id=10),
        5,
        4,
        (
            SequenceSiteLocation(2, 0, 0, 0),
            SequenceSiteLocation(3, 0, 1, 0),
            SequenceSiteLocation(3, 1, 2, 0),
            SequenceSiteLocation(9, 0, 4, 3),
        ),
    ))
    observer = ExperimentObserver(before)
    events = (
        WorldEvent.create(1, "sequence.face_material_extend", {
            "result_strand_id": 1,
            "strand_id": 1,
            "template_id": 9,
            "template_index": 0,
            "template_symbol": 2,
            "copy_match": True,
        }),
        WorldEvent.create(2, "sequence.backbone_cleave", {
            "parent_strand_id": 1,
            "child_strand_ids": [2, 3],
            "cut_index": 1,
        }),
    )

    observer.observe(1, before, after, events)

    copy_event = observer.canonical()["copy_events"][0]
    assert copy_event["result_strand_id"] == 1
    assert copy_event["copy_match"] is True
    assert len(copy_event["descendant_lineages"]) == 2
