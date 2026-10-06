"""Precision policies P0-P3 and the per-request ledger (PRECISION_PILOT_A1 protocol). Pure functions of the recorded
pass outcomes: no evaluator calls here.

A pass record needs: requested_p, outcome, completed_steps, endpoints_scaled (when step T was reached).
"""

from __future__ import annotations

import hashlib
import json
import math
from fractions import Fraction as Q

GRID = [64, 96, 128, 192, 256, 384, 512, 768, 1024]
P_MIN, P_MAX = 64, 1024
GUARD = 8
FINAL = ("DECIDED", "DOMAIN_VIOLATED_PROVEN", "OUT_OF_RANGE", "INVALID_EVIDENCE")


def rhe(x: Q) -> int:
    q, r = divmod(x.numerator, x.denominator)
    if 2 * r > x.denominator or (2 * r == x.denominator and q & 1):
        q += 1
    return q


def ceil_log2(x: Q) -> int:
    if x <= 0:
        raise ValueError
    e = x.numerator.bit_length() - x.denominator.bit_length()
    while Q(2) ** e < x:
        e += 1
    while e > -10**6 and Q(2) ** (e - 1) >= x:
        e -= 1
    return e


def width_extra(endpoints_scaled):
    """Extra bits suggested by the undecided components: max ceil(log2(width / margin)), margin <= 0 -> 32."""
    extra = None
    for lo, hi in endpoints_scaled:
        lo, hi = Q(lo), Q(hi)
        if rhe(lo) == rhe(hi):
            continue
        mid = (lo + hi) / 2
        margin = Q(1, 2) - abs(mid - rhe(mid))
        e = 32 if margin <= 0 else ceil_log2((hi - lo) / margin)
        extra = e if extra is None else max(extra, e)
    return 0 if extra is None else extra


def p2_next(last, T):
    """Learning-free next p after a non-final pass (P2 rule)."""
    p = last["requested_p"]
    if last["outcome"] == "UNDECIDED_AT_PRECISION" and last.get("endpoints_scaled"):
        nxt = p + max(width_extra(last["endpoints_scaled"]), 1) + GUARD
    elif last["outcome"] == "DOMAIN_UNPROVEN":
        k = last["completed_steps"]
        nxt = 2 * p if k <= 0 else -((-p * T) // k) + GUARD
    else:
        nxt = 2 * p
    return max(nxt, p + 1)


def next_p(policy, params, history, T):
    """The policy's next p, or None when the request is final. history: list of pass records in order."""
    if history and history[-1]["outcome"] in FINAL:
        return None
    tried = {h["requested_p"] for h in history}
    if policy == "P0":
        cand = [g for g in GRID if g not in tried and (not history or g > max(tried))]
        nxt = cand[0] if cand else None
    elif policy == "P1":
        if not history:
            nxt = params["s1"]
        else:
            cand = [g for g in GRID if g > max(tried)]
            nxt = cand[0] if cand else None
    elif policy == "P2":
        nxt = P_MIN if not history else p2_next(history[-1], T)
    elif policy == "P3":
        if not history:
            line = params["lines"].get(params["scenario"])
            nxt = P_MIN if line is None else max(P_MIN, math.ceil(Q(line[0]) + Q(line[1]) * T) + GUARD)
        else:
            nxt = p2_next(history[-1], T)
    else:
        raise ValueError(policy)
    if nxt is None:
        return None
    if nxt > P_MAX:
        return "CAP" if max(tried, default=0) >= P_MAX else P_MAX
    return nxt


def lowest_success(history):
    s = [h["requested_p"] for h in history if h["outcome"] == "DECIDED"]
    return min(s) if s else None


def train(training_runs):
    """training_runs: {(scenario, T): history} from P2. Returns frozen params and their hash."""
    lows = {k: lowest_success(h) for k, h in training_runs.items()}
    vals = sorted(v for v in lows.values() if v is not None)
    s1 = None
    if vals:
        n = len(vals)
        s1 = vals[n // 2] if n % 2 else -((-(vals[n // 2 - 1] + vals[n // 2])) // 2)
    lines = {}
    for scen in sorted({k[0] for k in training_runs}):
        pts = sorted((T, lows[(s, T)]) for (s, T) in lows if s == scen and lows[(s, T)] is not None)
        if len(pts) >= 2:
            (t1, p1), (t2, p2) = pts[0], pts[-1]
            b = Q(p2 - p1, t2 - t1)
            a = p1 - b * t1
            lines[scen] = [str(a), str(b)]
    params = {"s1": s1, "lines": lines, "training_lowest_success": {f"{k[0]}@{k[1]}": v for k, v in lows.items()}}
    h = hashlib.sha256(json.dumps(params, sort_keys=True).encode()).hexdigest()
    return params, h


def ledger(history, investigate=()):
    """Per-p states for one request (SERVE history plus INVESTIGATE passes)."""
    st = {}
    for h in list(history) + list(investigate):
        p, o = h["requested_p"], h["outcome"]
        if p in st and st[p] != o:
            st[p] = "RESULT_CONFLICT"
        else:
            st[p] = o
    low = min((p for p, o in st.items() if o == "DECIDED"), default=None)
    claim = None
    if low is not None:
        lower = range(P_MIN, low)
        if all(p in st and st[p] not in ("DECIDED", "RESULT_CONFLICT") for p in lower):
            claim = "MIN_SUCCESS_IN_DECLARED_DOMAIN"
        else:
            claim = "LOWEST_SUCCESS_OBSERVED"
    return {"states": {str(p): o for p, o in sorted(st.items())}, "lowest_success": low, "claim": claim,
            "untried_below_lowest": None if low is None else sum(1 for p in range(P_MIN, low) if p not in st)}
