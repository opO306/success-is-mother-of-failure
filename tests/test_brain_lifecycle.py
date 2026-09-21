import random

import pytest

from engine.brain import brains, choices, genetics, life, lifecycle
from engine.primal.scenario import build_world


class Scripted(brains.RandomPolicy):
    """Picks by a rule: rule(name, options) -> (op, target) or None to wait."""

    def __init__(self, rule):
        self.rule = rule

    def decide(self, person, sense, options, rng):
        wanted = self.rule(person, options)
        if wanted:
            op, target = wanted
            for option in options:
                if option.op == op:
                    picks = []
                    for candidates in option.args:
                        picks.append(next((c for c in candidates if c.value == target), candidates[0]))
                    return option, picks, {"think_steps": 0}
        wait = next(o for o in options if o.op == "wait")
        return wait, [], {"think_steps": 0}


def _couple(world, population):
    camp = next(iter(world.people.values())).camp
    woman, man = [p.name for p in world.people.values() if p.camp == camp][:2]
    population.lives[woman].sex, population.lives[man].sex = "F", "M"
    for name in (woman, man):
        population.lives[name].born = world.day - 100
    return woman, man


def test_founders_are_adults_with_genomes_and_their_strength_comes_from_genes():
    world = build_world(seed=0, band_size=2)
    population = lifecycle.found(world, None)
    assert set(population.lives) == set(world.people)
    for name, lived in population.lives.items():
        assert lived.sex in ("F", "M") and lifecycle.stage(population, world, name) == "adult"
        assert world.people[name].body.strength == genetics.strength_of(lived.development)


def test_mating_needs_both_to_choose_each_other_then_a_birth_brings_a_held_child_of_both(monkeypatch):
    monkeypatch.setattr(lifecycle, "CONCEPTION", 1.0)
    world = build_world(seed=0, band_size=2)
    population = lifecycle.found(world, None)
    woman, man = _couple(world, population)
    stats = life.new_stats()

    def day(brain):
        for name in (woman, man):   # the scripted pair never walks to water; keep them from dying of thirst mid-test
            world.people[name].body.hydration = 1.5
        life.live_day(world, brain, random.Random(0), stats, population)

    day(Scripted(lambda name, options: ("mate", man) if name == woman else None))
    assert population.lives[woman].pregnant_by is None and population.matings == 0
    day(Scripted(lambda name, options: ("mate", man) if name == woman else ("mate", woman) if name == man else None))
    assert population.matings >= 1 and population.lives[woman].pregnant_by == man
    for _ in range(lifecycle.PREGNANCY_DAYS):
        day(Scripted(lambda name, options: None))
    assert world.people[woman].alive
    child = population.births[0]["child"]
    kid = population.lives[child]
    assert kid.mother == woman and kid.father == man and kid.generation == 1
    assert world.people[child].location == world.people[woman].location
    assert lifecycle.stage(population, world, child) == "infant"
    decisions = stats["decisions"]
    lifecycle.before_slot(population, world)
    assert world.following[child] == woman
    assert not lifecycle.asked(population, world, world.people[child]) and stats["decisions"] == decisions


def test_an_approach_is_answered_by_the_other_persons_own_choice_and_only_adults_mate():
    world = build_world(seed=0, band_size=2)
    population = lifecycle.found(world, None)
    woman, man = _couple(world, population)
    assert lifecycle.resolve(population, world, {woman: ("mate", man)}, lambda target, proposer: False) == {}
    assert population.matings == 0
    pleasure = lifecycle.resolve(population, world, {woman: ("mate", man)}, lambda target, proposer: target == man)
    assert population.matings == 1 and pleasure == {woman: lifecycle.MATING_PLEASURE, man: lifecycle.MATING_PLEASURE}
    population.lives[man].born = world.day - lifecycle.ADULT_DAYS + 1
    lifecycle.resolve(population, world, {woman: ("mate", man)}, lambda target, proposer: True)
    assert population.matings == 1
    population.lives[man].born = world.day - 100
    stats = life.new_stats()
    life.live_day(world, Scripted(lambda name, options: ("mate", man) if name == woman else None), random.Random(0), stats, population)
    refused = population.matings
    life.live_day(world, _proposer_and_acceptor(woman, man), random.Random(0), stats, population)
    assert refused == 1 and population.matings > refused


def _proposer_and_acceptor(woman, man):
    def rule(name, options):
        ops = {o.op for o in options}
        if name == woman:
            return ("mate", man)
        if name == man and ops == {"mate", "wait"}:   # being asked
            return ("mate", woman)
        return None
    return Scripted(rule)


