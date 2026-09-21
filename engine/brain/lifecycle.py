"""Lives that begin and end inside the world (design doc 4, generations), on compressed time: a year of a human life is
4 days. A child is carried for 3 days, is an infant for 12 (3 years), comes of age at 60 (15), a woman can conceive until
180 (45), and from 120 (30) the chance of dying of age alone doubles every 32 days (8 years), as human mortality does
(Gompertz). The seasons are not compressed, so growing up takes a year and a half of seasons.

Only bodies are ruled here. Mating happens when two people choose each other within two slots; conception is a chance
that a well-fed body raises, and a woman nursing a baby seldom conceives. Pregnancy costs food. Birth costs the mother
health. An infant is not asked anything: it is held (it goes where its mother goes) and cannot eat or drink by itself, so
it lives on milk that someone lactating chooses to give. Its hunger and thirst reach those nearby as crying. A child's
food and water needs and strength grow with age. None of this says who should mate or feed whom.

Genes and development are genetics.py's. The founders are adults of 20 to 30 years with founder genomes, and every child
is conceived from its parents' gametes. How hard the mother's pregnancy was, and how hard the infant's own first 12 days
were, shape the child as far as its plasticity loci let them. Innate pleasures of mating and of nursing are handed back
as feelings (life.py); what the brain does about them is its own.
"""
from __future__ import annotations

import random
import statistics
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field

from ..agentworld import body as base
from ..primal import body as physiology
from ..primal import energy
from ..primal.body import PrimalBody
from ..primal.mind import new_mind
from ..primal.world import Person, World
from . import genetics, temperament

YEAR = 4
INFANT_DAYS = 3 * YEAR
ADULT_DAYS = 15 * YEAR
LAST_FERTILE_DAYS = 45 * YEAR
FOUNDER_AGE = (20 * YEAR, 30 * YEAR)
PREGNANCY_DAYS = 3
CONCEPTION = 0.3               # a well-fed fertile pair's chance per mating
NURSING_BLOCKS_DAYS = 2        # nursing within this many days makes conception unlikely
NURSING_CONCEPTION = 0.1       # share of the chance left while nursing
LACTATION_DAYS = 3 * YEAR      # milk comes for this long after a birth
MILK_FOOD, MILK_WATER, MILK_COST = 0.5, 0.5, 0.25
PREGNANCY_FOOD = 0.25          # extra food a pregnant body needs per day
BIRTH_HEALTH_COST = 10.0
SENESCENCE_START = 30 * YEAR
SENESCENCE_BASE = 0.0025       # chance per day of dying of age alone at 30 years
SENESCENCE_DOUBLING = 8 * YEAR
MATE_WINDOW = 2                # slots within which two choices of each other count as one mating
MATING_PLEASURE, NURSING_PLEASURE = 0.5, 0.2


@dataclass
class Life:
    sex: str                               # "F" | "M"
    born: int                              # world day of birth; founders were born before day 1
    genome: genetics.Genome
    development: genetics.Development
    mother: str | None = None
    father: str | None = None
    generation: int = 0
    pregnant_by: str | None = None
    pregnant_since: int | None = None
    pregnancy_hardship: list[float] = field(default_factory=list)
    infancy_hardship: list[float] = field(default_factory=list)
    last_birth: int | None = None
    last_nursed: int | None = None


@dataclass
class Population:
    lives: dict[str, Life]
    means: list[float] | None
    rng: random.Random
    born_count: int = 0
    slot_serial: int = 0
    offers: dict[str, tuple[str, int]] = field(default_factory=dict)   # who chose to mate with whom, and when
    births: list[dict] = field(default_factory=list)
    matings: int = 0


