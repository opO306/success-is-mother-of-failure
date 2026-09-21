"""Each slot of a life kept as a record: what was on them, what they did, what they thought, what it did to their body.

Stage 1 of the knowledge-and-habit design. The record is written for study and for habits later; it changes nothing
anyone meets in the world. The one thing a person does meet is their own thought from the morning, remembered in their
own words.
"""
from __future__ import annotations

from .. import recorder as recording
from ..agentworld.actions import SlotIntent
from . import mind as minds
from . import origins
from .world import Person, World

# a need is "on their mind" from the first level at which it is felt at all
_FIRST_FELT = {need: levels[0][0] for need, levels in minds._SIGNALS.items()}
# a body distress that lifted is lived proof of what lifts it
_LIFTED_BY = {"thirst": "water_thirst", "hunger": "food_hunger"}


def cue(world: World, person: Person, distress: dict[str, float]) -> dict:
    """What was on them as the slot began, bundled coarsely so the same situation can come round again."""
    body = sorted((kind for kind, level in distress.items() if level > 0), key=lambda kind: -distress[kind])
    mind = sorted((need for need, line in _FIRST_FELT.items() if person.mind.need[need] >= line), key=lambda need: -person.mind.need[need])
    weather = world.weather
    return {
        "felt": body[:2] + mind[:1],
        "weather": "폭풍" if weather.storm else "비" if weather.raining else "맑음",
        "place_kind": world.lands[person.location].kind,
        "alone": len(world.at(person.location)) <= 1,
    }


def remember_thought(world: World, person: Person, thought: str) -> None:
    """Their own reason for the day, in their own words, into their own memory."""
    if not thought:
        return
    world.__dict__.setdefault("thoughts_today", {})[person.name] = (world.day, thought)
    world.tell(person.name, f"속으로 든 생각: {thought}", incoming=False)


def record(world: World, person: Person, slot: str, began: dict | None, intent: SlotIntent,
           after: dict[str, float], relieved: str, relief: float, pleasure: float) -> None:
    done = world.__dict__.get("slot_done", {}).get(person.name, [])
    when = f"{world.day}일 {slot}"
    # what their body went through, only as the laws made it happen
    if relief > 0 and relieved in _LIFTED_BY:
        origins.note_lived(person, _LIFTED_BY[relieved], when)
    if relief > 0 and relieved == "cold" and world.lands[person.location].fire:
        origins.note_lived(person, "fire_warm", when)
    if person.body.wet >= 0.5 and after.get("cold", 0.0) > 0:
        origins.note_lived(person, "wet_cold", when)
    if any(d["op"] == "fire" and any("비가 와서" in line for line in d["felt"]) for d in done):
        origins.note_lived(person, "rain_fire", when)
    recorder = recording.active()
    if recorder is None:
        return
    day, thought = world.__dict__.get("thoughts_today", {}).get(person.name, (None, ""))
    recorder.write("experiences", {
        "day": world.day, "slot": slot, "person": person.name, "place": person.location, "cue": began,
        "main": intent.main, "did": done, "thought": thought if day == world.day else "",
        "body": {"relieved": relieved if relief > 0 else None, "relief": round(relief, 3),
                 "pressing": round(max(after.values(), default=0.0), 3)},
        "pleasure": round(pleasure, 3), "how": "생각해서",
    })

