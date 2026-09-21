"""The sky as causes (design doc 4): the sun's day and the moon's month over a land at the Danyang/Jecheon latitude. Off
unless PrimalConfig.sky is on; the brain world turns it on. Only what reaches a body is modelled: how long the day is,
how light each slot is, how full the moon is. What anyone makes of the sky is theirs.

Day length follows the standard sunrise equation for the latitude and the day of the year (solar declination from
Cooper's formula). A world's day 1 is the first day of spring, taken as 1 March; however long its seasons, a world's year
is mapped onto the calendar year. Slots are four hours around fixed clock times. The moon waxes and wanes on the synodic
month (29.53 days); a full moon lights a night a little, a fire lights the place it burns.
"""
from __future__ import annotations

import math

LATITUDE = 37.05
SYNODIC_MONTH = 29.530589
MARCH_FIRST = 59                     # day of the year before which a world's first spring day falls
SLOT_CENTER_HOURS = {"새벽": 5.0, "아침": 9.0, "낮": 13.0, "오후": 17.0, "저녁": 21.0, "밤": 1.0}
MOONLIGHT = 0.25                     # how much a full moon lights an open night, on the daylight scale
FIRELIGHT = 0.6                      # how much a fire lights the place it burns in


def day_of_year(day: int, c) -> float:
    year = c.days_per_season * 4
    return (MARCH_FIRST + ((day - 1) % year) / year * 365.0) % 365.0


def day_length(day: int, c, latitude: float | None = None) -> float:
    """Hours between sunrise and sunset, at this world's latitude."""
    latitude = getattr(c, "latitude", LATITUDE) if latitude is None else latitude
    declination = math.radians(23.44) * math.sin(2 * math.pi * (284 + day_of_year(day, c)) / 365.0)
    cos_hour = -math.tan(math.radians(latitude)) * math.tan(declination)
    return 24.0 * math.acos(max(-1.0, min(1.0, cos_hour))) / math.pi


def daylight(slot: str, day: int, c) -> float:
    """Share of a slot's four hours the sun is up."""
    half = day_length(day, c) / 2
    sunrise, sunset = 12.0 - half, 12.0 + half
    center = SLOT_CENTER_HOURS[slot]
    start, end = center - 2.0, center + 2.0
    lit = 0.0
    for shift in (-24.0, 0.0, 24.0):
        lit += max(0.0, min(end, sunset + shift) - max(start, sunrise + shift))
    return min(1.0, lit / 4.0)


def moon_fullness(day: int) -> float:
    """0 at new moon, 1 at full moon."""
    phase = ((day - 1) % SYNODIC_MONTH) / SYNODIC_MONTH
    return (1 - math.cos(2 * math.pi * phase)) / 2


def light(slot: str, day: int, c, fire: bool = False, raining: bool = False) -> float:
    sun = daylight(slot, day, c)
    moon = MOONLIGHT * moon_fullness(day) * (1.0 - sun) * (0.3 if raining else 1.0)
    return min(1.0, max(sun + moon, FIRELIGHT if fire else 0.0))


def circadian_pressure(slot: str, shift_hours: float, lit: float) -> float:
    """How strongly a body clock pushes toward sleep this slot: highest around 3 a.m. of that person's clock (earlier for
    larks, later for owls), and held down by light on the eyes."""
    hour = SLOT_CENTER_HOURS[slot]
    peak = 3.0 + shift_hours
    return (1 + math.cos(2 * math.pi * (hour - peak) / 24.0)) / 2 * (1.0 - 0.7 * lit)
