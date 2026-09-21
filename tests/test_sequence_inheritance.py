from engine.sequence import (
    Encounter,
    ConnectedMaterial,
    InheritedBond,
    InheritedContribution,
    MaterialAncestry,
    apply_encounter,
    assemble_inherited_world,
    connected_materials,
)


def test_parental_contributions_are_preserved_without_averaging() -> None:
    first = InheritedContribution("first", (0, 1))
    second = InheritedContribution("second", (2, 3, 0))
    seed = assemble_inherited_world((first, second), thermal_energy=6)

    assert sorted(unit.symbol for unit in seed.state.units) == [0, 0, 1, 2, 3]
    assert len(seed.origins) == 5
    assert {origin.observer_tag for origin in seed.origins} == {"first", "second"}


def test_ancestry_names_do_not_change_the_physical_world() -> None:
    first = assemble_inherited_world(
        (InheritedContribution("mother", (0, 1)), InheritedContribution("father", (2, 3))),
        thermal_energy=4,
    )
    renamed = assemble_inherited_world(
        (InheritedContribution("red", (0, 1)), InheritedContribution("blue", (2, 3))),
        thermal_energy=4,
    )

    assert first.state == renamed.state
    assert first.origins != renamed.origins


def test_swapping_parent_order_does_not_change_physics() -> None:
    first = InheritedContribution("first", (3,))
    second = InheritedContribution("second", (0, 1))

    forward = assemble_inherited_world((first, second), thermal_energy=4)
    reverse = assemble_inherited_world((second, first), thermal_energy=4)

    assert forward.state == reverse.state


def test_inherited_internal_bonds_use_the_same_world_bond_type() -> None:
    contribution = InheritedContribution("parent", (0, 3), (InheritedBond(0, 0, 1, 0),))
    seed = assemble_inherited_world((contribution,), thermal_energy=2)

    assert len(seed.state.bonds) == 1
    assert seed.state.bonds[0].strength == 2


def test_one_contribution_can_be_masked_without_being_deleted() -> None:
    first = InheritedContribution("first", (0,))
    second = InheritedContribution("second", (0,))
    context = InheritedContribution("context", (3,))
    seed = assemble_inherited_world((first, second, context), thermal_energy=4)
    first_id = seed.unit_id("first")
    second_id = seed.unit_id("second")
    context_id = seed.unit_id("context")

    bound = apply_encounter(seed.state, Encounter(first_id, 0, context_id, 0)).state
    blocked = apply_encounter(bound, Encounter(second_id, 0, context_id, 0))

    assert blocked.event.payload()["outcome"] == "ports_occupied"
    assert {unit.unit_id for unit in blocked.state.units} == {first_id, second_id, context_id}
    assert seed.unit_id("second") == second_id


def test_masked_contribution_can_act_after_the_context_changes() -> None:
    contributions = (
        InheritedContribution("first", (0,)),
        InheritedContribution("second", (0,)),
        InheritedContribution("context", (3,)),
    )
    seed = assemble_inherited_world(contributions, thermal_energy=4)
    first_id = seed.unit_id("first")
    second_id = seed.unit_id("second")
    context_id = seed.unit_id("context")

    first_bound = apply_encounter(seed.state, Encounter(first_id, 0, context_id, 0)).state
    released = apply_encounter(first_bound, Encounter(first_id, 0, context_id, 0)).state
    second_bound = apply_encounter(released, Encounter(second_id, 0, context_id, 0))

    assert second_bound.event.payload()["outcome"] == "bond_formed"
    assert any(
        {bond.left_id, bond.right_id} == {second_id, context_id} for bond in second_bound.state.bonds
    )


def test_duplicate_observer_tags_are_rejected_only_for_unambiguous_observation() -> None:
    contributions = (InheritedContribution("same", (0,)), InheritedContribution("same", (3,)))
    try:
        assemble_inherited_world(contributions, thermal_energy=2)
    except ValueError as error:
        assert "observer tags" in str(error)
    else:
        raise AssertionError("duplicate observer tags must be rejected")


def test_connected_material_boundaries_follow_current_bonds_not_parent_labels() -> None:
    first = InheritedContribution("first", (0, 3), (InheritedBond(0, 0, 1, 0),))
    second = InheritedContribution("second", (0,))
    seed = assemble_inherited_world((first, second), thermal_energy=4)

    materials = connected_materials(seed)

    assert sorted(len(material.symbols) for material in materials) == [1, 2]
    assert {frozenset(material.observer_tags) for material in materials} == {
        frozenset({"first"}),
        frozenset({"second"}),
    }


def test_breaking_one_physical_bond_creates_fragments_without_gene_boundaries() -> None:
    contribution = InheritedContribution(
        "source",
        (0, 3, 0),
        (InheritedBond(0, 0, 1, 0), InheritedBond(1, 1, 2, 0)),
    )
    seed = assemble_inherited_world((contribution,), thermal_energy=4)
    middle_id = seed.unit_id("source", 1)
    last_id = seed.unit_id("source", 2)

    broken = apply_encounter(seed.state, Encounter(middle_id, 1, last_id, 0)).state
    materials = connected_materials(type(seed)(broken, seed.origins))

    assert sorted(len(material.symbols) for material in materials) == [1, 2]
    assert all(material.observer_tags == {"source"} for material in materials)


def test_cross_origin_bond_makes_one_mixed_material_component() -> None:
    first = InheritedContribution("first", (0,))
    second = InheritedContribution("second", (3,))
    seed = assemble_inherited_world((first, second), thermal_energy=4)
    first_id = seed.unit_id("first")
    second_id = seed.unit_id("second")

    joined = apply_encounter(seed.state, Encounter(first_id, 0, second_id, 0)).state
    materials = connected_materials(type(seed)(joined, seed.origins))

    assert len(materials) == 1
    assert materials[0].observer_tags == {"first", "second"}
    assert materials[0].physical_canonical() == {
        "bonds": [{"left_index": 0, "left_port": 0, "right_index": 1, "right_port": 0}],
        "symbols": [0, 3],
    }


def test_renaming_ancestry_does_not_change_connected_material_physics() -> None:
    first = assemble_inherited_world(
        (InheritedContribution("first", (0,)), InheritedContribution("second", (3,))),
        thermal_energy=4,
    )
    renamed = assemble_inherited_world(
        (InheritedContribution("red", (0,)), InheritedContribution("blue", (3,))),
        thermal_energy=4,
    )
    first_joined = apply_encounter(first.state, Encounter(1, 0, 2, 0)).state
    renamed_joined = apply_encounter(renamed.state, Encounter(1, 0, 2, 0)).state

    first_material = connected_materials(type(first)(first_joined, first.origins))[0]
    renamed_material = connected_materials(type(renamed)(renamed_joined, renamed.origins))[0]

    assert first_material.physical_canonical() == renamed_material.physical_canonical()
    assert first_material.observer_tags != renamed_material.observer_tags


def test_connected_material_rejects_a_fake_boundary_around_disconnected_units() -> None:
    try:
        ConnectedMaterial(
            (0, 3),
            (),
            (MaterialAncestry(0, "source", 0), MaterialAncestry(1, "source", 1)),
        )
    except ValueError as error:
        assert "disconnected" in str(error)
    else:
        raise AssertionError("a material component must be connected by physical bonds")
