from engine.living.events import ReplayEventSource, SeededEventSource
from engine.sequence import (
    EnergySource,
    FaceMediumCell,
    FaceSoluteCell,
    FaceTransportLaw,
    NonlivingWorldState,
    SequenceSiteLocation,
    SequenceState,
    SpatialEnergyLaw,
    SpatialSequenceState,
    Strand,
    apply_spatial_sequence_candidate,
    apply_face_transport_cycle,
    observe_face_compartments,
    diffuse_face_solutes,
    observe_spatial_compartments,
    spatial_event_candidates,
    run_nonliving_world,
    step_nonliving_world,
)


def _world() -> NonlivingWorldState:
    physical = SpatialSequenceState(
        SequenceState((Strand(1, (0, 1, 2)), Strand(2, (2,))), thermal_energy=8),
        6,
        5,
        (
            SequenceSiteLocation(1, 0, 1, 1),
            SequenceSiteLocation(1, 1, 2, 1),
            SequenceSiteLocation(1, 2, 2, 2),
            SequenceSiteLocation(2, 0, 4, 3),
        ),
    )
    return NonlivingWorldState(physical)


def _law() -> SpatialEnergyLaw:
    return SpatialEnergyLaw(5, (EnergySource(0, 0, 3), EnergySource(5, 4, -3)), 8, 1)


def test_integrated_nonliving_step_never_skips_the_ordinary_event() -> None:
    source = SeededEventSource(9)
    state = _world()
    results = []
    for _ in range(6):
        result = step_nonliving_world(state, source, _law())
        state = result.state
        results.append(result)

    assert [len(item.events) for item in results] == [1, 1, 1, 1, 1, 4]
    assert state.ordinary_events == 6
    assert state.physical.time == 9


def test_integrated_nonliving_run_conserves_matter_and_full_energy_ledger() -> None:
    initial = _world()
    experiment = run_nonliving_world(initial, SeededEventSource(17), _law(), 500)

    assert experiment.final_state.ordinary_events == 500
    assert experiment.recorded_events == 797
    assert sum(len(item.symbols) for item in experiment.final_state.physical.sequence.strands) == 4
    assert (
        experiment.final_state.physical.reservoir_adjusted_energy
        == initial.physical.reservoir_adjusted_energy
    )


def test_integrated_nonliving_history_replays_exactly() -> None:
    initial = _world()
    source = SeededEventSource(21)
    state = initial
    draws = []
    events = []
    for _ in range(100):
        result = step_nonliving_world(state, source, _law())
        state = result.state
        draws.append(result.random_draw)
        events.append(result.events)

    replay = ReplayEventSource(draws)
    replayed = initial
    replayed_events = []
    for _ in range(100):
        result = step_nonliving_world(replayed, replay, _law())
        replayed = result.state
        replayed_events.append(result.events)

    assert replay.exhausted()
    assert replayed == state
    assert replayed_events == events


def test_physical_end_contact_closes_and_reopens_a_real_space() -> None:
    physical = SpatialSequenceState(
        SequenceState((Strand(1, (0, 1, 2, 3, 0, 1, 2, 3)),), thermal_energy=8),
        5,
        5,
        tuple(
            SequenceSiteLocation(1, index, *point)
            for index, point in enumerate(
                ((1, 1), (2, 1), (3, 1), (3, 2), (3, 3), (2, 3), (1, 3), (1, 2))
            )
        ),
    )
    close = next(
        item for item in spatial_event_candidates(physical)
        if item.kind == "fold"
        and item.contact.left_start == 0
        and item.contact.right_start == 7
    )

    closed = apply_spatial_sequence_candidate(physical, close).state
    opened = apply_spatial_sequence_candidate(
        closed,
        next(item for item in spatial_event_candidates(closed) if item.kind == "unfold"),
    ).state

    assert len(observe_spatial_compartments(closed)) == 1
    assert observe_spatial_compartments(opened) == ()
    assert closed.reservoir_adjusted_energy == physical.reservoir_adjusted_energy
    assert opened.reservoir_adjusted_energy == physical.reservoir_adjusted_energy


