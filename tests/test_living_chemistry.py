from dataclasses import fields

import pytest

from engine.living import (
    AbioticWorld,
    BodyIntent,
    BoundaryPhenotype,
    CatalystGene,
    Chemistry,
    Founder,
    Genome,
    MatterPool,
    ProcessLaw,
    body_tick,
    found_world,
    run_processes,
    weighted_matter,
)


def _chemistry():
    return Chemistry(
        material_weights=(1.0, 1.0, 1.0),
        processes=(
            # Free channel 0 becomes free channel 1 plus released channel 2.
            ProcessLaw((1.0, 0.0, 0.0), (0.0, 0.6, 0.0), (0.0, 0.0, 0.0), (0.0, 0.0, 0.4)),
            # Free channel 1 becomes bound structure of the same channel.
            ProcessLaw((0.0, 1.0, 0.0), (0.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 0.0)),
            # A balanced transformation whose physical side effect reduces damage.
            ProcessLaw((0.0, 0.5, 0.0), (0.0, 0.0, 0.0), (0.0, 0.0, 0.0), (0.0, 0.0, 0.5), -0.2),
        ),
    )


def _boundary(**changes):
    values = {
        "capacities": (4.0, 1.0, 2.0),
        "inward_limits": (2.0, 2.0, 2.0),
        "outward_limits": (2.0, 2.0, 2.0),
        "passive_loss": (0.0, 0.0, 0.0),
        "targets": (1.0, 0.5, 0.5),
        "maintenance": (0.0, 0.0, 0.0),
        "motion_cost": (0.0, 0.0, 0.0),
        "capacity_gain": ((0.0, 0.0, 0.0), (0.0, 0.5, 0.0), (0.0, 0.0, 0.0)),
    }
    values.update(changes)
    return BoundaryPhenotype(**values)


def _state(catalysts, reserves=(2.0, 0.0, 0.0), structure=(1.0, 1.0, 1.0), damage=0.0):
    genome = Genome(catalysts=tuple(catalysts))
    founder = Founder(1, genome, reserves, _boundary(), structure, (0.0, 0.0), damage)
    return found_world(AbioticWorld("t", "c", _chemistry().fingerprint()), [founder]).living[1]


def test_frozen_chemistry_rejects_creation_of_weighted_matter():
    with pytest.raises(ValueError, match="not balanced"):
        Chemistry(
            (1.0, 1.0),
            (ProcessLaw((1.0, 0.0), (0.0, 2.0), (0.0, 0.0), (0.0, 0.0)),),
        )


def test_metabolic_transformation_conserves_body_structure_and_environment_together():
    chemistry = _chemistry()
    state = _state([CatalystGene(0, 2.0)])
    ambient = MatterPool([0.0, 0.0, 0.0])
    before = weighted_matter(state, ambient, chemistry)

    result = run_processes(state, ambient, chemistry, (1.0,))

    assert result.extents == (1.0,)
    assert state.reserves == pytest.approx([1.0, 0.6, 0.0])
    assert ambient.amounts == pytest.approx([0.0, 0.0, 0.4])
    assert weighted_matter(state, ambient, chemistry) == pytest.approx(before)


def test_growth_binds_matter_and_the_developed_boundary_can_gain_capacity():
    chemistry = _chemistry()
    state = _state([CatalystGene(1, 2.0)], reserves=(0.0, 1.0, 0.0))
    ambient = MatterPool([0.0, 0.0, 0.0])
    before_capacity = state.boundary.capacities_for(state.structure)[1]

    result = run_processes(state, ambient, chemistry, (0.5,))

    assert result.structure_added == (0.0, 0.5, 0.0)
    assert state.structure == pytest.approx([1.0, 1.5, 1.0])
    assert state.boundary.capacities_for(state.structure)[1] > before_capacity


def test_balanced_process_can_repair_but_never_below_zero_damage():
    chemistry = _chemistry()
    state = _state([CatalystGene(2, 4.0)], reserves=(0.0, 1.5, 0.0), damage=0.3)
    ambient = MatterPool([0.0, 0.0, 0.0])

    first = run_processes(state, ambient, chemistry, (1.0,))
    second = run_processes(state, ambient, chemistry, (1.0,))

    assert first.damage_delta == pytest.approx(-0.2)
    assert second.damage_delta == pytest.approx(-0.1)
    assert state.damage == 0.0


def test_competing_processes_are_scaled_together_not_won_by_tuple_order():
    chemistry = _chemistry()
    # Two copies of the growth catalyst compete for one unit of channel 1.
    state = _state([CatalystGene(1, 1.0), CatalystGene(1, 1.0)], reserves=(0.0, 1.0, 0.0))
    ambient = MatterPool([0.0, 0.0, 0.0])

    result = run_processes(state, ambient, chemistry, (1.0, 1.0))

    assert result.common_scale == pytest.approx(0.5)
    assert result.extents == pytest.approx((0.5, 0.5))


def test_uncatalysed_process_is_unavailable_and_gene_does_not_name_its_meaning():
    state = _state([])
    ambient = MatterPool([0.0, 0.0, 0.0])

    assert run_processes(state, ambient, _chemistry(), ()).extents == ()
    forbidden = {"food", "growth", "repair", "plant", "animal", "human", "photosynthesis", "digestion"}
    assert {field.name for field in fields(CatalystGene)}.isdisjoint(forbidden)
    assert {field.name for field in fields(ProcessLaw)}.isdisjoint(forbidden)


def test_body_tick_runs_requested_process_before_motion_and_unavoidable_upkeep():
    chemistry = _chemistry()
    state = _state([CatalystGene(0, 1.0)])
    ambient = MatterPool([0.0, 0.0, 0.0])

    result = body_tick(state, ambient, BodyIntent((0.0, 0.0, 0.0), (0.0, 0.0), (1.0,)), chemistry)

    assert result.processes is not None
    assert result.processes.extents == (1.0,)
