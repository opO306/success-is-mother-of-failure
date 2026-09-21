"""What a body could try right now, and turning a brain's pick into a step on the land.

Options are what is physically at hand: you cannot pick up what is not lying here or walk to a place you do not know.
Whether an attempt works is never checked here. Drinking where there is no water is a real option, and the engine
answers it the way it answers anyone. Words in the steps (a place's name, a kind to gather, "오목하게") exist only on the
engine's side of the line; the brain chose an id among candidates.

Tasting (stage 4) is putting a held thing to the mouth: the engine's own test, a nibble of a tenth of what eating gives,
poison included. Mating and nursing (generations) take the slot on the land as waiting with someone; whether a mating
happened (both chose each other) or milk came (the giver is lactating, the other an infant) is lifecycle.py's to settle.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..primal.clerk import Step
from ..primal.world import Person, World
from . import senses
from .senses import CATEGORIES, Token

OPS = (
    "wait", "rest", "sleep", "train", "guard", "go", "flee", "gather", "pick", "drink", "eat", "fill", "drop", "heat",
    "soak", "dry", "fire", "build", "plant", "fish", "hunt", "feed", "strike", "grind", "scrape", "cut", "bind", "mix",
    "shape", "weave", "give", "follow", "attack", "steal",
    "taste",           # stage 4
    "mate", "nurse",   # generations; new ops go last so earlier ops keep their numbers in older genomes
)
FORMS = ("오목하게", "길쭉하게", "납작하게", "뾰족하게", "둥글게", "넓게")


@dataclass(frozen=True)
class Candidate:
    token: Token
    field: str | None      # "item" | "target" | "what" | "form" | None (nothing)
    value: object = None


NOTHING = Candidate(Token(CATEGORIES["none"], 0, (0.0,) * senses.PROPS), None)


@dataclass
class OpOption:
    op: str
    args: list[list[Candidate]]


def options(world: World, person: Person, gain: float = 1.0) -> list[OpOption]:
    carried = [Candidate(t, "item", i + 1) for i, t in enumerate(senses.carried_tokens(person, gain))]
    gatherable = [Candidate(t, "what", kind) for t, kind in senses.gatherable_tokens(world, person)]
    lying = [Candidate(t, "what", kind) for t, kind in senses.lying_tokens(world, person, gain)]
    herds = [Candidate(t, "target", species) for t, species in senses.herd_tokens(world, person)]
    people = [Candidate(t, "target", name) for t, name in senses.people_tokens(world, person)]
    places = [Candidate(t, "target", place) for t, place in senses.place_tokens(world, person)]
    forms = [Candidate(Token(CATEGORIES["form"], i + 1, (0.0,) * senses.PROPS), "form", word) for i, word in enumerate(FORMS)]
    maybe_carried = [NOTHING] + carried

    out: list[OpOption] = []

    def add(op: str, *args: list[Candidate]) -> None:
        if all(args):
            out.append(OpOption(op, [list(a) for a in args]))

    for op in ("wait", "rest", "sleep", "train", "guard"):
        add(op)
    add("go", places)
    add("flee", places)
    add("gather", gatherable)
    add("pick", lying)
    add("drink", maybe_carried)
    for op in ("eat", "fill", "drop", "heat", "soak", "dry", "plant"):
        add(op, carried)
    for op in ("fire", "build", "fish"):
        add(op, maybe_carried)
    add("hunt", herds, maybe_carried)
    add("feed", herds, carried)
    for op in ("strike", "grind", "scrape", "cut", "bind", "mix"):
        add(op, carried, carried)
    add("shape", carried, forms)
    add("weave", carried, carried, carried, forms)
    add("give", people, carried)
    for op in ("follow", "attack", "steal"):
        add(op, people)
    add("taste", carried)
    for op in ("mate", "nurse"):
        add(op, people)
    return out


def to_step(option: OpOption, picks: list[Candidate]) -> Step:
    fields: dict = {"op": option.op, "items": []}
    for pick in picks:
        if pick.field == "item":
            fields["items"].append(pick.value)
        elif pick.field is not None:
            fields[pick.field] = pick.value
    if option.op == "guard":
        fields["target"] = None
    if option.op == "taste":
        fields.update(op="test", content="맛")
    if option.op in ("mate", "nurse"):
        fields["op"] = "wait"
    return Step(**fields)
