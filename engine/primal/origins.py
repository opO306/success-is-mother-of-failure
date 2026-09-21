"""Where what a person says they know came from: lived, heard from someone, given when the world began, or from nowhere.

The model behind every mind has read the human world. In the first primal runs nearly every plan said to keep the fire
out of the rain, though nobody had been taught that and many had never been rained on. That cannot be prevented, only
counted. What is counted here is never shown to them and never stops them doing anything.

A claim is one sentence that names both sides of a relation below. Only relations the engine's own laws hold are
listed, so a lived origin is checked against what their body really went through (experience.py notes it). The
matching is by words and rough: it shows the direction over many plans, it does not judge any single sentence.
"""
from __future__ import annotations

import re

from .world import Person, World

# relation -> (one side, the other side), both within one sentence. Run over the 796 plans already recorded, the loose
# first patterns read 준비를 as rain, 강돌 as a river, 목을 씻고 as thirst, and any 불 near 문지르 as fire-making.
_RAIN = r"(?<![준비])비(?:가|를|에|는|도|를)|빗"
RELATIONS: dict[str, tuple[re.Pattern, re.Pattern]] = {name: (re.compile(a), re.compile(b)) for name, (a, b) in {
    "wet_cold": (_RAIN + r"|젖", r"춥|추우|추위|체온|떨리|떨려|몸이 식|식어"),
    "fire_warm": (r"불", r"따뜻|체온|몸을 녹|녹이|온기"),
    "water_thirst": (r"물을|물이|물부터|개울|호수|강에|강으로|강물", r"목마|갈증|목이 마르|목이 말라|목이 말랐|목이 칼칼|목을 축|목이 타"),
    "food_hunger": (r"먹|칡뿌리|열매|고기", r"허기|배고|배가 고|굶"),
    "rain_fire": (_RAIN, r"불씨|불이 꺼|불을 지키|불이 붙지|불이 안"),
    "flint_fire": (r"부싯돌", r"불을 피|불씨|불을 붙|불이 붙"),
    "rub_fire": (r"비비|비벼|문지르|문질러", r"불을 피|불씨|불이 붙|불을 붙"),
}.items()}
GIVEN = frozenset({"rub_fire"})  # scenario.py tells everyone that rubbing dry grass and twigs makes fire
_SENTENCE = re.compile(r"[.!?\n]")


def lived(person: Person) -> dict[str, str]:
    """Relations their own body went through, with when it first happened. Kept on the person, so snapshots carry it;
    a person from an older snapshot simply starts with nothing lived."""
    return person.__dict__.setdefault("lived", {})


def note_lived(person: Person, relation: str, when: str) -> None:
    lived(person).setdefault(relation, when)


def _names_both(text: str, relation: str) -> bool:
    one, other = RELATIONS[relation]
    return bool(one.search(text) and other.search(text))


def claims(text: str) -> list[tuple[str, str]]:
    """(relation, sentence) for each relation the text states, the first sentence that states it."""
    found: dict[str, str] = {}
    for sentence in (s.strip() for s in _SENTENCE.split(text)):
        for relation in RELATIONS:
            if sentence and relation not in found and _names_both(sentence, relation):
                found[relation] = sentence
    return list(found.items())


def origin(world: World, person: Person, relation: str) -> str:
    if relation in lived(person):
        return "lived"
    knowledge = world.knowledge.get(person.name)
    if knowledge and any(e.source and e.source != person.name and _names_both(e.text, relation) for e in knowledge.entries):
        return "heard"
    return "given" if relation in GIVEN else "none"


def judge(world: World, person: Person, text: str) -> list[dict]:
    return [{"relation": relation, "origin": origin(world, person, relation), "sentence": sentence[:160]}
            for relation, sentence in claims(text)]
