"""C1-B1 drift comparison (designer 14th ed. follow-up): the recorded measurement stays consistent.

a_reference/fixtures/c1b1_drift_compare_v1.json compares v1 round(r + p dt/m), v2 r + round(p dt/m) and exact drift
(every sub-grid remainder kept) under identical states, force, dt and references. It CHOOSES NOTHING -- the designer
decides. These checks read the record and pin the facts reported in the design doc, section 11.
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
D = json.loads((FIX / "c1b1_drift_compare_v1.json").read_text(encoding="utf-8"))
N2 = json.loads((FIX / "c1b1_numrep_study_v1.json").read_text(encoding="utf-8"))
D1 = json.loads((FIX / "c1b1_dt_study_v1.json").read_text(encoding="utf-8"))
REF80 = {r["case"]: r for r in N2["results"] if r["task"] == "ref" and r["dps"] == 80}
CASES = {c["name"]: c for c in D1["cases"]}
RULES = ("v1", "v2", "exact")
mpmath.mp.dps = 50


def _obs(c):
    if c["kind"] == "bound":
        return ["two_periods"]
    return ["time"] if c["b"] == "0" else ["sweep", "time"]


def test_provenance_names_the_code_that_produced_it() -> None:
    p = D["provenance"]
    assert p["uncommitted_changes_in_a_reference_audit_or_native"] is False
    assert all(D["states_accepted_by_contract"].values())          # every comparison state is a validated state
    if shutil.which("git") is None:
        pytest.skip("git not available")
    for f, h in p["code_sha256"].items():
        blob = subprocess.run(["git", "show", f"{p['git_head']}:{f}"], capture_output=True, cwd=ROOT)
        if blob.returncode != 0:
            pytest.skip("recorded commit not in this clone")
        assert hashlib.sha256(blob.stdout.replace(b"\r\n", b"\n")).hexdigest() == h, f


def test_A_accuracy_is_the_same_for_all_three_and_meets_the_criteria() -> None:
    runs = {(r["case"], r["dt"], r["profile"]): r for r in D["A_accuracy"]}
    assert len(runs) == 40 * 3 * 3 and all(r["status"] == "ok" for r in runs.values())
    for case, c in CASES.items():
        for rule in RULES:
            for k in _obs(c):
                v = mpmath.mpf(REF80[case]["represented"][k])
                e = {dt: mpmath.mpf(runs[(case, dt, rule)][k]) - v for dt in (10, 20, 40)}
                assert 3.5 < e[20] / e[10] < 4.5 and 3.5 < e[40] / e[20] < 4.5, (rule, case, k)   # second order
                if v:
                    assert abs(e[40]) / abs(v) <= (1e-4 if k == "two_periods" else 1e-5), (rule, case, k)
            assert runs[(case, 40, rule)]["max_abs_dE_over_De"] <= 1e-3
        for dt in (10, 20, 40):
            a, b, x = (runs[(case, dt, r)] for r in RULES)
            assert all(a[k] == b[k] for k in _obs(c)) and a["steps"] == b["steps"]             # v1 = v2: no ties
            for k in _obs(c):                                                                     # exact: ~1e-12
                v = mpmath.mpf(b[k])
                assert abs(mpmath.mpf(x[k]) - v) <= 1e-11 * abs(v)


def test_B_invariances_v1_breaks_at_ties_v2_and_exact_never() -> None:
    rows = {(r["rule"], r["state"]): r for r in D["B_invariance"]}
    assert len(rows) == 3 * 6
    keys = [k for k in rows[("v2", "tie")] if k.startswith(("translation", "exchange", "rotation", "frame"))]
    ok = lambda v: v["identical"] if isinstance(v, dict) else v
    for (rule, state), r in rows.items():
        if rule == "v1" and r["ties_met"]:
            failed = [k for k in keys if not ok(r[k])]
            assert failed and all(k.startswith(("translation", "frame")) for k in failed), state
            assert r["exchange"] and r["rotation_90"]
        else:
            assert all(ok(r[k]) for k in keys), (rule, state)
    assert rows[("v2", "far_tie")]["ties_met"] == 80                           # every drift of 40 steps a tie
    assert not rows[("v1", "far_tie")]["frame_change_at_7_1raw"]


def test_C_reversibility_v1_fails_from_odd_positions_at_ties() -> None:
    for r in D["C_reversibility"]:
        if r["rule"] == "v1" and r["state"] in ("tie", "far_tie") and r["shift_raw"] == 1:
            assert not r["exact_return"] and r["max_pos_dev_raw"] == 1
        else:
            assert r["exact_return"], r


def test_D_slow_motion_stall_and_bias() -> None:
    free = {(r["rule"], r["p_raw"]): r for r in D["D_free_drift"]}
    for rule in ("v1", "v2"):
        assert free[(rule, 910)]["stalled"] and not free[(rule, 911)]["stalled"]            # |p| < 3.2e-12 a.u.
        assert free[(rule, 911)]["moved_raw"] == 10000                                       # ~2x the exact move
        assert abs(free[(rule, 4995297890462500)]["error_raw"]) >= 4999                      # 1/2 raw per step
    assert all(r["error_raw"] == 0 for (rule, _), r in free.items() if rule == "exact")
    rest = {(r["rule"], r["R_bohr"]): r for r in D["D_rest_pair"]}
    for rule in RULES:                         # momentum grid: J rounds to 0 at 1000 bohr -- no rule can move them
        assert rest[(rule, 1000)]["first_step_with_momentum"] is None
    assert rest[("v2", 200)]["first_step_with_motion"] == 4 and rest[("exact", 200)]["first_step_with_motion"] == 1


def test_E_long_runs() -> None:
    L = {(r["rule"], r["state"]): r["points"] for r in D["E_long"]}
    for st in ("bound_f0.3", "orbit"):
        ref = L[("ref", st)]
        assert len(ref) == 40
        dev = {}
        for rule in RULES:
            pts = L[(rule, st)]
            assert [p["dE_over_De"] for p in pts] == pytest.approx([p["dE_over_De"] for p in ref], rel=1e-6, abs=1e-12)
            dev[rule] = max(abs(Q(a) - Q(b)) for p, q in zip(pts, ref) for a, b in zip(p["rel"], q["rel"]))
        assert L[("v1", st)] == L[("v2", st)]                                          # identical: no ties met
        assert all(d < Q(1, 10 ** 9) for d in dev.values())                           # < 1e-9 bohr after 8e6 a.u.
        assert max(p["pos_denominator_bits"] for p in L[("exact", st)]) <= 102        # exact lattice: bounded


def test_G_H_exact_lattice_widths() -> None:
    g = D["G_exact_bits_c1b1"]
    assert g["width_for_pm_2^47_bohr"] == 150 and g["v1_v2_width"] == 96
    w = [r["width_for_pm_2^47_bohr"] for r in D["H_lattice"]["species_growth"]]
    assert w[0] == 150 and w[-1] == 476 and all(b > a for a, b in zip(w, w[1:]))       # every species adds bits
    assert [r["width_for_pm_2^47_bohr"] for r in D["H_lattice"]["dt_growth"]][:3] == [150, 152, 150]
