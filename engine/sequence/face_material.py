"""Reversible exchange between dissolved face matter and spatial sequences.

Nothing in this module knows whether a boundary is alive.  A dissolved material
kind may condense at an empty lattice vertex and an unbound one-site fragment may
return to solution.  Nearby sequence symbols only change relative condensation
frequency through the same anonymous affinity axes used by side contacts.  Thus
template-like copying, including mismatches, is a consequence of local material
interaction rather than an engine instruction to reproduce.
"""
from __future__ import annotations

from dataclasses import dataclass

from engine.living.events import RandomDraw, WorldEvent

from .face_space import Face, FaceMediumCell, FaceSoluteCell
from .spatial_sequence import SequenceSiteLocation, SpatialSequenceState
from .substrate import BACKBONE_COST, ChoiceSource, Contact, SequenceState, Strand, pair_score


@dataclass(frozen=True)
class FaceMaterialLaw:
    interval: int = 1
    activation_energy: int = 1
    spontaneous_weight: int = 1
    affinity_weight: int = 1
    dissolution_weight: int = 1

    def __post_init__(self) -> None:
        values = (
            self.interval, self.activation_energy, self.spontaneous_weight,
            self.affinity_weight, self.dissolution_weight,
        )
        if any(isinstance(value, bool) or not isinstance(value, int) for value in values):
            raise TypeError("face material law values must be integers")
        if self.interval <= 0 or self.activation_energy < 0:
            raise ValueError("interval must be positive and activation energy non-negative")
        if self.spontaneous_weight <= 0 or self.affinity_weight < 0 or self.dissolution_weight <= 0:
            raise ValueError("material event weights are invalid")


@dataclass(frozen=True, order=True)
class FaceMaterialCandidate:
    kind: str
    face: Face
    x: int
    y: int
    symbol: int
    strand_id: int = -1
    template_id: int = -1
    template_index: int = -1
    end: int = 1
    weight: int = 1


@dataclass(frozen=True)
class FaceMaterialResult:
    physical: SpatialSequenceState
    face_medium: tuple[FaceMediumCell, ...]
    face_solutes: tuple[FaceSoluteCell, ...]
    event: WorldEvent
    random_draw: RandomDraw | None


def _corners(face: Face) -> tuple[tuple[int, int], ...]:
    x, y = face
    return ((x, y), (x + 1, y), (x, y + 1), (x + 1, y + 1))


def _adjacent_faces(point: tuple[int, int], width: int, height: int) -> tuple[Face, ...]:
    x, y = point
    return tuple(
        (fx, fy)
        for fx, fy in ((x - 1, y - 1), (x, y - 1), (x - 1, y), (x, y))
        if 0 <= fx < width - 1 and 0 <= fy < height - 1
    )


def face_material_candidates(
    physical: SpatialSequenceState,
    face_medium: tuple[FaceMediumCell, ...],
    face_solutes: tuple[FaceSoluteCell, ...],
    law: FaceMaterialLaw,
) -> tuple[FaceMaterialCandidate, ...]:
    occupied = {item.point for item in physical.locations}
    strand_by_id = {strand.strand_id: strand for strand in physical.sequence.strands}
    site_symbol = {item.point: strand_by_id[item.strand_id].symbols[item.site_index] for item in physical.locations}
    energy = {cell.face: cell.energy for cell in face_medium}
    candidates: list[FaceMaterialCandidate] = []
    for cell in face_solutes:
        if energy.get(cell.face, 0) < law.activation_energy:
            continue
        for point in _corners(cell.face):
            if point in occupied:
                continue
            neighbors = [
                site_symbol[other]
                for other in ((point[0] - 1, point[1]), (point[0] + 1, point[1]),
                              (point[0], point[1] - 1), (point[0], point[1] + 1))
                if other in site_symbol
            ]
            affinity = sum(max(0, pair_score(cell.kind, other)) for other in neighbors)
            weight = law.spontaneous_weight + law.affinity_weight * affinity
            candidates.append(FaceMaterialCandidate("condense", cell.face, *point, cell.kind, weight=weight))

    contacted = {
        site
        for contact in physical.sequence.contacts
        for site in (
            *((contact.left_id, contact.left_start + offset) for offset in range(contact.length)),
            *((contact.right_id, contact.right_start + offset) for offset in range(contact.length)),
        )
    }
    locations = {item.site: item.point for item in physical.locations}
    solute_cells = {(cell.face, cell.kind): cell.amount for cell in face_solutes}

    # A strand end can extend beside a neighboring template one site at a time.
    # Every material kind remains possible; affinity changes frequency, not legality.
    extensions: set[FaceMaterialCandidate] = set()
    for strand in physical.sequence.strands:
        if strand.cyclic:
            continue
        for end_index, end in ((0, -1), (len(strand.symbols) - 1, 1)):
            end_point = locations[(strand.strand_id, end_index)]
            for template_site, template_point in locations.items():
                template_id, template_index = template_site
                if template_id == strand.strand_id or abs(end_point[0] - template_point[0]) + abs(end_point[1] - template_point[1]) != 1:
                    continue
                template = strand_by_id[template_id]
                for direction in (-1, 1):
                    next_index = template_index + direction
                    if not 0 <= next_index < len(template.symbols):
                        continue
                    next_template = locations[(template_id, next_index)]
                    delta = next_template[0] - template_point[0], next_template[1] - template_point[1]
                    target = end_point[0] + delta[0], end_point[1] + delta[1]
                    if target in occupied or not (0 <= target[0] < physical.width and 0 <= target[1] < physical.height):
                        continue
                    shared_faces = set(_adjacent_faces(target, physical.width, physical.height)) & set(
                        _adjacent_faces(next_template, physical.width, physical.height)
                    )
                    for face in sorted(shared_faces):
                        if energy.get(face, 0) < law.activation_energy + BACKBONE_COST:
                            continue
                        for symbol in range(4):
                            if solute_cells.get((face, symbol), 0) <= 0:
                                continue
                            affinity = max(0, pair_score(symbol, template.symbols[next_index]))
                            weight = law.spontaneous_weight + law.affinity_weight * affinity
                            extensions.add(FaceMaterialCandidate(
                                "extend", face, *target, symbol, strand.strand_id,
                                template_id, next_index, end, weight,
                            ))
    candidates.extend(extensions)

    for strand in physical.sequence.strands:
        if strand.cyclic:
            continue
        ends = ((0, 0),) if len(strand.symbols) == 1 else ((0, -1), (len(strand.symbols) - 1, 1))
        for end_index, end in ends:
            if (strand.strand_id, end_index) in contacted:
                continue
            point = locations[(strand.strand_id, end_index)]
            for face in _adjacent_faces(point, physical.width, physical.height):
                if face in energy and physical.sequence.thermal_energy >= law.activation_energy:
                    candidates.append(FaceMaterialCandidate(
                        "dissolve" if len(strand.symbols) == 1 else "erode",
                        face, *point, strand.symbols[end_index], strand.strand_id,
                        end=end, weight=law.dissolution_weight,
                    ))
    return tuple(sorted(candidates))


