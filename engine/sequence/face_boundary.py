"""Reversible area changes of cyclic material boundaries on the face lattice."""
from __future__ import annotations

from dataclasses import dataclass

from engine.living.events import RandomDraw, WorldEvent

from .face_space import Face, FaceMediumCell, FaceSoluteCell
from .spatial_sequence import SequenceSiteLocation, SpatialSequenceState
from .substrate import BACKBONE_COST, ChoiceSource, Contact, SequenceState, Strand


@dataclass(frozen=True)
class FaceBoundaryLaw:
    interval: int = 4

    def __post_init__(self) -> None:
        if isinstance(self.interval, bool) or not isinstance(self.interval, int) or self.interval <= 0:
            raise ValueError("face boundary interval must be positive")


@dataclass(frozen=True, order=True)
class FaceBoundaryCandidate:
    kind: str
    face: Face
    strand_id: int
    edge_index: int
    first_symbol: int = -1
    second_symbol: int = -1
    weight: int = 1


@dataclass(frozen=True)
class FaceBoundaryResult:
    physical: SpatialSequenceState
    face_medium: tuple[FaceMediumCell, ...]
    face_solutes: tuple[FaceSoluteCell, ...]
    event: WorldEvent
    random_draw: RandomDraw


def _face_cycle(face: Face) -> tuple[tuple[int, int], ...]:
    x, y = face
    return ((x, y), (x + 1, y), (x + 1, y + 1), (x, y + 1))


def _other_corners(face: Face, first: tuple[int, int], second: tuple[int, int]):
    corners = _face_cycle(face)
    if first not in corners or second not in corners:
        return None
    start, finish = corners.index(first), corners.index(second)
    if finish == (start + 1) % 4:
        return corners[(start - 1) % 4], corners[(start - 2) % 4]
    if finish == (start - 1) % 4:
        return corners[(start + 1) % 4], corners[(start + 2) % 4]
    return None


def _edge_faces(first: tuple[int, int], second: tuple[int, int], width: int, height: int) -> tuple[Face, ...]:
    faces = []
    for y in range(max(0, min(first[1], second[1]) - 1), min(height - 1, max(first[1], second[1]) + 1)):
        for x in range(max(0, min(first[0], second[0]) - 1), min(width - 1, max(first[0], second[0]) + 1)):
            if first in _face_cycle((x, y)) and second in _face_cycle((x, y)) and _other_corners((x, y), first, second):
                faces.append((x, y))
    return tuple(sorted(faces))


def face_boundary_candidates(
    physical: SpatialSequenceState,
    medium: tuple[FaceMediumCell, ...],
    solutes: tuple[FaceSoluteCell, ...],
) -> tuple[FaceBoundaryCandidate, ...]:
    points = {item.site: item.point for item in physical.locations}
    occupied = set(points.values())
    energy = {cell.face: cell.energy for cell in medium}
    amounts = {(cell.face, cell.kind): cell.amount for cell in solutes}
    contacted = {
        site for contact in physical.sequence.contacts for site in (
            *((contact.left_id, contact.left_start + offset) for offset in range(contact.length)),
            *((contact.right_id, contact.right_start + offset) for offset in range(contact.length)),
        )
    }
    candidates: set[FaceBoundaryCandidate] = set()
    for strand in physical.sequence.strands:
        if not strand.cyclic:
            continue
        size = len(strand.symbols)
        for index in range(size):
            next_index = (index + 1) % size
            if (strand.strand_id, index) in contacted or (strand.strand_id, next_index) in contacted:
                continue
            first, second = points[(strand.strand_id, index)], points[(strand.strand_id, next_index)]
            for face in _edge_faces(first, second, physical.width, physical.height):
                path = _other_corners(face, first, second)
                if path is None or any(point in occupied for point in path) or energy.get(face, 0) < 2 * BACKBONE_COST:
                    continue
                for left_kind in range(4):
                    for right_kind in range(4):
                        need = 2 if left_kind == right_kind else 1
                        if amounts.get((face, left_kind), 0) < need or amounts.get((face, right_kind), 0) < need:
                            continue
                        candidates.add(FaceBoundaryCandidate(
                            "expand", face, strand.strand_id, index, left_kind, right_kind
                        ))

        if size < 6:
            continue
        for index in range(size - 3):
            sites = tuple(points[(strand.strand_id, index + offset)] for offset in range(4))
            first, middle_a, middle_b, last = sites
            if abs(first[0] - last[0]) + abs(first[1] - last[1]) != 1:
                continue
            if any((strand.strand_id, index + offset) in contacted for offset in (1, 2)):
                continue
            shared = set(_edge_faces(first, last, physical.width, physical.height))
            face = next((item for item in sorted(shared) if _other_corners(item, first, last) == (middle_a, middle_b)), None)
            try:
                shifted_contacts = tuple(
                    _shift_contact(contact, strand.strand_id, index + 2, -2)
                    for contact in physical.sequence.contacts
                )
                shortened = tuple(symbol for position, symbol in enumerate(strand.symbols) if position not in {index + 1, index + 2})
                candidate_strands = tuple(
                    Strand(item.strand_id, shortened, True) if item.strand_id == strand.strand_id else item
                    for item in physical.sequence.strands
                )
                SequenceState(
                    candidate_strands, physical.sequence.thermal_energy,
                    shifted_contacts, physical.sequence.time, physical.sequence.next_strand_id,
                )
            except ValueError:
                continue
            if face is not None and face in energy:
                candidates.add(FaceBoundaryCandidate("collapse", face, strand.strand_id, index))
    return tuple(sorted(candidates))


