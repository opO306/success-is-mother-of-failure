"""Unfiltered seed sweep for template growth in the explicit spatial sequence world."""

from __future__ import annotations

import argparse
import json
from concurrent.futures import ProcessPoolExecutor
from itertools import repeat
from pathlib import Path

from engine.living.events import SeededEventSource
from engine.sequence import (
    SequenceSiteLocation,
    SequenceState,
    SpatialSequenceState,
    Strand,
    observe_spatial_compartments,
    spatial_event_candidates,
    spatial_flex_candidates,
    spatial_rotation_candidates,
    step_spatial_sequence,
)


def initial_world() -> SpatialSequenceState:
    sequence = SequenceState(
        (
            Strand(1, (0, 1, 0, 1)),
            Strand(2, (3, 2)),
            Strand(3, (3, 2)),
        ),
        thermal_energy=16,
    )
    return SpatialSequenceState(sequence, 8, 7, (
        SequenceSiteLocation(1, 0, 2, 1),
        SequenceSiteLocation(1, 1, 2, 2),
        SequenceSiteLocation(1, 2, 2, 3),
        SequenceSiteLocation(1, 3, 2, 4),
        SequenceSiteLocation(2, 0, 3, 1),
        SequenceSiteLocation(2, 1, 3, 2),
        SequenceSiteLocation(3, 0, 3, 3),
        SequenceSiteLocation(3, 1, 3, 4),
    ))


def run_trial(seed: int, event_limit: int) -> dict[str, object]:
    initial = initial_world()
    source = SeededEventSource(seed)
    state = initial
    counts: dict[str, int] = {}
    first_join = None
    join_candidate_frames = 0
    max_join_weight = 0
    join_probability_sum = 0.0
    max_join_probability = 0.0
    join_candidate_outcomes: dict[str, int] = {}
    compartment_frames = 0
    max_compartments = 0
    first_compartment_event = None
    rotation_candidate_frames = 0
    flex_candidate_frames = 0
    for index in range(event_limit):
        joins = [item for item in spatial_event_candidates(state) if item.kind == "join"]
        rotations = spatial_rotation_candidates(state)
        flexes = spatial_flex_candidates(state)
        if rotations:
            rotation_candidate_frames += 1
        if flexes:
            flex_candidate_frames += 1
        if joins:
            join_candidate_frames += 1
            max_join_weight = max(max_join_weight, sum(item.weight for item in joins))
            all_reactions = spatial_event_candidates(state)
            join_weight = sum(item.weight for item in joins)
            total_weight = (
                len(state.locations) * 4
                + len(rotations)
                + len(flexes)
                + sum(item.weight for item in all_reactions)
            )
            probability = join_weight / total_weight
            join_probability_sum += probability
            max_join_probability = max(max_join_probability, probability)
        result = step_spatial_sequence(state, source)
        if joins:
            after_has_join = any(item.kind == "join" for item in spatial_event_candidates(result.state))
            if result.event.event_type == "sequence.backbone_join":
                outcome = "selected_join"
            elif after_has_join:
                outcome = f"persisted_after_{result.event.event_type.removeprefix('sequence.')}"
            else:
                outcome = f"lost_after_{result.event.event_type.removeprefix('sequence.')}"
            join_candidate_outcomes[outcome] = join_candidate_outcomes.get(outcome, 0) + 1
        state = result.state
        compartments = observe_spatial_compartments(state)
        if compartments:
            compartment_frames += 1
            max_compartments = max(max_compartments, len(compartments))
            if first_compartment_event is None:
                first_compartment_event = index + 1
        kind = result.event.event_type
        counts[kind] = counts.get(kind, 0) + 1
        if kind == "sequence.backbone_join" and first_join is None:
            first_join = index + 1
        if state.reservoir_adjusted_energy != initial.reservoir_adjusted_energy:
            raise AssertionError("reservoir-adjusted energy changed during a spatial sequence run")
        if sum(len(item.symbols) for item in state.sequence.strands) != 8:
            raise AssertionError("sequence matter was created or destroyed")
    return {
        "event_counts": dict(sorted(counts.items())),
        "compartment_frames": compartment_frames,
        "final_hash": state.state_hash(),
        "flex_candidate_frames": flex_candidate_frames,
        "first_compartment_event": first_compartment_event,
        "first_join_event": first_join,
        "join_candidate_frames": join_candidate_frames,
        "join_candidate_outcomes": dict(sorted(join_candidate_outcomes.items())),
        "join_probability_sum": join_probability_sum,
        "max_join_weight": max_join_weight,
        "max_join_probability": max_join_probability,
        "max_compartments": max_compartments,
        "rotation_candidate_frames": rotation_candidate_frames,
        "seed": seed,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=int, default=64)
    parser.add_argument("--events", type=int, default=1000)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--workers", type=int, default=1)
    args = parser.parse_args()
    if args.seeds <= 0 or args.events < 0 or args.workers <= 0:
        parser.error("seeds and workers must be positive and events non-negative")
    if args.workers == 1:
        trials = [run_trial(seed, args.events) for seed in range(args.seeds)]
    else:
        with ProcessPoolExecutor(max_workers=args.workers) as executor:
            trials = list(executor.map(run_trial, range(args.seeds), repeat(args.events)))
    result = {
        "event_limit": args.events,
        "seeds": args.seeds,
        "trials": trials,
    }
    rendered = json.dumps(result, indent=2, sort_keys=True)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)


if __name__ == "__main__":
    main()
