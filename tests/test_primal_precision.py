import random
import statistics

from engine.primal import laws, nature
from engine.primal.laws import Setting
from engine.primal.matter import Maker
from engine.primal.senses import FORBIDDEN

FELT: list[str] = []


def keep(outcome):
    FELT.extend(outcome.felt)
    return outcome


def test_a_hand_is_steadier_with_practice_and_wavers_less():
    rng = random.Random(0)
    novice = [laws.steadiness(0.0, rng) for _ in range(2000)]
    practised = [laws.steadiness(3.0, rng) for _ in range(2000)]
    assert abs(statistics.mean(novice) - 0.3) < 0.01 and min(novice) >= 0.16 - 1e-9
    assert statistics.mean(practised) > 0.9 and statistics.stdev(practised) < statistics.stdev(novice) / 5


def _bowl(steady, fire_slots):
    maker = Maker(random.Random(0))
    clay = maker.make("점토")
    keep(laws.mix([clay, maker.make("물")], maker, Setting()))
    keep(laws.shape(clay, "오목하게", steady))
    keep(laws.dry(clay, 8, Setting(temp=20)))
    keep(laws.heat(clay, fire_slots, Setting(fire=0.7), maker))
    return clay


def test_an_unsteady_hand_makes_a_bowl_that_seeps_where_a_steady_one_holds_and_longer_firing_closes_it():
    here = Setting(water_here=True)
    assert "새지 않았다" in keep(laws.test(_bowl(0.9, 4), "물을 부어 본다", "P01", here, 1.0)).felt[0]
    assert "스며" in keep(laws.test(_bowl(0.3, 4), "물을 부어 본다", "P01", here, 1.0)).felt[0]
    assert "새지 않았다" in keep(laws.test(_bowl(0.3, 6), "물을 부어 본다", "P01", here, 1.0)).felt[0]


def test_a_lopsided_hollow_is_felt_at_once_and_pours_water_off():
    maker = Maker(random.Random(0))
    clay = maker.make("점토")
    keep(laws.mix([clay, maker.make("물")], maker, Setting()))
    assert "기울어" in keep(laws.shape(clay, "오목하게", 0.05)).felt[0]
    assert "흘러내린다" in keep(laws.test(clay, "물을 부어 본다", "P01", Setting(water_here=True), 1.0)).felt[0]


def test_the_same_cord_holds_tighter_in_a_steady_hand():
    def bound(steady):
        maker = Maker(random.Random(0))
        cord = maker.derive("힘줄", {"fiber": 0.7, "weight": 0.05})
        return keep(laws.bind([maker.make("나뭇가지"), maker.make("나뭇가지")], cord, maker, steady))

    tight, loose = bound(1.0), bound(0.3)
    assert tight.made[0].p("binding") > loose.made[0].p("binding")
    assert "단단히" in tight.felt[0] and "헐겁" in loose.felt[0]


def test_a_steady_hand_weaves_a_closer_net_and_a_real_hollow():
    def woven(form, steady):
        maker = Maker(random.Random(0))
        strands = [maker.derive("풀", {"fiber": 0.6, "flexibility": 0.6, "weight": 0.05}) for _ in range(3)]
        return keep(laws.weave(strands, form, maker, steady))

    assert woven("넓게", 0.95).made[0].props["mesh"] > woven("넓게", 0.3).made[0].props["mesh"]
    assert "들쭉날쭉" in woven("넓게", 0.3).felt[0]
    flat = woven("오목하게", 0.1)
    assert flat.made[0].p("concavity") < 0.5 and "펑퍼짐" in flat.felt[0]
    assert woven("오목하게", 0.9).made[0].p("concavity") >= 0.5


def test_the_same_time_grinding_or_scraping_goes_further_in_a_steady_hand():
    def ground(steady):
        maker = Maker(random.Random(0))
        blade = maker.derive("부싯돌 조각", {"sharpness": 0.2, "hardness": 0.8, "weight": 0.2})
        keep(laws.grind(blade, maker.make("사암"), 2, "", steady))
        return blade.p("sharpness")

    def scraped(steady):
        maker = Maker(random.Random(0))
        hide = maker.make("가죽")
        keep(laws.scrape(hide, maker.derive("부싯돌 조각", {"sharpness": 0.6, "hardness": 0.8, "weight": 0.08}), 1, steady))
        return hide.p("scraped")

    assert ground(1.0) > ground(0.3)
    assert scraped(1.0) > scraped(0.3)


def test_a_hut_built_by_unsteady_hands_keeps_less_rain_off_and_stands_weaker():
    def hut(steady):
        maker = Maker(random.Random(0))
        camp = nature.Land("야영지", "야영지", plots=2)
        frame = [maker.make("통나무") for _ in range(3)] + [maker.make("힘줄") for _ in range(2)]
        cover = [maker.make("나무껍질") for _ in range(4)] + [maker.make("가죽") for _ in range(2)]
        out = keep(nature.build(camp, "P01", frame + cover, "움막", slots=20, strength=1.0, steady=steady))
        return camp.structures[0], out

    good, _ = hut(1.0)
    poor, out = hut(0.3)
    assert poor.roof < good.roof and poor.stability < good.stability
    assert "엉성" in out.felt[-1]


def test_what_hands_feel_never_names_the_engine():
    assert FELT, "run with the other tests in this file"
    for line in FELT:
        for word in FORBIDDEN:
            assert word not in line, (word, line)
