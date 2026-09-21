"""Record unbiased grid movement across a membrane with one physical gap."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict
from pathlib import Path

from engine.living.events import SeededEventSource
from engine.sequence import (
    GridBarrier,
    GridLocation,
    LocalDynamicsState,
    MatterUnit,
    SpatialState,
    step_spatial_movement,
    unit_ids_in_box,
)


OUTPUT = Path("runs/spatial_boundary_v1_probe.json")
STEPS = 1_000
SEED = 17


def _inside(state: SpatialState) -> set[int]:
    return set(unit_ids_in_box(state, 3, 0, 4, 2))


def main() -> None:
    local = LocalDynamicsState(tuple(MatterUnit(unit_id, unit_id - 1) for unit_id in range(1, 5)), 4)
    state = SpatialState(
        local,
        width=5,
        height=3,
        locations=(
            GridLocation(1, 0, 0),
            GridLocation(2, 0, 1),
            GridLocation(3, 1, 0),
            GridLocation(4, 1, 2),
        ),
        barriers=(GridBarrier(2, 0, 3, 0), GridBarrier(2, 2, 3, 2)),
    )
    initial = state
    chance = SeededEventSource(SEED)
    frames = []
    transitions = []
    outcomes: Counter[str] = Counter()
    ever_inside: set[int] = set(_inside(state))
    for index in range(1, STEPS + 1):
        before = _inside(state)
        result = step_spatial_movement(state, chance)
        state = result.state
        after = _inside(state)
        entered = sorted(after - before)
        exited = sorted(before - after)
        ever_inside.update(after)
        outcome = str(result.event.payload()["outcome"])
        outcomes[outcome] += 1
        if entered or exited:
            payload = result.event.payload()
            transitions.append(
                {
                    "index": index,
                    "entered": entered,
                    "exited": exited,
                    "from": payload["from"],
                    "to": payload["to"],
                }
            )
        frames.append(
            {
                "index": index,
                "random_draw": asdict(result.random_draw),
                "event": result.event.canonical(),
                "state": state.canonical(),
            }
        )
    record = {
        "format": "spatial-boundary-probe-v1",
        "seed": SEED,
        "steps": STEPS,
        "initial_state": initial.canonical(),
        "frames": frames,
        "outcomes": dict(sorted(outcomes.items())),
        "chamber_transitions": transitions,
        "ever_inside_observer_box": sorted(ever_inside),
        "final_inside_observer_box": sorted(_inside(state)),
        "final_state": state.canonical(),
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(record, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "outcomes": record["outcomes"],
                "transitions": len(transitions),
                "ever_inside": record["ever_inside_observer_box"],
                "final_inside": record["final_inside_observer_box"],
                "output": str(OUTPUT.resolve()),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
