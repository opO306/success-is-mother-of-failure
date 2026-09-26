"""C1-B1 E_min_scatter(b_max) -- CONDITIONAL CANDIDATE (designer 17th ed.): C1 and C3 closed, C2 / C4 / C5 open.

The recorded coefficients are regenerated from the interval cells and the analytic long-range bound, and the number
from the bound (passes at E_min, fails at E_min / 1.001). "Certified" is NOT claimed: the bound still assumes first
order (C2), the continuous radial speed (C4) and says nothing about R < 20 bohr (C5).
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
import a_reference.c1b1_two_atom as C

ROOT = Path(__file__).resolve().parents[1]
D = json.loads((ROOT / "a_reference" / "fixtures" / "c1b1_emin_candidate_v2.json").read_text(encoding="utf-8"))


def test_status_and_provenance() -> None:
    assert D["status"].startswith("CONDITIONAL CANDIDATE") and len(D["open"]) == 3
    p = D["provenance"]
    assert p["uncommitted_changes_in_a_reference"] is False
    if shutil.which("git") is None:
        pytest.skip("git not available")
    for f, h in p["code_sha256"].items():
        blob = subprocess.run(["git", "show", f"{p['git_head']}:{f}"], capture_output=True, cwd=ROOT)
        if blob.returncode != 0:
            pytest.skip("recorded commit not in this clone")
        assert hashlib.sha256(blob.stdout.replace(b"\r\n", b"\n")).hexdigest() == h, f


def test_long_range_bound_contains_the_model_beyond_R_END() -> None:
    Kc, V6 = K.long_range_bound()
    assert (str(Kc), str(V6)) == (D["long_range"]["K"], D["long_range"]["V6"]) and V6 < 0
    s = Q(1, 1 << 1024)
    for R in (K.R_END, 3 * K.R_END, 10 ** 9 * Q(1)):
        V, dV, _ = C._model(R * R, 1024, True)
        assert max(abs(dV[0]), abs(dV[1])) * s <= Kc / R ** 7 and V[1] * s <= V6 / R ** 6


def test_cells_cover_the_outer_region_and_V_is_negative_on_each() -> None:
    cs = K.cells()                                         # raises unless V < 0 is proven on every cell
    assert len(cs) == D["cells"] and cs[0][0] == K.RS and cs[-1][1] == K.R_END
    assert all(b == a2 for (_, b, _), (a2, _, _) in zip(cs, cs[1:]))   # no gaps
    row = next(r for r in D["momentum_FX96_80"] if Q(r["b_max"]) == K.B_MAX_STUDY)
    A, B = K.coefficients(K.B_MAX_STUDY, 80, cs)
    assert (str(A), str(B)) == (row["A"], row["B"])


@pytest.mark.parametrize("key", ["momentum_FX96_80", "momentum_FX64_48_for_comparison"])
def test_the_bound_generates_the_recorded_numbers(key) -> None:
    for r in D[key]:
        A, B, E = Q(r["A"]), Q(r["B"]), Q(r["E_min_hartree"])
        assert K.ratio_bound(E, A, B) <= K.TARGET < K.ratio_bound(E / Q(1001, 1000), A, B)


def test_recorded_values() -> None:
    e = {Q(r["b_max"]): r["E_min_over_De"] for r in D["momentum_FX96_80"]}
    assert all(6e-14 < v < 7e-14 for v in e.values())          # ~6.6e-14 De, nearly independent of b_max < 20
    assert e[Q(0)] <= e[K.B_MAX_STUDY] <= e[Q(39, 2)]
    f = {Q(r["b_max"]): r["E_min_over_De"] for r in D["momentum_FX64_48_for_comparison"]}
    assert f[K.B_MAX_STUDY] > 1e7 * e[K.B_MAX_STUDY]
