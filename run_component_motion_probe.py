"""Compare component shapes crossing the same one-cell membrane gap."""

from __future__ import annotations

import json
from pathlib import Path

from engine.sequence import (
    GridBarrier,
    GridLocation,
    LocalDynamicsState,
    MatterUnit,
    MoveAttempt,
    PortBond,
    SpatialState,
    apply_component_move,
    unit_ids_in_box,
)


OUTPUT = Path("runs/component_motion_v1_probe.json")
BARRIERS = (GridBarrier(2, 0, 3, 0), GridBarrier(2, 2, 3, 2))


def _record(name: str, initial: SpatialState, attempts: tuple[MoveAttempt, ...]) -> dict[str, object]:
    state = initial
    frames = []
    for index, attempt in enumerate(attempts, start=1):
        result = apply_component_move(state, attempt)
        state = result.state
        frames.append(
            {
                "index": index,
                "attempt": {"unit_id": attempt.unit_id, "dx": attempt.dx, "dy": attempt.dy},
                "event": result.event.canonical(),
                "state": state.canonical(),
                "inside_observer_box": list(unit_ids_in_box(state, 3, 0, 4, 2)),
            }
        )
    return {
        "name": name,
        "initial_state": initial.canonical(),
        "frames": frames,
        "final_inside_observer_box": list(unit_ids_in_box(state, 3, 0, 4, 2)),
    }


def main() -> None:
    single = SpatialState(
        LocalDynamicsState((MatterUnit(1, 0),), 4),
        5,
        3,
        (GridLocation(1, 2, 1),),
        BARRIERS,
    )
    vertical = SpatialState(
        LocalDynamicsState(
            (MatterUnit(1, 0), MatterUnit(2, 3)),
            4,
            (PortBond(1, 0, 2, 0, 2),),
        ),
        5,
        3,
        (GridLocation(1, 2, 0), GridLocation(2, 2, 1)),
        BARRIERS,
    )
    horizontal = SpatialState(
        LocalDynamicsState(
            (MatterUnit(1, 0), MatterUnit(2, 3)),
            4,
            (PortBond(1, 0, 2, 0, 2),),
        ),
        5,
        3,
        (GridLocation(1, 1, 1), GridLocation(2, 2, 1)),
        BARRIERS,
    )
    trials = [
        _record("single", single, (MoveAttempt(1, 1, 0),)),
        _record("vertical_dimer", vertical, (MoveAttempt(1, 1, 0),)),
        _record(
            "horizontal_dimer",
            horizontal,
            (MoveAttempt(1, 1, 0), MoveAttempt(2, 1, 0)),
        ),
    ]
    record = {"format": "component-motion-probe-v1", "trials": trials}
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                trial["name"]: {
                    "outcomes": [frame["event"]["payload"]["outcome"] for frame in trial["frames"]],
                    "final_inside": trial["final_inside_observer_box"],
                }
                for trial in trials
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
