"""C1-B1 lower energy bound for scattering, E_min_scatter(b_max) -- a CONDITIONAL CANDIDATE, not certified (designer 17th ed.).

The momentum profile rounds every impulse J = F(R) dr/R dt/2 (per component) to a 2^-F grid; below half a unit it
becomes 0. For one scattering event this module bounds the resulting relative-momentum error |dP| from the OUTER
region R >= R_S = 20 bohr and finds the smallest relative energy E with |dP| / p <= TARGET (1e-5).
It is NOT wired into the integrator domain check: conditions C2, C4, C5 below are still assumptions (17th ed.).

Closed (17th ed. items 1-2):
  C1  the impact parameter bound is a parameter b_max < R_S: |dR/dt|^2 = v^2 - 2V/mu - (b v / R)^2 >= v^2 (1 - b_max^2/R^2)
      wherever V <= 0 (and R >= R_S > b_max).
  C3  interval coverage, no monotonicity assumed: [R_S, R_END] is cut into geometric cells; on every cell interval
      arithmetic (a_reference.c1b1_two_atom._model_R over the whole cell) encloses V and dV/dR, and V < 0 is checked.
      Beyond R_END = 1e7 bohr an ANALYTIC bound from the frozen model's coefficients: |F(R)| <= K / R^7 and V < 0
      (long_range_bound below; every exponential factor bounded by e^-x <= n! / x^n).
Still assumptions (NOT closed):
  C2  first order: the rounding errors are summed along the unrounded trajectory; their feedback is not bounded.
  C4  positions per cell use the CONTINUOUS radial speed (the discrete KDK trajectory is not bounded directly).
  C5  inner region R < 20 bohr not bounded.

Bound (u = 2^-F, dt = 40, p = sqrt(2 mu E), v = p / mu), each leg (in / out), then x 2:
  cell j = [a_j, b_j]: positions <= (b_j - a_j) / s_j + 1, s_j = dt v sqrt(1 - b_max^2 / a_j^2)          (C1, C4)
  per position <= min(sqrt(3) u, dt sup_j |F|)   (per component min(u/2, |J_k|), two half kicks share one J)
  beyond R_END: dt K / R_END^7 + (1 / s_END) dt int K R^-7 dR = dt K / R_END^7 + K / (6 R_END^6 v c_END)

Run: python -m a_reference.c1b1_emin_certificate    -> fixtures/c1b1_emin_candidate_v2.json
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from fractions import Fraction as Q
from math import factorial, isqrt
from pathlib import Path

import a_reference.ar2_lang2024 as L
import a_reference.c1b1_two_atom as C

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent / "fixtures" / "c1b1_emin_candidate_v2.json"
M = 512                                    # enclosure precision (bits)
DT = Q(40)
MU = C.AR40_MASS_ME / 2
RS = Q(20)
R_END = Q(10 ** 7)
CELL = Q(65, 64)                           # geometric cell ratio
TARGET = Q(1, 10 ** 5)
SQRT3_UP = Q(17321, 10000)
assert SQRT3_UP ** 2 >= 3
B_MAX_STUDY = 2 * Q("7.1129")              # the validated study range: b <= 2 R_e (grid value), c1b1_dt_study.B_FRACS


def _sqrt_lo(x: Q) -> Q:
    k = 200
    return Q(isqrt(int(x * (1 << (2 * k)))), 1 << k)


# --- C3: interval coverage of [R_S, R_END] ------------------------------------------------------------------------

def cell_enclosure(a: Q, b: Q):
    """(V interval, dV/dR interval) valid for every R in [a, b]."""
    lo, hi = (a.numerator << M) // a.denominator, -((-(b.numerator << M)) // b.denominator)
    V, dV, _ = C._model_R((lo, hi), M, True)
    s = Q(1, 1 << M)
    return (V[0] * s, V[1] * s), (dV[0] * s, dV[1] * s)


def cells():
    out, a = [], RS
    while a < R_END:
        b = min(a * CELL, R_END)
        V, dV = cell_enclosure(a, b)
        if not V[1] < 0:
            raise AssertionError(f"V < 0 not proven on [{float(a)}, {float(b)}]")
        out.append((a, b, max(abs(dV[0]), abs(dV[1]))))
        a = b
    return out


# --- C3: analytic bound beyond R_END ---------------------------------------------------------------------------------

def long_range_bound(R0: Q = R_END):
    """(K, V6) with |dV/dR| <= K / R^7 and V <= V6 / R^6 < 0 for all R >= R0, from the frozen C1-A coefficients.
    Mirrors the structure of c1b1_two_atom._model: short-range e^-aR P(R), dispersion -C_k D_k(R) / R^2k with
    D = 1 - T_n(eta R), and with retardation g - T (BO, lowest k) or -T (REL, lowest k); T_n(x) = e^-x sum_{i<=n} x^i/i!."""
    assert all(a >= 0 for a in L.RET_A) and all(b >= 0 for b in L.RET_B) and len(L.RET_B) == len(L.RET_A) + 1
    K, V6 = Q(0), Q(0)
    B_top = L.RET_B[-1]
    top = len(L.RET_B)                                      # Dn = 1 + sum B_m R^(m+1), degree `top`
    nG = (R0 ** -(top - 1) + sum(a * R0 ** (m + 1 - (top - 1)) for m, a in enumerate(L.RET_A)))   # N <= nG R^(top-1)
    G = nG / B_top                                          # g = N / Dn <= G / R
    a1 = sum((m + 1) * a * R0 ** (m - (top - 2)) for m, a in enumerate(L.RET_A))   # N' <= a1 R^(top-2)
    b1 = sum((m + 1) * b * R0 ** (m - (top - 1)) for m, b in enumerate(L.RET_B))   # Dn' <= b1 R^(top-1)
    G2 = a1 / B_top + nG * b1 / B_top ** 2                  # |g'| <= G2 / R^2
    to7 = lambda coef, q: coef * R0 ** (7 - q)              # coef R^-q <= coef R0^(7-q) R^-7 for R >= R0, q >= 7
    for name, (short, (eta, Cs, kadd)) in L.COMPONENTS.items():
        for alpha, coefs in short.values():
            A = sum(abs(c) * (abs(i) + alpha) for i, c in coefs.items())   # |P' - aP| <= A R^2 (R >= 1, i <= 2)
            ex = Q(factorial(30)) / alpha ** 30                           # e^-aR <= 30! / (aR)^30 = ex / R^30
            K += to7(A * ex, 28)                                          # A R^2 / R^30
            P = sum(abs(c) for c in coefs.values())                       # |P| <= P R^2
            V6 += P * ex * R0 ** -22                                      # e^-aR |P| <= P ex R^-28 <= P ex R0^-22 R^-6
        kmin = min(Cs)
        for k, c in Cs.items():
            n = 2 * k + kadd
            Tq = Q(n + 1) * Q(factorial(n + 30)) / factorial(n) / eta ** 30    # T <= Tq R^-30  (x >= n)
            Tdq = eta * Q(factorial(n + 30)) / factorial(n) / eta ** 30        # |T'| <= Tdq R^-30
            if kmin == k and name == "BO":                                      # D = g - T
                K += abs(c) * (to7(G2, 2 * k + 2) + to7(Tdq, 2 * k + 30) + 2 * k * (to7(G, 2 * k + 2) + to7(Tq, 2 * k + 31)))
                V6 += abs(c) * Tq * R0 ** -30                                    # -C (g - T) / R^6 <= C T / R^6 (g >= 0)
            elif kmin == k and name == "REL":                                   # D = -T
                K += abs(c) * (to7(Tdq, 2 * k + 30) + 2 * k * to7(Tq, 2 * k + 31))
                V6 += abs(c) * Tq * R0 ** (6 - 2 * k - 30)
            else:                                                               # D = 1 - T
                if 2 * k + 1 < 7:
                    raise AssertionError(f"unretarded R^-{2 * k} term: K / R^7 does not bound it")
                K += abs(c) * (to7(Tdq, 2 * k + 30) + 2 * k * (to7(Q(1), 2 * k + 1) + to7(Tq, 2 * k + 31)))
                if k == 3:
                    V6 += -c + abs(c) * Tq * R0 ** -30                          # -C (1 - T) / R^6
                else:
                    V6 += abs(c) * R0 ** (6 - 2 * k)
    if not V6 < 0:
        raise AssertionError("V < 0 beyond R_END not proven")
    return K, V6


# --- the bound ------------------------------------------------------------------------------------------------

def coefficients(b_max: Q, F_bits: int, cs=None, KV=None):
    """(A, B) with |dP_outer| <= A / v + B for every scattering event with b <= b_max (both legs)."""
    if not 0 <= b_max < RS:
        raise ValueError("need 0 <= b_max < R_S")
    u = Q(1, 1 << F_bits)
    cs = cs or cells()
    K, _ = KV or long_range_bound()
    A = B = Q(0)
    for a, b, F in cs:
        c = _sqrt_lo(1 - (b_max / a) ** 2)
        w = min(SQRT3_UP * u, DT * F)
        A += w * (b - a) / (DT * c)
        B += w
    c_end = _sqrt_lo(1 - (b_max / R_END) ** 2)
    A += K / (6 * R_END ** 6 * c_end)
    B += DT * K / R_END ** 7
    return _round_up(2 * A), _round_up(2 * B)


def _round_up(x: Q, bits: int = 128) -> Q:
    """x rounded UP to a 128-bit binary mantissa (an upper bound stays an upper bound; keeps the record printable)."""
    e = bits - (x.numerator.bit_length() - x.denominator.bit_length())
    n = x * (Q(2) ** e)
    return Q(-((-n.numerator) // n.denominator)) / Q(2) ** e


def ratio_bound(E: Q, A: Q, B: Q) -> Q:
    """|dP_outer| / p <= (A / v + B) / p = A mu / p^2 + B / p = A / (2E) + B / p."""
    p = _sqrt_lo(2 * MU * E)
    return A / (2 * E) + B / p


def e_min(A: Q, B: Q) -> Q:
    lo, hi = Q(1, 10 ** 40), Q(1)
    assert ratio_bound(hi, A, B) <= TARGET
    while hi / lo > Q(10001, 10000):
        mid = (lo + hi) / 2 if hi / lo < 4 else Q(isqrt(int(lo * hi * 10 ** 100)), 10 ** 50)
        if ratio_bound(mid, A, B) <= TARGET:
            hi = mid
        else:
            lo = mid
    return hi


B_MAX_SCAN = [Q(0), Q(5), Q(10), B_MAX_STUDY, Q(18), Q(39, 2)]


def main():
    cs = cells()
    KV = long_range_bound()
    head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=ROOT).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain", "--", "a_reference"], capture_output=True, text=True,
                           cwd=ROOT).stdout.strip()
    sha = lambda f: hashlib.sha256((ROOT / f).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    rows = {}
    for bits in (80, 48):
        rows[bits] = []
        for bm in B_MAX_SCAN:
            A, B = coefficients(bm, bits, cs, KV)
            E = e_min(A, B)
            rows[bits].append({"b_max": str(bm), "A": str(A), "B": str(B), "E_min_hartree": str(E),
                               "E_min_over_De": float(E / C.DE_CONTRACT)})
    doc = {"format": "c1b1-emin-candidate-v2", "status": "CONDITIONAL CANDIDATE -- not certified (C2, C4, C5 open)",
           "contract": C.CONTRACT_VERSION, "dt": 40, "target": str(TARGET), "R_S_bohr": str(RS), "R_END_bohr": str(R_END),
           "cell_ratio": str(CELL), "cells": len(cs), "enclosure_bits": M,
           "long_range": {"K": str(KV[0]), "V6": str(KV[1])},
           "closed": ["C1 b_max parameter", "C3 interval coverage to 1e7 bohr + analytic bound beyond"],
           "open": ["C2 feedback of rounding errors on the trajectory", "C4 continuous radial speed / step spacing",
                    "C5 inner region R < 20 bohr"],
           "momentum_FX96_80": rows[80], "momentum_FX64_48_for_comparison": rows[48],
           "provenance": {"git_head": head, "uncommitted_changes_in_a_reference": bool(dirty),
                          "code_sha256": {f: sha(f) for f in ("a_reference/c1b1_two_atom.py",
                                                              "a_reference/c1b1_emin_certificate.py")}}}
    OUT.write_text(json.dumps(doc, indent=1), encoding="utf-8")
    for r in rows[80]:
        print("FX(96,80) b_max", r["b_max"], "E_min/De", r["E_min_over_De"])


if __name__ == "__main__":
    main()
