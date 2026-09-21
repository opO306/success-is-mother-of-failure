"""Predict next-tick impact scope and compare against private raw A trace."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from engine.deterministic import (
    ImpactScopeAdapter,
    PrivateTraceWriter,
    build_approved_change_view,
    evaluate_impact_scope,
    load_environment_world_spec,
    make_impact_scope_challenge,
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
    challenge = make_impact_scope_challenge(view, spec); adapter = ImpactScopeAdapter()
    claims, prediction = adapter.respond(challenge, view, spec)
    boundary, impact = evaluate_impact_scope(challenge, claims, prediction, args.source_trace, spec)
    run_dir = args.vault / args.run_id; writer = PrivateTraceWriter(run_dir, args.run_id)
    trace_b_exchange(writer, adapter.manifest, challenge, claims, boundary)
    writer.append("B", "impact_scope_evaluation", {"evaluation": impact.canonical(),
                                                     "evaluation_digest": impact.digest})
    manifest = writer.close(spec.digest, "impact-scope-has-no-authoritative-state")
    verification = verify_trace(run_dir)
    print(json.dumps({"boundary_evaluation": boundary.canonical(), "impact_evaluation": impact.canonical(),
                      "manifest": manifest, "prediction": prediction.canonical(),
                      "verification": verification}, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
