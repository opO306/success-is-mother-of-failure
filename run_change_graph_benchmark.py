"""Benchmark ChangeGraphAdapter through a path-free approved trace view."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from engine.deterministic import (
    ChangeGraphAdapter,
    PrivateTraceWriter,
    build_approved_change_view,
    build_change_graph,
    evaluate_change_graph_claims,
    load_environment_world_spec,
    make_change_graph_challenge,
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
    view = build_approved_change_view(args.source_trace, spec, args.target_tick)
    queries = (
        {"query_id": "reconstruct", "kind": "reconstructed_state_digest"},
        {"query_id": "local-source", "kind": "local_state", "point": [4, 4],
         "solute_kinds": spec.solute_kinds},
        {"query_id": "last-cell-change", "kind": "last_change", "path": "$.cells"},
        {"query_id": "graph-cost", "kind": "graph_cost"},
    )
    challenge = make_change_graph_challenge(view, queries); adapter = ChangeGraphAdapter()
    claims = adapter.respond(challenge, view)
    evaluation = evaluate_change_graph_claims(challenge, claims, args.source_trace, spec)
    graph = build_change_graph(view)
    run_dir = args.vault / args.run_id; writer = PrivateTraceWriter(run_dir, args.run_id)
    trace_b_exchange(writer, adapter.manifest, challenge, claims, evaluation)
    manifest = writer.close(spec.digest, graph.reconstructed_state_digest)
    verification = verify_trace(run_dir)
    payload = {"evaluation": evaluation.canonical(), "graph_summary": {
        "delta_operations": graph.delta_operation_count, "digest": graph.digest,
        "nodes": len(graph.nodes), "reconstructed_state_digest": graph.reconstructed_state_digest,
        "view_bytes": len(json.dumps(view.canonical(), ensure_ascii=False, separators=(",", ":")).encode("utf-8"))},
        "manifest": manifest, "verification": verification}
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
