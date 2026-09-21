"""The starting land: three bands who do not know of each other, spread over about thirty places."""
from __future__ import annotations

import random

from ..agentworld.model import WorldMap
from . import talent
from .body import PrimalBody
from .config import PrimalConfig
from .matter import Maker
from .mind import new_mind
from .nature import Fire, Gatherable, Herd, Land, weather_for
from .world import Person, World

CAMPS = ["북쪽 야영지", "동쪽 야영지", "남쪽 야영지"]


def _every(amount: float) -> dict[str, float]:
    return {"봄": amount, "여름": amount, "가을": amount, "겨울": amount}


def _g(kind: str, stock: float, cap: float, regen: dict[str, float] | float = 0.0, rate: float = 3.0) -> Gatherable:
    return Gatherable(kind, stock, cap, _every(regen) if isinstance(regen, (int, float)) else regen, rate)


# Food is set so that a band that forages every day can get through spring to autumn, and winter cannot be lived through
# on what grows then: it takes food put by. The first fake year starved everyone by day 20 whatever they did, because
# the land could not feed 45 people in any season; that was a starting condition deciding the outcome, not a choice.
def _forest(name: str, poison_mushrooms: bool) -> Land:
    gather = [
        _g("나뭇가지", 60, 60, 6), _g("통나무", 20, 20, 1, rate=1), _g("나무껍질", 30, 30, 2),
        _g("버섯", 10, 20, {"봄": 4, "가을": 6}), _g("도토리", 20, 60, {"가을": 10}), _g("새알", 6, 12, {"봄": 4}, rate=1),
        _g("풀", 20, 30, {"봄": 3, "여름": 3}),
    ]
    if poison_mushrooms:
        gather.append(_g("붉은 버섯", 4, 6, {"가을": 1}, rate=1))
    return Land(name, "숲", {g.kind: g for g in gather}, plots=3)


def _meadow(name: str, berries: bool) -> Land:
    gather = [_g("풀", 50, 60, {"봄": 8, "여름": 8, "가을": 3}), _g("들풀 씨앗", 10, 40, {"여름": 6, "가을": 10}),
              _g("칡뿌리", 15, 25, {"봄": 4, "여름": 4, "가을": 4, "겨울": 1}, rate=1)]
    if berries:
        gather.append(_g("산딸기", 0, 40, {"여름": 10}))
    return Land(name, "초원", {g.kind: g for g in gather}, plots=4)


def _river(name: str, fish: float, clay: bool = False) -> Land:
    gather = [_g("강돌", 80, 80, 0), _g("물고기", fish, fish + 20, {"봄": 6, "여름": 6, "가을": 4, "겨울": 1}, rate=1)]
    if clay:
        gather.append(_g("점토", 30, 30, 0, rate=2))
    return Land(name, "강", {g.kind: g for g in gather}, water="맑은 물", plots=2)


