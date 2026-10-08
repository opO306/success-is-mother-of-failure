"""ADAPTIVE_EXECUTION_V1 start p and experience records (protocol 'start_p').

The start p comes from the sealed EXPERIENCE_START_P_V2 store (read-only, hash-checked): EXACT_MEMORY -> FAMILY_MAX ->
64. Records of this experiment are written as UNVERIFIED candidates and are never read by any policy here.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from experiments.experience_start_p_v1.experience import ExperienceStore, family_key, fingerprint

ROOT = Path(__file__).resolve().parents[2]
BUNDLE = ROOT / "docs/active/experience_start_p_v2/training_bundle.json"
BUNDLE_SHA = "ec19eda9c6966be265709398480b4de4aa6bfcdb1ddb38de5f5f9d0602283ae3"
EVALUATOR = "rw:R1+R2"
DEFAULT_START = 64
CANDIDATE_SCHEMA = "adaptive-candidate-v1"


def load_store(path=BUNDLE, sha=BUNDLE_SHA):
    return ExperienceStore(path, sha)


def initial_state_digest(N):
    """The exact-fraction digest of the FCC_N initial state (independent of any p)."""
    from experiments.multiatom_parallel_v1 import scenarios as SC
    from experiments.multiatom_parallel_v1.run import initial_digest
    q0, p0 = SC.initial(N)
    return initial_digest(q0, p0)


def start_decision(N, T, start, store, env):
    """start: 'CHAIN' | 'BASE64' | 'FAMILY_MAX' | 'FIXED_START:<p>'."""
    physics, numeric = env["contracts"]["physics"], env["contracts"]["numeric"]
    dig = initial_state_digest(N)
    fp = fingerprint(physics, numeric, EVALUATOR, dig, T)
    fk = family_key(T, EVALUATOR, physics, numeric)
    match = (physics, numeric) == (store.physics, store.numeric)
    exact = store.exact(fp) if match else None
    fam = store.family(fk) if match else None
    d = {"start": start, "N": N, "T": T, "evaluator": EVALUATOR, "initial_state_digest": dig,
         "request_fingerprint": fp, "family_key": fk, "bundle_sha256": store.sha256, "contracts_match": match,
         "exact_hit": bool(exact and exact.get("lowest_observed_success_p")),
         "exact_lowest_observed_success_p": exact.get("lowest_observed_success_p") if exact else None,
         "family_hit": fam is not None, "FAMILY_MAX": fam["FAMILY_MAX"] if fam else None}
    if start == "CHAIN":
        if d["exact_hit"]:
            p, src = d["exact_lowest_observed_success_p"], "EXACT_MEMORY"
        elif fam:
            p, src = fam["FAMILY_MAX"], "FAMILY_MAX"
        else:
            p, src = DEFAULT_START, "DEFAULT_64"
    elif start == "BASE64":
        p, src = DEFAULT_START, "BASE64"
    elif start == "FAMILY_MAX":
        p, src = (fam["FAMILY_MAX"], "FAMILY_MAX") if fam else (DEFAULT_START, "DEFAULT_64")
    elif start.startswith("FIXED_START:"):
        p, src = int(start.split(":")[1]), "FIXED_START"
    else:
        raise ValueError(start)
    d.update(start_p=p, start_source=src)
    return d


def candidate_record(service, pz, env_id):
    """One UNVERIFIED candidate record per executed pass (candidates/; never a policy input)."""
    r = {"schema_version": CANDIDATE_SCHEMA, "verification_status": "UNVERIFIED",
         "request_fingerprint": service["start_decision"]["request_fingerprint"],
         "initial_state_digest": service["start_decision"]["initial_state_digest"], "N": service["N"],
         "T": service["T"], "evaluator": EVALUATOR, "env_id": env_id, "attempt_p": pz["requested_p"],
         "outcome": pz["outcome"], "completed_steps": pz["completed_steps"], "stop": pz["stop"],
         "stop_step": pz["stop_step"], "cells": pz["cells"],
         "endpoint_digest": hashlib.sha256(pz["endpoints_key"].encode()).hexdigest() if pz.get("endpoints_key") else None,
         "backend": pz["backend"], "wall_s": pz["wall_s"], "cpu_s": pz["cpu_s"],
         "run_id": f"{service['run_id']}#pass{pz['index']}"}
    r["record_sha256"] = hashlib.sha256(json.dumps(r, sort_keys=True).encode()).hexdigest()
    return r
