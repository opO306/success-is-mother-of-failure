"""Independent offline evidence reader. Stdlib only; no collector/selector/manager imports.

This inherits historical numerical evidence. It does NOT recalculate physics,
resolve shared RwForce, sign an identity, or activate a profile.
"""
from __future__ import annotations

import gzip
import hashlib
import json
from decimal import Decimal
from pathlib import Path


def _bytes(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _hash(obj):
    return hashlib.sha256(_bytes(obj)).hexdigest()


def _read(path):
    raw = Path(path).read_bytes()
    if str(path).endswith(".gz"):
        raw = gzip.decompress(raw)
    return json.loads(raw, parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def _ns(value):
    if isinstance(value, bool):
        raise ValueError("INVALID_TIMING")
    d = Decimal(str(value))
    if not d.is_finite() or d <= 0:
        raise ValueError("INVALID_TIMING")
    return int((d * 10**9).to_integral_value(rounding="ROUND_HALF_EVEN"))


def _check_service(service, env, spec):
    if service["N"] != spec["N"] or service["T"] != spec["T"] or service["p_sequence"] != [spec["p"]]:
        raise ValueError("REQUEST_SCOPE_MISMATCH")
    if service["env_id"] != env["env_id"] or service["status"] != "DECIDED" or service["events"]:
        raise ValueError("INVALID_SERVICE")
    if len(service["passes"]) != 1:
        raise ValueError("SINGLE_PASS_ONLY")
    pz = service["passes"][0]
    if pz["index"] != 0 or pz["start"] != "ORIGINAL_STATE" or len(pz["attempts"]) != 1:
        raise ValueError("INVALID_ORIGINAL_PASS")
    attempt = pz["attempts"][0]
    plan, result = attempt["plan"], attempt["result"]
    p = spec["p"]
    if [pz["requested_p"], pz["effective_p"], plan["p"], result["requested_p"], result["effective_p"]] != [p] * 5:
        raise ValueError("PRECISION_MISMATCH")
    if plan["env_id"] != env["env_id"] or plan["evaluator"] != "rw:R1+R2" or result["status_class"] != "OK":
        raise ValueError("EXECUTOR_MISMATCH")
    if pz["backend"] != plan["backend"] or result["backend"] != plan["backend"]:
        raise ValueError("BACKEND_MISMATCH")
    if result["initial_sha256"] != service["start_decision"]["initial_state_digest"]:
        raise ValueError("INITIAL_STATE_MISMATCH")
    if pz["outcome"] != "DECIDED" or pz["completed_steps"] != service["T"] or pz["stop"] is not None:
        raise ValueError("INVALID_OUTCOME")
    fields = ("outcome", "completed_steps", "stop", "stop_step", "cells", "endpoints_key")
    if any(pz[name] != result[name] for name in fields):
        raise ValueError("PASS_RESULT_MISMATCH")
    # Frozen V1 eligibility, independently expressed; no expansion of support.
    if (env["mpmath_version"], env["mpmath_backend"]) != ("1.3.0", "python"):
        raise ValueError("ENV_UNVERIFIED")
    if plan["backend"] == "GPU_HYBRID":
        if env["gpu"]["arch"] not in ("sm_86", "sm_89") or p not in (64, 73, 78, 109, 128, 161, 163, 166, 192):
            raise ValueError("GPU_UNVERIFIED")
        if service["N"] not in {1000: (12, 16, 40), 100: (12, 16, 40, 64, 128)}.get(service["T"], ()):
            raise ValueError("GPU_DOMAIN_OUTSIDE")
        gpu = result["gpu"]
        if gpu["device_p"] != p or gpu["device_p_echo"] != [p] or gpu["status"] != "OK" or gpu["block"] != 32:
            raise ValueError("GPU_ECHO_MISMATCH")
        if plan["worker_count"] != 0 or plan["gpu_profile"] != "GPU_V1" or plan["gpu_block"] != 32:
            raise ValueError("GPU_PLAN_MISMATCH")
    elif plan["backend"] in ("CPU_SERIAL", "CPU_PARALLEL"):
        cpus, cores = [], set()
        for cpu in sorted(env["allowed_cpus"]):
            core = env["core_of_cpu"].get(str(cpu))
            if core is not None and core not in cores:
                cpus.append(cpu)
                cores.add(core)
        quota = env.get("cpu_quota")
        limit = len(cpus) if quota is None else min(len(cpus), int(quota))
        workers = plan["worker_count"]
        expected = [] if plan["backend"] == "CPU_SERIAL" else cpus[1:6] + [cpus[0]]
        if workers not in (0, 6) or limit < (1 if workers == 0 else 6) or plan["main_cpu"] != cpus[0]:
            raise ValueError("CPU_PLACEMENT_INVALID")
        if plan["worker_cpus"] != expected or len(expected) != workers or result["executed_placement_ok"] is not True:
            raise ValueError("CPU_PLACEMENT_INVALID")
    else:
        raise ValueError("BACKEND_UNSUPPORTED")
    cpu = _ns(service["service_cpu_s"])
    if abs(cpu - _ns(pz["cpu_s"])) > 1 or abs(cpu - _ns(result["cpu_s"])) > 1:
        raise ValueError("CPU_ACCOUNTING_MISMATCH")
    if _ns(service["service_wall_s"]) < _ns(pz["wall_s"]):
        raise ValueError("WALL_ACCOUNTING_MISMATCH")
    return pz, plan


def verify(root, candidate):
    root = Path(root).resolve()
    here = root / "experiments/adaptive_execution_verification_v0"
    receipt = {"schema": "aev0-cost-receipt", "candidate_sha256": _hash(candidate), "verdict": "REFUSED",
               "scope": "HISTORICAL_SESSION_EXECUTION_COST_ONLY", "formula_independence": "UNRESOLVED_SHARED_RWFORCE",
               "verifier_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               "errors": [], "rows": []}
    try:
        seal = _read(here / "protocol_seal.json")
        for relative, expected in seal["files"].items():
            if hashlib.sha256((root / relative).read_bytes()).hexdigest() != expected:
                raise ValueError("PROTOCOL_SEAL_MISMATCH")
        receipt["protocol_sha256"] = seal["files"]["experiments/adaptive_execution_verification_v0/protocol.json"]
        receipt["manifest_sha256"] = seal["files"]["experiments/adaptive_execution_verification_v0/source_manifest.json"]
        protocol = _read(here / "protocol.json")
        manifest = _read(here / "source_manifest.json")
        limits = protocol["initial_evidence"]["source_budget"]
        if len(manifest["files"]) > limits["max_files"]:
            raise ValueError("FILE_BUDGET")
        total = 0
        for relative, expected in manifest["files"].items():
            source = (root / relative).resolve()
            if not source.is_relative_to(root):
                raise ValueError("PATH_OUTSIDE_ROOT")
            size = source.stat().st_size
            total += size
            if size > limits["max_file_bytes"] or total > limits["max_total_bytes"]:
                raise ValueError("BYTE_BUDGET")
            if hashlib.sha256(source.read_bytes()).hexdigest() != expected:
                raise ValueError("SOURCE_SEAL_MISMATCH:" + relative)
        base = root / protocol["initial_evidence"]["directory"]
        historical = _read(base / "checker_verdict_final.json")
        if historical["verdict"] != "EVIDENCE OK" or historical["errors"] or historical["phase"] != "final":
            raise ValueError("HISTORICAL_CHECKER_NOT_OK")
        env = _read(base / "env.json")["env"]
        rows, control_outputs, all_outputs, scopes = {}, {}, [], {}
        expected_paths = set()
        for request_id, spec in protocol["initial_evidence"]["requests"].items():
            for repeat in protocol["initial_evidence"]["repeats"]:
                for strategy in spec["strategies"]:
                    relative = f"{protocol['initial_evidence']['directory']}/services/r{repeat}/{request_id}__{strategy}.json.gz"
                    expected_paths.add(relative)
                    if relative not in manifest["files"]:
                        raise ValueError("MISSING_EXPECTED_REPEAT")
                    service = _read(root / relative)
                    if service["run_id"] != f"r{repeat}/{request_id}__{strategy}" or service["request_id"] != request_id:
                        raise ValueError("RUN_ID_MISMATCH")
                    if service["strategy"] != ("ADAPTIVE" if strategy == "ADAPTIVE_WALL" else strategy):
                        raise ValueError("STRATEGY_MISMATCH")
                    if service["goal"] != ("WALL_MIN" if strategy == "ADAPTIVE_WALL" else None):
                        raise ValueError("GOAL_MISMATCH")
                    pz, plan = _check_service(service, env, spec)
                    wanted_backend = {"FIXED_SERIAL": "CPU_SERIAL", "FIXED_W6": "CPU_PARALLEL", "FIXED_GPU": "GPU_HYBRID"}.get(strategy)
                    if wanted_backend and plan["backend"] != wanted_backend:
                        raise ValueError("FIXED_BACKEND_MISMATCH")
                    dec = service["start_decision"]
                    scope = {"env_id": env["env_id"], "evidence_session": manifest["evidence_session"],
                             "request_fingerprint": dec["request_fingerprint"], "initial_state_digest": dec["initial_state_digest"],
                             "N": service["N"], "T": service["T"], "p": spec["p"],
                             "physics": env["contracts"]["physics"], "numeric": env["contracts"]["numeric"],
                             "evaluator": dec["evaluator"]}
                    if scopes.setdefault(request_id, scope) != scope:
                        raise ValueError("EXACT_SCOPE_MISMATCH")
                    payload = {field: pz[field] for field in ("outcome", "completed_steps", "stop", "stop_step", "cells", "endpoints_key")}
                    output_hash = _hash(payload)
                    all_outputs.append((request_id, output_hash))
                    if strategy == "FIXED_SERIAL":
                        if control_outputs.setdefault(request_id, output_hash) != output_hash:
                            raise ValueError("SERIAL_REPEAT_MISMATCH")
                    key = (request_id, service["strategy"], service["goal"])
                    label = plan["backend"] + (f"/W{plan['worker_count']}" if plan["worker_count"] else "")
                    row = rows.setdefault(key, {"scope": scope, "backend": label, "placement_id": plan["placement_id"],
                                                "worker_count": plan["worker_count"], "observations": []})
                    if row["backend"] != label or row["placement_id"] != plan["placement_id"]:
                        raise ValueError("PLACEMENT_REPEAT_MISMATCH")
                    row["observations"].append({"source": relative, "source_sha256": manifest["files"][relative],
                                                "run_id": service["run_id"], "wall_ns": _ns(service["service_wall_s"]),
                                                "cpu_ns": _ns(service["service_cpu_s"]), "result_sha256": output_hash})
        actual_paths = {path for path in manifest["files"] if "/services/" in path}
        if actual_paths != expected_paths or len(expected_paths) != protocol["initial_evidence"]["expected_service_files"]:
            raise ValueError("EVIDENCE_SET_MISMATCH")
        if any(value != control_outputs[request] for request, value in all_outputs):
            raise ValueError("RESULT_MISMATCH")
        ordered = [rows[key] for key in sorted(rows, key=str)]
        for row in ordered:
            row["observations"].sort(key=lambda item: item["run_id"])
            if len(row["observations"]) != protocol["promotion"]["minimum_repeats"]:
                raise ValueError("REPEAT_COUNT")
            for metric in ("wall_ns", "cpu_ns"):
                values = [observation[metric] for observation in row["observations"]]
                if Decimal(max(values)) > Decimal(min(values)) * Decimal(protocol["promotion"]["maximum_spread_ratio"]):
                    raise ValueError("INVALID_MEASUREMENT_SPREAD")
        if candidate != {"schema": "aev0-candidate", "state": "CANDIDATE", "session": manifest["evidence_session"],
                         "rows": ordered, "formula_independence": "UNRESOLVED_SHARED_RWFORCE"}:
            raise ValueError("CANDIDATE_REDERIVATION_MISMATCH")
        receipt.update(verdict="VERIFIED", rows=ordered, n_services=len(expected_paths),
                       measurement_scope="WARM_GPU_SESSION; SERVICE_WALL; AGGREGATE_ATTEMPT_CPU; NO_ENERGY_MEASUREMENT")
    except (ValueError, KeyError, TypeError, IndexError, OSError, ArithmeticError) as error:
        receipt["errors"].append(str(error))
    return receipt
