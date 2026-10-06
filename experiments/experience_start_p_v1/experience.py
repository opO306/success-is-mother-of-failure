"""Experience data for EXPERIENCE_START_P_V1 (protocol 'contracts', 'experience_keys', 'experience_store').

ExperienceRecord  - one executed, verified pass (what was tried and what happened).
ExperienceSample  - one service run: pre-run features | attempts | observed summary (no true-minimum label).
ExperienceStore   - read-only view of a sealed training bundle (hash checked at load).

Field roles: PRE_RUN fields are known before any pass and may be inputs of a future predictor; POST_RUN fields are
known only after passes ran and must never be used as inputs for the same request.
"""

from __future__ import annotations

import gzip
import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from types import MappingProxyType

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_VERSION = "experience-v1"
PHYSICS_FILES = ("a_reference/ar2_lang2024.py", "exact_expression_gate_v0/lang_iv.py",
                 "exact_expression_gate_v1/common.py", "exact_expression_gate_v1/stream.py")
NUMERIC_FILES = ("experiments/formula_repro_b_v0/harness.py", "experiments/formula_repro_b_v0/upstream/probe.py",
                 "experiments/precision_pilot_a1/evaluator_adapter.py", "experiments/precision_pilot_a2t/evaluator_adapter.py",
                 "experiments/rewrite_pilot_a3/adapter.py", "experiments/rewrite_pilot_a3/rules.py",
                 "experiments/rewrite_pilot_a3/rwforce.py")
PRE_RUN = ("schema_version", "request_fingerprint", "physics_contract_hash", "numeric_contract_hash", "evaluator",
           "initial_state_digest", "N", "T", "pair_count", "topology_class")
POST_RUN = ("attempt_p", "outcome", "completed_steps", "stop", "stop_step", "cells", "endpoint_digest", "backend",
            "worker_count", "cpu_s", "wall_s", "run_id", "source_evidence_id", "verification_status")
SUCCESS = "DECIDED"
TOPOLOGY_CLASS = "6core-noSMT-1cpu-per-core"


