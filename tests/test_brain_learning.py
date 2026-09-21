import random

import pytest

torch = pytest.importorskip("torch")
from torch.nn.utils import parameters_to_vector  # noqa: E402

from engine.brain import brains, choices, evolve, life, senses  # noqa: E402
from engine.primal import body as physiology  # noqa: E402
from engine.primal.scenario import build_world  # noqa: E402


def _moment():
    world = build_world(seed=0, band_size=2)
    person = next(iter(world.people.values()))
    person.plan_item_ids = [t.id for t in person.carried]
    return world, person, senses.sense(world, person, 0), choices.options(world, person)


def test_the_body_eases_when_a_parched_person_drinks_and_that_ease_is_the_only_signal():
    world, person, _, _ = _moment()
    person.body.thirst_days, person.body.hydration, person.body.drank_today = 1, 0.0, 0.0
    before = life.drive(world, person)
    physiology.drink(person.body, 1.0, False)
    assert life.drive(world, person) < before


def test_a_choice_followed_by_ease_becomes_likelier_and_one_followed_by_distress_less_likely():
    world, person, perceived, possible = _moment()
    for reward, grows in ((1.0, True), (-1.0, False)):
        brain = brains.make("A", seed=0, learns=True, rule="plain")
        _, _, info = brain.decide(person.name, perceived, possible, random.Random(3))
        k = info["trace"][3]
        before = float(info["trace"][2][k])
        for _ in range(5):
            brain.learn(person.name, info["trace"], reward)
        _, _, again = brain.decide(person.name, perceived, possible, random.Random(3))
        after = float(again["trace"][2][k])
        assert (after > before) if grows else (after < before)


def test_a_body_that_always_slowly_worsens_stops_teaching_once_it_is_expected():
    world, person, perceived, possible = _moment()
    brain = brains.make("A", seed=0, learns=True)
    _, _, info = brain.decide(person.name, perceived, possible, random.Random(3))
    for _ in range(80):
        brain.learn(person.name, info["trace"], -0.2)
    assert brain.expected[person.name] == pytest.approx(-0.2, abs=0.01)
    before = brain.lifetime[person.name][0].clone()
    brain.learn(person.name, info["trace"], -0.2)
    assert float((brain.lifetime[person.name][0] - before).abs().max()) < 1e-3
    # the same drift under the plain rule goes on punishing whatever was chosen
    plain = brains.make("A", seed=0, learns=True, rule="plain")
    plain.learn(person.name, info["trace"], -0.2)
    first = plain.lifetime[person.name][0].clone()
    plain.learn(person.name, info["trace"], -0.2)
    assert float((plain.lifetime[person.name][0] - first).abs().max()) > 1e-3


def test_ease_that_comes_later_is_shared_back_with_the_choices_just_before():
    world, person, perceived, possible = _moment()
    brain = brains.make("A", seed=0, learns=True)
    _, _, walk = brain.decide(person.name, perceived, possible, random.Random(1))
    brain.learn(person.name, walk["trace"], 0.0)
    _, _, drink = brain.decide(person.name, perceived, possible, random.Random(2))
    brain.learn(person.name, drink["trace"], 1.0)
    assert [t is walk["trace"] or t is drink["trace"] for t in brain.recent[person.name]] == [True, True]
    assert brain.recent[person.name][0] is drink["trace"] and brain.recent[person.name][1] is walk["trace"]


def test_each_person_learns_alone_starts_empty_and_is_forgotten_at_reset():
    world, person, perceived, possible = _moment()
    brain = brains.make("B", seed=0, learns=True)
    assert not brain.lifetime
    _, _, info = brain.decide(person.name, perceived, possible, random.Random(0))
    brain.learn(person.name, info["trace"], 0.5)
    assert set(brain.lifetime) == {person.name}
    brain.reset_people()
    assert not brain.lifetime and not brain.state and not brain.expected and not brain.recent


def test_a_learning_genome_is_the_old_genome_plus_how_fast_it_learns(tmp_path):
    plain, learning = brains.make("A", seed=0), brains.make("A", seed=0, learns=True)
    assert parameters_to_vector(learning.parameters()).numel() == parameters_to_vector(plain.parameters()).numel() + 1
    for name in ("A", "B", "C"):   # the learning rate is the last number, after every weight the plain genome has
        with_rate = parameters_to_vector(brains.make(name, seed=0, learns=True).parameters())
        without = parameters_to_vector(brains.make(name, seed=0).parameters())
        assert torch.equal(with_rate[:-1], without) and float(with_rate[-1]) == pytest.approx(-2.302585, abs=1e-5)
    torch.save(parameters_to_vector(plain.parameters()).detach(), tmp_path / "old.pt")
    assert evolve.load_genome(learning, tmp_path / "old.pt").numel() == parameters_to_vector(learning.parameters()).numel()
    torch.save(parameters_to_vector(learning.parameters()).detach(), tmp_path / "learned.pt")
    assert torch.equal(evolve.load_genome(plain, tmp_path / "learned.pt"), parameters_to_vector(learning.parameters())[:-1])
    history = evolve.run("A", tmp_path / "evo", generations=1, population=2, per_camp=1, max_days=2, worlds=1, elite=1,
                         stop_alive=2.0, start=tmp_path / "old.pt", learns=True)
    assert history[0]["learns"] and history[0]["best_learning_rate"] == pytest.approx(0.1, rel=0.2)


def test_rewards_flow_back_during_a_life_and_the_dead_leave_nothing_pending():
    world = build_world(seed=0, band_size=2)
    brain = brains.make("A", seed=0, learns=True)
    stats = life.new_stats()
    rng = random.Random(0)
    for _ in range(2):
        life.live_day(world, brain, rng, stats)
    assert stats["rewards"] > 0 and brain.lifetime
    assert all(world.people[name].alive for name in stats["pending"])
    assert set(stats["by_day"]) == {1, 2}
