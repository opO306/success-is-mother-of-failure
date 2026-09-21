from __future__ import annotations

from dataclasses import dataclass, field

from ..agentworld.config import SLOTS, WorldConfig

SEASONS = ("봄", "여름", "가을", "겨울")
NIGHT = frozenset({"새벽", "밤"})


def _season_temps() -> dict[str, float]:
    return {"봄": 12.0, "여름": 24.0, "가을": 11.0, "겨울": -4.0}


def _slot_offsets() -> dict[str, float]:
    return {"새벽": -5.0, "아침": -2.0, "낮": 3.0, "오후": 4.0, "저녁": 0.0, "밤": -4.0}


def _rain() -> dict[str, float]:
    return {"봄": 0.35, "여름": 0.3, "가을": 0.25, "겨울": 0.2}


@dataclass
class PrimalConfig(WorldConfig):
    """Starting physical constants of the primal land. Inherits the body constants of the industrial world."""

    days_per_season: int = 10
    season_temp: dict[str, float] = field(default_factory=_season_temps)
    slot_temp_offset: dict[str, float] = field(default_factory=_slot_offsets)
    daily_temp_noise: float = 3.0
    rain_chance: dict[str, float] = field(default_factory=_rain)
    storm_share: float = 0.25
    lightning_share: float = 0.4

    # warmth: what a body feels is air temperature plus what it wears, sits by, and sleeps under
    comfort_temp: float = 8.0
    clothing_warmth: float = 15.0
    fire_warmth: float = 12.0
    shelter_warmth: float = 8.0
    wet_chill: float = 6.0
    exertion_warmth: float = 4.0
    cold_felt: float = 1.0
    cold_harm: float = 3.0
    cold_health_loss: float = 2.0
    heat_harm_temp: float = 32.0

    # water
    water_need_per_day: float = 1.0
    thirst_harm_days: int = 2
    thirst_health_loss: float = 30.0

    # food and drink effects
    poison_illness: float = 0.5
    intoxication_factor: float = 0.8

    # mind
    need_start: float = 20.0
    talent: bool = True   # off: everyone learns at the average rate up to the average ceiling (talent.py)
    energy_balance: bool = False   # on: spending by work, size and cold, fat stores (energy.py); the brain world uses it
    wildlife: bool = False         # on: animals drink, stalk and charge through the day (wildlife.py); the brain world uses it
    puddles: bool = False          # on: rain stands in hollows for days (nature.puddles_day); the brain world uses it
    living_plants: bool = False    # on: plants grow by warmth and moisture and bear by degree-days (plants.py)
    smooth_seasons: bool = False   # on: the day's temperature follows a year-long curve through the season means (nature.annual_temp)
    sky: bool = False              # on: day length, light per slot and the moon (sky.py)
    graded_feelings: bool = False  # on: continuous felt levels, adrenaline and cortisol, sleep that can be spoiled (body.felt_levels)
    animal_minds: bool = False     # on: herds live by their own water, food, fear and hunger (animals.py) instead of wildlife.py
    latitude: float = 37.05        # where the land sits, for day length and the body clock (sky.py)
    sleep_switch: bool = False     # on: asleep or awake flips by sleep pressure and clock against arousal (body.sleep_switch);
                                   # choosing sleep only lies the body down, and no debt forces a collapse

    # land
    fire_fuel_slots_per_weight: float = 6.0
    lightning_needs_dry_days: int = 2
    wildfire_slots: int = 3
    herd_fear_after_hunt: float = 0.35
    herd_flee_fear: float = 0.6
    feed_fear_drop: float = 0.15
    spring_birth_rate: float = 0.3
    wolf_pack_min: int = 3
    planting_growth_days: float = 5.0


__all__ = ["PrimalConfig", "SEASONS", "SLOTS", "NIGHT"]
