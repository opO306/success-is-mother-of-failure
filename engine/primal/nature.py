"""The land itself: seasons, weather, what grows and walks, fire, and what people raise on it."""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

from ..agentworld.model import WorldMap
from . import laws
from .config import NIGHT, SEASONS, PrimalConfig
from .laws import Outcome, Setting
from .matter import Maker, Thing


# ---- animals
@dataclass(frozen=True)
class Species:
    name: str
    toughness: float
    evasion: float
    aggression: float
    group_max: int
    habitats: tuple[str, ...]
    eats_meat: bool = False
    stalks_people: float = 0.0      # wildlife.py: boldness toward a person it could take, per slot
    charges: float = 0.0            # wildlife.py: chance per slot to run down someone it comes upon
    active: tuple[str, ...] = ()    # wildlife.py: slots it hunts in; empty means any
    solitary: bool = False          # wildlife.py: hunts alone (no pack needed)
    kill_force: float = 0.0         # wildlife.py: health an attack takes beyond the wound itself
    edible_meat_kg: float = 0.0     # carcass biomass available to carnivores; never inferred from combat toughness


SPECIES: dict[str, Species] = {s.name: s for s in [
    Species("사슴", 35, 0.7, 0.0, 12, ("숲", "초원"), edible_meat_kg=60),
    Species("토끼", 6, 0.8, 0.0, 20, ("초원", "숲"), edible_meat_kg=1),
    # Korean Pleistocene herbivores (우리역사넷 동물상 표 3), used on the Danyang land
    Species("큰사슴", 60, 0.7, 0.1, 10, ("숲", "초원"), edible_meat_kg=180),
    Species("노루", 15, 0.8, 0.0, 6, ("숲", "초원"), edible_meat_kg=15),
    Species("말", 80, 0.75, 0.2, 15, ("초원",), charges=0.003, edible_meat_kg=240),
    Species("원시소", 160, 0.4, 0.6, 12, ("초원", "숲"), charges=0.006, kill_force=15.0, edible_meat_kg=420),
    # Attack rates are starting values. The first ones (wolves 0.05, tiger 0.06, leopard 0.05, bear 0.01/0.04, hyena 0.04,
    # boar 0.05, bison 0.02) made animals 29 of 65 deaths in the test worlds, far above foragers' records where accidents,
    # animals among them, are a small share; all were cut to about a fifth (2026-09-15) and the share is measured again.
    Species("멧돼지", 45, 0.4, 0.6, 8, ("숲", "늪"), charges=0.01, edible_meat_kg=48),
    Species("들소", 90, 0.3, 0.4, 25, ("초원",), charges=0.005, kill_force=10.0, edible_meat_kg=420),
    Species("늑대", 30, 0.6, 0.8, 8, ("숲", "산기슭", "초원"), eats_meat=True, stalks_people=0.01,
            active=("새벽", "저녁", "밤"), edible_meat_kg=24),
    # Large predators found in Korean Pleistocene caves (Jeommal, Durubong, Geumgul, Sangsi, Yonggok; 우리역사넷 동물상
    # 표 3): tiger at 9 sites, leopard 4, brown bear 8, cave hyena 4. Only in worlds with wildlife on (scenario.PREDATORS).
    Species("호랑이", 150, 0.6, 0.95, 1, ("숲", "산기슭"), eats_meat=True, stalks_people=0.012,
            active=("새벽", "저녁", "밤"), solitary=True, kill_force=45.0, edible_meat_kg=108),
    Species("표범", 70, 0.7, 0.85, 1, ("숲", "언덕", "산기슭"), eats_meat=True, stalks_people=0.01,
            active=("새벽", "저녁", "밤"), solitary=True, kill_force=25.0, edible_meat_kg=30),
    Species("큰곰", 180, 0.3, 0.7, 1, ("숲", "산기슭"), stalks_people=0.002, charges=0.008,
            solitary=True, kill_force=30.0, edible_meat_kg=180),
    Species("동굴하이에나", 60, 0.5, 0.8, 6, ("초원", "늪", "언덕"), eats_meat=True, stalks_people=0.008,
            active=("밤", "새벽"), kill_force=15.0, edible_meat_kg=42),
    # The Olduvai plain (2026-09-17). Grazers of the Serengeti, the carnivores that follow them, and the baboons that
    # forage the same ground people do - the one other primate on this land.
    # Biomass starts from representative adult masses in field studies, with 60% left as accessible flesh/organs.
    Species("얼룩말", 250, 0.7, 0.3, 20, ("초원",), charges=0.004, edible_meat_kg=156),
    Species("누", 200, 0.6, 0.3, 40, ("초원",), charges=0.004, edible_meat_kg=108),
    Species("가젤", 20, 0.9, 0.0, 30, ("초원",), edible_meat_kg=12),
    Species("임팔라", 45, 0.85, 0.0, 20, ("초원", "숲"), edible_meat_kg=27),
    Species("혹멧돼지", 60, 0.6, 0.5, 8, ("초원", "숲"), charges=0.01, edible_meat_kg=44),
    Species("아프리카물소", 500, 0.3, 0.8, 30, ("초원", "숲"), charges=0.01, kill_force=40.0,
            edible_meat_kg=312),
    Species("사자", 180, 0.5, 0.95, 6, ("초원", "숲"), eats_meat=True, stalks_people=0.012,
            active=("새벽", "저녁", "밤"), kill_force=45.0, edible_meat_kg=100),
    Species("점박이하이에나", 60, 0.55, 0.85, 12, ("초원", "숲"), eats_meat=True, stalks_people=0.01,
            active=("밤", "새벽"), kill_force=15.0, edible_meat_kg=36),
    Species("개코원숭이", 25, 0.75, 0.4, 30, ("초원", "숲", "산기슭"), charges=0.004,
            edible_meat_kg=15),
]}


