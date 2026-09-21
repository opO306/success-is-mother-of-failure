from dataclasses import fields

import pytest

from engine.living.foundation import (
    AbioticWorld,
    BoundaryPhenotype,
    Founder,
    Genome,
    ObserverRecord,
    PhysicalCue,
    ReceptorGene,
    found_world,
    observer_index,
    perceive,
)


def _abiotic():
    return AbioticWorld("terrain-v1", "climate-v1", "matter-v1")


def _founders():
    boundary = BoundaryPhenotype(
        capacities=(10.0, 10.0),
        inward_limits=(1.0, 1.0),
        outward_limits=(1.0, 1.0),
        passive_loss=(0.0, 0.0),
        targets=(5.0, 5.0),
        maintenance=(0.1, 0.1),
        motion_cost=(0.1, 0.1),
        max_displacement=1.0,
    )
    return [
        Founder(1, Genome((ReceptorGene(0, gain=1.0),), (11,)), (4.0, 2.0), boundary, (1.0, 1.0), (0.0, 0.0)),
        Founder(2, Genome((ReceptorGene(1, gain=-0.5),), (22,)), (1.0, 8.0), boundary, (1.0, 1.0), (1.0, 0.0)),
        Founder(3, Genome((ReceptorGene(0, threshold=0.2),), (33,)), (3.0, 3.0), boundary, (1.0, 1.0), (0.0, 1.0)),
    ]


def test_all_founders_begin_together_without_internal_species_labels():
    records = [
        ObserverRecord(1, "식물형"),
        ObserverRecord(2, "동물형"),
        ObserverRecord(3, "사람형"),
    ]
    world = found_world(_abiotic(), _founders(), records)

    assert world.tick == 0
    assert set(world.living) == {1, 2, 3}
    assert all(state.age_ticks == 0 for state in world.living.values())
    assert {field.name for field in fields(next(iter(world.living.values())))}.isdisjoint(
        {"species", "lineage", "kind", "diet", "prey", "name"}
    )
    assert observer_index(world.observer_records) == {
        "동물형": (2,),
        "사람형": (3,),
        "식물형": (1,),
    }


def test_changing_observer_taxonomy_cannot_change_the_physical_world():
    first = found_world(_abiotic(), _founders(), [ObserverRecord(1, "식물"), ObserverRecord(2, "동물")])
    second = found_world(_abiotic(), _founders(), [ObserverRecord(1, "동물"), ObserverRecord(2, "미분류")])

    assert first.physical_snapshot() == second.physical_snapshot()


def test_genome_and_position_remain_part_of_physical_state():
    original = found_world(_abiotic(), _founders())
    changed = _founders()
    changed[0] = Founder(
        1, Genome((ReceptorGene(1),), (11,)), (4.0, 2.0), changed[0].boundary, (1.0, 1.0), (9.0, 9.0)
    )

    assert original.physical_snapshot() != found_world(_abiotic(), changed).physical_snapshot()


def test_perception_depends_on_physical_channels_and_inherited_receptors_not_taxonomy():
    cue = PhysicalCue(source_key=91, distance=1.0, bearing=-0.25, channels=(0.8, 0.1))
    light_biased = Genome((ReceptorGene(0, gain=2.0),))
    chemical_biased = Genome((ReceptorGene(1, gain=2.0),))

    first = perceive(light_biased, [cue])[0]
    second = perceive(chemical_biased, [cue])[0]

    assert first.source_key == second.source_key == 91
    assert first.receptor_activity != second.receptor_activity
    assert first.receptor_activity[0] > second.receptor_activity[0]


def test_physical_boundary_rejects_impossible_or_ambiguous_initial_state():
    with pytest.raises(ValueError, match="distance"):
        PhysicalCue(1, -1.0, 0.0, (0.2,))
    with pytest.raises(ValueError, match="reserves"):
        Founder(1, Genome(), (-0.1,), _founders()[0].boundary, (1.0, 1.0))
    with pytest.raises(ValueError, match="duplicate organism_id"):
        found_world(_abiotic(), [_founders()[0], _founders()[0]])
    with pytest.raises(ValueError, match="no living organism"):
        found_world(_abiotic(), _founders(), [ObserverRecord(99, "없는 계통")])
