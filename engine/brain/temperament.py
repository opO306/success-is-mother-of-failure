"""What a person is born with besides a body: how the mind is tuned, never what it knows (design doc 4, stage 4).

None of these numbers picks an act. Each only tunes how something is felt or learned: how loud a threat feels, how fast
a harmless threat stops frightening, how much something new pleases, how evenly a choice is spread, how strongly another
person pulls attention, how loud touch, smell and taste are, how much another's pain hurts. What is done with that is
still the brain's. Courage is not among them: whether someone goes toward what frightens them is measured, never set.

What clinics call ADHD, autism or psychopathy sits at the far ends of continuous, heritable dimensions like these
(Faraone & Larsson 2019; Constantino & Todd 2003), so no label is drawn. A lineage carries the mean of every dimension in
its genome, where evolution moves it; each person is scattered around that mean from a stream of their own, as talent
is. Parents do not pass their own draw on yet.

Fear is the body's. A threat at hand (a pack or a boar where one stands, a storm, a fresh corpse, a fight) is felt
through the person's gain. A threat lived through unharmed wears fear down; one that hurt sensitises at once. The two are
separately heritable in people (Hettema et al. 2003), and courage grows with exposures survived (Rachman).
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass

from ..primal.nature import SPECIES
from ..primal.world import Person, World

GENES = ("fear_gain", "habituation", "one_shot", "novelty_pull", "boredom", "patience", "action_noise",
         "people_pull", "sensory_gain", "empathy", "repetition",
         "chronotype")   # appended last so every earlier gene keeps its place in older genomes
SPREAD = 0.35   # how far people of one lineage scatter around its means, in gene units


@dataclass(frozen=True)
class Temper:
    fear_gain: float = 1.0       # how loud the same threat feels
    habituation: float = 0.2     # how fast threats lived through unharmed stop frightening
    one_shot: float = 1.0        # how hard one bad outcome lands: a threat that hurt, food that sickened
    novelty_pull: float = 0.3    # how much a new place, face or act pleases
    boredom: float = 1.0         # how fast doing the same thing again stops being new
    patience: float = 0.5        # how far back a good or bad outcome reaches over earlier choices
    action_noise: float = 1.0    # how evenly choices spread: above 1 flatter, below 1 sharper
    people_pull: float = 0.0     # how much a person draws a choice's target, or pushes it away when negative
    sensory_gain: float = 1.0    # how loud touch, smell and taste are
    empathy: float = 0.5         # how much the pain of those nearby hurts
    repetition: float = 0.0      # comfort (or unease, when negative) in doing the same thing again
    chronotype: float = 0.0      # hours the body clock runs late (owl, positive) or early (lark, negative)


DEFAULT = Temper()


def _scale(x: float) -> float:
    return math.exp(max(-3.0, min(3.0, x)))


def from_values(z: list[float]) -> Temper:
    """Gene units to a temper: 0 everywhere is the default person."""
    return Temper(
        fear_gain=_scale(z[0]), habituation=0.2 * _scale(z[1]), one_shot=_scale(z[2]), novelty_pull=0.3 * _scale(z[3]),
        boredom=_scale(z[4]), patience=min(0.95, 0.5 * _scale(z[5])), action_noise=min(4.0, max(0.25, _scale(z[6]))),
        people_pull=z[7], sensory_gain=min(2.0, _scale(z[8])), empathy=0.5 * _scale(z[9]), repetition=z[10],
        chronotype=max(-4.0, min(4.0, 2.0 * z[11])) if len(z) > 11 else 0.0,
    )


def draw(genes: list[float] | None, seed: int | None, name: str, spread: float = SPREAD) -> Temper:
    # its own stream, so the same world and person get the same temper whatever else the world draws
    rng = random.Random(f"temperament:{seed}:{name}")
    means = list(genes) if genes is not None else [0.0] * len(GENES)
    return from_values([m + rng.gauss(0.0, 1.0) * spread for m in means])


@dataclass
class Nerves:
    fear: float = 0.0
    safe: int = 0              # threats lived through unharmed
    sensitised: float = 0.0    # threats that hurt, weighed by one_shot


def threat_at(world: World, person: Person, corpses_before: int) -> float:
    """What threatens a person where they stand after a slot. Engine facts only: an animal's own aggression, the storm,
    a body that was not there before, a fight or a hunt the laws marked dangerous."""
    level = world.slot_features.get(person.name, {}).get("위험", 0.0)
    for herd in world.herds:
        if herd.place == person.location and herd.count > 0:
            level = max(level, SPECIES[herd.species].aggression)
    if world.weather.storm:
        level = max(level, 0.5)
    if len(world.lands[person.location].corpses) > corpses_before:
        level = max(level, 0.7)
    return level


def feel_threat(nerves: Nerves, temper: Temper, threat: float, harmed: bool) -> float:
    """One slot of fear. It fades by half a slot when nothing threatens."""
    if threat > 0:
        if harmed:
            nerves.sensitised += temper.one_shot
        else:
            nerves.safe += 1
    gain = temper.fear_gain * (1.0 + 0.5 * nerves.sensitised) / (1.0 + temper.habituation * nerves.safe)
    nerves.fear = max(min(1.0, threat * gain), nerves.fear * 0.5)
    return nerves.fear
