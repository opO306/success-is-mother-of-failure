"""T9 speculative candidate: the same KDK map and the algebra force evaluated in binary64 (no enclosure). It proposes
grid cells; it is NEVER a result. Type B demonstration (unchecked) and Type C (checked by the verified interval run).

    python -m experiments.resource_evolution_v1.floatcand SCENARIO T CPU OUT
"""

from __future__ import annotations

import json
import math
import sys
import time
from fractions import Fraction as Q


def rhe(x):
    n, d = x.numerator, x.denominator
    sign = -1 if n < 0 else 1
    q, r = divmod(abs(n), d)
    if 2 * r > d or (2 * r == d and q & 1):
        q += 1
    return sign * q


def make_force(program):
    groups, tail, num, den, dn, k, c = program
    fl = lambda P: sorted(((int(d), float(v)) for d, v in P.items() if v != 0), reverse=True)  # noqa: E731
    G = [(float(a), fl(P)) for a, P in groups]
    TL, NU, DE, DN = fl(tail), fl(num), fl(den), fl(dn)
    c, k = float(c), int(k)

    def poly(P, r):
        return sum(v * r ** d for d, v in P)

    def force(r2):
        r = math.sqrt(r2)
        out = poly(TL, r) + sum(math.exp(-a * r) * poly(P, r) for a, P in G)
        nu, de = poly(NU, r), poly(DE, r)
        g, dg = nu / de, poly(DN, r) / (de * de)
        out += c * (2 * k * g * r ** -(2 * k + 1) - dg * r ** -(2 * k))
        return -out / r
    return force


def run(scenario, T):
    from experiments.precision_pilot_a1 import evaluator_adapter as A1E
    from experiments.precision_pilot_a2t import evaluator_adapter as A2E
    from exact_expression_gate_v1 import common as K
    A2E.prepare("algebra")
    f = make_force(A2E._PROBE.PROGRAM)
    q0, p0 = A1E.initial(scenario)
    q = [[float(x) for x in r] for r in q0]
    p = [[float(x) for x in r] for r in p0]
    h, cdt = float(K.H), float(K.CDT)
    n = len(q)
    pairs = [(i, j) for i in range(n) for j in range(i + 1, n)]

    def forces(q):
        F = [[0.0] * 3 for _ in range(n)]
        for i, j in pairs:
            d = [q[j][k] - q[i][k] for k in range(3)]
            g = f((d[0] * d[0] + d[1] * d[1]) + d[2] * d[2])
            for k in range(3):
                t = (h * g) * d[k]
                F[j][k] += t
                F[i][k] -= t
        return F
    F = forces(q)
    for _ in range(T):
        p = [[p[a][k] + F[a][k] for k in range(3)] for a in range(n)]
        q = [[q[a][k] + p[a][k] * cdt for k in range(3)] for a in range(n)]
        F = forces(q)
        p = [[p[a][k] + F[a][k] for k in range(3)] for a in range(n)]
    return [rhe(Q(x) * (1 << 48)) for r in q for x in r] + [rhe(Q(x) * (1 << 80)) for r in p for x in r]


def main():
    scen, T, cpu, outp = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
    import psutil
    psutil.Process().cpu_affinity([cpu])
    t = (time.process_time(), time.perf_counter())
    cells = run(scen, T)
    open(outp, "w", encoding="utf-8").write(json.dumps({"scenario": scen, "T": T, "cells": cells,
                                                        "cpu_s": time.process_time() - t[0],
                                                        "wall_s": time.perf_counter() - t[1]}))


if __name__ == "__main__":
    main()