@dataclass
class Herd:
    id: int
    species: str
    count: int
    place: str
    fear: float = 0.3
    fear_of: dict[str, float] = field(default_factory=dict)   # person -> how warily this herd treats them
    hunted_days: list[int] = field(default_factory=list)
    settled: bool = False                                     # stays where it is fed and enclosed
    home: str | None = None                                   # wildlife.py: where it goes back to after drinking
    hydration: float = 1.0                                    # animals.py: a day's water at 1
    energy: float = 3.0                                       # animals.py: days of food stored per animal
    boldness: float = 0.0                                     # animals.py: -1..1, inherited within the herd
    fed_today: float = 0.0                                    # animals.py: days of food eaten since the day began

    def wariness(self, person: str) -> float:
        return self.fear_of.get(person, self.fear)


# ---- land
@dataclass
class Gatherable:
    kind: str
    stock: float
    cap: float
    regen: dict[str, float]          # season -> per day
    rate: float = 3.0                # things per worked slot, before skill and body
    gdd: float = 0.0                 # plants.py: warmth gathered this growing year
    cold_days: int = 0               # plants.py: cold days in a row
    bore: bool = False               # plants.py: has borne its crop this year
    ripe_left: int = 0               # plants.py: days the crop still hangs


@dataclass
class Fire:
    heat: float
    fuel_slots: float
    enclosed: bool = False


@dataclass
class Structure:
    id: int
    form: str
    materials: list[Thing] = field(default_factory=list)
    labor: float = 0.0
    builders: set[str] = field(default_factory=set)
    care: float = 1.0   # how true the hands that built it were, weighted by the work each put in (1.0 before hands differed)

    @property
    def required(self) -> float:
        return 2.0 + sum(m.p("weight") for m in self.materials) * 1.5

    @property
    def complete(self) -> bool:
        return bool(self.materials) and self.labor >= self.required

    @property
    def frame(self) -> float:
        return sum(m.p("hardness") * m.p("weight") * 2 for m in self.materials if m.p("reach") >= 0.5 or m.p("hardness") >= 0.6)

    @property
    def binding(self) -> float:
        return sum(m.p("fiber") for m in self.materials if m.p("fiber") >= 0.5)

    @property
    def cover(self) -> float:
        return sum(1.0 for m in self.materials if (m.p("flexibility") >= 0.4 and m.p("reach") < 0.5) or m.kind == "점토")

    @property
    def stability(self) -> float:
        return (self.frame + 0.5 * self.binding) * (0.6 + 0.4 * self.care)

    @property
    def roof(self) -> float:
        return min(1.0, self.cover / 4) * (0.6 + 0.4 * self.care) if self.complete and self.frame >= 1.0 else 0.0

    @property
    def warmth(self) -> float:
        clay = sum(1 for m in self.materials if m.kind == "점토")
        return min(1.0, self.roof * 0.6 + clay * 0.1) if self.complete else 0.0

    @property
    def capacity(self) -> int:
        return max(1, int(self.frame * 2))

    @property
    def encloses(self) -> bool:
        return self.complete and any(w in self.form for w in ("둘러", "울타리", "가두"))


