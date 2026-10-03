"""Bounded VENDOR/AUDIT/MUTANT orchestration on local Windows + WSL.

Prepare once, seal before execution, stop on first authoritative contradiction.
Large native snapshots remain in runs. No new R04 input or B2 implementation.
"""
import argparse
import datetime
import difflib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

from .instrument import bad_en, helper_bytes, instrument, low_itmax, strip_observer
from .observe import parse
from .snapshot import calibration, sha

BUILD = ["make", "LD=gfortran -fopenmp",
         "MPFR=/usr/lib/x86_64-linux-gnu/libmpfr.a /usr/lib/x86_64-linux-gnu/libgmp.a"]


def write(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=True) + "\n", encoding="utf8")


def linux(path):
    absolute = Path(path).resolve().as_posix()
    if len(absolute) < 3 or absolute[1:3] != ":/":
        raise ValueError("expected absolute Windows drive path")
    return "/mnt/" + absolute[0].lower() + "/" + absolute[3:]


def host(path):
    text = str(path)
    if text.startswith("/mnt/") and text[6:7] == "/":
        return Path(text[5].upper() + ":/" + text[7:])
    return Path(text)


def native(argv, cwd, folder, stem, stdin_path=None):
    folder.mkdir(parents=True, exist_ok=True)
    metrics = folder / (stem + ".time")
    command = ["wsl.exe", "-d", "Ubuntu-24.04", "--cd", linux(cwd), "--",
               "/usr/bin/env", "OMP_NUM_THREADS=1", "OMP_DYNAMIC=FALSE",
               "/usr/bin/time", "-f", "%e %U %S %M %x", "-o", linux(metrics),
               "/usr/bin/timeout", "--kill-after=5s", "600s", *argv]
    start = time.monotonic()
    completed = subprocess.run(command, input=stdin_path.read_bytes() if stdin_path else b"",
                               capture_output=True, timeout=620)
    (folder / (stem + ".stdout")).write_bytes(completed.stdout)
    (folder / (stem + ".stderr")).write_bytes(completed.stderr)
    result = dict(command=command, exit=completed.returncode,
                  wall_windows_seconds=time.monotonic() - start,
                  stdout_sha256=sha(folder / (stem + ".stdout")),
                  stderr_sha256=sha(folder / (stem + ".stderr")))
    if metrics.exists():
        for line in reversed(metrics.read_text().splitlines()):
            fields = line.split()
            if len(fields) == 5:
                try:
                    result.update(elapsed_seconds=float(fields[0]), cpu_user_seconds=float(fields[1]),
                                  cpu_system_seconds=float(fields[2]), peak_RSS_KiB=int(fields[3]))
                    break
                except ValueError:
                    continue
    write(folder / (stem + ".process.json"), result)
    return result


def verify(root, bindings):
    for path, digest in bindings.items():
        if sha(root / path) != digest:
            raise ValueError("BYTE DRIFT: " + path)


