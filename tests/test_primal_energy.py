import random

from engine.brain import brains, life, lifecycle
from engine.primal import body as physiology
from engine.primal import energy
from engine.primal.body import PrimalBody
from engine.primal.config import PrimalConfig
from engine.primal.scenario import build_world


def _config():
    return PrimalConfig(energy_balance=True)


def test_a_slot_costs_by_work_size_and_cold():
    c = _config()
    sleeper, hunter, big, cold = PrimalBody(), PrimalBody(), PrimalBody(strength=40.0), PrimalBody()
    cold.cold = 2.0
    asleep = energy.slot_spend(sleeper, "sleep", [], True, c.illness_onset)
    hunting = energy.slot_spend(hunter, "hunt", ["hunt"], False, c.illness_onset)
    assert hunting > 5 * asleep and hunter.spent_today == hunting
    assert energy.slot_spend(big, None, ["gather"], False, c.illness_onset) > energy.slot_spend(PrimalBody(), None, ["gather"], False, c.illness_onset)
    assert energy.slot_spend(cold, None, [], False, c.illness_onset) > energy.slot_spend(PrimalBody(), None, [], False, c.illness_onset)
    day = PrimalBody()
    for main in ("sleep", "sleep", None, "travel", "gather", None):
        energy.slot_spend(day, main, [], main == "sleep", c.illness_onset)
    assert 0.8 < day.spent_today < 1.3   # a forager's mixed day is about a day of food


def test_food_beyond_the_day_goes_to_fat_a_short_day_draws_on_fat_and_only_an_empty_body_starves():
    c = _config()
    fed = PrimalBody(fat=10.0, reserve=0.5, eaten_today=3.0, spent_today=1.0)
    physiology.day_update(fed, c)
    assert fed.fat > 10.0 and fed.underfed_days == 0 and not fed.starving
    lean = PrimalBody(fat=10.0, reserve=0.0, eaten_today=0.0, spent_today=1.0)
    physiology.day_update(lean, c)
    assert lean.fat == 9.0 and lean.underfed_days == 0 and not lean.starving
    empty = PrimalBody(fat=0.2, reserve=0.0, eaten_today=0.0, spent_today=1.0, strength=20.0)
    physiology.day_update(empty, c)
    assert empty.fat == 0.0 and empty.starving and empty.underfed_days == 1 and empty.strength < 20.0
    assert physiology.distress(PrimalBody(fat=1.0), c).get("hunger", 0.0) >= 0.8
    old = PrimalBody(fat=10.0, reserve=0.0, eaten_today=0.0)
    physiology.day_update(old, PrimalConfig())
    assert old.fat == 10.0 and old.underfed_days == 1


def test_a_world_with_the_law_gives_founders_fat_and_spends_it_while_the_old_world_does_not():
    on, off = build_world(seed=3, band_size=1, energy=True), build_world(seed=3, band_size=1)
    assert on.config.energy_balance and not off.config.energy_balance
    assert all(10.0 <= p.body.fat <= 20.0 for p in on.people.values())
    assert [p.body.strength for p in on.people.values()] == [p.body.strength for p in off.people.values()]
    start = {n: p.body.fat + p.body.reserve for n, p in on.people.items()}
    life.live_day(on, brains.RandomPolicy(), random.Random(0), life.new_stats())
    assert any(on.people[n].body.fat + on.people[n].body.reserve < start[n] for n in start if on.people[n].alive)


def test_pregnancy_milk_and_growing_cost_energy_under_the_law():
    world = build_world(seed=0, band_size=2, energy=True)
    population = lifecycle.found(world, None)
    names = sorted(population.lives)
    woman, man, child = names[0], names[1], names[2]
    population.lives[woman].sex, population.lives[man].sex = "F", "M"
    population.lives[woman].pregnant_by, population.lives[woman].pregnant_since = man, world.day
    population.lives[child].born = world.day - 30
    for name in (woman, child):
        world.people[name].body.spent_today = 0.0
    lifecycle.before_day_end(population, world, {})
    assert world.people[woman].body.spent_today == energy.PREGNANCY
    assert world.people[child].body.spent_today > 0.0
    population.lives[woman].pregnant_by = None
    population.lives[woman].last_birth = world.day
    population.lives[child].born = world.day - 1
    world.people[child].location = world.people[woman].location
    before = world.people[woman].body.spent_today
    lifecycle.resolve(population, world, {woman: ("nurse", child)})
    assert world.people[woman].body.spent_today == before + lifecycle.MILK_FOOD / energy.MILK_EFFICIENCY


def test_biting_a_stone_is_spat_out():
    world = build_world(seed=0, band_size=1, energy=True)
    person = next(iter(world.people.values()))
    person.carried.sort(key=lambda t: t.is_food)   # a stone or flake first

    class Biter(brains.RandomPolicy):
        def decide(self, name, sense, options, rng):
            option = next(o for o in options if o.op == "eat")
            return option, [option.args[0][0]], {"think_steps": 0}

    stats = life.new_stats()
    life.live_day(world, Biter(), random.Random(0), stats)
    assert stats["acts"][person.name] and stats["bonus"][person.name] < 0
