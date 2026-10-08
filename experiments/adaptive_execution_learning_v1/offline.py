"""Explicitly approved remote-only bounded CPU tests. Never starts Vast or physics."""
from __future__ import annotations
import argparse
import os
import platform
import subprocess
import sys
import time
from pathlib import Path
from .core import ROOT, HERE, check_frozen, raw_hash, read, write_new


def authorize(path, expected_code_seal):
    if platform.system() != "Linux":
        raise ValueError("REFUSED_EXECUTION_SURFACE")
    ticket = read(path)
    if ticket.get("gate") != "ADAPTIVE_EXECUTION_LEARNING_V1" or ticket.get("scope") != "OFFLINE_ONLY":
        raise ValueError("REFUSED_AUTHORIZATION_SCOPE")
    if ticket.get("explicit_user_approval") is not True or not ticket.get("approval_reference"):
        raise ValueError("REFUSED_USER_APPROVAL")
    if str(ticket.get("instance_id")) != os.environ.get("CONTAINER_ID"):
        raise ValueError("REFUSED_INSTANCE")
    if ticket.get("code_seal_sha256") != expected_code_seal:
        raise ValueError("REFUSED_CODE_AUTHORIZATION")
    if ticket.get("new_trajectories") != 0 or ticket.get("gpu_calls") != 0:
        raise ValueError("REFUSED_NUMERIC_EXECUTION")
    return ticket


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--code-seal-sha256", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    ticket = authorize(args.authorization, args.code_seal_sha256)
    import resource
    import signal
    started = time.monotonic()
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError("WALL_BUDGET")))
    signal.alarm(120)
    resource.setrlimit(resource.RLIMIT_CPU, (120, 120))
    resource.setrlimit(resource.RLIMIT_AS, (512 * 1024**2, 512 * 1024**2))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    seal_path = HERE / "code_seal.json"
    if raw_hash(seal_path) != args.code_seal_sha256:
        raise ValueError("CODE_SEAL_INTEGRITY")
    seal = read(seal_path)
    for relative, expected in seal["files"].items():
        path = (ROOT / relative).resolve()
        if not path.is_relative_to(ROOT) or raw_hash(path) != expected:
            raise ValueError("CODE_INTEGRITY:" + relative)
    check_frozen()
    # No implicit install/network fallback. Missing dependency is a preserved refusal.
    args.out.mkdir(parents=True, exist_ok=False)
    write_new(args.out / "authorization_used.json", ticket)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTEST_DISABLE_PLUGIN_AUTOLOAD="1")
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        import cryptography
        import pytest
        write_new(args.out / "runtime.json", {"python": platform.python_version(), "cryptography": cryptography.__version__,
                                             "pytest": pytest.__version__, "instance_id": os.environ.get("CONTAINER_ID")})
        with (args.out / "tests.log").open("xb") as log:
            run = subprocess.run([sys.executable, "-m", "pytest", "tests/test_adaptive_execution_verification_v0.py",
                                  "tests/test_adaptive_execution_learning_v1.py", "-q", "-p", "no:cacheprovider",
                                  "--junitxml=" + str(args.out / "junit.xml")], cwd=ROOT, env=env,
                                 stdout=log, stderr=subprocess.STDOUT, timeout=90)
        children = resource.getrusage(resource.RUSAGE_CHILDREN)
        if run.returncode:
            write_new(args.out / "status.json", {"status": "STOP_TEST_FAILURE", "exit": run.returncode})
            return 1
        resource.setrlimit(resource.RLIMIT_CPU, (max(1, int(120 - children.ru_utime - children.ru_stime)),) * 2)
        remaining = 120 - (time.monotonic() - started)
        if remaining <= 0:
            raise TimeoutError("WALL_BUDGET")
        signal.alarm(max(1, min(25, int(remaining))))
        # The demo identity is explicitly TEST_ONLY. It is not a production approval.
        from .demo import run_demo
        run_demo(args.out / "demo")
        check_frozen()
        parent = resource.getrusage(resource.RUSAGE_SELF)
        write_new(args.out / "status.json", {"status": "OFFLINE_TEST_VALIDATED_ONLY", "mode": "TEST_ONLY",
                                             "wall_seconds": time.monotonic() - started,
                                             "aggregate_cpu_seconds": parent.ru_utime + parent.ru_stime + children.ru_utime + children.ru_stime,
                                             "new_trajectories": 0, "gpu_calls": 0, "production_activation": False,
                                             "real_net_profit": "UNCONFIRMED", "formula_independence": "UNRESOLVED_SHARED_RWFORCE"})
        return 0
    except Exception as error:
        if not (args.out / "status.json").exists():
            write_new(args.out / "status.json", {"status": "STOP_OFFLINE_FAILURE", "error": str(error)})
        return 1


if __name__ == "__main__":
    sys.exit(main())