def build_lands() -> list[Land]:
    return [
        Land("북쪽 야영지", "야영지", plots=6), Land("동쪽 야영지", "야영지", plots=6), Land("남쪽 야영지", "야영지", plots=6),
        _river("북쪽 개울", 25, clay=True), _forest("북쪽 숲", True),
        Land("부싯돌 비탈", "부싯돌비탈", {"부싯돌": _g("부싯돌", 60, 60, 0, rate=2), "사암": _g("사암", 20, 20, 0, rate=1)}, plots=1),
        Land("산기슭", "산기슭", {"강돌": _g("강돌", 30, 30), "칡뿌리": _g("칡뿌리", 12, 15, 1, rate=1), "나뭇가지": _g("나뭇가지", 30, 30, 3)}, plots=2),
        Land("동굴", "동굴", natural_roof=0.8, natural_capacity=10, plots=0),
        _river("큰 강", 40),
        Land("점토 강둑", "점토강둑", {"점토": _g("점토", 150, 150, 0, rate=2), "강돌": _g("강돌", 20, 20)}, water="맑은 물", plots=2),
        _meadow("동쪽 초원", True), _meadow("들소 벌판", False), _forest("동쪽 숲", False),
        Land("호수", "호수", {"물고기": _g("물고기", 50, 70, {"봄": 8, "여름": 8, "가을": 6, "겨울": 2}, rate=1), "풀": _g("풀", 20, 30, 2),
                             "점토": _g("점토", 30, 30, 0, rate=2)}, water="맑은 물", plots=2),
        Land("늪", "늪", {"토란": _g("토란", 15, 30, {"봄": 5, "여름": 5, "가을": 5}, rate=1), "풀": _g("풀", 40, 50, 4)}, water="고인 물", plots=1),
        _forest("남쪽 숲", True),
        Land("사과 언덕", "언덕", {"들사과": _g("들사과", 0, 50, {"가을": 10}), "풀": _g("풀", 20, 30, 2), "사암": _g("사암", 15, 15, 0, rate=1)}, plots=3),
        _meadow("남쪽 초원", True), _forest("가운데 숲", True), _river("강 여울", 20, clay=True),
        Land("큰 바위 언덕", "언덕", {"사암": _g("사암", 30, 30, 0, rate=1), "부싯돌": _g("부싯돌", 10, 10, 0, rate=1)}, plots=3),
        Land("갈대밭", "초원", {"풀": _g("풀", 60, 60, 6), "들풀 씨앗": _g("들풀 씨앗", 10, 30, {"여름": 3, "가을": 5})}, plots=4),
    ]


ROADS = [
    ("북쪽 야영지", "북쪽 개울", 1), ("북쪽 야영지", "북쪽 숲", 1), ("북쪽 숲", "부싯돌 비탈", 1), ("북쪽 숲", "산기슭", 1),
    ("산기슭", "동굴", 1), ("북쪽 개울", "산기슭", 2),
    ("동쪽 야영지", "큰 강", 1), ("큰 강", "점토 강둑", 1), ("동쪽 야영지", "동쪽 초원", 1), ("동쪽 초원", "들소 벌판", 2), ("동쪽 야영지", "동쪽 숲", 1),
    ("남쪽 야영지", "호수", 1), ("호수", "늪", 1), ("남쪽 야영지", "남쪽 숲", 1), ("남쪽 숲", "사과 언덕", 1), ("남쪽 야영지", "남쪽 초원", 1),
    ("북쪽 숲", "가운데 숲", 3), ("동쪽 숲", "가운데 숲", 2), ("남쪽 숲", "가운데 숲", 3), ("가운데 숲", "강 여울", 1),
    ("가운데 숲", "큰 바위 언덕", 1), ("강 여울", "갈대밭", 1), ("큰 강", "강 여울", 2), ("산기슭", "큰 바위 언덕", 2),
    ("늪", "갈대밭", 2), ("들소 벌판", "갈대밭", 2),
]

HERDS = [
    ("사슴", 8, "북쪽 숲"), ("사슴", 10, "동쪽 숲"), ("사슴", 7, "남쪽 숲"), ("토끼", 15, "동쪽 초원"), ("토끼", 12, "남쪽 초원"),
    ("멧돼지", 6, "늪"), ("멧돼지", 5, "가운데 숲"), ("들소", 20, "들소 벌판"), ("늑대", 6, "산기슭"), ("늑대", 5, "가운데 숲"),
]


PREDATORS = [("호랑이", 1, "가운데 숲"), ("표범", 1, "큰 바위 언덕"), ("큰곰", 1, "북쪽 숲"), ("동굴하이에나", 4, "갈대밭")]