def test_backbone_cyclization_traps_space_and_any_free_backbone_can_open_it() -> None:
    physical = SpatialSequenceState(
        SequenceState((Strand(1, (0, 1, 2, 3, 0, 1, 2, 3)),), thermal_energy=8),
        5,
        5,
        tuple(
            SequenceSiteLocation(1, index, *point)
            for index, point in enumerate(
                ((1, 1), (2, 1), (3, 1), (3, 2), (3, 3), (2, 3), (1, 3), (1, 2))
            )
        ),
    )
    baseline = physical.reservoir_adjusted_energy
    close = next(item for item in spatial_event_candidates(physical) if item.kind == "cyclize")
    cyclic = apply_spatial_sequence_candidate(physical, close).state
    cuts = [item for item in spatial_event_candidates(cyclic) if item.kind == "cycle_open"]
    opened = apply_spatial_sequence_candidate(
        cyclic,
        next(item for item in cuts if item.cycle_cut.cut_index == 2),
    ).state

    assert cyclic.sequence.strands[0].cyclic
    assert len(cuts) == 8
    assert len(observe_spatial_compartments(cyclic)) == 1
    assert not opened.sequence.strands[0].cyclic
    assert observe_spatial_compartments(opened) == ()
    assert sorted(item.site_index for item in opened.locations if item.strand_id == 1) == list(range(8))
    assert cyclic.reservoir_adjusted_energy == baseline
    assert opened.reservoir_adjusted_energy == baseline


def test_four_site_cycle_traps_a_real_face_volume_and_opening_releases_it() -> None:
    physical = SpatialSequenceState(
        SequenceState((Strand(1, (0, 1, 2, 3), cyclic=True),), thermal_energy=4),
        4,
        4,
        (
            SequenceSiteLocation(1, 0, 1, 1),
            SequenceSiteLocation(1, 1, 2, 1),
            SequenceSiteLocation(1, 2, 2, 2),
            SequenceSiteLocation(1, 3, 1, 2),
        ),
    )
    cells = tuple(
        FaceMediumCell(x, y, 1, 0) if (x, y) != (1, 1) else FaceMediumCell(1, 1, 8, 4)
        for y in range(3) for x in range(3)
    )
    state = NonlivingWorldState(physical, face_medium=cells)
    observed = observe_face_compartments(physical, cells)
    opened_physical = apply_spatial_sequence_candidate(
        physical,
        next(item for item in spatial_event_candidates(physical) if item.kind == "cycle_open"),
    ).state
    opened = NonlivingWorldState(opened_physical, face_medium=cells)

    assert len(observed) == 1
    assert observed[0].interior_faces == ((1, 1),)
    assert observed[0].interior_medium_amount == 8
    assert observe_face_compartments(opened_physical, cells) == ()

    law = FaceTransportLaw(1, (), diffusion_divisor=4, absorption_per_site=0)
    closed_after = apply_face_transport_cycle(state, law)[-1][0]
    opened_after = apply_face_transport_cycle(opened, law)[-1][0]
    closed_center = next(cell for cell in closed_after.face_medium if cell.face == (1, 1))
    opened_center = next(cell for cell in opened_after.face_medium if cell.face == (1, 1))
    assert closed_center.amount == 8
    assert opened_center.amount < 8
    assert closed_after.reservoir_adjusted_energy == state.reservoir_adjusted_energy
    assert opened_after.reservoir_adjusted_energy == opened.reservoir_adjusted_energy


def test_same_surface_selectively_reflects_one_anonymous_kind_and_passes_another() -> None:
    physical = SpatialSequenceState(
        SequenceState((Strand(1, (0, 0)),), thermal_energy=0),
        3,
        2,
        (SequenceSiteLocation(1, 0, 1, 0), SequenceSiteLocation(1, 1, 1, 1)),
    )
    before = (FaceSoluteCell(0, 0, 0, 8), FaceSoluteCell(0, 0, 3, 8))

    after = diffuse_face_solutes(physical, before, 4)
    amounts = {(cell.face, cell.kind): cell.amount for cell in after}

    assert amounts.get(((1, 0), 0), 0) == 0
    assert amounts[((1, 0), 3)] == 2
    assert sum(cell.amount for cell in after if cell.kind == 0) == 8
    assert sum(cell.amount for cell in after if cell.kind == 3) == 8
