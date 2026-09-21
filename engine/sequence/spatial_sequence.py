"""One physical state joining evolvable sequences to explicit 2D locality."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from engine.living.events import RandomDraw, WorldEvent

from .spatial_dynamics import DIRECTIONS
from .substrate import (
    BACKBONE_COST,
    BackboneLigation,
    ChoiceSource,
    Contact,
    EventCandidate,
    SequenceState,
    StepResult,
    apply_candidate,
    backbone_ligation_candidates,
    candidate_sort_key,
    event_candidates,
)


SPATIAL_ROTATION_COST = 1


@dataclass(frozen=True, order=True)
class SequenceSiteLocation:
    strand_id: int
    site_index: int
    x: int
    y: int

    @property
    def site(self) -> tuple[int, int]:
        return self.strand_id, self.site_index

    @property
    def point(self) -> tuple[int, int]:
        return self.x, self.y


@dataclass(frozen=True, order=True)
class EnergyCell:
    x: int
    y: int
    amount: int

    def __post_init__(self) -> None:
        if any(isinstance(value, bool) or not isinstance(value, int) for value in (self.x, self.y, self.amount)):
            raise TypeError("energy-cell coordinates and amount must be integers")
        if self.amount <= 0:
            raise ValueError("stored field energy must be positive")

    @property
    def point(self) -> tuple[int, int]:
        return self.x, self.y


@dataclass(frozen=True, order=True)
class EnergySource:
    x: int
    y: int
    amount: int

    def __post_init__(self) -> None:
        if any(isinstance(value, bool) or not isinstance(value, int) for value in (self.x, self.y, self.amount)):
            raise TypeError("energy-source coordinates and amount must be integers")
        if self.amount == 0:
            raise ValueError("an energy source or sink must exchange a non-zero amount")

    @property
    def point(self) -> tuple[int, int]:
        return self.x, self.y


@dataclass(frozen=True, order=True)
class MediumCell:
    """Conserved mobile medium carrying an integer amount of energy."""

    x: int
    y: int
    amount: int
    energy: int = 0

    def __post_init__(self) -> None:
        values = (self.x, self.y, self.amount, self.energy)
        if any(isinstance(value, bool) or not isinstance(value, int) for value in values):
            raise TypeError("medium coordinates, amount, and energy must be integers")
        if self.amount <= 0 or self.energy < 0:
            raise ValueError("medium amount must be positive and energy non-negative")

    @property
    def point(self) -> tuple[int, int]:
        return self.x, self.y


def _distance(first: tuple[int, int], second: tuple[int, int]) -> int:
    return abs(first[0] - second[0]) + abs(first[1] - second[1])


@dataclass(frozen=True)
class SpatialSequenceState:
    sequence: SequenceState
    width: int
    height: int
    locations: tuple[SequenceSiteLocation, ...]
    external_energy_exchange: int = 0
    field_energy: tuple[EnergyCell, ...] = ()
    medium: tuple[MediumCell, ...] = ()

    def __post_init__(self) -> None:
        if any(isinstance(value, bool) or not isinstance(value, int) or value <= 0 for value in (self.width, self.height)):
            raise ValueError("grid dimensions must be positive integers")
        locations = tuple(sorted(self.locations))
        expected = tuple(
            (strand.strand_id, index)
            for strand in self.sequence.strands
            for index in range(len(strand.symbols))
        )
        if tuple(item.site for item in locations) != expected:
            raise ValueError("every sequence site needs exactly one spatial location")
        if len({item.point for item in locations}) != len(locations):
            raise ValueError("two sequence sites cannot occupy one grid point")
        if any(not (0 <= item.x < self.width and 0 <= item.y < self.height) for item in locations):
            raise ValueError("sequence site lies outside the grid")
        points = {item.site: item.point for item in locations}
        for strand in self.sequence.strands:
            for index in range(len(strand.symbols) - 1):
                if _distance(points[(strand.strand_id, index)], points[(strand.strand_id, index + 1)]) != 1:
                    raise ValueError("a backbone link must join adjacent grid sites")
            if strand.cyclic and _distance(
                points[(strand.strand_id, len(strand.symbols) - 1)],
                points[(strand.strand_id, 0)],
            ) != 1:
                raise ValueError("a cyclic backbone must close between adjacent grid sites")
        for contact in self.sequence.contacts:
            for offset in range(contact.length):
                left = points[(contact.left_id, contact.left_start + offset)]
                right = points[(contact.right_id, contact.right_start + offset)]
                if _distance(left, right) != 1:
                    raise ValueError("a side contact must join adjacent grid sites")
        object.__setattr__(self, "locations", locations)
        if isinstance(self.external_energy_exchange, bool) or not isinstance(self.external_energy_exchange, int):
            raise TypeError("external_energy_exchange must be an integer")
        field = tuple(sorted(self.field_energy))
        if len({cell.point for cell in field}) != len(field):
            raise ValueError("a grid point can have only one field-energy cell")
        if any(not (0 <= cell.x < self.width and 0 <= cell.y < self.height) for cell in field):
            raise ValueError("field energy lies outside the grid")
        object.__setattr__(self, "field_energy", field)
        medium = tuple(sorted(self.medium))
        if len({cell.point for cell in medium}) != len(medium):
            raise ValueError("a grid point can have only one medium cell")
        occupied_points = {item.point for item in locations}
        if any(cell.point in occupied_points for cell in medium):
            raise ValueError("medium and sequence matter cannot occupy the same grid point")
        if any(not (0 <= cell.x < self.width and 0 <= cell.y < self.height) for cell in medium):
            raise ValueError("medium lies outside the grid")
        object.__setattr__(self, "medium", medium)

    @property
    def time(self) -> int:
        return self.sequence.time

    def canonical(self) -> dict[str, object]:
        payload = {
            "height": self.height,
            "locations": [
                {"site_index": item.site_index, "strand_id": item.strand_id, "x": item.x, "y": item.y}
                for item in self.locations
            ],
            "sequence": self.sequence.canonical(),
            "width": self.width,
        }
        if self.external_energy_exchange:
            payload["external_energy_exchange"] = self.external_energy_exchange
        if self.field_energy:
            payload["field_energy"] = [
                {"amount": cell.amount, "x": cell.x, "y": cell.y}
                for cell in self.field_energy
            ]
        if self.medium:
            payload["medium"] = [
                {"amount": cell.amount, "energy": cell.energy, "x": cell.x, "y": cell.y}
                for cell in self.medium
            ]
        return payload

    def state_hash(self) -> str:
        raw = json.dumps(self.canonical(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @property
    def reservoir_adjusted_energy(self) -> int:
        """Energy conserved when the external reservoir is included in the ledger."""
        return (
            self.sequence.total_energy
            + sum(cell.amount for cell in self.field_energy)
            + sum(cell.energy for cell in self.medium)
            - self.external_energy_exchange
        )


@dataclass(frozen=True)
class SpatialSequenceStepResult:
    state: SpatialSequenceState
    event: WorldEvent | None
    random_draw: RandomDraw | None = None


@dataclass(frozen=True, order=True)
class SpatialRotationCandidate:
    """A rigid quarter-turn of one side of a backbone hinge."""

    pivot_site: tuple[int, int]
    moving_site: tuple[int, int]
    quarter_turn: int
    member_sites: tuple[tuple[int, int], ...]
    targets: tuple[tuple[tuple[int, int], tuple[int, int]], ...]


@dataclass(frozen=True, order=True)
class SpatialFlexCandidate:
    """A one-site corner flip that preserves every existing physical bond."""

    site: tuple[int, int]
    source: tuple[int, int]
    target: tuple[int, int]


@dataclass(frozen=True)
class PeriodicEnergyFlow:
    """A predictable reservoir exchange after each fixed number of world events."""

    interval: int
    amount: int

    def __post_init__(self) -> None:
        if isinstance(self.interval, bool) or not isinstance(self.interval, int) or self.interval <= 0:
            raise ValueError("energy-flow interval must be a positive integer")
        if isinstance(self.amount, bool) or not isinstance(self.amount, int) or self.amount == 0:
            raise ValueError("energy-flow amount must be a non-zero integer")


@dataclass(frozen=True)
class SpatialEnergyLaw:
    """Predictable placement, conservative spreading, and contact absorption."""

    interval: int
    sources: tuple[EnergySource, ...]
    diffusion_divisor: int = 4
    absorption_per_site: int = 1

    def __post_init__(self) -> None:
        if isinstance(self.interval, bool) or not isinstance(self.interval, int) or self.interval <= 0:
            raise ValueError("spatial-energy interval must be a positive integer")
        if not self.sources:
            raise ValueError("a spatial-energy law needs at least one source or sink")
        if (
            isinstance(self.diffusion_divisor, bool)
            or not isinstance(self.diffusion_divisor, int)
            or self.diffusion_divisor < 4
        ):
            raise ValueError("diffusion_divisor must be an integer of at least four")
        if (
            isinstance(self.absorption_per_site, bool)
            or not isinstance(self.absorption_per_site, int)
            or self.absorption_per_site < 0
        ):
            raise ValueError("absorption_per_site must be a non-negative integer")


@dataclass(frozen=True)
class MediumTransportLaw:
    """Cadence and rates for conserved medium flow and collision transfer."""

    interval: int
    diffusion_divisor: int = 8
    absorption_per_site: int = 1
    field_coupling_per_cell: int = 1

    def __post_init__(self) -> None:
        if isinstance(self.interval, bool) or not isinstance(self.interval, int) or self.interval <= 0:
            raise ValueError("medium interval must be a positive integer")
        if (
            isinstance(self.diffusion_divisor, bool)
            or not isinstance(self.diffusion_divisor, int)
            or self.diffusion_divisor < 4
        ):
            raise ValueError("medium diffusion_divisor must be an integer of at least four")
        if (
            isinstance(self.absorption_per_site, bool)
            or not isinstance(self.absorption_per_site, int)
            or self.absorption_per_site < 0
        ):
            raise ValueError("medium absorption_per_site must be a non-negative integer")
        if (
            isinstance(self.field_coupling_per_cell, bool)
            or not isinstance(self.field_coupling_per_cell, int)
            or self.field_coupling_per_cell < 0
        ):
            raise ValueError("field_coupling_per_cell must be a non-negative integer")


def _contact_is_local(contact: Contact, points: dict[tuple[int, int], tuple[int, int]]) -> bool:
    return all(
        _distance(
            points[(contact.left_id, contact.left_start + offset)],
            points[(contact.right_id, contact.right_start + offset)],
        ) == 1
        for offset in range(contact.length)
    )


def _contact_start(contact: Contact, strand_id: int) -> int:
    return contact.left_start if contact.left_id == strand_id else contact.right_start


def _other_strand(contact: Contact, strand_id: int) -> int:
    return contact.right_id if contact.left_id == strand_id else contact.left_id


def _join_fragments(candidate: EventCandidate) -> tuple[int, int]:
    first, second = candidate.related_contacts
    shared = {first.left_id, first.right_id} & {second.left_id, second.right_id}
    template_id = next(
        strand_id for strand_id in sorted(shared)
        if _contact_start(first, strand_id) != _contact_start(second, strand_id)
    )
    if _contact_start(first, template_id) < _contact_start(second, template_id):
        return _other_strand(first, template_id), _other_strand(second, template_id)
    return _other_strand(second, template_id), _other_strand(first, template_id)


def spatial_event_candidates(state: SpatialSequenceState) -> tuple[EventCandidate, ...]:
    points = {item.site: item.point for item in state.locations}
    lengths = {strand.strand_id: len(strand.symbols) for strand in state.sequence.strands}
    available = []
    for candidate in event_candidates(state.sequence, include_ligation=False):
        if candidate.kind in {"bind", "fold"} and not _contact_is_local(candidate.contact, points):
            continue
        if candidate.kind == "join":
            left_id, right_id = _join_fragments(candidate)
            if _distance(points[(left_id, lengths[left_id] - 1)], points[(right_id, 0)]) != 1:
                continue
        if candidate.kind == "cyclize":
            strand_id = candidate.cyclization.strand_id
            if _distance(points[(strand_id, lengths[strand_id] - 1)], points[(strand_id, 0)]) != 1:
                continue
        available.append(candidate)
    starts_at = {
        points[(strand.strand_id, 0)]: strand.strand_id
        for strand in state.sequence.strands
        if not strand.cyclic
    }
    local_pairs = []
    if state.sequence.thermal_energy >= BACKBONE_COST:
        for strand in state.sequence.strands:
            if strand.cyclic:
                continue
            x, y = points[(strand.strand_id, lengths[strand.strand_id] - 1)]
            for dx, dy in DIRECTIONS:
                right_id = starts_at.get((x + dx, y + dy))
                if right_id is not None and right_id != strand.strand_id:
                    local_pairs.append((strand.strand_id, right_id))
    available.extend(backbone_ligation_candidates(state.sequence, local_pairs))
    return tuple(sorted(available, key=candidate_sort_key))


def _remap_locations(
    before: SpatialSequenceState,
    candidate: EventCandidate,
    result: StepResult,
) -> tuple[SequenceSiteLocation, ...]:
    if candidate.kind not in {"cleave", "cycle_open", "join", "ligate"}:
        return before.locations
    payload = result.event.payload()
    if candidate.kind == "cycle_open":
        strand_id = int(payload["strand_id"])
        old_to_new = {old: new for new, old in enumerate(payload["index_order"])}
        return tuple(
            SequenceSiteLocation(item.strand_id, old_to_new[item.site_index], item.x, item.y)
            if item.strand_id == strand_id else item
            for item in before.locations
        )
    if candidate.kind == "cleave":
        parent_id = int(payload["parent_strand_id"])
        cut_index = int(payload["cut_index"])
        left_id, right_id = (int(value) for value in payload["child_strand_ids"])
        remapped = []
        for item in before.locations:
            if item.strand_id != parent_id:
                remapped.append(item)
            elif item.site_index < cut_index:
                remapped.append(SequenceSiteLocation(left_id, item.site_index, item.x, item.y))
            else:
                remapped.append(SequenceSiteLocation(right_id, item.site_index - cut_index, item.x, item.y))
        return tuple(remapped)
    if candidate.kind == "join":
        left_id, right_id = _join_fragments(candidate)
    else:
        left_id, right_id = candidate.ligation.left_id, candidate.ligation.right_id
    new_id = int(payload["new_strand_id"])
    left_length = next(len(item.symbols) for item in before.sequence.strands if item.strand_id == left_id)
    remapped = []
    for item in before.locations:
        if item.strand_id == left_id:
            remapped.append(SequenceSiteLocation(new_id, item.site_index, item.x, item.y))
        elif item.strand_id == right_id:
            remapped.append(SequenceSiteLocation(new_id, left_length + item.site_index, item.x, item.y))
        else:
            remapped.append(item)
    return tuple(remapped)


def apply_spatial_sequence_candidate(
    state: SpatialSequenceState,
    candidate: EventCandidate,
) -> SpatialSequenceStepResult:
    if candidate not in spatial_event_candidates(state):
        raise ValueError("sequence event is not spatially available")
    result = apply_candidate(state.sequence, candidate)
    locations = _remap_locations(state, candidate, result)
    next_state = SpatialSequenceState(
        result.state,
        state.width,
        state.height,
        locations,
        state.external_energy_exchange,
        state.field_energy,
        state.medium,
    )
    payload = result.event.payload()
    event = WorldEvent.create(
        next_state.time,
        result.event.event_type,
        {**payload, "spatial_state_hash": next_state.state_hash()},
    )
    return SpatialSequenceStepResult(next_state, event)


def _connected_sites(state: SpatialSequenceState, start: tuple[int, int]) -> set[tuple[int, int]]:
    adjacency = {item.site: set() for item in state.locations}
    for strand in state.sequence.strands:
        for index in range(len(strand.symbols) - 1):
            left, right = (strand.strand_id, index), (strand.strand_id, index + 1)
            adjacency[left].add(right)
            adjacency[right].add(left)
        if strand.cyclic:
            left = strand.strand_id, len(strand.symbols) - 1
            right = strand.strand_id, 0
            adjacency[left].add(right)
            adjacency[right].add(left)
    for contact in state.sequence.contacts:
        for offset in range(contact.length):
            left = contact.left_id, contact.left_start + offset
            right = contact.right_id, contact.right_start + offset
            adjacency[left].add(right)
            adjacency[right].add(left)
    reached, pending = {start}, [start]
    while pending:
        current = pending.pop()
        unseen = adjacency[current] - reached
        reached.update(unseen)
        pending.extend(unseen)
    return reached


def _bond_adjacency(state: SpatialSequenceState) -> dict[tuple[int, int], set[tuple[int, int]]]:
    adjacency = {item.site: set() for item in state.locations}
    for strand in state.sequence.strands:
        for index in range(len(strand.symbols) - 1):
            left, right = (strand.strand_id, index), (strand.strand_id, index + 1)
            adjacency[left].add(right)
            adjacency[right].add(left)
        if strand.cyclic:
            left = strand.strand_id, len(strand.symbols) - 1
            right = strand.strand_id, 0
            adjacency[left].add(right)
            adjacency[right].add(left)
    for contact in state.sequence.contacts:
        for offset in range(contact.length):
            left = contact.left_id, contact.left_start + offset
            right = contact.right_id, contact.right_start + offset
            adjacency[left].add(right)
            adjacency[right].add(left)
    return adjacency


def _medium_after_material_motion(
    state: SpatialSequenceState,
    moved_sites: set[tuple[int, int]],
    targets: dict[tuple[int, int], tuple[int, int]],
) -> tuple[MediumCell, ...]:
    """Displace target-cell medium into cells vacated by the moving material."""
    old_points = {item.site: item.point for item in state.locations}
    old_region = {old_points[site] for site in moved_sites}
    new_region = {targets[site] for site in moved_sites}
    incoming = sorted(new_region - old_region)
    vacated = sorted(old_region - new_region)
    medium_at = {cell.point: cell for cell in state.medium}
    displaced = [medium_at.pop(point) for point in incoming if point in medium_at]
    if len(displaced) > len(vacated):
        raise AssertionError("material motion has nowhere to displace medium")
    for cell, point in zip(displaced, vacated):
        medium_at[point] = MediumCell(point[0], point[1], cell.amount, cell.energy)
    return tuple(sorted(medium_at.values()))


def _reached_without_edge(
    adjacency: dict[tuple[int, int], set[tuple[int, int]]],
    start: tuple[int, int],
    blocked: frozenset[tuple[int, int]],
) -> set[tuple[int, int]]:
    reached, pending = {start}, [start]
    while pending:
        current = pending.pop()
        for neighbor in adjacency[current] - reached:
            if frozenset((current, neighbor)) == blocked:
                continue
            reached.add(neighbor)
            pending.append(neighbor)
    return reached


def spatial_rotation_candidates(state: SpatialSequenceState) -> tuple[SpatialRotationCandidate, ...]:
    """Return every collision-free quarter-turn around an unlocked backbone hinge."""
    if state.sequence.thermal_energy < SPATIAL_ROTATION_COST:
        return ()
    points = {item.site: item.point for item in state.locations}
    occupied = set(points.values())
    adjacency = _bond_adjacency(state)
    candidates = []
    for strand in state.sequence.strands:
        edges = [
            ((strand.strand_id, index), (strand.strand_id, index + 1))
            for index in range(len(strand.symbols) - 1)
        ]
        if strand.cyclic:
            edges.append(((strand.strand_id, len(strand.symbols) - 1), (strand.strand_id, 0)))
        for edge in edges:
            blocked = frozenset(edge)
            for pivot, moving_start in (edge, edge[::-1]):
                members = _reached_without_edge(adjacency, moving_start, blocked)
                if pivot in members:
                    continue
                px, py = points[pivot]
                stationary_points = occupied - {points[member] for member in members}
                for quarter_turn in (-1, 1):
                    targets = {}
                    for member in members:
                        x, y = points[member]
                        rx, ry = x - px, y - py
                        offset = (-ry, rx) if quarter_turn == 1 else (ry, -rx)
                        targets[member] = (px + offset[0], py + offset[1])
                    if any(
                        not (0 <= x < state.width and 0 <= y < state.height)
                        for x, y in targets.values()
                    ):
                        continue
                    if len(set(targets.values())) != len(targets) or any(
                        point in stationary_points for point in targets.values()
                    ):
                        continue
                    candidates.append(SpatialRotationCandidate(
                        pivot,
                        moving_start,
                        quarter_turn,
                        tuple(sorted(members)),
                        tuple(sorted(targets.items())),
                    ))
    return tuple(sorted(set(candidates)))


def apply_spatial_rotation(
    state: SpatialSequenceState,
    candidate: SpatialRotationCandidate,
) -> SpatialSequenceStepResult:
    """Apply one available hinge rotation and dissipate its cost into the local field."""
    if candidate not in spatial_rotation_candidates(state):
        raise ValueError("spatial rotation is not physically available")
    targets = dict(candidate.targets)
    locations = tuple(
        SequenceSiteLocation(item.strand_id, item.site_index, *targets[item.site])
        if item.site in targets else item
        for item in state.locations
    )
    sequence = SequenceState(
        state.sequence.strands,
        state.sequence.thermal_energy - SPATIAL_ROTATION_COST,
        state.sequence.contacts,
        state.sequence.time + 1,
        state.sequence.next_strand_id,
    )
    amounts = _field_map(state)
    pivot_point = next(item.point for item in state.locations if item.site == candidate.pivot_site)
    amounts[pivot_point] = amounts.get(pivot_point, 0) + SPATIAL_ROTATION_COST
    next_state = SpatialSequenceState(
        sequence,
        state.width,
        state.height,
        locations,
        state.external_energy_exchange,
        _field_cells(amounts),
        _medium_after_material_motion(state, set(targets), targets),
    )
    event = WorldEvent.create(next_state.time, "sequence.spatial_rotate", {
        "cost": SPATIAL_ROTATION_COST,
        "member_sites": [list(site) for site in candidate.member_sites],
        "moving_site": list(candidate.moving_site),
        "pivot_site": list(candidate.pivot_site),
        "quarter_turn": candidate.quarter_turn,
        "spatial_state_hash": next_state.state_hash(),
    })
    return SpatialSequenceStepResult(next_state, event)


def spatial_flex_candidates(state: SpatialSequenceState) -> tuple[SpatialFlexCandidate, ...]:
    """Return reversible local corner flips that stretch or break no bond."""
    if state.sequence.thermal_energy < SPATIAL_ROTATION_COST:
        return ()
    points = {item.site: item.point for item in state.locations}
    occupied = set(points.values())
    adjacency = _bond_adjacency(state)
    candidates = []
    for strand in state.sequence.strands:
        strand_id = strand.strand_id
        indexes = range(len(strand.symbols)) if strand.cyclic else range(1, len(strand.symbols) - 1)
        for index in indexes:
            site = strand_id, index
            before = points[(strand_id, (index - 1) % len(strand.symbols))]
            source = points[site]
            after = points[(strand_id, (index + 1) % len(strand.symbols))]
            if abs(before[0] - after[0]) != 1 or abs(before[1] - after[1]) != 1:
                continue
            target = before[0] + after[0] - source[0], before[1] + after[1] - source[1]
            if target == source or target in occupied:
                continue
            if not (0 <= target[0] < state.width and 0 <= target[1] < state.height):
                continue
            if any(_distance(target, points[neighbor]) != 1 for neighbor in adjacency[site]):
                continue
            candidates.append(SpatialFlexCandidate(site, source, target))
    return tuple(sorted(candidates))


def apply_spatial_flex(
    state: SpatialSequenceState,
    candidate: SpatialFlexCandidate,
) -> SpatialSequenceStepResult:
    """Apply one available corner flip and dissipate its cost at the source cell."""
    if candidate not in spatial_flex_candidates(state):
        raise ValueError("spatial flex is not physically available")
    locations = tuple(
        SequenceSiteLocation(item.strand_id, item.site_index, *candidate.target)
        if item.site == candidate.site else item
        for item in state.locations
    )
    sequence = SequenceState(
        state.sequence.strands,
        state.sequence.thermal_energy - SPATIAL_ROTATION_COST,
        state.sequence.contacts,
        state.sequence.time + 1,
        state.sequence.next_strand_id,
    )
    amounts = _field_map(state)
    amounts[candidate.source] = amounts.get(candidate.source, 0) + SPATIAL_ROTATION_COST
    next_state = SpatialSequenceState(
        sequence,
        state.width,
        state.height,
        locations,
        state.external_energy_exchange,
        _field_cells(amounts),
        _medium_after_material_motion(state, {candidate.site}, {candidate.site: candidate.target}),
    )
    event = WorldEvent.create(next_state.time, "sequence.spatial_flex", {
        "cost": SPATIAL_ROTATION_COST,
        "site": list(candidate.site),
        "source": list(candidate.source),
        "spatial_state_hash": next_state.state_hash(),
        "target": list(candidate.target),
    })
    return SpatialSequenceStepResult(next_state, event)


def apply_spatial_sequence_move(
    state: SpatialSequenceState,
    site: tuple[int, int],
    dx: int,
    dy: int,
) -> SpatialSequenceStepResult:
    if (dx, dy) not in DIRECTIONS:
        raise ValueError("movement must be one cardinal grid step")
    points = {item.site: item.point for item in state.locations}
    if site not in points:
        raise ValueError("movement refers to a missing sequence site")
    component = _connected_sites(state, site)
    targets = {member: (points[member][0] + dx, points[member][1] + dy) for member in component}
    stationary = {point for member, point in points.items() if member not in component}
    if any(not (0 <= x < state.width and 0 <= y < state.height) for x, y in targets.values()):
        outcome = "world_boundary"
    elif any(point in stationary for point in targets.values()):
        outcome = "site_occupied"
    else:
        outcome = "moved"
    locations = tuple(
        SequenceSiteLocation(item.strand_id, item.site_index, *targets[item.site])
        if outcome == "moved" and item.site in component else item
        for item in state.locations
    )
    sequence = SequenceState(
        state.sequence.strands,
        state.sequence.thermal_energy,
        state.sequence.contacts,
        state.sequence.time + 1,
        state.sequence.next_strand_id,
    )
    next_state = SpatialSequenceState(
        sequence,
        state.width,
        state.height,
        locations,
        state.external_energy_exchange,
        state.field_energy,
        _medium_after_material_motion(state, component, targets) if outcome == "moved" else state.medium,
    )
    event = WorldEvent.create(next_state.time, "sequence.spatial_move", {
        "dx": dx,
        "dy": dy,
        "member_sites": [list(member) for member in sorted(component)],
        "outcome": outcome,
        "spatial_state_hash": next_state.state_hash(),
        "trigger_site": list(site),
    })
    return SpatialSequenceStepResult(next_state, event)


def _select(candidates: tuple[EventCandidate, ...], ticket: int) -> EventCandidate:
    cursor = 0
    for candidate in candidates:
        cursor += candidate.weight
        if ticket < cursor:
            return candidate
    raise ValueError("selection ticket lies outside candidate weights")


def step_spatial_sequence(state: SpatialSequenceState, chance: ChoiceSource) -> SpatialSequenceStepResult:
    moves = tuple((item.site, dx, dy) for item in state.locations for dx, dy in DIRECTIONS)
    rotations = spatial_rotation_candidates(state)
    flexes = spatial_flex_candidates(state)
    reactions = spatial_event_candidates(state)
    reaction_weight = sum(item.weight for item in reactions)
    sample = chance.choice_index(len(moves) + len(rotations) + len(flexes) + reaction_weight)
    ticket = int(sample.value)
    if ticket < len(moves):
        site, dx, dy = moves[ticket]
        result = apply_spatial_sequence_move(state, site, dx, dy)
    elif ticket < len(moves) + len(rotations):
        result = apply_spatial_rotation(state, rotations[ticket - len(moves)])
    elif ticket < len(moves) + len(rotations) + len(flexes):
        result = apply_spatial_flex(state, flexes[ticket - len(moves) - len(rotations)])
    else:
        result = apply_spatial_sequence_candidate(
            state,
            _select(reactions, ticket - len(moves) - len(rotations) - len(flexes)),
        )
    return SpatialSequenceStepResult(result.state, result.event, sample.draw)


def apply_spatial_energy_flow(
    state: SpatialSequenceState,
    requested_amount: int,
) -> SpatialSequenceStepResult:
    """Exchange explicit thermal energy with a reservoir as one recorded event."""
    if isinstance(requested_amount, bool) or not isinstance(requested_amount, int) or requested_amount == 0:
        raise ValueError("requested energy flow must be a non-zero integer")
    applied = requested_amount
    if requested_amount < 0:
        applied = -min(-requested_amount, state.sequence.thermal_energy)
    sequence = SequenceState(
        state.sequence.strands,
        state.sequence.thermal_energy + applied,
        state.sequence.contacts,
        state.sequence.time + 1,
        state.sequence.next_strand_id,
    )
    next_state = SpatialSequenceState(
        sequence,
        state.width,
        state.height,
        state.locations,
        state.external_energy_exchange + applied,
        state.field_energy,
        state.medium,
    )
    event = WorldEvent.create(
        next_state.time,
        "sequence.environment_energy_flow",
        {
            "applied": applied,
            "requested": requested_amount,
            "reservoir_adjusted_energy": next_state.reservoir_adjusted_energy,
            "spatial_state_hash": next_state.state_hash(),
        },
    )
    return SpatialSequenceStepResult(next_state, event)


def step_spatial_sequence_with_flow(
    state: SpatialSequenceState,
    chance: ChoiceSource,
    flow: PeriodicEnergyFlow,
) -> tuple[SpatialSequenceStepResult, ...]:
    """Apply every due reservoir event, then one ordinary event without skipping it."""
    results = []
    current = state
    if current.time > 0 and current.time % flow.interval == 0:
        flowed = apply_spatial_energy_flow(current, flow.amount)
        results.append(flowed)
        current = flowed.state
    stepped = step_spatial_sequence(current, chance)
    results.append(stepped)
    return tuple(results)


def _field_map(state: SpatialSequenceState) -> dict[tuple[int, int], int]:
    return {cell.point: cell.amount for cell in state.field_energy}


def _field_cells(amounts: dict[tuple[int, int], int]) -> tuple[EnergyCell, ...]:
    return tuple(EnergyCell(x, y, amount) for (x, y), amount in sorted(amounts.items()) if amount > 0)


def apply_spatial_energy_sources(
    state: SpatialSequenceState,
    sources: tuple[EnergySource, ...],
) -> SpatialSequenceStepResult:
    """Apply fixed sources and sinks at exact coordinates and record actual exchange."""
    amounts = _field_map(state)
    applied = []
    net = 0
    for source in sources:
        if not (0 <= source.x < state.width and 0 <= source.y < state.height):
            raise ValueError("energy source lies outside the grid")
        before = amounts.get(source.point, 0)
        change = source.amount if source.amount > 0 else -min(-source.amount, before)
        after = before + change
        if after:
            amounts[source.point] = after
        else:
            amounts.pop(source.point, None)
        applied.append({"amount": change, "x": source.x, "y": source.y})
        net += change
    sequence = SequenceState(
        state.sequence.strands,
        state.sequence.thermal_energy,
        state.sequence.contacts,
        state.sequence.time + 1,
        state.sequence.next_strand_id,
    )
    next_state = SpatialSequenceState(
        sequence,
        state.width,
        state.height,
        state.locations,
        state.external_energy_exchange + net,
        _field_cells(amounts),
        state.medium,
    )
    event = WorldEvent.create(next_state.time, "sequence.environment_energy_sources", {
        "applied": applied,
        "net_external_exchange": net,
        "reservoir_adjusted_energy": next_state.reservoir_adjusted_energy,
        "spatial_state_hash": next_state.state_hash(),
    })
    return SpatialSequenceStepResult(next_state, event)


def apply_spatial_energy_diffusion(
    state: SpatialSequenceState,
    divisor: int = 4,
) -> SpatialSequenceStepResult:
    """Spread integer energy simultaneously; boundaries retain unexported shares."""
    if isinstance(divisor, bool) or not isinstance(divisor, int) or divisor < 4:
        raise ValueError("diffusion divisor must be an integer of at least four")
    before = _field_map(state)
    after = dict(before)
    transferred = 0
    for (x, y), amount in before.items():
        share = amount // divisor
        if share == 0:
            continue
        for dx, dy in DIRECTIONS:
            target = x + dx, y + dy
            if not (0 <= target[0] < state.width and 0 <= target[1] < state.height):
                continue
            after[(x, y)] -= share
            after[target] = after.get(target, 0) + share
            transferred += share
    sequence = SequenceState(
        state.sequence.strands,
        state.sequence.thermal_energy,
        state.sequence.contacts,
        state.sequence.time + 1,
        state.sequence.next_strand_id,
    )
    next_state = SpatialSequenceState(
        sequence,
        state.width,
        state.height,
        state.locations,
        state.external_energy_exchange,
        _field_cells(after),
        state.medium,
    )
    event = WorldEvent.create(next_state.time, "sequence.environment_energy_diffusion", {
        "reservoir_adjusted_energy": next_state.reservoir_adjusted_energy,
        "spatial_state_hash": next_state.state_hash(),
        "transferred": transferred,
    })
    return SpatialSequenceStepResult(next_state, event)


def apply_spatial_energy_absorption(
    state: SpatialSequenceState,
    per_site: int = 1,
) -> SpatialSequenceStepResult:
    """Move field energy into thermal energy only where material physically sits."""
    if isinstance(per_site, bool) or not isinstance(per_site, int) or per_site < 0:
        raise ValueError("per-site absorption must be a non-negative integer")
    amounts = _field_map(state)
    absorbed = 0
    for item in state.locations:
        available = amounts.get(item.point, 0)
        moved = min(per_site, available)
        if moved:
            amounts[item.point] = available - moved
            absorbed += moved
    sequence = SequenceState(
        state.sequence.strands,
        state.sequence.thermal_energy + absorbed,
        state.sequence.contacts,
        state.sequence.time + 1,
        state.sequence.next_strand_id,
    )
    next_state = SpatialSequenceState(
        sequence,
        state.width,
        state.height,
        state.locations,
        state.external_energy_exchange,
        _field_cells(amounts),
        state.medium,
    )
    event = WorldEvent.create(next_state.time, "sequence.environment_energy_absorption", {
        "absorbed": absorbed,
        "reservoir_adjusted_energy": next_state.reservoir_adjusted_energy,
        "spatial_state_hash": next_state.state_hash(),
    })
    return SpatialSequenceStepResult(next_state, event)


def apply_medium_diffusion(
    state: SpatialSequenceState,
    divisor: int = 8,
) -> SpatialSequenceStepResult:
    """Diffuse conserved medium and its carried energy through unoccupied cells."""
    if isinstance(divisor, bool) or not isinstance(divisor, int) or divisor < 4:
        raise ValueError("medium diffusion divisor must be an integer of at least four")
    occupied = {item.point for item in state.locations}
    amounts = {cell.point: cell.amount for cell in state.medium}
    energies = {cell.point: cell.energy for cell in state.medium}
    after_amounts = dict(amounts)
    after_energies = dict(energies)
    moved_amount = 0
    moved_energy = 0
    for point in sorted(amounts):
        x, y = point
        targets = [
            (x + dx, y + dy)
            for dx, dy in DIRECTIONS
            if 0 <= x + dx < state.width
            and 0 <= y + dy < state.height
            and (x + dx, y + dy) not in occupied
        ]
        amount_share = amounts[point] // divisor
        if energies[point] > 0 and targets:
            amount_share = min(amount_share, (amounts[point] - 1) // len(targets))
        energy_share = energies[point] // divisor
        if amount_share == 0:
            continue
        for target in targets:
            after_amounts[point] -= amount_share
            after_amounts[target] = after_amounts.get(target, 0) + amount_share
            after_energies[point] -= energy_share
            after_energies[target] = after_energies.get(target, 0) + energy_share
            moved_amount += amount_share
            moved_energy += energy_share
    medium = tuple(
        MediumCell(point[0], point[1], amount, after_energies.get(point, 0))
        for point, amount in sorted(after_amounts.items())
        if amount > 0
    )
    sequence = SequenceState(
        state.sequence.strands,
        state.sequence.thermal_energy,
        state.sequence.contacts,
        state.sequence.time + 1,
        state.sequence.next_strand_id,
    )
    next_state = SpatialSequenceState(
        sequence,
        state.width,
        state.height,
        state.locations,
        state.external_energy_exchange,
        state.field_energy,
        medium,
    )
    event = WorldEvent.create(next_state.time, "sequence.medium_diffusion", {
        "energy_transferred": moved_energy,
        "medium_transferred": moved_amount,
        "reservoir_adjusted_energy": next_state.reservoir_adjusted_energy,
        "spatial_state_hash": next_state.state_hash(),
    })
    return SpatialSequenceStepResult(next_state, event)


def apply_field_to_medium(
    state: SpatialSequenceState,
    per_cell: int = 1,
) -> SpatialSequenceStepResult:
    """Load field energy into co-located medium without creating energy."""
    if isinstance(per_cell, bool) or not isinstance(per_cell, int) or per_cell < 0:
        raise ValueError("field coupling per cell must be a non-negative integer")
    field = _field_map(state)
    transferred = 0
    medium = []
    for cell in state.medium:
        available = field.get(cell.point, 0)
        moved = min(per_cell, available)
        if moved:
            field[cell.point] = available - moved
            transferred += moved
        medium.append(MediumCell(cell.x, cell.y, cell.amount, cell.energy + moved))
    sequence = SequenceState(
        state.sequence.strands,
        state.sequence.thermal_energy,
        state.sequence.contacts,
        state.sequence.time + 1,
        state.sequence.next_strand_id,
    )
    next_state = SpatialSequenceState(
        sequence,
        state.width,
        state.height,
        state.locations,
        state.external_energy_exchange,
        _field_cells(field),
        tuple(medium),
    )
    event = WorldEvent.create(next_state.time, "sequence.field_to_medium", {
        "reservoir_adjusted_energy": next_state.reservoir_adjusted_energy,
        "spatial_state_hash": next_state.state_hash(),
        "transferred": transferred,
    })
    return SpatialSequenceStepResult(next_state, event)


def apply_medium_collision_absorption(
    state: SpatialSequenceState,
    per_site: int = 1,
) -> SpatialSequenceStepResult:
    """Transfer energy from adjacent medium into material without consuming medium."""
    if isinstance(per_site, bool) or not isinstance(per_site, int) or per_site < 0:
        raise ValueError("medium absorption per site must be a non-negative integer")
    medium = {cell.point: [cell.amount, cell.energy] for cell in state.medium}
    absorbed = 0
    for item in state.locations:
        remaining = per_site
        for dx, dy in DIRECTIONS:
            point = item.x + dx, item.y + dy
            cell = medium.get(point)
            if cell is None or remaining == 0:
                continue
            moved = min(remaining, cell[1])
            cell[1] -= moved
            remaining -= moved
            absorbed += moved
    cells = tuple(
        MediumCell(point[0], point[1], values[0], values[1])
        for point, values in sorted(medium.items())
    )
    sequence = SequenceState(
        state.sequence.strands,
        state.sequence.thermal_energy + absorbed,
        state.sequence.contacts,
        state.sequence.time + 1,
        state.sequence.next_strand_id,
    )
    next_state = SpatialSequenceState(
        sequence,
        state.width,
        state.height,
        state.locations,
        state.external_energy_exchange,
        state.field_energy,
        cells,
    )
    event = WorldEvent.create(next_state.time, "sequence.medium_collision_absorption", {
        "absorbed": absorbed,
        "reservoir_adjusted_energy": next_state.reservoir_adjusted_energy,
        "spatial_state_hash": next_state.state_hash(),
    })
    return SpatialSequenceStepResult(next_state, event)


def apply_medium_transport_cycle(
    state: SpatialSequenceState,
    law: MediumTransportLaw,
) -> tuple[SpatialSequenceStepResult, SpatialSequenceStepResult, SpatialSequenceStepResult]:
    coupled = apply_field_to_medium(state, law.field_coupling_per_cell)
    diffused = apply_medium_diffusion(coupled.state, law.diffusion_divisor)
    absorbed = apply_medium_collision_absorption(diffused.state, law.absorption_per_site)
    return coupled, diffused, absorbed


def apply_spatial_energy_cycle(
    state: SpatialSequenceState,
    law: SpatialEnergyLaw,
) -> tuple[SpatialSequenceStepResult, ...]:
    """One fully recorded source, diffusion, and contact-absorption cycle."""
    sourced = apply_spatial_energy_sources(state, law.sources)
    diffused = apply_spatial_energy_diffusion(sourced.state, law.diffusion_divisor)
    absorbed = apply_spatial_energy_absorption(diffused.state, law.absorption_per_site)
    return sourced, diffused, absorbed
