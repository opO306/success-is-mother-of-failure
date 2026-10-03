"""Run exactly one sealed README static build, then isolated vendor examples.

Run in local WSL; original source and all earlier evidence remain immutable.
No R04 input, B2 implementation, automatic flag retry, merge, rebase or push.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

from electronic_pilot.h2_vendor_resume_v2.compare import compare


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=True) + "\n", encoding="utf8")


def timed(argv, cwd, stdin_path, folder, stem, timeout, env):
    stdout = folder / (stem + ".stdout")
    stderr = folder / (stem + ".stderr")
    metrics = folder / (stem + ".time")
    command = ["/usr/bin/time", "-f", "%e %U %S %M %x", "-o", str(metrics), *argv]
    start = time.monotonic()
    # stdout/stderr are captured separately; do not reorder or normalize bytes.
    with stdin_path.open("rb") if stdin_path else open(os.devnull, "rb") as inp:
        try:
            result = subprocess.run(command, cwd=cwd, stdin=inp, capture_output=True,
                                    env=env, timeout=timeout)
            stdout.write_bytes(result.stdout)
            stderr.write_bytes(result.stderr)
            exit_code = result.returncode
        except subprocess.TimeoutExpired as exc:
            stdout.write_bytes(exc.stdout or b"")
            stderr.write_bytes(exc.stderr or b"")
            exit_code = None
    measurement = {"command": command, "exit": exit_code,
                   "wall_monotonic_seconds": time.monotonic() - start,
                   "timed_out": exit_code is None,
                   "stdout_sha256": sha(stdout), "stderr_sha256": sha(stderr),
                   "gnu_time_seconds": None, "cpu_user_seconds": None,
                   "cpu_system_seconds": None, "peak_RSS_KiB": None}
    if metrics.exists():
        lines = metrics.read_text(encoding="utf8").splitlines()
        for line in reversed(lines):
            tokens = line.split()
            if len(tokens) == 5:
                try:
                    measurement.update(gnu_time_seconds=float(tokens[0]),
                                       cpu_user_seconds=float(tokens[1]),
                                       cpu_system_seconds=float(tokens[2]),
                                       peak_RSS_KiB=int(tokens[3]))
                    break
                except ValueError:
                    continue
    write(folder / (stem + ".process.json"), measurement)
    return measurement


def verify_bindings(root, bindings):
    for path, digest in bindings.items():
        if sha(root / path) != digest:
            raise ValueError("BYTE DRIFT: " + path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True)
    args = parser.parse_args()
    root = Path.cwd()
    run = root / args.run
    plan = json.loads((run / "protocol.json").read_text(encoding="utf8"))
    assert sha(run / "protocol.json") == (run / "protocol.sha256").read_text().strip()
    # Never overwrite an earlier attempt or resume an interrupted build.
    claim = run / "execution_started.json"
    with claim.open("x", encoding="utf8") as f:
        json.dump({"started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                   "protocol_sha256": sha(run / "protocol.json")}, f, indent=2)
    verify_bindings(root, plan["protected_sha256"])
    verify_bindings(root, plan["wrapper_sha256"])
    for path, digest in plan["archive_file_sha256"].items():
        assert sha(Path(path)) == digest, "ARCHIVE BYTE DRIFT: " + path
    original = root / plan["original_tree"]
    for row in plan["vendor_inventory"]:
        assert sha(original / row["path"]) == row["sha256"], row["path"]
    build = run / "vendor_build"
    shutil.copytree(original, build)
    folder = build / "h2solv/f"
    env = dict(os.environ, OMP_NUM_THREADS="1", OMP_DYNAMIC="FALSE")
    # README-supported variable override only; Makefile bytes stay identical.
    build_result = timed(plan["build_argv"], folder, None, run,
                         "build", plan["build_timeout_s"], env)
    cases = []
    statuses = []
    if build_result["exit"] != 0 or not (folder / "h2solv").is_file() or not (folder / "example").is_file():
        statuses = ["VENDOR_BUILD_STILL_UNRESOLVED", "STOP"]
    else:
        statuses = ["README_SUPPORTED_BUILD_PATH_WORKS",
                    "VENDOR_BUILD_ENVIRONMENT_COMPATIBILITY_SUPPORTED"]
        for name in ["h2solv", "example"]:
            binary = folder / name
            for label, command in [("ldd", ["ldd", str(binary)]),
                                   ("readelf", ["readelf", "-d", str(binary)])]:
                p = subprocess.run(command, capture_output=True)
                (run / (name + "." + label + ".stdout")).write_bytes(p.stdout)
                (run / (name + "." + label + ".stderr")).write_bytes(p.stderr)
            write(run / (name + ".binary.json"), {"sha256": sha(binary), "bytes": binary.stat().st_size})
        for case in plan["examples"]:
            case_dir = run / "cases" / case["name"]
            case_dir.mkdir(parents=True, exist_ok=False)
            input_path = original / case["input_path"]
            ref_path = original / case["reference_path"]
            assert sha(input_path) == case["input_sha256"]
            assert sha(ref_path) == case["reference_sha256"]
            shutil.copyfile(input_path, case_dir / "input.inp")
            shutil.copyfile(ref_path, case_dir / "reference.out")
            solver = timed([str(folder / "h2solv")], case_dir, input_path,
                           case_dir, "solver", plan["case_timeout_s"], env)
            wf = case_dir / "wf_7.dat"
            example = {"exit": None, "not_executed": True}
            if solver["exit"] == 0 and wf.is_file():
                example = timed([str(folder / "example")], case_dir, wf,
                                case_dir, "example", plan["case_timeout_s"], env)
            actual = (case_dir / "solver.stdout").read_bytes()
            if (case_dir / "example.stdout").exists():
                actual += (case_dir / "example.stdout").read_bytes()
            (case_dir / "combined.out").write_bytes(actual)
            stderr = (case_dir / "solver.stderr").read_bytes()
            if (case_dir / "example.stderr").exists():
                stderr += (case_dir / "example.stderr").read_bytes()
            comparison = compare(ref_path.read_text(encoding="utf8"),
                                 actual.decode("utf8", errors="strict"),
                                 stderr.decode("utf8", errors="strict"),
                                 solver["exit"], example["exit"], plan)
            record = {"name": case["name"], "input_sha256": sha(input_path),
                      "reference_output_sha256": sha(ref_path),
                      "actual_output_sha256": sha(case_dir / "combined.out"),
                      "solver": solver, "example": example,
                      "wavefunction_sha256": sha(wf) if wf.exists() else None,
                      "comparison": comparison}
            write(case_dir / "result.json", record)
            cases.append(record)
            print(json.dumps({"completed_case": case["name"],
                              "printed_match": comparison["printed_output_match"],
                              "wall_s": solver["wall_monotonic_seconds"],
                              "peak_RSS_KiB": solver["peak_RSS_KiB"]}), flush=True)
            if not comparison["printed_output_match"]:
                statuses.extend(["H2SOLV_VENDOR_EXAMPLE_MISMATCH", "STOP"])
                break
        if len(cases) == 5 and all(x["comparison"]["printed_output_match"] for x in cases):
            # Do not equate matching printed energy with observing native convergence.
            statuses.extend(["ALL_FIVE_VENDOR_PRINTED_OUTPUTS_REPRODUCED",
                             "NATIVE_ROOT_CONVERGENCE_UNAVAILABLE",
                             "VENDOR_GUARD_QUALIFICATION_UNRESOLVED", "STOP"])
    for row in plan["vendor_inventory"]:
        assert sha(original / row["path"]) == row["sha256"]
        assert sha(build / row["path"]) == row["sha256"]
    verify_bindings(root, plan["protected_sha256"])
    for path, digest in plan["archive_file_sha256"].items():
        assert sha(Path(path)) == digest, "ARCHIVE BYTE DRIFT: " + path
    write(run / "result.json", {"statuses": statuses + ["NOT_CERTIFIED", "NOT_PRODUCTION_APPROVED"],
                               "build": build_result, "cases": cases,
                               "all_five_printed_outputs_match": len(cases) == 5 and all(x["comparison"]["printed_output_match"] for x in cases),
                               "strict_vendor_gate_pass": False,
                               "root_convergence_independently_observed": False,
                               "vendor_source_byte_mismatches": [],
                               "protected_byte_mismatches": [], "B1_R04_runs": 0,
                               "B2_started": False, "build_attempts_this_resume": 1})


if __name__ == "__main__":
    main()
