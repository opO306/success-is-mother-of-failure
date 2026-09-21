from engine.living.events import RandomDraw, ReplayEventSource, SeededEventSource
from engine.sequence import (
    Encounter,
    LocalDynamicsState,
    LocalExperiment,
    LocalStepResult,
    MatterUnit,
    PortBond,
    apply_encounter,
    encounter_pairs,
    run_local_experiment,
    step_local,
)


def _pair(thermal: int = 4) -> LocalDynamicsState:
    return LocalDynamicsState((MatterUnit(1, 0), MatterUnit(2, 3)), thermal)


def test_every_port_pair_is_sampled_without_success_filtering() -> None:
    encounters = encounter_pairs(_pair())
    assert len(encounters) == 16
    assert encounters[0] == Encounter(1, 0, 2, 0)
    assert encounters[-1] == Encounter(1, 3, 2, 3)


def test_one_common_collision_law_forms_a_bond_and_conserves_energy() -> None:
    state = _pair()
    result = apply_encounter(state, Encounter(1, 0, 2, 3))

    assert result.event.payload()["outcome"] == "bond_formed"
    assert result.state.bonds == (PortBond(1, 0, 2, 3, 2),)
    assert result.state.total_energy == state.total_energy


def test_the_same_encounter_law_can_break_the_same_bond() -> None:
    formed = apply_encounter(_pair(), Encounter(1, 0, 2, 3)).state
    broken = apply_encounter(formed, Encounter(1, 0, 2, 3))

    assert broken.event.payload()["outcome"] == "bond_broken"
    assert broken.state.bonds == ()
    assert broken.state.total_energy == formed.total_energy


def test_bond_holds_when_local_thermal_energy_cannot_pay_its_strength() -> None:
    state = LocalDynamicsState(
        (MatterUnit(1, 0), MatterUnit(2, 3)),
        thermal_energy=1,
        bonds=(PortBond(1, 0, 2, 3, 2),),
    )
    result = apply_encounter(state, Encounter(1, 0, 2, 3))

    assert result.event.payload()["outcome"] == "bond_held"
    assert result.state.bonds == state.bonds
    assert result.state.total_energy == state.total_energy


def test_incompatible_collision_is_recorded_without_forcing_a_change() -> None:
    state = LocalDynamicsState((MatterUnit(1, 0), MatterUnit(2, 1)), thermal_energy=4)
    result = apply_encounter(state, Encounter(1, 2, 2, 2))

    assert result.event.payload()["outcome"] == "inert"
    assert result.state.bonds == ()
    assert result.state.time == 1
    assert result.state.total_energy == state.total_energy


def test_occupied_ports_block_only_that_local_encounter() -> None:
    state = LocalDynamicsState(
        (MatterUnit(1, 0), MatterUnit(2, 3), MatterUnit(3, 3)),
        thermal_energy=6,
        bonds=(PortBond(1, 0, 2, 0, 2),),
    )
    blocked = apply_encounter(state, Encounter(1, 0, 3, 0))
    free = apply_encounter(state, Encounter(1, 1, 3, 0))

    assert blocked.event.payload()["outcome"] == "ports_occupied"
    assert free.event.payload()["outcome"] == "bond_formed"


def test_units_can_form_branches_without_a_chain_or_growth_opcode() -> None:
    state = LocalDynamicsState(
        (MatterUnit(1, 0), MatterUnit(2, 3), MatterUnit(3, 3)),
        thermal_energy=6,
    )
    first = apply_encounter(state, Encounter(1, 0, 2, 0)).state
    second = apply_encounter(first, Encounter(1, 1, 3, 0)).state

    assert len(second.bonds) == 2
    assert {bond.left_id for bond in second.bonds} == {1}


def test_uniform_encounter_draw_replays_exactly() -> None:
    state = _pair()
    original = step_local(state, SeededEventSource(42))
    replay = step_local(state, ReplayEventSource((original.random_draw,)))

    assert replay == original


def test_explicit_encounter_needs_no_random_draw() -> None:
    result = apply_encounter(_pair(), Encounter(1, 0, 2, 0))
    assert result.random_draw is None


def test_less_than_two_units_is_quiescent_without_consuming_randomness() -> None:
    state = LocalDynamicsState((MatterUnit(1, 0),), thermal_energy=0)
    source = SeededEventSource(1)

    result = step_local(state, source)

    assert result == LocalStepResult(state, None, None)
    assert source.draw_count == 0


def test_bounded_local_experiment_is_reproducible_and_energy_conserving() -> None:
    initial = LocalDynamicsState(tuple(MatterUnit(index, index % 4) for index in range(8)), thermal_energy=8)
    first = run_local_experiment(initial, SeededEventSource(77), max_encounters=200)
    second = run_local_experiment(initial, SeededEventSource(77), max_encounters=200)

    assert first == second
    assert first.stop_reason == "encounter_limit"
    assert all(frame.state.total_energy == initial.total_energy for frame in first.frames)


def test_local_experiment_preserves_natural_quiescence() -> None:
    initial = LocalDynamicsState((MatterUnit(1, 0),), thermal_energy=0)
    experiment = run_local_experiment(initial, SeededEventSource(1), max_encounters=10)
    assert experiment == LocalExperiment(initial, (), "quiescent")
