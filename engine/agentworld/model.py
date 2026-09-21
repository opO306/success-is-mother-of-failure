from __future__ import annotations

import heapq
from dataclasses import dataclass, field

from ..entities import Proposal


@dataclass
class Injury:
    kind: str            # "가벼운 상처" | "깊은 상처"
    bleeding: bool
    days: int = 0
    treated: bool = False


@dataclass
class Body:
    health: float = 100.0
    strength: float = 20.0
    reserve: float = 1.0          # days of food the body still has
    eaten_today: float = 0.0
    underfed_days: int = 0
    slept_today: int = 0
    sleep_debt: float = 0.0
    trained_today: int = 0
    injuries: list[Injury] = field(default_factory=list)
    illness: float = 0.0
    addiction: float = 0.0
    used_drug_today: bool = False
    alive: bool = True
    cause_of_death: str = ""


@dataclass
class Letter:
    sender: str
    recipient: str
    content: str
    day: int


@dataclass
class Person:
    name: str
    home: str
    location: str
    money: float = 0.0
    inventory: dict[str, float] = field(default_factory=dict)
    body: Body = field(default_factory=Body)
    org: str | None = None
    tech: float = 1.0
    skills: dict[str, float] = field(default_factory=dict)
    disposition: str | None = None
    grudge_target: str | None = None
    temperature: float = 0.7
    known_places: set[str] = field(default_factory=set)
    letters: list[Letter] = field(default_factory=list)
    plan_steps: list = field(default_factory=list)   # clerk Steps for the current routine
    habit: bool = False                               # they said to live today like yesterday
    felt_at_plan: tuple[str, ...] = ()
    restrained_day: int = -1                          # overpowered and held for the rest of that day

    @property
    def alive(self) -> bool:
        return self.body.alive


@dataclass
class Org:
    name: str
    building: str
    money: float = 0.0
    tech: float = 1.0
    members: list[str] = field(default_factory=list)
    agenda: list[Proposal] = field(default_factory=list)
    applicants: list[str] = field(default_factory=list)
    resolutions: list[str] = field(default_factory=list)
    origin: str = ""      # the starting condition it was built from; never shown to anyone inside the world
    alive: bool = True


@dataclass
class Contract:
    employer: str         # org or person name
    worker: str
    wage: float
    every_days: int
    next_pay_day: int
    unpaid: int = 0


@dataclass
class Offer:
    employer: str
    worker: str
    wage: float
    every_days: int
    day: int
    told: bool = False    # the worker only knows once it has reached them


@dataclass
class Order:
    id: int
    owner: str
    side: str             # "buy" | "sell"
    good: str
    qty: float
    price: float
    day: int


@dataclass
class Trade:
    day: int
    slot: str
    good: str
    qty: float
    price: float
    buyer: str
    seller: str


@dataclass
class Notice:
    author: str
    text: str
    day: int


@dataclass
class Loan:
    borrower: str
    principal: float
    outstanding: float
    rate: float
    due_day: int
    closed: bool = False
    defaulted: bool = False


@dataclass
class Bank:
    place: str = "은행"
    coins: float = 0.0
    loans: list[Loan] = field(default_factory=list)
    refused: set[str] = field(default_factory=set)   # borrowers who defaulted


@dataclass
class Place:
    name: str
    kind: str
    village: str | None = None
    deposits: dict[str, float] = field(default_factory=dict)
    regen: dict[str, float] = field(default_factory=dict)
    caps: dict[str, float] = field(default_factory=dict)
    yields: dict[str, float] = field(default_factory=dict)   # per worked slot, before tech, skill and tools
    stash: dict[str, dict[str, float]] = field(default_factory=dict)  # holder -> good -> qty
    notices: list[Notice] = field(default_factory=list)
    telegraph: bool = False
    steam_engines: dict[str, int] = field(default_factory=dict)  # owner -> installed engines
    corpses: list[str] = field(default_factory=list)


class WorldMap:
    def __init__(self) -> None:
        self.places: dict[str, Place] = {}
        self.roads: dict[str, dict[str, int]] = {}

    def add_place(self, place: Place) -> Place:
        self.places[place.name] = place
        self.roads.setdefault(place.name, {})
        return place

    def connect(self, a: str, b: str, slots: int) -> None:
        self.roads.setdefault(a, {})[b] = slots
        self.roads.setdefault(b, {})[a] = slots

    def neighbors(self, name: str) -> dict[str, int]:
        return self.roads.get(name, {})

    def route(self, start: str, goal: str) -> tuple[list[str], int] | None:
        """Shortest path as the list of places after `start`, and its total travel slots."""
        if start not in self.places or goal not in self.places:
            return None
        best = {start: 0}
        previous: dict[str, str] = {}
        queue = [(0, start)]
        while queue:
            cost, here = heapq.heappop(queue)
            if here == goal:
                break
            if cost > best.get(here, 1 << 30):
                continue
            for there, step in self.roads.get(here, {}).items():
                candidate = cost + step
                if candidate < best.get(there, 1 << 30):
                    best[there] = candidate
                    previous[there] = here
                    heapq.heappush(queue, (candidate, there))
        if goal not in best:
            return None
        path = [goal]
        while path[-1] != start:
            path.append(previous[path[-1]])
        path.reverse()
        return path[1:], best[goal]
