"""Applicability and enclosure checks of the exact formula rearrangement (run in its own process).

1. Applicability: the rearranged form divides by R and by den(R) = 1 + sum RET_B[m] R^(m+1); every RET_B > 0 makes
   den(R) >= 1 for R > 0, and the run's domain obligation R >= r_min > 0 keeps R > 0.
2. Point enclosures: at 48 radii in [r_min, 30] bohr and p in {64, 96, 128, 192}, the algebra enclosure must contain the
   1024-bit enclosure of the ORIGINAL formula (lang_iv). Necessary evidence, not a proof.
3. Interval inputs: on 12 R^2 intervals, the algebra enclosure over the interval must contain the 1024-bit original
   enclosures at the interval's two ends and midpoint (true values at points of the interval).

    python -m experiments.formula_repro_b_v0.transform_checks OUT
"""

from __future__ import annotations

import json
import sys
from fractions import Fraction as Q
from pathlib import Path

from .harness import load_probe


def main(out):
    P = load_probe()
    P.PROGRAM = P.exact_program()
    L = P.L
    res = {"RET_B_all_positive": all(b > 0 for b in L.RET_B), "r_min_positive": L.R_MIN_BOHR > 0}
    rmin = L.R_MIN_BOHR
    radii = [rmin + (Q(30) - rmin) * Q(i, 47) for i in range(48)]
    H = P.Backend("mp", 1024)
    refs = [H.bounds(P.LI.G_of_R2(H.lift(r * r))) for r in radii]
    bad, n = [], 0
    for bits in (64, 96, 128, 192):
        B = P.Backend("mp", bits)
        f = P.Force(B, compiled=True)
        for r, (rlo, rhi) in zip(radii, refs):
            lo, hi = B.bounds(f(B.lift(r * r)))
            n += 1
            if not (lo <= rlo and rhi <= hi):
                bad.append({"bits": bits, "R": str(r)})
    res["point_checks"], res["point_failures"] = n, bad
    ibad, m = [], 0
    centers = [rmin + (Q(30) - rmin) * Q(i, 11) for i in range(12)]
    for bits in (64, 96, 128, 192):
        B = P.Backend("mp", bits)
        f = P.Force(B, compiled=True)
        for c in centers:
            a, b = (c * c) * (1 - Q(1, 10 ** 6)), (c * c) * (1 + Q(1, 10 ** 6))
            if a < rmin * rmin:
                a = rmin * rmin
            Hh = P.Backend("mp", 1024)
            pts = [Hh.bounds(P.LI.G_of_R2(Hh.lift(x))) for x in (a, (a + b) / 2, b)]
            B = P.Backend("mp", bits)                      # Backend('mp') sets the global iv.prec: re-select
            from mpmath import iv
            x = iv.mpf([P.LI.c(a).a, P.LI.c(b).b])           # outward hull of [a, b] at this precision
            lo, hi = B.bounds(f(x))
            m += 1
            if not all(lo <= plo and phi <= hi for plo, phi in pts):
                ibad.append({"bits": bits, "center_R": str(c)})
    res["interval_checks"], res["interval_failures"] = m, ibad
    res["PASS"] = res["RET_B_all_positive"] and res["r_min_positive"] and not bad and not ibad
    Path(out).write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps({k: (v if not isinstance(v, list) else len(v)) for k, v in res.items()}))


if __name__ == "__main__":
    main(sys.argv[1])
