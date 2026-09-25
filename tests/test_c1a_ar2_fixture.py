"""C1-A reference fixture and hard-input audit (designer 9th ed., items 1-3).

The fixture (a_reference/fixtures/ar2_lang2024_c1a_v1.json) freezes the reference's result bits inside Git.
The core physics regression here runs WITHOUT D:\\reference; only the provenance audit (re-hashing the
published files and re-judging every stored bit with the independent audit) needs them and skips without.
"""
from __future__ import annotations

import re
from fractions import Fraction as Q
from pathlib import Path

import pytest

import a_reference.ar2_lang2024 as L
import a_reference.ar2_lang2024_fixture as X

DATA = X.DATA
HAVE_DATA = all((DATA / f).exists() for f in X.SOURCE_FILES)
needs_data = pytest.mark.skipif(not HAVE_DATA, reason="published Lang 2024 files not on D:\\reference")
FIX = X.load()
CASES = FIX["cases"]
HEX64 = re.compile(r"^[0-9a-f]{64}$")


def test_fixture_is_in_git_and_names_its_contract() -> None:
    assert X.FIXTURE.resolve().is_relative_to(X.ROOT)
    assert FIX["format"] == X.FIXTURE_FORMAT
    c = FIX["contract"]
    assert c["version"] == L.CONTRACT_VERSION
    assert c["parameter_fingerprint"] == L.parameter_fingerprint()      # any parameter change breaks this
    assert Q(c["bohr_angstrom"]) == L.BOHR_ANGSTROM
    assert "source-versioned" in c["bohr_angstrom_source"]
    assert set(c["quantities"]) == set(X.QUANTITIES) == {"V", "V_ret_off", "F", "F_ret_off", "sigma",
                                                         "V+sigma", "V-sigma"}
    p = FIX["provenance"]
    assert set(p["lang2024_files_sha256"]) == set(X.SOURCE_FILES)
    for h in [*p["lang2024_files_sha256"].values(), *p["audit_code_sha256"].values(),
              p["reference_code_sha256"], p["generator_code_sha256"]]:
        assert HEX64.match(h)
    assert re.match(r"^[0-9a-f]{40}$", p["git_head_at_generation"])
    for case in CASES:
        assert set(case["results"]) == set(X.QUANTITIES)
        assert X.R_of(case["profile"], X.raw_parse(case["profile"], case["R_raw"])) == Q(case["R"])


def test_codata_conversion_is_scoped_to_this_contract() -> None:
    """Item 1: the CODATA 2018 a0 reproduces Lang 2024 and converts 1.2 A; it is not A's general constant."""
    doc = L.__doc__
    assert "SOURCE-VERSIONED" in doc and "does NOT fix A's general" in doc
    assert L.R_MIN_BOHR == Q("1.2") / Q("0.529177210903")


@pytest.mark.parametrize("profile", ["B64", "FX64_32"])
def test_reference_reproduces_every_fixture_bit(profile) -> None:
    """The core regression: no D:\\reference needed, nothing skipped."""
    n = 0
    for case in CASES:
        if case["profile"] != profile:
            continue
        raw = X.raw_parse(profile, case["R_raw"])
        for name, stored in case["results"].items():
            assert X.outcome(profile, name, raw) == stored, (profile, case["R_bohr_approx"], name, case["tags"])
            n += 1
    assert n > 7 * 100


def test_fixture_covers_the_designated_regions() -> None:
    tags = {(c["profile"], t) for c in CASES for t in c["tags"]}
    both = ["grid", "r_min", "V_sign_change", "F_zero_minimum", "strong_cancellation", "20_angstrom",
            "long_range_250_bohr_plus", "tiny_V_F_to_1e4_bohr", "retardation_onset_1e-5", "retardation_onset_1e-3",
            "retardation_onset_1e-2", "retardation_onset_1e-1", "V+sigma_sign_change", "V-sigma_sign_change"]
    for p in ("B64", "FX64_32"):
        for t in both:
            assert (p, t) in tags, (p, t)
    assert ("B64", "b0_range_end") in tags
    assert ("FX64_32", "FX_V_underflow_edge") in tags and ("FX64_32", "FX_F_underflow_edge") in tags
    # r_min: the input just below 1.2 A is refused as physics, the first one at or above it is evaluated
    for p in ("B64", "FX64_32"):
        r0 = X.raw_ceil(p, L.R_MIN_BOHR)
        by_raw = {X.raw_parse(p, c["R_raw"]): c for c in CASES if c["profile"] == p}
        assert by_raw[r0 - 1]["results"]["V"] == {"domain": "physics_domain_exceeded"}
        assert all("raw" in by_raw[r0 + d]["results"]["F"] for d in range(4))
    # 250 bohr and beyond up to 10^4 bohr: tiny but nonzero in binary64
    long = [c for c in CASES if c["profile"] == "B64" and 250 <= c["R_bohr_approx"] <= 10000]
    assert long and all(c["results"]["V"]["raw"] != "0000000000000000" for c in long)
    assert max(c["R_bohr_approx"] for c in long) == 10000


