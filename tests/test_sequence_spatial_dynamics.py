from engine.living.events import ReplayEventSource, SeededEventSource
from engine.sequence import (
    Encounter,
    GridBarrier,
    GridLocation,
    LocalDynamicsState,
    MatterUnit,
    MoveAttempt,
    PortBond,
    SpatialState,
    apply_component_move,
    apply_move,
    apply_spatial_encounter,
    step_spatial_movement,
    step_spatial_component_movement,
    unit_ids_in_box,
)


def _state(*locations: GridLocation, barriers: tuple[GridBarrier, ...] = ()) -> SpatialState:
    local = LocalDynamicsState(tuple(MatterUnit(item.unit_id, (item.unit_id - 1) % 4) for item in locations), 4)
    return SpatialState(local, 5, 3, locations, barriers)


def test_every_matter_unit_needs_exactly_one_location() -> None:
    local = LocalDynamicsState((MatterUnit(1, 0), MatterUnit(2, 3)), 4)
    try:
        SpatialState(local, 3, 3, (GridLocation(1, 0, 0),))
    except ValueError as error:
        assert "exactly one location" in str(error)
    else:
        raise AssertionError("missing physical location must be rejected")


def test_an_inert_barrier_blocks_crossing() -> None:
    state = _state(
        GridLocation(1, 2, 0),
        barriers=(GridBarrier(2, 0, 3, 0),),
    )
    result = apply_move(state, MoveAttempt(1, 1, 0))

    assert result.event.payload()["outcome"] == "barrier_blocked"
    assert result.state.locations == state.locations
    assert result.state.time == 1


def test_a_missing_barrier_edge_is_a_physical_gap() -> None:
    state = _state(
        GridLocation(1, 2, 1),
        barriers=(GridBarrier(2, 0, 3, 0), GridBarrier(2, 2, 3, 2)),
    )
    result = apply_move(state, MoveAttempt(1, 1, 0))

    assert result.event.payload()["outcome"] == "moved"
    assert result.state.locations == (GridLocation(1, 3, 1),)


def test_chamber_contents_are_observed_from_position_only() -> None:
    state = _state(GridLocation(1, 3, 1), GridLocation(2, 1, 1))

    assert unit_ids_in_box(state, 3, 0, 4, 2) == (1,)


def test_failed_world_boundary_move_is_preserved_as_time() -> None:
    state = _state(GridLocation(1, 0, 0))
    result = apply_move(state, MoveAttempt(1, -1, 0))

    assert result.event.payload()["outcome"] == "world_boundary"
    assert result.state.time == 1
    assert result.state.locations == state.locations


def test_bonded_unit_cannot_stretch_a_local_bond() -> None:
    local = LocalDynamicsState(
        (MatterUnit(1, 0), MatterUnit(2, 3)),
        4,
        (PortBond(1, 0, 2, 0, 2),),
    )
    state = SpatialState(local, 4, 3, (GridLocation(1, 1, 1), GridLocation(2, 2, 1)))
    result = apply_move(state, MoveAttempt(1, -1, 0))

    assert result.event.payload()["outcome"] == "bond_constraint"
    assert result.state.locations == state.locations


def test_seeded_movement_samples_all_units_and_directions_without_success_filtering() -> None:
    state = _state(GridLocation(1, 0, 0))
    source = SeededEventSource(0)
    result = step_spatial_movement(state, source)

    assert result.random_draw is not None
    assert result.random_draw.operation == "choice_index"
    assert result.random_draw.arguments == (4,)
    assert result.event.payload()["outcome"] in {"moved", "world_boundary"}


def test_barrier_cannot_be_hidden_under_an_existing_bond() -> None:
    local = LocalDynamicsState(
        (MatterUnit(1, 0), MatterUnit(2, 3)),
        4,
        (PortBond(1, 0, 2, 0, 2),),
    )
    try:
        SpatialState(
            local,
            4,
            3,
            (GridLocation(1, 1, 1), GridLocation(2, 2, 1)),
            (GridBarrier(1, 1, 2, 1),),
        )
    except ValueError as error:
        assert "through a barrier" in str(error)
    else:
        raise AssertionError("matter bond cannot cross an inert barrier")


