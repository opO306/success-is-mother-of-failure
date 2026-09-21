"""Run a branch-preserving multi-fidelity counterfactual benchmark."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from engine.deterministic import (
    CounterfactualBranchAdapter,
    PrivateTraceWriter,
    build_approved_change_view,
    execute_counterfactual_plan,
    load_environment_world_spec,
    make_counterfactual_challenge,
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
    parser.add_argument("--exact-budget", type=int, default=3)
    args = parser.parse_args()
    spec = load_environment_world_spec(args.spec)
    view = build_approved_change_view(args.source_trace, spec, args.source_tick)
    challenge = make_counterfactual_challenge(view, spec); adapter = CounterfactualBranchAdapter(args.exact_budget)
    claims, plan = adapter.respond(challenge, view, spec)
    boundary, evaluation = execute_counterfactual_plan(challenge, claims, plan, view, spec)
    run_dir = args.vault / args.run_id; writer = PrivateTraceWriter(run_dir, args.run_id)
    trace_b_exchange(writer, adapter.manifest, challenge, claims, boundary)
    writer.append("B", "counterfactual_plan", {"plan": plan.canonical(), "plan_digest": plan.digest})
    for result in evaluation.fidelity_results:
        writer.append("B", "fidelity_result", {"result": result.canonical()}, tick=plan.target_tick,
                      phase=result.fidelity)
    writer.append("B", "counterfactual_evaluation", {"evaluation": evaluation.canonical(),
                                                       "evaluation_digest": evaluation.digest})
    manifest = writer.close(spec.digest, "counterfactual-evaluation-has-no-authoritative-state")
    verification = verify_trace(run_dir)
    print(json.dumps({"boundary_evaluation": boundary.canonical(),
                      "counterfactual_evaluation": evaluation.canonical(), "manifest": manifest,
                      "plan": plan.canonical(), "verification": verification},
                     ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
