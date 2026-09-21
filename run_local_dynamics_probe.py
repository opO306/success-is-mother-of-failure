"""Run and fully record the first universal-collision dynamics probe."""

from __future__ import annotations

import gzip
import io
import json
from collections import Counter
from dataclasses import asdict
from pathlib import Path

from engine.living.events import SeededEventSource
from engine.sequence import LocalDynamicsState, MatterUnit, run_local_experiment


OUTPUT = Path("runs/local_dynamics_v1_probe.jsonl.gz")


def _maximum_degree(state: LocalDynamicsState) -> int:
    degree: Counter[int] = Counter()
    for bond in state.bonds:
        degree[bond.left_id] += 1
        degree[bond.right_id] += 1
    return max(degree.values(), default=0)


def main() -> None:
    initial = LocalDynamicsState(
        tuple(MatterUnit(unit_id, (unit_id - 1) % 4) for unit_id in range(1, 9)),
        thermal_energy=8,
    )
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    summaries = []
    with OUTPUT.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            with io.TextIOWrapper(compressed, encoding="utf-8", newline="\n") as handle:
                for seed in (0, 1):
                    experiment = run_local_experiment(initial, SeededEventSource(seed), 10_000)
                    outcomes = Counter(frame.event.payload()["outcome"] for frame in experiment.frames)
                    maximum_bonds = max((len(frame.state.bonds) for frame in experiment.frames), default=0)
                    maximum_degree = max(
                        (_maximum_degree(frame.state) for frame in experiment.frames),
                        default=0,
                    )
                    topologies = {
                        tuple(
                            (bond.left_id, bond.left_port, bond.right_id, bond.right_port)
                            for bond in frame.state.bonds
                        )
                        for frame in experiment.frames
                    }
                    record = {
                        "seed": seed,
                        "initial_state": initial.canonical(),
                        "stop_reason": experiment.stop_reason,
                        "frames": [
                            {
                                "index": frame.index,
                                "random_draw": asdict(frame.random_draw),
                                "event": frame.event.canonical(),
                                "state": frame.state.canonical(),
                            }
                            for frame in experiment.frames
                        ],
                    }
                    handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
                    handle.write("\n")
                    summaries.append(
                        {
                            "seed": seed,
                            "outcomes": dict(sorted(outcomes.items())),
                            "final_bonds": len(experiment.final_state.bonds),
                            "maximum_final_degree": _maximum_degree(experiment.final_state),
                            "maximum_bonds": maximum_bonds,
                            "maximum_degree": maximum_degree,
                            "distinct_bond_topologies": len(topologies),
                            "final_total_energy": experiment.final_state.total_energy,
                        }
                    )
    print(json.dumps({"trials": summaries, "output": str(OUTPUT.resolve())}, indent=2))


if __name__ == "__main__":
    main()