def sha_lf(path):
    return hashlib.sha256(Path(path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def contract_hash(table, files):
    """sha256 over the sorted 'path:sha256_lf' lines; table maps path -> sha256_lf."""
    return hashlib.sha256("\n".join(f"{f}:{table[f]}" for f in sorted(files)).encode()).hexdigest()


def current_contracts(root=ROOT):
    table = {f: sha_lf(Path(root) / f) for f in PHYSICS_FILES + NUMERIC_FILES}
    return contract_hash(table, PHYSICS_FILES), contract_hash(table, NUMERIC_FILES)


def fingerprint(physics, numeric, evaluator, initial_digest, T):
    return hashlib.sha256(json.dumps([physics, numeric, evaluator, initial_digest, T]).encode()).hexdigest()


def family_key(T, evaluator, physics, numeric):
    return f"FCC_N|T={T}|{evaluator}|{physics}|{numeric}"


@dataclass(frozen=True)
class ExperienceRecord:
    schema_version: str
    request_fingerprint: str
    physics_contract_hash: str
    numeric_contract_hash: str
    evaluator: str
    initial_state_digest: str
    N: int
    T: int
    pair_count: int
    topology_class: str
    attempt_p: int
    outcome: str
    completed_steps: int
    stop: object
    stop_step: object
    cells: object
    endpoint_digest: object
    backend: str
    worker_count: int
    cpu_s: float
    wall_s: float
    run_id: str
    source_evidence_id: str
    verification_status: str


def record_from_pass(rec, physics, numeric, run_id, source_id, verified):
    """ExperienceRecord from one runner record (the dict written by experiments/w5_placement_v1/run)."""
    ev, N, T = rec["evaluator"], rec["N"], rec["T"]
    ek = rec.get("endpoints_key")
    return ExperienceRecord(
        schema_version=SCHEMA_VERSION,
        request_fingerprint=fingerprint(physics, numeric, ev, rec["initial_sha256"], T),
        physics_contract_hash=physics, numeric_contract_hash=numeric, evaluator=ev,
        initial_state_digest=rec["initial_sha256"], N=N, T=T, pair_count=N * (N - 1) // 2,
        topology_class=TOPOLOGY_CLASS, attempt_p=rec["requested_p"], outcome=rec["outcome"],
        completed_steps=rec["completed_steps"], stop=rec["stop"], stop_step=rec["stop_step"], cells=rec["cells"],
        endpoint_digest=hashlib.sha256(ek.encode()).hexdigest() if ek else None,
        backend=rec["plan"]["backend"], worker_count=rec["plan"]["worker_count"], cpu_s=rec["total_cpu_s"],
        wall_s=rec["end_to_end_wall_s"], run_id=run_id, source_evidence_id=source_id,
        verification_status="VERIFIED" if verified else "UNVERIFIED")


def summarize(records):
    """Per exact key and per family: observed success / failure bounds from VERIFIED records only."""
    exact = {}
    for r in records:
        if r["verification_status"] != "VERIFIED":
            continue
        e = exact.setdefault(r["request_fingerprint"], {
            "N": r["N"], "T": r["T"], "evaluator": r["evaluator"], "initial_state_digest": r["initial_state_digest"],
            "physics_contract_hash": r["physics_contract_hash"], "numeric_contract_hash": r["numeric_contract_hash"],
            "success_p": set(), "failure_p": set()})
        (e["success_p"] if r["outcome"] == SUCCESS else e["failure_p"]).add(r["attempt_p"])
    out_exact = {}
    for k, e in exact.items():
        s, f = sorted(e.pop("success_p")), sorted(e.pop("failure_p"))
        out_exact[k] = {**e, "lowest_observed_success_p": s[0] if s else None,
                        "highest_observed_failure_p": f[-1] if f else None, "observed_success_p": s,
                        "observed_failure_p": f}
    fam = {}
    for k, e in out_exact.items():
        if e["lowest_observed_success_p"] is None:
            continue
        fk = family_key(e["T"], e["evaluator"], e["physics_contract_hash"], e["numeric_contract_hash"])
        fam.setdefault(fk, {"T": e["T"], "evaluator": e["evaluator"], "members": []})["members"].append(
            {"request_fingerprint": k, "N": e["N"], "lowest_observed_success_p": e["lowest_observed_success_p"]})
    for fk, v in fam.items():
        v["members"].sort(key=lambda m: (m["N"], m["request_fingerprint"]))
        lows = [m["lowest_observed_success_p"] for m in v["members"]]
        v["FAMILY_MIN"], v["FAMILY_MAX"] = min(lows), max(lows)
    return out_exact, fam


def build_bundle(source_dir_gz, checker_verdict_path, seal_path, source_id):
    """Training bundle from one verified evidence archive (records.json.gz written by pack.py)."""
    files = json.load(gzip.open(source_dir_gz))["files"]
    verdict = json.loads(Path(checker_verdict_path).read_text(encoding="utf-8"))
    seal = json.loads(Path(seal_path).read_text(encoding="utf-8"))
    verified = verdict.get("verdict") == "EVIDENCE OK" and verdict.get("bit_mismatches", 1) == 0
    table = seal["source_sha256_lf"]
    physics, numeric = contract_hash(table, PHYSICS_FILES), contract_hash(table, NUMERIC_FILES)
    records = []
    for name in sorted(files):
        if not name.endswith(".json"):
            continue
        if name.startswith("service/"):
            s = json.loads(files[name])
            for pz in s["passes"]:
                rec = dict(pz["record"], requested_p=pz["p"])
                records.append(asdict(record_from_pass(rec, physics, numeric, f"{name}#pass{pz['index']}", source_id, verified)))
        elif name.startswith("shadow/"):
            rec = json.loads(files[name])
            records.append(asdict(record_from_pass(rec, physics, numeric, name, source_id, verified)))
    exact, fam = summarize(records)
    return {"schema_version": SCHEMA_VERSION, "source_evidence_id": source_id,
            "source_archive_sha256_raw": hashlib.sha256(Path(source_dir_gz).read_bytes()).hexdigest(),
            "source_checker_verdict": verdict.get("verdict"), "physics_contract_hash": physics,
            "numeric_contract_hash": numeric, "field_roles": {"pre_run": list(PRE_RUN), "post_run": list(POST_RUN)},
            "records": records, "exact": exact, "family": fam}


def canonical_bytes(bundle):
    return json.dumps(bundle, sort_keys=True, separators=(",", ":")).encode("utf-8")


class ExperienceStore:
    """Read-only sealed training bundle. Lookups return copies; nothing can be added."""

    def __init__(self, path, expected_sha256):
        raw = Path(path).read_bytes()
        bundle = json.loads(raw)
        got = hashlib.sha256(canonical_bytes(bundle)).hexdigest()
        if got != expected_sha256:
            raise ValueError(f"training bundle hash {got} != sealed {expected_sha256}")
        self.sha256 = got
        self._exact = MappingProxyType({k: MappingProxyType(v) for k, v in bundle["exact"].items()})
        self._family = MappingProxyType({k: MappingProxyType(v) for k, v in bundle["family"].items()})
        self.physics, self.numeric = bundle["physics_contract_hash"], bundle["numeric_contract_hash"]

    def exact(self, fp):
        e = self._exact.get(fp)
        return dict(e) if e is not None else None

    def family(self, fk):
        f = self._family.get(fk)
        return dict(f) if f is not None else None