# The Danyang/Jecheon land at the Last Glacial Maximum (terrain.py). Seasons are Jecheon's 1991-2020 normals (KMA:
# Mar-May 10.2, Jun-Aug 22.7, Sep-Nov 11.5, Dec-Feb -3.1 °C) cooled as climate models and pollen put the LGM over Korea:
# about 5.9 °C colder a year, most in winter and least in summer (winter -8, spring and autumn -6, summer -4 here), and
# about 40% drier. Animals are the large and medium mammals of Korean Pleistocene caves (우리역사넷 동물상 표 3):
# sika, red and roe deer, boar, horse, aurochs, and wolves; hares stand in for the small game the table does not list.
LGM_SEASON_TEMP = {"봄": 4.2, "여름": 18.7, "가을": 5.5, "겨울": -11.1}
LGM_RAIN_SHARE = 0.6
REAL_SEASON_DAYS = 91
TERRAIN_HERDS = [("사슴", 8, "숲", 4), ("큰사슴", 6, "숲", 3), ("노루", 5, "숲", 3), ("멧돼지", 6, "숲", 2), ("말", 12, "초원", 1),
                 ("원시소", 10, "초원", 1), ("토끼", 12, "초원", 2), ("늑대", 6, "산기슭", 1)]
# Meat-eaters are held to what the prey can carry: about 90 kg of one carnivore species per 10,000 kg of prey (Carbone &
# Gittleman 2002). The land's prey weighs about 17 t (143 t on the wide land), so two wolf packs and a clan of four
# hyenas were about twice that; since 2026-09-16 one pack and a pair.
TERRAIN_PREDATORS = [("호랑이", 1, "숲", 1), ("표범", 1, "산기슭", 1), ("큰곰", 1, "숲", 2), ("동굴하이에나", 2, "초원", 1)]
DANYANG_PLACES = {"숲": 23, "산기슭": 13, "초원": 3}   # places of each kind the herd plan was written for
# Grazing across a whole place, apart from the handfuls people gather (2026-09-16). A gathering stand holds tens of
# units, but a place is a 6 km square, 3,600 ha: stands sized for hands starved every grazer on the land. Forage units
# are about 10 kg of dry plant (a horse eats 0.8 a day). Starting values per hectare at the height of summer, not
# measured: cold dry steppe about 500 kg, a valley floor 200, the browse and grass under forest 150, mountain foot 100,
# rocky hills 30.
PASTURE_PER_HA = {"초원": 50.0, "강": 20.0, "숲": 15.0, "산기슭": 10.0, "언덕": 3.0}
PASTURE_START = 0.3   # a world begins in mid-spring, the pasture still coming up
# Lands made by tools/build_land.py. "danyang_wide" is the same ground cut about six times wider (36.45-37.65N,
# 128.0-129.0E, 334 places), built 2026-09-16 to test whether the animals die out because the land is too small.
TERRAIN_FILES = {"danyang": "danyang_lgm.json", "danyang_wide": "danyang_wide_lgm.json", "olduvai": "olduvai.json"}
# The Olduvai basin, 3°S and about 1,500 m up (2026-09-17): warm all year with two rainy seasons, the woodland-and-grass
# mosaic our own line lived in. Temperatures are the Serengeti's highland means; the rains come in the first and third
# seasons (the long and the short rains). What people eat here is what foragers of this plain eat: tubers dug from the
# ground, baobab pods, berries, grass seed, honey and fish from the rivers. Stone is what the ground gives.
OLDUVAI_SEASON_TEMP = {"봄": 22.0, "여름": 20.0, "가을": 22.0, "겨울": 24.0}
OLDUVAI_RAIN = {"봄": 0.45, "여름": 0.08, "가을": 0.35, "겨울": 0.12}
OLDUVAI_LATITUDE = -3.0
OLDUVAI_GATHER = {
    "초원": lambda: [_g("덩이줄기", 40, 60, {"봄": 6, "여름": 3, "가을": 5, "겨울": 3}, rate=1), _g("들열매", 0, 40, 0),
                    _g("들풀 씨앗", 10, 40, 0), _g("풀", 30, 40, {"봄": 6, "가을": 5})],
    "숲": lambda: [_g("바오바브 열매", 0, 30, 0), _g("들열매", 0, 40, 0), _g("벌꿀", 4, 10, {"봄": 1, "가을": 1}, rate=1),
                  _g("나뭇가지", 40, 60, 5), _g("통나무", 10, 20, 1, rate=1), _g("나무껍질", 20, 30, 2),
                  _g("덩이줄기", 15, 25, {"봄": 3, "가을": 2}, rate=1)],
    "산기슭": lambda: [_g("아카시아 씨", 0, 30, 0), _g("강돌", 30, 30, 0), _g("나뭇가지", 20, 30, 2)],
    "언덕": lambda: [_g("사암", 30, 30, 0, rate=1), _g("부싯돌", 12, 12, 0, rate=1)],
    "강": lambda: [_g("강돌", 60, 60, 0), _g("점토", 20, 20, 0, rate=2)],
}
# Herds per land, not per Danyang: the plain carries game in numbers no temperate valley does (the Serengeti holds over
# a million wildebeest). Lions and hyenas are set near what this much prey carries (Carbone & Gittleman 2002).
OLDUVAI_HERDS = [("누", 30, "초원", 20), ("얼룩말", 16, "초원", 15), ("가젤", 25, "초원", 25), ("임팔라", 12, "숲", 6),
                 ("혹멧돼지", 8, "초원", 10), ("아프리카물소", 20, "숲", 4), ("개코원숭이", 20, "숲", 6)]
