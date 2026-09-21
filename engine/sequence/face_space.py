"""Dual-lattice volume: sequence matter sits on vertices, medium in faces."""
from __future__ import annotations

from dataclasses import dataclass

from .spatial_sequence import SpatialSequenceState
from .substrate import pair_score


Point = tuple[int, int]
Edge = tuple[Point, Point]
Face = tuple[int, int]


def _edge(first: Point, second: Point) -> Edge:
    return (first, second) if first < second else (second, first)


@dataclass(frozen=True, order=True)
class FaceMediumCell:
    x: int
    y: int
    amount: int
    energy: int = 0

    def __post_init__(self) -> None:
        if any(isinstance(value, bool) or not isinstance(value, int) for value in (self.x, self.y, self.amount, self.energy)):
            raise TypeError("face medium values must be integers")
        if self.amount <= 0 or self.energy < 0:
            raise ValueError("face medium amount must be positive and energy non-negative")

    @property
    def face(self) -> Face:
        return self.x, self.y


@dataclass(frozen=True, order=True)
class FaceSoluteCell:
    x: int
    y: int
    kind: int
    amount: int

    def __post_init__(self) -> None:
        if any(isinstance(value, bool) or not isinstance(value, int) for value in (self.x, self.y, self.kind, self.amount)):
            raise TypeError("face solute values must be integers")
        if not 0 <= self.kind < 4 or self.amount <= 0:
            raise ValueError("solute kind must be zero through three and amount positive")

    @property
    def face(self) -> Face:
        return self.x, self.y


@dataclass(frozen=True, order=True)
class FaceEnergySource:
    x: int
    y: int
    amount: int

    def __post_init__(self) -> None:
        if any(isinstance(value, bool) or not isinstance(value, int) for value in (self.x, self.y, self.amount)):
            raise TypeError("face source values must be integers")
        if self.amount == 0:
            raise ValueError("face source amount cannot be zero")

    @property
    def face(self) -> Face:
        return self.x, self.y


@dataclass(frozen=True)
class FaceTransportLaw:
    interval: int
    sources: tuple[FaceEnergySource, ...]
    diffusion_divisor: int = 8
    absorption_per_site: int = 1

    def __post_init__(self) -> None:
        if isinstance(self.interval, bool) or not isinstance(self.interval, int) or self.interval <= 0:
            raise ValueError("face transport interval must be positive")
        if isinstance(self.diffusion_divisor, bool) or not isinstance(self.diffusion_divisor, int) or self.diffusion_divisor < 4:
            raise ValueError("face diffusion divisor must be at least four")
        if isinstance(self.absorption_per_site, bool) or not isinstance(self.absorption_per_site, int) or self.absorption_per_site < 0:
            raise ValueError("face absorption must be non-negative")


@dataclass(frozen=True, order=True)
class ObservedFaceCompartment:
    boundary_edges: tuple[Edge, ...]
    interior_faces: tuple[Face, ...]
    interior_medium_amount: int
    interior_medium_energy: int


def bond_barriers(state: SpatialSequenceState) -> frozenset[Edge]:
    points = {item.site: item.point for item in state.locations}
    barriers = set()
    for strand in state.sequence.strands:
        for index in range(len(strand.symbols) - 1):
            barriers.add(_edge(points[(strand.strand_id, index)], points[(strand.strand_id, index + 1)]))
        if strand.cyclic:
            barriers.add(_edge(points[(strand.strand_id, len(strand.symbols) - 1)], points[(strand.strand_id, 0)]))
    for contact in state.sequence.contacts:
        for offset in range(contact.length):
            barriers.add(_edge(
                points[(contact.left_id, contact.left_start + offset)],
                points[(contact.right_id, contact.right_start + offset)],
            ))
    return frozenset(barriers)


def barrier_materials(state: SpatialSequenceState) -> dict[Edge, tuple[int, int]]:
    points = {item.site: item.point for item in state.locations}
    symbols = {
        (strand.strand_id, index): symbol
        for strand in state.sequence.strands for index, symbol in enumerate(strand.symbols)
    }
    found = {}
    def add(left, right):
        found[_edge(points[left], points[right])] = (symbols[left], symbols[right])
    for strand in state.sequence.strands:
        for index in range(len(strand.symbols) - 1):
            add((strand.strand_id, index), (strand.strand_id, index + 1))
        if strand.cyclic:
            add((strand.strand_id, len(strand.symbols) - 1), (strand.strand_id, 0))
    for contact in state.sequence.contacts:
        for offset in range(contact.length):
            add((contact.left_id, contact.left_start + offset), (contact.right_id, contact.right_start + offset))
    return found


