"""C1-B1 study 2 data (designer 12th ed., steps 1-4): the recorded measurement stays consistent.

a_reference/fixtures/c1b1_numrep_study_v1.json is a MEASUREMENT; it chooses no number profile. These checks read
it (and study 1) only.
"""
from __future__ import annotations

import collections
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import mpmath
import pytest

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "a_reference" / "fixtures"
D2 = json.loads((FIX / "c1b1_numrep_study_v1.json").read_text(encoding="utf-8"))
D1 = json.loads((FIX / "c1b1_dt_study_v1.json").read_text(encoding="utf-8"))
RES = D2["results"]
REF80 = {r["case"]: r for r in RES if r["task"] == "ref" and r["dps"] == 80}
RUNS1 = collections.defaultdict(dict)
for r in D1["runs"]:
    RUNS1[r["case"]][(r["dt"], r["profile"])] = r
CASES = {c["name"]: c for c in D1["cases"]}
mpmath.mp.dps = 60


def _obs(c):
    if c["kind"] == "bound":
        return ["two_periods"]
    return ["time"] if c["b"] == "0" else ["sweep", "time"]


def test_provenance_names_the_code_that_produced_it() -> None:
    p = D2["provenance"]
    assert p["uncommitted_changes_in_a_reference_or_audit"] is False
    if shutil.which("git") is None:
        pytest.skip("git not available")
    for f, h in p["code_sha256"].items():
        blob = subprocess.run(["git", "show", f"{p['git_head']}:{f}"], capture_output=True, cwd=ROOT)
        if blob.returncode != 0:
            pytest.skip("recorded commit not in this clone")
        assert hashlib.sha256(blob.stdout).hexdigest() == h, f


def test_references_converge_in_precision_and_study1_stays_valid() -> None:
    """Item 8: 30 / 50 / 80 digits agree far below the tolerances; study 1's errors move by < 1e-12 relative."""
    by = collections.defaultdict(dict)
    for r in RES:
        if r["task"] == "ref":
            by[r["case"]][r["dps"]] = r
    old = {r["case"]: r for r in D1["references"]}
    for name, d in by.items():
        for tag in ("represented", "nominal"):
            for k, v in d[80][tag].items():
                v80 = mpmath.mpf(v)
                scale = abs(v80) or 1
                assert abs(mpmath.mpf(d[30][tag][k]) - v80) / scale < 1e-18
                assert abs(mpmath.mpf(d[50][tag][k]) - v80) / scale < 1e-32
                if v80 != 0:
                    for dt in D1["dts"]:
                        h = mpmath.mpf(RUNS1[name][(dt, "HP")][k]) if tag == "represented" else None
                        if h is not None:
                            e_new = abs(h - v80) / v80
                            e_old = abs(h - mpmath.mpf(old[name][tag][k])) / v80
                            assert abs(e_new - e_old) < 1e-12


def test_domain_guard_stress_record() -> None:
    """Item 6 (not an accuracy claim): below V(r_min) every run turns back above r_min; at 1.01 V(r_min) the
    guard stops every run with dt <= 20; at dt = 40 the discrete path turns back above r_min (recorded fact)."""
    for r in (x for x in RES if x["task"] == "stress"):
        f, dt = r["f"], r["dt"]
        if f != "101/100":
            assert r["status"] == "ok" and r["min_R_drift_segments"] >= r["r_min"], (f, dt)
        elif dt == "40":
            assert r["status"] == "ok"
        else:
            assert r["status"].startswith("physics_domain_exceeded: drift segment"), (f, dt)


def _ratio(profile, dt):
    worst = mpmath.mpf(0)
    for r in RES:
        if r["task"] == "cand" and r["profile"] == profile and r["dt"] == dt:
            for k in _obs(CASES[r["case"]]):
                ref = mpmath.mpf(REF80[r["case"]]["represented"][k])
                h = mpmath.mpf(RUNS1[r["case"]][(dt, "HP")][k])
                worst = max(worst, abs(mpmath.mpf(r[k]) - h) / abs(h - ref))
    return worst


