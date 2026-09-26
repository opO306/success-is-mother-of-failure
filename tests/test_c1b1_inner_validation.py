"""C1-B1 inner region R < 20 bohr: NUMERICALLY VALIDATED evidence (designer 18th/19th ed.) -- not a certificate.

fixtures/c1b1_inner_validation_v1.json (observables, 72 cases x 3 runs) and fixtures/c1b1_inner_energy_v1.json
(energy carried out of the inner region, with position-only / momentum-only rounding hybrids). These checks pin the
facts reported in the design doc, section 20, including where the error crosses the 1e-5 target (the knee).
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

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "a_reference" / "fixtures"
V = json.loads((FIX / "c1b1_inner_validation_v1.json").read_text(encoding="utf-8"))
En = json.loads((FIX / "c1b1_inner_energy_v1.json").read_text(encoding="utf-8"))
DE = Q("0.000451995775")


def _prov(p, flag):
    assert p[flag] is False
    if shutil.which("git") is None:
        pytest.skip("git not available")
    for f, h in p["code_sha256"].items():
        blob = subprocess.run(["git", "show", f"{p['git_head']}:{f}"], capture_output=True, cwd=ROOT)
        if blob.returncode != 0:
            pytest.skip("recorded commit not in this clone")
        assert hashlib.sha256(blob.stdout.replace(b"\r\n", b"\n")).hexdigest() == h, f


def test_provenance() -> None:
    assert V["status"].startswith("NUMERICALLY VALIDATED") and En["status"].startswith("NUMERICALLY VALIDATED")
    _prov(V["provenance"], "uncommitted_changes_in_a_reference_or_audit")
    _prov(En["provenance"], "uncommitted_changes_in_a_reference")


def test_observables_quantization_and_discretization_are_small_at_every_energy() -> None:
    with mpmath.workdps(50):
        refs = {r["case"]: r for r in V["references"]}
        runs = {(r["case"], r["dt"], r["profile"]): r for r in V["runs"]}
        # v1 record: 96 case entries, 72 distinct -- the buggy first orbiting_b added the b = 0 case twice more per energy
        # (same name, same state, run once); see orbiting_b's docstring
        uniq = {c["name"]: c for c in V["cases"]}
        assert len(V["cases"]) == 96 and len(uniq) == 72 and not any(c["near_orbiting"] for c in V["cases"])
        assert len(runs) == 216 and all(r["status"] == "ok" for r in runs.values())
        for c in uniq.values():
            n = c["name"]
            cand, hp, hp20, ref = runs[(n, 40, "cand")], runs[(n, 40, "hp")], runs[(n, 20, "hp")], refs[n]
            m = lambda r, k: mpmath.mpf(r[k])
            assert abs(m(cand, "sweep") - m(hp, "sweep")) < 2e-12                        # rounding, rad
            assert abs(m(cand, "time") - m(hp, "time")) < 2e-11 * m(hp, "time")
            assert abs(m(hp, "sweep") - m(ref, "sweep")) < 4e-7                          # dt = 40, rad
            assert abs(m(hp, "time") - m(ref, "time")) < 1e-7 * m(ref, "time")
            e40, e20 = m(hp, "time") - m(ref, "time"), m(hp20, "time") - m(ref, "time")
            assert 3.9 < e40 / e20 < 4.1                                                  # second order
            if cand["steps"] == hp["steps"]:
                q = lambda x: mpmath.mpf(x.numerator) / x.denominator
                p_inf = mpmath.sqrt(2 * q(Q("39.9623831237") / Q("5.485799090441e-4") / 2) * q(Q(c["e"]) * DE))
                dP = max(abs(Q(a) - Q(b)) for a, b in zip(cand["P_exit"], hp["P_exit"]))
                assert q(dP) / p_inf < 1e-5


def _energy():
    R = {(r["e"], r["b"], r["profile"]): r for r in En["runs"]}
    em = lambda r: Q(r["Emod_exit"]) - Q(r["Emod_initial"])
    return R, em


def test_the_rounding_energy_error_is_position_rounding_and_crosses_the_target_between_1e8_and_1e9_De() -> None:
    R, em = _energy()
    worst = {}
    for (e, b, p), h in R.items():
        if p != "hp":
            continue
        q = em(R[(e, b, "cand")]) - em(h)
        assert abs(q) < Q(2, 10 ** 16)                                    # ~1e-17 hartree at every energy
        worst[Q(e)] = max(worst.get(Q(e), 0), abs(q) / (2 * Q(e) * DE))  # relative momentum error dE / 2E
        if (e, b, "pos_only") in R:                                      # the cause: position rounding alone
            po, mo = em(R[(e, b, "pos_only")]) - em(h), em(R[(e, b, "mom_only")]) - em(h)
            assert abs(q - po) <= Q(1, 10 ** 9) * abs(q)
            assert abs(mo) <= Q(1, 10 ** 11) * Q(e) * DE                 # momentum FX(96,80): negligible
    assert all(v <= Q(1, 10 ** 5) for e, v in worst.items() if e >= Q(1, 10 ** 8))
    assert worst[Q(1, 10 ** 9)] > Q(1, 10 ** 5)                          # the knee: 1e-8 passes, 1e-9 fails


def test_the_dt40_energy_error_crosses_the_target_near_1e11_De() -> None:
    R, em = _energy()
    for (e, b, p), h in R.items():
        if p == "hp":
            rel = abs(em(h)) / (2 * Q(e) * DE)
            assert rel <= Q(1, 10 ** 5) if Q(e) >= Q(1, 10 ** 11) else rel > Q(1, 10 ** 5)


def test_orbiting_impact_parameter_regression() -> None:
    """b_orb from the barrier-top conditions (both earlier grid versions were wrong: always 0, then invented orbiting
    above E_max). Orbiting exists only below E_max ~ 0.9964 De; inside b <= 2 R_e only from ~0.14 De up."""
    import a_reference.c1b1_inner_validation as I
    for e, want in ((Q(1, 2), 11.719), (Q(15, 100), 14.103), (Q(1, 10), 15.019), (Q(1, 100), 21.679)):
        b, R = I.orbiting(e)
        assert abs(float(b) - want) < 2e-3 and b > 0 and R > I.S.RE_GRID       # never 0, outside the well
        E, dV = I.barrier_energy(R)
        assert abs(E - e * I.S.DE_GRID) < Q(1, 10 ** 30) and dV > 0           # really on a barrier top
    assert I.orbiting(Q(1)) is None and I.orbiting(Q(10)) is None               # above E_max: no orbiting
    assert I.orbiting_b(Q(1, 100)) is None and I.orbiting_b(Q(1, 10)) is None   # b_orb > 2 R_e
    assert I.orbiting_b(Q(1, 2)) is not None


# --- near-orbiting (designer 20th ed., item 3): fixtures/c1b1_orbit_validation_v1.json, run on the Vast node --------

O = json.loads((FIX / "c1b1_orbit_validation_v1.json").read_text(encoding="utf-8"))


def _orbit_rows():
    refs = {r["case"]: r for r in O["references"]}
    runs = {(r["case"], r["dt"], r["profile"]): r for r in O["runs"]}
    for c in O["cases"]:
        n = c["name"]
        yield c, runs[(n, 40, "cand")], runs[(n, 40, "hp")], runs[(n, 20, "hp")], refs[n]


def test_orbit_provenance_and_rounding_stays_below_the_target_even_on_the_separatrix() -> None:
    _prov(O["provenance"], "uncommitted_changes_in_a_reference_or_audit")
    assert len(O["cases"]) == 59 and len(O["runs"]) == 177 and all(r["status"] == "ok" for r in O["runs"])
    with mpmath.workdps(50):
        for c, cand, hp, _, _ in _orbit_rows():
            assert abs(mpmath.mpf(cand["sweep"]) - mpmath.mpf(hp["sweep"])) < 1e-6                 # rounding, rad
            assert abs(mpmath.mpf(cand["time"]) - mpmath.mpf(hp["time"])) < 1e-7 * mpmath.mpf(hp["time"])


def test_orbit_dt40_meets_the_target_away_from_the_separatrix_and_FAILS_near_it() -> None:
    """RECORDED FAILURE (reported, verdict pending): within |b/b_orb - 1| <= 1e-4 the dt = 40 discretization error
    exceeds 1e-5 (sweep up to ~9e-4 rad at 1e-4, O(1) at 1e-6 and on b_orb); at 1e-2 and 0.8 / 1.2 it is second order
    and small. The audit quadrature itself fails at b_orb (1 + 1e-6) for five energies."""
    audit_fail = 0
    with mpmath.workdps(50):
        for c, _, hp, hp20, ref in _orbit_rows():
            tag = c["b_over_b_orb"]
            if "error" in ref:
                audit_fail += 1
                assert tag == "1+1/1000000"
                continue
            e40 = mpmath.mpf(hp["sweep"]) - mpmath.mpf(ref["sweep"])
            t40 = (mpmath.mpf(hp["time"]) - mpmath.mpf(ref["time"])) / mpmath.mpf(ref["time"])
            if tag in ("0.8", "1.2", "1-1/100", "1+1/100"):
                assert abs(e40) < 5e-6 and abs(t40) < 1e-6
                e20 = mpmath.mpf(hp20["time"]) - mpmath.mpf(ref["time"])
                assert 3.9 < (mpmath.mpf(hp["time"]) - mpmath.mpf(ref["time"])) / e20 < 4.1
            elif tag in ("1-1/10000", "1+1/10000"):
                assert abs(e40) > 1e-5                                   # the failure, recorded as such
            else:
                assert abs(e40) > 1e-3
    assert audit_fail == 5
