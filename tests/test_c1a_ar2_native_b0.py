"""C1-A B0: the serial C++ evaluator of the Ar-Ar V(R) and F(R) = -dV/dR against the reference.

docs/current/A_MICRO_V6_ARAR_POTENTIAL_SURVEY_V1.md 11 (designer 9th ed., item 4). The judges are the Git
fixture (reference bits, audited) and the Python reference evaluated live on inputs outside the fixture.
B0 must give the same bits on every supported input and refuse the rest. Skipped when MSVC is absent.
"""
from __future__ import annotations

import hashlib
import math
from fractions import Fraction as Q

import pytest

import a_reference.ar2_lang2024 as L
import a_reference.ar2_lang2024_fixture as X
from a_numeric_native.harness import find_vcvars, run_with_timeout
from a_physics_native import harness as H

pytestmark = pytest.mark.skipif(find_vcvars() is None, reason="MSVC not installed")

FIX = X.load()
VF = {"V": ("V", True), "V_ret_off": ("V", False), "F": ("F", True), "F_ret_off": ("F", False)}

# defect -> what it is. Every one must be caught by the fixture; `grid_blind` ones are missed by the 94-point grid
MUTANTS = {
    1: "Fortran-like evaluation, every operation rounded in binary64",
    2: "one modest precision (M = 64), first answer taken",
    3: "no refinement: the lower end's rounding accepted at M = 96",
    4: "domain limit converted to binary64 and compared with <=",
    5: "force missing the +2k C D / R^(2k+1) term",
    6: "BO retardation g(R) ignored",
    7: "interval product from lo*lo and hi*hi only",
    8: "Tang-Toennies tail taken as 0 for x >= 64",
    9: "binary64 rounding toward zero",
    10: "FX rounding toward minus infinity",
    11: "Tang-Toennies order one too low",
}


def fixture_queries():
    qs, want = [], []
    for c in FIX["cases"]:
        for name, (q, ret) in VF.items():
            qs.append((q, ret, c["profile"], c["R_raw"]))
            beyond = c["R_bohr_approx"] > H.B0_R_MAX_BOHR
            want.append((c, name, {"refuse": "beyond_native_range"} if beyond else c["results"][name]))
    return qs, want


def mismatches(got, want):
    bad = []
    for g, (c, name, w) in zip(got, want):
        if (g if "refuse" in w else H.as_outcome(g)) != w:
            bad.append((c, name, w, g))
    return bad


@pytest.fixture(scope="module")
def b0(tmp_path_factory):
    return H.build("b0", tmp_path_factory.mktemp("ar2b0"))


def test_knuth_division_selftest(b0) -> None:
    r = run_with_timeout([b0, "selftest"])
    assert r.returncode == 0 and "selftest ok" in r.stdout


def test_b0_gives_the_fixture_bits(b0) -> None:
    qs, want = fixture_queries()
    got = H.run(b0, qs)
    assert mismatches(got, want) == []
    assert {g["M"] for g in got if "M" in g} >= {96, 192}          # the refinement path is exercised
    # the physics refusal and the capability refusal stay distinct
    assert sum("domain" in g for g in got) == 4 * sum("domain" in c["results"]["V"] for c in FIX["cases"])
    assert sum(g.get("refuse") == "beyond_native_range" for g in got) == 4


def _dense(n, tag):
    lo, hi = math.log(float(L.R_MIN_BOHR)), math.log(2 ** 20)
    out = []
    for i in range(n):
        u = int.from_bytes(hashlib.sha256(f"{tag}:{i}".encode()).digest()[:8], "big") / 2 ** 64
        p = "B64" if i % 4 else "FX64_32"
        raw = X.raw_ceil(p, Q(math.exp(lo + (hi - lo) * u * u)))
        for name in (("V", "F") if i % 3 else ("V_ret_off", "F_ret_off")):
            q, ret = VF[name]
            out.append(((q, ret, p, X.raw_str(p, raw)), (p, name, raw)))
    return out


def test_b0_matches_the_live_reference_outside_the_fixture(b0) -> None:
    sample = _dense(150, "b0-test")
    got = H.run(b0, [q for q, _ in sample])
    for g, (_, (p, name, raw)) in zip(got, sample):
        assert H.as_outcome(g) == X.outcome(p, name, raw), (p, name, raw)


def test_b0_domain_and_range_edges(b0) -> None:
    r0 = X.raw_ceil("B64", L.R_MIN_BOHR)
    qs = [("V", True, "B64", X.raw_str("B64", r)) for r in (r0 - 1, r0)]
    qs += [("F", True, "B64", "0000000000000000"), ("V", True, "B64", "bff0000000000000"),   # 0 and -1
           ("V", True, "B64", "7ff0000000000000"),                                        # +inf pattern
           ("V", True, "B64", X.raw_str("B64", X.bits(2.0 ** 20))),
           ("V", True, "B64", X.raw_str("B64", X.bits(math.nextafter(2.0 ** 20, math.inf)))),
           ("V", True, "FX64_32", "0"), ("V", True, "FX64_32", "-5")]
    got = [H.as_outcome(g) for g in H.run(b0, qs)]
    dom = {"domain": "physics_domain_exceeded"}
    assert got[0] == dom and "raw" in got[1]
    assert got[2] == dom and got[3] == dom and got[4] == {"refuse": "invalid_input"}
    assert "raw" in got[5] and got[6] == {"refuse": "beyond_native_range"}
    assert got[7] == dom and got[8] == dom


def test_b0_refuses_instead_of_guessing(tmp_path_factory) -> None:
    """With the precision cap lowered to the first attempt, B0 refuses the inputs it cannot decide there --
    and every answer it does give is still the reference's."""
    exe = H.build("b0", tmp_path_factory.mktemp("ar2b0cap"), defines={"AR2_M_CAP": 96})
    qs, want = fixture_queries()
    got = H.run(exe, qs)
    refused = [g for g in got if g.get("refuse") == "undecided"]
    assert len(refused) > 50
    answered = [(g, w) for g, w in zip(got, want) if g.get("refuse") != "undecided"]
    assert mismatches([g for g, _ in answered], [w for _, w in answered]) == []


@pytest.mark.parametrize("n", sorted(MUTANTS))
def test_injected_defect_is_caught(n, tmp_path_factory) -> None:
    exe = H.build("b0", tmp_path_factory.mktemp(f"ar2b0inj{n}"), n)
    qs, want = fixture_queries()
    bad = mismatches(H.run(exe, qs), want)
    assert bad, MUTANTS[n]
