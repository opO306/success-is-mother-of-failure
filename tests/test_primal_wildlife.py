import dataclasses

from engine.primal import nature, wildlife
from engine.primal.nature import Fire
from engine.primal.scenario import build_world


class Dice:
    """A world rng that always rolls the same number."""

    def __init__(self, value):
        self.value = value

    def random(self):
        return self.value

    def choice(self, options):
        return options[0]


def _herd(world, species):
    return next(h for h in world.herds if h.species == species)


def test_a_herd_walks_to_the_nearest_water_at_dawn_and_goes_home_after():
    world = build_world(seed=0, band_size=1, wildlife=True)
    deer = next(h for h in world.herds if h.species == "사슴" and h.place == "북쪽 숲")
    wildlife.slot(world, "새벽")
    assert deer.place == "북쪽 개울" and deer.home == "북쪽 숲"
    wildlife.slot(world, "아침")
    assert deer.place == "북쪽 숲"


def test_a_predator_takes_the_lone_sleeper_in_the_open_but_not_a_crowd_by_a_fire(monkeypatch):
    world = build_world(seed=0, band_size=5, wildlife=True)
    tiger = _herd(world, "호랑이")
    monkeypatch.setitem(nature.SPECIES, "호랑이", dataclasses.replace(nature.SPECIES["호랑이"], stalks_people=0.3))
    camp = world.lands["북쪽 야영지"]
    people = world.at("북쪽 야영지")
    tiger.place = tiger.home = "북쪽 야영지"
    world.rng = Dice(0.5)
    camp.fire = Fire(heat=0.7, fuel_slots=8)
    before = [len(p.body.injuries) for p in people]
    wildlife.slot(world, "밤")
    assert [len(p.body.injuries) for p in people] == before
    loner = people[0]
    for other in people[1:]:
        other.location = "북쪽 숲"
    camp.fire = None
    world.asleep = {loner.name}
    wildlife.slot(world, "밤")
    assert loner.body.injuries and loner.body.injuries[-1].kind == "깊은 상처"


def test_a_tiger_can_kill_and_a_boar_runs_down_whoever_it_comes_upon():
    world = build_world(seed=0, band_size=1, wildlife=True)
    person = next(iter(world.people.values()))
    tiger = _herd(world, "호랑이")
    tiger.place = tiger.home = person.location
    person.body.health = 40.0
    world.rng = Dice(0.0)
    wildlife.slot(world, "밤")
    assert not person.body.alive and person.body.cause_of_death == wildlife.DEATH
    other = build_world(seed=1, band_size=1, wildlife=True)
    walker = next(iter(other.people.values()))
    boar = _herd(other, "멧돼지")
    boar.place = boar.home = walker.location
    other.rng = Dice(0.0)
    wildlife.slot(other, "낮")
    assert walker.body.injuries and other.slot_features[walker.name]["위험"] == 1.0


def test_large_predators_live_only_in_worlds_with_wildlife():
    wild, tame = build_world(seed=0, band_size=1, wildlife=True), build_world(seed=0, band_size=1)
    predators = {name for name, _, _ in __import__("engine.primal.scenario", fromlist=["PREDATORS"]).PREDATORS}
    assert predators <= {h.species for h in wild.herds}
    assert not predators & {h.species for h in tame.herds} and not tame.config.wildlife
