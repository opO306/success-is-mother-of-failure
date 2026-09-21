"""Energy in and out of a body (design doc 4, energy balance), on the food scale the engine already uses: 1.0 is an
adult's day of food, about 2,500 kcal. Off unless PrimalConfig.energy_balance is on (the brain world turns it on).

A body spends every slot: its resting rate scaled by size, times how hard the slot's work was, plus what shivering and
fever burn. Resting rate follows Kleiber's law (metabolism grows with mass to the 3/4); strength stands in for mass, as
people have no weight in the engine. Work costs are METs from the Compendium of Physical Activities (Ainsworth et al.
2011): sleep 0.95, sitting 1.3, walking and foraging 3.5, hunting 6, fighting and fleeing 7. A forager's mixed day comes
near what Hadza foragers spend (Pontzer et al. 2012).

What is eaten beyond what was spent tops up a short store (a day's worth, as glycogen) and then fat, at 85%. A short day
draws on the short store, then on fat. Only when fat is gone does the body starve: muscle goes (strength falls) and,
after days of it, health, by the engine's starvation rules. Healthy adults starve over weeks, not days; hunger strikers
have died after 45 to 75 days. Pregnancy (+0.15 a day, about 375 kcal), giving milk (the milk's energy over 80%) and
growing (a tenth of resting rate) cost on top (lifecycle.py).

Lives are compressed (a year is 4 days) but days are not, so a day's food is still a day's food, and raising a child to
15 costs some 70 times less food in total than it does for real people. That distortion is accepted and written down
here, not corrected (decided 2026-09-15).
"""
from __future__ import annotations

KCAL_PER_UNIT = 2500.0
RESTING = 0.6              # an average adult's day at rest, about 1,500 kcal
SIZE_STRENGTH = 20.0       # the strength of the average adult whose resting day is RESTING
SLOTS_PER_DAY = 6
MET = {
    "sleep": 0.95, "rest": 1.3, "wait": 1.3, "eat": 1.3, "drink": 1.3, "drop": 1.3, "test": 1.3, "guard": 1.5,
    "give": 1.5, "heat": 1.5, "soak": 1.5, "dry": 1.5, "pick": 2.0, "fill": 2.0, "bind": 2.0, "mix": 2.0, "shape": 2.0,
    "weave": 2.0, "feed": 2.0, "fire": 2.5, "strike": 2.5, "grind": 2.5, "scrape": 2.5, "cut": 2.5, "steal": 3.0,
    "go": 3.5, "travel": 3.5, "follow": 3.5, "gather": 3.5, "fish": 3.5, "plant": 3.5, "build": 4.0, "train": 5.0,
    "hunt": 6.0, "attack": 7.0, "flee": 7.0,
}
DEFAULT_MET = 1.3
COLD_BURN, COLD_BURN_MAX = 0.4, 1.5     # extra resting-multiples per unit of cold felt (shivering), capped
FEVER_BURN = 0.15
SHORT_STORE = 1.0
STORE_EFFICIENCY = 0.85
FAT_MAX = 40.0
FAT_START = (10.0, 20.0)                 # founders: lean foragers, roughly 5 to 9 kg of fat
NEWBORN_FAT = 1.5
FAT_LOW = 2.0                            # below this the body keeps signalling hunger even on a fed day
MUSCLE_STRENGTH_PER_UNIT = 2.0
PREGNANCY = 0.15
MILK_EFFICIENCY = 0.8
GROWTH = 0.1


def resting(body) -> float:
    return RESTING * max(0.1, body.strength / SIZE_STRENGTH) ** 0.75


def slot_spend(body, main: str | None, ops: list[str], asleep: bool, illness_onset: float) -> float:
    if asleep:
        work = MET["sleep"]
    else:
        work = max([MET.get(op, DEFAULT_MET) for op in ops] + [MET.get(main, DEFAULT_MET) if main else DEFAULT_MET])
    burn = min(COLD_BURN_MAX, COLD_BURN * body.cold) + (FEVER_BURN if body.illness >= illness_onset else 0.0)
    spent = resting(body) / SLOTS_PER_DAY * (work + burn)
    body.spent_today += spent
    return spent


def settle_day(body, c) -> None:
    """Balance the day before the rest of the body's day is settled. Leaves reserve/eaten_today so that the engine's own
    day rules read it the same way: what is left in the short store, and underfed only while starving."""
    available = body.reserve + body.eaten_today - body.spent_today
    body.starving = False
    if available > SHORT_STORE:
        body.fat = min(FAT_MAX, body.fat + (available - SHORT_STORE) * STORE_EFFICIENCY)
        available = SHORT_STORE
    elif available < 0:
        drawn = min(body.fat, -available)
        body.fat -= drawn
        available += drawn
        if available < 0:
            body.starving = True
            body.strength = max(c.strength_floor, body.strength + available * MUSCLE_STRENGTH_PER_UNIT)
            available = 0.0
    body.reserve = 0.0
    body.eaten_today = 0.0 if body.starving else available + c.food_need_per_day
    body.spent_today = 0.0
