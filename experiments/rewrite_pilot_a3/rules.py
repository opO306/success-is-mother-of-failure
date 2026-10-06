"""REWRITE_PILOT_A3 rule catalogue and candidate generator.

A candidate is a PLAN: pure data (exact Fractions, small ints, flags) derived from the algebra PROGRAM
(groups, tail, num, den, dn, k, c) by a set of exact rewrite rules. The fixed interpreter rwforce.py evaluates a plan;
no source code is generated.

G(R^2) = -(1/R) * [ tail(R) + sum_i e^(-a_i R) P_i(R) + c * (2k g R^-(2k+1) - g' R^-(2k)) ],  g = num/den,
g' = dn/den^2 (dn = num' den - num den').
"""

from __future__ import annotations

import itertools
from fractions import Fraction as Q

RULES = {
    "R1": "ZERO_FOLD: drop exact-zero coefficients; gap-aware Horner with shared power tables",
    "R2": "RECIP_POWER_REUSE: 1/den once; inv^(2k) shared; c*((2k g inv - dg) * inv^(2k))",
    "R3": "COLLECT_BY_POWER: sum_d x^d (sum_i c_id e_i + t_d); requires R1",
    "R4": "REVERSE_HORNER: each block as one Horner in 1/R times R^dmax",
    "R5": "FOLD_FINAL_INV: push -1/R into all coefficients (degree shift -1, sign flip)",
}
R6_PREDICATE = "sqrt(x) < y -> x < y^2 only for y >= 0 proven; no site in the force block (value needed)"
MAX_RULES = 4
MAX_OPS = 400


def candidates():
    """Every subset of R1..R5 with at most MAX_RULES rules, excluding R3 without R1; fixed order."""
    out = []
    for n in range(MAX_RULES + 1):
        for s in itertools.combinations(sorted(RULES), n):
            if "R3" in s and "R1" not in s:
                continue
            out.append(s)
    return out


def ev_id(rules):
    return "rw:" + ("+".join(rules) if rules else "R0")


def parse_ev(ev):
    body = ev.split(":", 1)[1]
    rules = () if body == "R0" else tuple(body.split("+"))
    if any(r not in RULES for r in rules) or list(rules) != sorted(set(rules)):
        raise ValueError(ev)
    return rules


def check_premises(program):
    groups, tail, num, den, dn, k, c = program
    if not all(isinstance(v, Q) for P in [tail, num, den, dn] + [P for _, P in groups] for v in P.values()):
        raise ValueError("coefficients must be exact Fractions")
    if not all(isinstance(a, Q) and a > 0 for a, _ in groups):
        raise ValueError("exponents must be positive exact Fractions")
    if den.get(0) != 1 or not all(v > 0 for d, v in den.items() if d > 0):
        raise ValueError("den(R) = 1 + sum RET_B R^(m+1) with every RET_B > 0 is required (den > 0 for R > 0)")


def build_plan(program, rules):
    """The plan of a rule set. rules: sorted tuple of rule ids."""
    rules = tuple(rules)
    if "R3" in rules and "R1" not in rules:
        raise ValueError("R3 requires R1")
    if len(rules) > MAX_RULES or any(r not in RULES for r in rules):
        raise ValueError(rules)
    check_premises(program)
    groups, tail, num, den, dn, k, c = program
    fold = "R1" in rules
    final_fold = "R5" in rules

    def shape(P):
        P = {int(d): Q(v) for d, v in P.items()}
        if final_fold:                                  # -(1/R) * sum c_d R^d = sum (-c_d) R^(d-1)
            P = {d - 1: -v for d, v in P.items()}
        if fold:
            P = {d: v for d, v in P.items() if v != 0}
        return P

    plan = {"rules": list(rules), "alphas": [Q(a) for a, _ in groups], "fold": fold, "recip": "R2" in rules,
            "collect": "R3" in rules, "mode": "inv" if "R4" in rules else "split", "final_fold": final_fold,
            "blocks": [shape(P) for _, P in groups], "tail": shape(tail),
            "num": {int(d): Q(v) for d, v in num.items()}, "den": {int(d): Q(v) for d, v in den.items()},
            "dn": {int(d): Q(v) for d, v in dn.items()}, "k": int(k), "c": Q(c),
            # retardation term: rat_sign * c * (2k g R^-(2k+1+s) - g' R^-(2k+s)), s = rat_shift
            "rat_sign": -1 if final_fold else 1, "rat_shift": 1 if final_fold else 0}
    if fold:
        for key in ("num", "den", "dn"):
            plan[key] = {d: v for d, v in plan[key].items() if v != 0}
    if plan["collect"]:
        degs = sorted({d for P in plan["blocks"] for d in P} | set(plan["tail"]))
        plan["collected"] = {d: {"tail": plan["tail"].get(d, Q(0)),
                                 "exp": [(i, P[d]) for i, P in enumerate(plan["blocks"]) if d in P]} for d in degs}
    n = op_count(plan)
    if n > MAX_OPS:
        raise ValueError(f"plan too large: {n} ops")
    plan["ops"] = n
    return plan


