"""C1-B1 certified E_min_scatter (designer 16th ed.): the recorded certificate re-checks with the current code.

The certificate's number is regenerated from its bound: at the recorded E_min the bound is <= 1e-5, just below it
(E_min / 1.001) it is not -- decided with exact rationals and enclosure upper bounds, never with floats.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from fractions import Fraction as Q
from pathlib import Path

import pytest

import a_reference.c1b1_emin_certificate as K

ROOT = Path(__file__).resolve().parents[1]
D = json.loads((ROOT / "a_reference" / "fixtures" / "c1b1_emin_certificate_v1.json").read_text(encoding="utf-8"))


def test_provenance() -> None:
    p = D["provenance"]
    assert p["uncommitted_changes_in_a_reference"] is False
    if shutil.which("git") is None:
        pytest.skip("git not available")
    for f, h in p["code_sha256"].items():
        blob = subprocess.run(["git", "show", f"{p['git_head']}:{f}"], capture_output=True, cwd=ROOT)
        if blob.returncode != 0:
            pytest.skip("recorded commit not in this clone")
        assert hashlib.sha256(blob.stdout.replace(b"\r\n", b"\n")).hexdigest() == h, f


@pytest.mark.parametrize("key,bits", [("momentum_FX96_80", 80), ("momentum_FX64_48_for_comparison", 48)])
def test_the_bound_generates_the_recorded_number(key, bits) -> None:
    c = D[key]
    E, Rc = Q(c["E_min_hartree"]), Q(c["R_c_bohr"])
    FcU, VcU = K.abs_F_up(Rc), K.abs_V_up(Rc)
    assert str(FcU) == c["abs_F_Rc_up"] and str(VcU) == c["abs_V_Rc_up"]
    assert K.ratio_bound(E, bits, Rc, FcU, VcU) <= K.TARGET                   # certified at E_min
    assert K.ratio_bound(E / Q(1001, 1000), bits, Rc, FcU, VcU) > K.TARGET     # and not much below it
    assert all(s["E_min_over_De"] >= c["E_min_over_De"] for s in c["scan"])  # the smallest over the R_c scan


def test_recorded_values_and_conditions() -> None:
    fx96 = D["momentum_FX96_80"]["E_min_over_De"]
    fx64 = D["momentum_FX64_48_for_comparison"]["E_min_over_De"]
    assert 8e-14 < fx96 < 1.1e-13                                  # ~9.2e-14 De
    assert fx64 > 1e7 * fx96                                       # 16 more fraction bits: ~1e8 lower E_min
    assert D["target"] == "1/100000" and D["b_max_bohr"] == "7071/500" and D["monotone_grid"]["points"] > 600
    assert len(D["conditions"]) == 5
