import math

from engine.primal import nature, plants
from engine.primal.config import PrimalConfig
from engine.primal.nature import Gatherable, Land, Weather
from engine.primal.scenario import LGM_SEASON_TEMP, REAL_SEASON_DAYS, build_world


def _glacial():
    c = PrimalConfig(smooth_seasons=True, living_plants=True)
    c.season_temp = dict(LGM_SEASON_TEMP)
    c.days_per_season = REAL_SEASON_DAYS
    return c


def _day(temp, season="봄"):
    return Weather(1, season, temp, False, False)


def test_leaves_grow_with_warmth_and_wet_soil_and_frost_takes_them_back():
    c = _glacial()
    warm, cool, dry = Land("a", "초원"), Land("b", "초원"), Land("c", "초원")
    for land in (warm, cool, dry):
        land.gather["풀"] = Gatherable("풀", 10.0, 60.0, {})
    dry.soil_moisture = 0.1
    plants.plants_day(warm, _day(20.0), c)
    plants.plants_day(cool, _day(8.0), c)
    plants.plants_day(dry, _day(20.0), c)
    assert warm.gather["풀"].stock > cool.gather["풀"].stock > 10.0
    assert warm.gather["풀"].stock > dry.gather["풀"].stock
    plants.plants_day(warm, _day(-5.0, "겨울"), c)
    assert warm.gather["풀"].stock < 60.0 * 0.95


def _first_crop(kind, c, rng=None):
    land = Land("곳", "숲")
    land.gather[kind] = Gatherable(kind, 0.0, 30.0, {})
    for day in range(1 - c.days_per_season, 4 * c.days_per_season):
        noise = rng.uniform(-c.daily_temp_noise, c.daily_temp_noise) if rng else 0.0
        plants.plants_day(land, Weather(day, nature.season_of(day, c), nature.annual_temp(day, c) + noise, False, False), c)
        if land.gather[kind].bore:
            return day
    return None


def test_a_year_without_scatter_bears_each_crop_on_its_own_day_of_the_simulated_calendar():
    c = _glacial()
    c.daily_temp_noise = 0.0
    for kind in ("잣", "들풀 씨앗"):
        assert _first_crop(kind, c) == plants.ripe_day(plants.TRAITS[kind], c)
    assert plants.ripe_day(plants.TRAITS["잣"], c) > 2 * c.days_per_season           # autumn, not summer


def test_years_with_the_worlds_daily_scatter_bear_around_that_day():
    import random
    import statistics
    c = _glacial()
    for kind in ("잣", "들풀 씨앗"):
        days = [_first_crop(kind, c, random.Random(seed)) for seed in range(30)]
        bore = [d for d in days if d is not None]
        assert len(bore) >= 0.7 * len(days)        # a year cool enough can pass without a crop, as the law intends
        assert abs(statistics.mean(bore) - plants.ripe_day(plants.TRAITS[kind], c)) <= 7


def test_warmth_not_dates_decides_a_crop_hangs_a_while_and_a_cold_spell_starts_a_new_year():
    c = _glacial()
    need = plants.fruit_thresholds(c)["잣"]
    land = Land("숲", "숲")
    land.gather["잣"] = Gatherable("잣", 0.0, 30.0, {})
    stand = land.gather["잣"]
    days = 0
    while stand.stock == 0.0:
        plants.plants_day(land, _day(20.0, "여름"), c)
        days += 1
    assert days == math.ceil(need / 15.0) and stand.bore              # a hot run bears early
    for _ in range(plants.TRAITS["잣"].ripe_days):
        plants.plants_day(land, _day(20.0, "가을"), c)
    assert stand.stock == 0.0
    for _ in range(plants.YEAR_ENDS_AFTER_COLD_DAYS):
        plants.plants_day(land, _day(-10.0, "겨울"), c)
    assert stand.gdd == 0.0 and not stand.bore
    cold = Land("고지대", "숲")
    cold.gather["잣"] = Gatherable("잣", 0.0, 30.0, {})
    for _ in range(int(need / 2.0) - 1):
        plants.plants_day(cold, _day(7.0), c)
    assert cold.gather["잣"].stock == 0.0                             # a cold year has not had the warmth yet


def test_the_glacial_danyang_land_grows_pine_and_mugwort_and_nothing_has_borne_on_the_first_day():
    world = build_world(seed=0, band_size=1, land="danyang", plants=True)
    kinds = {k for land in world.lands.values() for k in land.gather}
    assert {"잣", "쑥"} <= kinds and not {"칡뿌리", "토란", "도토리", "산딸기"} & kinds
    assert all(s.stock == 0.0 for land in world.lands.values() for k, s in land.gather.items() if plants.bears_fruit(k))
    assert world.config.living_plants
    assert all(t.kind != "칡뿌리" for p in world.people.values() for t in p.carried)
