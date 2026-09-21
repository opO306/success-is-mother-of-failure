"""Multi-seed probe of the integrated nonliving matter world."""
from __future__ import annotations

import argparse
import json
from concurrent.futures import ProcessPoolExecutor
from itertools import repeat
from pathlib import Path

from engine.living.events import SeededEventSource
from engine.sequence import (
    EnergySource,
    FaceEnergySource,
    FaceChemistryLaw,
    FaceBoundaryLaw,
    FaceMaterialLaw,
    FaceMediumCell,
    FaceSoluteCell,
    FaceTransportLaw,
    FaceReaction,
    NonlivingWorldState,
    SequenceSiteLocation,
    SequenceState,
    SpatialEnergyLaw,
    SpatialSequenceState,
    Strand,
    run_nonliving_world,
)


def initial_world() -> NonlivingWorldState:
    patterns = (
        (0, 1, 2, 3, 0, 1, 2, 3),
        (3, 2, 1, 0, 3, 2, 1, 0),
        (0, 2, 1, 3, 2, 0, 3, 1),
        (1, 3, 0, 2, 3, 1, 2, 0),
    )
    strands = [Strand(index + 1, symbols) for index, symbols in enumerate(patterns)]
    locations = []
    for index in range(8):
        locations.append(SequenceSiteLocation(1, index, 2 + index, 2))
        locations.append(SequenceSiteLocation(2, index, 2 + index, 6))
        locations.append(SequenceSiteLocation(3, index, 12, 2 + index))
        locations.append(SequenceSiteLocation(4, index, 16, 2 + index))
    free_points = ((2, 12), (4, 14), (7, 11), (9, 15), (12, 13), (14, 15), (16, 12), (6, 16))
    for offset, point in enumerate(free_points):
        strand_id = 5 + offset
        strands.append(Strand(strand_id, (offset % 4,)))
        locations.append(SequenceSiteLocation(strand_id, 0, *point))
    face_medium = tuple(
        FaceMediumCell(x, y, 16, 4 if x < 3 and y < 3 else 0)
        for y in range(18)
        for x in range(19)
    )
    physical = SpatialSequenceState(
        SequenceState(tuple(strands), thermal_energy=96),
        20,
        19,
        tuple(locations),
    )
    face_solutes = []
    for y in range(18):
        for x in range(19):
            if x < 6:
                face_solutes.append(FaceSoluteCell(x, y, 0, 8))
            if x >= 13:
                face_solutes.append(FaceSoluteCell(x, y, 1, 8))
            if y < 6:
                face_solutes.append(FaceSoluteCell(x, y, 2, 8))
            if y >= 12:
                face_solutes.append(FaceSoluteCell(x, y, 3, 8))
    return NonlivingWorldState(physical, face_medium=face_medium, face_solutes=tuple(face_solutes))


def energy_law() -> SpatialEnergyLaw:
    return SpatialEnergyLaw(
        1000000,
        (EnergySource(0, 0, 8), EnergySource(19, 18, -8)),
        diffusion_divisor=8,
        absorption_per_site=1,
    )


def face_law() -> FaceTransportLaw:
    return FaceTransportLaw(
        20,
        (FaceEnergySource(0, 0, 8), FaceEnergySource(18, 17, -8)),
        diffusion_divisor=8,
        absorption_per_site=1,
    )


def chemistry_law() -> FaceChemistryLaw:
    """Two reversible anonymous exchanges; signatures affect rate, never legality."""
    return FaceChemistryLaw(3, (
        FaceReaction((1, 1, 0, 0), (0, 0, 1, 1), (2, 3)),
        FaceReaction((0, 0, 1, 1), (1, 1, 0, 0), (0, 1)),
        FaceReaction((1, 0, 1, 0), (0, 1, 0, 1), (1, 3)),
        FaceReaction((0, 1, 0, 1), (1, 0, 1, 0), (0, 2)),
    ))


def run_trial(seed: int, events: int, material_cycle: bool = False) -> dict[str, object]:
    experiment = run_nonliving_world(
        initial_world(), SeededEventSource(seed), energy_law(), events, face_law=face_law(),
        material_law=FaceMaterialLaw(interval=2) if material_cycle else None,
        chemistry_law=chemistry_law() if material_cycle else None,
        boundary_law=FaceBoundaryLaw(interval=4) if material_cycle else None,
    )
    physical = experiment.final_state.physical
    return {
        "compartment_frames": experiment.compartment_frames,
        "compartments_created": experiment.compartments_created,
        "compartments_destroyed": experiment.compartments_destroyed,
        "compartment_splits": experiment.compartment_splits,
        "compartment_merges": experiment.compartment_merges,
        "cyclic_strands": sum(strand.cyclic for strand in physical.sequence.strands),
        "cyclic_frames": experiment.cyclic_frames,
        "cyclization_sizes": dict(experiment.cyclization_sizes),
        "event_counts": dict(experiment.event_counts),
        "external_energy_exchange": physical.external_energy_exchange,
        "face_external_energy_exchange": experiment.final_state.face_external_energy_exchange,
        "field_energy": sum(cell.amount for cell in physical.field_energy),
        "final_state_hash": experiment.final_state.state_hash(),
        "first_compartment_event": experiment.first_compartment_event,
        "max_compartments": experiment.max_compartments,
        "max_cyclic_strands": experiment.max_cyclic_strands,
        "max_compartment_medium_amount": experiment.max_compartment_medium_amount,
        "max_compartment_medium_energy": experiment.max_compartment_medium_energy,
        "medium_amount": sum(cell.amount for cell in experiment.final_state.face_medium),
        "medium_energy": sum(cell.energy for cell in experiment.final_state.face_medium),
        "solute_totals": {
            str(kind): sum(cell.amount for cell in experiment.final_state.face_solutes if cell.kind == kind)
            for kind in range(4)
        },
        "material_totals": {
            str(kind): sum(cell.amount for cell in experiment.final_state.face_solutes if cell.kind == kind)
            + sum(strand.symbols.count(kind) for strand in physical.sequence.strands)
            for kind in range(4)
        },
        "recorded_events": experiment.recorded_events,
        "reservoir_adjusted_energy": experiment.final_state.reservoir_adjusted_energy,
        "seed": seed,
        "strand_count": len(physical.sequence.strands),
        "thermal_energy": physical.sequence.thermal_energy,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=int, default=8)
    parser.add_argument("--events", type=int, default=10000)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--material-cycle", action="store_true")
    args = parser.parse_args()
    if args.seeds <= 0 or args.events < 0 or args.workers <= 0:
        parser.error("seeds and workers must be positive and events non-negative")
    if args.workers == 1:
        trials = [run_trial(seed, args.events, args.material_cycle) for seed in range(args.seeds)]
    else:
        with ProcessPoolExecutor(max_workers=args.workers) as executor:
            trials = list(executor.map(
                run_trial, range(args.seeds), repeat(args.events), repeat(args.material_cycle)
            ))
    rendered = json.dumps({"events": args.events, "seeds": args.seeds, "trials": trials}, indent=2, sort_keys=True)
    if args.output is None:
        print(rendered)
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
