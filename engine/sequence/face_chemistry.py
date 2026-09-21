"""Anonymous balanced reactions in every face, accelerated by local material.

Reactions are not restricted to observed compartments.  Closed boundaries only
change future chemistry by changing transport, so an observer's classification
can never cause metabolism.  Sequence symbols near a face change event frequency
through the same pair affinity used elsewhere; they are catalysts, not opcodes.
"""
from __future__ import annotations

from dataclasses import dataclass

from engine.living.events import RandomDraw, WorldEvent

from .face_space import Face, FaceSoluteCell
from .spatial_sequence import SpatialSequenceState
from .substrate import ChoiceSource, SequenceState, pair_score


def _counts(values: tuple[int, ...], name: str) -> tuple[int, int, int, int]:
    values = tuple(values)
    if len(values) != 4 or any(isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in values):
        raise ValueError(f"{name} must contain four non-negative integers")
    return values  # type: ignore[return-value]


@dataclass(frozen=True)
class FaceReaction:
    consumes: tuple[int, int, int, int]
    produces: tuple[int, int, int, int]
    signature: tuple[int, ...] = ()

    def __post_init__(self) -> None:
        consumes = _counts(self.consumes, "reaction consumes")
        produces = _counts(self.produces, "reaction produces")
        if sum(consumes) <= 0 or sum(consumes) != sum(produces):
            raise ValueError("a face reaction must conserve a positive number of material units")
        if any(isinstance(value, bool) or not isinstance(value, int) or not 0 <= value < 4 for value in self.signature):
            raise ValueError("reaction signature kinds must be zero through three")
        object.__setattr__(self, "consumes", consumes)
        object.__setattr__(self, "produces", produces)
        object.__setattr__(self, "signature", tuple(self.signature))


@dataclass(frozen=True)
class FaceChemistryLaw:
    interval: int
    reactions: tuple[FaceReaction, ...]
    spontaneous_weight: int = 1
    catalytic_weight: int = 1

    def __post_init__(self) -> None:
        if isinstance(self.interval, bool) or not isinstance(self.interval, int) or self.interval <= 0:
            raise ValueError("face chemistry interval must be positive")
        if not self.reactions:
            raise ValueError("face chemistry needs at least one balanced reaction")
        if self.spontaneous_weight <= 0 or self.catalytic_weight < 0:
            raise ValueError("face chemistry weights are invalid")
        object.__setattr__(self, "reactions", tuple(self.reactions))


@dataclass(frozen=True, order=True)
class FaceReactionCandidate:
    face: Face
    reaction_index: int
    weight: int


@dataclass(frozen=True)
class FaceChemistryResult:
    physical: SpatialSequenceState
    face_solutes: tuple[FaceSoluteCell, ...]
    event: WorldEvent
    random_draw: RandomDraw


def face_reaction_candidates(
    physical: SpatialSequenceState,
    solutes: tuple[FaceSoluteCell, ...],
    law: FaceChemistryLaw,
) -> tuple[FaceReactionCandidate, ...]:
    amounts = {(cell.face, cell.kind): cell.amount for cell in solutes}
    symbols = {
        item.point: next(s.symbols[item.site_index] for s in physical.sequence.strands if s.strand_id == item.strand_id)
        for item in physical.locations
    }
    faces = sorted({cell.face for cell in solutes})
    candidates = []
    for face in faces:
        x, y = face
        nearby = tuple(symbols[point] for point in ((x, y), (x + 1, y), (x, y + 1), (x + 1, y + 1)) if point in symbols)
        for index, reaction in enumerate(law.reactions):
            if any(amounts.get((face, kind), 0) < needed for kind, needed in enumerate(reaction.consumes)):
                continue
            catalytic_score = sum(
                max(0, pair_score(material, signature))
                for material in nearby for signature in reaction.signature
            )
            candidates.append(FaceReactionCandidate(
                face, index, law.spontaneous_weight + law.catalytic_weight * catalytic_score
            ))
    return tuple(candidates)


def step_face_chemistry(
    physical: SpatialSequenceState,
    solutes: tuple[FaceSoluteCell, ...],
    chance: ChoiceSource,
    law: FaceChemistryLaw,
) -> FaceChemistryResult | None:
    candidates = face_reaction_candidates(physical, solutes, law)
    if not candidates:
        return None
    total = sum(candidate.weight for candidate in candidates)
    sample = chance.choice_index(total)
    offset = int(sample.value)
    selected = candidates[-1]
    for candidate in candidates:
        if offset < candidate.weight:
            selected = candidate
            break
        offset -= candidate.weight
    reaction = law.reactions[selected.reaction_index]
    amounts = {(cell.face, cell.kind): cell.amount for cell in solutes}
    for kind, (consumed, produced) in enumerate(zip(reaction.consumes, reaction.produces)):
        key = selected.face, kind
        amounts[key] = amounts.get(key, 0) - consumed + produced
    next_solutes = tuple(
        FaceSoluteCell(face[0], face[1], kind, amount)
        for (face, kind), amount in sorted(amounts.items()) if amount > 0
    )
    sequence = SequenceState(
        physical.sequence.strands, physical.sequence.thermal_energy,
        physical.sequence.contacts, physical.sequence.time + 1,
        physical.sequence.next_strand_id,
    )
    next_physical = SpatialSequenceState(
        sequence, physical.width, physical.height, physical.locations,
        physical.external_energy_exchange, physical.field_energy, physical.medium,
    )
    event = WorldEvent.create(next_physical.time, "sequence.face_reaction", {
        "face": list(selected.face), "reaction_index": selected.reaction_index,
        "state_hash": next_physical.state_hash(), "weight": selected.weight,
    })
    return FaceChemistryResult(next_physical, next_solutes, event, sample.draw)
