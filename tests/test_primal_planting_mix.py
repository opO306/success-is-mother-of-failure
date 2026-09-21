from engine.primal import laws, nature
from engine.primal.config import PrimalConfig
from engine.primal.scenario import build_world


def _grow(land, c):
    for _ in range(200):   # a mixture carries only part of its seeds' germination, so it comes up slowly
        nature.plantings_day(land, "봄", c)


def test_a_buried_mixture_of_pine_nuts_sprouts_pine_that_can_be_gathered():
    world = build_world(seed=0, band_size=1)
    c = world.config
    land = next(l for l in world.lands.values() if l.kind == "숲")
    land.soil_moisture = 0.6
    setting = nature.setting_at(land, world.weather, "낮", c, 0)
    out = laws.mix([world.maker.make("잣"), world.maker.make("풀")], world.maker, setting)
    blend = out.made[0]
    assert blend.kind == "섞은 것" and blend.p("germination") > 0
    nature.plant(land, blend, world.day)
    _grow(land, c)
    assert "섞은 것" not in land.gather and land.gather["잣"].stock >= 1
    gathered = nature.gather(land, "잣", 1, 1.0, 0.0, world.maker, "봄")
    assert gathered.ok and all(t.kind == "잣" for t in gathered.made)


def test_a_mixture_with_no_seed_in_it_does_not_grow():
    world = build_world(seed=0, band_size=1)
    land = next(l for l in world.lands.values() if l.kind == "숲")
    blend = world.maker.derive("섞은 것", {"germination": 0.2})
    nature.plant(land, blend, world.day)
    assert land.plantings[-1].dead
