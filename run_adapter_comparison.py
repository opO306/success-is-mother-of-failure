"""Compare Cognitive Map and Change Graph on identical external queries."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from engine.deterministic import (
    PrivateTraceWriter,
    compare_cognitive_and_change_graph,
    load_environment_world_spec,
    trace_b_exchange,
    verify_trace,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--source-trace", type=Path, required=True)
    parser.add_argument("--vault", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--target-tick", type=int, required=True)
    args = parser.parse_args()
    spec = load_environment_world_spec(args.spec)
    comparison, exchanges = compare_cognitive_and_change_graph(spec, args.source_trace, args.target_tick)
    run_dir = args.vault / args.run_id; writer = PrivateTraceWriter(run_dir, args.run_id)
    for adapter, challenge, claims, evaluation in exchanges:
        trace_b_exchange(writer, adapter.manifest, challenge, claims, evaluation)
    manifest = writer.close(spec.digest, "comparison-has-no-authoritative-state")
    verification = verify_trace(run_dir)
    print(json.dumps({"comparison": comparison.canonical(), "manifest": manifest,
                      "verification": verification}, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
