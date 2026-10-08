"""Collect historical observations only. No verifier import, promotion or executor."""
from __future__ import annotations

from .common import ROOT, RESULT_FIELDS, check_seals, digest, read, seconds_ns


def collect(root=ROOT):
    manifest = check_seals(root)
    base = root / "docs/active/adaptive_execution_v1/vast_evaluate/run_evaluate"
    env = read(base / "env.json")["env"]
    rows = {}
    for relative, source_hash in manifest["files"].items():
        if "/services/" not in relative:
            continue
        service = read(root / relative)
        passes = service["passes"]
        if len(passes) != 1 or len(passes[0]["attempts"]) != 1:
            raise ValueError("SINGLE_PASS_ONLY")
        pz = passes[0]
        plan = pz["attempts"][0]["plan"]
        dec = service["start_decision"]
        scope = {"env_id": service["env_id"], "evidence_session": manifest["evidence_session"],
                 "request_fingerprint": dec["request_fingerprint"], "initial_state_digest": dec["initial_state_digest"],
                 "N": service["N"], "T": service["T"], "p": pz["requested_p"],
                 "physics": env["contracts"]["physics"], "numeric": env["contracts"]["numeric"],
                 "evaluator": dec["evaluator"]}
        label = plan["backend"] + (f"/W{plan['worker_count']}" if plan["worker_count"] else "")
        key = (service["request_id"], service["strategy"], service["goal"])
        row = rows.setdefault(key, {"scope": scope, "backend": label, "placement_id": plan["placement_id"],
                                    "worker_count": plan["worker_count"], "observations": []})
        row["observations"].append({"source": relative, "source_sha256": source_hash,
                                    "run_id": service["run_id"], "wall_ns": seconds_ns(service["service_wall_s"]),
                                    "cpu_ns": seconds_ns(service["service_cpu_s"]),
                                    "result_sha256": digest({name: pz[name] for name in RESULT_FIELDS})})
    ordered = [rows[key] for key in sorted(rows, key=str)]
    for row in ordered:
        row["observations"].sort(key=lambda item: item["run_id"])
    return {"schema": "aev0-candidate", "state": "CANDIDATE", "session": manifest["evidence_session"],
            "rows": ordered, "formula_independence": "UNRESOLVED_SHARED_RWFORCE"}


def knowledge_gaps(candidate):
    return {"known": ["historical outputs and timings", "V1 rule-compliant serial fallback for R7",
                       "R1 GPU CPU-time observations"],
            "unknown": ["future session performance", "reuse count", "guaranteed future gain",
                         "new measurement and verification cost", "independent RwForce formula validation"],
            "correctness": "HISTORICAL_CHECKER_EVIDENCE_NOT_NEW_PHYSICS_CERTIFICATION",
            "choice_assessment": "VALID_CORRECT_BUT_COST_INFORMATION_INCOMPLETE",
            "state": candidate["state"]}
