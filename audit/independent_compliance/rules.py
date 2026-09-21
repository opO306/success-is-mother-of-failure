"""The rules a world declares, restated for checking.

Conservation asks whether the totals survived a tick. It cannot ask whether
matter took a legal route to get where it ended up: water that tunnels through
a blocked edge, or jumps to a cell it never touches, leaves every total exactly
as it found them.

This module reads the rules straight out of a world specification document so
they can be checked against what a trace actually recorded. Nothing is imported
from the kernel — the point is to hold the kernel to its own declared contract,
not to ask the kernel whether it obeyed itself.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterator, Mapping

_V2_PLUS = (
    "deterministic-environment-world-spec-v2",
    "deterministic-environment-world-spec-v3",
    "deterministic-environment-world-spec-v4",
)
_V3_PLUS = (
    "deterministic-environment-world-spec-v3",
    "deterministic-environment-world-spec-v4",
)


class RuleError(ValueError):
    """A world specification cannot be read as a set of rules."""


def _integer(value: Any, what: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise RuleError(f"{what} must be an integer, found {value!r}")
    return value


@dataclass(frozen=True)
class WorldRules:
    """Everything needed to judge whether a recorded change was permitted."""

    format: str
    width: int
    height: int
    boundary: str
    solute_kinds: int
    blocked_edges: frozenset[frozenset[tuple[int, int]]]
    phase_order: tuple[str, ...]
    max_heat_transfer: int
    max_water_transfer: int
    max_solute_transfer: int
    max_vapor_transfer: int
    max_mineral_conversion: int
    max_water_phase_change: int
    mineral_solute_kind: int
    mineral_conversion_energy: int
    vaporization_energy: int
    dissolve_heat_at_least: int
    precipitate_heat_at_most: int
    evaporation_heat_at_least: int
    condensation_heat_at_most: int
    hot_solubility_per_water: int
    cold_solubility_per_water: int
    energy_inputs: Mapping[tuple[int, int], int]
    energy_outputs: Mapping[tuple[int, int], int]

    @property
    def wraps(self) -> bool:
        return self.boundary == "wrap"

    @property
    def has_vapor(self) -> bool:
        return self.format in _V3_PLUS

    @property
    def has_mineral_conversion(self) -> bool:
        return self.format in _V2_PLUS

    def neighbours(self, point: tuple[int, int]) -> set[tuple[int, int]]:
        """Cells `point` may exchange with in one transport step."""
        x, y = point
        found = set()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if self.wraps:
                nx, ny = nx % self.width, ny % self.height
            elif not (0 <= nx < self.width and 0 <= ny < self.height):
                continue
            found.add((nx, ny))
        return found

    def is_blocked(self, first: tuple[int, int], second: tuple[int, int]) -> bool:
        return frozenset((first, second)) in self.blocked_edges

    def phase_pairs(self, phase: str) -> Iterator[tuple[tuple[int, int], tuple[int, int]]]:
        """The cell pairs a named transport phase is allowed to touch.

        Restated from the phase naming convention rather than imported, so a
        kernel that pairs cells differently from what its phase name promises
        shows up as a disagreement.
        """
        if phase.startswith("horizontal"):
            parity = 0 if phase.endswith("even") else 1
            for y in range(self.height):
                for x in range(parity, self.width, 2):
                    yield (x, y), ((x + 1) % self.width, y)
        elif phase.startswith("vertical"):
            parity = 0 if phase.endswith("even") else 1
            for x in range(self.width):
                for y in range(parity, self.height, 2):
                    yield (x, y), (x, (y + 1) % self.height)
        else:
            raise RuleError(f"unknown transport phase {phase!r}")

    def transfer_limit(self, channel: str) -> int:
        return {
            "heat": self.max_heat_transfer,
            "water": self.max_water_transfer,
            "solute": self.max_solute_transfer,
            "vapor": self.max_vapor_transfer,
        }[channel]


def read_rules(spec: Mapping[str, Any]) -> WorldRules:
    """Extract the checkable rules from a world specification document."""
    if not isinstance(spec, Mapping):
        raise RuleError("world spec must be a mapping")
    law = spec.get("law") or {}
    causal = spec.get("causal_world") or {}
    kernel = causal.get("kernel") or {}

    blocked = set()
    for edge in spec.get("blocked_edges") or ():
        first = edge.get("first") or edge.get("a")
        second = edge.get("second") or edge.get("b")
        if first is None or second is None:
            raise RuleError(f"blocked edge needs two endpoints: {edge!r}")
        blocked.add(frozenset((tuple(first), tuple(second))))

    inputs: dict[tuple[int, int], int] = {}
    outputs: dict[tuple[int, int], int] = {}
    for boundary in spec.get("energy_boundaries") or ():
        point = (_integer(boundary.get("x"), "boundary x"),
                 _integer(boundary.get("y"), "boundary y"))
        given = _integer(boundary.get("input_per_tick", 0), "input_per_tick")
        taken = _integer(boundary.get("output_per_tick", 0), "output_per_tick")
        if given:
            inputs[point] = inputs.get(point, 0) + given
        if taken:
            outputs[point] = outputs.get(point, 0) + taken

    return WorldRules(
        format=str(spec.get("format")),
        width=_integer(kernel.get("width"), "kernel width"),
        height=_integer(kernel.get("height"), "kernel height"),
        boundary=str(kernel.get("boundary", "wrap")),
        solute_kinds=_integer(spec.get("solute_kinds", 0), "solute_kinds"),
        blocked_edges=frozenset(blocked),
        phase_order=tuple(law.get("phase_order") or ()),
        max_heat_transfer=_integer(law.get("max_heat_transfer", 0), "max_heat_transfer"),
        max_water_transfer=_integer(law.get("max_water_transfer", 0), "max_water_transfer"),
        max_solute_transfer=_integer(law.get("max_solute_transfer", 0), "max_solute_transfer"),
        max_vapor_transfer=_integer(law.get("max_vapor_transfer", 0), "max_vapor_transfer"),
        max_mineral_conversion=_integer(
            law.get("max_mineral_conversion", 0), "max_mineral_conversion"),
        max_water_phase_change=_integer(
            law.get("max_water_phase_change", 0), "max_water_phase_change"),
        mineral_solute_kind=_integer(law.get("mineral_solute_kind", 0), "mineral_solute_kind"),
        mineral_conversion_energy=_integer(
            law.get("mineral_conversion_energy", 0), "mineral_conversion_energy"),
        vaporization_energy=_integer(law.get("vaporization_energy", 0), "vaporization_energy"),
        dissolve_heat_at_least=_integer(
            law.get("dissolve_heat_at_least", 0), "dissolve_heat_at_least"),
        precipitate_heat_at_most=_integer(
            law.get("precipitate_heat_at_most", 0), "precipitate_heat_at_most"),
        evaporation_heat_at_least=_integer(
            law.get("evaporation_heat_at_least", 0), "evaporation_heat_at_least"),
        condensation_heat_at_most=_integer(
            law.get("condensation_heat_at_most", 0), "condensation_heat_at_most"),
        hot_solubility_per_water=_integer(
            law.get("hot_solubility_per_water", 0), "hot_solubility_per_water"),
        cold_solubility_per_water=_integer(
            law.get("cold_solubility_per_water", 0), "cold_solubility_per_water"),
        energy_inputs=inputs,
        energy_outputs=outputs,
    )