def test_only_a_lactating_body_gives_milk_and_only_to_an_infant(monkeypatch):
    monkeypatch.setattr(lifecycle, "CONCEPTION", 1.0)
    world = build_world(seed=0, band_size=2)
    population = lifecycle.found(world, None)
    woman, man = _couple(world, population)
    population.lives[woman].pregnant_by, population.lives[woman].pregnant_since = man, world.day - lifecycle.PREGNANCY_DAYS
    lifecycle.before_day_end(population, world, {})
    child = population.births[0]["child"]
    baby = world.people[child].body
    lifecycle.resolve(population, world, {man: ("nurse", child)})
    assert baby.eaten_today == 0.0
    pleasure = lifecycle.resolve(population, world, {woman: ("nurse", child)})
    assert baby.eaten_today == lifecycle.MILK_FOOD and pleasure[woman] == lifecycle.NURSING_PLEASURE
    nurse = next(o for o in choices.options(world, world.people[woman]) if o.op == "nurse")
    assert choices.to_step(nurse, [next(c for c in nurse.args[0] if c.value == child)]).op == "wait"


def test_a_hungry_infant_held_by_its_lactating_mother_suckles_without_anyone_choosing_it():
    world = build_world(seed=0, band_size=2)
    population = lifecycle.found(world, None)
    woman, man = _couple(world, population)
    population.lives[woman].pregnant_by, population.lives[woman].pregnant_since = man, world.day - lifecycle.PREGNANCY_DAYS
    lifecycle.before_day_end(population, world, {})
    child = population.births[0]["child"]
    baby = world.people[child].body
    baby.reserve, baby.eaten_today, baby.hydration = 0.0, 0.0, 0.0
    pleasure = lifecycle.resolve(population, world, {})
    assert baby.eaten_today == lifecycle.MILK_FOOD and pleasure[woman] == lifecycle.NURSING_PLEASURE
    world.people[woman].location = "동굴"
    before = baby.eaten_today
    lifecycle.resolve(population, world, {})
    assert baby.eaten_today == before                    # the mother is not there to suck from


def test_the_very_old_die_of_age_and_an_infants_hard_first_days_leave_a_mark(monkeypatch):
    world = build_world(seed=0, band_size=1)
    population = lifecycle.found(world, None)
    old, young = sorted(population.lives)[:2]
    population.lives[old].born = world.day - 400
    monkeypatch.setattr(lifecycle, "SENESCENCE_BASE", 1.0)
    population.lives[young].born = world.day - lifecycle.INFANT_DAYS
    population.lives[young].development.settled = False
    population.lives[young].development.early = {}
    population.lives[young].infancy_hardship = [1.0] * lifecycle.INFANT_DAYS
    before = lifecycle.temper(population, young).fear_gain
    lifecycle.before_day_end(population, world, {})
    assert not world.people[old].alive and world.people[old].body.cause_of_death == "나이 들어 몸이 다함"
    assert population.lives[young].development.settled and lifecycle.temper(population, young).fear_gain > before


def test_each_persons_neural_genes_change_how_the_shared_brain_chooses():
    torch = pytest.importorskip("torch")
    from engine.brain import senses
    world = build_world(seed=0, band_size=2)
    person = next(iter(world.people.values()))
    brain = brains.make("A", seed=0, learns=True)
    perceived, possible = senses.sense(world, person, 0), choices.options(world, person)
    plain = brain.decide(person.name, perceived, possible, random.Random(0))[2]["trace"][2]
    brain.set_neural(person.name, [1.0] * brain.d, [0.0] * brain.op_head.out_features)
    same = brain.decide(person.name, perceived, possible, random.Random(0))[2]["trace"][2]
    brain.set_neural(person.name, [3.0] * brain.d, [0.0] * brain.op_head.out_features)
    changed = brain.decide(person.name, perceived, possible, random.Random(0))[2]["trace"][2]
    assert torch.allclose(plain, same) and not torch.allclose(plain, changed)
    population = lifecycle.found(world, None)
    fresh = brains.make("A", seed=0)
    life.live_day(world, fresh, random.Random(0), life.new_stats(), population)
    assert set(fresh.neural) == set(population.lives)


def test_a_census_and_heritability_come_back_and_evolution_can_score_descendants():
    world = build_world(seed=0, band_size=2)
    population = lifecycle.found(world, None)
    report = lifecycle.census(population, world)
    assert report["alive"] == 6 and report["adult"] == 6 and set(report["traits"]) == set(genetics.TRAITS)
    assert set(lifecycle.heritability(population)) == set(genetics.TRAITS)
    torch = pytest.importorskip("torch")  # noqa: F841
    from engine.brain import evolve
    result = evolve.evaluate(brains.make("A", seed=0), [0], per_camp=2, max_days=2, births=True)
    assert {"lineage_days", "births_per_founder", "deepest_generation"} <= set(result)
