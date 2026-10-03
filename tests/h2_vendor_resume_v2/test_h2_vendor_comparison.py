"""Fault injection of observable wrapper failures, not solver certification."""
import pytest

from electronic_pilot.h2_vendor_resume_v2.compare import compare


PLAN = {"comparison": {"energy_absolute_Eh": "1e-17",
                       "float_token_abs_relative": "5e-16"}}
TEXT = """James-Coolidge SYM basis: X = Y = 0; U = W
integrals completed
Hamitonian matrix completed
Work. prec. for integr.: 80
Work. prec. for lin. alg.: 60
Rank (OMEGA): 7
Length of Taylor series: 80
Type 1 of restriction: 1
Type 2 of restriction: 1
Basis size: 228
A <-> B symmetry: GERADE
r1 <-> r2 symmetry: SYM
Resulting energy:
EN = -1.057326153651244754e0
Input OK
4*Pi*DELTA(r12) = 0.3115301186773375E-01
"""


def result(text=TEXT, stderr="", solver_exit=0, example_exit=0):
    return compare(TEXT, text, stderr, solver_exit, example_exit, PLAN)


def test_exact_printed_match_does_not_claim_unreported_root_convergence():
    out = result()
    assert out["printed_output_match"] and out["energy_exact_decimal_match"]
    assert out["native_iteration_count"] is None
    assert out["native_iteration_limit_reached"] is None
    assert out["native_root_convergence"].startswith("UNAVAILABLE")
    assert not out["independent_root_convergence_pass"]
    assert not out["lowest_root_certified"]


def test_whitespace_differences_are_accepted():
    assert result(TEXT.replace(" ", "  "))["printed_output_match"]


@pytest.mark.parametrize("old,new", [
    ("Basis size: 228", "Basis size: 227"),
    ("Type 1 of restriction: 1", "Type 1 of restriction: 0"),
    ("for lin. alg.: 60", "for lin. alg.: 40"),
    ("symmetry: GERADE", "symmetry: UNGERADE"),
    ("Length of Taylor series: 80", "Length of Taylor series: 40"),
])
def test_scientific_structure_mismatch_rejected(old, new):
    assert not result(TEXT.replace(old, new))["printed_output_match"]


@pytest.mark.parametrize("value", ["-1.057326153651244700e0", "NaN", "Inf"])
def test_changed_or_nonfinite_energy_rejected_even_with_exit_zero(value):
    assert not result(TEXT.replace("-1.057326153651244754e0", value))["printed_output_match"]


def test_energy_tolerance_boundary_uses_decimal_not_binary_float():
    inside = result(TEXT.replace("-1.057326153651244754e0", "-1.057326153651244744e0"))
    outside = result(TEXT.replace("-1.057326153651244754e0", "-1.057326153651244743e0"))
    assert inside["printed_output_match"]
    assert not inside["energy_exact_decimal_match"]
    assert not outside["printed_output_match"]


@pytest.mark.parametrize("stderr", ["invsg: error = 65", "iteration limit reached",
                                    "WARNING: integral evaluation", "NaN"])
def test_reported_failure_rejected_with_matching_energy_and_exit_zero(stderr):
    assert not result(stderr=stderr)["printed_output_match"]


@pytest.mark.parametrize("solver,example", [(1, 0), (0, 1), (None, 0), (0, None)])
def test_process_failure_or_unexecuted_probe_rejected(solver, example):
    assert not result(solver_exit=solver, example_exit=example)["printed_output_match"]


@pytest.mark.parametrize("marker", ["integrals completed", "Hamitonian matrix completed",
                                    "Input OK", "EN = -1.057326153651244754e0"])
def test_incomplete_output_rejected(marker):
    assert not result(TEXT.replace(marker, ""))["printed_output_match"]


def test_duplicate_energy_rejected():
    assert not result(TEXT + "EN = -1.057326153651244754e0\n")["printed_output_match"]


def test_delta_probe_mismatch_not_hidden_by_final_energy_match():
    assert not result(TEXT.replace("0.3115301186773375E-01", "0.4115301186773375E-01"))["printed_output_match"]