def test_nonadjacent_units_cannot_collide_through_space() -> None:
    state = _state(GridLocation(1, 0, 1), GridLocation(4, 3, 1))
    result = apply_spatial_encounter(state, Encounter(1, 0, 4, 0))

    assert result.event.payload()["outcome"] == "not_adjacent"
    assert result.state.local_state.bonds == ()


def test_barrier_separates_adjacent_units_from_collision() -> None:
    state = _state(
        GridLocation(1, 2, 0),
        GridLocation(4, 3, 0),
        barriers=(GridBarrier(2, 0, 3, 0),),
    )
    result = apply_spatial_encounter(state, Encounter(1, 0, 4, 0))

    assert result.event.payload()["outcome"] == "barrier_separated"
    assert result.state.local_state.bonds == ()


def test_adjacent_units_use_the_same_common_bond_law() -> None:
    state = _state(GridLocation(1, 1, 1), GridLocation(4, 2, 1))
    result = apply_spatial_encounter(state, Encounter(1, 0, 4, 0))

    assert result.event.payload()["outcome"] == "bond_formed"
    assert len(result.state.local_state.bonds) == 1


def test_seeded_spatial_movement_can_be_fully_replayed() -> None:
    initial = _state(GridLocation(1, 0, 0), GridLocation(2, 2, 2))
    source = SeededEventSource(9)
    state = initial
    draws = []
    for _ in range(50):
        result = step_spatial_movement(state, source)
        state = result.state
        draws.append(result.random_draw)

    replay = ReplayEventSource(draws)
    replayed = initial
    for _ in range(50):
        replayed = step_spatial_movement(replayed, replay).state

    assert replay.exhausted()
    assert replayed == state


def test_one_impulse_translates_the_whole_bonded_component() -> None:
    local = LocalDynamicsState(
        (MatterUnit(1, 0), MatterUnit(2, 3)),
        4,
        (PortBond(1, 0, 2, 0, 2),),
    )
    state = SpatialState(local, 5, 3, (GridLocation(1, 1, 1), GridLocation(2, 2, 1)))
    result = apply_component_move(state, MoveAttempt(1, 1, 0))

    assert result.event.payload()["outcome"] == "moved"
    assert result.event.payload()["member_ids"] == [1, 2]
    assert result.state.locations == (GridLocation(1, 2, 1), GridLocation(2, 3, 1))
    assert result.state.local_state.bonds == state.local_state.bonds


def test_one_blocked_member_blocks_the_whole_component() -> None:
    local = LocalDynamicsState(
        (MatterUnit(1, 0), MatterUnit(2, 3)),
        4,
        (PortBond(1, 0, 2, 0, 2),),
    )
    state = SpatialState(
        local,
        5,
        3,
        (GridLocation(1, 2, 0), GridLocation(2, 2, 1)),
        (GridBarrier(2, 0, 3, 0),),
    )
    result = apply_component_move(state, MoveAttempt(2, 1, 0))

    assert result.event.payload()["outcome"] == "barrier_blocked"
    assert result.state.locations == state.locations


def test_stationary_matter_blocks_component_translation() -> None:
    local = LocalDynamicsState(
        (MatterUnit(1, 0), MatterUnit(2, 3), MatterUnit(3, 1)),
        4,
        (PortBond(1, 0, 2, 0, 2),),
    )
    state = SpatialState(
        local,
        5,
        3,
        (GridLocation(1, 0, 1), GridLocation(2, 1, 1), GridLocation(3, 2, 1)),
    )
    result = apply_component_move(state, MoveAttempt(1, 1, 0))

    assert result.event.payload()["outcome"] == "site_occupied"
    assert result.state.locations == state.locations


def test_component_movement_samples_unit_impulses_without_success_filtering() -> None:
    local = LocalDynamicsState(
        (MatterUnit(1, 0), MatterUnit(2, 3)),
        4,
        (PortBond(1, 0, 2, 0, 2),),
    )
    state = SpatialState(local, 5, 3, (GridLocation(1, 1, 1), GridLocation(2, 2, 1)))
    result = step_spatial_component_movement(state, SeededEventSource(2))

    assert result.random_draw is not None
    assert result.random_draw.arguments == (8,)
    assert result.event.payload()["member_ids"] == [1, 2]
