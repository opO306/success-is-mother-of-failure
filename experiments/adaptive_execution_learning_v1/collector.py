"""Executor-side ingestion only: no signer, activation, physics or self-admission."""
from __future__ import annotations
from collections import defaultdict
from pathlib import Path
from .core import Ledger, canonical, digest, protocol, raw_hash, read, stop, stopped


def derive(paths):
    paths = [Path(path).resolve() for path in paths]
    cap = protocol()["budget"]["inputs"]
    if not paths or len(paths) > cap["max_records"]:
        raise ValueError("RECORD_BUDGET")
    total, sources, rows = 0, [], defaultdict(list)
    records = []
    for path in paths:
        size = path.stat().st_size
        total += size
        if size > cap["max_record_bytes"] or total > cap["max_total_bytes"]:
            raise ValueError("BYTE_BUDGET")
        record = read(path)
        records.append(record)
        sources.append({"path": str(path), "sha256": raw_hash(path)})
        rows[record["method"]].append({"run_id": record["run_id"], "wall_ns": record["wall_ns"],
                                      "cpu_ns": record["aggregate_cpu_ns"], "source_sha256": sources[-1]["sha256"],
                                      "result_sha256": digest(record["result"])})
    return {"schema": "ael1-candidate", "state": "CANDIDATE", "scope": records[0]["scope"],
            "measurement_kind": records[0]["measurement_kind"], "sources": sources,
            "rows": [{"method": method, "observations": sorted(observations, key=lambda x: x["run_id"])}
                     for method, observations in sorted(rows.items())]}


def eligible(scope, method):
    if method in ("CPU_SERIAL", "CPU_PARALLEL/W6"):
        return scope.get("environment", {}).get("cpu_capacity", 0) >= (1 if method == "CPU_SERIAL" else 6)
    if method != "GPU_HYBRID":
        return False
    gpu = protocol()["gpu_eligibility"]
    return (scope.get("N") in gpu["N_by_T"].get(str(scope.get("T")), [])
            and scope.get("p") in gpu["precisions"]
            and scope.get("environment", {}).get("gpu_arch") in gpu["architectures"])


def gaps(candidate, scope, methods, verified_profiles):
    # Candidates, unsigned profiles and other sessions do not count as known cost knowledge.
    known = set()
    for profile in verified_profiles:
        if profile.get("state") == "VERIFIED" and profile.get("scope") == scope:
            known.update(row["method"] for row in profile["rows"])
    unsupported = sorted(method for method in methods if not eligible(scope, method))
    unknown = sorted(method for method in methods if method not in known and method not in unsupported)
    return {"state": "UNKNOWN" if unknown else "VERIFIED", "known_methods": sorted(known),
            "unknown_methods": unknown, "unsupported_methods": unsupported,
            "choice_assessment": "VALID_CORRECT_BUT_COST_INFORMATION_INCOMPLETE",
            "unknown_other": ["confirmed future reuse", "realized net gain", "independent RwForce formula validation"]}


class Ingest:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.ledger = Ledger(self.directory / "experience")

    def history(self):
        return self.ledger.history()

    def stopped(self):
        return stopped(self.directory)

    def collect(self, paths):
        if self.stopped():
            raise ValueError("STOP_INGEST")
        identity = digest([str(Path(path).resolve()) for path in paths])
        self.ledger.append({"state": "UNKNOWN", "experience_id": identity, "missing": ["independent validated session costs"]})
        try:
            candidate = derive(paths)
            self.ledger.append({"state": "CANDIDATE", "experience_id": identity, "candidate_sha256": digest(candidate), "candidate": candidate})
            return candidate
        except Exception as error:
            self.ledger.append({"state": "UNKNOWN", "experience_id": identity, "verdict": "REFUSED", "error": str(error)})
            stop(self.directory, "INGEST_FAILURE", identity)
            raise

    def record_receipt(self, candidate, receipt):
        cid = digest(candidate)
        if not any(event["payload"].get("candidate_sha256") == cid for event in self.history()):
            self.ledger.append({"state": "CANDIDATE", "verdict": "REFUSED", "error": "UNRECORDED_OR_MUTATED_CANDIDATE",
                                "candidate_sha256": cid, "candidate": candidate, "receipt": receipt})
            stop(self.directory, "CANDIDATE_INTEGRITY", cid)
            return
        self.ledger.append({"state": "CANDIDATE", "candidate_sha256": cid, "receipt": receipt})
        # This is a recorded inspector report, not signature admission or VERIFIED authority.
        if receipt.get("body", {}).get("stop_required"):
            stop(self.directory, "INSPECTOR_STOP", receipt)

    def mark_verified(self, candidate, profile, registry):
        from .manager import Registry
        if not isinstance(registry, Registry) or self.stopped():
            raise ValueError("MANAGER_ADMISSION_REQUIRED")
        if not registry.owns(profile, digest(candidate)):
            raise ValueError("MANAGER_ADMISSION_REQUIRED")
        cid = digest(candidate)
        if not any(event["payload"].get("candidate_sha256") == cid and "receipt" in event["payload"] for event in self.history()):
            raise ValueError("INSPECTOR_REPORT_REQUIRED")
        self.ledger.append({"state": "VERIFIED", "candidate_sha256": cid, "profile_id": profile["id"], "mode": "TEST_ONLY"})
