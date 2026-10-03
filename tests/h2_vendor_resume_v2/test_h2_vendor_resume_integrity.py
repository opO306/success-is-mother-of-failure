"""Actual vendor evidence integrity; native convergence remains unavailable."""
import ast
import hashlib
import json
from pathlib import Path

import pytest

from electronic_pilot.frontend_reference_v0.audit import verify
from electronic_pilot.h2_vendor_resume_v2.compare import compare

ROOT = Path(__file__).resolve().parents[2]
EV = ROOT / "docs/active/h2_vendor_build_resume_v2/evidence"


def read(name):
    return json.loads((EV / name).read_text(encoding="utf8"))


def test_single_static_build_and_scope():
    p, r = read("protocol.json"), read("result.json")
    assert p["build_attempts_allowed"] == r["build_attempts_this_resume"] == 1
    assert p["build_argv"] == ["make", "LD=gfortran -fopenmp",
                               "MPFR=/usr/lib/x86_64-linux-gnu/libmpfr.a /usr/lib/x86_64-linux-gnu/libgmp.a"]
    assert not p["source_edit_allowed"] and not p["merge_rebase_push_allowed"]
    assert r["build"]["exit"] == 0
    assert "README_SUPPORTED_BUILD_PATH_WORKS" in r["statuses"]
    assert not r["strict_vendor_gate_pass"]
    assert not r["root_convergence_independently_observed"]
    assert r["B1_R04_runs"] == 0 and not r["B2_started"]


@pytest.mark.parametrize("index", range(5))
def test_each_actual_case_reproduces_reference_bytes_but_not_unreported_convergence(index):
    record = read("result.json")["cases"][index]
    folder = EV / "cases" / record["name"]
    reference = (folder / "reference.out").read_bytes()
    actual = (folder / "combined.out").read_bytes()
    assert reference == actual
    assert hashlib.sha256(reference).hexdigest() == record["reference_output_sha256"]
    assert hashlib.sha256(actual).hexdigest() == record["actual_output_sha256"]
    assert record["solver"]["exit"] == record["example"]["exit"] == 0
    assert record["solver"]["peak_RSS_KiB"] > 0
    stderr = (folder / "solver.stderr").read_text(encoding="utf8") + (folder / "example.stderr").read_text(encoding="utf8")
    assert not stderr
    replayed = compare(reference.decode(), actual.decode(), stderr, 0, 0, read("protocol.json"))
    assert replayed == record["comparison"]
    assert replayed["native_iteration_limit_reached"] is None
    assert not replayed["independent_root_convergence_pass"]


def test_presealed_archive_and_source_wrapper_hashes():
    plan = read("protocol.json")
    assert hashlib.sha256((EV / "protocol.json").read_bytes()).hexdigest() == (EV / "protocol.sha256").read_text().strip()
    for path, digest in plan["wrapper_sha256"].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest
    for path, digest in plan["protected_sha256"].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest
    assert read("preservation.json")["protected_bindings"] == 61
    assert not read("preservation.json")["Attempt1_overwritten"]


def test_linkage_evidence_and_failure_warning_preserved():
    ldd = (EV / "h2solv.ldd.stdout").read_text(encoding="utf8")
    assert "libgfortran.so" in ldd and "libgomp.so" in ldd
    assert "libmpfr.so" not in ldd and "libgmp.so" not in ldd
    assert "mpfr_root" in (EV / "build.stderr").read_text(encoding="utf8")
    assert read("environment_before.json")["LDFLAGS"] is None


def test_wrapper_imports_only_own_comparator_and_standard_library():
    area = ROOT / "electronic_pilot/h2_vendor_resume_v2"
    forbidden = ("engine", "a_reference", "a_numeric", "electronic_pilot.solver")
    for path in area.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf8"))
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [x.name for x in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            assert not any(name.startswith(forbidden) for name in names)


def test_final_byte_seal():
    assert verify(read("final_seal.json")["bound_sha256"], ROOT, ROOT) >= 90


def test_byte_seal_rejects_mutated_output(tmp_path):
    key = "worktree:docs/active/h2_vendor_build_resume_v2/evidence/cases/H2.1.1.1.3_jc_sym/combined.out"
    digest = read("final_seal.json")["bound_sha256"][key]
    copy = tmp_path / key.split(":", 1)[1]
    copy.parent.mkdir(parents=True)
    original = (EV / "cases/H2.1.1.1.3_jc_sym/combined.out").read_bytes()
    copy.write_bytes(original + b"CORRUPTED")
    with pytest.raises(ValueError, match="BYTE DRIFT"):
        verify({key: digest}, tmp_path, tmp_path)