OLDUVAI_PREDATORS = [("사자", 5, "초원", 8), ("점박이하이에나", 10, "초원", 8), ("표범", 1, "숲", 3)]


# What grows where the glacial ground is (Hanam pollen and macrofossils, 26-20 ka): Korean pine on the plateau instead of
# oak's acorns, Artemisia greens instead of kudzu roots and taro, which need warmth; berries are left out until a glacial
# record for them is found.
LGM_PLANT_SWAP = {"도토리": "잣", "칡뿌리": "쑥", "토란": "쑥", "산딸기": None}


def _glacial_plants(land: Land) -> None:
    for old, new in LGM_PLANT_SWAP.items():
        stand = land.gather.pop(old, None)
        if stand is not None and new is not None and new not in land.gather:
            stand.kind = new
            land.gather[new] = stand


def _olduvai_plants(land: Land) -> None:
    """The plain's own stands in place of the temperate ones; fish stay where there is water."""
    make = OLDUVAI_GATHER.get(land.kind)
    if make is None:
        return
    fish = land.gather.get("물고기")
    land.gather = {g.kind: g for g in make()}
    if fish is not None:
        land.gather["물고기"] = fish


def lands_from_terrain(data: dict, flora: str = "danyang") -> list[Land]:
    lands = []
    for p in data["places"]:
        kind, name = p["kind"], p["name"]
        if kind == "강":
            land = _river(name, min(60.0, 15.0 + p["catchment_km2"] / 40.0), clay=p["slope"] < 10.0)
        elif kind == "초원":
            land = _meadow(name, berries=(p["row"] + p["col"]) % 2 == 0)
        elif kind == "숲":
            land = _forest(name, poison_mushrooms=(7 * p["row"] + p["col"]) % 3 == 0)
        elif kind == "산기슭":
            land = Land(name, "산기슭", {"강돌": _g("강돌", 30, 30), "칡뿌리": _g("칡뿌리", 12, 15, 1, rate=1),
                                        "나뭇가지": _g("나뭇가지", 30, 30, 3)}, plots=2)
        elif kind == "언덕":
            land = Land(name, "언덕", {"사암": _g("사암", 30, 30, 0, rate=1), "부싯돌": _g("부싯돌", 10, 10, 0, rate=1)}, plots=3)
        elif kind in ("동굴", "바위그늘"):
            land = Land(name, kind, natural_roof=p["roof"], natural_capacity=10 if kind == "동굴" else 6, plots=0)
        else:   # a riverside terrace where stone was worked (Suyanggae)
            land = Land(name, kind, {"부싯돌": _g("부싯돌", 40, 40, 0, rate=2), "강돌": _g("강돌", 40, 40, 0)}, plots=6)
        if p["water"] and land.water is None:
            land.water = p["water"]
            if kind in ("숲", "초원", "산기슭"):
                land.gather["물고기"] = _g("물고기", 6, 12, {"봄": 2, "여름": 2, "가을": 1, "겨울": 0}, rate=1)
        _olduvai_plants(land) if flora == "olduvai" else _glacial_plants(land)
        land.pasture_cap = PASTURE_PER_HA.get(kind, 0.0) * data.get("cell_km", 6.0) ** 2 * 100
        land.pasture = land.pasture_cap * PASTURE_START
        lands.append(land)
    return lands