def _weighted_choice(candidates: tuple[FaceMaterialCandidate, ...], chance: ChoiceSource):
    total = sum(item.weight for item in candidates)
    sample = chance.choice_index(total)
    offset = int(sample.value)
    for item in candidates:
        if offset < item.weight:
            return item, sample.draw
        offset -= item.weight
    raise AssertionError("weighted material choice exceeded candidate weights")


def apply_face_material_candidate(
    physical: SpatialSequenceState,
    face_medium: tuple[FaceMediumCell, ...],
    face_solutes: tuple[FaceSoluteCell, ...],
    candidate: FaceMaterialCandidate,
    law: FaceMaterialLaw,
    random_draw: RandomDraw | None = None,
) -> FaceMaterialResult:
    candidates = face_material_candidates(physical, face_medium, face_solutes, law)
    if candidate not in candidates:
        raise ValueError("face material candidate is not currently possible")
    medium = {cell.face: [cell.amount, cell.energy] for cell in face_medium}
    solutes = {(cell.face, cell.kind): cell.amount for cell in face_solutes}
    strands = list(physical.sequence.strands)
    locations = list(physical.locations)
    thermal = physical.sequence.thermal_energy
    next_id = int(physical.sequence.next_strand_id)
    result_strand_id = candidate.strand_id
    template_symbol = -1
    copy_match = False
    if candidate.kind == "condense":
        result_strand_id = next_id
        key = candidate.face, candidate.symbol
        solutes[key] -= 1
        medium[candidate.face][1] -= law.activation_energy
        thermal += law.activation_energy
        strands.append(Strand(next_id, (candidate.symbol,)))
        locations.append(SequenceSiteLocation(next_id, 0, candidate.x, candidate.y))
        next_id += 1
    elif candidate.kind == "extend":
        key = candidate.face, candidate.symbol
        solutes[key] -= 1
        medium[candidate.face][1] -= law.activation_energy + BACKBONE_COST
        template_symbol = next(
            strand.symbols[candidate.template_index]
            for strand in strands if strand.strand_id == candidate.template_id
        )
        affinity = pair_score(candidate.symbol, template_symbol)
        copy_match = candidate.symbol == template_symbol
        contacted_sites = {
            site for contact in physical.sequence.contacts for site in (
                *((contact.left_id, contact.left_start + offset) for offset in range(contact.length)),
                *((contact.right_id, contact.right_start + offset) for offset in range(contact.length)),
            )
        }
        stabilizes = affinity > 0 and (candidate.template_id, candidate.template_index) not in contacted_sites
        thermal += law.activation_energy + (affinity if stabilizes else 0)
        old = next(strand for strand in strands if strand.strand_id == candidate.strand_id)
        if candidate.end > 0:
            strands = [Strand(s.strand_id, s.symbols + (candidate.symbol,)) if s.strand_id == old.strand_id else s for s in strands]
            locations.append(SequenceSiteLocation(old.strand_id, len(old.symbols), candidate.x, candidate.y))
            new_index = len(old.symbols)
            contacts = list(physical.sequence.contacts)
        else:
            strands = [Strand(s.strand_id, (candidate.symbol,) + s.symbols) if s.strand_id == old.strand_id else s for s in strands]
            locations = [
                SequenceSiteLocation(item.strand_id, item.site_index + 1, item.x, item.y)
                if item.strand_id == old.strand_id else item for item in locations
            ]
            locations.append(SequenceSiteLocation(old.strand_id, 0, candidate.x, candidate.y))
            new_index = 0
            contacts = []
            for contact in physical.sequence.contacts:
                left_start = contact.left_start + int(contact.left_id == old.strand_id)
                right_start = contact.right_start + int(contact.right_id == old.strand_id)
                contacts.append(Contact(contact.left_id, left_start, contact.right_id, right_start, contact.length, contact.bond_energy))
        if stabilizes:
            first = (old.strand_id, new_index)
            second = (candidate.template_id, candidate.template_index)
            if first <= second:
                contacts.append(Contact(first[0], first[1], second[0], second[1], 1, affinity))
            else:
                contacts.append(Contact(second[0], second[1], first[0], first[1], 1, affinity))
    elif candidate.kind == "dissolve":
        strands = [strand for strand in strands if strand.strand_id != candidate.strand_id]
        locations = [item for item in locations if item.strand_id != candidate.strand_id]
        solutes[(candidate.face, candidate.symbol)] = solutes.get((candidate.face, candidate.symbol), 0) + 1
        medium[candidate.face][1] += law.activation_energy
        thermal -= law.activation_energy
    else:
        old = next(strand for strand in strands if strand.strand_id == candidate.strand_id)
        if candidate.end > 0:
            strands = [Strand(s.strand_id, s.symbols[:-1]) if s.strand_id == old.strand_id else s for s in strands]
            locations = [item for item in locations if not (item.strand_id == old.strand_id and item.site_index == len(old.symbols) - 1)]
            contacts = list(physical.sequence.contacts)
        else:
            strands = [Strand(s.strand_id, s.symbols[1:]) if s.strand_id == old.strand_id else s for s in strands]
            locations = [
                SequenceSiteLocation(item.strand_id, item.site_index - 1, item.x, item.y)
                if item.strand_id == old.strand_id and item.site_index > 0 else item
                for item in locations if not (item.strand_id == old.strand_id and item.site_index == 0)
            ]
            contacts = []
            for contact in physical.sequence.contacts:
                left_start = contact.left_start - int(contact.left_id == old.strand_id)
                right_start = contact.right_start - int(contact.right_id == old.strand_id)
                contacts.append(Contact(contact.left_id, left_start, contact.right_id, right_start, contact.length, contact.bond_energy))
        solutes[(candidate.face, candidate.symbol)] = solutes.get((candidate.face, candidate.symbol), 0) + 1
        medium[candidate.face][1] += law.activation_energy + BACKBONE_COST
        thermal -= law.activation_energy

    sequence = SequenceState(
        tuple(strands), thermal, tuple(contacts) if candidate.kind in {"extend", "erode"} else physical.sequence.contacts,
        physical.sequence.time + 1, next_id,
    )
    next_physical = SpatialSequenceState(
        sequence, physical.width, physical.height, tuple(locations),
        physical.external_energy_exchange, physical.field_energy, physical.medium,
    )
    next_medium = tuple(
        FaceMediumCell(x, y, values[0], values[1])
        for (x, y), values in sorted(medium.items())
    )
    next_solutes = tuple(
        FaceSoluteCell(face[0], face[1], kind, amount)
        for (face, kind), amount in sorted(solutes.items()) if amount > 0
    )
    event = WorldEvent.create(next_physical.time, f"sequence.face_material_{candidate.kind}", {
        "face": list(candidate.face), "kind": candidate.symbol,
        "state_hash": next_physical.state_hash(), "strand_id": candidate.strand_id,
        "result_strand_id": result_strand_id,
        "template_id": candidate.template_id, "template_index": candidate.template_index,
        "template_symbol": template_symbol, "copy_match": copy_match,
        "end": candidate.end, "weight": candidate.weight,
    })
    return FaceMaterialResult(next_physical, next_medium, next_solutes, event, random_draw)


def step_face_material(
    physical: SpatialSequenceState,
    face_medium: tuple[FaceMediumCell, ...],
    face_solutes: tuple[FaceSoluteCell, ...],
    chance: ChoiceSource,
    law: FaceMaterialLaw,
) -> FaceMaterialResult | None:
    candidates = face_material_candidates(physical, face_medium, face_solutes, law)
    if not candidates:
        return None
    selected, draw = _weighted_choice(candidates, chance)
    return apply_face_material_candidate(physical, face_medium, face_solutes, selected, law, draw)
