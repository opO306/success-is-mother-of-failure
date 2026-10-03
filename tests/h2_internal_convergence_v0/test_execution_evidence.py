"""Verify acquired native evidence, immutable source, and isolated real mutants."""
import ast
import hashlib
import json
from pathlib import Path

import pytest

from electronic_pilot.h2_internal_convergence_v0.instrument import strip_observer, low_itmax
from electronic_pilot.h2_internal_convergence_v0.observe import parse
from electronic_pilot.h2_internal_convergence_v0.snapshot import calibration, context, sha

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "runs/h2_representation_pilot1/internal_convergence_v0_20261003"
NAMES = ["H2.0.1.1.6_h-h+", "H2.1.1.1.3_jc_sym", "H2.1.1.1.6_h2_sym",
         "H2.1.1.2.3_jc_asym", "H2.1.1.2.6_general"]


def read(path):
    return json.loads(path.read_text(encoding="utf8"))


def test_sealed_plan_and_protected_originals():
    plan = read(RUN / "protocol.json")
    assert sha(RUN / "protocol.json") == (RUN / "protocol.sha256").read_text().strip()
    for path, expected in plan["protected_sha256"].items():
        assert sha(ROOT / path) == expected, path
    for path, expected in plan["wrapper_sha256"].items():
        assert sha(ROOT / path) == expected, path
    assert read(RUN / "preservation.json")["mismatch_count"] == 0


def test_observation_only_and_separate_sources():
    plan = read(RUN / "protocol.json")
    source = (ROOT / plan["original_tree"] / "h2solv/f/h2solv.f").read_bytes()
    observed = (ROOT / plan["builds"]["audit_build"]["source_path"]).read_bytes()
    mutant = (ROOT / plan["builds"]["mutant_low_itmax_build"]["source_path"]).read_bytes()
    assert strip_observer(observed) == source
    assert mutant == low_itmax(observed)
    assert len({hashlib.sha256(s).hexdigest() for s in (source, observed, mutant)}) == 3
    for label, metadata in plan["builds"].items():
        assert sha(ROOT / metadata["source_path"]) == metadata["source_sha256"]


@pytest.mark.parametrize("name", NAMES)
def test_fresh_vendor_audit_and_original_reference_all_equal(name):
    plan = read(RUN / "protocol.json")
    case = next(c for c in plan["examples"] if c["name"] == name)
    folder = RUN / "cases" / name
    source = ROOT / plan["original_tree"] / case["reference_path"]
    reference = source.read_bytes()
    for role in ("VENDOR", "AUDIT"):
        assert (folder / role / "combined.out").read_bytes() == reference
        assert read(folder / role / "solver.process.json")["exit"] == 0
        assert read(folder / role / "example.process.json")["exit"] == 0
        assert (folder / role / "solver.stderr").read_bytes() == b""
    assert (folder / "VENDOR/wf_7.dat").read_bytes() == (folder / "AUDIT/wf_7.dat").read_bytes()
    observed = parse(folder / "AUDIT/audit_invsg.log")
    assert observed == read(folder / "observation.json")
    assert observed["inverse_iteration_supported"]
    assert not observed["maxit_exhausted"]
    assert all(row["error"] == 0 for row in observed["leq1s"])
    assert observed["final_ierror"] == 0
    ctx = context()
    expected = 16 * observed["dimension"] * ctx.mpf("1e-64")
    assert abs(ctx.mpf(observed["errest"]) - expected) <= ctx.ldexp(expected, -380)
    measurements = read(folder / "AUDIT/independent_residual.json")
    assert measurements["status"] == "MEASURED_ONLY_NO_ACCEPTANCE_THRESHOLD"
    assert measurements["decimal_digits"] == 160
    assert not measurements["formal_or_interval_certificate"]
    assert sha(folder / "AUDIT/audit_HS.bin") == measurements["matrix_snapshot"]["sha256"]
    assert sha(folder / "AUDIT/audit_EV.bin") == measurements["returned_state_snapshot"]["sha256"]
    assert not measurements["root_diagnostic"].get("root_contradiction", False)


def test_real_low_itmax_fault_is_detected_even_with_exit_zero():
    x = read(RUN / "mutants/LOW_ITMAX/result.json")
    assert x["process"]["solver"]["exit"] == 0
    assert x["observation"]["final_ierror"] == 0
    assert x["observation"]["ITMAX"] == 1
    assert x["observation"]["actual_iteration_count"] == 1
    assert x["observation"]["termination_reason"] == "MAXIT_EXHAUSTED"
    assert x["detected"] and not x["physical_result_eligible"]
    assert not x["observation"]["inverse_iteration_supported"]


def test_bad_en_mutant_is_isolated_and_count_changes():
    x = read(RUN / "mutants/BAD_EN/result.json")
    baseline = read(RUN / "cases/H2.1.1.1.3_jc_sym/observation.json")
    assert x["detected_inertia_change"] and not x["physical_result_eligible"]
    assert x["observation"]["number_of_eigenvalues_below_initial_EN_source_reported"] != baseline["number_of_eigenvalues_below_initial_EN_source_reported"]
    assert (RUN / "mutant_bad_en_binary/h2solv").read_bytes() == (RUN / "audit_build/h2solv/f/h2solv").read_bytes()
    original = RUN / "cases/H2.1.1.1.3_jc_sym/AUDIT"
    assert (RUN / "mutants/BAD_EN/audit_HS.bin").read_bytes() == (original / "audit_HS.bin").read_bytes()
    assert (RUN / "mutants/LOW_ITMAX/audit_HS.bin").read_bytes()[72:] == (original / "audit_HS.bin").read_bytes()[72:]
    original_input = (original / "input.inp").read_bytes().splitlines()
    changed_input = (RUN / "mutants/BAD_EN/input.inp").read_bytes().splitlines()
    assert len(original_input) == len(changed_input) == 15
    assert all(a == b for i, (a, b) in enumerate(zip(original_input, changed_input)) if i != 10)


def test_native_calibration_preserved():
    assert calibration(RUN / "probe/probe.bin") == read(RUN / "calibration.json")


def test_terminates_here_and_does_not_upgrade_residual_or_root():
    result = read(RUN / "result.json")
    assert len(result["cases"]) == 5 and len(result["mutants"]) == 2
    assert "first_failure" not in result
    assert result["R04_runs"] == 0 and not result["B2_started"] and not result["push"]
    assert result["overall_residual_qualification"] == "MEASURED_ONLY_NO_ACCEPTANCE_THRESHOLD"
    assert "H2SOLV_GENERALIZED_RESIDUAL_SUPPORTED" not in result["statuses"]
    assert "H2SOLV_VENDOR_INTERNAL_SOLVER_CONVERGENCE_SUPPORTED" not in result["statuses"]
    assert result["statuses"][-3:] == ["STOP", "NOT_CERTIFIED", "NOT_PRODUCTION_APPROVED"]


def test_independent_path_import_boundaries():
    folder = ROOT / "electronic_pilot/h2_internal_convergence_v0"
    for filename in ("residual.py", "snapshot.py", "observe.py"):
        source = (folder / filename).read_text(encoding="utf8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue
            assert not any(name.startswith(("engine", "audit", "electronic_pilot.h2_vendor", "mpfun")) for name in names)
