"""Evaluator adapter for PRECISION_PILOT_A1. One pass = one call of the evaluator at an integer working precision p,
from the exact initial state to step T, reading step T.

Registry: 'original' = repository exact_expression_gate_v1.stream (read-only), the only evaluator used in A1.
'algebra' is registered for A2 and refuses to run here, so A1 cannot use it by accident.
"""

from __future__ import annotations

import ast
import time
from fractions import Fraction as Q

SCENARIOS = {
    "A2_bound": ([("-71/20", 0, 0), ("71/20", 0, 0)], [(1, -3, 0), (-1, 3, 0)]),
    "A3_low": ([(0, 0, 0), (25, 0, 0), (0, 25, 0)], [(2, 1, 0), (-1, 2, 0), (-1, -3, 0)]),
    "A3_high": ([(0, 0, 0), ("71/10", 0, 0), ("71/20", "6149/1000", 0)],
                [(3, 0, "1/2"), ("-3/2", "13/5", 0), ("-3/2", "-13/5", "-1/2")]),
}
P_MIN, P_MAX = 64, 1024
OUTCOMES = ("DECIDED", "UNDECIDED_AT_PRECISION", "DOMAIN_UNPROVEN", "DOMAIN_VIOLATED_PROVEN", "OUT_OF_RANGE")


def initial(name):
    q0, p0 = SCENARIOS[name]
    return [[Q(x) for x in r] for r in q0], [[Q(x) for x in r] for r in p0]


def _scaled_endpoints(key):
    """Exact endpoints of every component, positions times 2^48, momenta times 2^80 (as decimal fraction strings)."""
    from mpmath.libmp import to_rational
    ends = []
    for part in key.split("|"):
        lo, hi = ast.literal_eval(part)
        ends.append((Q(*to_rational(lo)), Q(*to_rational(hi))))
    n = len(ends) // 2
    out = [(lo * (1 << 48), hi * (1 << 48)) for lo, hi in ends[:n]] + \
          [(lo * (1 << 80), hi * (1 << 80)) for lo, hi in ends[n:]]
    return [[str(lo), str(hi)] for lo, hi in out]


def _original(name, p, T):
    from mpmath import iv
    from exact_expression_gate_v1 import stream
    q0, p0 = initial(name)
    r = stream.run(q0, p0, p, T, {T}, exact=False)
    effective = iv.prec
    rec = {"completed_steps": r["completed_steps"], "stop": r["stop"], "stop_step": r["stop_step"],
           "effective_p": effective, "cells": None, "endpoints_scaled": None}
    if T in r["read"]:
        cells, key = r["read"][T]
        rec["cells"] = cells
        rec["endpoints_scaled"] = _scaled_endpoints(key)
    if r["stop"] == "VIOLATED":
        rec["outcome"] = "DOMAIN_VIOLATED_PROVEN"
    elif r["stop"] == "UNPROVEN":
        rec["outcome"] = "DOMAIN_UNPROVEN"
    elif r["stop"] == "OUT_OF_RANGE":
        rec["outcome"] = "OUT_OF_RANGE"
    elif rec["cells"] is not None:
        rec["outcome"] = "DECIDED"
    else:
        rec["outcome"] = "UNDECIDED_AT_PRECISION"
    return rec


def _algebra(name, p, T):
    raise NotImplementedError("evaluator 'algebra' is registered for A2 and is not used in A1")


EVALUATORS = {"original": _original, "algebra": _algebra}


def run_pass(evaluator, name, p, T):
    if not (isinstance(p, int) and P_MIN <= p <= P_MAX):
        raise ValueError(f"p {p!r} outside the audited domain [{P_MIN}, {P_MAX}]")
    t = (time.process_time(), time.perf_counter())
    rec = EVALUATORS[evaluator](name, p, T)
    rec.update(requested_p=p, evaluator=evaluator, scenario=name, T=T,
               cpu_s=time.process_time() - t[0], wall_s=time.perf_counter() - t[1])
    if rec["effective_p"] != p:
        rec["outcome"] = "INVALID_EVIDENCE"
    return rec
