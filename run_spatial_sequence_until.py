"""Run one spatial-sequence world untouched until a wall-clock deadline."""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from engine.living.events import SeededEventSource
from engine.sequence import step_spatial_sequence
from run_spatial_sequence_probe import initial_world


def _write(path: Path, payload: dict[str, object]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--until", required=True, help="ISO-8601 deadline with timezone")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--checkpoint-events", type=int, default=10000)
    args = parser.parse_args()
    deadline = datetime.fromisoformat(args.until)
    if deadline.tzinfo is None or args.checkpoint_events <= 0:
        parser.error("deadline needs a timezone and checkpoint-events must be positive")
    deadline_timestamp = deadline.timestamp()
    args.output.parent.mkdir(parents=True, exist_ok=True)

    seed = args.seed
    source = SeededEventSource(seed)
    state = initial_world()
    initial_energy = state.reservoir_adjusted_energy
    initial_matter = sum(len(strand.symbols) for strand in state.sequence.strands)
    events = 0
    restarts = 0
    counts: dict[str, int] = {}
    started = datetime.now(timezone.utc)

    while time.time() < deadline_timestamp:
        matter = sum(len(strand.symbols) for strand in state.sequence.strands)
        if matter == 0:
            restarts += 1
            seed += 1
            source = SeededEventSource(seed)
            state = initial_world()
            initial_energy = state.reservoir_adjusted_energy
            initial_matter = sum(len(strand.symbols) for strand in state.sequence.strands)
            continue
        result = step_spatial_sequence(state, source)
        state = result.state
        events += 1
        kind = result.event.event_type
        counts[kind] = counts.get(kind, 0) + 1
        if state.reservoir_adjusted_energy != initial_energy:
            raise AssertionError("reservoir-adjusted energy changed")
        if sum(len(strand.symbols) for strand in state.sequence.strands) != initial_matter:
            raise AssertionError("matter was created or destroyed")
        if events % args.checkpoint_events == 0:
            _write(args.output, {
                "complete": False,
                "current_seed": seed,
                "deadline": args.until,
                "event_counts": dict(sorted(counts.items())),
                "events": events,
                "final_state_hash": state.state_hash(),
                "restarts_after_empty_world": restarts,
                "started_utc": started.isoformat(),
                "updated_utc": datetime.now(timezone.utc).isoformat(),
            })

    _write(args.output, {
        "complete": True,
        "current_seed": seed,
        "deadline": args.until,
        "event_counts": dict(sorted(counts.items())),
        "events": events,
        "final_state_hash": state.state_hash(),
        "restarts_after_empty_world": restarts,
        "started_utc": started.isoformat(),
        "stopped_utc": datetime.now(timezone.utc).isoformat(),
    })


if __name__ == "__main__":
    main()
