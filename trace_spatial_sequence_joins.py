"""Replay selected spatial-sequence seeds and track exact joined strand identities."""

from __future__ import annotations

import argparse
import json

from engine.living.events import SeededEventSource
from run_spatial_sequence_probe import initial_world
from engine.sequence import step_spatial_sequence


def trace(seed: int, event_limit: int) -> dict[str, object]:
    source = SeededEventSource(seed)
    state = initial_world()
    products: list[dict[str, object]] = []
    for index in range(event_limit):
        result = step_spatial_sequence(state, source)
        event_number = index + 1
        payload = result.event.payload()
        if result.event.event_type == "sequence.backbone_join":
            products.append({
                "birth_event": event_number,
                "end_event": None,
                "end_event_type": None,
                "last_present_event": event_number,
                "strand_id": int(payload["new_strand_id"]),
            })
        present_ids = {strand.strand_id for strand in result.state.sequence.strands}
        for product in products:
            if product["end_event"] is not None:
                continue
            if product["strand_id"] in present_ids:
                product["last_present_event"] = event_number
            else:
                product["end_event"] = event_number
                product["end_event_type"] = result.event.event_type
        state = result.state
    for product in products:
        product["observed_state_count"] = int(product["last_present_event"]) - int(product["birth_event"]) + 1
        product["present_at_limit"] = product["end_event"] is None
    return {"final_hash": state.state_hash(), "products": products, "seed": seed}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("seeds", nargs="+", type=int)
    parser.add_argument("--events", type=int, default=1000)
    args = parser.parse_args()
    print(json.dumps({"event_limit": args.events, "traces": [trace(seed, args.events) for seed in args.seeds]}, indent=2))


if __name__ == "__main__":
    main()
