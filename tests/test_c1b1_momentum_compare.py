"""C1-B1 momentum-precision comparison (designer 15th ed.): the recorded measurement stays consistent.

a_reference/fixtures/c1b1_momentum_compare_v1.json compares momentum FX(64,48), FX(80,64), FX(96,80), FX(128,112) and
the carry representation (coarse FX(64,48) + 2^-111 residual) with position FX(96,48) and drift v2, against the
rounding-free FX(256,192). It CHOOSES NOTHING. These checks pin the facts reported in the design doc, section 13.
"""
from __future__ import annotations

import collections
import hashlib
import json
import shutil
import subprocess
from fractions import Fraction as Q
from pathlib import Path

import mpmath
import pytest

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "a_reference" / "fixtures"
D = json.loads((FIX / "c1b1_momentum_compare_v1.json").read_text(encoding="utf-8"))
N2 = json.loads((FIX / "c1b1_numrep_study_v1.json").read_text(encoding="utf-8"))
D1 = json.loads((FIX / "c1b1_dt_study_v1.json").read_text(encoding="utf-8"))
REF80 = {r["case"]: r for r in N2["results"] if r["task"] == "ref" and r["dps"] == 80}
CASES = {c["name"]: c for c in D1["cases"]}
CANDS = ["fx64_48", "fx80_64", "fx96_80", "fx128_112", "carry"]
mpmath.mp.dps = 50


def _obs(c):
    if c["kind"] == "bound":
        return ["two_periods"]
    return ["time"] if c["b"] == "0" else ["sweep", "time"]


def test_provenance_names_the_code_that_produced_it() -> None:
    p = D["provenance"]
    assert p["uncommitted_changes_in_a_reference_audit_or_native"] is False
    if shutil.which("git") is None:
        pytest.skip("git not available")
    for f, h in p["code_sha256"].items():
        blob = subprocess.run(["git", "show", f"{p['git_head']}:{f}"], capture_output=True, cwd=ROOT)
        if blob.returncode != 0:
            pytest.skip("recorded commit not in this clone")
        assert hashlib.sha256(blob.stdout.replace(b"\r\n", b"\n")).hexdigest() == h, f


def test_A_accuracy_is_unchanged_by_the_momentum_representation() -> None:
    runs = {(r["case"], r["dt"], r["profile"]): r for r in D["A_accuracy"]}
    assert len(runs) == 40 * 3 * 5 and all(r["status"] == "ok" and r["dP"] == ["0", "0", "0"] for r in runs.values())
    for case, c in CASES.items():
        for cand in CANDS:
            for k in _obs(c):
                v = mpmath.mpf(REF80[case]["represented"][k])
                e = {dt: mpmath.mpf(runs[(case, dt, cand)][k]) - v for dt in (10, 20, 40)}
                assert 3.5 < e[20] / e[10] < 4.5 and 3.5 < e[40] / e[20] < 4.5
                if v:
                    assert abs(e[40]) / abs(v) <= (1e-4 if k == "two_periods" else 1e-5)
                    b = mpmath.mpf(runs[(case, 40, "fx64_48")][k])
                    assert abs(mpmath.mpf(runs[(case, 40, cand)][k]) - b) <= 1e-12 * abs(b)   # all within 1e-12
            assert runs[(case, 40, cand)]["max_abs_dE_over_De"] <= 1e-3


def test_B_E_cutoff_moves_about_4x_per_16_bits_and_never_disappears() -> None:
    b = {r["candidate"]: r for r in D["B_E_budget"]}
    rc = [b[c]["R_cut_bohr"] for c in ("fx64_48", "fx80_64", "fx96_80", "fx128_112")]
    assert 430 < rc[0] < 445 and 1850 < rc[1] < 1900 and 7500 < rc[2] < 7650 and 1.2e5 < rc[3] < 1.3e5
    assert all(3.8 < y / x < 4.4 for x, y in zip(rc[:3], rc[1:3]))
    E = [b[c]["E_min_over_De"] for c in CANDS]
    assert 1e-5 < E[0] < 2e-5 and E[1] < 2e-9 and E[2] < 1e-13 and E[3] < 1e-21 and E[4] < 1e-21
    assert all(e > 0 for e in E)                                   # a finite grid always leaves an E_min


def test_C_far_pairs_lose_or_bias_the_force_near_and_beyond_the_cutoff() -> None:
    far = {(r["candidate"], r["R_bohr"]): r for r in D["C_far_pairs"]}
    assert all(r["dP"] == ["0", "0", "0"] for r in D["C_far_pairs"])
    rel = lambda c, R: (Q(far[(c, R)]["p_j_x"]) - Q(far[("ref", R)]["p_j_x"])) / Q(far[("ref", R)]["p_j_x"])
    for R in (438, 1000, 1872, 5000, 7567, 20000):
        assert far[("fx64_48", R)]["p_j_x"] == "0"                 # the implicit cutoff: never any momentum
    assert abs(rel("fx64_48", 200)) > 1e-3                         # below the cutoff: biased by rounding
    assert 0.99 < rel("fx80_64", 1872) < 1.01                      # near its cutoff: about twice the momentum
    assert abs(rel("fx96_80", 5000)) > 1e-2 and far[("fx96_80", 7567)]["p_j_x"] == "0"
    for c in ("fx128_112", "carry"):
        assert all(abs(rel(c, R)) < 2e-6 for R in (100, 200, 438, 1000, 1872, 5000, 7567, 20000))


def test_D_far_field_deflection_differences_are_far_below_the_criterion() -> None:
    ff = {(r["candidate"], r["e"], r["b"]): r for r in D["D_far_field"]}
    assert len(ff) == 6 * 3
    for (cand, e, b), r in ff.items():
        ref = ff[("ref", e, b)]
        assert abs(mpmath.mpf(r["angle_at_out"]) - mpmath.mpf(ref["angle_at_out"])) < 2e-12
        assert r["dP"] == ["0", "0", "0"]
        tail = mpmath.mpf(ref["angle_at_out"]) - mpmath.mpf(ref["angle_at_20"])
        assert 1e-5 < abs(tail) < 1e-3                             # 20 -> 2500 bohr still turns the pair


def test_F_invariance_conservation_and_long_runs() -> None:
    assert len(D["F_invariance"]) == 6 * 4
    assert all(all(v for v in r.values() if isinstance(v, bool)) for r in D["F_invariance"])
    L = {(r["candidate"], r["state"]): r["points"] for r in D["F_long"]}
    for st in ("bound_f0.3", "orbit"):
        ref = L[("ref", st)]
        for c in CANDS:
            pts = L[(c, st)]
            assert [p["dE_over_De"] for p in pts] == pytest.approx([p["dE_over_De"] for p in ref], rel=1e-6, abs=1e-12)
            dev = max(abs(Q(a) - Q(b)) for p, q in zip(pts, ref) for a, b in zip(p["rel"], q["rel"]))
            assert dev < Q(1, 10 ** 10)
            if c in ("fx80_64", "fx96_80", "fx128_112"):
                assert dev == 0                                     # identical positions to the reference
