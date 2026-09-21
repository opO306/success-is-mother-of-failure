"""What code alone can tell is wrong with a clerk's answer.

Nothing here judges what the speaker meant. Each check is a contradiction with the words themselves or with the lists
the clerk was handed: a place never mentioned, a number past the end of what they carry, the same sentence to a row of
names. An answer with none of these can still be wrong; one with any of them is wrong for certain.
"""
from __future__ import annotations

from collections import Counter

from engine.primal.clerk import FEW_ITEM_OPS, Step, _place_meant, _place_said

PROBLEMS = (
    "no_answer", "empty", "whole_as_intent", "unsaid_place", "repeated_talk", "all_items", "item_out_of_range", "unknown_person",
)
_PERSON_OPS = frozenset({"give", "follow", "steal", "attack"})


def problems(text: str, steps: list[Step] | None, carried_count: int, names: list[str], places: list[str], camp: str) -> list[str]:
    if steps is None:
        return ["no_answer"]
    if not steps:
        return ["empty"]
    found = []
    if len(steps) == 1 and steps[0].op == "intent" and len(text) > 30:
        found.append("whole_as_intent")
    for step in steps:
        if step.op in ("go", "flee") and step.target and step.target != "여기" and step.target not in text:
            meant = _place_meant(step.target, places)
            if meant is None or not _place_said(meant, text, places, camp):
                found.append("unsaid_place")
                break
    said = Counter(s.content.strip() for s in steps if s.op == "talk" and s.content.strip())
    if any(count >= 3 for count in said.values()):
        found.append("repeated_talk")
    if carried_count > 2 and any(s.op in FEW_ITEM_OPS and len(set(s.items)) == carried_count for s in steps):
        found.append("all_items")
    if any(i < 1 or i > carried_count for s in steps for i in s.items):
        found.append("item_out_of_range")
    if any(s.op in _PERSON_OPS and s.target and s.target not in names for s in steps):
        found.append("unknown_person")
    return found