def herds_from_terrain(lands: dict[str, Land], seed: int | None, wildlife: bool, plan: list | None = None,
                       predators: list | None = None) -> list[tuple[str, int, str]]:
    """The herd plan above is for the Danyang land; a wider land holds as many groups per place of their kind."""
    rng = random.Random(f"herds:{seed}")
    out = []
    for species, count, kind, groups in (plan or TERRAIN_HERDS) + ((predators if predators is not None else TERRAIN_PREDATORS) if wildlife else []):
        places = sorted(n for n, l in lands.items() if l.kind == kind) or sorted(n for n, l in lands.items() if l.kind == "숲")
        if plan is None and kind in DANYANG_PLACES and len(places) != DANYANG_PLACES[kind]:
            groups = max(1, round(groups * len(places) / DANYANG_PLACES[kind]))
        for place in rng.sample(places, min(groups, len(places))):
            out.append((species, count, place))
    return out


def build_world(seed: int | None = None, band_size: int = 15, talent_on: bool = True, energy: bool = False,
                wildlife: bool = False, puddles: bool = False, land: str = "old", plants: bool = False,
                season_days: int | None = None, sky: bool = False, graded: bool = False, animals: bool = False,
                sleep_switch: bool = False) -> World:
    """energy: spending by work, size and cold with fat stores (energy.py); founders then start with 10-20 days of fat,
    drawn from a stream of their own so the rest of the world is the same either way.
    wildlife: animals go to water, stalk and charge through the day (wildlife.py), and the large predators live here."""
    from .energy import FAT_START
    rng = random.Random(seed)
    c = PrimalConfig(talent=talent_on, energy_balance=energy, wildlife=wildlife, puddles=puddles, living_plants=plants,
                     sky=sky, graded_feelings=graded, animal_minds=animals, sleep_switch=sleep_switch)
    if season_days is not None:
        c.days_per_season = season_days
    maker = Maker(rng)
    world_map = WorldMap()
    start_day = 1
    if land in TERRAIN_FILES:
        from . import terrain
        data = terrain.load(terrain.ROOT / TERRAIN_FILES[land])
        c.season_temp = dict(OLDUVAI_SEASON_TEMP) if land == "olduvai" else dict(LGM_SEASON_TEMP)
        c.latitude = OLDUVAI_LATITUDE if land == "olduvai" else 37.05
        # real season lengths and a smooth year, so warmth builds and plants bear as they do (decided 2026-09-15);
        # a world begins in mid-spring, not on its coldest first day
        c.days_per_season = season_days if season_days is not None else REAL_SEASON_DAYS
        c.smooth_seasons = True
        start_day = c.days_per_season // 2 + 1
        c.rain_chance = dict(OLDUVAI_RAIN) if land == "olduvai" else {s: v * LGM_RAIN_SHARE for s, v in c.rain_chance.items()}
        lands = {l.name: l for l in lands_from_terrain(data, "olduvai" if land == "olduvai" else "danyang")}
        roads, camps, reach = [tuple(r) for r in data["roads"]], list(data["camps"]), 1
        herd_plan = herds_from_terrain(lands, seed, wildlife or animals,
                                       OLDUVAI_HERDS if land == "olduvai" else None,
                                       OLDUVAI_PREDATORS if land == "olduvai" else None)
    else:
        lands = {l.name: l for l in build_lands()}
        roads, camps, reach = ROADS, CAMPS, 2
        herd_plan = HERDS + (PREDATORS if wildlife or animals else [])
    if plants:   # a world starts in spring: nothing has borne yet, and the stands have had the warmth of the days before
        from .plants import TRAITS, bears_fruit, normal_gdd
        for place in lands.values():
            for kind, stand in place.gather.items():
                if bears_fruit(kind):
                    stand.stock = 0.0
                    stand.gdd = normal_gdd(TRAITS[kind], c, start_day - 1)
    for place in lands.values():
        world_map.add_place(place)
    for a, b, slots in roads:
        world_map.connect(a, b, slots)
    herds = [Herd(i + 1, species, count, place) for i, (species, count, place) in enumerate(herd_plan)]
    if animals:   # each herd's inherited boldness, from a stream of its own, and a half-full store
        from .animals import DIETS, START_STORE, Diet
        for herd in herds:
            herd.energy = DIETS.get(herd.species, Diet()).store * START_STORE
            herd.boldness = max(-1.0, min(1.0, random.Random(f"herd:{seed}:{herd.id}").gauss(0.0, 0.5)))
            herd.home = herd.place

    ids = [f"P{i:02d}" for i in range(1, band_size * len(camps) + 1)]
    rng.shuffle(ids)
    people: dict[str, Person] = {}
    world = World(config=c, map=world_map, lands=lands, people=people, herds=herds, maker=maker, rng=rng, weather=weather_for(start_day, rng, c), seed=seed, day=start_day)
    for camp in camps:
        camp_land = lands[camp]
        camp_land.fire = Fire(heat=0.7, fuel_slots=8)
        for _ in range(8):
            twig = maker.make("나뭇가지")
            twig.props["moisture"] = 0.1
            camp_land.lying.append(twig)
        band = [ids.pop() for _ in range(band_size)]
        nearby = {place for place in lands if (route := world_map.route(camp, place)) is not None and route[1] <= reach} | {camp}
        for name in band:
            cloak = maker.make("가죽")
            cloak.props.update({"scraped": 1.2, "moisture": 0.1, "insulation": 0.6, "flexibility": 0.5})
            flakes = [maker.derive("부싯돌 조각", {"hardness": 0.8, "brittleness": 0.8, "sharpness": rng.uniform(0.4, 0.55), "weight": 0.08}) for _ in range(2)]
            food = "덩이줄기" if land == "olduvai" else "잣" if land in TERRAIN_FILES else "칡뿌리"
            carried = flakes + [maker.make("강돌"), maker.make(food), maker.make(food)]
            person = Person(
                name=name, camp=camp, location=camp, body=PrimalBody(strength=rng.uniform(12, 28)), mind=new_mind(rng, c.need_start),
                carried=carried, worn=[cloak], temperature=rng.uniform(0.3, 1.1), known_places=set(nearby),
            )
            if energy:
                person.body.fat = random.Random(f"fat:{seed}:{name}").uniform(*FAT_START)
            for thing in carried + [cloak]:
                thing.handled_by.add(name)
            person.encountered.update(t.kind for t in carried + [cloak])
            for place in nearby:
                person.encountered.update(g.kind for g in lands[place].gather.values())
                person.encountered.update(h.species for h in herds if h.place == place)
            people[name] = person
        for name in band:
            world.acquaintances[name] = set(band) - {name}
            world.tell(name, f"당신은 이 무리와 함께 {camp}에서 지낸다. 함께 지내는 사람: {', '.join(n for n in band if n != name)}", incoming=False)
            world.tell(name, "마른 풀과 마른 나뭇가지를 비비면 불을 피울 수 있다는 것을 당신은 해봐서 안다.", incoming=False)
            world.tell(name, "단단한 돌로 부싯돌을 내리치면 날카로운 조각이 떨어진다는 것을 당신은 해봐서 안다.", incoming=False)
            world.tell(name, f"당신은 {camp} 근처 두 칸 안의 곳들을 잘 안다.", incoming=False)
    talent.settle(world)
    return world
