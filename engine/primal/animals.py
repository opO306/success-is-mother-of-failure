"""Animals as living bodies with instincts (design doc 4, animals as agents). Off unless PrimalConfig.animal_minds is on;
the brain world turns it on, and it then replaces wildlife.py's schedules and odds. Nothing here happens at a set hour or
by a set chance of attack: what a herd does each slot follows from its own state.

Body (the engine's facts): every herd has water in its bodies (hydration, a day's worth at 1) and food stored (days of
it per animal). A day uses half a day of water and a day of food, less in the short days for bodies that slow down in
winter (red deer's metabolism falls by about 60% at its winter low, Arnold et al. 2004; bears den). A store run out costs
animals, and the dead lie as carrion that rots faster the warmer it is. A herd in good condition bears young at the turn
of spring, as many as its kind bears and its condition allows, and a herd grown past the size its kind keeps together
splits, the new group going to a neighbouring place of its habitat. What the herd eats comes from the land: grazers take
the stands plants.py grows, so a herd too big for its meadow eats it down and has to move, and meat-eaters eat carrion
where they find it and the herds they catch, leaving what they cannot hold.

Instincts (the animals' side, innate): startled by people working or hunting where it is, a herd grows wary; wary enough,
grazers flee to a quieter place and boars, bison, aurochs and bears run the nearest person down instead. Thirsty, a herd
walks toward the nearest water it can reach. Short of food, grazers graze and move to better forage, and predators, in
their active hours, eat carrion here, chase the prey herds where they are or follow the smell of prey or carrion to a
neighbouring place. A predator turns on a person only when hunger, its herd's inherited boldness and its taste for
people, times how easy the person is to take (alone, asleep in the open, wounded, small), outweigh what keeps it off
(three or more awake people, a fire). A full tiger walks past. Whether a chase ends in a kill still carries the chance
every chase has, from the margin between the hunter's strength and the prey's evasion, as people's hunts do. Diets,
needs, stores and births are starting values, written down.

2026-09-16, after an empty Danyang land lost every animal but deer, bears and elk within 250 days: grazers held 5 days
of food and burned it at the summer rate all winter, frost took all the grass, predators ate the small game and starved,
and births could never grow a herd past its group size. A six times wider land kept predators alive about twice as long
and still lost the rest at the first winter, so the store, winter slowing, standing winter grass (plants.py), carrion,
condition-based births and herd splitting were written in.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from . import sky, wildlife
from .nature import SPECIES, Herd
from .world import Person, World


@dataclass(frozen=True)
class Diet:
    forage: tuple[str, ...] = ()     # plant stands it eats
    intake: float = 0.0              # plant units one animal eats in a day
    prey: tuple[str, ...] = ()       # herds it hunts
    need: float = 0.0                # kilograms of meat one animal needs in a day
    man_eater: float = 0.0           # 0-1: how readily hunger turns it on a person it could take
    store: float = 30.0              # days of food a body can hold as fat
    winter_use: float = 1.0          # share of the summer's food a day burns on the shortest day
    births: float = 0.0              # young per animal a year in full condition
    meal: float = 3.0                # days of need a gut takes in within one day (a wolf eats about a fifth of itself)
    capture_scale: float | None = None  # species hunting style; still multiplied by hunter/prey physical margin


# Stores: wild ungulates lose up to about 30% of their mass over a northern winter, living mostly on autumn fat
# (Kautz et al. 2020), about a month of full need; hunters feast and fast, going about two weeks between kills.
# Births per animal (half the herd female): deer and cattle one calf, roe deer twins, boar litters of four to six,
# hares several litters, wolves one litter for the pack, big cats and bears a litter every two years or so.
DIETS: dict[str, Diet] = {
    "사슴": Diet(("풀", "쑥", "나무껍질"), 0.3, winter_use=0.4, births=0.4),
    "큰사슴": Diet(("풀", "쑥", "나무껍질"), 0.5, winter_use=0.4, births=0.4),
    "노루": Diet(("풀", "쑥", "나무껍질"), 0.15, winter_use=0.5, births=0.7),
    "토끼": Diet(("풀", "쑥", "나무껍질"), 0.05, store=10.0, winter_use=0.7, births=3.0),
    "말": Diet(("풀", "쑥"), 0.8, winter_use=0.5, births=0.3),
    "원시소": Diet(("풀", "쑥"), 1.2, winter_use=0.5, births=0.35),
    "들소": Diet(("풀", "쑥"), 1.2, winter_use=0.5, births=0.35),
    "멧돼지": Diet(("버섯", "잣", "도토리", "칡뿌리", "풀"), 0.4, store=20.0, winter_use=0.7, births=2.0),
    "늑대": Diet(prey=("사슴", "노루", "토끼", "말", "큰사슴", "멧돼지"), need=2.5, man_eater=0.35, store=14.0, births=0.7),
    "호랑이": Diet(prey=("사슴", "큰사슴", "멧돼지", "노루", "원시소"), need=6.0, man_eater=0.5, store=14.0, births=0.5),
    "표범": Diet(prey=("노루", "사슴", "토끼", "멧돼지", "가젤", "임팔라", "혹멧돼지", "개코원숭이"),
                 need=3.0, man_eater=0.45, store=14.0, births=0.6, capture_scale=0.7),
    "큰곰": Diet(("잣", "버섯", "풀", "물고기"), 0.6, prey=("사슴", "노루"), need=3.0, man_eater=0.15, store=60.0,
                winter_use=0.25, births=0.4),
    "동굴하이에나": Diet(prey=("말", "사슴", "노루", "토끼", "원시소"), need=4.0, man_eater=0.35, store=14.0, births=0.7),
    # Olduvai. Baboons eat what people eat, which is why they are worth watching and worth quarrelling with.
    "얼룩말": Diet(("풀",), 1.0, winter_use=0.9, births=0.3),
    "누": Diet(("풀",), 0.9, winter_use=0.9, births=0.4),
    "가젤": Diet(("풀", "들열매"), 0.12, store=15.0, winter_use=0.9, births=0.8),
    "임팔라": Diet(("풀", "들열매", "나무껍질"), 0.3, winter_use=0.9, births=0.7),
    "혹멧돼지": Diet(("덩이줄기", "풀"), 0.4, store=20.0, winter_use=0.9, births=2.0),
    "아프리카물소": Diet(("풀",), 2.0, winter_use=0.9, births=0.35),
    "사자": Diet(prey=("누", "얼룩말", "가젤", "임팔라", "혹멧돼지"), need=6.0, man_eater=0.5, store=14.0,
                 births=0.6, capture_scale=0.6),
    "점박이하이에나": Diet(prey=("가젤", "임팔라", "누", "혹멧돼지", "얼룩말"), need=4.0, man_eater=0.4,
                          store=14.0, births=0.8, capture_scale=1.4),
    "개코원숭이": Diet(("들열매", "덩이줄기", "풀", "아카시아 씨"), 0.15, store=12.0, winter_use=0.9, births=0.8),
}
STORE_DAYS = 5.0
THIRSTY_BELOW = 0.4
HUNGRY_BELOW = 2.0
FLEE_AT, CHARGE_AT = 0.6, 0.7
FEAR_FROM_WORK, FEAR_FROM_PRESENCE = 0.2, 0.05
HUMAN_EDIBLE_MEAT_KG = 20.0
CROWD_KEEPS_OFF, FIRE_KEEPS_OFF = 10.0, 5.0
STARVING_LOSS = 0.1
STARTLING_WORK = frozenset({"hunt", "gather", "strike", "attack", "fire", "build", "cut", "fish"})
SLOTS_PER_DAY = 6
GRAZING_BOUT_DAYS = 0.5
BIRTH_CONDITION = 0.5        # share of a full store below which a herd bears nothing
ROT_PER_DEGREE = 0.03        # share of carrion gone a day per °C above freezing (flies, microbes, small scavengers)
FROZEN_ROT = 0.01
START_STORE = 0.5            # herds begin the world half full
# A hunter sets out once half its store is gone and it has not had a day's food today. Waiting until two days were left
# gave a lone tiger or leopard two days to find prey before it starved, and every one died within weeks even on the
# wide land; hunting from half a store with no limit on a day's eating then let a pack kill deer after deer to fill two
# weeks of fat, and the wide land's deer went from 208 to 24 in 100 days. A gut holds a few days' need (meal), so kills
# slow once the hunters have fed, as a predator's kill rate levels off when prey is plentiful (Holling's type II).
HUNT_BELOW = 0.5
# Most chases fail: wolves bring down 3-14% of the prey they chase (15-26% of elk in some years, Mech et al.), tigers
# about one stalk in ten to twenty (Schaller). The strength margin alone (about 0.45 for a pack on deer) let predators
# empty an empty land of prey that thrived when the predators were taken out, so a chase ends in a kill at CATCH times
# the margin.
CATCH = 0.3


def _move_toward(world: World, herd: Herd, goal: str) -> bool:
    route = world.map.route(herd.place, goal)
    if not route or not route[0]:
        return False
    herd.place = route[0][0]
    return True


def _habitat_neighbours(world: World, herd: Herd) -> list[str]:
    species = SPECIES[herd.species]
    lands = world.lands
    return sorted(n for n in world.map.neighbors(herd.place) if n in lands and lands[n].kind in species.habitats)


def _startle(world: World, herd: Herd, here: list[Person]) -> None:
    if here:
        herd.fear = min(1.0, herd.fear + FEAR_FROM_PRESENCE)
    for person in here:
        for record in world.slot_done.get(person.name, []):
            if record["op"] in STARTLING_WORK:
                herd.fear = min(1.0, herd.fear + FEAR_FROM_WORK)


def _flee(world: World, herd: Herd) -> bool:
    options = _habitat_neighbours(world, herd)
    if not options:
        return False
    herd.place = min(options, key=lambda n: len(world.at(n)))
    herd.home = herd.place
    herd.fear = max(0.0, herd.fear - 0.3)
    return True


def _charge(world: World, herd: Herd, awake: list[Person], slot_name: str) -> bool:
    species = SPECIES[herd.species]
    if not species.charges or herd.fear < CHARGE_AT or not awake:
        return False
    target = max(awake, key=lambda p: (-p.body.strength, p.name))
    wildlife._hurt(world, herd, species, target, species.toughness >= 60 and herd.fear >= 0.9, awake, slot_name, "받혔다")
    herd.fear = max(0.0, herd.fear - 0.4)
    return True


def _drink(world: World, herd: Herd) -> bool:
    land = world.lands[herd.place]
    if land.water:
        herd.hydration = 1.0
        world.animal_acts.append((herd.place, herd.species, "drink", land.water))
        return True
    reach = [(route[1], n) for n in world.lands if world.lands[n].water and (route := world.map.route(herd.place, n)) is not None]
    return bool(reach) and _move_toward(world, herd, min(reach)[1])


def _graze(world: World, herd: Herd, diet: Diet) -> bool:
    land = world.lands[herd.place]
    stands = [land.gather[k] for k in diet.forage if k in land.gather and land.gather[k].stock >= 1]
    # a herd grazes in bouts to its fill, up to half a day's food a slot, not a sixth of the day spread over every slot:
    # with the thinner bite, one slot spent walking to water left every herd short and all starved on standing grass
    want = diet.intake * herd.count * min(GRAZING_BOUT_DAYS, diet.store - herd.energy)
    eaten = 0.0
    if "풀" in diet.forage and land.pasture > 0:   # the open ground first, then the stands people gather from
        eaten = min(land.pasture, want)
        land.pasture -= eaten
    for stand in stands:
        if eaten >= want:
            break
        bite = min(stand.stock, want - eaten)
        stand.stock -= bite
        eaten += bite
    if want > 0:
        herd.energy = min(diet.store, herd.energy + eaten / (diet.intake * herd.count))
    if eaten > 0:   # people standing here can see what it ate
        world.animal_acts.append((herd.place, herd.species, "eat", stands[0].kind if stands else "풀"))
    if eaten < 0.5 * want:
        lands = world.lands
        richer = max(_habitat_neighbours(world, herd),
                     key=lambda n: sum(lands[n].gather[k].stock for k in diet.forage if k in lands[n].gather), default=None)
        if richer is not None:
            herd.place = herd.home = richer
    return True


def _feed_on_meat(world: World, herd: Herd, diet: Diet, meat: float) -> None:
    """Eat what the guts can take today and the bodies can store; the rest stays where it lies."""
    room = max(0.0, min(diet.store - herd.energy, diet.meal - herd.fed_today)) * diet.need * herd.count
    eaten = min(meat, room)
    herd.energy += eaten / (diet.need * herd.count)
    herd.fed_today += eaten / (diet.need * herd.count)
    world.lands[herd.place].carrion += meat - eaten


def _scavenge(world: World, herd: Herd, diet: Diet) -> bool:
    land = world.lands[herd.place]
    if land.carrion <= 0.0 or herd.energy >= diet.store or herd.fed_today >= diet.meal:
        return False
    meat, land.carrion = land.carrion, 0.0
    world.animal_acts.append((herd.place, herd.species, "eat", "고기"))
    _feed_on_meat(world, herd, diet, meat)
    return True


def _hunt(world: World, herd: Herd, diet: Diet, here: list[Person], awake: list[Person], slot_name: str) -> bool:
    species = SPECIES[herd.species]
    prey = [h for h in world.herds if h is not herd and h.place == herd.place and h.count > 0 and h.species in diet.prey]
    if prey:
        target = max(prey, key=lambda h: (h.count, h.id))
        strength = species.toughness * max(1.0, herd.count ** 0.5) * (1.0 + 0.3 * herd.boldness)
        evasion = SPECIES[target.species].toughness * (1.0 + SPECIES[target.species].evasion) * (1.0 + target.fear)
        margin = strength / (strength + evasion)
        world.animal_acts.append((herd.place, herd.species, "hunt", target.species))
        if world.rng.random() < min(0.95, (diet.capture_scale or CATCH) * margin):
            target.count -= 1
            _feed_on_meat(world, herd, diet, SPECIES[target.species].edible_meat_kg)
        target.fear = 1.0
        return True
    if diet.man_eater and here:
        roof = wildlife.shelter_at(world.lands[herd.place], len(here))[0]
        person = max(here, key=lambda p: (wildlife._vulnerability(world, p, awake, roof), p.name))
        hunger = max(0.0, min(1.0, 1.0 - herd.energy / HUNGRY_BELOW))
        pack = 1.0 if species.solitary else min(1.0, herd.count / world.config.wolf_pack_min)
        urge = hunger * (1.0 + herd.boldness) * diet.man_eater * pack * wildlife._vulnerability(world, person, awake, roof)
        if len(awake) >= wildlife.CROWD:
            urge /= CROWD_KEEPS_OFF
        if world.lands[herd.place].fire:
            urge /= FIRE_KEEPS_OFF
        if urge >= 1.0:
            wildlife._hurt(world, herd, species, person, species.aggression >= 0.8, awake, slot_name, "물렸다")
            if not person.body.alive:
                _feed_on_meat(world, herd, diet, HUMAN_EDIBLE_MEAT_KG)
            return True
    options = _habitat_neighbours(world, herd)
    smelled = [n for n in options if world.lands[n].carrion > 0.0
               or any(h.place == n and h.count > 0 and h.species in diet.prey for h in world.herds)]
    if smelled:
        herd.place = smelled[0]
        return True
    if options:
        herd.place = world.rng.choice(options)
        return True
    return False


def slot(world: World, slot_name: str) -> None:
    for herd in [h for h in world.herds if h.count > 0]:
        species = SPECIES[herd.species]
        diet = DIETS.get(herd.species, Diet())
        here = world.at(herd.place)
        awake = [p for p in here if p.name not in world.asleep]
        _startle(world, herd, here)
        for person in awake:
            world.feature(person.name, "위험", species.aggression)
        if _charge(world, herd, awake, slot_name):
            continue
        if herd.fear >= FLEE_AT and awake and not diet.prey and _flee(world, herd):
            continue
        if herd.hydration < THIRSTY_BELOW and _drink(world, herd):
            continue
        if species.active and slot_name not in species.active:
            continue
        if diet.prey and _scavenge(world, herd, diet):
            continue
        hungry = herd.energy < HUNT_BELOW * diet.store and herd.fed_today < 1.0
        if diet.prey and hungry and _hunt(world, herd, diet, here, awake, slot_name):
            continue
        if diet.forage and herd.energy < diet.store:
            _graze(world, herd, diet)


def _day_length_range(latitude: float = sky.LATITUDE) -> tuple[float, float]:
    def hours(declination_deg: float) -> float:
        cos_hour = -math.tan(math.radians(latitude)) * math.tan(math.radians(declination_deg))
        return 24.0 * math.acos(max(-1.0, min(1.0, cos_hour))) / math.pi
    return hours(-23.44), hours(23.44)


def food_use(world: World, diet: Diet) -> float:
    """Days of food a body burns today: all of it on the longest day, winter_use of it on the shortest."""
    if diet.winter_use >= 1.0:
        return 1.0
    shortest, longest = _day_length_range()
    share = (sky.day_length(world.day, world.config) - shortest) / (longest - shortest)
    return diet.winter_use + (1.0 - diet.winter_use) * max(0.0, min(1.0, share))


def rot_share(temp: float) -> float:
    return FROZEN_ROT if temp <= 0.0 else min(1.0, FROZEN_ROT + ROT_PER_DEGREE * temp)


def _split(world: World, herd: Herd) -> Herd | None:
    species = SPECIES[herd.species]
    options = _habitat_neighbours(world, herd)
    if herd.count <= species.group_max or not options:
        return None
    place = min(options, key=lambda n: (sum(h.count for h in world.herds if h.place == n and h.species == herd.species), n))
    young = Herd(max(h.id for h in world.herds) + 1, herd.species, herd.count // 2, place, energy=herd.energy,
                 hydration=herd.hydration, boldness=herd.boldness, home=place)
    herd.count -= young.count
    return young


def day(world: World) -> list[str]:
    """A day's end for every herd: food and water used, the starving and parched lose animals to carrion, carrion rots,
    a herd in condition bears at the turn of spring, a herd too big splits, and wariness fades."""
    c = world.config
    notes = []
    rot = rot_share(world.weather.base_temp)
    for land in world.lands.values():
        if land.carrion > 0.0:
            land.carrion = land.carrion * (1.0 - rot) if land.carrion > 0.05 else 0.0
    spring_turn = world.weather.season == "봄" and (world.day - 1) % c.days_per_season == 0
    for herd in list(world.herds):
        if herd.count <= 0:
            continue
        species = SPECIES[herd.species]
        diet = DIETS.get(herd.species, Diet())
        herd.energy -= food_use(world, diet)
        herd.hydration -= 0.5
        herd.fed_today = 0.0
        for store in ("energy", "hydration"):
            if getattr(herd, store) < 0:
                lost = min(herd.count, max(1, round(herd.count * STARVING_LOSS)))
                herd.count -= lost
                world.lands[herd.place].carrion += lost * species.edible_meat_kg
                setattr(herd, store, 0.0)
                notes.append(f"{herd.species}:{herd.place} -{lost} ({store})")
        condition = herd.energy / diet.store
        if spring_turn and herd.count > 0 and condition >= BIRTH_CONDITION:
            herd.count += int(round(herd.count * diet.births * min(1.0, condition)))
        young = _split(world, herd) if herd.count > 0 else None
        if young is not None:
            world.herds.append(young)
        herd.fear = max(0.1, herd.fear - 0.05)
    return notes
