"""Record a minimal context-dependent inheritance demonstration."""

from __future__ import annotations

import json
from pathlib import Path

from engine.sequence import (
    Encounter,
    InheritedContribution,
    apply_encounter,
    assemble_inherited_world,
)


OUTPUT = Path("runs/inherited_context_v1_probe.json")


def _encounter(first_id: int, first_port: int, second_id: int, second_port: int) -> Encounter:
    left, right = sorted(((first_id, first_port), (second_id, second_port)))
    return Encounter(left[0], left[1], right[0], right[1])


def main() -> None:
    contributions = (
        InheritedContribution("first_contribution", (0,)),
        InheritedContribution("second_contribution", (0,)),
        InheritedContribution("local_context", (3,)),
    )
    seed = assemble_inherited_world(contributions, thermal_energy=4)
    first_id = seed.unit_id("first_contribution")
    second_id = seed.unit_id("second_contribution")
    context_id = seed.unit_id("local_context")
    schedule = (
        _encounter(first_id, 0, context_id, 0),
        _encounter(second_id, 0, context_id, 0),
        _encounter(first_id, 0, context_id, 0),
        _encounter(second_id, 0, context_id, 0),
    )

    state = seed.state
    frames = []
    for index, encounter in enumerate(schedule, start=1):
        result = apply_encounter(state, encounter)
        state = result.state
        frames.append(
            {
                "index": index,
                "encounter": {
                    "left_id": encounter.left_id,
                    "left_port": encounter.left_port,
                    "right_id": encounter.right_id,
                    "right_port": encounter.right_port,
                },
                "event": result.event.canonical(),
                "state": state.canonical(),
            }
        )

    record = {
        "format": "inherited-context-probe-v1",
        "initial_state": seed.state.canonical(),
        "observer_only_origins": [
            {
                "local_index": origin.local_index,
                "observer_tag": origin.observer_tag,
                "unit_id": origin.unit_id,
            }
            for origin in seed.origins
        ],
        "frames": frames,
        "outcomes": [frame["event"]["payload"]["outcome"] for frame in frames],
        "final_state": state.canonical(),
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"outcomes": record["outcomes"], "output": str(OUTPUT.resolve())}, indent=2))


if __name__ == "__main__":
    main()
