import random
import re

import pytest

from engine.primal import laws
from engine.primal.laws import Setting
from engine.primal.matter import Maker
from engine.primal.senses import FORBIDDEN, describe

FELT: list[str] = []


@pytest.fixture
def maker():
    return Maker(random.Random(0))


def keep(outcome):
    FELT.extend(outcome.felt)
    return outcome


def test_brittle_stone_struck_by_harder_stone_sheds_sharp_flakes(maker):
    flint, hammer = maker.make("부싯돌"), maker.make("강돌")
    out = keep(laws.strike(hammer, flint, strength=1.0, skill=1.0, maker=maker, rng=random.Random(1)))
    assert out.made and max(f.p("sharpness") for f in out.made) >= 0.35


def test_tough_stone_does_not_flake_and_a_soft_hammer_only_hurts_itself(maker):
    river, flint = maker.make("강돌"), maker.make("부싯돌")
    assert not keep(laws.strike(flint, river, 1.0, 1.0, maker, random.Random(1))).made
    stick = maker.make("나뭇가지")
    out = keep(laws.strike(stick, flint, 1.0, 1.0, maker, random.Random(1)))
    assert not out.made and stick.p("hardness") < 0.35


def test_heated_flint_breaks_more_easily_though_nobody_is_told(maker):
    flint = maker.make("부싯돌")
    before = flint.p("brittleness")
    out = keep(laws.heat(flint, 3, Setting(fire=0.5), maker))
    assert flint.p("brittleness") > before
    assert "빛깔" in out.felt[0]


def test_wet_clay_bursts_in_the_fire(maker):
    clay = maker.make("점토")
    keep(laws.mix([clay, maker.make("물")], maker, Setting()))
    keep(laws.shape(clay, "오목하게"))
    keep(laws.heat(clay, 3, Setting(fire=0.7), maker))
    assert clay.p("concavity") == 0.0 and clay.p("fired") < 1.0


def test_shaped_dried_and_fired_clay_holds_water_and_unfired_does_not(maker):
    fired, raw = maker.make("점토"), maker.make("점토")
    for clay in (fired, raw):
        keep(laws.mix([clay, maker.make("물")], maker, Setting()))
        keep(laws.shape(clay, "오목하게"))
        keep(laws.dry(clay, 8, Setting(temp=20)))
    keep(laws.heat(fired, 4, Setting(fire=0.7), maker))
    assert fired.p("fired") >= 1.0 and fired.p("hardness") >= 0.65
    here = Setting(water_here=True)
    assert "새지 않았다" in keep(laws.test(fired, "물을 부어 본다", "P01", here, 1.0)).felt[0]
    assert "스며" in keep(laws.test(raw, "물을 부어 본다", "P01", here, 1.0)).felt[0]


def test_nobody_knows_it_holds_water_until_they_pour_some_in(maker):
    bowl = maker.make("점토")
    bowl.shape, bowl.props.update({"concavity": 0.9, "fired": 2.0, "porosity": 0.1, "hardness": 0.8})
    assert "물이 새지 않음" not in describe(bowl, "P01")
    laws.test(bowl, "물을 부어 본다", "P01", Setting(water_here=True), 1.0)
    assert "물이 새지 않음" in describe(bowl, "P01")
    assert "물이 새지 않음" not in describe(bowl, "P02")


def test_cooking_takes_the_poison_out_of_a_bitter_root(maker):
    taro = maker.make("토란")
    before = taro.p("toxicity")
    keep(laws.heat(taro, 2, Setting(fire=0.6), maker))
    assert taro.p("toxicity") <= before * 0.3 + 1e-9


def test_boiling_in_a_watertight_vessel_leaches_more_than_roasting(maker):
    pot = maker.make("점토")
    pot.shape, pot.props.update({"concavity": 0.9, "fired": 2.0, "porosity": 0.1, "hardness": 0.8})
    acorn = maker.make("도토리")
    pot.contents = [maker.make("물"), acorn]
    before = acorn.p("toxicity")
    keep(laws.heat(pot, 2, Setting(fire=0.6), maker))
    assert acorn.p("toxicity") <= before * 0.15 + 1e-9


def test_sweet_fruit_shut_away_turns_sour_and_fruit_left_out_rots(maker):
    sealed, open_air = maker.make("산딸기"), maker.make("산딸기")
    for _ in range(3):
        laws.day_passes(sealed, 18, sealed=True)
        laws.day_passes(open_air, 18, sealed=False)
    assert sealed.p("ferment") > 0.5 and sealed.p("spoil") < 0.5
    assert open_air.p("spoil") > sealed.p("spoil")


def test_a_scraped_dried_hide_keeps_warm_and_an_unscraped_one_rots(maker):
    good, bad = maker.make("가죽"), maker.make("가죽")
    flake = maker.derive("부싯돌 조각", {"sharpness": 0.6, "hardness": 0.8, "weight": 0.08})
    keep(laws.scrape(good, flake, 2))
    for hide in (good, bad):
        laws.day_passes(hide, 15, sealed=False)
        keep(laws.dry(hide, 12, Setting(temp=20)))
    assert good.p("insulation") >= 0.6
    assert bad.p("insulation") < 0.6 and bad.p("spoil") > 0


def test_a_sharp_flake_bound_to_a_stick_cuts_far_better_than_the_flake_alone(maker):
    flake = maker.derive("부싯돌 조각", {"sharpness": 0.6, "hardness": 0.8, "weight": 0.08})
    stick, sinew = maker.make("나뭇가지"), maker.make("힘줄")
    joined = keep(laws.bind([stick, flake], sinew, maker)).made[0]
    assert laws.cutting_power(joined, 1.0) > laws.cutting_power(flake, 1.0) * 1.5


def test_a_carcass_yields_meat_hide_and_bone_to_a_sharp_edge_only(maker):
    carcass = maker.derive("사슴 사체", {"hardness": 0.3, "fiber": 0.5, "weight": 3.0})
    dull = maker.make("강돌")
    assert not keep(laws.cut(carcass, dull, 1.0, maker)).ok
    flake = maker.derive("부싯돌 조각", {"sharpness": 0.7, "hardness": 0.8, "weight": 0.08})
    out = keep(laws.cut(carcass, flake, 1.0, maker))
    assert {t.kind for t in out.made} >= {"고기", "가죽"}


def test_nothing_the_laws_say_names_a_technique_a_property_or_a_number():
    assert FELT, "run with the other tests in this file"
    for line in FELT:
        for word in FORBIDDEN:
            assert word not in line, (word, line)
        assert not re.search(r"\d+\.\d", line), line
