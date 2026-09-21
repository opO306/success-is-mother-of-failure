import statistics

from engine.primal import nature
from engine.primal.config import PrimalConfig
from engine.primal.scenario import LGM_SEASON_TEMP, REAL_SEASON_DAYS, build_world


def test_the_smooth_year_averages_to_each_seasons_mean_and_warms_through_spring():
    c = PrimalConfig(smooth_seasons=True)
    c.season_temp = dict(LGM_SEASON_TEMP)
    c.days_per_season = REAL_SEASON_DAYS
    days = range(1, 4 * REAL_SEASON_DAYS + 1)
    by_season = {s: [nature.annual_temp(d, c) for d in days if nature.season_of(d, c) == s] for s in nature.SEASONS}
    assert abs(statistics.mean(by_season["여름"]) - LGM_SEASON_TEMP["여름"]) < 0.3
    assert abs(statistics.mean(by_season["겨울"]) - LGM_SEASON_TEMP["겨울"]) < 0.3
    spring = by_season["봄"]
    assert spring[0] < 0 < 5.0 < spring[-1]          # a frozen start, a late spring above a plant's base warmth
    assert max(by_season["여름"]) == max(nature.annual_temp(d, c) for d in days)


def test_the_danyang_world_runs_real_seasons_on_a_smooth_year_from_mid_spring():
    world = build_world(seed=0, band_size=1, land="danyang", plants=True)
    assert world.config.days_per_season == REAL_SEASON_DAYS and world.config.smooth_seasons
    assert world.day == REAL_SEASON_DAYS // 2 + 1 and world.weather.season == "봄"
    old = build_world(seed=0, band_size=1)
    assert old.day == 1 and not old.config.smooth_seasons and old.config.days_per_season == 10
