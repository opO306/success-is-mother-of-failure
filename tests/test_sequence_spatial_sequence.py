from engine.living.events import ReplayEventSource, SeededEventSource
from engine.sequence import (
    Contact,
    SequenceSiteLocation,
    SequenceState,
    SpatialSequenceState,
    Strand,
    PeriodicEnergyFlow,
    EnergyCell,
    EnergySource,
    MediumCell,
    SpatialEnergyLaw,
    apply_spatial_energy_absorption,
    apply_spatial_energy_cycle,
    apply_spatial_energy_diffusion,
    apply_spatial_energy_flow,
    apply_spatial_energy_sources,
    apply_spatial_sequence_candidate,
    apply_spatial_sequence_move,
    apply_spatial_rotation,
    apply_medium_collision_absorption,
    apply_medium_diffusion,
    apply_spatial_flex,
    event_candidates,
    spatial_event_candidates,
    spatial_rotation_candidates,
    spatial_flex_candidates,
    step_spatial_sequence,
    step_spatial_sequence_with_flow,
)


def _two_strands(near: bool) -> SpatialSequenceState:
    sequence = SequenceState((Strand(1, (0, 1)), Strand(2, (3, 2))), 12)
    second_x = 2 if near else 5
    return SpatialSequenceState(sequence, 8, 5, (
        SequenceSiteLocation(1, 0, 1, 1),
        SequenceSiteLocation(1, 1, 1, 2),
        SequenceSiteLocation(2, 0, second_x, 1),
        SequenceSiteLocation(2, 1, second_x, 2),
    ))


def test_distant_sequences_cannot_bind_abstractly() -> None:
    distant = spatial_event_candidates(_two_strands(False))
    near = spatial_event_candidates(_two_strands(True))

    assert not any(item.kind == "bind" for item in distant)
    assert any(item.kind == "bind" for item in near)


def test_binding_requires_real_adjacency_and_preserves_energy() -> None:
    state = _two_strands(True)
    candidate = next(item for item in spatial_event_candidates(state) if item.kind == "bind")
    result = apply_spatial_sequence_candidate(state, candidate)

    assert result.state.sequence.total_energy == state.sequence.total_energy
    assert len(result.state.sequence.contacts) == 1
    assert result.event.payload()["spatial_state_hash"] == result.state.state_hash()


def test_adjacent_singletons_can_form_a_backbone_without_an_existing_template() -> None:
    state = SpatialSequenceState(
        SequenceState((Strand(1, (0,)), Strand(2, (1,))), thermal_energy=2),
        3,
        1,
        (SequenceSiteLocation(1, 0, 0, 0), SequenceSiteLocation(2, 0, 1, 0)),
    )
    candidate = next(
        item
        for item in spatial_event_candidates(state)
        if item.kind == "ligate" and item.ligation.left_id == 1
    )

    result = apply_spatial_sequence_candidate(state, candidate)

    assert [strand.symbols for strand in result.state.sequence.strands] == [(0, 1)]
    assert result.state.sequence.thermal_energy == 0
    assert result.state.sequence.total_energy == state.sequence.total_energy
    assert [(item.site_index, item.x) for item in result.state.locations] == [(0, 0), (1, 1)]
    assert result.event.event_type == "sequence.backbone_ligate"


def test_nonadjacent_singletons_cannot_ligate_in_a_spatial_world() -> None:
    state = SpatialSequenceState(
        SequenceState((Strand(1, (0,)), Strand(2, (1,))), thermal_energy=2),
        3,
        1,
        (SequenceSiteLocation(1, 0, 0, 0), SequenceSiteLocation(2, 0, 2, 0)),
    )

    assert not any(item.kind == "ligate" for item in spatial_event_candidates(state))


