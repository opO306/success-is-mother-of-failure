"""MULTIATOM_PARALLEL_V1 E2 gate (b) in the new domain: for every distinct step-0 pair R^2 of every FCC_N scenario,
the E1 (algebra) and E2 (rw:R1+R2) force intervals at p must contain the 1024-bit original (E0) enclosure.

    python -m experiments.multiatom_parallel_v1.e2gate P OUT
"""

from __future__ import annotations

import json
import sys
import time
from fractions import Fraction as Q

from mpmath import iv
from mpmath.libmp import to_rational

from experiments.multiatom_parallel_v1 import scenarios as SC

N_LIST = (2, 3, 4, 6, 8, 12, 16, 24, 32, 48)


def _b(x):
    return Q(*to_rational(x._mpi_[0])), Q(*to_rational(x._mpi_[1]))


def main():
    prec, outp = int(sys.argv[1]), sys.argv[2]
    t0 = time.process_time()
    from experiments.precision_pilot_a2t import evaluator_adapter as A2E
    from experiments.rewrite_pilot_a3 import adapter as AD
    from experiments.rewrite_pilot_a3 import rwforce as RW
    AD.prepare("rw:R1+R2")
    LI = sys.modules["exact_expression_gate_v0.lang_iv"]
    r2s = set()
    for n in N_LIST:
        q0, _ = SC.initial(n)
        for i in range(n):
            for j in range(i + 1, n):
                r2s.add(sum((q0[j][k] - q0[i][k]) ** 2 for k in range(3)))
    rows, ok = [], True
    for r2 in sorted(r2s):
        iv.prec = 1024
        ref = _b(LI.G_of_R2(LI.c(r2)))
        f1 = A2E._PROBE.Force(A2E._PROBE.Backend("mp", prec), True)   # sets iv.prec = prec
        e1 = _b(f1(LI.c(r2)))
        iv.prec = prec
        e2 = _b(RW.RwForce(AD._PLAN)(LI.c(r2)))
        c1 = e1[0] <= ref[0] and ref[1] <= e1[1]
        c2 = e2[0] <= ref[0] and ref[1] <= e2[1]
        ok = ok and c1 and c2
        rows.append({"R2": str(r2), "E1_contains_E0_1024": c1, "E2_contains_E0_1024": c2,
                     "E1_width": float(e1[1] - e1[0]), "E2_width": float(e2[1] - e2[0])})
    json.dump({"p": prec, "n_distinct_R2": len(rows), "PASS": ok, "rows": rows,
               "cpu_s": time.process_time() - t0}, open(outp, "w", encoding="utf-8"), indent=1)
    print("E2 domain gate", ok, len(rows))


if __name__ == "__main__":
    main()
