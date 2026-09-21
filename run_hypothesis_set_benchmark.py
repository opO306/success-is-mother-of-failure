"""Create and evaluate a nonexclusive HypothesisSet against private A trace."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from engine.deterministic import (
    HypothesisSetAdapter,
    PrivateTraceWriter,
    build_approved_change_view,
    evaluate_hypothesis_set,
    load_environment_world_spec,
    make_hypothesis_challenge,
    trace_b_exchange,
    verify_trace,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--source-trace", type=Path, required=True)
    parser.add_argument("--vault", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--source-tick", type=int, required=True)
    args = parser.parse_args()
    spec = load_environment_world_spec(args.spec)
    view = build_approved_change_view(args.source_trace, spec, args.source_tick)
    challenge = make_hypothesis_challenge(view, spec); adapter = HypothesisSetAdapter()
    claims, hypothesis_set = adapter.respond(challenge, view, spec)
    boundary, resolution = evaluate_hypothesis_set(challenge, claims, hypothesis_set, args.source_trace, spec)
    run_dir = args.vault / args.run_id; writer = PrivateTraceWriter(run_dir, args.run_id)
    trace_b_exchange(writer, adapter.manifest, challenge, claims, boundary)
    writer.append("B", "hypothesis_set", {"hypothesis_set": hypothesis_set.canonical(),
                                           "hypothesis_set_digest": hypothesis_set.digest})
    writer.append("B", "hypothesis_resolution", {"resolution": resolution.canonical(),
                                                  "resolution_digest": resolution.digest})
    manifest = writer.close(spec.digest, "hypothesis-evaluation-has-no-authoritative-state")
    verification = verify_trace(run_dir)
    print(json.dumps({"boundary_evaluation": boundary.canonical(),
                      "hypothesis_set": hypothesis_set.canonical(), "manifest": manifest,
                      "resolution": resolution.canonical(), "verification": verification},
                     ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