def test_local_end_index_is_exactly_equivalent_to_filtering_every_ligation_pair() -> None:
    state = SpatialSequenceState(
        SequenceState(tuple(Strand(index, (index % 4,)) for index in range(1, 9)), thermal_energy=12),
        5,
        5,
        (
            SequenceSiteLocation(1, 0, 0, 0),
            SequenceSiteLocation(2, 0, 1, 0),
            SequenceSiteLocation(3, 0, 4, 0),
            SequenceSiteLocation(4, 0, 4, 1),
            SequenceSiteLocation(5, 0, 2, 2),
            SequenceSiteLocation(6, 0, 0, 4),
            SequenceSiteLocation(7, 0, 3, 4),
            SequenceSiteLocation(8, 0, 4, 4),
        ),
    )
    points = {item.site: item.point for item in state.locations}
    exhaustive = tuple(
        candidate
        for candidate in event_candidates(state.sequence)
        if candidate.kind == "ligate"
        and abs(points[(candidate.ligation.left_id, 0)][0] - points[(candidate.ligation.right_id, 0)][0])
        + abs(points[(candidate.ligation.left_id, 0)][1] - points[(candidate.ligation.right_id, 0)][1])
        == 1
    )
    indexed = tuple(candidate for candidate in spatial_event_candidates(state) if candidate.kind == "ligate")

    assert indexed == exhaustive


def test_external_energy_flow_has_an_exact_reservoir_ledger() -> None:
    state = SpatialSequenceState(
        SequenceState((Strand(1, (0,)),), thermal_energy=2),
        2,
        1,
        (SequenceSiteLocation(1, 0, 0, 0),),
    )
    baseline = state.reservoir_adjusted_energy

    added = apply_spatial_energy_flow(state, 5)
    removed = apply_spatial_energy_flow(added.state, -10)

    assert added.state.sequence.thermal_energy == 7
    assert added.state.external_energy_exchange == 5
    assert removed.event.payload()["applied"] == -7
    assert removed.state.sequence.thermal_energy == 0
    assert removed.state.reservoir_adjusted_energy == baseline


def test_due_periodic_flow_is_recorded_without_skipping_the_ordinary_event() -> None:
    state = SpatialSequenceState(
        SequenceState((Strand(1, (0,)),), thermal_energy=0, time=2),
        2,
        1,
        (SequenceSiteLocation(1, 0, 0, 0),),
    )
    results = step_spatial_sequence_with_flow(state, SeededEventSource(7), PeriodicEnergyFlow(2, 3))

    assert len(results) == 2
    assert results[0].event.event_type == "sequence.environment_energy_flow"
    assert results[1].event.event_type == "sequence.spatial_move"
    assert results[1].state.time == 4


def test_spatial_source_diffusion_and_contact_absorption_are_exact_and_conservative() -> None:
    state = SpatialSequenceState(
        SequenceState((Strand(1, (0,)), Strand(2, (1,))), thermal_energy=2),
        3,
        3,
        (SequenceSiteLocation(1, 0, 0, 0), SequenceSiteLocation(2, 0, 1, 0)),
    )
    baseline = state.reservoir_adjusted_energy

    sourced = apply_spatial_energy_sources(state, (EnergySource(0, 0, 8),))
    diffused = apply_spatial_energy_diffusion(sourced.state, 4)
    absorbed = apply_spatial_energy_absorption(diffused.state, 1)

    assert sourced.state.field_energy == (EnergyCell(0, 0, 8),)
    assert sourced.state.external_energy_exchange == 8
    assert diffused.state.field_energy == (
        EnergyCell(0, 0, 4),
        EnergyCell(0, 1, 2),
        EnergyCell(1, 0, 2),
    )
    assert absorbed.event.payload()["absorbed"] == 2
    assert absorbed.state.sequence.thermal_energy == 4
    assert absorbed.state.field_energy == (
        EnergyCell(0, 0, 3),
        EnergyCell(0, 1, 2),
        EnergyCell(1, 0, 1),
    )
    assert absorbed.state.reservoir_adjusted_energy == baseline


def test_spatial_energy_cycle_is_fully_recorded_and_predictable() -> None:
    state = SpatialSequenceState(
        SequenceState((Strand(1, (0,)),), thermal_energy=0),
        3,
        3,
        (SequenceSiteLocation(1, 0, 1, 1),),
    )
    law = SpatialEnergyLaw(10, (EnergySource(1, 1, 9),), diffusion_divisor=4, absorption_per_site=1)

    first = apply_spatial_energy_cycle(state, law)
    second = apply_spatial_energy_cycle(state, law)

    assert [result.event.event_type for result in first] == [
        "sequence.environment_energy_sources",
        "sequence.environment_energy_diffusion",
        "sequence.environment_energy_absorption",
    ]
    assert first[-1].state == second[-1].state
    assert first[-1].state.reservoir_adjusted_energy == state.reservoir_adjusted_energy


