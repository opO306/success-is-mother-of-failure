"""Run one spatial sequence world with a fully recorded spatial energy field."""
from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from engine.living.events import SeededEventSource
from engine.sequence import (
    EnergySource,
    SpatialEnergyLaw,
    apply_spatial_energy_cycle,
    step_spatial_sequence,
)
from run_spatial_sequence_probe import initial_world


def _write(path: Path, payload: dict[str, object]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _record(counts: dict[str, int], event_type: str) -> None:
    counts[event_type] = counts.get(event_type, 0) + 1


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--until", required=True, help="ISO-8601 deadline with timezone")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--checkpoint-events", type=int, default=100000)
    parser.add_argument("--energy-interval", type=int, default=10000)
    args = parser.parse_args()
    deadline = datetime.fromisoformat(args.until)
    if deadline.tzinfo is None or args.checkpoint_events <= 0 or args.energy_interval <= 0:
        parser.error("deadline needs a timezone and intervals must be positive")
    deadline_timestamp = deadline.timestamp()
    args.output.parent.mkdir(parents=True, exist_ok=True)

    source = SeededEventSource(args.seed)
    state = initial_world()
    law = SpatialEnergyLaw(
        args.energy_interval,
        (EnergySource(0, 0, 4), EnergySource(state.width - 1, state.height - 1, -4)),
        diffusion_divisor=8,
        absorption_per_site=1,
    )
    baseline_adjusted_energy = state.reservoir_adjusted_energy
    initial_matter = sum(len(strand.symbols) for strand in state.sequence.strands)
    ordinary_events = 0
    total_recorded_events = 0
    energy_cycles = 0
    counts: dict[str, int] = {}
    started = datetime.now(timezone.utc)

    def payload(complete: bool) -> dict[str, object]:
        data: dict[str, object] = {
            "complete": complete,
            "deadline": args.until,
            "energy_cycles": energy_cycles,
            "energy_interval": args.energy_interval,
            "event_counts": dict(sorted(counts.items())),
            "external_energy_exchange": state.external_energy_exchange,
            "field_energy": sum(cell.amount for cell in state.field_energy),
            "final_state_hash": state.state_hash(),
            "ordinary_events": ordinary_events,
            "reservoir_adjusted_energy": state.reservoir_adjusted_energy,
            "seed": args.seed,
            "started_utc": started.isoformat(),
            "thermal_energy": state.sequence.thermal_energy,
            "total_recorded_events": total_recorded_events,
        }
        data["stopped_utc" if complete else "updated_utc"] = datetime.now(timezone.utc).isoformat()
        return data

    while time.time() < deadline_timestamp:
        if ordinary_events > 0 and ordinary_events % law.interval == 0:
            cycle = apply_spatial_energy_cycle(state, law)
            for result in cycle:
                state = result.state
                total_recorded_events += 1
                _record(counts, result.event.event_type)
            energy_cycles += 1
        result = step_spatial_sequence(state, source)
        state = result.state
        ordinary_events += 1
        total_recorded_events += 1
        _record(counts, result.event.event_type)

        if state.reservoir_adjusted_energy != baseline_adjusted_energy:
            raise AssertionError("energy changed outside the explicit reservoir ledger")
        if sum(len(strand.symbols) for strand in state.sequence.strands) != initial_matter:
            raise AssertionError("matter was created or destroyed")
        if ordinary_events % args.checkpoint_events == 0:
            _write(args.output, payload(False))

    _write(args.output, payload(True))


if __name__ == "__main__":
    main()