def found(world: World, means: list[float] | None) -> Population:
    rng = random.Random(f"population:{world.seed}")
    population = Population({}, means, rng)
    for name in sorted(world.people):
        person = world.people[name]
        genome = genetics.founder(rng)
        development = genetics.born(genome, rng)
        genetics.settle_early(development, 0.0)
        age = rng.randint(*FOUNDER_AGE)
        population.lives[name] = Life("F" if rng.random() < 0.5 else "M", world.day - age, genome, development)
        person.body.strength = genetics.strength_of(development)
        person.body.health = min(person.body.health, 100.0 * genetics.vigour(genome))
    return population


def age(population: Population, world: World, name: str) -> int:
    return world.day - population.lives[name].born


def stage(population: Population, world: World, name: str) -> str:
    days = age(population, world, name)
    return "infant" if days < INFANT_DAYS else "child" if days < ADULT_DAYS else "adult"


def asked(population: Population, world: World, person: Person) -> bool:
    return stage(population, world, person.name) != "infant"


def temper(population: Population, name: str) -> temperament.Temper:
    return genetics.temper_of(population.lives[name].development, population.means)


def neural(population: Population, name: str) -> tuple[list[float], list[float]]:
    return genetics.neural_of(population.lives[name].development)


def lactating(population: Population, world: World, name: str) -> bool:
    life = population.lives[name]
    return life.last_birth is not None and world.day - life.last_birth <= LACTATION_DAYS


def before_slot(population: Population, world: World) -> None:
    """Infants are held: they go where their mother goes."""
    for person in world.living():
        life = population.lives[person.name]
        mother = world.people.get(life.mother) if life.mother else None
        if stage(population, world, person.name) == "infant" and mother is not None and mother.alive:
            world.following[person.name] = mother.name


def _conceive(population: Population, world: World, a: Person, b: Person) -> None:
    la, lb = population.lives[a.name], population.lives[b.name]
    if la.sex == lb.sex:
        return
    woman, man = (a, b) if la.sex == "F" else (b, a)
    her = population.lives[woman.name]
    if (her.pregnant_by is not None or not ADULT_DAYS <= age(population, world, woman.name) <= LAST_FERTILE_DAYS
            or age(population, world, man.name) < ADULT_DAYS):
        return
    chance = CONCEPTION * min(1.0, woman.body.reserve + 0.5)
    if her.last_nursed is not None and world.day - her.last_nursed < NURSING_BLOCKS_DAYS:
        chance *= NURSING_CONCEPTION
    if woman.body.illness >= world.config.illness_onset:
        chance *= 0.5
    if population.rng.random() < chance:
        her.pregnant_by, her.pregnant_since, her.pregnancy_hardship = man.name, world.day, []


def _can_mate(population: Population, world: World, a: Person | None, b: Person | None) -> bool:
    return (a is not None and b is not None and a.alive and b.alive and a.location == b.location
            and stage(population, world, a.name) == "adult" and stage(population, world, b.name) == "adult")


def _mated(population: Population, world: World, a: Person, b: Person, pleasure: dict[str, float]) -> None:
    population.offers.pop(a.name, None)
    population.offers.pop(b.name, None)
    population.matings += 1
    for who in (a.name, b.name):
        pleasure[who] = pleasure.get(who, 0.0) + MATING_PLEASURE
    _conceive(population, world, a, b)


