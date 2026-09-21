"""A snapshot read as plain fields, for comparing one stage against the next.

Compliance checking works on the difference between two recorded stages, so
each snapshot is flattened into `{point: value}` maps. Cells the recorder
dropped because they became empty read as zero rather than as missing, which
is what makes "this cell lost all its water" and "this cell is absent"
the same statement.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


class FieldError(ValueError):
    """A snapshot cannot be read as an integer field."""


def _integer(value: Any, what: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise FieldError(f"{what} must be an integer, found {value!r}")
    return value


@dataclass(frozen=True)
class FieldView:
    """One snapshot, flattened to per-cell quantities."""

    heat: Mapping[tuple[int, int], int]
    water: Mapping[tuple[int, int], int]
    vapor: Mapping[tuple[int, int], int]
    mineral: Mapping[tuple[int, int], int]
    elevation: Mapping[tuple[int, int], int]
    solutes: Mapping[tuple[int, int], tuple[int, ...]]
    energy_supplied: int
    energy_removed: int
    points: frozenset[tuple[int, int]]

    def solute(self, point: tuple[int, int], kind: int) -> int:
        values = self.solutes.get(point)
        return values[kind] if values and kind < len(values) else 0

    def channel(self, name: str, point: tuple[int, int]) -> int:
        return {"heat": self.heat, "water": self.water,
                "vapor": self.vapor, "mineral": self.mineral}[name].get(point, 0)


def read_field(snapshot: Mapping[str, Any], solute_kinds: int) -> FieldView:
    if not isinstance(snapshot, Mapping):
        raise FieldError("snapshot must be a mapping")
    causal = snapshot.get("causal")
    if not isinstance(causal, Mapping):
        raise FieldError("snapshot has no causal section")

    heat: dict[tuple[int, int], int] = {}
    for cell in causal.get("heat") or ():
        point = (_integer(cell.get("x"), "heat x"), _integer(cell.get("y"), "heat y"))
        heat[point] = _integer(cell.get("energy", 0), "heat energy")

    water: dict[tuple[int, int], int] = {}
    vapor: dict[tuple[int, int], int] = {}
    mineral: dict[tuple[int, int], int] = {}
    elevation: dict[tuple[int, int], int] = {}
    solutes: dict[tuple[int, int], tuple[int, ...]] = {}
    for cell in snapshot.get("cells") or ():
        point = (_integer(cell.get("x"), "cell x"), _integer(cell.get("y"), "cell y"))
        water[point] = _integer(cell.get("water", 0), "cell water")
        vapor[point] = _integer(cell.get("vapor", 0), "cell vapor")
        mineral[point] = _integer(cell.get("mineral", 0), "cell mineral")
        elevation[point] = _integer(cell.get("elevation", 0), "cell elevation")
        recorded = cell.get("solutes") or ()
        solutes[point] = tuple(
            _integer(recorded[k], f"cell solute {k}") if k < len(recorded) else 0
            for k in range(solute_kinds)
        )

    points = frozenset(heat) | frozenset(water)
    return FieldView(
        heat=heat, water=water, vapor=vapor, mineral=mineral,
        elevation=elevation, solutes=solutes,
        energy_supplied=_integer(snapshot.get("energy_supplied", 0), "energy_supplied"),
        energy_removed=_integer(snapshot.get("energy_removed", 0), "energy_removed"),
        points=points,
    )


def changed_points(before: FieldView, after: FieldView,
                   solute_kinds: int) -> set[tuple[int, int]]:
    """Every cell whose contents differ between the two snapshots."""
    candidates = set(before.points) | set(after.points) | set(before.water) | set(after.water)
    moved = set()
    for point in candidates:
        if (before.heat.get(point, 0) != after.heat.get(point, 0)
                or before.water.get(point, 0) != after.water.get(point, 0)
                or before.vapor.get(point, 0) != after.vapor.get(point, 0)
                or before.mineral.get(point, 0) != after.mineral.get(point, 0)
                or any(before.solute(point, k) != after.solute(point, k)
                       for k in range(solute_kinds))):
            moved.add(point)
    return moved
