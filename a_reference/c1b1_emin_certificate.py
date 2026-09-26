"""C1-B1 certified lower energy bound for scattering, E_min_scatter (designer 16th ed.): the proof generates the number.

The momentum profile rounds every impulse J = F(R) dr/R dt/2 (per component) to a 2^-F grid; below half a unit it
becomes 0. For one scattering event this module bounds the resulting relative-momentum error |dP| and finds the
smallest relative energy E for which |dP| / p <= TARGET (1e-5) is guaranteed -- under the conditions listed below.
Nothing here is wired into the integrator domain check yet (that needs the designer's approval of condition C1).

Bound (momentum FX(W, F), unit u = 2^-F, dt = 40 a.u., relative momentum p = sqrt(2 mu E), v = p / mu):
  * one impulse, rounded per component to the nearest unit: |error| <= min(sqrt(3) u / 2, |J|), |J| = |F(R)| dt / 2;
    the same J is used by two half kicks (the second of one step and the first of the next): 2 x that per position.
  * outer region R >= R_S = 20 bohr, each leg (in and out): R is monotone and |dR/dt| >= v / sqrt(2)   [needs C1]
    so successive positions are >= s = dt v / sqrt(2) apart. With a free split radius R_c:
        positions with R <= R_c:  at most (R_c - R_S) / s + 1, error sqrt(3) u each (2 half kicks)
        positions with R >  R_c:  sum of 2 |F(R_k)| dt / 2 <= dt |F(R_c)| + (dt / s) int_Rc^inf |F| dR
                                   = dt |F(R_c)| + (dt / s) |V(R_c)|                 [needs C3]
    both legs: |dP_outer| <= 2 sqrt(3) u ((R_c - R_S)/s + 1) + 2 dt |F(R_c)| + 2 (dt / s) |V(R_c)|
  * inner region R < 20 bohr: NOT part of the certificate (C5) -- estimated separately, ~1e9 below the target.
  E_min = the smallest E (bisection on exact rationals, every term an upper bound) with |dP_outer| / p <= TARGET,
  minimised over R_c.

Conditions (all disclosed in the design doc, section 15):
  C1  impact parameter b <= R_S / sqrt(2) = 14.14 bohr (|dR/dt|^2 = v^2 - 2V/mu - (b v / R)^2 >= v^2 / 2 for R >= sqrt(2) b,
      using V < 0 there). A NEW domain condition -- the validated study cases have b <= 2 R_e ~ 14.2 bohr.
  C2  first order: the rounding errors are summed along the unrounded trajectory; their feedback on later forces is
      not included (two-body scattering is not chaotic, but this is an assumption).
  C3  V < 0, V increasing and |F| decreasing on [R_S, infinity): checked with enclosures on a geometric grid
      20 ... 1e7 bohr (grid points only); beyond 1e7 bohr the model's long-range form is relied on.
  C4  step spacing uses the continuous trajectory (the discrete one follows it within the measured 1e-5).
  C5  inner region R < 20 bohr: rounding error estimated, not certified.

Run: python -m a_reference.c1b1_emin_certificate    -> fixtures/c1b1_emin_certificate_v1.json
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from fractions import Fraction as Q
from math import isqrt
from pathlib import Path

import a_reference.c1b1_two_atom as C

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent / "fixtures" / "c1b1_emin_certificate_v1.json"
M = 1024                                   # enclosure precision (bits)
DT = Q(40)
MU = C.AR40_MASS_ME / 2
RS = Q(20)
TARGET = Q(1, 10 ** 5)
B_MAX = Q(14142, 1000)                     # <= 20 / sqrt(2) = 14.1421...
SQRT3_UP = Q(17321, 10000)                 # >= sqrt(3)
SQRT2_UP = Q(14143, 10000)                 # >= sqrt(2)
assert SQRT3_UP ** 2 >= 3 and SQRT2_UP ** 2 >= 2 and (B_MAX * 2) ** 2 * 2 <= (RS * 2) ** 2   # sqrt(2) b <= R_S


def _enc(R: Q):
    V, dV, _ = C._model(Q(R) ** 2, M, True)
    s = Q(1, 1 << M)
    return (V[0] * s, V[1] * s), (dV[0] * s, dV[1] * s)


def abs_F_up(R: Q) -> Q:
    return max(abs(x) for x in _enc(R)[1])


def abs_V_up(R: Q) -> Q:
    return max(abs(x) for x in _enc(R)[0])


def monotone_grid(r1=10 ** 7, ratio=Q(51, 50)) -> int:
    """C3 on grid points: V < 0, dV/dR > 0, V increasing and |F| = dV/dR decreasing from one point to the next."""
    R, n, prev = RS, 0, None
    while R <= r1:
        V, dV = _enc(R)
        if not (V[1] < 0 and dV[0] > 0):
            raise AssertionError(f"sign condition fails at {float(R)} bohr")
        if prev is not None and not (dV[1] <= prev[0] and V[0] >= prev[1]):
            raise AssertionError(f"monotonicity fails at {float(R)} bohr")
        prev = (dV[0], V[1])
        R *= ratio
        n += 1
    return n


def _sqrt_lo(x: Q) -> Q:
    k = 200
    return Q(isqrt(int(x * (1 << (2 * k)))), 1 << k)


def ratio_bound(E: Q, F_bits: int, Rc: Q, FcU: Q, VcU: Q) -> Q:
    """Upper bound of |dP_outer| / p at relative energy E (hartree)."""
    u = Q(1, 1 << F_bits)
    p = _sqrt_lo(2 * MU * E)
    s_inv = SQRT2_UP * MU / (DT * p)                            # 1 / s, s = dt v / sqrt(2)
    n_in = (Rc - RS) * s_inv + 1
    dP = 2 * SQRT3_UP * u * n_in + 2 * DT * FcU + 2 * DT * VcU * s_inv
    return dP / p


def e_min_for(F_bits: int, Rc: Q) -> Q:
    FcU, VcU = abs_F_up(Rc), abs_V_up(Rc)
    lo, hi = Q(1, 10 ** 40), Q(1)
    if ratio_bound(hi, F_bits, Rc, FcU, VcU) > TARGET:
        raise AssertionError("no certified E below 1 hartree")
    while hi / lo > Q(10001, 10000):
        mid = (lo + hi) / 2 if hi / lo < 4 else Q(isqrt(int(lo * hi * 10 ** 100)), 10 ** 50)
        if ratio_bound(mid, F_bits, Rc, FcU, VcU) <= TARGET:
            hi = mid
        else:
            lo = mid
    return hi


def certify(F_bits: int, rc_grid) -> dict:
    """E_min minimised over the split radius R_c (any R_c gives a valid bound; the smallest wins)."""
    rows = [(e_min_for(F_bits, Q(r)), Q(r)) for r in rc_grid]
    E, Rc = min(rows)
    return {"fraction_bits": F_bits, "R_c_bohr": str(Rc), "E_min_hartree": str(E),
            "E_min_over_De": float(E / C.DE_CONTRACT), "abs_F_Rc_up": str(abs_F_up(Rc)), "abs_V_Rc_up": str(abs_V_up(Rc)),
            "scan": [{"R_c": str(r), "E_min_over_De": float(e / C.DE_CONTRACT)} for e, r in rows]}


RC_GRID = {80: [4000, 5000, 6000, 7000, 7567, 8000, 9000, 10000, 12000],
           48: [150, 200, 300, 400, 438, 500, 600, 800, 1000]}


def main():
    n = monotone_grid()
    head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=ROOT).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain", "--", "a_reference"], capture_output=True, text=True,
                           cwd=ROOT).stdout.strip()
    sha = lambda f: hashlib.sha256((ROOT / f).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    doc = {"format": "c1b1-emin-certificate-v1", "contract": C.CONTRACT_VERSION, "dt": 40, "target": str(TARGET),
           "R_S_bohr": str(RS), "b_max_bohr": str(B_MAX), "enclosure_bits": M,
           "monotone_grid": {"from_bohr": 20, "to_bohr": 10 ** 7, "ratio": "51/50", "points": n},
           "conditions": ["C1 b <= 14.14 bohr (new domain condition)", "C2 first order (no feedback)",
                          "C3 monotone V, |F| beyond 20 bohr (grid-checked to 1e7 bohr)",
                          "C4 continuous-trajectory step spacing", "C5 inner region R < 20 bohr not certified"],
           "momentum_FX96_80": certify(80, RC_GRID[80]),
           "momentum_FX64_48_for_comparison": certify(48, RC_GRID[48]),
           "provenance": {"git_head": head, "uncommitted_changes_in_a_reference": bool(dirty),
                          "code_sha256": {f: sha(f) for f in ("a_reference/c1b1_two_atom.py",
                                                              "a_reference/c1b1_emin_certificate.py")}}}
    OUT.write_text(json.dumps(doc, indent=1), encoding="utf-8")
    print(json.dumps({k: doc[k]["E_min_over_De"] for k in ("momentum_FX96_80", "momentum_FX64_48_for_comparison")}))


if __name__ == "__main__":
    main()
