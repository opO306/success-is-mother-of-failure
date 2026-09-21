import random

from engine.brain import senses
from engine.primal import nature
from engine.primal.actions import _HANDLERS
from engine.primal.clerk import Step
from engine.primal.nature import Weather
from engine.primal.scenario import build_world


def test_rain_stands_longest_in_rock_hollows_dries_by_season_and_freezes():
    hill, camp, river = nature.Land("바위", "언덕"), nature.Land("터", "야영지"), nature.Land("물가", "강", water="맑은 물")
    storm = Weather(1, "여름", 24.0, True, True)
    for land in (hill, camp, river):
        nature.puddles_day(land, storm)
    assert hill.puddle == 6.0 and camp.puddle == 2.0 and river.puddle == 0.0
    dry = Weather(2, "여름", 24.0, False, False)
    nature.puddles_day(hill, dry)
    nature.puddles_day(camp, dry)
    assert hill.puddle == 5.0 and camp.puddle == 1.0
    assert nature.puddle_water(hill, dry) == "고인 물"
    assert nature.puddle_water(hill, Weather(3, "겨울", -4.0, False, False)) is None


def test_after_rain_a_camp_has_still_water_to_drink_and_see_but_only_in_worlds_with_puddles():
    world = build_world(seed=0, band_size=1, puddles=True)
    person = next(iter(world.people.values()))
    land = world.lands[person.location]
    world.weather = Weather(world.day, "봄", 12.0, False, False)
    assert not _HANDLERS["drink"](world, person, Step(op="drink"), "낮", []).ok
    land.puddle = 1.0
    assert any(t.category == senses.CATEGORIES["water"] for t in senses.water_tokens(world, person))
    out = _HANDLERS["drink"](world, person, Step(op="drink"), "낮", [])
    assert out.ok and person.body.poison > 0 and land.puddle < 1.0
    old = build_world(seed=0, band_size=1)
    walker = next(iter(old.people.values()))
    old.lands[walker.location].puddle = 1.0
    assert not _HANDLERS["drink"](old, walker, Step(op="drink"), "낮", []).ok
