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


def test_orbiting_impact_parameter_is_outside_the_study_range_below_1e2_De() -> None:
    """The fixed orbiting_b: at E <= 1e-2 De orbiting needs b > 2 R_e (none in the study); at 1 De it lies inside."""
    import a_reference.c1b1_inner_validation as I
    assert I.orbiting_b(Q(1, 100)) is None
    b1 = I.orbiting_b(Q(1))
    assert b1 is not None and 10 < b1 < 10.4                  # ~10.17 bohr: inside b <= 2 R_e -- not yet validated
