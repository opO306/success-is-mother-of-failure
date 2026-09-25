"""C1-B1 boundary study (designer 14th ed.): the E = 10 De cases rebuilt inside the strict integrator contract.

a_reference/fixtures/c1b1_boundary_study_v1.json is a MEASUREMENT. The contract bound E_rel <= 10 De stays strict
(no tolerance); what changed is the test input: the nearest stored state (radial momentum, 2^-48 steps) that the
contract accepts. These checks read the record, and re-decide acceptance with the current contract code.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from fractions import Fraction as Q
from pathlib import Path

import mpmath
import pytest

import a_reference.c1b1_dt_study as S
import a_reference.c1b1_two_atom as C
from a_numeric import FixedPoint

ROOT = Path(__file__).resolve().parents[1]
D = json.loads((ROOT / "a_reference" / "fixtures" / "c1b1_boundary_study_v1.json").read_text(encoding="utf-8"))
REFS = {r["case"]: r for r in D["references"]}
POS, MOM = FixedPoint(96, 48), FixedPoint(64, 48)


def test_provenance_names_the_code_that_produced_it() -> None:
    p = D["provenance"]
    assert p["uncommitted_changes_in_a_reference_or_audit"] is False
    assert D["contract"] == "c1b1-two-atom-v2" and D["integrator_E_max"] == str(C.INTEGRATOR_E_MAX)
    if shutil.which("git") is None:
        pytest.skip("git not available")
    for f, h in p["code_sha256"].items():
        blob = subprocess.run(["git", "show", f"{p['git_head']}:{f}"], capture_output=True, cwd=ROOT)
        if blob.returncode != 0:
            pytest.skip("recorded commit not in this clone")
        assert hashlib.sha256(blob.stdout.replace(b"\r\n", b"\n")).hexdigest() == h, f


def test_old_grid_states_are_refused_by_the_strict_contract() -> None:
    """Why the inputs were rebuilt: 5 of the 7 study-1 states (FX(64,32) grid) lie above 10 De."""
    refused = 0
    for b in S.B_FRACS:
        st = S.scattering_state(Q(10), b)
        try:
            C.new_run(POS, 40, st["r_i"], st["p_i"], st["r_j"], st["p_j"], momentum_profile=MOM)
        except C.IntegratorDomainExceeded:
            refused += 1
    assert refused == 5


def test_rebuilt_states_are_accepted_and_nearest() -> None:
    """Each rebuilt state is accepted (re-decided now, exact enclosure); one raw unit more radial momentum is not
    whenever the state had to be lowered -- so no nearer accepted state exists along that direction."""
    assert len(D["cases"]) == 7
    for c in D["cases"]:
        P = tuple(Q(x) for x in c["p_j"])
        ri, rj = (-S.R_START / 2, Q(0), Q(0)), (S.R_START / 2, Q(0), Q(0))
        C.new_run(POS, 40, ri, tuple(-x for x in P), rj, P, momentum_profile=MOM)
        assert c["E_rep_hi_le_10De"] is True and float(c["E_rep_over_10De_minus_1"]) <= 0
        assert abs(float(c["E_rep_over_10De_minus_1"])) < 1e-14         # within ~1e-16 of the bound, not 1e-10
        assert all(MOM.to_exact(MOM.from_exact(x)) == x for x in P) and P[2] == 0
        if c["raw_units_lowered"]:
            up = (P[0] - Q(1, 1 << 48), P[1], P[2])
            with pytest.raises(C.IntegratorDomainExceeded):
                C.new_run(POS, 40, ri, tuple(-x for x in up), rj, up, momentum_profile=MOM)
    assert sum(c["raw_units_lowered"] > 0 for c in D["cases"]) >= 1


def test_boundary_runs_meet_the_criteria_at_dt_40_and_converge() -> None:
    mpmath.mp.dps = 40
    runs = {(r["case"], r["dt"]): r for r in D["runs"]}
    assert len(runs) == 7 * 3
    for c in D["cases"]:
        ref = REFS[c["name"]]["represented"]
        keys = ["time"] if c["b"] == "0" else ["sweep", "time"]
        for dt in (10, 20, 40):
            r = runs[(c["name"], dt)]
            assert r["status"] == "ok" and r["dP"] == ["0", "0", "0"]
        assert runs[(c["name"], 40)]["max_abs_dE_over_De"] <= 1e-3
        for k in keys:
            v = mpmath.mpf(ref[k])
            err = {dt: mpmath.mpf(runs[(c["name"], dt)][k]) - v for dt in (10, 20, 40)}
            assert abs(err[40]) / abs(v) <= 1e-5, (c["name"], k)
            assert 3.5 < err[20] / err[10] < 4.5 and 3.5 < err[40] / err[20] < 4.5, (c["name"], k, err)
