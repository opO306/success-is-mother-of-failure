"""Independent original-evidence reader and TEST_ONLY signer. No executor imports.

Signatures authenticate this inspector identity, not the truth of synthetic timing.
Production promotion requires a separately approved attestation adapter, not provided.
"""
from __future__ import annotations
import gzip
import hashlib
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "experiments/adaptive_execution_learning_v1"


def _bytes(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode()


def _hash(obj):
    return hashlib.sha256(_bytes(obj)).hexdigest()


def _raw(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _read(path):
    def pairs(items):
        answer = {}
        for key, val in items:
            if key in answer:
                raise ValueError("DUPLICATE_JSON_KEY")
            answer[key] = val
        return answer
    raw = Path(path).read_bytes()
    if str(path).endswith(".gz"):
        raw = gzip.decompress(raw)
    return json.loads(raw, object_pairs_hook=pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError("NONFINITE_JSON")))


def _positive(value):
    if type(value) is not int or value <= 0:
        raise ValueError("INVALID_TIMING")


def _eligible(scope, method, rules):
    if method in ("CPU_SERIAL", "CPU_PARALLEL/W6"):
        if scope["environment"]["cpu_capacity"] < (1 if method == "CPU_SERIAL" else 6):
            raise ValueError("CPU_UNSUPPORTED")
    elif method == "GPU_HYBRID":
        gpu = rules["gpu_eligibility"]
        if (scope["N"] not in gpu["N_by_T"].get(str(scope["T"]), [])
                or scope["p"] not in gpu["precisions"] or scope["environment"]["gpu_arch"] not in gpu["architectures"]):
            raise ValueError("GPU_UNSUPPORTED")
    else:
        raise ValueError("METHOD_UNSUPPORTED")


def inspect(candidate):
    rules = _read(HERE / "protocol.json")
    receipt = {"schema": "ael1-cost-receipt", "mode": "TEST_ONLY", "verdict": "REFUSED", "errors": [],
               "scope": "SYNTHETIC_TEST_ONLY", "formula_independence": "UNRESOLVED_SHARED_RWFORCE",
               "candidate_sha256": _hash(candidate), "protocol_sha256": _hash(rules),
               "verifier_sha256": _raw(__file__), "rows": [], "stop_required": False}
    try:
        # Independent raw seal validation, not collector output or caller-provided trust hashes.
        for relative, expected in _read(HERE / "protocol_seal.json")["files"].items():
            if _raw(ROOT / relative) != expected:
                raise ValueError("PROTOCOL_INTEGRITY:" + relative)
        protected = _read(HERE / "preservation_manifest.json")["files"]
        for relative, expected in protected.items():
            if _raw(ROOT / relative) != expected:
                raise ValueError("PROTECTED_INTEGRITY:" + relative)
        sources = candidate["sources"]
        budget = rules["budget"]["inputs"]
        if not sources or len(sources) > budget["max_records"]:
            raise ValueError("RECORD_BUDGET")
        rows, scope, kind, total, run_ids, paths = defaultdict(list), None, None, 0, set(), set()
        result_control = None
        oldenv = _read(ROOT / "docs/active/adaptive_execution_v1/vast_evaluate/run_evaluate/env.json")["env"]
        for source in sources:
            path = Path(source["path"]).resolve()
            if str(path) in paths:
                raise ValueError("DUPLICATE_SOURCE")
            paths.add(str(path))
            total += path.stat().st_size
            if path.stat().st_size > budget["max_record_bytes"] or total > budget["max_total_bytes"]:
                raise ValueError("BYTE_BUDGET")
            if _raw(path) != source["sha256"]:
                raise ValueError("SOURCE_INTEGRITY")
            obj = _read(path)
            if obj["schema"] != "ael1-execution-record" or not obj["choice_reason"]:
                raise ValueError("INVALID_RECORD")
            if obj["run_id"] in run_ids or not obj["run_id"]:
                raise ValueError("DUPLICATE_RUN_ID")
            run_ids.add(obj["run_id"])
            if scope is None:
                scope, kind = obj["scope"], obj["measurement_kind"]
            if obj["scope"] != scope or obj["measurement_kind"] != kind:
                raise ValueError("SESSION_SCOPE_MISMATCH")
            if set(scope) != set(rules["experience"]["scope_key"]) or not scope["session_id"]:
                raise ValueError("SCOPE_MISMATCH")
            if kind != "SYNTHETIC_TEST_ONLY":
                raise ValueError("REAL_SESSION_ATTESTATION_ADAPTER_REQUIRED")
            if any(type(scope[key]) is not int or scope[key] <= 0 for key in ("N", "T", "p")):
                raise ValueError("REQUEST_MISMATCH")
            if obj["precision"] != scope["p"] or obj["domain"] != "OK":
                raise ValueError("PRECISION_DOMAIN_MISMATCH")
            if _hash(obj["initial_state"]) != scope["initial_state_sha256"]:
                raise ValueError("INITIAL_STATE_MISMATCH")
            _eligible(scope, obj["method"], rules)
            proof = obj["correctness_evidence"]
            historical_path = proof["source"]
            if (proof["level"] != "PINNED_HISTORICAL_OUTPUT_ONLY" or historical_path not in protected
                    or "/services/" not in historical_path or proof["source_sha256"] != protected[historical_path]):
                raise ValueError("CORRECTNESS_EVIDENCE_MISMATCH")
            historical = _read(ROOT / historical_path)
            if (historical["N"] != scope["N"] or historical["T"] != scope["T"]
                    or historical["final_p"] != scope["p"]
                    or historical["start_decision"]["request_fingerprint"] != scope["request_fingerprint"]
                    or historical["start_decision"]["initial_state_digest"] != obj["initial_state"].get("historical_sha256")
                    or scope["request_type"] != "FCC" or scope["evaluator"] != "rw:R1+R2"
                    or scope["physics"] != oldenv["contracts"]["physics"] or scope["numeric"] != oldenv["contracts"]["numeric"]):
                raise ValueError("HISTORICAL_REQUEST_MISMATCH")
            fields = ("outcome", "completed_steps", "stop", "stop_step", "cells", "endpoints_key")
            expected_result = {field: historical["passes"][0][field] for field in fields}
            if obj["result"] != expected_result:
                raise ValueError("RESULT_MISMATCH")
            if result_control is not None and obj["result"] != result_control:
                raise ValueError("RESULT_MISMATCH")
            result_control = obj["result"]
            _positive(obj["wall_ns"]); _positive(obj["aggregate_cpu_ns"])
            attempts = obj["attempts"]
            if not attempts or attempts[-1]["p"] != obj["precision"] or attempts[-1]["status"] != "DECIDED":
                raise ValueError("ATTEMPT_PRECISION_MISMATCH")
            for attempt in attempts:
                _positive(attempt["cpu_ns"]); _positive(attempt["wall_ns"])
                if attempt["start"] != "ORIGINAL_STATE" or attempt["initial_state_sha256"] != scope["initial_state_sha256"]:
                    raise ValueError("ORIGINAL_STATE_MISMATCH")
            if sum(attempt["cpu_ns"] for attempt in attempts) != obj["aggregate_cpu_ns"]:
                raise ValueError("CPU_ACCOUNTING_MISMATCH")
            if sum(attempt["wall_ns"] for attempt in attempts) > obj["wall_ns"]:
                raise ValueError("WALL_ACCOUNTING_MISMATCH")
            rows[obj["method"]].append({"run_id": obj["run_id"], "wall_ns": obj["wall_ns"], "cpu_ns": obj["aggregate_cpu_ns"],
                                        "source_sha256": source["sha256"], "result_sha256": _hash(obj["result"])})
        if "CPU_SERIAL" not in rows:
            raise ValueError("SERIAL_BASELINE_REQUIRED")
        for observations in rows.values():
            if len(observations) != rules["promotion"]["minimum_repeats_per_method"]:
                raise ValueError("REPEATS_REQUIRED")
            for metric in ("wall_ns", "cpu_ns"):
                times = [obj[metric] for obj in observations]
                if max(times) * 4 > min(times) * 5:
                    raise ValueError("SPREAD_REFUSED")
        ordered = [{"method": method, "observations": sorted(observations, key=lambda item: item["run_id"])}
                   for method, observations in sorted(rows.items())]
        rederived = {"schema": "ael1-candidate", "state": "CANDIDATE", "scope": scope,
                     "measurement_kind": kind, "sources": sources, "rows": ordered}
        if candidate != rederived:
            raise ValueError("CANDIDATE_MISMATCH")
        receipt.update(verdict="VERIFIED", rows=ordered, session_scope=scope, n_records=len(sources))
    except Exception as error:
        receipt["errors"] = [str(error)]
        receipt["stop_required"] = any(term in str(error) for term in ("INTEGRITY", "MISMATCH", "BUDGET", "NONFINITE", "DUPLICATE_JSON"))
    return receipt


def inspect_and_sign(candidate, inspector_private_key):
    # The only signing entry point re-reads evidence itself; it does not sign caller verdicts.
    body = inspect(candidate)
    return {"body": body, "signature": inspector_private_key.sign(b"AEL1_RECEIPT\0" + _bytes(body)).hex()}
