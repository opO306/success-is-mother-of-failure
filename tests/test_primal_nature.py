import random

from engine.agentworld.model import WorldMap
from engine.primal import body as primal_body
from engine.primal import mind as minds
from engine.primal import nature
from engine.primal.config import PrimalConfig
from engine.primal.laws import Setting
from engine.primal.matter import Maker
from engine.primal.nature import Gatherable, Herd, Land, Weather

C = PrimalConfig()


def test_seasons_turn_every_ten_days_and_winter_is_cold():
    assert [nature.season_of(d, C) for d in (1, 10, 11, 21, 31, 41)] == ["봄", "봄", "여름", "가을", "겨울", "봄"]
    rng = random.Random(0)
    winter = [nature.air_temp(nature.weather_for(d, rng, C), "밤", C) for d in range(31, 41)]
    summer = [nature.air_temp(nature.weather_for(d, rng, C), "낮", C) for d in range(11, 21)]
    assert max(winter) < 5 < min(summer)


def test_a_winter_night_in_the_open_harms_and_fire_hides_and_a_roof_protect():
    exposed, cared = primal_body.PrimalBody(), primal_body.PrimalBody()
    for _ in range(4):
        primal_body.exposure(exposed, -9, False, clothing=0.0, fire=0.0, roof=0.0, warmth=0.0, exertion=0.0, c=C)
        primal_body.exposure(cared, -9, False, clothing=0.6, fire=0.7, roof=1.0, warmth=0.6, exertion=0.0, c=C)
    assert exposed.health < 100 and exposed.cold >= C.cold_harm
    assert cared.health == 100 and cared.cold < C.cold_felt


def test_rain_soaks_those_without_a_roof():
    open_air, covered = primal_body.PrimalBody(), primal_body.PrimalBody()
    primal_body.exposure(open_air, 10, True, 0.0, 0.0, roof=0.0, warmth=0.0, exertion=0.0, c=C)
    primal_body.exposure(covered, 10, True, 0.0, 0.0, roof=0.8, warmth=0.3, exertion=0.0, c=C)
    assert open_air.wet > 0 and covered.wet == 0


def test_days_without_water_kill():
    body = primal_body.PrimalBody(hydration=0.0)
    days = 0
    while body.alive and days < 30:
        primal_body.eat(body, Maker(random.Random(0)).make("고기"), C)
        body.eaten_today = 1.0
        body.slept_today = 2
        primal_body.day_update(body, C)
        days += 1
    assert not body.alive and days <= 6
    assert body.cause_of_death == "목이 말라 쓰러짐"


def test_rotten_or_poisonous_food_sickens_and_soured_fruit_intoxicates():
    maker = Maker(random.Random(0))
    sick = primal_body.PrimalBody()
    felt = primal_body.eat(sick, maker.make("붉은 버섯"), C)
    assert sick.illness >= C.illness_onset and any("속이" in line for line in felt)
    merry = primal_body.PrimalBody()
    berry = maker.make("산딸기")
    berry.props["ferment"] = 0.8
    assert any("둥실" in line for line in primal_body.eat(merry, berry, C))
    assert primal_body.capability(merry, C) < primal_body.capability(primal_body.PrimalBody(), C)


def test_the_same_afternoon_pleases_people_differently_and_wears_thin_when_repeated():
    thrill_seeker = minds.new_mind(random.Random(1), 50)
    homebody = minds.new_mind(random.Random(2), 50)
    thrill_seeker.temperament["위험"], homebody.temperament["위험"] = 1.8, 0.1
    features = {"위험": 1.0, "몸씀": 0.5}
    for mind in (thrill_seeker, homebody):
        mind.temperament["몸씀"] = 1.0
    first = minds.experience(thrill_seeker, features, "hunt:멧돼지", "멧돼지 사냥")
    assert first > minds.experience(homebody, features, "hunt:멧돼지", "멧돼지 사냥")
    for _ in range(5):
        again = minds.experience(thrill_seeker, features, "hunt:멧돼지", "멧돼지 사냥")
    assert again < first * 0.5


def test_loneliness_grows_alone_and_eases_with_company():
    mind = minds.new_mind(random.Random(0), 20)
    for _ in range(12):
        minds.slot_passes(mind, alone=True)
    lonely = mind.need["사람"]
    assert lonely > 20
    minds.experience(mind, {"함께": 1.0}, "talk", "이야기", companions=["P02"])
    assert mind.need["사람"] < lonely
    assert any("사람들 틈에 있고 싶다" in line for line in minds.felt(minds.Mind({**mind.need, "사람": 70}, mind.rise, mind.temperament)))


