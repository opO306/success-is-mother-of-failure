"""Explicitly fabricated cost panel; copies sealed historical output, executes no physics."""
from __future__ import annotations
import copy
from pathlib import Path
from .core import ROOT, digest, read, raw_hash, write_new


def panel(directory, *, session="NEW_SYNTHETIC_A", N=12, costs=None):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    request = "R1" if N == 12 else "R7"
    relative = f"docs/active/adaptive_execution_v1/vast_evaluate/run_evaluate/services/r1/{request}__FIXED_SERIAL.json.gz"
    old = read(ROOT / relative)
    oldenv = read(ROOT / "docs/active/adaptive_execution_v1/vast_evaluate/run_evaluate/env.json")["env"]
    # Old archive carries only initial-state digest; no claim of reconstructing all its values.
    initial = {"representation": "PINNED_HISTORICAL_REFERENCE_ONLY", "historical_sha256": old["start_decision"]["initial_state_digest"]}
    scope = {"request_type": "FCC", "N": N, "T": 1000, "p": 163, "initial_state_sha256": digest(initial),
             "request_fingerprint": old["start_decision"]["request_fingerprint"],
             "physics": oldenv["contracts"]["physics"], "numeric": oldenv["contracts"]["numeric"], "evaluator": "rw:R1+R2",
             "environment": {"cpu_model": "SYNTHETIC_CPU", "cpu_capacity": 6, "gpu_arch": "sm_89",
                             "runtime": "mpmath-1.3.0/python", "timing_scope": "FULL_SERVICE_ALL_ATTEMPTS"},
             "session_id": session}
    fields = ("outcome", "completed_steps", "stop", "stop_step", "cells", "endpoints_key")
    result = {field: old["passes"][0][field] for field in fields}
    costs = costs or {"CPU_SERIAL": (100, 100), "CPU_PARALLEL/W6": (60, 250), "GPU_HYBRID": (25, 20)}
    if N == 14:
        costs = {method: pair for method, pair in costs.items() if method != "GPU_HYBRID"}
    paths = []
    for method, (wall, cpu) in sorted(costs.items()):
        for rep in range(5):
            obj = {"schema": "ael1-execution-record", "run_id": f"{session}/{method}/{rep}", "scope": copy.deepcopy(scope),
                   "initial_state": copy.deepcopy(initial), "method": method,
                   "choice_reason": "SYNTHETIC experiment; costs fabricated, historical output copied",
                   "wall_ns": wall * 1000000, "aggregate_cpu_ns": cpu * 1000000,
                   "attempts": [{"start": "ORIGINAL_STATE", "initial_state_sha256": digest(initial), "p": 163,
                                 "cpu_ns": cpu * 1000000, "wall_ns": wall * 1000000, "status": "DECIDED"}],
                   "result": copy.deepcopy(result), "precision": 163, "domain": "OK",
                   "correctness_evidence": {"level": "PINNED_HISTORICAL_OUTPUT_ONLY", "source": relative,
                                             "source_sha256": raw_hash(ROOT / relative)},
                   "measurement_kind": "SYNTHETIC_TEST_ONLY"}
            path = directory / (method.replace("/", "_") + f"_{rep}.json")
            write_new(path, obj)
            paths.append(path)
    return paths
