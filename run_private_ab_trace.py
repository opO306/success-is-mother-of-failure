"""Record a full owner-private A/B trace and verify it immediately."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from engine.deterministic import (
    CognitiveMapAdapter,
    PrivateTraceWriter,
    evaluate_cognitive_map_claims,
    load_environment_world_spec,
    make_cognitive_map_challenge,
    trace_b_exchange,
    trace_environment_run,
    verify_trace,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--vault", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    spec = load_environment_world_spec(args.spec)
    run_dir = args.vault / args.run_id
    writer = PrivateTraceWriter(run_dir, args.run_id)
    final_state = trace_environment_run(spec, writer)
    queries = (
        {"query_id": "source-state", "kind": "local_state", "point": [4, 4]},
        {"query_id": "blocked-shortest", "kind": "shortest_path", "start": [20, 20], "goal": [21, 20]},
        {"query_id": "reachable-three", "kind": "reachable_within", "start": [20, 20], "goal": [21, 20], "max_steps": 3},
    )
    challenge = make_cognitive_map_challenge(spec, queries)
    adapter = CognitiveMapAdapter(); claims = adapter.respond(challenge, spec)
    evaluation = evaluate_cognitive_map_claims(challenge, claims, spec)
    trace_b_exchange(writer, adapter.manifest, challenge, claims, evaluation)
    manifest = writer.close(spec.digest, final_state.digest)
    verification = verify_trace(run_dir)
    print(json.dumps({"manifest": manifest, "run_dir": str(run_dir), "verification": verification},
                     ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