def prepare(root, run):
    run.mkdir(parents=True, exist_ok=False)
    previous = root / "docs/active/h2_vendor_build_resume_v2/evidence"
    old = json.loads((previous / "protocol.json").read_text())
    original = root / old["original_tree"]
    protected = dict(old["protected_sha256"])
    for dirname in ("h2_representation_pilot1", "h2_representation_pilot1_resume_v1", "h2_vendor_build_resume_v2"):
        for path in (root / "docs/active" / dirname).rglob("*"):
            if path.is_file():
                protected[path.relative_to(root).as_posix()] = sha(path)
    for dirname in ("h2_vendor_resume_v2",):
        for path in (root / "electronic_pilot" / dirname).glob("*"):
            if path.is_file():
                protected[path.relative_to(root).as_posix()] = sha(path)
    for row in old["vendor_inventory"]:
        path = original / row["path"]
        assert sha(path) == row["sha256"]
        protected[path.relative_to(root).as_posix()] = row["sha256"]
    vendor = root / "runs/h2_representation_pilot1/vendor_build_resume_v2_20261003/vendor_build/h2solv/f"
    for name in ("h2solv", "example"):
        digest = json.loads((previous / (name + ".binary.json")).read_text())["sha256"]
        assert sha(vendor / name) == digest
        protected[(vendor / name).relative_to(root).as_posix()] = digest
    source = (original / "h2solv/f/h2solv.f").read_bytes()
    observed = instrument(source, helper_bytes())
    sources = {}
    for label, patched in (("audit_build", observed), ("mutant_low_itmax_build", low_itmax(observed))):
        build = run / label
        shutil.copytree(original, build)
        target = build / "h2solv/f/h2solv.f"
        target.write_bytes(patched)
        diff = "".join(difflib.unified_diff(source.decode("ascii").splitlines(True),
                                            patched.decode("ascii").splitlines(True),
                                            fromfile="VENDOR/h2solv.f", tofile=label + "/h2solv.f", n=2))
        (run / (label + ".patch")).write_text(diff, encoding="ascii")
        sources[label] = dict(source_sha256=sha(target), source_path=target.relative_to(root).as_posix(),
                              observation_blocks_strip_to_original=strip_observer(patched) == source,
                              patch_sha256=sha(run / (label + ".patch")))
    probe = run / "probe"
    probe.mkdir()
    for name in ("observer.f", "probe.f"):
        shutil.copyfile(Path(__file__).with_name(name), probe / name)
    # Snapshot all code/plan bytes before either native compilation or new execution.
    wrapper = {path.relative_to(root).as_posix(): sha(path)
               for path in Path(__file__).parent.glob("*") if path.is_file()}
    plan_path = root / "docs/active/h2_internal_convergence_v0/PLAN.md"
    wrapper[plan_path.relative_to(root).as_posix()] = sha(plan_path)
    for path in (root / "tests/h2_internal_convergence_v0").glob("*.py"):
        wrapper[path.relative_to(root).as_posix()] = sha(path)
    git = dict(HEAD=subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip(),
               branch=subprocess.check_output(["git", "branch", "--show-current"]).decode().strip(),
               start_clean_verified_before_implementation=True,
               prepare_status=subprocess.check_output(["git", "status", "--short", "--branch"]).decode("utf8"),
               origin_live_refs=subprocess.check_output(["git", "ls-remote", "origin", "refs/heads/master", "refs/heads/codex/h2-representation-pilot1"]).decode(),
               ahead_behind=subprocess.check_output(["git", "rev-list", "--left-right", "--count", "HEAD...origin/codex/h2-representation-pilot1"]).decode().strip(),
               auto_merge_rebase=False, push=False)
    write(run / "git_start.json", git)
    env = subprocess.run(["wsl.exe", "-d", "Ubuntu-24.04", "--", "/usr/bin/env"], capture_output=True)
    # Whitelist non-secret environment fields, rather than preserving an entire environment dump.
    visible = {}
    for line in env.stdout.decode("utf8").splitlines():
        key, _, value = line.partition("=")
        if key in ("LANG", "LC_ALL", "OMP_NUM_THREADS", "OMP_DYNAMIC", "LDFLAGS"):
            visible[key] = value
    write(run / "environment.json", dict(inherited_fields=visible,
          native_overrides={"OMP_NUM_THREADS": "1", "OMP_DYNAMIC": "FALSE"},
          previous_environment_sha256=sha(previous / "environment_before.json"),
          previous_environment=json.loads((previous / "environment_before.json").read_text()),
          python_executable=sys.executable, python_version=sys.version))
    archives = {str(host(path)): digest for path, digest in old["archive_file_sha256"].items()}
    for path, digest in archives.items():
        assert sha(path) == digest, "archive provenance mismatch"
    plan = dict(sealed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                purpose="H2SOLV native termination observation and independent stored-matrix residual",
                original_tree=old["original_tree"], vendor_binary_directory=vendor.relative_to(root).as_posix(),
                examples=old["examples"], vendor_inventory=old["vendor_inventory"],
                archive_file_sha256=archives, protected_sha256=protected,
                wrapper_sha256=wrapper, builds=sources, build_argv=BUILD,
                observer_probe_expected="0,-3/2,1+2^-100,-2^100,2^-300,25/8",
                residual_decimal_digits=160, acceptance="MEASURED_ONLY_NO_ACCEPTANCE_THRESHOLD",
                R04_runs=0, B2_started=False, push=False, scope_ends="STOP")
    write(run / "protocol.json", plan)
    (run / "protocol.sha256").write_text(sha(run / "protocol.json") + "\n", encoding="ascii")
    print(json.dumps({"prepared": str(run), "protocol_sha256": sha(run / "protocol.json"),
                      "protected_bindings": len(protected), "wrapper_bindings": len(wrapper)}), flush=True)


def solver(root, binary_folder, case, source_input, folder):
    folder.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(source_input, folder / "input.inp")
    process = native([linux(binary_folder / "h2solv")], folder, folder, "solver", source_input)
    example = {"exit": None, "not_executed": True}
    wf = folder / "wf_7.dat"
    if process["exit"] == 0 and wf.exists():
        example = native([linux(binary_folder / "example")], folder, folder, "example", wf)
    output = (folder / "solver.stdout").read_bytes()
    if (folder / "example.stdout").exists():
        output += (folder / "example.stdout").read_bytes()
    (folder / "combined.out").write_bytes(output)
    return dict(solver=process, example=example, combined_output_sha256=sha(folder / "combined.out"),
                wavefunction_sha256=sha(wf) if wf.exists() else None)