def test_wider_fixed_point_candidates() -> None:
    """Item 4: every candidate run finished; the rounding-to-discretisation ratio at dt = 40 falls with the
    fraction bits (about 2^-8 per 8 bits)."""
    assert all(r["status"] == "ok" for r in RES if r["task"] == "cand")
    r40 = {p: _ratio(p, 40) for p in ("FX64_40", "FX64_48", "FX96_64", "FX128_96")}
    assert 1e-2 < r40["FX64_40"] < 5e-2
    assert r40["FX64_48"] < 1e-4
    assert r40["FX96_64"] < 1e-8 and r40["FX128_96"] < 1e-17
    assert r40["FX64_40"] > r40["FX64_48"] > r40["FX96_64"] > r40["FX128_96"]


def test_sensitive_cases_converge_to_their_own_references() -> None:
    """Item 7: each shifted-b input converges (second order) to ITS OWN independent reference."""
    refs = {(r["e"], r["b"], r["db"]): mpmath.mpf(r["represented"]["sweep"]) for r in RES if r["task"] == "sens_ref"}
    assert len(refs) == 6
    for key, ref in refs.items():
        err = {r["dt"]: mpmath.mpf(r["sweep"]) - ref for r in RES
               if r["task"] == "sens" and (r["e"], r["b"], r["db"]) == key}
        assert 3.9 < err[20] / err[10] < 4.1 and 3.9 < err[40] / err[20] < 4.1, key
        assert abs(err[40]) / abs(ref) < 1e-5                                        # within the C1-B1 criterion


def test_typed_profile_pair_reproduces_fx64_48_and_meets_the_criteria() -> None:
    """Study 3: position FX(96,48) + momentum FX(64,48) gives exactly the FX(64,48) observables (same fraction
    bits, no position outside +-32768 bohr) and meets the 12th-ed. criteria at dt = 40."""
    t = json.loads((FIX / "c1b1_typed_study_v1.json").read_text(encoding="utf-8"))
    assert t["provenance"]["uncommitted_changes_in_a_reference_or_audit"] is False
    cand = {(r["case"], r["dt"]): r for r in RES if r["task"] == "cand" and r["profile"] == "FX64_48"}
    assert len(t["runs"]) == 120
    for r in t["runs"]:
        c = cand[(r["case"], r["dt"])]
        assert r["status"] == c["status"] == "ok" and r["steps"] == c["steps"] and r["dLz"] == c["dLz"]
        for k in ("sweep", "time", "two_periods"):
            assert r.get(k) == c.get(k)
        if r["dt"] == 40:
            assert r["max_abs_dE_over_De"] <= 1e-3
            for k in _obs(CASES[r["case"]]):
                v = mpmath.mpf(REF80[r["case"]]["represented"][k])
                if v:
                    assert abs(mpmath.mpf(r[k]) - v) / abs(v) <= (1e-4 if k == "two_periods" else 1e-5)


def test_typed_study_v2_reproduces_v1_bit_for_bit() -> None:
    """Designer 14th ed.: the 120 typed runs re-run under contract v2 (drift r + round(p dt/m)) give exactly the v1
    observables, step counts and angular-momentum changes -- no study case meets an exact drift tie."""
    v1 = json.loads((FIX / "c1b1_typed_study_v1.json").read_text(encoding="utf-8"))
    v2 = json.loads((FIX / "c1b1_typed_study_v2.json").read_text(encoding="utf-8"))
    assert v2["contract"] == "c1b1-two-atom-v2" and v2["provenance"]["uncommitted_changes_in_a_reference_or_audit"] is False
    strip = lambda r: {k: v for k, v in r.items() if k != "seconds"}
    a = {(r["case"], r["dt"]): strip(r) for r in v1["runs"]}
    b = {(r["case"], r["dt"]): strip(r) for r in v2["runs"]}
    assert len(a) == len(b) == 120 and a == b
