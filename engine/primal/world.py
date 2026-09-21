from __future__ import annotations

import random
from dataclasses import dataclass, field

from .. import recorder as recording
from ..agentworld.model import WorldMap
from ..knowledge import Knowledge
from .body import PrimalBody
from .config import PrimalConfig
from .matter import Maker, Thing
from .mind import Mind
from .nature import Herd, Land, Weather
from .senses import polish


@dataclass
class Person:
    name: str
    camp: str
    location: str
    body: PrimalBody
    mind: Mind
    carried: list[Thing] = field(default_factory=list)
    worn: list[Thing] = field(default_factory=list)
    skills: dict[str, float] = field(default_factory=dict)
    gather_progress: dict[str, float] = field(default_factory=dict)   # nature.gather: what is picked but not yet a whole thing
    temperature: float = 0.7
    known_places: set[str] = field(default_factory=set)
    encountered: set[str] = field(default_factory=set)    # kinds of things and creatures they have met or heard of
    plan_steps: list = field(default_factory=list)
    plan_item_ids: list[int] = field(default_factory=list)  # what "1, 2, 3" meant in this morning's list
    habit: bool = False
    felt_at_plan: tuple[str, ...] = ()
    restrained_day: int = -1

    @property
    def alive(self) -> bool:
        return self.body.alive

    @property
    def home(self) -> str:   # where someone runs to when fleeing
        return self.camp

    def clothing(self) -> float:
        return min(1.0, sum(t.p("insulation") for t in self.worn))


@dataclass
class World:
    config: PrimalConfig
    map: WorldMap
    lands: dict[str, Land]
    people: dict[str, Person]
    herds: list[Herd]
    maker: Maker
    rng: random.Random
    weather: Weather
    day: int = 1
    label: str = "primal"
    seed: int | None = None
    knowledge: dict[str, Knowledge] = field(default_factory=dict)
    acquaintances: dict[str, set[str]] = field(default_factory=dict)
    asleep: set[str] = field(default_factory=set)
    busy: set[str] = field(default_factory=set)
    guarding: dict[str, str] = field(default_factory=dict)
    following: dict[str, str] = field(default_factory=dict)
    day_log: dict[str, list[str]] = field(default_factory=dict)
    seen_today: dict[str, dict[str, set[str]]] = field(default_factory=dict)
    seen_corpses: dict[str, set[str]] = field(default_factory=dict)
    events_today: list[str] = field(default_factory=list)
    plans_today: list[tuple[str, str]] = field(default_factory=list)
    slot_features: dict[str, dict[str, float]] = field(default_factory=dict)
    slot_activity: dict[str, tuple[str, str]] = field(default_factory=dict)
    leaks_today: dict[str, list[str]] = field(default_factory=dict)
    hunts_done: set[tuple] = field(default_factory=set)
    slot_done: dict[str, list[dict]] = field(default_factory=dict)        # what each did this slot, for experience.py
    animal_acts: list[tuple[str, str, str, str | None]] = field(default_factory=list)   # (place, species, act, on what)
    tasted_kinds: dict[str, set[str]] = field(default_factory=dict)   # person -> kinds whose taste they know
    thoughts_today: dict[str, tuple[int, str]] = field(default_factory=dict)  # (day, their own morning thought)

    # ---- lookups
    def person(self, name: str | None) -> Person | None:
        return self.people.get(name) if name else None

    def living(self) -> list[Person]:
        return [p for p in self.people.values() if p.alive]

    def at(self, place: str) -> list[Person]:
        return [p for p in self.living() if p.location == place]

    def awake_at(self, place: str, exclude: set[str] | frozenset[str] = frozenset()) -> list[Person]:
        return [p for p in self.at(place) if p.name not in self.asleep and p.name not in self.busy and p.name not in exclude]

    def knows(self, actor: str, name: str | None) -> bool:
        return bool(name) and name in self.acquaintances.get(actor, set())

    def log(self, name: str, text: str) -> None:
        self.day_log.setdefault(name, []).append(text)

    def feature(self, name: str, key: str, value: float) -> None:
        bag = self.slot_features.setdefault(name, {})
        bag[key] = max(bag.get(key, 0.0), value)

    # ---- knowledge
    def tell(self, person: str, text: str, source: str | None = None, incoming: bool = True, slot: str | None = None) -> None:
        who = self.people.get(person)
        if who is None or not who.alive:
            return
        stamp = f"{self.day}번째 날" + (f" {slot}" if slot else "")
        text = polish(text)
        self.knowledge.setdefault(person, Knowledge()).add(self.day, f"[{stamp}] {text}", source=source, incoming=incoming)
        known = self.acquaintances.setdefault(person, set())
        if source and source != person:
            known.add(source)
        for other in self.people:
            if other != person and other in text:
                known.add(other)
        for place in self.lands:
            if place in text:
                who.known_places.add(place)
        recorder = recording.active()
        if recorder is not None:
            recorder.write("deliveries", {"day": self.day, "slot": slot, "to": person, "text": text, "source": source, "incoming": incoming})

    def arrive(self, person: Person, place: str) -> None:
        person.location = place
        person.known_places.add(place)
        person.known_places.update(self.map.neighbors(place))
