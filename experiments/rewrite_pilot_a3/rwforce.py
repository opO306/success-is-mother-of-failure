"""Fixed interval interpreter for REWRITE_PILOT_A3 plans (rules.py). Evaluates G(R^2) with mpmath iv at the current
working precision. The empty plan (rw:R0) performs exactly the algebra force's operations in the same order.

Domain duties are kept explicitly: an R^2 enclosure whose lower end is not > 0 is refused (DomainStop UNPROVEN) even
when every inverse-power term has been folded away; with R2 a den enclosure whose lower end is not > 0 is refused.
"""

from __future__ import annotations

from mpmath import iv
from mpmath.libmp import mpf_sign

import exact_expression_gate_v0.lang_iv as LI
from exact_expression_gate_v1 import common as K


def _pos(x):
    return mpf_sign(x._mpi_[0]) > 0


class _Pow:
    """Per-call power table x^g (g >= 1), built by squaring and reused."""
    __slots__ = ("x", "t")

    def __init__(self, x):
        self.x, self.t = x, {1: x}

    def __call__(self, g):
        t = self.t
        v = t.get(g)
        if v is None:
            a = self(g // 2)
            v = a * a if g % 2 == 0 else (a * a) * self.x
            t[g] = v
        return v


def _dense_split(P, lift):
    pos_top = max([d for d in P if d >= 0], default=-1)
    neg_top = max([-d for d in P if d < 0], default=0)
    return ("dense_split", tuple(lift(P.get(i, 0)) for i in range(pos_top, -1, -1)),
            tuple(lift(P.get(-i, 0)) for i in range(neg_top, 0, -1)))


def _gap_steps(exps):
    """exps: nonnegative exponents (distinct). Returns (descending exponents, [gaps], lowest)."""
    es = sorted(exps, reverse=True)
    return es, [a - b for a, b in zip(es, es[1:])], es[-1]


def _compile(P, fold, mode, lift):
    """A block evaluator spec for a {degree: Fraction} block (constant coefficients)."""
    if not fold and mode == "split":
        return _dense_split(P, lift)
    if not P:
        return ("zero",)
    if mode == "inv":
        dmax = max(0, max(P))
        if fold:
            es, gaps, low = _gap_steps([dmax - d for d in P])
            return ("gap_inv", tuple(lift(P[dmax - e]) for e in es), tuple(gaps), low, dmax)
        emax = dmax - min(P)
        return ("dense_inv", tuple(lift(P.get(dmax - e, 0)) for e in range(emax, -1, -1)), dmax)
    pos = [d for d in P if d >= 0]
    neg = [-d for d in P if d < 0]
    ps = _gap_steps(pos) if pos else None
    ns = _gap_steps(neg) if neg else None
    return ("gap_split", None if ps is None else (tuple(lift(P[d]) for d in ps[0]), tuple(ps[1]), ps[2]),
            None if ns is None else (tuple(lift(P[-d]) for d in ns[0]), tuple(ns[1]), ns[2]))


def _gap(cs, gaps, low, xp):
    acc = cs[0]
    for g, cv in zip(gaps, cs[1:]):
        acc = acc * xp(g) + cv
    return acc * xp(low) if low > 0 else acc


def _eval(spec, r, inv, rp, ip, zero):
    kind = spec[0]
    if kind == "dense_split":
        _, pos, neg = spec
        a = zero
        for cv in pos:
            a = a * r + cv
        b = zero
        for cv in neg:
            b = b * inv + cv
        return a + b * inv if neg else a
    if kind == "zero":
        return zero
    if kind == "gap_split":
        _, ps, ns = spec
        a = None if ps is None else _gap(ps[0], ps[1], ps[2], rp)
        b = None if ns is None else _gap(ns[0], ns[1], ns[2], ip)
        return b if a is None else (a if b is None else a + b)
    if kind == "dense_inv":
        _, cs, dmax = spec
        acc = zero
        for cv in cs:
            acc = acc * inv + cv
        return acc * rp(dmax) if dmax > 0 else acc
    if kind == "gap_inv":
        _, cs, gaps, low, dmax = spec
        acc = _gap(cs, gaps, low, ip)
        return acc * rp(dmax) if dmax > 0 else acc
    raise ValueError(kind)


class RwForce:
    """G(R^2) of one plan at the current iv.prec (constants lifted at construction)."""

    def __init__(self, plan):
        lift = LI.c
        self.plan = plan
        fold, mode = plan["fold"], plan["mode"]
        self.zero = lift(0)
        self.alphas = [lift(a) for a in plan["alphas"]]
        self.collect = plan["collect"]
        if self.collect:
            degs = sorted(plan["collected"])
            self.cterms = {d: (lift(v["tail"]) if v["tail"] != 0 else None, tuple((i, lift(cv)) for i, cv in v["exp"]))
                           for d, v in plan["collected"].items()}
            if mode == "inv":
                dmax = max(0, max(degs))
                es, gaps, low = _gap_steps([dmax - d for d in degs])
                self.cplan = ("inv", [dmax - e for e in es], gaps, low, dmax)
            else:
                pos = [d for d in degs if d >= 0]
                neg = [-d for d in degs if d < 0]
                self.cplan = ("split", _gap_steps(pos) if pos else None, _gap_steps(neg) if neg else None)
        else:
            self.blocks = [_compile(P, fold, mode, lift) for P in plan["blocks"]]
            self.tail = _compile(plan["tail"], fold, mode, lift)
        self.num, self.den, self.dn = (_compile(plan[x], fold, mode, lift) for x in ("num", "den", "dn"))
        self.k, self.s = plan["k"], plan["rat_shift"]
        self.c = lift(plan["c"] * plan["rat_sign"])
        self.recip, self.final_fold = plan["recip"], plan["final_fold"]

    def _collected(self, r, inv, rp, ip, es):
        S = {}
        for d, (t, terms) in self.cterms.items():
            acc = t
            for i, cv in terms:
                v = es[i] * cv
                acc = v if acc is None else acc + v
            S[d] = acc
        cp = self.cplan
        if cp[0] == "inv":
            _, degs, gaps, low, dmax = cp
            acc = S[degs[0]]
            for g, d in zip(gaps, degs[1:]):
                acc = acc * ip(g) + S[d]
            if low > 0:
                acc = acc * ip(low)
            return acc * rp(dmax) if dmax > 0 else acc
        _, ps, ns = cp
        a = b = None
        if ps:
            es_, gaps, low = ps
            a = S[es_[0]]
            for g, d in zip(gaps, es_[1:]):
                a = a * rp(g) + S[d]
            if low > 0:
                a = a * rp(low)
        if ns:
            es_, gaps, low = ns
            b = S[-es_[0]]
            for g, d in zip(gaps, es_[1:]):
                b = b * ip(g) + S[-d]
            if low > 0:
                b = b * ip(low)
        return b if a is None else (a if b is None else a + b)

    def __call__(self, r2):
        if not _pos(r2):
            raise K.DomainStop(K.UNPROVEN, None)        # R > 0 duty kept even if inverse terms were folded away
        r = iv.sqrt(r2)
        inv = 1 / r
        rp, ip, zero = _Pow(r), _Pow(inv), self.zero
        if self.collect:
            es = [iv.exp(-a * r) for a in self.alphas]
            out = self._collected(r, inv, rp, ip, es)
        else:
            out = _eval(self.tail, r, inv, rp, ip, zero)
            for a, spec in zip(self.alphas, self.blocks):
                out = out + iv.exp(-a * r) * _eval(spec, r, inv, rp, ip, zero)
        num = _eval(self.num, r, inv, rp, ip, zero)
        den = _eval(self.den, r, inv, rp, ip, zero)
        k, s = self.k, self.s
        if self.recip:
            if not _pos(den):
                raise K.DomainStop(K.UNPROVEN, None)
            idn = 1 / den
            g = num * idn
            dg = (_eval(self.dn, r, inv, rp, ip, zero) * idn) * idn
            term = (2 * k * g * inv - dg) * ip(2 * k + s)
        else:
            g = num / den
            dg = _eval(self.dn, r, inv, rp, ip, zero) / (den * den)
            term = 2 * k * g * inv ** (2 * k + 1 + s) - dg * inv ** (2 * k + s)
        out = out + self.c * term
        return out if self.final_fold else -out * inv