def execute(root, run):
    plan = json.loads((run / "protocol.json").read_text())
    assert sha(run / "protocol.json") == (run / "protocol.sha256").read_text().strip()
    with (run / "execution_started.json").open("x", encoding="utf8") as handle:
        json.dump({"protocol_sha256": sha(run / "protocol.json"),
                   "started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat()}, handle)
    verify(root, plan["protected_sha256"])
    verify(root, plan["wrapper_sha256"])
    for path, digest in plan["archive_file_sha256"].items():
        assert sha(Path(path)) == digest
    for label, metadata in plan["builds"].items():
        assert sha(root / metadata["source_path"]) == metadata["source_sha256"]
    result = dict(protocol_sha256=sha(run / "protocol.json"), cases=[], mutants=[],
                  statuses=[], R04_runs=0, B2_started=False, push=False,
                  overall_residual_qualification="MEASURED_ONLY_NO_ACCEPTANCE_THRESHOLD",
                  integral_truncation_convergence="UNRESOLVED")
    try:
        audit_build = run / "audit_build/h2solv/f"
        build = native(plan["build_argv"], audit_build, run, "audit_build")
        result["build"] = build
        assert build["exit"] == 0, "AUDIT build failed"
        for name in ("h2solv", "example"):
            write(run / ("audit_" + name + ".binary.json"), dict(sha256=sha(audit_build / name), bytes=(audit_build / name).stat().st_size))
        probe = run / "probe"
        argv = ["gfortran", "-O3", "-fno-underscoring", "-fopenmp", "-ffixed-line-length-132",
                linux(probe / "probe.f"), linux(probe / "observer.f"),
                "mpmodule.o", "mpfuna.o", "mpfunf.o", "mpfung1.o", "mpinterface.o",
                "/usr/lib/x86_64-linux-gnu/libmpfr.a", "/usr/lib/x86_64-linux-gnu/libgmp.a",
                "-o", linux(probe / "snapshot_probe")]
        probe_build = native(argv, audit_build, probe, "build")
        assert probe_build["exit"] == 0, "observer probe build failed"
        probe_process = native([linux(probe / "snapshot_probe")], probe, probe, "probe")
        assert probe_process["exit"] == 0, "observer probe process failed"
        result["calibration"] = calibration(probe / "probe.bin")
        write(run / "calibration.json", result["calibration"])
        print(json.dumps({"build": "AUDIT_BUILD_PASS", "calibration": result["calibration"]["status"]}), flush=True)
        vendor_build = root / plan["vendor_binary_directory"]
        original = root / plan["original_tree"]
        for case in plan["examples"]:
            folder = run / "cases" / case["name"]
            folder.mkdir(parents=True, exist_ok=False)
            inp = original / case["input_path"]
            reference = original / case["reference_path"]
            assert sha(inp) == case["input_sha256"] and sha(reference) == case["reference_sha256"]
            vendor = solver(root, vendor_build, case, inp, folder / "VENDOR")
            audit_record = solver(root, audit_build, case, inp, folder / "AUDIT")
            observation = parse(folder / "AUDIT/audit_invsg.log")
            write(folder / "observation.json", observation)
            processes_ok = all(p["solver"]["exit"] == 0 and p["example"]["exit"] == 0 for p in (vendor, audit_record))
            clean_stderr = all((folder / role / (stem + ".stderr")).stat().st_size == 0 for role in ("VENDOR", "AUDIT") for stem in ("solver", "example"))
            identical = vendor["combined_output_sha256"] == audit_record["combined_output_sha256"] == sha(reference)
            wf_identical = vendor["wavefunction_sha256"] == audit_record["wavefunction_sha256"]
            record = dict(name=case["name"], input_sha256=sha(inp), reference_output_sha256=sha(reference),
                          vendor=vendor, audit=audit_record, scientific_output_byte_identical=identical,
                          wavefunction_byte_identical=wf_identical, clean_stderr=clean_stderr,
                          observation=observation)
            result["cases"].append(record)
            write(folder / "result.json", record)
            assert processes_ok and clean_stderr and identical and wf_identical, "authoritative output noninterference failed"
            assert observation["inverse_iteration_supported"], "authoritative invsg termination/error contradiction"
            env = dict(os.environ, OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1", OMP_NUM_THREADS="1")
            start = time.monotonic()
            independent = subprocess.run([sys.executable, "-m", "electronic_pilot.h2_internal_convergence_v0.residual",
                                          "--folder", str(folder / "AUDIT")], cwd=root, env=env,
                                         capture_output=True, timeout=600)
            (folder / "independent.stdout").write_bytes(independent.stdout)
            (folder / "independent.stderr").write_bytes(independent.stderr)
            write(folder / "independent.process.json", dict(exit=independent.returncode,
                  wall_seconds=time.monotonic() - start, python=sys.executable))
            assert independent.returncode == 0, "independent residual process failed"
            measured = json.loads((folder / "AUDIT/independent_residual.json").read_text())
            record["independent_residual"] = measured
            write(folder / "result.json", record)
            assert not measured["root_diagnostic"].get("root_contradiction", False), "qualified root diagnostic contradiction"
            print(json.dumps({"completed_case": case["name"], "output_byte_identical": identical,
                              "iterations": observation["actual_iteration_count"],
                              "reason": observation["termination_reason"],
                              "residual_l2": measured["measurements"]["residual_l2"],
                              "root_status": measured["root_diagnostic"]["root_selection"]}), flush=True)
        # Only isolated observer tests may change iteration limit or EN.
        case = next(c for c in plan["examples"] if "jc_sym" in c["name"])
        mutant_build = run / "mutant_low_itmax_build/h2solv/f"
        mutant_build_result = native(plan["build_argv"], mutant_build, run, "mutant_build")
        assert mutant_build_result["exit"] == 0, "mutant build failed"
        folder = run / "mutants/LOW_ITMAX"
        process = solver(root, mutant_build, case, original / case["input_path"], folder)
        observation = parse(folder / "audit_invsg.log")
        mutant = dict(label="LOW_ITMAX", process=process, observation=observation,
                      physical_result_eligible=False, detected=observation["maxit_exhausted"] and not observation["inverse_iteration_supported"])
        write(folder / "result.json", mutant)
        result["mutants"].append(mutant)
        assert process["solver"]["exit"] == 0 and mutant["detected"], "MAXIT_EXHAUSTED fault not detected"
        # Duplicate the AUDIT binary into a separate observer-only input mutant directory.
        bad_build = run / "mutant_bad_en_binary"
        bad_build.mkdir()
        for name in ("h2solv", "example"):
            shutil.copyfile(audit_build / name, bad_build / name)
        bad_input = run / "mutant_bad_en.inp"
        bad_input.write_bytes(bad_en((original / case["input_path"]).read_bytes()))
        folder = run / "mutants/BAD_EN"
        process = solver(root, bad_build, case, bad_input, folder)
        observation = parse(folder / "audit_invsg.log")
        baseline = next(c for c in result["cases"] if c["name"] == case["name"])["observation"]
        changed = observation.get("number_of_eigenvalues_below_initial_EN_source_reported") != baseline.get("number_of_eigenvalues_below_initial_EN_source_reported")
        mutant = dict(label="BAD_EN_MINUS_2", process=process, observation=observation,
                      physical_result_eligible=False, detected_inertia_change=changed,
                      binary_is_separate_path_identical_to_AUDIT=True, input_sha256=sha(bad_input))
        write(folder / "result.json", mutant)
        result["mutants"].append(mutant)
        assert process["solver"]["exit"] == 0 and changed, "bad EN inertia change not detected"
        result["statuses"] = ["H2SOLV_VENDOR_OUTPUT_REPRODUCTION_PASS", "H2SOLV_INSTRUMENTATION_NONINTERFERENCE_PASS",
                              "H2SOLV_INVERSE_ITERATION_CONVERGENCE_SUPPORTED", "H2SOLV_MAXIT_EXHAUSTION_DETECTION_SUPPORTED",
                              "H2SOLV_GENERALIZED_RESIDUAL_MEASURED_ACCEPTANCE_UNRESOLVED",
                              "H2SOLV_ROOT_SELECTION_UNRESOLVED", "H2SOLV_INTEGRAL_TRUNCATION_CONVERGENCE_UNRESOLVED"]
    except Exception as exc:
        result["statuses"] = ["H2SOLV_VENDOR_INTERNAL_CONVERGENCE_UNRESOLVED"]
        result["first_failure"] = type(exc).__name__ + ": " + str(exc)
        print(json.dumps({"STOP": result["first_failure"]}), flush=True)
    finally:
        verify(root, plan["protected_sha256"])
        verify(root, plan["wrapper_sha256"])
        for path, digest in plan["archive_file_sha256"].items():
            assert sha(Path(path)) == digest
        for label, metadata in plan["builds"].items():
            assert sha(root / metadata["source_path"]) == metadata["source_sha256"]
        write(run / "preservation.json", dict(protected_bindings=len(plan["protected_sha256"]),
                                              wrapper_bindings=len(plan["wrapper_sha256"]),
                                              mismatch_count=0, before_and_after_verified=True))
        result["statuses"] += ["STOP", "NOT_CERTIFIED", "NOT_PRODUCTION_APPROVED"]
        write(run / "result.json", result)
    return 1 if "first_failure" in result else 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--prepare", action="store_true")
    args = parser.parse_args()
    root = Path.cwd()
    run = root / args.run
    if args.prepare:
        prepare(root, run)
    else:
        raise SystemExit(execute(root, run))


if __name__ == "__main__":
    main()
