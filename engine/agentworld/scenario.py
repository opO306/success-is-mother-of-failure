"""The starting world: 48 people, four orgs, three villages. Starting conditions only; nothing here is a role."""
from __future__ import annotations

import random

from .config import WorldConfig
from .model import Bank, Body, Contract, Org, Person, Place, WorldMap
from .world import World

ORG_NAMES = ["조직A", "조직B", "조직C", "조직D"]
VILLAGES = ["동쪽 마을", "서쪽 마을", "북쪽 마을"]
DISPOSITIONS = ["protector", "grudge", "opportunist", "indifferent"]


def build_map() -> WorldMap:
    m = WorldMap()
    m.add_place(Place("시장", "시장"))
    m.add_place(Place("은행", "은행"))
    for village in VILLAGES:
        m.add_place(Place(village, "마을"))
    for village, farm in zip(VILLAGES, ["동쪽 농지", "서쪽 농지", "북쪽 농지"]):
        m.add_place(Place(farm, "농지", deposits={"식량": 150.0}, regen={"식량": 20.0}, caps={"식량": 200.0}, yields={"식량": 2.0}))
        m.connect(village, farm, 1)
    m.add_place(Place("강", "강", deposits={"물고기": 30.0}, regen={"물고기": 5.0}, caps={"물고기": 40.0}, yields={"물고기": 1.0}))
    m.add_place(Place(
        "숲", "숲", deposits={"목재": 300.0, "약초": 60.0}, regen={"목재": 3.0, "약초": 2.0},
        caps={"목재": 300.0, "약초": 60.0}, yields={"목재": 3.0, "약초": 1.0},
    ))
    m.add_place(Place("탄광", "탄광", deposits={"석탄": 600.0}, yields={"석탄": 3.0}))
    m.add_place(Place("철광", "철광", deposits={"철광석": 400.0}, yields={"철광석": 2.0}))
    m.add_place(Place("갈림길", "길목"))
    m.connect("시장", "은행", 0)
    m.connect("시장", "동쪽 마을", 1)
    m.connect("시장", "서쪽 마을", 1)
    m.connect("시장", "북쪽 마을", 2)
    m.connect("시장", "갈림길", 1)
    m.connect("갈림길", "탄광", 2)
    m.connect("갈림길", "철광", 2)
    m.connect("탄광", "철광", 1)
    m.connect("서쪽 마을", "숲", 2)
    m.connect("숲", "강", 1)
    m.connect("동쪽 마을", "강", 2)
    return m


def build_world(seed: int | None = None, org_sizes: tuple[int, int, int, int] = (14, 14, 4, 4), unaffiliated: int = 12) -> World:
    rng = random.Random(seed)
    config = WorldConfig()
    world_map = build_map()
    starts = [
        ("DOOMSAYER", org_sizes[0], rng.uniform(600, 900), rng.uniform(2, 8), {"식량": 40, "도구": 6, "철": 5, "석탄": 10}),
        ("SAFETY_COORDINATOR", org_sizes[1], rng.uniform(600, 900), rng.uniform(2, 8), {"식량": 40, "도구": 6, "철": 5, "석탄": 10}),
        ("GROWTH", org_sizes[2], 450.0, 10.0, {"식량": 15, "도구": 2, "철": 2}),
        ("CONGLOMERATE", org_sizes[3], 350.0, 8.0, {"식량": 15, "도구": 2, "철": 2}),
    ]
    org_names = list(ORG_NAMES)
    rng.shuffle(org_names)
    anchors = ["동쪽 마을", "서쪽 마을", "시장", "북쪽 마을"]
    total = sum(s[1] for s in starts) + unaffiliated
    ids = [f"P{i:02d}" for i in range(1, total + 1)]
    rng.shuffle(ids)

    people: dict[str, Person] = {}
    orgs: dict[str, Org] = {}
    contracts: list[Contract] = []

    def new_person(village: str, money: float) -> Person:
        name = ids.pop()
        home = f"{name}의 집"
        world_map.add_place(Place(home, "집", village=village))
        world_map.connect(village, home, 0)
        person = Person(
            name=name, home=home, location=home, money=round(money, 1), inventory={"식량": 3.0},
            body=Body(strength=rng.uniform(12, 28)), temperature=rng.uniform(0.3, 1.1),
        )
        people[name] = person
        return person

    for (origin, size, coins, tech, stash), org_name, anchor in zip(starts, org_names, anchors):
        building = f"{org_name} 건물"
        world_map.add_place(Place(building, "조직 건물"))
        world_map.connect(anchor, building, 1)
        org = Org(name=org_name, building=building, money=round(coins, 1), tech=tech, origin=origin)
        world_map.places[building].stash[org_name] = {k: float(v) for k, v in stash.items()}
        orgs[org_name] = org
        for _ in range(size):
            village = anchor if anchor in VILLAGES else rng.choice(VILLAGES)
            member = new_person(village, rng.uniform(5, 20))
            member.org = org_name
            org.members.append(member.name)
            contracts.append(Contract(org_name, member.name, round(rng.uniform(8, 15), 1), 7, 7))

    loners: list[Person] = []
    for _ in range(unaffiliated):
        person = new_person(rng.choice(VILLAGES), rng.uniform(15, 30))
        person.disposition = rng.choice(DISPOSITIONS)
        if person.disposition == "grudge":
            person.grudge_target = rng.choice(list(orgs))
        loners.append(person)

    world = World(
        config=config, map=world_map, people=people, orgs=orgs, bank=Bank(coins=800.0), rng=rng,
        contracts=contracts, label="agentworld",
    )
    _seed_knowledge(world)
    return world


def _seed_knowledge(world: World) -> None:
    org_list = ", ".join(world.orgs)
    for person in world.people.values():
        village = world.map.places[person.home].village
        world.arrive(person, person.home)
        person.known_places.update({village, "시장", "은행"})
        person.known_places.update(world.map.neighbors(village))
        known = world.acquaintances.setdefault(person.name, set())
        known.update(world.orgs)
        known.update(p.name for p in world.people.values() if world.map.places[p.home].village == village and p.name != person.name)
        org = world.org_of(person)
        if org is not None:
            person.known_places.add(org.building)
            coworkers = [m for m in org.members if m != person.name]
            known.update(coworkers)
            world.tell(person.name, f"당신은 {org.name}에서 일한다. 일터는 {org.building}. 함께 일하는 사람: {', '.join(coworkers) or '없음'}", incoming=False)
        else:
            world.tell(person.name, "당신은 어느 조직에도 속해 있지 않다.", incoming=False)
        world.tell(person.name, f"이 고장에 있다고 알려진 조직: {org_list}. 시장 옆에 은행이 있다.", incoming=False)
        world.tell(person.name, f"당신은 {village}에 산다. 이웃: {', '.join(sorted(n for n in known if n in world.people)) or '없음'}", incoming=False)
