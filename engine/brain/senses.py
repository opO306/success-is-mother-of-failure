"""What a v0 brain perceives: numbers only. No Korean word, no law, no name of a thing ever reaches it.

A kind of thing becomes an arbitrary id (a hash bucket of its engine name), so the id says nothing about what the thing
is, yet the same kind looks the same in every world and every generation. Two kinds can share a bucket, the way two
lookalikes are confused. Only what a person could see or feel is encoded: how badly thirst or cold presses, whether it
rains, what lies around and how it looks (a sharp edge, rot, a hollow), who is near and whether they are known.

Stage 4 adds the near senses. What is held is felt (hard, heavy, rough, bending); what is held or lying close is smelled
(sour, foul); taste needs a mouth, so it shows only on a thing this person has tasted. How loud the three are is the
person's sensory gain. Feelings that are not things (fear now, the pain of those nearby, what was just tasted, how new
the last moment was) come in after the context. Each new number sits after every old one, so a brain from before stage 4
reads its old numbers in their old places.
"""
from __future__ import annotations

import zlib
from dataclasses import dataclass, field

from ..primal import body as physiology
from ..primal import mind as minds
from ..primal import matter, nature
from ..primal.config import SLOTS
from ..primal.matter import Thing
from ..primal.world import Person, World

BODY_KINDS = ("thirst", "hunger", "cold", "wet", "sleepy", "pain", "craving", "danger")
BODY_SIZE = len(BODY_KINDS) + 1 + len(minds.NEEDS)
CONTEXT_SIZE = len(SLOTS) + 7
EXTRA_KINDS = ("fear", "others_pain", "sweet", "bitter", "sour", "foul", "novelty",
               "light", "moon", "arousal")   # sky and adrenaline, appended last so older genomes read the rest in place
EXTRA_SIZE = len(EXTRA_KINDS)
CATEGORIES = {"none": 0, "carried": 1, "gatherable": 2, "lying": 3, "herd": 4, "water": 5, "person": 6, "place": 7, "form": 8,
              "seen": 9}
# What someone nearby was seen doing, grouped as an onlooker sees acts, not as the engine names them
SEEN_GROUPS = (
    ("eat", "taste"), ("drink",), ("gather", "pick", "fish", "fill"), ("hunt", "attack", "feed", "steal"),
    ("strike", "grind", "scrape", "cut", "bind", "mix", "shape", "weave", "heat", "soak", "dry", "fire", "build", "plant"),
)
LOOKS = 8      # props seen (the first 8, as before stage 4)
PROPS = 16     # + touch 4, smell 2, taste 2
KIND_BUCKETS = 4093
MAX_CARRIED, MAX_LYING, MAX_PLACES, MAX_PEOPLE = 12, 12, 12, 12


@dataclass(frozen=True)
class Token:
    category: int
    kind: int
    props: tuple[float, ...]


@dataclass
class Sense:
    body: tuple[float, ...]
    context: tuple[float, ...]
    tokens: list[Token]
    extra: tuple[float, ...] = field(default=(0.0,) * EXTRA_SIZE)


def kind_id(name: str) -> int:
    return 1 + zlib.crc32(name.encode("utf-8")) % (KIND_BUCKETS - 1)


def _pad(values: tuple[float, ...]) -> tuple[float, ...]:
    return (tuple(values) + (0.0,) * PROPS)[:PROPS]


def _look(thing: Thing) -> tuple[float, ...]:
    return (
        1.0 if thing.p("sharpness") >= 0.35 else 0.0,
        1.0 if thing.p("spoil") >= 0.5 else 0.0,
        1.0 if thing.p("cooked") >= 1.0 else 0.0,
        1.0 if thing.p("fired") >= 1.0 else 0.0,
        1.0 if thing.shape == "오목함" else 0.0,
        1.0 if thing.p("moisture") >= 0.5 else 0.0,
        1.0 if thing.contents else 0.0,
        1.0 if thing.parts else 0.0,
    )


def looks(thing: Thing) -> tuple[float, ...]:
    """How a thing looks: the same cues describe() gives a person in words."""
    return _pad(_look(thing))


def feels(thing: Thing, person: str, held: bool, gain: float = 1.0) -> tuple[float, ...]:
    """Touch (only in the hand), smell, and taste (only once this person has tasted it), each as loud as their gain."""
    touch = (thing.p("hardness") >= 0.6, thing.p("weight") >= 0.5, thing.p("roughness") >= 0.5,
             thing.p("flexibility") >= 0.5) if held else (False,) * 4
    smell = (thing.p("ferment") >= 0.3, thing.p("spoil") >= 0.5)
    tasted = "taste" in thing.tested.get(person, set())
    taste = (thing.p("sweetness") >= 0.4, thing.p("toxicity") >= 0.3) if tasted else (False, False)
    return tuple(min(2.0, gain * float(v)) for v in touch + smell + taste)


def body_vector(world: World, person: Person, circadian: float = 0.0) -> tuple[float, ...]:
    if world.config.graded_feelings:
        pressing = physiology.felt_levels(person.body, world.config, circadian)
    else:
        pressing = physiology.distress(person.body, world.config)
    felt = tuple(pressing.get(kind, 0.0) for kind in BODY_KINDS)
    needs = tuple(min(1.0, person.mind.need[n] / 100) for n in minds.NEEDS)
    return felt + (person.body.health / 100,) + needs