def surface_permeability(materials: tuple[int, int], solute_kind: int) -> int:
    """Anonymous compatibility; zero reflects, positive values cross per cycle."""
    return max(0, pair_score(solute_kind, materials[0]) + pair_score(solute_kind, materials[1]))


def diffuse_face_solutes(
    state: SpatialSequenceState,
    solutes: tuple[FaceSoluteCell, ...],
    divisor: int = 8,
) -> tuple[FaceSoluteCell, ...]:
    """Diffuse conserved anonymous solutes through open or compatible edges."""
    if isinstance(divisor, bool) or not isinstance(divisor, int) or divisor < 4:
        raise ValueError("solute diffusion divisor must be at least four")
    amounts = {(cell.face, cell.kind): cell.amount for cell in solutes}
    after = dict(amounts)
    materials = barrier_materials(state)
    for (face, kind), amount in sorted(amounts.items()):
        share = amount // divisor
        if share == 0:
            continue
        for neighbor, edge in face_sides(face):
            if not _inside(neighbor, state):
                continue
            moved = share if edge not in materials else min(share, surface_permeability(materials[edge], kind))
            if moved == 0:
                continue
            after[(face, kind)] -= moved
            after[(neighbor, kind)] = after.get((neighbor, kind), 0) + moved
    return tuple(
        FaceSoluteCell(face[0], face[1], kind, amount)
        for (face, kind), amount in sorted(after.items()) if amount > 0
    )


def face_sides(face: Face) -> tuple[tuple[Face | None, Edge], ...]:
    x, y = face
    return (
        ((x - 1, y), _edge((x, y), (x, y + 1))),
        ((x + 1, y), _edge((x + 1, y), (x + 1, y + 1))),
        ((x, y - 1), _edge((x, y), (x + 1, y))),
        ((x, y + 1), _edge((x, y + 1), (x + 1, y + 1))),
    )


def _inside(face: Face, state: SpatialSequenceState) -> bool:
    return 0 <= face[0] < state.width - 1 and 0 <= face[1] < state.height - 1


def observe_face_compartments(
    state: SpatialSequenceState,
    medium: tuple[FaceMediumCell, ...] = (),
) -> tuple[ObservedFaceCompartment, ...]:
    """Find face volumes disconnected from the exterior by actual bonded edges."""
    barriers = bond_barriers(state)
    faces = {(x, y) for y in range(state.height - 1) for x in range(state.width - 1)}
    exterior_starts = set()
    for face in faces:
        for neighbor, edge in face_sides(face):
            if not _inside(neighbor, state) and edge not in barriers:
                exterior_starts.add(face)
                break
    exterior = set(exterior_starts)
    pending = list(exterior_starts)
    while pending:
        face = pending.pop()
        for neighbor, edge in face_sides(face):
            if neighbor in faces and edge not in barriers and neighbor not in exterior:
                exterior.add(neighbor)
                pending.append(neighbor)
    unseen = faces - exterior
    medium_at = {cell.face: cell for cell in medium}
    observations = []
    while unseen:
        start = min(unseen)
        region = {start}
        pending = [start]
        while pending:
            face = pending.pop()
            for neighbor, edge in face_sides(face):
                if neighbor in unseen and edge not in barriers and neighbor not in region:
                    region.add(neighbor)
                    pending.append(neighbor)
        unseen.difference_update(region)
        boundary = set()
        for face in region:
            for neighbor, edge in face_sides(face):
                if neighbor not in region and edge in barriers:
                    boundary.add(edge)
        observations.append(ObservedFaceCompartment(
            tuple(sorted(boundary)),
            tuple(sorted(region)),
            sum(medium_at[face].amount for face in region if face in medium_at),
            sum(medium_at[face].energy for face in region if face in medium_at),
        ))
    return tuple(sorted(observations))
