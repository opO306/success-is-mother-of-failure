"""What each person can come to do well: how fast practice turns into skill, and where that skill stops, per family of work.

Talent is never the odds of success. It only shapes the skill; what the skill does is still the laws' (a sharper flake,
more roots gathered). Nobody is told their talent. They find it out the way anyone does, from what comes of their hands.

How widely people differ follows Hunter, Schmidt & Judiesch (1990): the output of people doing the same job spreads 19%
of the mean in simple work, 32% in middling and 48% in complex work. Body work takes 23%, the spread the starting
strength (12-28) already has. Both values are log-normal with mean 1, so most people sit near the middle, a rare few
reach far above it, and nobody's ceiling falls below zero.

These are spreads of talent, not of outcomes: practice adds its own spread on top. tools/talent_spread.py measures the
outcomes so the numbers get checked against the study instead of trusted.
"""
from __future__ import annotations

import math
import random

from .. import recorder as recording
from .world import Person, World

SPREAD = {"repeat": 0.19, "body": 0.23, "perceive": 0.32, "hand": 0.48}
FAMILY = {
    **dict.fromkeys(("gather", "pick", "fill", "eat", "drink"), "repeat"),
    **dict.fromkeys(("build", "train", "attack"), "body"),
    **dict.fromkeys(("hunt", "fish", "steal", "test"), "perceive"),
    **dict.fromkeys(("strike", "grind", "scrape", "cut", "weave", "bind", "shape"), "hand"),
}
GAIN = 0.1  # what one time adds from nothing for an average learner, as it did for everyone before talent
# Where an average person's skill stops. Striking already stopped at 1.0 for everyone. Gathering, fishing, hunting and
# stealing had no stop; in the first 18-day worlds nobody's went past 1.4, so 5 leaves the average person about where
# they were. Work whose laws do not use skill yet gets 1.0, the scale precision will be given in when it enters them.
CEILING = {"strike": 1.0, "gather": 5.0, "fish": 5.0, "hunt": 5.0, "steal": 5.0}
DEFAULT_CEILING = 1.0


def _lognormal(rng: random.Random, spread: float) -> float:
    sigma = math.sqrt(math.log(1 + spread ** 2))
    return rng.lognormvariate(-sigma ** 2 / 2, sigma)


def draw(seed: int | None, name: str) -> dict[str, dict[str, float]]:
    # its own stream, so a world with talent and one without, from the same seed, get the same weather and people
    rng = random.Random(f"talent:{seed}:{name}")
    return {family: {"rate": _lognormal(rng, spread), "ceiling": _lognormal(rng, spread)} for family, spread in SPREAD.items()}


def practice(person: Person) -> dict[str, int]:
    """How many times they have done each thing."""
    return person.__dict__.setdefault("practice", {})


def of(world: World, person: Person) -> dict[str, dict[str, float]]:
    found = person.__dict__.get("talent")
    if found is not None:
        return found
    if world.config.talent:
        found = draw(world.seed, person.name)
    else:
        found = {family: {"rate": 1.0, "ceiling": 1.0} for family in SPREAD}
    person.__dict__["talent"] = found
    # someone from a snapshot made before talent: their skill was 0.1 per time done with no stop, so it is lived again
    old = dict(person.skills)
    person.skills.clear()
    practice(person).clear()
    for op, value in old.items():
        for _ in range(round(value / GAIN)):
            practise(world, person, op)
    return found


def settle(world: World) -> None:
    for person in world.people.values():
        of(world, person)


def _family(world: World, person: Person, op: str) -> dict[str, float]:
    family = FAMILY.get(op)
    return of(world, person)[family] if family else {"rate": 1.0, "ceiling": 1.0}


def ceiling(world: World, person: Person, op: str) -> float:
    return CEILING.get(op, DEFAULT_CEILING) * _family(world, person, op)["ceiling"]


def practise(world: World, person: Person, op: str) -> float:
    """One more time doing it. Returns the skill it added: less and less as they near their own ceiling, never past it."""
    rate = _family(world, person, op)["rate"]
    top = ceiling(world, person, op)
    skill = person.skills.get(op, 0.0)
    gain = max(0.0, min(top - skill, GAIN * rate * (1 - skill / top)))
    person.skills[op] = skill + gain
    counts = practice(person)
    counts[op] = counts.get(op, 0) + 1
    return gain


def record(world: World) -> None:
    """The hidden values, for measuring only. Written once when a run starts."""
    recorder = recording.active()
    if recorder is None:
        return
    for person in world.people.values():
        recorder.write("talent", {"day": world.day, "person": person.name, "talent": {
            family: {k: round(v, 3) for k, v in values.items()} for family, values in of(world, person).items()}})


__all__ = ["SPREAD", "FAMILY", "CEILING", "GAIN", "draw", "of", "settle", "ceiling", "practise", "practice", "record"]
