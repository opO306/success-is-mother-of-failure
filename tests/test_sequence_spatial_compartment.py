from dataclasses import fields

from engine.sequence import (
    Contact,
    EnergyCell,
    MediumCell,
    ObservedSequenceCompartment,
    SequenceSiteLocation,
    SequenceState,
    SpatialSequenceState,
    Strand,
    observe_spatial_compartments,
)


def _ring(*, closed: bool = True, energy: int = 7) -> SpatialSequenceState:
    strand = Strand(1, (0, 1, 2, 3, 0, 1, 2, 3))
    contact = (Contact(1, 0, 1, 7, 1, 2),) if closed else ()
    sequence = SequenceState((strand,), thermal_energy=20, contacts=contact)
    points = ((1, 1), (2, 1), (3, 1), (3, 2), (3, 3), (2, 3), (1, 3), (1, 2))
    field = (EnergyCell(2, 2, energy),) if energy else ()
    return SpatialSequenceState(
        sequence,
        5,
        5,
        tuple(SequenceSiteLocation(1, index, *point) for index, point in enumerate(points)),
        field_energy=field,
    )


def test_bonded_spatial_sequence_wall_creates_one_physical_interior() -> None:
    observed = observe_spatial_compartments(_ring())

    assert observed == (
        ObservedSequenceCompartment(
            tuple((1, index) for index in range(8)),
            ((2, 2),),
            7,
        ),
    )


def test_geometric_ring_without_a_closed_bond_graph_is_not_declared_a_boundary() -> None:
    assert observe_spatial_compartments(_ring(closed=False)) == ()


def test_only_energy_at_actually_enclosed_coordinates_is_internal() -> None:
    state = _ring(energy=0)
    state = SpatialSequenceState(
        state.sequence,
        state.width,
        state.height,
        state.locations,
        field_energy=(EnergyCell(2, 2, 5), EnergyCell(0, 0, 11)),
    )

    observed = observe_spatial_compartments(state)

    assert observed[0].interior_field_energy == 5


def test_only_medium_at_actually_enclosed_coordinates_is_internal() -> None:
    state = _ring(energy=0)
    state = SpatialSequenceState(
        state.sequence,
        state.width,
        state.height,
        state.locations,
        medium=(MediumCell(2, 2, 7, 3), MediumCell(0, 0, 11, 5)),
    )

    observed = observe_spatial_compartments(state)

    assert observed[0].interior_medium_amount == 7
    assert observed[0].interior_medium_energy == 3


def test_observation_does_not_modify_physics_or_use_life_taxonomy() -> None:
    state = _ring()
    before = state.state_hash()

    for _ in range(100):
        observe_spatial_compartments(state)

    assert state.state_hash() == before
    forbidden = {"alive", "species", "organism", "food", "sex", "will", "intelligence"}
    assert {item.name for item in fields(ObservedSequenceCompartment)}.isdisjoint(forbidden)