@dataclass
class Planting:
    kind: str
    day: int
    germination: float
    progress: float = 0.0
    grown: bool = False
    dead: bool = False


@dataclass
class Land:
    name: str
    kind: str
    gather: dict[str, Gatherable] = field(default_factory=dict)
    water: str | None = None                 # "맑은 물" | "고인 물"
    soil_moisture: float = 0.5
    plots: int = 2
    natural_roof: float = 0.0                # a cave keeps rain off
    natural_capacity: int = 0
    structures: list[Structure] = field(default_factory=list)
    lying: list[Thing] = field(default_factory=list)
    fire: Fire | None = None
    plantings: list[Planting] = field(default_factory=list)
    corpses: list[str] = field(default_factory=list)
    dry_days: int = 0
    puddle: float = 0.0                      # days of rainwater standing in hollows (puddles_day)
    carrion: float = 0.0                     # animals.py: edible kilograms from dead animals lying here
    pasture: float = 0.0                     # animals.py: grazing and browse standing across the whole place, forage units
    pasture_cap: float = 0.0                 # most the place's ground holds at the height of summer


# ---- time and weather
@dataclass
class Weather:
    day: int
    season: str
    base_temp: float
    raining: bool
    storm: bool


def season_of(day: int, c: PrimalConfig) -> str:
    return SEASONS[((day - 1) // c.days_per_season) % len(SEASONS)]


QUARTER_MEAN_OF_PEAK = 2 * math.sqrt(2) / math.pi   # average of a cosine over the quarter centred on its peak


def annual_temp(day: int, c: PrimalConfig) -> float:
    """A year-long cosine: warmest in mid-summer, coldest in mid-winter. Centre and amplitude are set so that the average
    over summer and over winter match their means exactly; a symmetric curve cannot also match spring and autumn, which
    both come out at the midpoint (LGM Danyang: 3.8 °C against 4.2 and 5.5). What it buys is that late spring warms past
    a plant's base temperature instead of the whole spring sitting at its mean."""
    t = c.season_temp
    mean = (t["여름"] + t["겨울"]) / 2
    amplitude = (t["여름"] - t["겨울"]) / 2 / QUARTER_MEAN_OF_PEAK
    year = c.days_per_season * len(SEASONS)
    mid_summer = 1.5 * c.days_per_season
    return mean + amplitude * math.cos(2 * math.pi * ((day - 1) - mid_summer + 0.5) / year)


def weather_for(day: int, rng: random.Random, c: PrimalConfig) -> Weather:
    season = season_of(day, c)
    raining = rng.random() < c.rain_chance[season]
    storm = raining and season != "겨울" and rng.random() < c.storm_share
    base = annual_temp(day, c) if c.smooth_seasons else c.season_temp[season]
    return Weather(day, season, base + rng.uniform(-c.daily_temp_noise, c.daily_temp_noise), raining, storm)


def air_temp(weather: Weather, slot: str, c: PrimalConfig) -> float:
    return weather.base_temp + c.slot_temp_offset[slot]


def shelter_at(land: Land, occupants: int) -> tuple[float, float]:
    """(roof, warmth) a sleeper here gets. Shared by everyone present: a crowded hut shelters each of them less."""
    capacity = land.natural_capacity + sum(s.capacity for s in land.structures if s.complete)
    if capacity <= 0:
        return 0.0, 0.0
    roofs = [land.natural_roof] + [s.roof for s in land.structures if s.complete]
    warmths = [land.natural_roof * 0.5] + [s.warmth for s in land.structures if s.complete]
    crowd = min(1.0, capacity / max(1, occupants))
    return max(roofs) * crowd, max(warmths) * crowd


def setting_at(land: Land, weather: Weather, slot: str, c: PrimalConfig, occupants: int = 1) -> Setting:
    roof, _ = shelter_at(land, occupants)
    return Setting(
        temp=air_temp(weather, slot, c), raining=weather.raining, sheltered=roof >= 0.5,
        fire=land.fire.heat if land.fire else 0.0, fire_enclosed=bool(land.fire and land.fire.enclosed),
        water_here=land.water is not None, season=weather.season, soil_moisture=land.soil_moisture,
    )


# ---- gathering and fire
def gather(land: Land, kind: str | None, slots: int, strength: float, skill: float, maker: Maker, season: str,
           progress: dict[str, float] | None = None) -> Outcome:
    """progress: what these hands have already picked of this kind but not yet filled out. Gathering is continuous and
    things are whole: until 2026-09-17 the leftover was thrown away every slot, so a weak or starving person, who picks
    less than one thing a slot, came back with nothing for ever (a starving man got 0 river stones from a bank of 77)."""
    out = Outcome(ok=True, exertion=0.5 * slots)
    available = {k: g for k, g in land.gather.items() if g.stock >= 1}
    if kind and kind not in available:
        near = [k for k in available if kind in k or k in kind]
        kind = near[0] if len(near) == 1 else kind
    if not kind or kind not in available:
        out.ok = False
        out.felt.append(f"{land.name}에서는 {kind or '그런 것'}이(가) 보이지 않는다")
        return out
    source = available[kind]
    picked = min(source.stock, source.rate * slots * max(0.2, strength) * (1 + 0.1 * skill))
    carried = (progress.get(kind, 0.0) if progress is not None else 0.0) + picked
    count = int(carried)
    if progress is not None:
        progress[kind] = carried - count
    if count <= 0:
        out.felt.append(f"{kind}을(를) 조금씩 모으는 중이다")
        return out
    source.stock -= count
    out.made = [maker.make(kind) for _ in range(count)]
    out.felt.append(f"{kind} {count}개를 모았다")
    return out


def light_fire(land: Land, fuel: list[Thing], setting: Setting, c: PrimalConfig) -> Outcome:
    out = Outcome(ok=True, exertion=0.3)
    if setting.raining and not setting.sheltered:
        out.ok = False
        out.felt.append("비가 와서 불씨가 살지 않는다")
        return out
    dry = [f for f in fuel if f.p("flammability") >= 0.5 and f.p("moisture") < 0.3]
    if not dry:
        out.ok = False
        # What was in their hands is what they met. The first primal runs told flint flakes, river stones and roots
        # "too damp to catch" hundreds of times, so nobody could ever find out why the fire never came.
        unburnable = ", ".join(dict.fromkeys(f.kind for f in fuel if f.p("flammability") < 0.5))
        damp = ", ".join(dict.fromkeys(f.kind for f in fuel if f.p("flammability") >= 0.5))
        if not fuel:
            out.felt.append("불을 붙일 만한 것이 없다")
        if unburnable:
            out.felt.append(f"{unburnable}에는 불이 붙지 않는다")
        if damp:
            out.felt.append(f"{damp}이(가) 눅눅해서 불이 붙지 않는다")
        return out
    slots = sum(f.p("weight") * f.p("flammability") for f in dry) * c.fire_fuel_slots_per_weight
    heat = max(f.p("flammability") for f in dry) * (1.0 if any(f.kind == "숯" for f in dry) else 0.7)
    enclosed = any(s.complete and any(w in s.form for w in ("가두", "덮", "둘러")) for s in land.structures)
    if land.fire:
        land.fire.fuel_slots += slots
        land.fire.heat = max(land.fire.heat, heat)
    else:
        land.fire = Fire(heat=heat, fuel_slots=slots, enclosed=enclosed)
    out.used = dry
    out.felt.append("불이 붙어 타오른다" if slots >= 2 else "불이 붙었지만 금방 사그라들 것 같다")
    return out


def burn_slot(land: Land, weather: Weather, occupants: int) -> None:
    if not land.fire:
        return
    roof, _ = shelter_at(land, occupants)
    land.fire.fuel_slots -= 1
    if land.fire.fuel_slots <= 0 or (weather.raining and roof < 0.5 and land.natural_roof < 0.5):
        land.fire = None


def lightning(lands: dict[str, Land], weather: Weather, rng: random.Random, c: PrimalConfig, maker: Maker) -> list[str]:
    """A storm can set a dry forest alight. Whatever lies there is heated; whoever is there sees it."""
    if not weather.storm or rng.random() >= c.lightning_share:
        return []
    forests = [l for l in lands.values() if l.kind == "숲" and l.dry_days >= c.lightning_needs_dry_days]
    if not forests:
        return []
    land = rng.choice(forests)
    land.fire = Fire(heat=0.8, fuel_slots=c.wildfire_slots)
    for thing in list(land.lying):
        result = laws.heat(thing, c.wildfire_slots, Setting(fire=0.8), maker)
        for used in result.used:
            land.lying.remove(used)
        land.lying.extend(result.made)
    wood = land.gather.get("나뭇가지")
    if wood:
        wood.stock *= 0.5
    return [land.name]


# ---- growing
def _sprouts(seed: Thing) -> str | None:
    """What can grow from a buried thing: its own kind if that kind is a living seed, and a mixture sprouts the seeds
    that went into it (a mash of pine nuts and grass holds whole pine nuts). A mixture has no kind of its own to grow
    as; until 2026-09-17 one became a gathering stand named "섞은 것" and gathering from it crashed the world."""
    from .matter import TEMPLATES
    if seed.kind in TEMPLATES:
        return seed.kind
    for line in seed.history:
        if line.startswith("mixed "):
            for kind in line[len("mixed "):].split(","):
                if kind in TEMPLATES and TEMPLATES[kind].props.get("germination", 0.0) > 0:
                    return kind
    return None


def plant(land: Land, seed: Thing, day: int) -> Outcome:
    out = Outcome(ok=True, exertion=0.2)
    kind = _sprouts(seed)
    if seed.p("germination") <= 0 or kind is None:
        out.felt.append("땅에 묻었다")
        land.plantings.append(Planting(seed.kind, day, 0.0, dead=True))
        out.used.append(seed)
        return out
    land.plantings.append(Planting(kind, day, seed.p("germination")))
    out.used.append(seed)
    out.felt.append("땅에 묻었다")
    return out


def plantings_day(land: Land, season: str, c: PrimalConfig) -> None:
    for planting in land.plantings:
        if planting.dead or planting.grown:
            continue
        if season in ("봄", "여름") and land.soil_moisture >= 0.3:
            planting.progress += planting.germination * (1.0 if season == "봄" else 0.7)
            if planting.progress >= c.planting_growth_days:
                planting.grown = True
                grown_kind = "들풀 씨앗" if planting.kind == "들풀 씨앗" else planting.kind
                source = land.gather.setdefault(grown_kind, Gatherable(grown_kind, 0.0, 40.0, {}))
                source.stock = min(source.cap, source.stock + 12)
        else:
            planting.germination -= 0.1
            if planting.germination <= 0:
                planting.dead = True


# Rain stands where the ground holds it: hollows in bare rock keep it longest, trodden or leafy ground briefly. Water in
# a hollow is still water (고인 물): it can make a body sick like a swamp's. It dries by season and is ice below freezing.
PUDDLE_HOLD = {"언덕": 3.0, "산기슭": 2.0, "부싯돌비탈": 2.0, "야영지": 1.0, "초원": 1.0, "숲": 1.0, "동굴": 1.0}
PUDDLE_DRYING = {"여름": 1.0, "봄": 0.5, "가을": 0.5, "겨울": 0.3}
PUDDLE_SIP = 0.1


def puddles_day(land: Land, weather: Weather) -> None:
    """A new day's weather: rain fills the hollows (a storm twice over), a dry day dries them."""
    if land.water is not None:
        return
    hold = PUDDLE_HOLD.get(land.kind, 0.0)
    if weather.raining:
        land.puddle = max(land.puddle, hold * (2.0 if weather.storm else 1.0))
    else:
        land.puddle = max(0.0, land.puddle - PUDDLE_DRYING[weather.season])


def puddle_water(land: Land, weather: Weather) -> str | None:
    return "고인 물" if land.water is None and land.puddle > 0 and weather.base_temp > 0 else None


def regenerate(land: Land, season: str, raining: bool) -> None:
    for source in land.gather.values():
        source.stock = min(source.cap, source.stock + source.regen.get(season, 0.0))
    soil_day(land, raining)


def soil_day(land: Land, raining: bool) -> None:
    land.dry_days = 0 if raining else land.dry_days + 1
    land.soil_moisture = min(1.0, land.soil_moisture + 0.2) if raining else max(0.1, land.soil_moisture - 0.05)


# ---- building
def build(land: Land, builder: str, items: list[Thing], form: str, slots: int, strength: float, steady: float = 1.0) -> Outcome:
    out = Outcome(ok=True, exertion=0.6 * slots)
    open_site = next((s for s in land.structures if not s.complete and builder in s.builders), None)
    if open_site is None:
        open_site = next((s for s in land.structures if not s.complete), None)
    if open_site is None:
        if len(land.structures) >= land.plots:
            out.ok = False
            out.felt.append(f"{land.name}에는 더 지을 자리가 없다")
            return out
        open_site = Structure(id=len(land.structures) + 1, form=form)
        land.structures.append(open_site)
    open_site.builders.add(builder)
    open_site.materials.extend(items)
    out.used = list(items)
    was_complete = open_site.complete
    added = slots * max(0.2, strength)
    open_site.care = (open_site.care * open_site.labor + steady * added) / (open_site.labor + added)
    open_site.labor += added
    if open_site.complete and not was_complete:
        if open_site.roof >= 0.5:
            out.felt.append("다 지었다. 비를 가릴 만큼 위가 덮였다")
        elif open_site.encloses:
            out.felt.append("다 지었다. 빙 둘러막혔다")
        else:
            out.felt.append("다 지었지만 위가 성기고 바람이 숭숭 든다")
        if open_site.care < 0.5:
            out.felt.append("이음새가 엉성하다")
    elif not items and not open_site.materials:
        out.ok = False
        out.felt.append("쌓을 재료가 없다")
    else:
        out.felt.append("짓는 중이다. 아직 덜 됐다")
    return out


def storm_damage(land: Land, weather: Weather) -> list[int]:
    if not weather.storm:
        return []
    fallen = [s for s in land.structures if s.complete and s.stability < 1.5]
    for s in fallen:
        land.structures.remove(s)
        land.lying.extend(s.materials)
    return [s.id for s in fallen]


# ---- animals
def feed(herd: Herd, person: str, food: Thing, c: PrimalConfig) -> Outcome:
    out = Outcome(ok=True)
    species = SPECIES[herd.species]
    if species.eats_meat != (food.kind in ("고기", "지방", "물고기")):
        out.ok = False
        out.felt.append(f"{herd.species}이(가) 먹이에 관심을 보이지 않는다")
        return out
    before = herd.wariness(person)
    herd.fear_of[person] = max(0.0, before - c.feed_fear_drop)
    out.used.append(food)
    out.felt.append(f"{herd.species}이(가) 경계하며 다가와 먹었다" if before < 0.7 else f"{herd.species}이(가) 멀찍이서 지켜보다 먹이를 물고 달아났다")
    return out


def herds_day(herds: list[Herd], lands: dict[str, Land], world_map: WorldMap, day: int, season: str, rng: random.Random, c: PrimalConfig) -> list[str]:
    moves = []
    for herd in herds:
        if herd.count <= 0:
            continue
        species = SPECIES[herd.species]
        herd.hunted_days = [d for d in herd.hunted_days if day - d <= 3]
        land = lands[herd.place]
        enclosed = any(s.encloses for s in land.structures)
        herd.settled = enclosed and min(herd.fear_of.values(), default=1.0) < 0.3
        pressed = len(herd.hunted_days) >= 2 or herd.fear >= c.herd_flee_fear
        if not herd.settled and (pressed or land.kind not in species.habitats):
            options = [n for n in world_map.neighbors(herd.place) if n in lands and lands[n].kind in species.habitats]
            if options:
                herd.place = rng.choice(options)
                herd.home = herd.place
                herd.fear = max(0.2, herd.fear - 0.2)
                moves.append(f"{herd.species}:{land.name}->{herd.place}")
        if season == "봄" and (day - 1) % c.days_per_season == 0:
            herd.count += int(round(herd.count * c.spring_birth_rate * (1 - herd.count / species.group_max)))
        herd.fear = max(0.1, herd.fear - 0.05)
    return moves


def wolf_attack_targets(herd: Herd, land: Land, slot: str, sleepers_unsheltered: list[str], c: PrimalConfig) -> list[str]:
    """Hungry packs come at night for whoever sleeps out in the open with no fire. The rule is the wolves', not a choice."""
    species = SPECIES[herd.species]
    if not species.eats_meat or herd.count < c.wolf_pack_min or slot not in NIGHT or land.fire:
        return []
    return sleepers_unsheltered[:1]
