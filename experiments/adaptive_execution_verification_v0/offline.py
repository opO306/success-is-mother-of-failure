"""Remote-only, explicitly authorized offline tests and historical evidence reread.

Never launches Vast, physics, CUDA, V1 campaign or a shutdown network operation.
Byte-preserving archive extraction is required; the sealed sources use raw hashes.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import platform
import subprocess
import sys
import time
from pathlib import Path

from .common import ROOT, digest, exclusive_json, read


def authorize(path, *, expected_code_seal_sha256):
    if platform.system() != "Linux":
        raise ValueError("REFUSED_NON_APPROVED_EXECUTION_SURFACE")
    ticket = read(path)
    if ticket.get("gate") != "ADAPTIVE_EXECUTION_VERIFICATION_V0" or ticket.get("scope") != "OFFLINE_ONLY":
        raise ValueError("REFUSED_AUTHORIZATION_SCOPE")
    if ticket.get("explicit_user_approval") is not True or not ticket.get("approval_reference"):
        raise ValueError("REFUSED_MISSING_USER_APPROVAL")
    instance_id = str(ticket.get("instance_id", ""))
    if not instance_id or os.environ.get("CONTAINER_ID") != instance_id:
        raise ValueError("REFUSED_INSTANCE_ID_MISMATCH")
    if ticket.get("code_seal_sha256") != expected_code_seal_sha256:
        raise ValueError("REFUSED_CODE_AUTHORIZATION_MISMATCH")
    if ticket.get("new_trajectories") != 0 or ticket.get("gpu_calls") != 0:
        raise ValueError("REFUSED_COMPUTATION_SCOPE")
    return ticket


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--code-seal-sha256", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    ticket = authorize(args.authorization, expected_code_seal_sha256=args.code_seal_sha256)
    import signal
    started = time.monotonic()
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError("OFFLINE_WALL_BUDGET")))
    signal.alarm(120)
    seal_path = ROOT / "experiments/adaptive_execution_verification_v0/code_seal.json"
    if hashlib.sha256(seal_path.read_bytes()).hexdigest() != args.code_seal_sha256:
        raise ValueError("CODE_SEAL_MISMATCH")
    for relative, expected in read(seal_path)["files"].items():
        path = (ROOT / relative).resolve()
        if not path.is_relative_to(ROOT.resolve()) or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError("CODE_FILE_MISMATCH:" + relative)
    # A failed/preexisting output is never overwritten or resumed implicitly.
    args.out.mkdir(parents=True, exist_ok=False)
    exclusive_json(args.out / "authorization_used.json", ticket)
    import resource
    resource.setrlimit(resource.RLIMIT_CPU, (120, 120))
    resource.setrlimit(resource.RLIMIT_AS, (512 * 1024**2, 512 * 1024**2))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTEST_DISABLE_PLUGIN_AUTOLOAD="1")
    try:
        with (args.out / "tests.log").open("xb") as log:
            result = subprocess.run([sys.executable, "-m", "pytest", "tests/test_adaptive_execution_verification_v0.py",
                                     "-q", "-p", "no:cacheprovider"], cwd=ROOT, env=env,
                                    stdout=log, stderr=subprocess.STDOUT, timeout=90)
        children = resource.getrusage(resource.RUSAGE_CHILDREN)
        parent_limit = max(1, int(120 - children.ru_utime - children.ru_stime))
        resource.setrlimit(resource.RLIMIT_CPU, (parent_limit, parent_limit))
        if result.returncode:
            exclusive_json(args.out / "status.json", {"status": "STOP_TEST_FAILURE", "exit": result.returncode})
            return 1
        # Parent-only reread after tests; final 30s is bounded by alarm and CPU cap.
        remaining = 120 - (time.monotonic() - started)
        if remaining <= 0:
            raise TimeoutError("OFFLINE_WALL_BUDGET")
        signal.alarm(max(1, min(25, int(remaining))))
        from .collector import collect, knowledge_gaps
        from .verifier import verify
        from .manager import Registry, admit
        from .journal import ExperienceJournal
        from .selector import recommend
        candidate = collect(ROOT)
        experience = ExperienceJournal(args.out / "experience_journal")
        experience.unknown(["verified historical-session execution costs", "future reuse and experiment cost"])
        experience.candidate(candidate)
        exclusive_json(args.out / "candidate.json", candidate)
        exclusive_json(args.out / "knowledge_gaps.json", knowledge_gaps(candidate))
        receipt = verify(ROOT, candidate)
        exclusive_json(args.out / "verification_receipt.json", receipt)
        experience.receipt(receipt, trusted_receipt_sha256=digest(receipt))
        if receipt["verdict"] != "VERIFIED":
            exclusive_json(args.out / "status.json", {"status": "STOP_VERIFICATION_REFUSED", "errors": receipt["errors"]})
            return 1
        # Closed offline harness handoff only; this does not authorize production.
        pins = {"receipt_sha256": digest(receipt), "verifier_sha256": receipt["verifier_sha256"],
                "protocol_sha256": receipt["protocol_sha256"], "manifest_sha256": receipt["manifest_sha256"]}
        exclusive_json(args.out / "offline_manager_handoff.json", dict(pins, mode="OFFLINE_TEST_HARNESS_ONLY"))
        profile = admit(candidate, receipt, trusted_receipt_sha256=pins["receipt_sha256"],
                        trusted_verifier_sha256=pins["verifier_sha256"], trusted_protocol_sha256=pins["protocol_sha256"],
                        trusted_manifest_sha256=pins["manifest_sha256"])
        exclusive_json(args.out / "verified_profile.json", profile)
        experience.verified(profile, trusted_profile_sha256=digest(profile))
        registry = Registry(args.out / "shadow_registry")
        before = registry.begin_request()
        registry.activate(profile, reason="offline pinned receipt", trusted_profile_sha256=digest(profile))
        active = registry.begin_request()
        suggestions = []
        scopes = {digest(row["scope"]): row["scope"] for row in profile["rows"]}
        for scope in scopes.values():
            for goal in ("WALL_MIN", "CPU_MIN"):
                suggestions.append({"scope": scope, "before": recommend(scope, goal, before, eligible_backends=set()),
                                    "after": recommend(scope, goal, active, eligible_backends={"CPU_SERIAL", "CPU_PARALLEL/W6", "GPU_HYBRID"})})
        registry.activate(reason="offline rollback demonstration")
        exclusive_json(args.out / "shadow_recommendations.json", suggestions)
        exclusive_json(args.out / "status.json", {"status": "OFFLINE_VALIDATED_ONLY", "production_activation": False,
                       "new_trajectories": 0, "gpu_calls": 0, "live_stop_validated": False,
                       "rollback": registry.begin_request().version, "formula_independence": "UNRESOLVED_SHARED_RWFORCE"})
        signal.alarm(0)
        return 0
    except (subprocess.TimeoutExpired, TimeoutError) as error:
        exclusive_json(args.out / "status.json", {"status": "STOP_BUDGET", "reason": type(error).__name__})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
