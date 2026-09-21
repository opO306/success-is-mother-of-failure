"""Topological compartments observed from bonded spatial sequence matter.

Nothing here declares life or feeds an observer label back into physics.  A
compartment exists only while a physically bonded material wall disconnects
grid positions from the outside.  Opening the wall removes the observation.
"""
from __future__ import annotations

from dataclasses import dataclass

from .spatial_dynamics import DIRECTIONS
from .spatial_sequence import SpatialSequenceState


Site = tuple[int, int]
Point = tuple[int, int]


@dataclass(frozen=True, order=True)
class ObservedSequenceCompartment:
    boundary_sites: tuple[Site, ...]
    interior_points: tuple[Point, ...]
    interior_field_energy: int
    interior_medium_amount: int = 0
    interior_medium_energy: int = 0


def _bond_graph(state: SpatialSequenceState) -> dict[Site, set[Site]]:
    graph = {item.site: set() for item in state.locations}
    for strand in state.sequence.strands:
        for index in range(len(strand.symbols) - 1):
            left = strand.strand_id, index
            right = strand.strand_id, index + 1
            graph[left].add(right)
            graph[right].add(left)
        if strand.cyclic:
            left = strand.strand_id, len(strand.symbols) - 1
            right = strand.strand_id, 0
            graph[left].add(right)
            graph[right].add(left)
    for contact in state.sequence.contacts:
        for offset in range(contact.length):
            left = contact.left_id, contact.left_start + offset
            right = contact.right_id, contact.right_start + offset
            graph[left].add(right)
            graph[right].add(left)
    return graph


def _components(graph: dict[Site, set[Site]]) -> tuple[frozenset[Site], ...]:
    unseen = set(graph)
    found = []
    while unseen:
        start = min(unseen)
        reached = {start}
        pending = [start]
        while pending:
            current = pending.pop()
            fresh = graph[current] - reached
            reached.update(fresh)
            pending.extend(fresh)
        unseen.difference_update(reached)
        found.append(frozenset(reached))
    return tuple(sorted(found, key=lambda item: (min(item), len(item))))


def _cycle_core(component: frozenset[Site], graph: dict[Site, set[Site]]) -> frozenset[Site]:
    """Remove bonded tails; only sites supported in at least two directions remain."""
    core = set(component)
    changed = True
    while changed:
        removable = {site for site in core if len(graph[site] & core) < 2}
        changed = bool(removable)
        core.difference_update(removable)
    return frozenset(core)


def _neighbors(point: Point, width: int, height: int) -> tuple[Point, ...]:
    x, y = point
    return tuple(
        (x + dx, y + dy)
        for dx, dy in DIRECTIONS
        if 0 <= x + dx < width and 0 <= y + dy < height
    )


def _enclosed_regions(wall: set[Point], width: int, height: int) -> tuple[frozenset[Point], ...]:
    passable = {(x, y) for y in range(height) for x in range(width)} - wall
    exterior_starts = {
        point
        for point in passable
        if point[0] in {0, width - 1} or point[1] in {0, height - 1}
    }
    exterior = set(exterior_starts)
    pending = list(exterior_starts)
    while pending:
        current = pending.pop()
        fresh = set(_neighbors(current, width, height)) & passable - exterior
        exterior.update(fresh)
        pending.extend(fresh)
    unseen = passable - exterior
    regions = []
    while unseen:
        start = min(unseen)
        reached = {start}
        pending = [start]
        while pending:
            current = pending.pop()
            fresh = set(_neighbors(current, width, height)) & unseen - reached
            reached.update(fresh)
            pending.extend(fresh)
        unseen.difference_update(reached)
        regions.append(frozenset(reached))
    return tuple(sorted(regions, key=lambda item: (min(item), len(item))))


def observe_spatial_compartments(
    state: SpatialSequenceState,
) -> tuple[ObservedSequenceCompartment, ...]:
    """Report bonded walls and their actual enclosed energy without changing state."""
    graph = _bond_graph(state)
    point_for = {item.site: item.point for item in state.locations}
    energy_at = {cell.point: cell.amount for cell in state.field_energy}
    medium_at = {cell.point: cell for cell in state.medium}
    observations = []
    for component in _components(graph):
        core = _cycle_core(component, graph)
        if not core:
            continue
        wall = {point_for[site] for site in core}
        for interior in _enclosed_regions(wall, state.width, state.height):
            boundary = set(core)
            if not boundary:
                continue
            # A geometrically closed arrangement is not a material wall unless
            # every wall site is bonded onward in both directions around it.
            if any(len(graph[site] & boundary) < 2 for site in boundary):
                continue
            observations.append(ObservedSequenceCompartment(
                tuple(sorted(boundary)),
                tuple(sorted(interior)),
                sum(energy_at.get(point, 0) for point in interior),
                sum(medium_at[point].amount for point in interior if point in medium_at),
                sum(medium_at[point].energy for point in interior if point in medium_at),
            ))
    return tuple(sorted(set(observations)))
