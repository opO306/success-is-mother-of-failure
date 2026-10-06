"""S3 identity checks for REWRITE_PILOT_A3 plans.

S3a canonical: the plan's actual tables -> exact canonical form of G(R) = {(alpha, degree): coefficient} (alpha 0 for
the tail) plus the retardation part (num, den, dn, k, signed c, shift); compared by Fraction equality with the canonical
form computed directly from the algebra PROGRAM (separate code path from rules.build_plan). Also checks
dn = num' den - num den' exactly.
S3b sympy: expand(candidate expression - algebra expression) == 0, both expressions built from tables.
Both are identity checks of exact data; neither is a formal proof of the interpreter.
"""

from __future__ import annotations

from fractions import Fraction as Q


def _nz(P):
    return {int(d): Q(v) for d, v in P.items() if Q(v) != 0}


def canon_program(program):
    groups, tail, num, den, dn, k, c = program
    terms = {}
    for a, P in groups:
        for d, v in P.items():
            if v != 0:
                terms[(Q(a), int(d) - 1)] = -Q(v)
    for d, v in tail.items():
        if v != 0:
            terms[(Q(0), int(d) - 1)] = -Q(v)
    return {"terms": terms, "rat": (_nz(num), _nz(den), _nz(dn), int(k), -Q(c), 1)}


def canon_plan(plan):
    shift, sign = (0, 1) if plan["final_fold"] else (-1, -1)
    terms = {}

    def put(alpha, d, v):
        if v != 0:
            key = (Q(alpha), int(d) + shift)
            if key in terms:
                raise ValueError(f"duplicate term {key}")
            terms[key] = sign * Q(v)
    if plan["collect"]:
        for d, v in plan["collected"].items():
            put(0, d, v["tail"])
            for i, cv in v["exp"]:
                put(plan["alphas"][i], d, cv)
    else:
        for a, P in zip(plan["alphas"], plan["blocks"]):
            for d, v in P.items():
                put(a, d, v)
        for d, v in plan["tail"].items():
            put(0, d, v)
    s_total = plan["rat_shift"] + (0 if plan["final_fold"] else 1)
    c_total = Q(plan["c"]) * plan["rat_sign"] * (1 if plan["final_fold"] else -1)
    return {"terms": terms, "rat": (_nz(plan["num"]), _nz(plan["den"]), _nz(plan["dn"]), int(plan["k"]), c_total, s_total)}


def _pmul(a, b):
    out = {}
    for i, x in a.items():
        for j, y in b.items():
            out[i + j] = out.get(i + j, Q(0)) + x * y
    return {d: v for d, v in out.items() if v != 0}


def _pder(a):
    return {d - 1: d * v for d, v in a.items() if d}


def dn_identity(num, den, dn):
    lhs = _pmul(_pder(num), den)
    for d, v in _pmul(num, _pder(den)).items():
        lhs[d] = lhs.get(d, Q(0)) - v
    return {d: v for d, v in lhs.items() if v != 0} == _nz(dn)


def s3a(plan, program):
    a, b = canon_plan(plan), canon_program(program)
    return {"canonical_equal": a == b, "dn_identity": dn_identity(*a["rat"][:3]),
            "n_terms": len(a["terms"])}


def s3b(plan, program):
    import sympy as s
    x = s.symbols("x", positive=True)
    R = lambda v: s.Rational(Q(v).numerator, Q(v).denominator)  # noqa: E731
    poly = lambda P: sum((R(v) * x ** int(d) for d, v in P.items()), s.Integer(0))  # noqa: E731
    groups, tail, num, den, dn, k, c = program
    N, D, DN = poly(num), poly(den), poly(dn)
    alg = -(poly(tail) + sum((s.exp(-R(a) * x) * poly(P) for a, P in groups), s.Integer(0))
            + R(c) * (2 * k * N / D * x ** -(2 * k + 1) - DN / D ** 2 * x ** -(2 * k))) / x
    if plan["collect"]:
        body = sum((x ** int(d) * (R(v["tail"]) + sum((R(cv) * s.exp(-R(plan["alphas"][i]) * x) for i, cv in v["exp"]),
                                                       s.Integer(0)))
                    for d, v in plan["collected"].items()), s.Integer(0))
    else:
        body = poly(plan["tail"]) + sum((s.exp(-R(a) * x) * poly(P) for a, P in zip(plan["alphas"], plan["blocks"])),
                                        s.Integer(0))
    Np, Dp, DNp = poly(plan["num"]), poly(plan["den"]), poly(plan["dn"])
    kk, sh = plan["k"], plan["rat_shift"]
    rat = R(plan["c"]) * plan["rat_sign"] * (2 * kk * Np / Dp * x ** -(2 * kk + 1 + sh) - DNp / Dp ** 2 * x ** -(2 * kk + sh))
    cand = body + rat if plan["final_fold"] else -(body + rat) / x
    diff = s.expand(cand - alg)
    if diff != 0:
        diff = s.simplify(s.together(diff))
    return {"sympy_zero": diff == 0}
