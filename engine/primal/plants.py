"""Plants living by what the weather gives them (design doc 4, living plants). Off unless PrimalConfig.living_plants is on;
the brain world turns it on. A plant here is a stand of one kind on one land (the engine's Gatherable).

Leaves, stems and fungi grow each day in proportion to how far the day's warmth rises above the kind's base temperature
(up to the warmth it grows best in) and how moist the soil is, and frost takes them back. Seeds, nuts and fruit are not on
a calendar: a stand gathers growing degree-days from the end of winter and bears once it has had its warmth, holds the crop
for a while, then it falls or rots. Five cold days in a row end a growing year.

How much warmth a kind needs is fitted once to the climate the world runs (fruit_thresholds): the time of year it ripens
in life (pine nuts at the start of autumn, say) is placed on the simulation's own calendar, and the warmth a normal year of
that climate has gathered by that day becomes the need. So a normal year bears in season, a cold one late or not at all;
nothing is set to a date. Wood still falls, stone still lies, fish and eggs still come as before; they are not plants.

Traits are botanical starting values for temperate plants, written down, not measured on this land. Day length is not
modelled.
"""
from __future__ import annotations

from dataclasses import dataclass

from . import sky
from .config import SEASONS
from .nature import annual_temp, season_of

YEAR_ENDS_AFTER_COLD_DAYS = 5


@dataclass(frozen=True)
class Trait:
    base: float                             # °C below which it does not grow
    best: float                             # °C above which more warmth adds nothing
    grow: float = 0.0                       # share of the stand's room filled per day at best warmth on wet soil
    ripe_at: tuple[str, float] | None = None   # when it ripens in life: season and how far into it; None for leaves and fungi
    ripe_days: int = 0                      # days a crop stays before it falls or rots
    frost_loss: float = 0.1                 # share lost per freezing day
    wet: float = 0.0                        # soil moisture it needs to grow at all


# Seasons as months: spring Mar-May, summer Jun-Aug, autumn Sep-Nov, winter Dec-Feb.
TRAITS: dict[str, Trait] = {
    # Grass and Artemisia die back in the cold but stand dry through winter, the forage horses, bison and deer of the
    # glacial steppe lived on; frost only wears the standing stems slowly (it took 10% a day until 2026-09-16, which
    # left no winter food on the land at all).
    "풀": Trait(5.0, 20.0, grow=0.08, frost_loss=0.01),
    "쑥": Trait(5.0, 18.0, grow=0.06, frost_loss=0.01),
    "버섯": Trait(8.0, 18.0, grow=0.12, frost_loss=0.5, wet=0.5),
    "붉은 버섯": Trait(8.0, 18.0, grow=0.08, frost_loss=0.5, wet=0.5),
    "칡뿌리": Trait(12.0, 28.0, grow=0.02, frost_loss=0.0),
    "토란": Trait(15.0, 30.0, grow=0.03),
    "산딸기": Trait(5.0, 20.0, ripe_at=("여름", 0.3), ripe_days=12),        # late June to July
    "들풀 씨앗": Trait(5.0, 20.0, ripe_at=("여름", 0.9), ripe_days=20, frost_loss=0.0),   # late August
    "들사과": Trait(5.0, 22.0, ripe_at=("가을", 0.25), ripe_days=20),      # September
    "도토리": Trait(5.0, 22.0, ripe_at=("가을", 0.35), ripe_days=30, frost_loss=0.0),     # late September to October
    "잣": Trait(5.0, 20.0, ripe_at=("가을", 0.35), ripe_days=30, frost_loss=0.0),       # late September to October
    # Olduvai: tubers hold underground all year and are dug when wanted, baobab pods hang dry for months after the
    # rains, berries follow each rainy season, grass seed after the long rains, honey whenever a hive is found
    "덩이줄기": Trait(10.0, 30.0, grow=0.02, frost_loss=0.0),
    "바오바브 열매": Trait(12.0, 30.0, ripe_at=("여름", 0.2), ripe_days=90, frost_loss=0.0),
    "들열매": Trait(10.0, 28.0, ripe_at=("봄", 0.6), ripe_days=45),
    "벌꿀": Trait(12.0, 30.0, grow=0.01, frost_loss=0.0),
    "아카시아 씨": Trait(10.0, 30.0, ripe_at=("가을", 0.5), ripe_days=40, frost_loss=0.0),
}
_THRESHOLDS: dict[tuple, dict[str, float]] = {}


def bears_fruit(kind: str) -> bool:
    trait = TRAITS.get(kind)
    return trait is not None and trait.ripe_at is not None


