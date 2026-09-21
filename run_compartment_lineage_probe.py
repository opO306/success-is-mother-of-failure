"""Replay one integrated world for a fixed event count with lineage observation."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from engine.living.events import SeededEventSource
from engine.sequence import (
    CompartmentLineageTracker,
    FaceBoundaryLaw,
    FaceMaterialLaw,
    step_nonliving_world,
)
from run_nonliving_world_probe import chemistry_law, energy_law, face_law, initial_world


def _write(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--events", type=int, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--checkpoint-events", type=int, default=1000)
    args = parser.parse_args()
    if args.events < 0 or args.checkpoint_events <= 0:
        parser.error("events must be non-negative and checkpoint-events positive")

    state = initial_world()
    source = SeededEventSource(args.seed)
    tracker = CompartmentLineageTracker(state)
    baseline_material = (
        sum(len(strand.symbols) for strand in state.physical.sequence.strands)
        + sum(cell.amount for cell in state.face_solutes)
    )
    baseline_medium = sum(cell.amount for cell in state.face_medium)
    baseline_energy = state.reservoir_adjusted_energy
    counts: dict[str, int] = {}
    recorded_events = 0

    def payload(complete: bool, include_lineage: bool) -> dict[str, object]:
        data: dict[str, object] = {
            "complete": complete,
            "event_counts": dict(sorted(counts.items())),
            "event_limit": args.events,
            "final_state_hash": state.state_hash(),
            "lineage_digest": tracker.digest,
            "lineage_event_count": len(tracker.events),
            "material_total": (
                sum(len(strand.symbols) for strand in state.physical.sequence.strands)
                + sum(cell.amount for cell in state.face_solutes)
            ),
            "medium_amount": sum(cell.amount for cell in state.face_medium),
            "ordinary_events": state.ordinary_events,
            "recorded_events": recorded_events,
            "reservoir_adjusted_energy": state.reservoir_adjusted_energy,
            "seed": args.seed,
            "sequence_sites": sum(
                len(strand.symbols) for strand in state.physical.sequence.strands
            ),
            "strand_count": len(state.physical.sequence.strands),
        }
        if include_lineage:
            data["lineage"] = tracker.canonical()
        return data

    for event_index in range(1, args.events + 1):
        before = state
        result = step_nonliving_world(
            state,
            source,
            energy_law(),
            face_law=face_law(),
            material_law=FaceMaterialLaw(interval=2),
            chemistry_law=chemistry_law(),
            boundary_law=FaceBoundaryLaw(interval=4),
        )
        state = result.state
        tracker.observe(event_index, before, state, result.events)
        for event in result.events:
            counts[event.event_type] = counts.get(event.event_type, 0) + 1
            recorded_events += 1
        material = (
            sum(len(strand.symbols) for strand in state.physical.sequence.strands)
            + sum(cell.amount for cell in state.face_solutes)
        )
        if material != baseline_material:
            raise AssertionError("total material changed")
        if sum(cell.amount for cell in state.face_medium) != baseline_medium:
            raise AssertionError("face medium changed")
        if state.reservoir_adjusted_energy != baseline_energy:
            raise AssertionError("energy ledger changed")
        if args.output is not None and event_index % args.checkpoint_events == 0:
            _write(args.output, payload(False, True))

    final = payload(True, args.output is not None)
    if args.output is None:
        print(json.dumps(final, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        _write(args.output, final)


if __name__ == "__main__":
    main()