def test_fixture_contains_inputs_near_rounding_boundaries() -> None:
    """Item 3, boundary search: the exact value lies within 2^-18 of the result spacing of a rounding boundary."""
    hardest = {}
    for c in CASES:
        for q, d in c["boundary_distance_log2"].items():
            if d is not None:
                key = (c["profile"], q)
                hardest[key] = min(hardest.get(key, 0), d)
    for key in (("B64", "V"), ("B64", "F"), ("FX64_32", "V"), ("FX64_32", "F")):
        assert hardest[key] <= -18, (key, hardest[key])
    n_hard = sum(1 for c in CASES for d in c["boundary_distance_log2"].values() if d is not None and d <= -16)
    assert n_hard >= 60


def test_fx_profile_loses_the_long_range_tail() -> None:
    """Disclosed: in FX(64,32) (resolution 2^-32 hartree) V and F round to exactly 0 far out."""
    far = [c for c in CASES if c["profile"] == "FX64_32" and c["R_bohr_approx"] >= 250]
    assert far and all(c["results"]["V"] == {"raw": "0"} and c["results"]["F"] == {"raw": "0"} for c in far)


def test_reference_refuses_instead_of_guessing(monkeypatch) -> None:
    """At a precision cap too low for a hard input the reference raises ReferenceUndecided; it never guesses."""
    hard = min((c for c in CASES if c["profile"] == "FX64_32" and "FX_V_underflow_edge" in c["tags"]),
               key=lambda c: c["boundary_distance_log2"]["V"])
    easy = next(c for c in CASES if c["profile"] == "FX64_32" and "grid" in c["tags"] and "raw" in c["results"]["V"]
                and -3 < c["boundary_distance_log2"]["V"])
    monkeypatch.setattr(L, "START_PRECISION_BITS", 64)
    monkeypatch.setattr(L, "MAX_PRECISION_BITS", 64)
    assert X.outcome("FX64_32", "V", X.raw_parse("FX64_32", easy["R_raw"])) == easy["results"]["V"]
    with pytest.raises(L.ReferenceUndecided):
        X.outcome("FX64_32", "V", X.raw_parse("FX64_32", hard["R_raw"]))


# --- provenance audit: only with the published files ------------------------------------------------

@needs_data
def test_provenance_hashes_match_the_published_files() -> None:
    p = FIX["provenance"]["lang2024_files_sha256"]
    sums = {}
    for line in (DATA / "SHA256SUMS.txt").read_text().splitlines():
        h, name = line.split()
        sums[name.lstrip("*")] = h
    for f, h in p.items():
        assert X._sha256(DATA / f) == h == sums[f], f


@needs_data
def test_audit_re_judges_every_stored_bit() -> None:
    """Every stored outcome re-judged by the independent audit (interval V / sigma, 80-digit derivative F)."""
    from audit.independent_physics.ar2_lang2024 import Model, parse_fortran
    model = Model(parse_fortran())
    for case in CASES:
        p, raw = case["profile"], X.raw_parse(case["profile"], case["R_raw"])
        for name, stored in case["results"].items():
            assert X.verify_with_audit(p, raw, name, stored, model) is None, (p, case["R_bohr_approx"], name)


def test_injected_defects_are_caught_without_the_published_files(monkeypatch) -> None:
    """The fixture alone (no D:\reference) catches a changed parameter digit and a dropped derivative term."""
    b64 = [c for c in CASES if c["profile"] == "B64" and "raw" in c["results"]["V"]][:60]

    def mismatches(name):
        return sum(X.outcome("B64", name, X.raw_parse("B64", c["R_raw"])) != c["results"][name] for c in b64)
    eta, C, kadd = L.BO_LONG
    monkeypatch.setattr(L, "BO_LONG", (eta, {**C, 3: Q("64.2295223")}, kadd))     # one digit of C6
    monkeypatch.setitem(L.COMPONENTS, "BO", (L.BO_SHORT, L.BO_LONG))
    assert L.parameter_fingerprint() != FIX["contract"]["parameter_fingerprint"]
    assert mismatches("V") > 0
    monkeypatch.undo()
    orig = L._damp_deriv
    monkeypatch.setattr(L, "_damp_deriv", lambda n, x, M: orig(n, x, M) * Q(1 + 10 ** -12))   # a 1e-12 slip in f_n'
    assert mismatches("F") > 0
