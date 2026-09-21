import random

from engine.primal import body as physiology
from engine.primal import laws
from engine.primal.body import PrimalBody
from engine.primal.config import PrimalConfig
from engine.primal.laws import Setting
from engine.primal.matter import Maker


def _fish(lodge=None):
    fish = Maker(random.Random(0)).make("물고기")
    if lodge is not None:
        fish.props["bone_lodge"] = lodge
    return fish


def test_every_fish_is_made_with_its_own_lie_of_bones():
    maker = Maker(random.Random(3))
    lodges = {round(maker.make("물고기").p("bone_lodge"), 6) for _ in range(20)}
    assert len(lodges) == 20 and all(0.0 <= v <= 1.0 for v in lodges)


def test_a_bone_sticks_by_its_size_its_lie_and_a_hungry_gulp_never_by_a_roll():
    c = PrimalConfig()
    lying_badly = PrimalBody()
    felt = physiology.eat(lying_badly, _fish(lodge=1.0), c)
    assert lying_badly.injuries and any("가시" in f for f in felt)
    lying_flat = PrimalBody()
    physiology.eat(lying_flat, _fish(lodge=0.5), c)
    assert not lying_flat.injuries
    starving = PrimalBody(underfed_days=c.starvation_after_days, reserve=0.0)
    assert physiology.distress(starving, c).get("hunger", 0.0) == 1.0
    physiology.eat(starving, _fish(lodge=0.5), c)
    assert starving.injuries                          # the same fish, gulped
    again = PrimalBody()
    physiology.eat(again, _fish(lodge=1.0), c)
    assert again.injuries                             # same fish, same eater, same outcome


def test_cutting_out_the_bones_or_cooking_removes_the_cause():
    c = PrimalConfig()
    maker = Maker(random.Random(1))
    boned = _fish(lodge=1.0)
    flake = maker.derive("부싯돌 조각", {"hardness": 0.8, "brittleness": 0.8, "sharpness": 0.5, "weight": 0.08})
    assert laws.cut(boned, flake, 1.0, maker).ok and boned.p("bones") < 0.3
    clean = PrimalBody()
    physiology.eat(clean, boned, c)
    assert not clean.injuries
    cooked = _fish(lodge=1.0)
    laws.heat(cooked, 3, Setting(fire=0.8), maker)
    eater = PrimalBody()
    physiology.eat(eater, cooked, c)
    assert not eater.injuries and eater.parasites == 0.0


def test_raw_fish_leaves_flukes_that_make_illness_only_weeks_later_and_heat_kills_them():
    c = PrimalConfig()
    body = PrimalBody()
    for _ in range(3):
        physiology.eat(body, _fish(lodge=0.0), c)
    assert body.parasites >= physiology.PARASITE_LOAD and body.illness < c.illness_onset
    for _ in range(physiology.PARASITE_LATENCY - 1):
        body.hydration, body.eaten_today, body.slept_today = 1.5, 1.0, 2
        physiology.day_update(body, c)
        assert body.illness < c.illness_onset
    body.hydration, body.eaten_today, body.slept_today = 1.5, 1.0, 2
    physiology.day_update(body, c)
    assert body.parasite_days >= physiology.PARASITE_LATENCY
    fish = _fish()
    laws.heat(fish, 3, Setting(fire=0.8), Maker(random.Random(2)))
    assert fish.p("cooked") >= 1.0 and fish.p("parasites") == 0.0 and fish.p("bones") < 0.3