def test_lightning_sets_a_dry_forest_alight_and_bakes_what_lies_there():
    maker = Maker(random.Random(0))
    forest = Land("숲", "숲", gather={"나뭇가지": Gatherable("나뭇가지", 40, 60, {})}, dry_days=5)
    clay = maker.make("점토")
    clay.props.update({"moisture": 0.1, "plasticity": 0.1})
    clay.shape = "오목함"
    forest.lying.append(clay)
    storm = Weather(3, "여름", 25, True, True)
    c = PrimalConfig(lightning_share=1.0)
    assert nature.lightning({"숲": forest}, storm, random.Random(0), c, maker) == ["숲"]
    assert forest.fire and clay.p("fired") >= 1.0


def test_a_hunted_herd_moves_on_and_a_fed_one_grows_less_wary_of_the_feeder():
    m = WorldMap()
    lands = {"숲1": Land("숲1", "숲"), "숲2": Land("숲2", "숲")}
    for land in lands.values():
        m.add_place(land)
    m.connect("숲1", "숲2", 1)
    deer = Herd(1, "사슴", 8, "숲1", hunted_days=[4, 5])
    nature.herds_day([deer], lands, m, 6, "여름", random.Random(0), C)
    assert deer.place == "숲2"
    grass = Maker(random.Random(0)).make("들사과")
    before = deer.wariness("P01")
    nature.feed(deer, "P01", grass, C)
    assert deer.wariness("P01") < before and deer.wariness("P02") == deer.fear


def test_seeds_sown_in_spring_come_up_and_seeds_sown_in_winter_rot():
    maker = Maker(random.Random(0))
    spring, winter = Land("들", "초원"), Land("들2", "초원")
    nature.plant(spring, maker.make("들풀 씨앗"), 1)
    nature.plant(winter, maker.make("들풀 씨앗"), 31)
    for _ in range(10):
        nature.plantings_day(spring, "봄", C)
        nature.plantings_day(winter, "겨울", C)
    assert spring.plantings[0].grown and spring.gather["들풀 씨앗"].stock > 0
    assert winter.plantings[0].dead


def test_there_is_only_so_much_room_to_build_and_a_flimsy_hut_falls_in_a_storm():
    maker = Maker(random.Random(0))
    camp = Land("야영지", "야영지", plots=1)
    poles = [maker.make("나뭇가지") for _ in range(3)] + [maker.make("풀") for _ in range(4)]
    out = nature.build(camp, "P01", poles, "움막", slots=6, strength=1.0)
    assert out.ok and camp.structures[0].complete
    other = nature.build(camp, "P02", [maker.make("나뭇가지")], "움막", slots=1, strength=1.0)
    assert not other.ok and "자리가 없다" in other.felt[0]
    nature.storm_damage(camp, Weather(5, "여름", 20, True, True))
    assert not camp.structures and len(camp.lying) == 7


def test_a_good_hut_keeps_rain_off_and_crowding_shares_it_thin():
    maker = Maker(random.Random(0))
    camp = Land("야영지", "야영지", plots=2)
    frame = [maker.make("통나무") for _ in range(3)] + [maker.make("힘줄") for _ in range(2)]
    cover = [maker.make("나무껍질") for _ in range(4)] + [maker.make("가죽") for _ in range(2)]
    nature.build(camp, "P01", frame + cover, "움막", slots=20, strength=1.0)
    roof_alone, _ = nature.shelter_at(camp, 1)
    roof_crowd, _ = nature.shelter_at(camp, 30)
    assert roof_alone >= 0.5 > roof_crowd


def test_rain_puts_out_a_fire_in_the_open():
    maker = Maker(random.Random(0))
    camp = Land("야영지", "야영지")
    fuel = [maker.make("나뭇가지") for _ in range(3)]
    for f in fuel:
        f.props["moisture"] = 0.1
    assert nature.light_fire(camp, fuel, Setting(), C).ok
    nature.burn_slot(camp, Weather(1, "봄", 10, True, False), 1)
    assert camp.fire is None


def test_a_fire_that_does_not_catch_tells_what_was_in_hand_and_never_a_cause_that_was_not_there():
    maker = Maker(random.Random(0))
    camp = Land("야영지", "야영지")
    stone, root, twig = maker.make("강돌"), maker.make("칡뿌리"), maker.make("나뭇가지")
    twig.props["moisture"] = 0.6
    out = nature.light_fire(camp, [stone, root], Setting(), C)
    assert not out.ok and out.felt == ["강돌, 칡뿌리에는 불이 붙지 않는다"]
    assert nature.light_fire(camp, [twig], Setting(), C).felt == ["나뭇가지이(가) 눅눅해서 불이 붙지 않는다"]
    assert nature.light_fire(camp, [stone, twig], Setting(), C).felt == ["강돌에는 불이 붙지 않는다", "나뭇가지이(가) 눅눅해서 불이 붙지 않는다"]
    assert nature.light_fire(camp, [], Setting(), C).felt == ["불을 붙일 만한 것이 없다"]
    assert camp.fire is None
