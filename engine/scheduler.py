from __future__ import annotations

from typing import Any

from .physics import person_names


def due_persons(world: Any, tick: int) -> list[str]:
    """A person acts only when something reached them or when they chose to act again."""
    due: list[str] = []
    for name in person_names(world):
        knowledge = world.knowledge.get(name)
        if (knowledge is not None and knowledge.unread > 0) or tick >= world.next_wake.get(name, 0):
            due.append(name)
    return due
