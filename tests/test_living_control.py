from dataclasses import fields

import pytest

from engine.living import (
    AbioticWorld,
    ActionPattern,
    BoundaryPhenotype,
    ControllerGene,
    Founder,
    Genome,
    MatterPool,
    PhysicalCue,
    ReceptorGene,
    controlled_body_tick,
    decide,
    found_world,
    perceive,
)


def _boundary():
    return BoundaryPhenotype(
        capacities=(10.0,),
        inward_limits=(2.0,),
        outward_limits=(2.0,),
        passive_loss=(0.0,),
        targets=(5.0,),
        maintenance=(0.0,),
        motion_cost=(0.0,),
        max_displacement=1.0,
    )


def _gene(*, first_input=1.0, persistence=0.0, learning_rate=0.0, control_cost=(0.0,)):
    return ControllerGene(
        # shortage, damage, and three anonymous source-memory features
        input_weights=((first_input, 0.0, 0.0, 0.0, 0.0),),
        recurrent_weights=((0.0,),),
        action_weights=((1.0,), (-1.0,)),
        node_bias=(0.0,),
        node_retention=(0.0,),
        actions=(ActionPattern((1.0,), (0.0,)), ActionPattern((-1.0,), (0.0,))),
        persistence=persistence,
        commitment_decay=0.5,
        switch_margin=0.0,
        learning_rate=learning_rate,
        control_cost=control_cost,
    )


def _state(gene, reserves=(2.0,)):
    founder = Founder(1, Genome(controller=gene), reserves, _boundary(), (1.0,), (0.0,))
    return found_world(AbioticWorld("t", "c", "m"), [founder]).living[1]


def test_same_shortage_can_produce_opposite_choices_from_inherited_network_diversity():
    approach = _state(_gene(first_input=1.0))
    release = _state(_gene(first_input=-1.0))

    first = decide(approach, ())
    second = decide(release, ())

    assert first.inputs == second.inputs
    assert first.action_index == 0
    assert second.action_index == 1
    assert first.intent.exchange == (1.0,)
    assert second.intent.exchange == (-1.0,)


def test_persistence_can_inhibit_the_strongest_new_impulse_but_eventually_decays():
    state = _state(_gene(persistence=4.0), reserves=(8.0,))
    first = decide(state, ())
    assert first.action_index == 1  # surplus activates the outward pattern

    state.reserves[0] = 0.0
    retained = decide(state, ())
    assert retained.action_index == 1
    assert retained.retained_previous

    later = None
    switched = False
    for _ in range(8):
        later = decide(state, ())
        switched = switched or (later.action_index == 0 and not later.retained_previous)
    assert later.action_index == 0
    assert switched


def test_learning_uses_experienced_body_change_not_an_action_label():
    state = _state(_gene(learning_rate=1.0))
    ambient = MatterPool([10.0])
    before = state.controller.action_weights[0][0]

    result = controlled_body_tick(state, ambient)

    assert result.decision.action_index == 0
    assert result.distress_change > 0
    assert state.controller.action_weights[0][0] > before


def test_control_has_a_conserved_material_cost_and_can_fail_to_pay_it():
    state = _state(_gene(control_cost=(0.5,)), reserves=(0.25,))
    ambient = MatterPool([0.0])
    before = state.reserves[0] + ambient.amounts[0]

    result = controlled_body_tick(state, ambient)

    assert result.control_cost.spent == (0.25,)
    assert result.control_cost.shortfall == (0.25,)
    assert result.control_cost.damage_added > 0
    assert state.reserves[0] + ambient.amounts[0] == pytest.approx(before)


def test_a_sources_physical_consequence_becomes_familiarity_and_association_not_a_label():
    gene = ControllerGene(
        input_weights=((1.0, 0.0, 0.0, 0.0, 0.0, 0.0),),
        recurrent_weights=((0.0,),),
        action_weights=((1.0,),),
        node_bias=(0.0,),
        node_retention=(0.0,),
        actions=(ActionPattern((1.0,), (0.0,)),),
        learning_rate=0.0,
        association_learning=1.0,
        memory_decay=0.9,
    )
    founder = Founder(
        1,
        Genome(receptors=(ReceptorGene(0),), controller=gene),
        (2.0,),
        _boundary(),
        (1.0,),
        (0.0,),
    )
    state = found_world(AbioticWorld("t", "c", "m"), [founder]).living[1]
    cue = PhysicalCue(91, 0.0, 0.0, (1.0,))

    controlled_body_tick(state, MatterPool([10.0]), (cue,))
    association, familiarity = state.memory[91]

    assert association > 0
    assert familiarity > 0
    next_decision = decide(state, perceive(state.genome, (cue,)))
    assert next_decision.inputs[3] == pytest.approx(association)
    assert next_decision.inputs[4] == pytest.approx(familiarity)


def test_controller_contains_no_named_instinct_will_or_taxonomy_fields():
    forbidden = {"hunger", "fear", "love", "hate", "willpower", "species", "sex", "talent"}
    assert {item.name for item in fields(ControllerGene)}.isdisjoint(forbidden)
    assert {item.name for item in fields(ActionPattern)}.isdisjoint(forbidden)


def test_observer_records_still_cannot_change_controller_state():
    founder = Founder(1, Genome(controller=_gene()), (2.0,), _boundary(), (1.0,), (0.0,))
    first = found_world(AbioticWorld("t", "c", "m"), [founder])
    second = found_world(AbioticWorld("t", "c", "m"), [founder])

    controlled_body_tick(first.living[1], MatterPool([10.0]))
    controlled_body_tick(second.living[1], MatterPool([10.0]))

    assert first.physical_snapshot() == second.physical_snapshot()
