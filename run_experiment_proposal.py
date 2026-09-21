"""Create a sealed held-out experiment proposal without executing any A world."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from engine.deterministic import (
    EnvironmentWorldSpec,
    ExperimentProposalAdapter,
    PrivateTraceWriter,
    TheoryRevisionAdapter,
    TheoryVersion,
    build_residual_pattern,
    collect_omitted_component_residual,
    make_experiment_proposal_challenge,
    make_theory_revision_challenge,
    require_experiment_authorization,
    review_experiment_proposal,
    trace_b_exchange,
    verify_trace,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-spec", type=Path, required=True)
    parser.add_argument("--revision-campaign", type=Path, required=True)
    parser.add_argument("--vault", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    raw_base = json.loads(args.base_spec.read_text(encoding="utf-8"))
    theory = TheoryVersion("limited-no-vapor-v1", None,
                           ("heat", "water", "mineral", "solute"), ("local-transport",))
    residuals = []; training_specs = []
    for run_dir in sorted(args.revision_campaign.glob("world-*")):
        spec = EnvironmentWorldSpec.from_mapping(json.loads((run_dir / "spec.json").read_text(encoding="utf-8")))
        training_specs.append(spec.digest)
        residuals.append(collect_omitted_component_residual(run_dir, run_dir.name, spec, theory,
                                                            "vapor", 0, 1))
    pattern = build_residual_pattern(tuple(residuals), 3)
    revision_challenge = make_theory_revision_challenge(pattern, theory)
    _, revisions = TheoryRevisionAdapter().respond(revision_challenge, pattern, theory)
    challenge = make_experiment_proposal_challenge(pattern, revisions, theory)
    adapter = ExperimentProposalAdapter(); claims, proposal = adapter.respond(
        challenge, pattern, revisions, theory, raw_base)
    boundary, review = review_experiment_proposal(challenge, claims, proposal, revisions,
                                                  tuple(training_specs))
    try:
        require_experiment_authorization(proposal)
        execution_gate = "unexpectedly-open"
    except PermissionError:
        execution_gate = "blocked-pending-user-approval"
    run_dir = args.vault / args.run_id; writer = PrivateTraceWriter(run_dir, args.run_id)
    trace_b_exchange(writer, adapter.manifest, challenge, claims, boundary)
    writer.append("B", "experiment_proposal", {"proposal": proposal.canonical(),
                                                 "proposal_digest": proposal.digest})
    writer.append("B", "experiment_proposal_review", {"review": review.canonical(),
                                                        "review_digest": review.digest})
    manifest = writer.close(revisions.digest, "experiment-not-run")
    (run_dir / "proposal.json").write_text(json.dumps(proposal.canonical(), ensure_ascii=False,
                                                       indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (run_dir / "proposal_review.json").write_text(json.dumps(review.canonical(), ensure_ascii=False,
                                                              indent=2, sort_keys=True) + "\n", encoding="utf-8")
    verification = verify_trace(run_dir)
    print(json.dumps({"boundary_evaluation": boundary.canonical(), "execution_gate": execution_gate,
                      "manifest": manifest, "proposal": proposal.canonical(),
                      "proposal_digest": proposal.digest, "review": review.canonical(),
                      "verification": verification}, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
