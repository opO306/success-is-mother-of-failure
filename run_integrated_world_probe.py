"""Run an unfiltered seed sweep of the integrated spatial matter world."""

from __future__ import annotations

import argparse
import json

from engine.living.events import SeededEventSource
from engine.sequence import (
    GridLocation,
    LocalDynamicsState,
    MatterUnit,
    PortBond,
    SpatialState,
    run_integrated_world,
)


def initial_world(closed: bool) -> SpatialState:
    ring_points = ((3, 3), (4, 3), (5, 3), (5, 4), (5, 5), (4, 5), (3, 5), (3, 4))
    free_points = ((1, 1), (2, 1), (7, 1), (8, 2), (1, 7), (2, 8), (7, 7), (8, 8))
    points = (*ring_points, *free_points)
    locations = tuple(GridLocation(index, *point) for index, point in enumerate(points, 1))
    units = tuple(MatterUnit(index, (index + 1) % 2 * 3) for index in range(1, len(points) + 1))
    edges = [(1, 2), (2, 3), (3, 4), (4, 5), (5, 6), (6, 7), (7, 8)]
    if closed:
        edges.append((1, 8))
    bonds = []
    for left, right in edges:
        if (left, right) == (1, 8):
            bonds.append(PortBond(1, 0, 8, 1, 2))
        else:
            bonds.append(PortBond(left, 1, right, 0, 2))
    return SpatialState(LocalDynamicsState(units, 40, tuple(bonds)), 10, 10, locations)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=int, default=16)
    parser.add_argument("--events", type=int, default=2000)
    args = parser.parse_args()
    if args.seeds <= 0 or args.events < 0:
        parser.error("seeds must be positive and events non-negative")
    trials = []
    for closed in (False, True):
        for seed in range(args.seeds):
            experiment = run_integrated_world(initial_world(closed), SeededEventSource(seed), args.events)
            counts = [len(frame.compartments) for frame in experiment.frames]
            present = [count > 0 for count in counts]
            formations = sum(now and not before for before, now in zip([closed, *present[:-1]], present))
            losses = sum(before and not now for before, now in zip([closed, *present[:-1]], present))
            trials.append({
                "initially_closed": closed,
                "seed": seed,
                "formations": formations,
                "losses": losses,
                "max_compartments": max(counts, default=int(closed)),
                "closed_frames": sum(present),
                "final_hash": experiment.final_state.state_hash(),
            })
    print(json.dumps({"events": args.events, "seeds_per_condition": args.seeds, "trials": trials}, indent=2))


if __name__ == "__main__":
    main()
