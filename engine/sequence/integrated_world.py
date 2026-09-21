"""An ancestry-blind spatial world in which compartments are observed, not declared.

Every unit obeys the same port, affinity, movement, and energy laws.  A closed
bonded loop is reported as a compartment only by the observer helpers below;
the transition function never receives those reports and cannot reward them.
"""

from __future__ import annotations

from dataclasses import dataclass

from engine.living.events import RandomDraw, WorldEvent

from .local_dynamics import Encounter, PORT_COUNT
from .spatial_dynamics import (
    DIRECTIONS,
    MoveAttempt,
    SpatialState,
    apply_component_move,
    apply_spatial_encounter,
)
from .substrate import ChoiceSource


@dataclass(frozen=True, order=True)
class ObservedCompartment:
    """Observer-side description of one minimal closed material loop."""

    boundary_unit_ids: tuple[int, ...]
    enclosed_sites: tuple[tuple[int, int], ...]


@dataclass(frozen=True)
class IntegratedStepResult:
    state: SpatialState
    event: WorldEvent
    random_draw: RandomDraw


@dataclass(frozen=True)
class IntegratedFrame:
    index: int
    random_draw: RandomDraw
    event: WorldEvent
    state: SpatialState
    compartments: tuple[ObservedCompartment, ...]


@dataclass(frozen=True)
class IntegratedExperiment:
    initial_state: SpatialState
    frames: tuple[IntegratedFrame, ...]
    stop_reason: str

    @property
    def final_state(self) -> SpatialState:
        return self.frames[-1].state if self.frames else self.initial_state


def _canonical_cycle(path: tuple[int, ...]) -> tuple[int, ...]:
    variants: list[tuple[int, ...]] = []
    for sequence in (path, tuple(reversed(path))):
        for offset in range(len(sequence)):
            variants.append(sequence[offset:] + sequence[:offset])
    return min(variants)


def _simple_cycles(state: SpatialState) -> tuple[tuple[int, ...], ...]:
    adjacency = {unit.unit_id: set() for unit in state.local_state.units}
    for bond in state.local_state.bonds:
        adjacency[bond.left_id].add(bond.right_id)
        adjacency[bond.right_id].add(bond.left_id)
    found: set[tuple[int, ...]] = set()
    for start in sorted(adjacency):
        pending: list[tuple[int, tuple[int, ...]]] = [(start, (start,))]
        while pending:
            current, path = pending.pop()
            for neighbor in adjacency[current]:
                if neighbor == start and len(path) >= 4:
                    found.add(_canonical_cycle(path))
                elif neighbor not in path and neighbor >= start:
                    pending.append((neighbor, (*path, neighbor)))
    # Larger cycles containing a smaller loop are observer aliases, not new walls.
    ordered = sorted(found, key=lambda item: (len(item), item))
    minimal: list[tuple[int, ...]] = []
    for cycle in ordered:
        if not any(set(existing) < set(cycle) for existing in minimal):
            minimal.append(cycle)
    return tuple(minimal)


def _inside_polygon(point: tuple[int, int], polygon: tuple[tuple[int, int], ...]) -> bool:
    px, py = point[0] + 0.5, point[1] + 0.5
    inside = False
    previous = polygon[-1]
    for current in polygon:
        x1, y1 = previous
        x2, y2 = current
        if (y1 > py) != (y2 > py):
            crossing = (x2 - x1) * (py - y1) / (y2 - y1) + x1
            if px < crossing:
                inside = not inside
        previous = current
    return inside


def observe_compartments(state: SpatialState) -> tuple[ObservedCompartment, ...]:
    """Find closed bonded loops from physical state without feeding them back."""
    points = {item.unit_id: item.point for item in state.locations}
    occupied = set(points.values())
    observations: list[ObservedCompartment] = []
    for cycle in _simple_cycles(state):
        polygon = tuple(points[unit_id] for unit_id in cycle)
        twice_area = abs(sum(
            first[0] * second[1] - second[0] * first[1]
            for first, second in zip(polygon, (*polygon[1:], polygon[0]))
        ))
        if twice_area == 0:
            continue
        enclosed = tuple(
            (x, y)
            for y in range(state.height)
            for x in range(state.width)
            if (x, y) not in occupied and _inside_polygon((x, y), polygon)
        )
        if enclosed:
            observations.append(ObservedCompartment(tuple(sorted(cycle)), enclosed))
    return tuple(sorted(set(observations)))


def _encounters(state: SpatialState) -> tuple[Encounter, ...]:
    locations = {item.unit_id: item.point for item in state.locations}
    barriers = {item.edge for item in state.barriers}
    unit_ids = sorted(locations)
    pairs: list[tuple[int, int]] = []
    for index, left_id in enumerate(unit_ids):
        for right_id in unit_ids[index + 1 :]:
            left, right = locations[left_id], locations[right_id]
            if abs(left[0] - right[0]) + abs(left[1] - right[1]) != 1:
                continue
            edge = (left, right) if left < right else (right, left)
            if edge not in barriers:
                pairs.append((left_id, right_id))
    return tuple(
        Encounter(left_id, left_port, right_id, right_port)
        for left_id, right_id in pairs
        for left_port in range(PORT_COUNT)
        for right_port in range(PORT_COUNT)
    )


def step_integrated_world(state: SpatialState, chance: ChoiceSource) -> IntegratedStepResult:
    """Choose uniformly from real local impulses and adjacent port encounters."""
    moves = tuple(
        MoveAttempt(unit.unit_id, dx, dy)
        for unit in state.local_state.units
        for dx, dy in DIRECTIONS
    )
    encounters = _encounters(state)
    count = len(moves) + len(encounters)
    if not count:
        raise ValueError("an integrated world needs at least one matter unit")
    sample = chance.choice_index(count)
    selected = int(sample.value)
    if selected < len(moves):
        result = apply_component_move(state, moves[selected])
    else:
        result = apply_spatial_encounter(state, encounters[selected - len(moves)])
    before = observe_compartments(state)
    after = observe_compartments(result.state)
    event = WorldEvent.create(
        result.state.time,
        "integrated.transition",
        {
            "compartments_after": len(after),
            "compartments_before": len(before),
            "physical_event": result.event.canonical(),
            "state_hash": result.state.state_hash(),
        },
    )
    return IntegratedStepResult(result.state, event, sample.draw)


def run_integrated_world(
    initial_state: SpatialState,
    chance: ChoiceSource,
    event_limit: int,
) -> IntegratedExperiment:
    if isinstance(event_limit, bool) or not isinstance(event_limit, int) or event_limit < 0:
        raise ValueError("event_limit must be a non-negative integer")
    initial_units = tuple(initial_state.local_state.units)
    initial_total_energy = initial_state.local_state.total_energy
    state = initial_state
    frames: list[IntegratedFrame] = []
    for index in range(event_limit):
        result = step_integrated_world(state, chance)
        state = result.state
        if state.local_state.units != initial_units:
            raise AssertionError("matter was created, destroyed, or transmuted")
        if state.local_state.total_energy != initial_total_energy:
            raise AssertionError("bond and thermal energy ceased to balance")
        frames.append(
            IntegratedFrame(
                index,
                result.random_draw,
                result.event,
                state,
                observe_compartments(state),
            )
        )
    return IntegratedExperiment(initial_state, tuple(frames), "event_limit")