def context_vector(world: World, person: Person, slot_index: int) -> tuple[float, ...]:
    land = world.lands[person.location]
    here = world.at(land.name)
    temp = nature.air_temp(world.weather, SLOTS[slot_index], world.config)
    roof, _ = nature.shelter_at(land, len(here))
    slot = tuple(1.0 if i == slot_index else 0.0 for i in range(len(SLOTS)))
    return slot + (float(world.weather.raining), float(world.weather.storm), max(-1.0, min(1.0, temp / 30)),
                   1.0 if land.fire else 0.0, roof, min(1.0, (len(here) - 1) / 10), min(1.0, len(land.corpses) / 5))


def carried_tokens(person: Person, gain: float = 1.0) -> list[Token]:
    return [Token(CATEGORIES["carried"], kind_id(t.kind), _look(t) + feels(t, person.name, True, gain))
            for t in person.carried[:MAX_CARRIED]]


def _standing(kind: str) -> Thing | None:
    """One of the things a patch is made of, to be looked at. Nothing of this particular patch, only its kind."""
    template = matter.TEMPLATES.get(kind)
    return Thing(id=0, kind=kind, props=dict(template.props)) if template is not None else None


def gatherable_tokens(world: World, person: Person, gain: float = 1.0) -> list[tuple[Token, str]]:
    """What grows here, as eyes and nose take it: how much there is, what it looks like, what it smells of, and - only
    for a mouth that has had this kind before - what it tastes of. Until 2026-09-17 a patch showed nothing but its
    amount, so berries and branches looked alike and there was nothing to choose by."""
    land = world.lands[person.location]
    tasted = world.tasted_kinds.get(person.name, ())
    out = []
    for g in land.gather.values():
        if g.stock < 1:
            continue
        one = _standing(g.kind)
        props = (min(1.0, g.stock / 30),) + (_look(one)[1:] if one is not None else ())
        if one is not None:
            known = one.tested.setdefault(person.name, set())
            if g.kind in tasted:
                known.add("taste")
            props = props + feels(one, person.name, False, gain)
        out.append((Token(CATEGORIES["gatherable"], kind_id(g.kind), _pad(props)), g.kind))
    return out


def lying_tokens(world: World, person: Person, gain: float = 1.0) -> list[tuple[Token, str]]:
    land = world.lands[person.location]
    return [(Token(CATEGORIES["lying"], kind_id(t.kind), _look(t) + feels(t, person.name, False, gain)), t.kind)
            for t in land.lying[:MAX_LYING]]


def herd_tokens(world: World, person: Person) -> list[tuple[Token, str]]:
    return [(Token(CATEGORIES["herd"], kind_id(h.species), _pad((min(1.0, h.count / 20),))), h.species)
            for h in world.herds if h.place == person.location and h.count > 0]


def water_tokens(world: World, person: Person) -> list[Token]:
    land = world.lands[person.location]
    water = land.water or (nature.puddle_water(land, world.weather) if world.config.puddles else None)
    return [Token(CATEGORIES["water"], kind_id(water), _pad(()))] if water else []


def people_tokens(world: World, person: Person) -> list[tuple[Token, str]]:
    known = world.acquaintances.get(person.name, set())
    out = []
    for other in world.at(person.location):
        if other.name == person.name:
            continue
        props = (1.0 if other.name in known else 0.0, person.mind.bonds.get(other.name, 0.0),
                 1.0 if other.camp == person.camp else 0.0, 1.0 if other.name in world.asleep else 0.0)
        out.append((Token(CATEGORIES["person"], 0, _pad(props)), other.name))
    return out[:MAX_PEOPLE]


def place_tokens(world: World, person: Person) -> list[tuple[Token, str]]:
    out = []
    for place in sorted(person.known_places):
        if place == person.location:
            continue
        route = world.map.route(person.location, place)
        if route is not None:
            out.append((Token(CATEGORIES["place"], kind_id(world.lands[place].kind), _pad((min(1.0, route[1] / 6),))), place))
    return out[:MAX_PLACES]


def seen_token(op: str, kind: str | None, ok: bool, pleasure: float, disgust: float, pain: float, fear: float,
               kin: bool, bond: float) -> Token:
    """Someone nearby, just now: which sort of act, on what (the same id the thing has in one's own hands), whether it
    worked, and the face after it. Faces after a taste are innate in people and apes (Steiner); pain and fear show too."""
    group = next((i for i, ops in enumerate(SEEN_GROUPS) if op in ops), len(SEEN_GROUPS))
    onehot = tuple(1.0 if i == group else 0.0 for i in range(len(SEEN_GROUPS) + 1))
    props = onehot + (float(ok), min(2.0, pleasure), min(2.0, disgust), pain, fear, float(kin), bond)
    return Token(CATEGORIES["seen"], kind_id(kind) if kind else 0, _pad(props))


def sense(world: World, person: Person, slot_index: int, extra: tuple[float, ...] | None = None, gain: float = 1.0,
          seen: list[Token] | None = None, circadian: float = 0.0) -> Sense:
    tokens = carried_tokens(person, gain) + [t for t, _ in gatherable_tokens(world, person, gain)]
    tokens += [t for t, _ in lying_tokens(world, person, gain)]
    tokens += [t for t, _ in herd_tokens(world, person)] + water_tokens(world, person)
    tokens += [t for t, _ in people_tokens(world, person)] + [t for t, _ in place_tokens(world, person)]
    tokens += list(seen or [])
    felt = tuple(extra) if extra is not None else (0.0,) * EXTRA_SIZE
    return Sense(body_vector(world, person, circadian), context_vector(world, person, slot_index), tokens, felt)