def resolve(population: Population, world: World, chosen: dict[str, tuple[str, str | None]],
            respond: Callable[[str, str], bool] | None = None) -> dict[str, float]:
    """After a slot: matings and milk given. Returns each person's innate pleasure.

    A mating needs two adults who both want it. Two who chose each other within MATE_WINDOW slots mate. Someone chosen
    who did not choose back is asked, once, through respond(target, proposer): their own brain answers. Only adults
    mate; an approach to or from anyone younger comes to nothing."""
    pleasure: dict[str, float] = {}
    population.slot_serial += 1
    for name, (op, target) in chosen.items():
        if op == "mate" and target:
            population.offers[name] = (target, population.slot_serial)
    for name, (target, serial) in list(population.offers.items()):
        if name not in population.offers:
            continue
        if population.slot_serial - serial >= MATE_WINDOW:
            del population.offers[name]
            continue
        a, b = world.people.get(name), world.people.get(target)
        if not _can_mate(population, world, a, b):
            continue
        theirs = population.offers.get(target)
        if theirs and theirs[0] == name:
            _mated(population, world, a, b, pleasure)
        elif serial == population.slot_serial and respond is not None and target not in world.asleep and respond(target, name):
            _mated(population, world, a, b, pleasure)
    fed = set()
    for name, life in population.lives.items():
        # primate reflexes: a hungry or thirsty infant held by its mother roots and sucks, and her milk lets down in
        # answer; nobody chooses it. Feeding someone else's baby is still a choice (below).
        baby = world.people.get(name)
        mother = world.people.get(life.mother) if life.mother else None
        if (baby is None or mother is None or not baby.alive or not mother.alive or baby.location != mother.location
                or stage(population, world, name) != "infant" or not lactating(population, world, mother.name)):
            continue
        pressing = physiology.distress(baby.body, world.config)
        if max(pressing.get("hunger", 0.0), pressing.get("thirst", 0.0)) > 0:
            _give_milk(population, world, mother, baby, pleasure)
            fed.add(name)
    for name, (op, target) in chosen.items():
        if op != "nurse" or not target or target in fed:
            continue
        giver, baby = world.people[name], world.people.get(target)
        if (baby is not None and baby.alive and giver.alive and baby.location == giver.location
                and lactating(population, world, name) and stage(population, world, target) == "infant"):
            _give_milk(population, world, giver, baby, pleasure)
    return pleasure


def _give_milk(population: Population, world: World, giver: Person, baby: Person, pleasure: dict[str, float]) -> None:
    baby.body.eaten_today += MILK_FOOD
    baby.body.drank_today += MILK_WATER
    if world.config.energy_balance:
        giver.body.spent_today += MILK_FOOD / energy.MILK_EFFICIENCY
    else:
        giver.body.reserve = max(0.0, giver.body.reserve - MILK_COST)
    population.lives[giver.name].last_nursed = world.day
    pleasure[giver.name] = pleasure.get(giver.name, 0.0) + NURSING_PLEASURE


def _hardship(world: World, person: Person, fear: float) -> float:
    pressing = physiology.distress(person.body, world.config)
    return min(1.0, max(pressing.get("hunger", 0.0), pressing.get("thirst", 0.0), pressing.get("cold", 0.0), fear))


def _birth(population: Population, world: World, mother: Person) -> Person:
    her = population.lives[mother.name]
    his = population.lives.get(her.pregnant_by)
    rng = population.rng
    genome = genetics.conceive(her.genome, his.genome, rng)
    hardship = statistics.mean(her.pregnancy_hardship) if her.pregnancy_hardship else 0.0
    development = genetics.born(genome, rng, hardship, her.development.early)
    population.born_count += 1
    name = f"C{population.born_count:04d}"
    body = PrimalBody(strength=genetics.strength_of(development) * 0.3, health=100.0 * genetics.vigour(genome),
                      fat=energy.NEWBORN_FAT)
    child = Person(name=name, camp=mother.camp, location=mother.location, body=body,
                   mind=new_mind(rng, world.config.need_start), known_places=set(mother.known_places))
    world.people[name] = child
    world.acquaintances[name] = {mother.name}
    world.acquaintances.setdefault(mother.name, set()).add(name)
    generation = max(her.generation, his.generation if his else 0) + 1
    population.lives[name] = Life("F" if rng.random() < 0.5 else "M", world.day, genome, development,
                                  mother.name, her.pregnant_by, generation)
    population.births.append({"day": world.day, "child": name, "mother": mother.name, "father": her.pregnant_by,
                              "generation": generation, "vigour": round(genetics.vigour(genome), 3),
                              "pregnancy_hardship": round(hardship, 3)})
    mother.body.health -= BIRTH_HEALTH_COST
    base._check_death(mother.body, "아이를 낳다 숨짐")
    her.pregnant_by, her.pregnant_since, her.last_birth = None, None, world.day
    return child


