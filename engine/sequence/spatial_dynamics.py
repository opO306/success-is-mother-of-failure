"""Minimal 2D locality and inert barriers for the common matter dynamics."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from engine.living.events import RandomDraw, WorldEvent

from .local_dynamics import Encounter, LocalDynamicsState, apply_encounter
from .substrate import ChoiceSource


DIRECTIONS: tuple[tuple[int, int], ...] = ((-1, 0), (0, -1), (0, 1), (1, 0))


@dataclass(frozen=True, order=True)
class GridLocation:
    unit_id: int
    x: int
    y: int

    def __post_init__(self) -> None:
        if any(isinstance(value, bool) or not isinstance(value, int) for value in (self.unit_id, self.x, self.y)):
            raise TypeError("grid location values must be integers")

    @property
    def point(self) -> tuple[int, int]:
        return self.x, self.y


@dataclass(frozen=True, order=True)
class GridBarrier:
    left_x: int
    left_y: int
    right_x: int
    right_y: int

    def __post_init__(self) -> None:
        values = (self.left_x, self.left_y, self.right_x, self.right_y)
        if any(isinstance(value, bool) or not isinstance(value, int) for value in values):
            raise TypeError("barrier coordinates must be integers")
        left = (self.left_x, self.left_y)
        right = (self.right_x, self.right_y)
        if left >= right or abs(self.left_x - self.right_x) + abs(self.left_y - self.right_y) != 1:
            raise ValueError("barrier endpoints must be adjacent and canonically ordered")

    @property
    def edge(self) -> tuple[tuple[int, int], tuple[int, int]]:
        return (self.left_x, self.left_y), (self.right_x, self.right_y)


@dataclass(frozen=True, order=True)
class MoveAttempt:
    unit_id: int
    dx: int
    dy: int

    def __post_init__(self) -> None:
        if isinstance(self.unit_id, bool) or not isinstance(self.unit_id, int):
            raise TypeError("unit_id must be an integer")
        if (self.dx, self.dy) not in DIRECTIONS:
            raise ValueError("movement must be one cardinal grid step")


@dataclass(frozen=True)
class SpatialState:
    local_state: LocalDynamicsState
    width: int
    height: int
    locations: tuple[GridLocation, ...]
    barriers: tuple[GridBarrier, ...] = ()

    def __post_init__(self) -> None:
        if any(isinstance(value, bool) or not isinstance(value, int) or value <= 0 for value in (self.width, self.height)):
            raise ValueError("grid dimensions must be positive integers")
        locations = tuple(sorted(self.locations))
        unit_ids = tuple(unit.unit_id for unit in self.local_state.units)
        if tuple(location.unit_id for location in locations) != unit_ids:
            raise ValueError("spatial state needs exactly one location per matter unit")
        if len({location.point for location in locations}) != len(locations):
            raise ValueError("two matter units cannot occupy the same grid site")
        if any(not (0 <= item.x < self.width and 0 <= item.y < self.height) for item in locations):
            raise ValueError("matter location lies outside the grid")
        barriers = tuple(sorted(self.barriers))
        if len(set(barriers)) != len(barriers):
            raise ValueError("barriers cannot be duplicated")
        for barrier in barriers:
            if any(
                not (0 <= x < self.width and 0 <= y < self.height)
                for x, y in barrier.edge
            ):
                raise ValueError("barrier lies outside the grid")
        location_map = {location.unit_id: location.point for location in locations}
        barrier_edges = {barrier.edge for barrier in barriers}
        for bond in self.local_state.bonds:
            endpoints = location_map[bond.left_id], location_map[bond.right_id]
            if abs(endpoints[0][0] - endpoints[1][0]) + abs(endpoints[0][1] - endpoints[1][1]) != 1:
                raise ValueError("a local bond cannot span nonadjacent grid sites")
            if tuple(sorted(endpoints)) in barrier_edges:
                raise ValueError("a local bond cannot pass through a barrier")
        object.__setattr__(self, "locations", locations)
        object.__setattr__(self, "barriers", barriers)

    @property
    def time(self) -> int:
        return self.local_state.time

    def canonical(self) -> dict[str, object]:
        return {
            "barriers": [
                {
                    "left": [item.left_x, item.left_y],
                    "right": [item.right_x, item.right_y],
                }
                for item in self.barriers
            ],
            "height": self.height,
            "local_state": self.local_state.canonical(),
            "locations": [
                {"unit_id": item.unit_id, "x": item.x, "y": item.y}
                for item in self.locations
            ],
            "width": self.width,
        }

    def state_hash(self) -> str:
        raw = json.dumps(self.canonical(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class SpatialStepResult:
    state: SpatialState
    event: WorldEvent
    random_draw: RandomDraw | None = None


def _edge(first: tuple[int, int], second: tuple[int, int]) -> tuple[tuple[int, int], tuple[int, int]]:
    return (first, second) if first < second else (second, first)


def apply_move(state: SpatialState, attempt: MoveAttempt) -> SpatialStepResult:
    location_map = {location.unit_id: location for location in state.locations}
    try:
        current = location_map[attempt.unit_id]
    except KeyError as exc:
        raise ValueError("movement refers to a missing matter unit") from exc
    target = (current.x + attempt.dx, current.y + attempt.dy)
    outcome: str
    next_locations = state.locations
    if not (0 <= target[0] < state.width and 0 <= target[1] < state.height):
        outcome = "world_boundary"
    elif _edge(current.point, target) in {barrier.edge for barrier in state.barriers}:
        outcome = "barrier_blocked"
    elif target in {location.point for location in state.locations}:
        outcome = "site_occupied"
    else:
        proposed = dict((unit_id, location.point) for unit_id, location in location_map.items())
        proposed[attempt.unit_id] = target
        attached = [
            bond.right_id if bond.left_id == attempt.unit_id else bond.left_id
            for bond in state.local_state.bonds
            if attempt.unit_id in (bond.left_id, bond.right_id)
        ]
        if any(
            abs(target[0] - proposed[other_id][0]) + abs(target[1] - proposed[other_id][1]) != 1
            for other_id in attached
        ):
            outcome = "bond_constraint"
        else:
            next_locations = tuple(
                GridLocation(item.unit_id, target[0], target[1]) if item.unit_id == attempt.unit_id else item
                for item in state.locations
            )
            outcome = "moved"
    next_local = LocalDynamicsState(
        state.local_state.units,
        state.local_state.thermal_energy,
        state.local_state.bonds,
        state.local_state.time + 1,
    )
    next_state = SpatialState(next_local, state.width, state.height, next_locations, state.barriers)
    event = WorldEvent.create(
        next_state.time,
        "spatial.move",
        {
            "dx": attempt.dx,
            "dy": attempt.dy,
            "from": [current.x, current.y],
            "outcome": outcome,
            "state_hash": next_state.state_hash(),
            "to": list(target),
            "unit_id": attempt.unit_id,
        },
    )
    return SpatialStepResult(next_state, event)


def _bonded_component_ids(state: SpatialState, start_id: int) -> tuple[int, ...]:
    unit_ids = {unit.unit_id for unit in state.local_state.units}
    if start_id not in unit_ids:
        raise ValueError("component movement refers to a missing matter unit")
    adjacency = {unit_id: set() for unit_id in unit_ids}
    for bond in state.local_state.bonds:
        adjacency[bond.left_id].add(bond.right_id)
        adjacency[bond.right_id].add(bond.left_id)
    reached = {start_id}
    pending = [start_id]
    while pending:
        unit_id = pending.pop()
        unseen = adjacency[unit_id] - reached
        reached.update(unseen)
        pending.extend(unseen)
    return tuple(sorted(reached))


def apply_component_move(state: SpatialState, attempt: MoveAttempt) -> SpatialStepResult:
    """Translate the entire currently bonded component hit by one local impulse."""
    member_ids = _bonded_component_ids(state, attempt.unit_id)
    location_map = {location.unit_id: location for location in state.locations}
    targets = {
        unit_id: (
            location_map[unit_id].x + attempt.dx,
            location_map[unit_id].y + attempt.dy,
        )
        for unit_id in member_ids
    }
    stationary_sites = {
        location.point for location in state.locations if location.unit_id not in member_ids
    }
    barrier_edges = {barrier.edge for barrier in state.barriers}
    if any(
        not (0 <= target[0] < state.width and 0 <= target[1] < state.height)
        for target in targets.values()
    ):
        outcome = "world_boundary"
    elif any(
        _edge(location_map[unit_id].point, targets[unit_id]) in barrier_edges
        for unit_id in member_ids
    ):
        outcome = "barrier_blocked"
    elif any(target in stationary_sites for target in targets.values()):
        outcome = "site_occupied"
    else:
        outcome = "moved"
    if outcome == "moved":
        next_locations = tuple(
            GridLocation(item.unit_id, *targets[item.unit_id]) if item.unit_id in targets else item
            for item in state.locations
        )
    else:
        next_locations = state.locations
    next_local = LocalDynamicsState(
        state.local_state.units,
        state.local_state.thermal_energy,
        state.local_state.bonds,
        state.local_state.time + 1,
    )
    next_state = SpatialState(next_local, state.width, state.height, next_locations, state.barriers)
    event = WorldEvent.create(
        next_state.time,
        "spatial.component_move",
        {
            "dx": attempt.dx,
            "dy": attempt.dy,
            "member_ids": list(member_ids),
            "outcome": outcome,
            "state_hash": next_state.state_hash(),
            "trigger_unit_id": attempt.unit_id,
        },
    )
    return SpatialStepResult(next_state, event)


def step_spatial_movement(state: SpatialState, chance: ChoiceSource) -> SpatialStepResult:
    attempts = tuple(
        MoveAttempt(unit.unit_id, dx, dy)
        for unit in state.local_state.units
        for dx, dy in DIRECTIONS
    )
    sample = chance.choice_index(len(attempts))
    result = apply_move(state, attempts[int(sample.value)])
    return SpatialStepResult(result.state, result.event, sample.draw)


def step_spatial_component_movement(state: SpatialState, chance: ChoiceSource) -> SpatialStepResult:
    """Sample local unit impulses uniformly, translating their whole bonded component."""
    attempts = tuple(
        MoveAttempt(unit.unit_id, dx, dy)
        for unit in state.local_state.units
        for dx, dy in DIRECTIONS
    )
    sample = chance.choice_index(len(attempts))
    result = apply_component_move(state, attempts[int(sample.value)])
    return SpatialStepResult(result.state, result.event, sample.draw)


def apply_spatial_encounter(state: SpatialState, encounter: Encounter) -> SpatialStepResult:
    """Apply the common bond law only to physically adjacent, unseparated units."""
    location_map = {location.unit_id: location.point for location in state.locations}
    try:
        endpoints = location_map[encounter.left_id], location_map[encounter.right_id]
    except KeyError as exc:
        raise ValueError("encounter refers to a missing placed matter unit") from exc
    distance = abs(endpoints[0][0] - endpoints[1][0]) + abs(endpoints[0][1] - endpoints[1][1])
    barrier_edges = {barrier.edge for barrier in state.barriers}
    if distance != 1:
        outcome = "not_adjacent"
        next_local = LocalDynamicsState(
            state.local_state.units,
            state.local_state.thermal_energy,
            state.local_state.bonds,
            state.local_state.time + 1,
        )
        strength = 0
    elif _edge(*endpoints) in barrier_edges:
        outcome = "barrier_separated"
        next_local = LocalDynamicsState(
            state.local_state.units,
            state.local_state.thermal_energy,
            state.local_state.bonds,
            state.local_state.time + 1,
        )
        strength = 0
    else:
        local_result = apply_encounter(state.local_state, encounter)
        next_local = local_result.state
        payload = local_result.event.payload()
        outcome = str(payload["outcome"])
        strength = int(payload["strength"])
    next_state = SpatialState(next_local, state.width, state.height, state.locations, state.barriers)
    event = WorldEvent.create(
        next_state.time,
        "spatial.encounter",
        {
            "left_id": encounter.left_id,
            "left_port": encounter.left_port,
            "outcome": outcome,
            "right_id": encounter.right_id,
            "right_port": encounter.right_port,
            "state_hash": next_state.state_hash(),
            "strength": strength,
        },
    )
    return SpatialStepResult(next_state, event)


def unit_ids_in_box(
    state: SpatialState,
    minimum_x: int,
    minimum_y: int,
    maximum_x: int,
    maximum_y: int,
) -> tuple[int, ...]:
    """Observer-only region query; it never changes the world."""
    if not (0 <= minimum_x <= maximum_x < state.width and 0 <= minimum_y <= maximum_y < state.height):
        raise ValueError("observation box lies outside the grid")
    return tuple(
        item.unit_id
        for item in state.locations
        if minimum_x <= item.x <= maximum_x and minimum_y <= item.y <= maximum_y
    )