def _horner_ops(P, fold, mode):
    """Interval ops (mul, add) of one Laurent block as the interpreter evaluates it."""
    if not P:
        return 1 if not fold else 0
    if mode == "inv":
        dmax = max(0, max(P))
        es = sorted({dmax - d for d in P})
        n = (2 * (es[-1] + 1)) if not fold else (2 * (len(es) - 1) + (1 if es[0] > 0 else 0))
        return n + (1 if dmax > 0 else 0)
    pos = [d for d in P if d >= 0]
    neg = [-d for d in P if d < 0]
    if not fold:
        return 2 * ((max(pos) + 1) if pos else 0) + 2 * (max(neg) if neg else 0) + (2 if neg else 0)
    n = 0
    for part in (pos, neg):
        if part:
            part = sorted(part)
            n += 2 * (len(part) - 1) + (1 if part[0] > 0 else 0)
    return n + (1 if pos and neg else 0)


def op_count(plan):
    """Static count of interval operations per force call (excluding power-table builds, counted separately)."""
    fold, mode = plan["fold"], plan["mode"]
    n = 2                                               # sqrt, 1/r
    n += 3 * len(plan["alphas"])                        # -a*r, exp, (and one of: e*P or e*c in collect)
    if plan["collect"]:
        n += sum(2 * len(v["exp"]) + (1 if v["tail"] != 0 else 0) for v in plan["collected"].values())
        n += _horner_ops({d: 1 for d in plan["collected"]}, True, mode)
    else:
        n += sum(_horner_ops(P, fold, mode) + 1 for P in plan["blocks"]) + _horner_ops(plan["tail"], fold, mode)
    n += sum(_horner_ops(plan[x], fold, mode) for x in ("num", "den", "dn"))
    n += 9 if not plan["recip"] else 8                  # retardation term
    n += 0 if plan["final_fold"] else 2                 # -out * inv
    return n


def sqrt_lt(x_lo, x_hi, y_lo, y_hi):
    """R6 reference (catalogue only, no site in the force block): decide sqrt(x) < y for every x in [x_lo, x_hi],
    y in [y_lo, y_hi] (exact Fractions, x_lo >= 0) via x < y^2. True/False when proven, None = refuse. The rewrite
    is valid only where y >= 0 is proven; strictness is kept (x == y^2 is not 'less')."""
    if x_lo < 0:
        return None                                     # sqrt domain duty
    if y_lo < 0:
        return False if y_hi < 0 else None              # y < 0: sqrt(x) >= 0 > y; y crossing 0: refuse
    if x_hi < y_lo * y_lo:
        return True
    if x_lo >= y_hi * y_hi:
        return False
    return None


def plan_to_json(plan):
    def enc(v):
        if isinstance(v, Q):
            return str(v)
        if isinstance(v, dict):
            return {str(k): enc(x) for k, x in v.items()}
        if isinstance(v, (list, tuple)):
            return [enc(x) for x in v]
        return v
    return enc(plan)
