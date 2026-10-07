"""Experience data for EXPERIENCE_START_P_V2 (protocol 'training_bundle_v2').

Reuses the V1 record / summary / store code unchanged and adds a multi-source bundle with de-duplication:
records are rebuilt from the source runner records of every listed verified evidence archive, keyed by
(source_evidence_id, run_id) and by record content hash.
"""

from __future__ import annotations

import gzip
import hashlib
import json
from dataclasses import asdict
from pathlib import Path

from experiments.experience_start_p_v1 import experience as EX1
from experiments.experience_start_p_v1.experience import (NUMERIC_FILES, PHYSICS_FILES, POST_RUN, PRE_RUN, ExperienceStore,
                                                          canonical_bytes, contract_hash, current_contracts, family_key,
                                                          fingerprint, summarize)

ROOT = EX1.ROOT
SCHEMA_VERSION = "experience-v2"
EVALUATOR = "rw:R1+R2"
SOURCES = (
    {"id": "SELECTOR_SERVICE_V1@0e6953b:docs/active/selector_service_v1/laptop_run",
     "dir": "docs/active/selector_service_v1/laptop_run", "kinds": ("service", "shadow")},
    {"id": "EXPERIENCE_START_P_V1@abf5ac7:docs/active/experience_start_p_v1/laptop_run",
     "dir": "docs/active/experience_start_p_v1/laptop_run", "kinds": ("service",)},
)
__all__ = ["ExperienceStore", "canonical_bytes", "current_contracts", "family_key", "fingerprint", "build_bundle",
           "record_sha256", "candidate_record", "SCHEMA_VERSION", "EVALUATOR"]


def record_sha256(rec):
    r = {k: v for k, v in rec.items() if k != "record_sha256"}
    return hashlib.sha256(json.dumps(r, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _source_records(src, root=ROOT):
    d = Path(root) / src["dir"]
    files = json.load(gzip.open(d / "records.json.gz"))["files"]
    verdict = json.loads((d / "checker_verdict.json").read_text(encoding="utf-8"))
    seal = json.loads((d / "execution_seal.json").read_text(encoding="utf-8"))
    verified = verdict.get("verdict") == "EVIDENCE OK" and verdict.get("bit_mismatches", 1) == 0
    table = seal["source_sha256_lf"]
    physics, numeric = contract_hash(table, PHYSICS_FILES), contract_hash(table, NUMERIC_FILES)
    out = []
    for name in sorted(files):
        if not name.endswith(".json"):
            continue
        kind = name.split("/")[0]
        if kind not in src["kinds"]:
            continue
        if kind == "service":
            s = json.loads(files[name])
            for pz in s["passes"]:
                rec = dict(pz["record"], requested_p=pz["p"])
                out.append(asdict(EX1.record_from_pass(rec, physics, numeric, f"{name}#pass{pz['index']}", src["id"],
                                                       verified)))
        else:
            rec = json.loads(files[name])
            out.append(asdict(EX1.record_from_pass(rec, physics, numeric, name, src["id"], verified)))
    meta = {"id": src["id"], "archive_sha256_raw": hashlib.sha256((d / "records.json.gz").read_bytes()).hexdigest(),
            "checker_verdict": verdict.get("verdict"), "bit_mismatches": verdict.get("bit_mismatches"),
            "physics_contract_hash": physics, "numeric_contract_hash": numeric, "n_records_read": len(out)}
    return meta, out


def build_bundle(sources=SOURCES, root=ROOT, extra_records=()):
    """extra_records exists only for the fault-injection tests (it must make the build or the checker fail)."""
    metas, records, seen_key, seen_hash, dropped = [], [], set(), set(), []
    for src in sources:
        meta, recs = _source_records(src, root)
        metas.append(meta)
        records += recs
    records += [dict(r) for r in extra_records]
    kept = []
    for r in records:
        r["record_sha256"] = record_sha256(r)
        key = (r["source_evidence_id"], r["run_id"])
        if key in seen_key or r["record_sha256"] in seen_hash:
            dropped.append({"source_evidence_id": r["source_evidence_id"], "run_id": r["run_id"]})
            continue
        seen_key.add(key)
        seen_hash.add(r["record_sha256"])
        kept.append(r)
    contracts = {(m["physics_contract_hash"], m["numeric_contract_hash"]) for m in metas}
    if len(contracts) != 1:
        raise ValueError(f"sources disagree on contracts: {contracts}")
    physics, numeric = contracts.pop()
    bad = [r["run_id"] for r in kept if (r["physics_contract_hash"], r["numeric_contract_hash"], r["evaluator"]) !=
           (physics, numeric, EVALUATOR)]
    if bad:
        raise ValueError(f"records with another contract or evaluator: {bad[:5]}")
    exact, fam = summarize(kept)
    return {"schema_version": SCHEMA_VERSION, "sources": metas, "physics_contract_hash": physics,
            "numeric_contract_hash": numeric, "field_roles": {"pre_run": list(PRE_RUN), "post_run": list(POST_RUN)},
            "dedup": {"key": "(source_evidence_id, run_id) or record_sha256", "n_dropped": len(dropped),
                      "dropped": dropped}, "n_records": len(kept), "records": kept, "exact": exact, "family": fam}


def candidate_record(rec, physics, numeric, run_id, topology_class):
    """An UNVERIFIED record of this campaign (candidate_v2/), never read by any policy."""
    r = asdict(EX1.record_from_pass(rec, physics, numeric, run_id, "EXPERIENCE_START_P_V2:candidate", False))
    r["schema_version"], r["topology_class"] = SCHEMA_VERSION, topology_class
    r["record_sha256"] = record_sha256(r)
    return r
