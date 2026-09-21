"""Replay every collision in the first local-dynamics probe."""

from __future__ import annotations

import gzip
import json

from engine.living.events import RandomDraw, ReplayEventSource
from engine.sequence import LocalDynamicsState, MatterUnit, PortBond, run_local_experiment


def _state(raw: dict) -> LocalDynamicsState:
    return LocalDynamicsState(
        tuple(MatterUnit(item["unit_id"], item["symbol"]) for item in raw["units"]),
        raw["thermal_energy"],
        tuple(
            PortBond(
                item["left_id"],
                item["left_port"],
                item["right_id"],
                item["right_port"],
                item["strength"],
            )
            for item in raw["bonds"]
        ),
        raw["time"],
    )


def main() -> None:
    verified = 0
    with gzip.open("runs/local_dynamics_v1_probe.jsonl.gz", "rt", encoding="utf-8") as handle:
        for line in handle:
            raw = json.loads(line)
            draws = tuple(
                RandomDraw(
                    item["random_draw"]["index"],
                    item["random_draw"]["operation"],
                    tuple(item["random_draw"]["arguments"]),
                    item["random_draw"]["result"],
                )
                for item in raw["frames"]
            )
            replayed = run_local_experiment(
                _state(raw["initial_state"]),
                ReplayEventSource(draws),
                len(raw["frames"]),
            )
            for expected, actual in zip(raw["frames"], replayed.frames, strict=True):
                if expected["event"] != actual.event.canonical() or expected["state"] != actual.state.canonical():
                    raise SystemExit(f"replay divergence in seed {raw['seed']} at frame {actual.index}")
            verified += 1
    print(json.dumps({"trials_verified": verified}, indent=2))


if __name__ == "__main__":
    main()
