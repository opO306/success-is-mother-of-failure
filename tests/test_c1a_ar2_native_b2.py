"""C1-A B2: the CUDA evaluator of the Ar-Ar V(R) and F(R) against the fixture and B0.

designer 9th ed. item 5: B2 only after B1 matched B0. Device arithmetic is written separately from the host
core. Block size, grid size and launch chunking must not change a bit (E9); precision and width limits must
surface as refusals, never as wrong bits. Skipped without MSVC, nvcc or a CUDA device.
"""
from __future__ import annotations

import pytest

import a_reference.ar2_lang2024_fixture as X
from a_numeric_native.harness import cuda_device_present, find_nvcc, find_vcvars
from a_physics_native import harness as H

pytestmark = pytest.mark.skipif(find_vcvars() is None or find_nvcc() is None or not cuda_device_present(),
                                reason="MSVC, nvcc or a CUDA device missing")

FIX = X.load()
VF = {"V": ("V", True), "V_ret_off": ("V", False), "F": ("F", True), "F_ret_off": ("F", False)}
LAYOUTS = [(1, 0, 0), (32, 0, 0), (64, 3, 0), (256, 0, 0), (128, 2, 100), (32, 1, 7)]


def queries():
    qs, want = [], []
    for c in FIX["cases"]:
        for name, (q, ret) in VF.items():
            qs.append((q, ret, c["profile"], c["R_raw"]))
            beyond = c["R_bohr_approx"] > H.B0_R_MAX_BOHR
            want.append({"refuse": "beyond_native_range"} if beyond else c["results"][name])
    return qs, want


def tally(got, want):
    """(answers with wrong bits, refusals the fixture does not expect)"""
    wrong = refused = 0
    for g, w in zip(got, want):
        if "refuse" in g and "refuse" not in w:
            refused += 1
        elif (g if "refuse" in w else H.as_outcome(g)) != w:
            wrong += 1
    return wrong, refused


@pytest.fixture(scope="module")
def exes(tmp_path_factory):
    d = tmp_path_factory.mktemp("ar2b2")
    out = {n: H.build("b2", d, n) for n in (0, 201, 202, 204, 205)}
    out["b0"] = H.build("b0", d)
    out["width"] = H.build("b2", d, 206, {"AR2_FORCE_M": 384})
    out["cap"] = H.build("b2", d, 0, {"NATIVE_AR2_MAX_ATTEMPTS": 1})
    return out


def test_b2_gives_the_fixture_bits_in_every_layout(exes) -> None:
    qs, want = queries()
    b0 = H.run(exes["b0"], qs)
    for lay in LAYOUTS:
        got = H.run(exes[0], qs, lay)
        assert tally(got, want) == (0, 0), lay
        assert got == b0, lay                   # same bits and the same precision M as B0


def test_injected_defects_are_caught(exes) -> None:
    qs, want = queries()
    for n in (201, 202, 204):                   # truncation, no refinement, force term dropped
        for lay in ((32, 0, 0), (128, 0, 0)):
            assert sum(tally(H.run(exes[n], qs, lay), want)) > 0, (n, lay)
    # 205: threads past the first warp at a fixed low precision -- hidden while blocks have <= 32 threads
    assert tally(H.run(exes[205], qs, (32, 0, 0)), want) == (0, 0)
    assert tally(H.run(exes[205], qs, (1, 0, 0)), want) == (0, 0)
    assert sum(tally(H.run(exes[205], qs, (128, 0, 0)), want)) > 0


def test_width_and_precision_limits_refuse_never_guess(exes) -> None:
    qs, want = queries()
    got = H.run(exes["width"], qs, (128, 0, 0))   # 36 limbs, every query at M = 384
    wrong, refused = tally(got, want)
    assert wrong == 0 and refused > 100
    assert {g["refuse"] for g in got if "refuse" in g} >= {"device_width"}
    got = H.run(exes["cap"], qs, (128, 0, 0))     # one attempt only (M = 96)
    wrong, refused = tally(got, want)
    assert wrong == 0 and refused > 50
    assert {g["refuse"] for g in got if "refuse" in g} >= {"device_precision_cap"}
