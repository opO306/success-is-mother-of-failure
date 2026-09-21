import random

import pytest

from engine.brain import choices, life, senses
from engine.primal.scenario import build_world

torch = pytest.importorskip("torch")
from engine.brain import brains  # noqa: E402


def _all_numbers(sense):
    values = list(sense.body) + list(sense.context)
    for token in sense.tokens:
        values += [token.category, token.kind, *token.props]
    return values


def test_a_brain_perceives_numbers_only_and_the_same_kind_looks_the_same_in_every_world():
    world = build_world(seed=0, band_size=2)
    person = next(iter(world.people.values()))
    perceived = senses.sense(world, person, 0)
    assert perceived.tokens and all(isinstance(v, (int, float)) for v in _all_numbers(perceived))
    assert len(perceived.body) == senses.BODY_SIZE and len(perceived.context) == senses.CONTEXT_SIZE
    assert senses.kind_id("부싯돌") == senses.kind_id("부싯돌") != senses.kind_id("강돌")
    other = build_world(seed=7, band_size=2)
    first = next(iter(other.people.values()))
    assert {t.kind for t in senses.carried_tokens(first)} == {t.kind for t in senses.carried_tokens(person)}


def test_options_are_what_is_at_hand_and_an_empty_hand_has_nothing_to_strike_with():
    world = build_world(seed=0, band_size=2)
    person = next(iter(world.people.values()))
    ops = {o.op for o in choices.options(world, person)}
    assert {"go", "strike", "drink", "eat", "wait"} <= ops
    person.carried.clear()
    empty = {o.op for o in choices.options(world, person)}
    assert "strike" not in empty and "eat" not in empty and "drink" in empty


def test_a_pick_becomes_an_engine_step_with_words_only_on_the_engine_side():
    world = build_world(seed=0, band_size=2)
    person = next(iter(world.people.values()))
    person.plan_item_ids = [t.id for t in person.carried]
    strike = next(o for o in choices.options(world, person) if o.op == "strike")
    step = choices.to_step(strike, [strike.args[0][0], strike.args[1][1]])
    assert step.op == "strike" and step.items == [1, 2]
    go = next(o for o in choices.options(world, person) if o.op == "go")
    assert choices.to_step(go, [go.args[0][0]]).target in world.lands
    drink = next(o for o in choices.options(world, person) if o.op == "drink")
    assert choices.to_step(drink, [choices.NOTHING]).items == []


@pytest.mark.parametrize("name", ["random", "A", "B", "C"])
def test_every_candidate_lives_a_whole_day_on_the_real_engine(name):
    world = build_world(seed=0, band_size=2)
    brain = brains.make(name, seed=0)
    stats = life.new_stats()
    summary = life.live_day(world, brain, random.Random(0), stats)
    assert summary["day"] == 1 and world.day == 2
    assert stats["decisions"] >= len(world.people) and sum(stats["ops_tried"].values()) > 0
    assert brain.parameters_count() < 1_000_000


def test_a_body_collapsed_asleep_is_not_asked_for_a_choice_it_could_not_live():
    world = build_world(seed=0, band_size=1)
    for person in world.people.values():
        person.body.sleep_debt = world.config.collapse_debt + 5
    stats = life.new_stats()
    life.live_day(world, brains.make("random"), random.Random(0), stats)
    assert stats["decisions"] == 0


def test_the_recurrent_brain_carries_its_state_and_the_pondering_brain_thinks_a_bounded_number_of_steps():
    world = build_world(seed=0, band_size=2)
    person = next(iter(world.people.values()))
    perceived, possible = senses.sense(world, person, 0), choices.options(world, person)
    b = brains.make("B", seed=0)
    b.decide(person.name, perceived, possible, random.Random(0))
    first = b.state[person.name][1].clone()
    b.decide(person.name, perceived, possible, random.Random(0))
    assert not torch.equal(first, b.state[person.name][1])
    c = brains.make("C", seed=0)
    _, _, info = c.decide(person.name, perceived, possible, random.Random(0))
    assert 1 <= info["think_steps"] <= c.max_steps
