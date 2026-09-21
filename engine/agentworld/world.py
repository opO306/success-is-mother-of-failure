from __future__ import annotations

import random
from dataclasses import dataclass, field

from .. import recorder as recording
from ..knowledge import Knowledge
from .config import WorldConfig
from .model import Bank, Contract, Offer, Order, Org, Person, Trade, WorldMap

NOTE_SUFFIX = " 지폐"


def note_name(issuer: str) -> str:
    return f"{issuer}{NOTE_SUFFIX}"


def note_issuer(good: str | None) -> str | None:
    return good[: -len(NOTE_SUFFIX)] if good and good.endswith(NOTE_SUFFIX) else None


@dataclass
class World:
    config: WorldConfig
    map: WorldMap
    people: dict[str, Person]
    orgs: dict[str, Org]
    bank: Bank
    rng: random.Random
    day: int = 1
    label: str = "agentworld"
    knowledge: dict[str, Knowledge] = field(default_factory=dict)
    acquaintances: dict[str, set[str]] = field(default_factory=dict)
    contracts: list[Contract] = field(default_factory=list)
    offers: list[Offer] = field(default_factory=list)
    orders: list[Order] = field(default_factory=list)
    trades: list[Trade] = field(default_factory=list)
    next_order_id: int = 1
    # what an owner will find missing the next time they are at that place: (place, owner) -> lines
    pending_losses: dict[tuple[str, str], list[str]] = field(default_factory=dict)
    seen_corpses: dict[str, set[str]] = field(default_factory=dict)
    # per-slot physical state, rebuilt every slot
    asleep: set[str] = field(default_factory=set)
    guarding: dict[str, str] = field(default_factory=dict)
    busy: set[str] = field(default_factory=set)   # travelling or held; cannot act at the place
    seen_today: dict[str, dict[str, set[str]]] = field(default_factory=dict)
    # what each person did today, told back to them as one line at night so memory is not flooded
    day_log: dict[str, list[str]] = field(default_factory=dict)
    notices_read: dict[str, set[tuple[str, str, int, str]]] = field(default_factory=dict)
    losses_to_tell: dict[str, list[str]] = field(default_factory=dict)
    events_today: list[str] = field(default_factory=list)       # for the human-readable digest only
    plans_today: list[tuple[str, str]] = field(default_factory=list)

    def log(self, name: str, text: str) -> None:
        self.day_log.setdefault(name, []).append(text)

    # ---- lookups
    def person(self, name: str | None) -> Person | None:
        return self.people.get(name) if name else None

    def living(self) -> list[Person]:
        return [p for p in self.people.values() if p.alive]

    def org(self, name: str | None) -> Org | None:
        org = self.orgs.get(name) if name else None
        return org if org is not None and org.alive else None

    def org_of(self, person: Person) -> Org | None:
        return self.org(person.org)

    def at(self, place: str) -> list[Person]:
        return [p for p in self.living() if p.location == place]

    def awake_at(self, place: str, exclude: set[str] | frozenset[str] = frozenset()) -> list[Person]:
        return [
            p for p in self.at(place)
            if p.name not in self.asleep and p.name not in self.busy and p.name not in exclude
        ]

    def stash(self, place: str, holder: str) -> dict[str, float]:
        return self.map.places[place].stash.setdefault(holder, {})

    def knows(self, actor: str, name: str | None) -> bool:
        return bool(name) and name in self.acquaintances.get(actor, set())

    # ---- knowledge
    def tell(
        self, person: str, text: str, source: str | None = None, incoming: bool = True, slot: str | None = None,
    ) -> None:
        who = self.people.get(person)
        if who is None or not who.alive:
            return
        stamp = f"{self.day}일째" + (f" {slot}" if slot else "")
        self.knowledge.setdefault(person, Knowledge()).add(self.day, f"[{stamp}] {text}", source=source, incoming=incoming)
        known = self.acquaintances.setdefault(person, set())
        if source and source != person:
            known.add(source)
        # hearing a name is how someone comes to know that a person, an org or a place exists
        for org_name in self.orgs:
            if org_name in text:
                known.add(org_name)
        for other in self.people:
            if other != person and other in text:
                known.add(other)
        for place in self.map.places:
            if place in text:
                who.known_places.add(place)
        recorder = recording.active()
        if recorder is not None:
            recorder.write("deliveries", {
                "day": self.day, "slot": slot, "to": person, "text": text, "source": source, "incoming": incoming,
            })

    def arrive(self, person: Person, place: str) -> None:
        person.location = place
        person.known_places.add(place)
        # standing somewhere, you can see where its roads lead
        person.known_places.update(self.map.neighbors(place))
