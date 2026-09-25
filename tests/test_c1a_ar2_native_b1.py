"""C1-A B1: the parallel CPU evaluator of the Ar-Ar V(R) and F(R) against the fixture and B0.

designer 9th ed. item 5: B1 only after B0 passed. Thread count, query layout (chunk / stride) and the
per-query component split must not change a bit. Two injected defects each hide in some layout
(T = 1, or no component split) and must be caught in another. Skipped when MSVC is absent.
"""
from __future__ import annotations

import pytest

import a_reference.ar2_lang2024_fixture as X
from a_numeric_native.harness import find_vcvars
from a_physics_native import harness as H

pytestmark = pytest.mark.skipif(find_vcvars() is None, reason="MSVC not installed")

FIX = X.load()
VF = {"V": ("V", True), "V_ret_off": ("V", False), "F": ("F", True), "F_ret_off": ("F", False)}
LAYOUTS = [(1, "chunk"), (2, "chunk"), (4, "stride"), (8, "chunk"), (12, "stride"), (1, "split"), (4, "split")]


def queries():
    qs, want = [], []
    for c in FIX["cases"]:
        for name, (q, ret) in VF.items():
            qs.append((q, ret, c["profile"], c["R_raw"]))
            beyond = c["R_bohr_approx"] > H.B0_R_MAX_BOHR
            want.append({"refuse": "beyond_native_range"} if beyond else c["results"][name])
    return qs, want


def n_bad(got, want):
    return sum((g if "refuse" in w else H.as_outcome(g)) != w for g, w in zip(got, want))


@pytest.fixture(scope="module")
def exes(tmp_path_factory):
    d = tmp_path_factory.mktemp("ar2b1")
    return {n: H.build("b1", d, n) for n in (0, 101, 102)} | {"b0": H.build("b0", d)}


def test_b1_equals_fixture_and_b0_in_every_layout(exes) -> None:
    qs, want = queries()
    b0 = H.run(exes["b0"], qs)
    for T, layout in LAYOUTS:
        got = H.run(exes[0], qs, (T, layout))
        assert n_bad(got, want) == 0, (T, layout)
        assert got == b0, (T, layout)                 # same bits AND the same precision M used


def test_layout_dependent_defects_are_caught_where_they_show(exes) -> None:
    qs, want = queries()
    dropped = {lay: n_bad(H.run(exes[101], qs, lay), want) for lay in LAYOUTS}
    assert all(v == 0 for (T, l), v in dropped.items() if l != "split")      # hides without the split
    assert all(v > 0 for (T, l), v in dropped.items() if l == "split")
    last_thread = {lay: n_bad(H.run(exes[102], qs, lay), want) for lay in LAYOUTS}
    assert all(v == 0 for (T, l), v in last_thread.items() if T == 1)         # hides at T = 1
    assert all(v > 0 for (T, l), v in last_thread.items() if T > 1)