def _shift_contact(contact: Contact, strand_id: int, after: int, delta: int) -> Contact:
    left = contact.left_start + (delta if contact.left_id == strand_id and contact.left_start > after else 0)
    right = contact.right_start + (delta if contact.right_id == strand_id and contact.right_start > after else 0)
    return Contact(contact.left_id, left, contact.right_id, right, contact.length, contact.bond_energy)


def step_face_boundary(
    physical: SpatialSequenceState,
    medium: tuple[FaceMediumCell, ...],
    solutes: tuple[FaceSoluteCell, ...],
    chance: ChoiceSource,
) -> FaceBoundaryResult | None:
    candidates = face_boundary_candidates(physical, medium, solutes)
    if not candidates:
        return None
    sample = chance.choice_index(sum(candidate.weight for candidate in candidates))
    selected = candidates[int(sample.value)]
    strands = list(physical.sequence.strands)
    locations = list(physical.locations)
    contacts = list(physical.sequence.contacts)
    amounts = {(cell.face, cell.kind): cell.amount for cell in solutes}
    energies = {cell.face: [cell.amount, cell.energy] for cell in medium}
    strand = next(item for item in strands if item.strand_id == selected.strand_id)
    if selected.kind == "expand":
        insertion = selected.edge_index + 1
        first_point = next(item.point for item in locations if item.site == (strand.strand_id, selected.edge_index))
        second_index = (selected.edge_index + 1) % len(strand.symbols)
        second_point = next(item.point for item in locations if item.site == (strand.strand_id, second_index))
        new_points = _other_corners(selected.face, first_point, second_point)
        if new_points is None:
            raise AssertionError("boundary expansion lost its face geometry")
        symbols = strand.symbols[:insertion] + (selected.first_symbol, selected.second_symbol) + strand.symbols[insertion:]
        strands = [Strand(item.strand_id, symbols, True) if item.strand_id == strand.strand_id else item for item in strands]
        locations = [
            SequenceSiteLocation(item.strand_id, item.site_index + 2, item.x, item.y)
            if item.strand_id == strand.strand_id and item.site_index >= insertion else item
            for item in locations
        ]
        locations.extend((
            SequenceSiteLocation(strand.strand_id, insertion, *new_points[0]),
            SequenceSiteLocation(strand.strand_id, insertion + 1, *new_points[1]),
        ))
        contacts = [_shift_contact(contact, strand.strand_id, selected.edge_index, 2) for contact in contacts]
        amounts[(selected.face, selected.first_symbol)] -= 1
        amounts[(selected.face, selected.second_symbol)] -= 1
        energies[selected.face][1] -= 2 * BACKBONE_COST
    else:
        remove = {selected.edge_index + 1, selected.edge_index + 2}
        removed_symbols = (strand.symbols[selected.edge_index + 1], strand.symbols[selected.edge_index + 2])
        symbols = tuple(symbol for index, symbol in enumerate(strand.symbols) if index not in remove)
        strands = [Strand(item.strand_id, symbols, True) if item.strand_id == strand.strand_id else item for item in strands]
        locations = [
            SequenceSiteLocation(item.strand_id, item.site_index - 2, item.x, item.y)
            if item.strand_id == strand.strand_id and item.site_index > selected.edge_index + 2 else item
            for item in locations if not (item.strand_id == strand.strand_id and item.site_index in remove)
        ]
        contacts = [_shift_contact(contact, strand.strand_id, selected.edge_index + 2, -2) for contact in contacts]
        for symbol in removed_symbols:
            amounts[(selected.face, symbol)] = amounts.get((selected.face, symbol), 0) + 1
        energies[selected.face][1] += 2 * BACKBONE_COST

    sequence = SequenceState(
        tuple(strands), physical.sequence.thermal_energy, tuple(contacts),
        physical.sequence.time + 1, physical.sequence.next_strand_id,
    )
    next_physical = SpatialSequenceState(
        sequence, physical.width, physical.height, tuple(locations),
        physical.external_energy_exchange, physical.field_energy, physical.medium,
    )
    next_medium = tuple(FaceMediumCell(x, y, values[0], values[1]) for (x, y), values in sorted(energies.items()))
    next_solutes = tuple(
        FaceSoluteCell(face[0], face[1], kind, amount)
        for (face, kind), amount in sorted(amounts.items()) if amount > 0
    )
    event = WorldEvent.create(next_physical.time, f"sequence.face_boundary_{selected.kind}", {
        "edge_index": selected.edge_index, "face": list(selected.face),
        "state_hash": next_physical.state_hash(), "strand_id": selected.strand_id,
        "symbols": list(
            (selected.first_symbol, selected.second_symbol)
            if selected.kind == "expand" else removed_symbols
        ),
    })
    return FaceBoundaryResult(next_physical, next_medium, next_solutes, event, sample.draw)
