"""Universal local collision dynamics without behavior-specific event weights."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from itertools import combinations

from engine.living.events import RandomDraw, WorldEvent

from .substrate import ChoiceSource, pair_score


PORT_COUNT = 4


def _port(value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value < PORT_COUNT:
        raise ValueError("port must be an integer from zero through three")
    return value


@dataclass(frozen=True, order=True)
class MatterUnit:
    unit_id: int
    symbol: int

    def __post_init__(self) -> None:
        if isinstance(self.unit_id, bool) or not isinstance(self.unit_id, int):
            raise TypeError("unit_id must be an integer")
        if isinstance(self.symbol, bool) or not isinstance(self.symbol, int) or not 0 <= self.symbol < 4:
            raise ValueError("unit symbol must be an integer from zero through three")


@dataclass(frozen=True, order=True)
class PortBond:
    left_id: int
    left_port: int
    right_id: int
    right_port: int
    strength: int

    def __post_init__(self) -> None:
        left = (self.left_id, _port(self.left_port))
        right = (self.right_id, _port(self.right_port))
        if left >= right:
            raise ValueError("bond endpoints must be distinct and canonically ordered")
        if self.left_id == self.right_id:
            raise ValueError("a unit cannot collide with itself in the well-mixed v1 world")
        if isinstance(self.strength, bool) or not isinstance(self.strength, int) or self.strength <= 0:
            raise ValueError("bond strength must be a positive integer")


@dataclass(frozen=True, order=True)
class Encounter:
    left_id: int
    left_port: int
    right_id: int
    right_port: int

    def __post_init__(self) -> None:
        left = (self.left_id, _port(self.left_port))
        right = (self.right_id, _port(self.right_port))
        if left >= right or self.left_id == self.right_id:
            raise ValueError("encounter endpoints must be on distinct units in canonical order")


@dataclass(frozen=True)
class LocalDynamicsState:
    units: tuple[MatterUnit, ...]
    thermal_energy: int
    bonds: tuple[PortBond, ...] = ()
    time: int = 0

    def __post_init__(self) -> None:
        units = tuple(sorted(self.units))
        if len({unit.unit_id for unit in units}) != len(units):
            raise ValueError("unit ids must be unique")
        if isinstance(self.thermal_energy, bool) or not isinstance(self.thermal_energy, int):
            raise TypeError("thermal_energy must be an integer")
        if self.thermal_energy < 0:
            raise ValueError("thermal_energy cannot be negative")
        if isinstance(self.time, bool) or not isinstance(self.time, int) or self.time < 0:
            raise ValueError("time must be a non-negative integer")
        unit_map = {unit.unit_id: unit for unit in units}
        occupied: set[tuple[int, int]] = set()
        bonds = tuple(sorted(self.bonds))
        for bond in bonds:
            try:
                left = unit_map[bond.left_id]
                right = unit_map[bond.right_id]
            except KeyError as exc:
                raise ValueError("bond refers to a missing matter unit") from exc
            if pair_score(left.symbol, right.symbol) != bond.strength:
                raise ValueError("bond strength must equal the common local affinity")
            endpoints = ((bond.left_id, bond.left_port), (bond.right_id, bond.right_port))
            if any(endpoint in occupied for endpoint in endpoints):
                raise ValueError("each port can hold at most one bond")
            occupied.update(endpoints)
        object.__setattr__(self, "units", units)
        object.__setattr__(self, "bonds", bonds)

    @property
    def total_energy(self) -> int:
        return self.thermal_energy - sum(bond.strength for bond in self.bonds)

    def canonical(self) -> dict[str, object]:
        return {
            "bonds": [
                {
                    "left_id": bond.left_id,
                    "left_port": bond.left_port,
                    "right_id": bond.right_id,
                    "right_port": bond.right_port,
                    "strength": bond.strength,
                }
                for bond in self.bonds
            ],
            "thermal_energy": self.thermal_energy,
            "time": self.time,
            "units": [{"symbol": unit.symbol, "unit_id": unit.unit_id} for unit in self.units],
        }

    def state_hash(self) -> str:
        raw = json.dumps(self.canonical(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class LocalStepResult:
    state: LocalDynamicsState
    event: WorldEvent | None
    random_draw: RandomDraw | None = None


@dataclass(frozen=True)
class LocalExperimentFrame:
    index: int
    random_draw: RandomDraw
    event: WorldEvent
    state: LocalDynamicsState


@dataclass(frozen=True)
class LocalExperiment:
    initial_state: LocalDynamicsState
    frames: tuple[LocalExperimentFrame, ...]
    stop_reason: str

    @property
    def final_state(self) -> LocalDynamicsState:
        return self.frames[-1].state if self.frames else self.initial_state


def encounter_pairs(state: LocalDynamicsState) -> tuple[Encounter, ...]:
    endpoints = tuple((unit.unit_id, port) for unit in state.units for port in range(PORT_COUNT))
    return tuple(
        Encounter(left_id, left_port, right_id, right_port)
        for (left_id, left_port), (right_id, right_port) in combinations(endpoints, 2)
        if left_id != right_id
    )


def apply_encounter(state: LocalDynamicsState, encounter: Encounter) -> LocalStepResult:
    unit_map = {unit.unit_id: unit for unit in state.units}
    if encounter.left_id not in unit_map or encounter.right_id not in unit_map:
        raise ValueError("encounter refers to a missing matter unit")
    direct = next(
        (
            bond
            for bond in state.bonds
            if (bond.left_id, bond.left_port, bond.right_id, bond.right_port)
            == (encounter.left_id, encounter.left_port, encounter.right_id, encounter.right_port)
        ),
        None,
    )
    outcome: str
    strength = 0
    thermal = state.thermal_energy
    bonds = state.bonds
    if direct is not None:
        strength = direct.strength
        if thermal >= strength:
            bonds = tuple(bond for bond in state.bonds if bond != direct)
            thermal -= strength
            outcome = "bond_broken"
        else:
            outcome = "bond_held"
    else:
        occupied = {
            (bond.left_id, bond.left_port) for bond in state.bonds
        } | {
            (bond.right_id, bond.right_port) for bond in state.bonds
        }
        endpoints = ((encounter.left_id, encounter.left_port), (encounter.right_id, encounter.right_port))
        if any(endpoint in occupied for endpoint in endpoints):
            outcome = "ports_occupied"
        else:
            strength = pair_score(unit_map[encounter.left_id].symbol, unit_map[encounter.right_id].symbol)
            if strength <= 0:
                strength = 0
                outcome = "inert"
            else:
                bond = PortBond(
                    encounter.left_id,
                    encounter.left_port,
                    encounter.right_id,
                    encounter.right_port,
                    strength,
                )
                bonds = tuple(sorted((*state.bonds, bond)))
                thermal += strength
                outcome = "bond_formed"
    next_state = LocalDynamicsState(state.units, thermal, bonds, state.time + 1)
    event = WorldEvent.create(
        next_state.time,
        "local.encounter",
        {
            "left_id": encounter.left_id,
            "left_port": encounter.left_port,
            "outcome": outcome,
            "right_id": encounter.right_id,
            "right_port": encounter.right_port,
            "state_hash": next_state.state_hash(),
            "strength": strength,
            "thermal_after": thermal,
        },
    )
    return LocalStepResult(next_state, event)


def step_local(state: LocalDynamicsState, chance: ChoiceSource) -> LocalStepResult:
    encounters = encounter_pairs(state)
    if not encounters:
        return LocalStepResult(state, None, None)
    sample = chance.choice_index(len(encounters))
    result = apply_encounter(state, encounters[int(sample.value)])
    return LocalStepResult(result.state, result.event, sample.draw)


def run_local_experiment(
    initial_state: LocalDynamicsState,
    chance: ChoiceSource,
    max_encounters: int,
) -> LocalExperiment:
    if isinstance(max_encounters, bool) or not isinstance(max_encounters, int) or max_encounters < 0:
        raise ValueError("max_encounters must be a non-negative integer")
    state = initial_state
    frames: list[LocalExperimentFrame] = []
    for index in range(max_encounters):
        result = step_local(state, chance)
        if result.event is None or result.random_draw is None:
            return LocalExperiment(initial_state, tuple(frames), "quiescent")
        state = result.state
        frames.append(LocalExperimentFrame(index, result.random_draw, result.event, state))
    return LocalExperiment(initial_state, tuple(frames), "encounter_limit")
