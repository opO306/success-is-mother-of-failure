"""B0 (serial C++) against the A-Numeric VM, which is the judge.

docs/current/A_NUMERIC_EXECUTION_STACK_V1.md 4.1. Same straight-line programs,
same inputs; registers, branch records and halts must be identical. Skipped
when MSVC is not installed.
"""
from __future__ import annotations

import collections
import re
from concurrent.futures import ThreadPoolExecutor

import pytest

from a_numeric_native import harness as H

pytestmark = pytest.mark.skipif(H.find_vcvars() is None, reason="MSVC not installed")

# defect -> families that must expose it (a catch elsewhere does not count)
MUTANTS = {
    1: ("binary64 SUM as a sequential float reduction", {"b64_sum_dot"}),
    2: ("binary64 DOT rounding every product and addition", {"b64_sum_dot", "distance"}),
    3: ("overflow saturates to the largest finite value", {"b64_hard", "b64_stream", "b64_sum_dot", "b64_const"}),
    4: ("FX MUL rounds toward minus infinity", {"fx_exhaustive", "fx_wide"}),
    5: ("FX DIV/CONST ties toward zero", {"fx_exhaustive"}),
    6: ("binary64 exact rounding ties away from zero", {"b64_sum_dot"}),
    7: ("flush-to-zero / denormals-are-zero", {"b64_hard", "b64_stream"}),
    8: ("FX range check skipped", {"fx_exhaustive", "fx_wide"}),
    9: ("exact-zero SUM always +0", {"b64_sum_dot"}),
    10: ("CMP margin through a rounded subtraction", {"b64_stream"}),
    11: ("FX SQRT floor instead of nearest", {"fx_exhaustive", "fx_wide"}),
    12: ("binary64 CONST via double(num) / double(den)", {"b64_const"}),
}


@pytest.fixture(scope="module")
def cases():
    progs = {name: make() for name, make in H.FAMILIES.items()}
    return progs, {name: H.vm_expected(p) for name, p in progs.items()}


@pytest.fixture(scope="module")
def b0(tmp_path_factory):
    return H.build_b0(tmp_path_factory.mktemp("b0"))


@pytest.mark.parametrize("family", sorted(H.FAMILIES))
def test_b0_matches_vm(family, cases, b0) -> None:
    progs, expected = cases
    got = H.run_native(b0, progs[family])
    bad = H.mismatches(expected[family], got)
    assert not bad, [(progs[family][i][2], expected[family][i], got[i]) for i in bad[:3]]


def test_cases_are_not_vacuous(cases) -> None:
    """Each kind of outcome the judge can report actually occurs."""
    _, expected = cases
    halts = collections.Counter(e["halt"][1] for rows in expected.values() for e in rows if e["halt"])
    assert halts["overflow"] > 1000 and halts["sqrt_of_negative"] > 100 and halts["division_by_zero"] > 100
    assert sum(len(e["branches"]) for rows in expected.values() for e in rows) > 5000
    subnormal = sum(1 for e in expected["b64_hard"] for v in e["registers"].values()
                    if v != "0" * 16 and int(v, 16) & 0x7FF0000000000000 == 0)
    assert subnormal > 500
    assert sum(1 for e in expected["potentials"] if e["halt"] is None) > 1000


def test_b0_source_never_calls_the_vm() -> None:
    src = H.B0_SOURCE.read_text(encoding="utf-8")
    assert not re.search(r"a_numeric\b|Python\.h|popen|system\(", src)


def test_every_injected_defect_is_caught_where_it_should_be(cases, tmp_path_factory) -> None:
    progs, expected = cases
    out = tmp_path_factory.mktemp("b0_mutants")
    with ThreadPoolExecutor(len(MUTANTS)) as pool:
        exes = dict(zip(MUTANTS, pool.map(lambda i: H.build_b0(out, i), MUTANTS)))
    for i, (label, must) in MUTANTS.items():
        caught = {f for f in must if H.mismatches(expected[f], H.run_native(exes[i], progs[f]))}
        assert caught == must, (i, label, sorted(must - caught))
