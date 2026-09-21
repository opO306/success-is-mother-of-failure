import random

import pytest

from engine.brain import choices, life, senses
from engine.primal.scenario import build_world

torch = pytest.importorskip("torch")
from torch.nn.utils import parameters_to_vector, vector_to_parameters  # noqa: E402

from engine.brain import brains, evolve  # noqa: E402


class Scripted(brains.RandomPolicy):
    def __init__(self, rule):
        self.rule = rule
        self.watched = {}

    def observe(self, person, events):
        self.watched.setdefault(person, []).extend(events)

    def decide(self, person, sense, options, rng):
        wanted = self.rule(person)
        option = next((o for o in options if o.op == wanted), next(o for o in options if o.op == "wait"))
        return option, [c[0] for c in option.args], {"think_steps": 0}


def test_an_onlooker_sees_what_was_eaten_and_the_pleased_face_that_followed():
    world = build_world(seed=0, band_size=2)
    camp = next(iter(world.people.values())).camp
    eater, onlooker = [p for p in world.people.values() if p.camp == camp][:2]
    berry = world.maker.make("산딸기")
    eater.carried.insert(0, berry)
    brain = Scripted(lambda name: "eat" if name == eater.name else "wait")
    stats = life.new_stats()
    life.live_day(world, brain, random.Random(0), stats)
    events = brain.watched[onlooker.name]
    ate = [e for e in events if e[0] == "eat"]
    assert ate, "the onlooker was asked after seeing the eating"
    op, token, signal = ate[0]
    assert token.category == senses.CATEGORIES["seen"] and token.kind == senses.kind_id("산딸기")
    assert token.props[len(senses.SEEN_GROUPS) + 2] > 0 and signal > 0     # a pleased face, a positive pull


def test_a_pleased_eater_pulls_the_onlooker_toward_eating_and_a_hurt_hunter_pushes_away_from_hunting():
    world = build_world(seed=0, band_size=2)
    person = next(iter(world.people.values()))
    perceived, possible = senses.sense(world, person, 0), choices.options(world, person)
    eat = [o.op for o in possible].index("eat")
    brain = brains.make("A", seed=0, learns=True)

    def eat_probability():
        return float(brain.decide(person.name, perceived, possible, random.Random(0))[2]["trace"][2][eat])

    before = eat_probability()
    pleased = senses.seen_token("eat", "칡뿌리", True, 1.0, 0.0, 0.0, 0.0, True, 0.0)
    for _ in range(5):
        brain.observe(person.name, [("eat", pleased, 3.0)])
        after = eat_probability()
    assert after > before
    hurt = senses.seen_token("eat", "칡뿌리", True, 0.0, 0.0, 1.0, 1.0, False, 0.0)
    for _ in range(10):
        brain.observe(person.name, [("eat", hurt, -3.0)])
        later = eat_probability()
    assert later < after


def test_a_genome_from_before_others_could_be_seen_grows_in(tmp_path):
    old = brains.make("B", seed=3, n_categories=brains.PRE_SEEN_CATEGORIES, n_extra=brains.PRE_SKY_EXTRA,
                      n_genes=brains.PRE_CLOCK_GENES, foresight=False, drives=False)
    old.enable_learning(0.2)
    torch.save(parameters_to_vector(old.parameters()).detach(), tmp_path / "old.pt")
    new = brains.make("B", seed=0, learns=True)
    vector_to_parameters(evolve.load_genome(new, tmp_path / "old.pt"), new.parameters())
    assert torch.equal(new.encoder.category.weight[: brains.PRE_SEEN_CATEGORIES], old.encoder.category.weight)
    assert new.learning_rate() == pytest.approx(0.2, rel=1e-4)
