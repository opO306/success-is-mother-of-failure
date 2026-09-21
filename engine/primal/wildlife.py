"""Animals living their own day beside people (design doc 4, nature). Off unless PrimalConfig.wildlife is on; the brain
world turns it on. Engine facts only: where a herd goes to drink, when a predator comes for someone it can take, when a
boar or a bison runs someone down. Nobody is told an animal is dangerous. What it does to a body is felt as pain and fear,
and what to make of that is the brain's.

Herbivores and predators alike need water. A herd whose home has none walks to the nearest water up to two slots away at
dawn and dusk and goes home after, and that is when animals and people meet at the water's edge.

A predator that takes people goes for whoever is easiest where it is: someone alone, asleep in the open, wounded, or
small. Several awake people together and a fire keep most of them off. Wolves need a pack. Big cats took early humans
(the Swartkrans child's skull with a leopard's canine punctures, Brain 1981). Boars and bison run down whoever they come
upon, more in spring when they have young.

No study gives attacks per encounter, so the rates are starting values, not measurements. The share of deaths animals
cause is measured and set against foragers' records instead: among the Hadza, !Kung and Agta most deaths are disease
(75-85%) and accidents, animals among them, a small share (Hill et al. 2007; Gurven & Kaplan 2007).
"""
from __future__ import annotations

from ..agentworld import body as base_body
from . import mind as minds
from .nature import SPECIES, Herd, Species, shelter_at
from .world import Person, World

DRINK_SLOTS = frozenset({"새벽", "저녁"})
DRINK_REACH = 2           # travel slots a herd will go for water
CROWD = 3                 # this many awake people together keep most predators off
CROWD_LEFT = 0.1          # share of a predator's boldness left against a crowd
FIRE_LEFT = 0.2           # share left beside a fire
SPRING_CHARGE = 1.5
DEATH = "짐승에게 당함"


def _write(world: World, payload: dict) -> None:
    from .contest import _write as write
    write("wildlife", world, payload)


def slot(world: World, slot_name: str) -> None:
    for herd in world.herds:
        if herd.count > 0:
            _drink_trip(world, herd, slot_name)
    for herd in world.herds:
        if herd.count > 0:
            _meet(world, herd, slot_name)


def _drink_trip(world: World, herd: Herd, slot_name: str) -> None:
    home = herd.home or herd.place
    herd.home = home
    lands = world.lands
    if slot_name in DRINK_SLOTS and herd.place == home and lands[home].water is None:
        reach = {n: route[1] for n in lands if lands[n].water and (route := world.map.route(home, n)) is not None and route[1] <= DRINK_REACH}
        if reach:
            nearest = min(reach.values())
            herd.place = world.rng.choice(sorted(n for n, d in reach.items() if d == nearest))
    elif slot_name not in DRINK_SLOTS and herd.place != home:
        herd.place = home


def _vulnerability(world: World, person: Person, awake: list[Person], roof: float) -> float:
    v = 1.0
    if person in awake and len(awake) == 1:
        v *= 2.0
    if person.name in world.asleep and roof < 0.5:
        v *= 2.0
    if person.body.injuries:
        v *= 1.5
    if person.body.strength < 12:
        v *= 1.5
    return v


def _hurt(world: World, herd: Herd, species: Species, victim: Person, heavy: bool, awake: list[Person], slot_name: str, how: str) -> None:
    base_body.wound(victim.body, heavy, extra_health_loss=species.kill_force)
    if not victim.body.alive:   # wound() names every death by a wound a fight's; this one was an animal's
        victim.body.cause_of_death = DEATH
    world.asleep.discard(victim.name)
    world.feature(victim.name, "위험", 1.0)
    world.tell(victim.name, f"{herd.species}에게 {how}", slot=slot_name)
    minds.event(victim.mind, "안전", 40, f"{victim.location}에서 {herd.species}에게 {how} 때")
    for witness in awake:
        if witness is not victim:
            world.feature(witness.name, "위험", 1.0)
            world.tell(witness.name, f"{herd.species}이(가) {victim.name}을(를) 덮쳤다", slot=slot_name)
    base_body._check_death(victim.body, DEATH)
    _write(world, {"slot": slot_name, "place": victim.location, "species": herd.species, "victim": victim.name, "how": how,
                   "heavy": heavy, "dead": not victim.body.alive, "summary": f"{herd.species}이(가) {victim.name}을(를) 덮침"})


def _meet(world: World, herd: Herd, slot_name: str) -> None:
    species = SPECIES[herd.species]
    here = world.at(herd.place)
    if not here:
        return
    land = world.lands[herd.place]
    awake = [p for p in here if p.name not in world.asleep]
    for person in awake:
        world.feature(person.name, "위험", species.aggression)
    rng = world.rng
    if species.stalks_people and (not species.active or slot_name in species.active):
        roof, _ = shelter_at(land, len(here))
        target = max(here, key=lambda p: _vulnerability(world, p, awake, roof))
        chance = species.stalks_people * _vulnerability(world, target, awake, roof)
        if not species.solitary:
            chance *= min(1.0, herd.count / world.config.wolf_pack_min)
        if len(awake) >= CROWD:
            chance *= CROWD_LEFT
        if land.fire:
            chance *= FIRE_LEFT
        if rng.random() < min(0.9, chance):
            _hurt(world, herd, species, target, species.aggression >= 0.8, awake, slot_name, "물렸다")
            return
    if species.charges and awake:
        spring = SPRING_CHARGE if world.weather.season == "봄" else 1.0
        for person in awake:
            if rng.random() < species.charges * spring:
                _hurt(world, herd, species, person, species.toughness >= 60 and rng.random() < 0.3, awake, slot_name, "받혔다")
                return
