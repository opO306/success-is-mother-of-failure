"""Append-only compact evidence and hash/source closure for this gate."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(4*1024*1024), b""):
            h.update(block)
    return h.hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--historical-root", required=True)
    args = p.parse_args()
    root, out, original = Path(args.root), Path(args.output), Path(args.historical_root)
    out.mkdir(parents=True, exist_ok=False)
    stages = ("controls_v2", "target_v1", "controls_generalized_h_v2", "target_generalized_h_v2")
    current = {x.name: sha(x) for x in Path("electronic_pilot/minimum_bracket").glob("*") if x.is_file()}
    binding = {}
    for stage in stages:
        seal = json.loads((root/stage/"seal.json").read_text(encoding="utf-8"))
        snapshots = {name: sha(root/stage/(name+".executed.txt")) for name in seal["source_sha256"]}
        binding[stage] = dict(executed_snapshots_match=snapshots == seal["source_sha256"],
                              current_executed_files_match=all(current.get(name) == digest for name,digest in seal["source_sha256"].items()),
                              added_post_acquisition_files=sorted(set(current)-set(seal["source_sha256"])),
                              expected_historical_candidate=stage in ("controls_v2", "target_v1"))
        for name, digest in seal["protected_sha256"].items():
            if sha(Path(name)) != digest:
                raise ValueError("historical protected source/evidence changed: "+name)
    for control, target in (("controls_v2", "target_v1"), ("controls_generalized_h_v2", "target_generalized_h_v2")):
        cs = json.loads((root/control/"seal.json").read_text(encoding="utf-8"))
        ts = json.loads((root/target/"seal.json").read_text(encoding="utf-8"))
        if cs["source_sha256"] != ts["source_sha256"] or cs["protocol"] != ts["protocol"]:
            raise ValueError("control/target source or protocol changed")
    pre = json.loads((root/"historical_raw_precheck.json").read_text(encoding="utf-8"))
    post = []
    for row in pre["rows"]:
        path = original/Path(row["path"].replace("\\", "/"))
        actual = sha(path) if path.is_file() else None
        post.append(dict(path=row["path"], status="MATCH" if actual == row["expected_sha256"] == row["sha256"] else "MISMATCH", sha256=actual))
    if not all(x["status"] == "MATCH" for x in post):
        raise ValueError("historical raw closure failed")
    with (root/"historical_raw_postcheck.json").open("x", encoding="utf-8") as f:
        json.dump(dict(count=len(post), all_unchanged=True, rows=post), f, indent=2)
    results = {stage: json.loads((root/stage/"results.json").read_text(encoding="utf-8")) for stage in stages}
    audit = json.loads((root/"product_action_audit.json").read_text(encoding="utf-8"))
    hp = json.loads((root/"ao_amplification/results.json").read_text(encoding="utf-8"))
    summary = dict(status="PARTIAL", QZ_short_R_support="UNSUPPORTED_UNRESOLVED",
                   candidate_B="NOT_IMPLEMENTED_NOT_EVALUATED; feasibility only; stop rule",
                   sampled_bracket="UNRESOLVED", R13_trusted_energy=None,
                   controls=[results[x]["control_verdict"] for x in ("controls_v2", "controls_generalized_h_v2")],
                   R13_refusals=[results[x]["rows"][0] for x in ("target_v1", "target_generalized_h_v2")],
                   stages_wall_seconds=sum(results[x]["stage_wall_seconds"] for x in stages),
                   stages_worker_cpu_seconds=sum(r.get("cpu_seconds", 0) for x in stages for r in results[x]["rows"]),
                   max_process_peak_rss_bytes=max(r["process_peak_rss_bytes"] for x in stages for r in results[x]["rows"]),
                   product_action_audit_status=audit["status"],
                   max_accepted_full_product_residual_l2=max(x.get("full_product_residual_l2", 0) for x in audit["rows"]),
                   scalar_MP_diagnostic=hp, source_binding=binding,
                   protected_source_and_evidence_file_count=len(json.loads((root/stages[0]/"seal.json").read_text(encoding="utf-8"))["protected_sha256"]),
                   historical_raw_file_count=len(post), historical_raw_all_unchanged=True,
                   numerical_attempts=8, accepted_controls=6, refused_target_attempts=2,
                   startup_failures=1, unexecuted_target_R14=True,
                   local_full="OMITTED_RELATED_TESTS_ONLY_BASELINE_UNCHANGED",
                   windows_tests=72, wsl_tests=78, unique_new_tests=29,
                   conceptual_review="author review; full dimensions, exact basis inputs, guards preserved, no energy from refused matrices; not external audit approval",
                   basis_error="unchanged finite cc-pVQZ approximation; no continuum error bound",
                   model_error="fixed nuclei, isolated nonrelativistic Coulomb; no dynamics or radiation",
                   reference_error="controls use archived same-basis numerical results; no new physical-reference calculation",
                   scaling="M=60, D=1830; 60^4=12960000 AO entries; 8 small fresh workers only; no many-electron scaling measurement",
                   next_gate="Electronic Sector Panel V1 proposed; not started", push=False)
    with (root/"summary.json").open("x", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, allow_nan=False)
    for path in root.rglob("*"):
        if path.is_file() and path.suffix in (".json", ".log", ".xml", ".txt", ".dat"):
            target = out/path.relative_to(root)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
    raw = {str(x.relative_to(root)): dict(sha256=sha(x), bytes=x.stat().st_size)
           for x in root.rglob("*") if x.is_file()}
    with (out/"raw_manifest.json").open("x", encoding="utf-8") as f:
        json.dump(dict(raw_root=str(root.resolve()), files=raw), f, indent=2, ensure_ascii=False)
    print(json.dumps({k:v for k,v in summary.items() if k not in ("controls", "R13_refusals", "scalar_MP_diagnostic", "source_binding")}, indent=2))


if __name__ == "__main__":
    main()
