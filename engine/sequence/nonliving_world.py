"""Integrated nonliving matter world built only from physical sequence laws.

The transition loop never receives compartment observations.  Observations are
collected after each transition for audit only and cannot affect future events.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from engine.living.events import RandomDraw, WorldEvent

from .spatial_compartment import observe_spatial_compartments
from .face_space import (
    FaceMediumCell,
    FaceSoluteCell,
    FaceTransportLaw,
    bond_barriers,
    face_sides,
    observe_face_compartments,
    diffuse_face_solutes,
)
from .spatial_sequence import (
    ChoiceSource,
    MediumTransportLaw,
    SpatialEnergyLaw,
    SpatialSequenceState,
    apply_spatial_energy_cycle,
    apply_medium_transport_cycle,
    step_spatial_sequence,
)
from .substrate import SequenceState
from .face_material import FaceMaterialLaw, step_face_material
from .face_chemistry import FaceChemistryLaw, step_face_chemistry
from .face_boundary import FaceBoundaryLaw, step_face_boundary


@dataclass(frozen=True)
class NonlivingWorldState:
    physical: SpatialSequenceState
    ordinary_events: int = 0
    face_medium: tuple[FaceMediumCell, ...] = ()
    face_external_energy_exchange: int = 0
    face_solutes: tuple[FaceSoluteCell, ...] = ()

    def __post_init__(self) -> None:
        if isinstance(self.ordinary_events, bool) or not isinstance(self.ordinary_events, int):
            raise TypeError("ordinary_events must be an integer")
        if self.ordinary_events < 0:
            raise ValueError("ordinary_events cannot be negative")
        cells = tuple(sorted(self.face_medium))
        if len({cell.face for cell in cells}) != len(cells):
            raise ValueError("a face can contain only one face-medium cell")
        if any(not (0 <= cell.x < self.physical.width - 1 and 0 <= cell.y < self.physical.height - 1) for cell in cells):
            raise ValueError("face medium lies outside the dual lattice")
        if isinstance(self.face_external_energy_exchange, bool) or not isinstance(self.face_external_energy_exchange, int):
            raise TypeError("face external energy exchange must be an integer")
        object.__setattr__(self, "face_medium", cells)
        solutes = tuple(sorted(self.face_solutes))
        if len({(cell.face, cell.kind) for cell in solutes}) != len(solutes):
            raise ValueError("a face can contain only one cell of each solute kind")
        object.__setattr__(self, "face_solutes", solutes)

    def canonical(self) -> dict[str, object]:
        payload = {"ordinary_events": self.ordinary_events, "physical": self.physical.canonical()}
        if self.face_medium:
            payload["face_medium"] = [
                {"amount": cell.amount, "energy": cell.energy, "x": cell.x, "y": cell.y}
                for cell in self.face_medium
            ]
        if self.face_external_energy_exchange:
            payload["face_external_energy_exchange"] = self.face_external_energy_exchange
        if self.face_solutes:
            payload["face_solutes"] = [
                {"amount": cell.amount, "kind": cell.kind, "x": cell.x, "y": cell.y}
                for cell in self.face_solutes
            ]
        return payload

    def state_hash(self) -> str:
        raw = json.dumps(self.canonical(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @property
    def reservoir_adjusted_energy(self) -> int:
        return (
            self.physical.reservoir_adjusted_energy
            + sum(cell.energy for cell in self.face_medium)
            - self.face_external_energy_exchange
        )


def _advance_physical(state: SpatialSequenceState, thermal_delta: int = 0) -> SpatialSequenceState:
    sequence = SequenceState(
        state.sequence.strands,
        state.sequence.thermal_energy + thermal_delta,
        state.sequence.contacts,
        state.sequence.time + 1,
        state.sequence.next_strand_id,
    )
    return SpatialSequenceState(
        sequence, state.width, state.height, state.locations,
        state.external_energy_exchange, state.field_energy, state.medium,
    )


def _face_source_step(state: NonlivingWorldState, law: FaceTransportLaw) -> tuple[NonlivingWorldState, WorldEvent]:
    cells = {cell.face: [cell.amount, cell.energy] for cell in state.face_medium}
    net = 0
    for source in law.sources:
        if source.face not in cells:
            raise ValueError("a face energy source needs medium at its face")
        applied = source.amount if source.amount > 0 else -min(-source.amount, cells[source.face][1])
        cells[source.face][1] += applied
        net += applied
    physical = _advance_physical(state.physical)
    next_state = NonlivingWorldState(
        physical,
        state.ordinary_events,
        tuple(FaceMediumCell(x, y, values[0], values[1]) for (x, y), values in sorted(cells.items())),
        state.face_external_energy_exchange + net,
        state.face_solutes,
    )
    event = WorldEvent.create(physical.time, "sequence.face_energy_sources", {
        "net_external_exchange": net,
        "state_hash": next_state.state_hash(),
    })
    return next_state, event


def _face_diffusion_step(state: NonlivingWorldState, law: FaceTransportLaw) -> tuple[NonlivingWorldState, WorldEvent]:
    barriers = bond_barriers(state.physical)
    amounts = {cell.face: cell.amount for cell in state.face_medium}
    energies = {cell.face: cell.energy for cell in state.face_medium}
    after_amounts = dict(amounts)
    after_energies = dict(energies)
    transferred = 0
    for face in sorted(amounts):
        targets = [neighbor for neighbor, edge in face_sides(face) if neighbor in amounts and edge not in barriers]
        if not targets:
            continue
        share = amounts[face] // law.diffusion_divisor
        if energies[face] > 0:
            share = min(share, (amounts[face] - 1) // len(targets))
        energy_share = energies[face] // law.diffusion_divisor
        if share == 0:
            continue
        for target in targets:
            after_amounts[face] -= share
            after_amounts[target] += share
            after_energies[face] -= energy_share
            after_energies[target] += energy_share
            transferred += share
    physical = _advance_physical(state.physical)
    next_state = NonlivingWorldState(
        physical,
        state.ordinary_events,
        tuple(
            FaceMediumCell(x, y, after_amounts[(x, y)], after_energies[(x, y)])
            for x, y in sorted(after_amounts)
        ),
        state.face_external_energy_exchange,
        diffuse_face_solutes(state.physical, state.face_solutes, law.diffusion_divisor),
    )
    event = WorldEvent.create(physical.time, "sequence.face_medium_diffusion", {
        "medium_transferred": transferred,
        "state_hash": next_state.state_hash(),
    })
    return next_state, event


def _face_absorption_step(state: NonlivingWorldState, law: FaceTransportLaw) -> tuple[NonlivingWorldState, WorldEvent]:
    cells = {cell.face: [cell.amount, cell.energy] for cell in state.face_medium}
    absorbed = 0
    for item in state.physical.locations:
        remaining = law.absorption_per_site
        adjacent = sorted({
            (item.x - 1, item.y - 1), (item.x, item.y - 1),
            (item.x - 1, item.y), (item.x, item.y),
        })
        for face in adjacent:
            if face not in cells or remaining == 0:
                continue
            moved = min(remaining, cells[face][1])
            cells[face][1] -= moved
            remaining -= moved
            absorbed += moved
    physical = _advance_physical(state.physical, absorbed)
    next_state = NonlivingWorldState(
        physical,
        state.ordinary_events,
        tuple(FaceMediumCell(x, y, values[0], values[1]) for (x, y), values in sorted(cells.items())),
        state.face_external_energy_exchange,
        state.face_solutes,
    )
    event = WorldEvent.create(physical.time, "sequence.face_collision_absorption", {
        "absorbed": absorbed,
        "state_hash": next_state.state_hash(),
    })
    return next_state, event


def apply_face_transport_cycle(
    state: NonlivingWorldState,
    law: FaceTransportLaw,
) -> tuple[tuple[NonlivingWorldState, WorldEvent], ...]:
    sourced = _face_source_step(state, law)
    diffused = _face_diffusion_step(sourced[0], law)
    absorbed = _face_absorption_step(diffused[0], law)
    return sourced, diffused, absorbed


@dataclass(frozen=True)
class NonlivingStepResult:
    state: NonlivingWorldState
    events: tuple[WorldEvent, ...]
    random_draw: RandomDraw
    auxiliary_random_draws: tuple[RandomDraw, ...] = ()

    @property
    def all_random_draws(self) -> tuple[RandomDraw, ...]:
        return (*self.auxiliary_random_draws, self.random_draw)


@dataclass(frozen=True)
class NonlivingExperiment:
    initial_state: NonlivingWorldState
    final_state: NonlivingWorldState
    event_counts: tuple[tuple[str, int], ...]
    recorded_events: int
    compartment_frames: int
    compartments_created: int
    compartments_destroyed: int
    compartment_splits: int
    compartment_merges: int
    first_compartment_event: int | None
    max_compartments: int
    cyclic_frames: int
    max_cyclic_strands: int
    cyclization_sizes: tuple[tuple[int, int], ...]
    max_compartment_medium_amount: int
    max_compartment_medium_energy: int


def step_nonliving_world(
    state: NonlivingWorldState,
    chance: ChoiceSource,
    energy_law: SpatialEnergyLaw,
    medium_law: MediumTransportLaw | None = None,
    face_law: FaceTransportLaw | None = None,
    material_law: FaceMaterialLaw | None = None,
    chemistry_law: FaceChemistryLaw | None = None,
    boundary_law: FaceBoundaryLaw | None = None,
) -> NonlivingStepResult:
    """Apply every due environment event and then exactly one ordinary event."""
    physical = state.physical
    events = []
    if state.ordinary_events > 0 and state.ordinary_events % energy_law.interval == 0:
        for result in apply_spatial_energy_cycle(physical, energy_law):
            physical = result.state
            events.append(result.event)
    if (
        medium_law is not None
        and state.ordinary_events > 0
        and state.ordinary_events % medium_law.interval == 0
    ):
        for result in apply_medium_transport_cycle(physical, medium_law):
            physical = result.state
            events.append(result.event)
    working = NonlivingWorldState(
        physical, state.ordinary_events, state.face_medium, state.face_external_energy_exchange, state.face_solutes
    )
    auxiliary_draws: list[RandomDraw] = []
    if (
        face_law is not None
        and state.ordinary_events > 0
        and state.ordinary_events % face_law.interval == 0
    ):
        for working, event in apply_face_transport_cycle(working, face_law):
            events.append(event)
    if (
        chemistry_law is not None
        and state.ordinary_events > 0
        and state.ordinary_events % chemistry_law.interval == 0
    ):
        chemistry = step_face_chemistry(
            working.physical, working.face_solutes, chance, chemistry_law
        )
        if chemistry is not None:
            working = NonlivingWorldState(
                chemistry.physical, working.ordinary_events, working.face_medium,
                working.face_external_energy_exchange, chemistry.face_solutes,
            )
            events.append(chemistry.event)
            auxiliary_draws.append(chemistry.random_draw)
    if (
        material_law is not None
        and state.ordinary_events > 0
        and state.ordinary_events % material_law.interval == 0
    ):
        material = step_face_material(
            working.physical, working.face_medium, working.face_solutes, chance, material_law
        )
        if material is not None:
            working = NonlivingWorldState(
                material.physical, working.ordinary_events, material.face_medium,
                working.face_external_energy_exchange, material.face_solutes,
            )
            events.append(material.event)
            if material.random_draw is not None:
                auxiliary_draws.append(material.random_draw)
    if (
        boundary_law is not None
        and state.ordinary_events > 0
        and state.ordinary_events % boundary_law.interval == 0
    ):
        boundary = step_face_boundary(
            working.physical, working.face_medium, working.face_solutes, chance
        )
        if boundary is not None:
            working = NonlivingWorldState(
                boundary.physical, working.ordinary_events, boundary.face_medium,
                working.face_external_energy_exchange, boundary.face_solutes,
            )
            events.append(boundary.event)
            auxiliary_draws.append(boundary.random_draw)
    ordinary = step_spatial_sequence(working.physical, chance)
    events.append(ordinary.event)
    return NonlivingStepResult(
        NonlivingWorldState(
            ordinary.state,
            state.ordinary_events + 1,
            working.face_medium,
            working.face_external_energy_exchange,
            working.face_solutes,
        ),
        tuple(events),
        ordinary.random_draw,
        tuple(auxiliary_draws),
    )


def run_nonliving_world(
    initial: NonlivingWorldState,
    chance: ChoiceSource,
    energy_law: SpatialEnergyLaw,
    event_limit: int,
    medium_law: MediumTransportLaw | None = None,
    face_law: FaceTransportLaw | None = None,
    material_law: FaceMaterialLaw | None = None,
    chemistry_law: FaceChemistryLaw | None = None,
    boundary_law: FaceBoundaryLaw | None = None,
) -> NonlivingExperiment:
    """Run unassisted physics and audit invariants without selecting for outcomes."""
    if isinstance(event_limit, bool) or not isinstance(event_limit, int) or event_limit < 0:
        raise ValueError("event_limit must be a non-negative integer")
    state = initial
    initial_matter = (
        sum(len(strand.symbols) for strand in state.physical.sequence.strands)
        + sum(cell.amount for cell in state.face_solutes)
    )
    baseline_energy = state.reservoir_adjusted_energy
    initial_medium = sum(cell.amount for cell in state.physical.medium)
    initial_face_medium = sum(cell.amount for cell in state.face_medium)
    initial_solutes = {
        kind: sum(cell.amount for cell in state.face_solutes if cell.kind == kind)
        + sum(strand.symbols.count(kind) for strand in state.physical.sequence.strands)
        for kind in range(4)
    }
    counts: dict[str, int] = {}
    recorded_events = 0
    compartment_frames = 0
    created = 0
    destroyed = 0
    splits = 0
    merges = 0
    first = None
    maximum = 0
    cyclic_frames = 0
    max_cyclic = 0
    cycle_sizes: dict[int, int] = {}
    max_medium_amount = 0
    max_medium_energy = 0
    before = (
        observe_face_compartments(state.physical, state.face_medium)
        if state.face_medium else observe_spatial_compartments(state.physical)
    )
    for event_index in range(1, event_limit + 1):
        result = step_nonliving_world(
            state, chance, energy_law, medium_law, face_law, material_law, chemistry_law
            , boundary_law
        )
        state = result.state
        for event in result.events:
            counts[event.event_type] = counts.get(event.event_type, 0) + 1
            recorded_events += 1
            if event.event_type == "sequence.backbone_cyclize":
                size = int(event.payload()["site_count"])
                cycle_sizes[size] = cycle_sizes.get(size, 0) + 1
        matter = (
            sum(len(strand.symbols) for strand in state.physical.sequence.strands)
            + sum(cell.amount for cell in state.face_solutes)
        )
        if matter != initial_matter:
            raise AssertionError("matter was created or destroyed")
        if sum(cell.amount for cell in state.physical.medium) != initial_medium:
            raise AssertionError("medium matter was created or destroyed")
        if sum(cell.amount for cell in state.face_medium) != initial_face_medium:
            raise AssertionError("face medium matter was created or destroyed")
        if chemistry_law is None and any(
            sum(cell.amount for cell in state.face_solutes if cell.kind == kind)
            + sum(strand.symbols.count(kind) for strand in state.physical.sequence.strands) != amount
            for kind, amount in initial_solutes.items()
        ):
            raise AssertionError("a face solute kind was created or destroyed")
        if state.reservoir_adjusted_energy != baseline_energy:
            raise AssertionError("energy left the explicit reservoir ledger")
        after = (
            observe_face_compartments(state.physical, state.face_medium)
            if state.face_medium else observe_spatial_compartments(state.physical)
        )
        cyclic_count = sum(strand.cyclic for strand in state.physical.sequence.strands)
        if cyclic_count:
            cyclic_frames += 1
            max_cyclic = max(max_cyclic, cyclic_count)
        def compartment_key(item):
            if hasattr(item, "interior_faces"):
                return item.boundary_edges, item.interior_faces
            return item.boundary_sites, item.interior_points

        before_set = {compartment_key(item) for item in before}
        after_set = {compartment_key(item) for item in after}
        created += len(after_set - before_set)
        destroyed += len(before_set - after_set)
        splits += sum(
            len([new for new in after if set(old.interior_faces) & set(new.interior_faces)]) >= 2
            for old in before if hasattr(old, "interior_faces")
        )
        merges += sum(
            len([old for old in before if set(old.interior_faces) & set(new.interior_faces)]) >= 2
            for new in after if hasattr(new, "interior_faces")
        )
        if after:
            compartment_frames += 1
            maximum = max(maximum, len(after))
            max_medium_amount = max(
                max_medium_amount,
                max(item.interior_medium_amount for item in after),
            )
            max_medium_energy = max(
                max_medium_energy,
                max(item.interior_medium_energy for item in after),
            )
            if first is None:
                first = event_index
        before = after
    return NonlivingExperiment(
        initial,
        state,
        tuple(sorted(counts.items())),
        recorded_events,
        compartment_frames,
        created,
        destroyed,
        splits,
        merges,
        first,
        maximum,
        cyclic_frames,
        max_cyclic,
        tuple(sorted(cycle_sizes.items())),
        max_medium_amount,
        max_medium_energy,
    )