def test_cleavage_remaps_the_same_material_sites_in_place() -> None:
    state = SpatialSequenceState(
        SequenceState((Strand(4, (0, 1, 2)),), 8),
        5,
        3,
        tuple(SequenceSiteLocation(4, index, index + 1, 1) for index in range(3)),
    )
    candidate = next(item for item in spatial_event_candidates(state) if item.kind == "cleave" and item.cut.cut_index == 1)
    result = apply_spatial_sequence_candidate(state, candidate)

    assert tuple(item.point for item in result.state.locations) == tuple(item.point for item in state.locations)
    assert sum(len(strand.symbols) for strand in result.state.sequence.strands) == 3
    assert result.state.sequence.total_energy == state.sequence.total_energy


def test_one_impulse_moves_the_whole_backbone() -> None:
    state = _two_strands(False)
    result = apply_spatial_sequence_move(state, (1, 0), 1, 0)

    strand_one = [item.point for item in result.state.locations if item.strand_id == 1]
    strand_two = [item.point for item in result.state.locations if item.strand_id == 2]
    assert strand_one == [(2, 1), (2, 2)]
    assert strand_two == [(5, 1), (5, 2)]


def test_backbone_hinge_can_rotate_one_side_and_conserves_total_energy() -> None:
    state = SpatialSequenceState(
        SequenceState((Strand(1, (0, 1, 2)),), thermal_energy=4),
        5,
        5,
        (
            SequenceSiteLocation(1, 0, 1, 2),
            SequenceSiteLocation(1, 1, 2, 2),
            SequenceSiteLocation(1, 2, 3, 2),
        ),
    )
    candidate = next(
        item for item in spatial_rotation_candidates(state)
        if item.pivot_site == (1, 1) and item.moving_site == (1, 2) and item.quarter_turn == 1
    )
    baseline = state.reservoir_adjusted_energy

    result = apply_spatial_rotation(state, candidate)

    assert [item.point for item in result.state.locations] == [(1, 2), (2, 2), (2, 3)]
    assert result.state.sequence.thermal_energy == 3
    assert result.state.field_energy == (EnergyCell(2, 2, 1),)
    assert result.state.reservoir_adjusted_energy == baseline
    assert result.event.event_type == "sequence.spatial_rotate"


def test_rotation_is_unavailable_when_another_bond_locks_the_hinge() -> None:
    state = SpatialSequenceState(
        SequenceState(
            (Strand(1, (0, 1, 2, 3)),),
            thermal_energy=4,
            contacts=(),
        ),
        4,
        4,
        (
            SequenceSiteLocation(1, 0, 1, 1),
            SequenceSiteLocation(1, 1, 2, 1),
            SequenceSiteLocation(1, 2, 2, 2),
            SequenceSiteLocation(1, 3, 1, 2),
        ),
    )
    # Closing the last-first gap makes every backbone edge part of a bonded cycle.
    locked = SpatialSequenceState(
        SequenceState(state.sequence.strands, 4, (Contact(1, 0, 1, 3, 1, 2),)),
        state.width,
        state.height,
        state.locations,
    )

    assert spatial_rotation_candidates(locked) == ()


def test_rotation_candidates_exclude_collision_and_world_boundary() -> None:
    state = SpatialSequenceState(
        SequenceState((Strand(1, (0, 1)), Strand(2, (2,))), thermal_energy=3),
        3,
        2,
        (
            SequenceSiteLocation(1, 0, 0, 0),
            SequenceSiteLocation(1, 1, 1, 0),
            SequenceSiteLocation(2, 0, 0, 1),
        ),
    )

    candidates = spatial_rotation_candidates(state)

    assert not any(item.pivot_site == (1, 0) and item.moving_site == (1, 1) for item in candidates)


def test_local_corner_flex_preserves_bonds_and_total_energy() -> None:
    state = SpatialSequenceState(
        SequenceState((Strand(1, (0, 1, 2)),), thermal_energy=4),
        4,
        4,
        (
            SequenceSiteLocation(1, 0, 1, 1),
            SequenceSiteLocation(1, 1, 2, 1),
            SequenceSiteLocation(1, 2, 2, 2),
        ),
    )
    candidate = spatial_flex_candidates(state)[0]
    baseline = state.reservoir_adjusted_energy

    result = apply_spatial_flex(state, candidate)

    assert candidate.source == (2, 1)
    assert candidate.target == (1, 2)
    assert [item.point for item in result.state.locations] == [(1, 1), (1, 2), (2, 2)]
    assert result.state.field_energy == (EnergyCell(2, 1, 1),)
    assert result.state.reservoir_adjusted_energy == baseline
    assert result.event.event_type == "sequence.spatial_flex"
    assert any(item.target == (2, 1) for item in spatial_flex_candidates(result.state))