def ripe_day(trait: Trait, c) -> int:
    season, share = trait.ripe_at
    return SEASONS.index(season) * c.days_per_season + int(share * c.days_per_season) + 1


NOISE_POINTS = 21


def _normal_temp(day: int, c) -> float:
    return annual_temp(day, c) if c.smooth_seasons else c.season_temp[season_of(day, c)]


def _expected_warmth(trait: Trait, temp: float, noise: float) -> float:
    """Warmth a day adds on average when its temperature scatters evenly by ±noise around temp. Clipping at the base and
    at the best makes this differ from the warmth of the average day: near the best, scatter costs warmth."""
    if noise <= 0:
        return max(0.0, min(temp, trait.best) - trait.base)
    points = [temp - noise + 2 * noise * i / (NOISE_POINTS - 1) for i in range(NOISE_POINTS)]
    return sum(max(0.0, min(t, trait.best) - trait.base) for t in points) / NOISE_POINTS


def normal_gdd(trait: Trait, c, until_day: int) -> float:
    """Degree-days a normal year of this climate has gathered by the end of until_day, counted from the start of the
    winter before so the year resets as it does in the world (a year is taken to reset on the normal curve's cold days)."""
    gdd, cold = 0.0, 0
    for day in range(1 - c.days_per_season, until_day + 1):
        temp = _normal_temp(day, c)
        cold = cold + 1 if temp < trait.base else 0
        if cold >= YEAR_ENDS_AFTER_COLD_DAYS:
            gdd = 0.0
        gdd += _expected_warmth(trait, temp, c.daily_temp_noise)
    return gdd


def fruit_thresholds(c) -> dict[str, float]:
    """Degree-days each fruiting kind needs: what a normal year of this world's climate, day-to-day scatter included,
    has gathered by the day it ripens on the simulation's calendar."""
    key = (c.days_per_season, c.smooth_seasons, c.daily_temp_noise, tuple(sorted(c.season_temp.items())))
    if key not in _THRESHOLDS:
        _THRESHOLDS[key] = {kind: max(1.0, normal_gdd(trait, c, ripe_day(trait, c)))
                            for kind, trait in TRAITS.items() if trait.ripe_at is not None}
    return _THRESHOLDS[key]


def plants_day(land, weather, c) -> None:
    """One day of growing on a land, under that day's weather. A place's pasture grows and weathers as its grass does."""
    temp = weather.base_temp
    if land.pasture_cap > 0:
        grass = TRAITS["풀"]
        warmth = max(0.0, min(temp, grass.best) - grass.base)
        if warmth > 0:
            share = warmth / (grass.best - grass.base)
            daylight = min(1.2, max(0.6, sky.day_length(weather.day, c) / 12.0)) if getattr(c, "sky", False) else 1.0
            land.pasture = min(land.pasture_cap, land.pasture + land.pasture_cap * grass.grow * share * daylight
                               * min(1.0, land.soil_moisture / 0.5))
        if temp < 0:
            land.pasture *= 1.0 - grass.frost_loss
    for kind, stand in land.gather.items():
        trait = TRAITS.get(kind)
        if trait is None:
            stand.stock = min(stand.cap, stand.stock + stand.regen.get(weather.season, 0.0))
            continue
        stand.cold_days = stand.cold_days + 1 if temp < trait.base else 0
        if stand.cold_days >= YEAR_ENDS_AFTER_COLD_DAYS:
            stand.gdd, stand.bore = 0.0, False
        warmth = max(0.0, min(temp, trait.best) - trait.base)
        stand.gdd += warmth
        if trait.ripe_at is None:
            if warmth > 0 and land.soil_moisture >= trait.wet:
                share = warmth / (trait.best - trait.base)
                daylight = min(1.2, max(0.6, sky.day_length(weather.day, c) / 12.0)) if getattr(c, "sky", False) else 1.0
                stand.stock = min(stand.cap, stand.stock + stand.cap * trait.grow * share * daylight * min(1.0, land.soil_moisture / 0.5))
            if temp < 0:
                stand.stock *= 1.0 - trait.frost_loss
        elif not stand.bore and stand.gdd >= fruit_thresholds(c)[kind]:
            stand.stock = stand.cap * min(1.0, 0.5 + land.soil_moisture)
            stand.bore, stand.ripe_left = True, trait.ripe_days
        elif stand.ripe_left > 0:
            stand.ripe_left -= 1
            if stand.ripe_left == 0:
                # the crop is gone, and the stand begins gathering warmth for the next one. In a cold land the five
                # cold days did this; on a plain that never freezes nothing ever reset it, so a tree bore once and
                # never again (found when the Olduvai land was built, 2026-09-17).
                stand.stock, stand.gdd, stand.bore = 0.0, 0.0, False
