from engine.living.events import ReplayEventSource, SeededEventSource
from engine.sequence import (
    GridLocation,
    LocalDynamicsState,
    MatterUnit,
    PortBond,
    SpatialState,
    observe_compartments,
    run_integrated_world,
)


def _ring() -> SpatialState:
    locations = (
        GridLocation(1, 1, 1), GridLocation(2, 2, 1), GridLocation(3, 3, 1),
        GridLocation(4, 3, 2), GridLocation(5, 3, 3), GridLocation(6, 2, 3),
        GridLocation(7, 1, 3), GridLocation(8, 1, 2), GridLocation(9, 5, 5),
    )
    units = tuple(MatterUnit(item.unit_id, (item.unit_id + 1) % 2 * 3) for item in locations)
    edges = ((1, 2), (2, 3), (3, 4), (4, 5), (5, 6), (6, 7), (7, 8))
    bonds = tuple(PortBond(left, 1, right, 0, 2) for left, right in edges)
    bonds += (PortBond(1, 0, 8, 1, 2),)
    local = LocalDynamicsState(units, 20, bonds)
    return SpatialState(local, 7, 7, locations)


def test_closed_bonded_matter_is_observed_as_a_compartment() -> None:
    observed = observe_compartments(_ring())

    assert len(observed) == 1
    assert observed[0].boundary_unit_ids == tuple(range(1, 9))
    assert observed[0].enclosed_sites == ((2, 2),)


def test_open_material_is_not_given_a_compartment_label() -> None:
    state = _ring()
    local = LocalDynamicsState(state.local_state.units, 18, state.local_state.bonds[:-1])
    opened = SpatialState(local, state.width, state.height, state.locations)

    assert observe_compartments(opened) == ()


def test_integrated_run_conserves_matter_and_total_energy() -> None:
    initial = _ring()
    experiment = run_integrated_world(initial, SeededEventSource(7), 200)

    assert len(experiment.frames) == 200
    assert experiment.final_state.local_state.units == initial.local_state.units
    assert experiment.final_state.local_state.total_energy == initial.local_state.total_energy


def test_integrated_history_replays_exactly() -> None:
    initial = _ring()
    first = run_integrated_world(initial, SeededEventSource(19), 120)
    replay = ReplayEventSource(frame.random_draw for frame in first.frames)
    second = run_integrated_world(initial, replay, 120)

    assert replay.exhausted()
    assert second.final_state == first.final_state
    assert tuple(frame.event for frame in second.frames) == tuple(frame.event for frame in first.frames)


def test_observer_compartment_reports_do_not_change_randomness_or_physics() -> None:
    initial = _ring()
    source = SeededEventSource(31)
    before = source.draw_count
    for _ in range(100):
        observe_compartments(initial)

    assert source.draw_count == before
    assert initial == _ring()
