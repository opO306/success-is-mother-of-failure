"""Build a private multi-world residual campaign and propose theory revisions."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from engine.deterministic import (
    EnvironmentWorldSpec,
    PrivateTraceWriter,
    TheoryRevisionAdapter,
    TheoryVersion,
    build_residual_pattern,
    collect_omitted_component_residual,
    make_theory_revision_challenge,
    review_theory_revision_set,
    trace_b_exchange,
    trace_environment_run,
    verify_trace,
)


def _digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-spec", type=Path, required=True)
    parser.add_argument("--vault", type=Path, required=True)
    parser.add_argument("--campaign-id", required=True)
    parser.add_argument("--worlds", type=int, default=4)
    args = parser.parse_args()
    if args.worlds < 3: raise ValueError("residual campaign needs at least three worlds")
    campaign = args.vault / args.campaign_id; campaign.mkdir(parents=True, exist_ok=False)
    raw_base = json.loads(args.base_spec.read_text(encoding="utf-8"))
    theory = TheoryVersion("limited-no-vapor-v1", None,
                           ("heat", "water", "mineral", "solute"), ("local-transport",))
    residuals = []; specs = []
    for index in range(args.worlds):
        raw = json.loads(json.dumps(raw_base)); raw["causal_world"]["world_id"] = f"vapor-residual-{index}"
        raw["causal_world"]["execution"]["ticks"] = 2; raw["cells"][1]["vapor"] = 4 + index * 2
        spec = EnvironmentWorldSpec.from_mapping(raw); specs.append(spec.digest)
        run_dir = campaign / f"world-{index}"; writer = PrivateTraceWriter(run_dir, f"world-{index}")
        (run_dir / "spec.json").write_text(json.dumps(spec.canonical(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                                           encoding="utf-8")
        final = trace_environment_run(spec, writer); writer.close(spec.digest, final.digest)
        residuals.append(collect_omitted_component_residual(run_dir, f"world-{index}", spec, theory,
                                                            "vapor", 0, 1))
    pattern = build_residual_pattern(tuple(residuals), 3)
    challenge = make_theory_revision_challenge(pattern, theory); adapter = TheoryRevisionAdapter()
    claims, revisions = adapter.respond(challenge, pattern, theory)
    boundary, review = review_theory_revision_set(challenge, claims, revisions, theory)
    analysis_dir = campaign / "analysis"; writer = PrivateTraceWriter(analysis_dir, "analysis")
    trace_b_exchange(writer, adapter.manifest, challenge, claims, boundary)
    for residual in residuals: writer.append("B", "prediction_residual", {"residual": residual.canonical()})
    writer.append("B", "residual_pattern", {"pattern": pattern.canonical(), "pattern_digest": pattern.digest})
    writer.append("B", "theory_revision_set", {"revisions": revisions.canonical(),
                                                 "revisions_digest": revisions.digest})
    writer.append("B", "theory_revision_review", {"review": review.canonical(), "review_digest": review.digest})
    campaign_digest = _digest({"specs": specs, "theory": theory.digest})
    manifest = writer.close(campaign_digest, "theory-revisions-not-applied")
    verification = verify_trace(analysis_dir)
    files = []
    for path in sorted(item for item in campaign.rglob("*") if item.is_file()
                       and item.name != "campaign_manifest.json"):
        files.append({"bytes": path.stat().st_size, "path": path.relative_to(campaign).as_posix(),
                      "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    campaign_manifest = {"campaign_id": args.campaign_id, "files": files,
                         "format": "private-trace-campaign-manifest-v1",
                         "residual_pattern_digest": pattern.digest,
                         "revision_set_digest": revisions.digest}
    campaign_manifest_path = campaign / "campaign_manifest.json"
    campaign_manifest_path.write_text(json.dumps(campaign_manifest, ensure_ascii=False, indent=2,
                                                 sort_keys=True) + "\n", encoding="utf-8")
    campaign_manifest_sha256 = hashlib.sha256(campaign_manifest_path.read_bytes()).hexdigest()
    print(json.dumps({"boundary_evaluation": boundary.canonical(), "campaign": str(campaign),
                      "campaign_manifest_sha256": campaign_manifest_sha256,
                      "manifest": manifest, "parent_theory": theory.canonical(),
                      "residual_pattern": pattern.canonical(), "revision_set": revisions.canonical(),
                      "review": review.canonical(), "verification": verification},
                     ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