def test_local_flex_is_blocked_by_occupancy_and_side_contact_geometry() -> None:
    occupied = SpatialSequenceState(
        SequenceState((Strand(1, (0, 1, 2)), Strand(2, (2,))), thermal_energy=4),
        4,
        4,
        (
            SequenceSiteLocation(1, 0, 1, 1),
            SequenceSiteLocation(1, 1, 2, 1),
            SequenceSiteLocation(1, 2, 2, 2),
            SequenceSiteLocation(2, 0, 1, 2),
        ),
    )
    contacted = SpatialSequenceState(
        SequenceState(
            occupied.sequence.strands,
            thermal_energy=4,
            contacts=(Contact(1, 1, 2, 0, 1, 2),),
        ),
        occupied.width,
        occupied.height,
        (
            SequenceSiteLocation(1, 0, 1, 1),
            SequenceSiteLocation(1, 1, 2, 1),
            SequenceSiteLocation(1, 2, 2, 2),
            SequenceSiteLocation(2, 0, 3, 1),
        ),
    )

    assert spatial_flex_candidates(occupied) == ()
    assert spatial_flex_candidates(contacted) == ()


def test_medium_flows_through_open_space_but_not_through_material_wall() -> None:
    state = SpatialSequenceState(
        SequenceState(tuple(Strand(index, (index % 4,)) for index in range(1, 4)), thermal_energy=0),
        3,
        3,
        (
            SequenceSiteLocation(1, 0, 1, 0),
            SequenceSiteLocation(2, 0, 1, 1),
            SequenceSiteLocation(3, 0, 1, 2),
        ),
        medium=(MediumCell(0, 1, 8, 4),),
    )

    blocked = apply_medium_diffusion(state, 4).state
    open_state = SpatialSequenceState(
        SequenceState((Strand(1, (1,)), Strand(3, (3,))), thermal_energy=0),
        3,
        3,
        (SequenceSiteLocation(1, 0, 1, 0), SequenceSiteLocation(3, 0, 1, 2)),
        medium=(MediumCell(0, 1, 8, 4),),
    )
    flowed = apply_medium_diffusion(open_state, 4).state

    assert all(cell.x == 0 for cell in blocked.medium)
    assert any(cell.point == (1, 1) and cell.amount == 2 for cell in flowed.medium)
    assert sum(cell.amount for cell in blocked.medium) == 8
    assert sum(cell.energy for cell in blocked.medium) == 4


def test_material_motion_displaces_medium_and_collision_transfers_only_energy() -> None:
    state = SpatialSequenceState(
        SequenceState((Strand(1, (0,)),), thermal_energy=0),
        3,
        1,
        (SequenceSiteLocation(1, 0, 0, 0),),
        medium=(MediumCell(1, 0, 5, 3),),
    )
    baseline = state.reservoir_adjusted_energy

    moved = apply_spatial_sequence_move(state, (1, 0), 1, 0).state
    absorbed = apply_medium_collision_absorption(moved, 2).state

    assert moved.medium == (MediumCell(0, 0, 5, 3),)
    assert absorbed.medium == (MediumCell(0, 0, 5, 1),)
    assert absorbed.sequence.thermal_energy == 2
    assert absorbed.reservoir_adjusted_energy == baseline


def test_spatial_sequence_history_replays_exactly() -> None:
    initial = _two_strands(False)
    source = SeededEventSource(83)
    state = initial
    draws = []
    events = []
    for _ in range(200):
        result = step_spatial_sequence(state, source)
        state = result.state
        draws.append(result.random_draw)
        events.append(result.event)

    replay = ReplayEventSource(draws)
    replayed = initial
    replayed_events = []
    for _ in range(200):
        result = step_spatial_sequence(replayed, replay)
        replayed = result.state
        replayed_events.append(result.event)

    assert replay.exhausted()
    assert replayed == state
    assert replayed_events == events
