"""Run one selective face-transport world until an exact wall-clock deadline."""
from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from engine.living.events import SeededEventSource
from engine.sequence import (
    CompartmentLineageTracker,
    ExperimentObserver,
    FaceBoundaryLaw,
    FaceMaterialLaw,
    observe_face_compartments,
    step_nonliving_world,
)
from run_nonliving_world_probe import chemistry_law, energy_law, face_law, initial_world


def _write(path: Path, payload: dict[str, object]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--until", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--checkpoint-events", type=int, default=1000)
    parser.add_argument("--lineage-output", type=Path)
    parser.add_argument("--lineage-checkpoint-events", type=int, default=10000)
    parser.add_argument("--observer-output", type=Path)
    parser.add_argument("--observer-checkpoint-events", type=int, default=10000)
    parser.add_argument("--observer-census-events", type=int, default=10000)
    parser.add_argument("--observer-ring-events", type=int, default=20000)
    parser.add_argument("--observer-post-trigger-events", type=int, default=20000)
    args = parser.parse_args()
    deadline = datetime.fromisoformat(args.until)
    if (
        deadline.tzinfo is None
        or args.checkpoint_events <= 0
        or args.lineage_checkpoint_events <= 0
        or args.observer_checkpoint_events <= 0
        or args.observer_census_events <= 0
        or args.observer_ring_events <= 0
        or args.observer_post_trigger_events < 0
    ):
        parser.error("deadline needs timezone and checkpoint intervals must be positive")
    outputs = [item for item in (args.output, args.lineage_output, args.observer_output) if item is not None]
    if len(set(outputs)) != len(outputs):
        parser.error("output, lineage-output, and observer-output must differ")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    for optional_output in (args.lineage_output, args.observer_output):
        if optional_output is not None:
            optional_output.parent.mkdir(parents=True, exist_ok=True)
    state = initial_world()
    source = SeededEventSource(args.seed)
    baseline_energy = state.reservoir_adjusted_energy
    baseline_matter = (
        sum(len(strand.symbols) for strand in state.physical.sequence.strands)
        + sum(cell.amount for cell in state.face_solutes)
    )
    baseline_medium = sum(cell.amount for cell in state.face_medium)
    counts: dict[str, int] = {}
    ordinary = recorded = compartment_frames = created = destroyed = 0
    splits = merges = 0
    max_compartments = 0
    max_trapped = {kind: 0 for kind in range(4)}
    started = datetime.now(timezone.utc)
    before = observe_face_compartments(state.physical, state.face_medium)
    experiment_chemistry_law = chemistry_law()
    observer = (
        ExperimentObserver(
            state,
            chemistry_law=experiment_chemistry_law,
            census_interval=args.observer_census_events,
            ring_event_limit=args.observer_ring_events,
            post_trigger_steps=args.observer_post_trigger_events,
        )
        if args.observer_output is not None else None
    )
    tracker = (
        observer.lineage if observer is not None
        else CompartmentLineageTracker(state) if args.lineage_output is not None
        else None
    )

    def key(item):
        return item.boundary_edges, item.interior_faces

    def payload(complete: bool) -> dict[str, object]:
        data = {
            "complete": complete,
            "compartment_frames": compartment_frames,
            "compartments_created": created,
            "compartments_destroyed": destroyed,
            "compartment_splits": splits,
            "compartment_merges": merges,
            "deadline": args.until,
            "event_counts": dict(sorted(counts.items())),
            "face_external_energy_exchange": state.face_external_energy_exchange,
            "final_state_hash": state.state_hash(),
            "max_compartments": max_compartments,
            "max_trapped_solute_by_kind": {str(k): v for k, v in max_trapped.items()},
            "medium_amount": sum(cell.amount for cell in state.face_medium),
            "material_total": (
                sum(len(strand.symbols) for strand in state.physical.sequence.strands)
                + sum(cell.amount for cell in state.face_solutes)
            ),
            "ordinary_events": ordinary,
            "recorded_events": recorded,
            "reservoir_adjusted_energy": state.reservoir_adjusted_energy,
            "seed": args.seed,
            "solute_totals": {
                str(kind): sum(cell.amount for cell in state.face_solutes if cell.kind == kind)
                for kind in range(4)
            },
            "sequence_kind_totals": {
                str(kind): sum(strand.symbols.count(kind) for strand in state.physical.sequence.strands)
                for kind in range(4)
            },
            "sequence_sites": sum(len(strand.symbols) for strand in state.physical.sequence.strands),
            "strand_count": len(state.physical.sequence.strands),
            "started_utc": started.isoformat(),
        }
        if tracker is not None:
            data["lineage_digest"] = tracker.digest
            data["lineage_event_count"] = len(tracker.events)
        if observer is not None:
            observer_report = observer.canonical() if complete else observer.checkpoint_canonical()
            data["observer_digest"] = observer_report["digest"]
            data["observer_integrity_violations"] = len(observer_report["integrity_violations"])
        data["stopped_utc" if complete else "updated_utc"] = datetime.now(timezone.utc).isoformat()
        return data

    while time.time() < deadline.timestamp():
        previous_state = state
        result = step_nonliving_world(
            state, source, energy_law(), face_law=face_law(),
            material_law=FaceMaterialLaw(interval=2), chemistry_law=experiment_chemistry_law,
            boundary_law=FaceBoundaryLaw(interval=4),
        )
        state = result.state
        ordinary += 1
        for event in result.events:
            counts[event.event_type] = counts.get(event.event_type, 0) + 1
            recorded += 1
        if (
            sum(len(strand.symbols) for strand in state.physical.sequence.strands)
            + sum(cell.amount for cell in state.face_solutes)
        ) != baseline_matter:
            raise AssertionError("total material changed")
        if sum(cell.amount for cell in state.face_medium) != baseline_medium:
            raise AssertionError("face medium changed")
        if state.reservoir_adjusted_energy != baseline_energy:
            raise AssertionError("energy ledger changed")
        after = observe_face_compartments(state.physical, state.face_medium)
        if observer is not None:
            observer.observe(
                ordinary,
                previous_state,
                state,
                result.events,
                before_observations=before,
                after_observations=after,
            )
        elif tracker is not None:
            tracker.observe(
                ordinary,
                previous_state,
                state,
                result.events,
                before_observations=before,
                after_observations=after,
            )
        before_keys, after_keys = {key(item) for item in before}, {key(item) for item in after}
        created += len(after_keys - before_keys)
        destroyed += len(before_keys - after_keys)
        splits += sum(
            len([new for new in after if set(old.interior_faces) & set(new.interior_faces)]) >= 2
            for old in before
        )
        merges += sum(
            len([old for old in before if set(old.interior_faces) & set(new.interior_faces)]) >= 2
            for new in after
        )
        if after:
            compartment_frames += 1
            max_compartments = max(max_compartments, len(after))
            solute_at = {(cell.face, cell.kind): cell.amount for cell in state.face_solutes}
            for compartment in after:
                for kind in range(4):
                    trapped = sum(solute_at.get((face, kind), 0) for face in compartment.interior_faces)
                    max_trapped[kind] = max(max_trapped[kind], trapped)
        before = after
        if observer is not None and ordinary % args.observer_checkpoint_events == 0:
            observer.checkpoint(ordinary, state, source.draw_count)
            if args.observer_output is not None:
                _write(args.observer_output, {
                    "complete": False,
                    "ordinary_events": ordinary,
                    "seed": args.seed,
                    **observer.checkpoint_canonical(),
                })
        if ordinary % args.checkpoint_events == 0:
            _write(args.output, payload(False))
        if (
            tracker is not None
            and ordinary % args.lineage_checkpoint_events == 0
            and args.lineage_output is not None
        ):
            _write(args.lineage_output, {
                "complete": False,
                "ordinary_events": ordinary,
                "seed": args.seed,
                **tracker.canonical(),
            })
    if observer is not None:
        observer.checkpoint(ordinary, state, source.draw_count)
        if args.observer_output is not None:
            _write(args.observer_output, {
                "complete": True,
                "ordinary_events": ordinary,
                "seed": args.seed,
                **observer.canonical(),
            })
    _write(args.output, payload(True))
    if tracker is not None and args.lineage_output is not None:
        _write(args.lineage_output, {
            "complete": True,
            "ordinary_events": ordinary,
            "seed": args.seed,
            **tracker.canonical(),
        })


if __name__ == "__main__":
    main()