def before_day_end(population: Population, world: World, fears: dict[str, float]) -> list[str]:
    """Called just before the day's end: needs by age, pregnancy, growing up, dying of age, births. Returns the born."""
    c = world.config
    for person in list(world.living()):
        name = person.name
        life = population.lives[name]
        days = age(population, world, name)
        share = 0.5 + 0.5 * min(1.0, days / ADULT_DAYS)
        person.body.drank_today += (1.0 - share) * c.water_need_per_day
        if c.energy_balance:   # a small body already spends less (energy.resting); growing costs on top
            if days < ADULT_DAYS:
                person.body.spent_today += energy.resting(person.body) * energy.GROWTH
        else:
            person.body.eaten_today += (1.0 - share) * c.food_need_per_day
        if days < ADULT_DAYS:
            person.body.strength = genetics.strength_of(life.development) * (0.3 + 0.7 * days / ADULT_DAYS)
        if life.pregnant_by is not None:
            if c.energy_balance:
                person.body.spent_today += energy.PREGNANCY
            else:
                person.body.eaten_today -= PREGNANCY_FOOD
            life.pregnancy_hardship.append(_hardship(world, person, fears.get(name, 0.0)))
        if days < INFANT_DAYS:
            life.infancy_hardship.append(_hardship(world, person, fears.get(name, 0.0)))
        elif not life.development.settled:
            genetics.settle_early(life.development, statistics.mean(life.infancy_hardship) if life.infancy_hardship else 0.0)
        if days >= SENESCENCE_START and population.rng.random() < SENESCENCE_BASE * 2 ** ((days - SENESCENCE_START) / SENESCENCE_DOUBLING):
            person.body.health = 0.0
            base._check_death(person.body, "나이 들어 몸이 다함")
    born = []
    for person in list(world.living()):
        life = population.lives[person.name]
        if life.pregnant_by is not None and world.day - life.pregnant_since >= PREGNANCY_DAYS and life.pregnant_by in population.lives:
            born.append(_birth(population, world, person).name)
    return born


def census(population: Population, world: World) -> dict:
    living = world.living()
    stages = Counter(stage(population, world, p.name) for p in living)
    out = {"day": world.day, "alive": len(living), "infant": stages["infant"], "child": stages["child"], "adult": stages["adult"],
           "born": population.born_count, "matings": population.matings,
           "pregnant": sum(1 for p in living if population.lives[p.name].pregnant_by)}
    if not living:
        return out
    lives = [population.lives[p.name] for p in living]
    pool = genetics.frequencies([life.genome for life in lives])
    load = [pool[l.name] for l in genetics.LOCI if l.kind == "load"]
    markers = [pool[l.name] for l in genetics.LOCI if l.kind == "marker"]
    values = [life.development.traits(population.means) for life in lives]
    out.update({
        "generation": max(life.generation for life in lives),
        "vigour": round(statistics.mean(genetics.vigour(life.genome) for life in lives), 3),
        "homozygosity": round(statistics.mean(genetics.marker_homozygosity(life.genome) for life in lives), 3),
        "harmful_share": round(statistics.mean(load), 4), "marker_top": round(statistics.mean(markers), 3),
        "traits": {t: round(statistics.mean(v[t] for v in values), 3) for t in genetics.TRAITS},
        "alleles": {t: round(sum(pool[f"{t}.{i}"] for i in range(genetics.LOCI_PER_TRAIT)), 3) for t in genetics.TRAITS},
    })
    return out


def heritability(population: Population) -> dict[str, float | None]:
    """Children on mid-parents, on what genes and noise made (before any hardship)."""
    kids = [life for life in population.lives.values() if life.mother in population.lives and life.father in population.lives]
    out = {}
    for trait in genetics.TRAITS:
        mid = [(population.lives[k.mother].development.own(trait) + population.lives[k.father].development.own(trait)) / 2 for k in kids]
        out[trait] = genetics.regression_slope(mid, [k.development.own(trait) for k in kids])
    return out
