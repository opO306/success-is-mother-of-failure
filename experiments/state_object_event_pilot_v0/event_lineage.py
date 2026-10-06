"""PART B: inherited interaction-event lineage on Exact Expression V1 A2_bound (survey only).

World: V1's UNROUNDED KDK exact-real map (dt = 40, h = 20, Ar40 mass of C1-B1, Lang 2024 with retardation). The FX
projection is a measurement and is never fed back. Same operation sequence as exact_expression_gate_v1/stream.py.

Representation of every state component (an ENCLOSURE, never a state):
    x  in  { c + sum_t k_t * eps_t + rho :  |rho| <= r }
c and every k_t are working-precision binary numbers (mpmath.libmp raw mpf, round to nearest); r is an upper bound.
The rounding error of every nearest-rounded result s is bounded by 2^(1-prec) |s| and added to r (rounded up).
eps_t in [-1, 1] is ONE fixed unknown number per tag t.

Tags are created ONLY by an InteractionEvent (one per force evaluation):
    G tag   : all new uncertainty of G(r^2) (G(s0) enclosure width, mean-value remainder, |alpha| * r(r^2), rounding)
    J_k tag : all remaining uncertainty of the impulse component J_k = 20 G d_k (inherited remainders included)
Atom j receives +J and atom i -J with the SAME tags. J has no remainder after the event.

G(s) for s in [a, b] (domain-proven): G(s) = G(s0) + alpha (s - s0) + e, |e| <= max|G'([a, b]) - alpha| max|s - s0|,
with G'([a, b]) the hull of the derivative certificate cells covering [sqrt(a), sqrt(b)] and G(s0) from the V0
lang_iv transcription (shared TCB with the baseline). Outside the certificate: EventDerivativeDomainUnsupported.

Worker: python -m experiments.state_object_event_pilot_v0.event_lineage --path {baseline,candidate}
            --prec 96 --last 100 --want 10,100 --cert FILE --out FILE
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
import time
from fractions import Fraction as Q
from pathlib import Path

from mpmath import iv
from mpmath.libmp import (from_int, from_rational, fzero, mpf_abs, mpf_add, mpf_cmp, mpf_mul, mpf_neg, mpf_shift,
                          round_ceiling, round_floor, round_nearest, to_rational)

from exact_expression_gate_v0 import lang_iv as LI
from exact_expression_gate_v1 import common as K

from .derivative_certificate import EventDerivativeDomainUnsupported, Table

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
MAX_TAGS = 4096
Q0 = ((Q(-71, 20), Q(0), Q(0)), (Q(71, 20), Q(0), Q(0)))
P0 = ((Q(1), Q(-3), Q(0)), (Q(-1), Q(3), Q(0)))
DEFAULT_CERT = ROOT / "docs/active/state_object_event_pilot_v0/derivative_certificate.json.gz"


class LineageTagCap(Exception):
    """LINEAGE_TAG_CAP: more than MAX_TAGS tags (REFUSED)."""


class TagReuse(AssertionError):
    """A tag id was issued twice (two different errors would share one eps)."""


def rq(x):
    """Exact Fraction of a raw mpf."""
    return Q(*to_rational(x))


class Tags:
    """Globally unique, monotonically increasing tag ids within one run."""

    def __init__(self, cap=MAX_TAGS):
        self.next, self.issued, self.cap = 0, set(), cap

    def new(self):
        t = self.next
        if t in self.issued:
            raise TagReuse(t)
        self.issued.add(t)
        self.next += 1
        if len(self.issued) > self.cap:
            raise LineageTagCap(f"{len(self.issued)} tags > {self.cap}")
        return t


class Arith:
    """Working-precision operations with a rigorous bound on each rounding error."""

    def __init__(self, prec):
        self.prec = prec

    def err(self, s):                          # |s_rounded - s_exact| <= 2^(1-prec) |s_rounded| (nearest; no underflow)
        return mpf_shift(mpf_abs(s), 1 - self.prec)

    def up(self, *xs):                         # sum of non-negative terms, rounded up
        acc = fzero
        for x in xs:
            acc = mpf_add(acc, x, self.prec, round_ceiling)
        return acc

    def mul_up(self, a, b):
        return mpf_mul(mpf_abs(a), mpf_abs(b), self.prec, round_ceiling)


class Form:
    __slots__ = ("c", "k", "r")

    def __init__(self, c, k=None, r=fzero):
        self.c, self.k, self.r = c, (k if k is not None else {}), r

    def is_zero(self):
        return self.c == fzero and not self.k and self.r == fzero


def total_radius(A, x):
    acc = x.r
    for v in x.k.values():
        acc = mpf_add(acc, mpf_abs(v), A.prec, round_ceiling)
    return acc


def const_form(A, value: Q):
    c = from_rational(value.numerator, value.denominator, A.prec, round_nearest)
    d = abs(value - rq(c))
    r = from_rational(d.numerator, d.denominator, A.prec, round_ceiling) if d else fzero
    return Form(c, {}, r)


def add(A, x, y, sign=1):
    p = A.prec
    yc = y.c if sign > 0 else mpf_neg(y.c)
    c = mpf_add(x.c, yc, p, round_nearest)
    errs = [x.r, y.r, A.err(c)]
    k = dict(x.k)
    for t, v in y.k.items():
        v = v if sign > 0 else mpf_neg(v)
        if t in k:
            s = mpf_add(k[t], v, p, round_nearest)
            errs.append(A.err(s))
            if s == fzero:                     # exact cancellation (a nearest-rounded sum is 0 only if exact)
                del k[t]
            else:
                k[t] = s
        else:
            k[t] = v
    return Form(c, k, A.up(*errs))


def scale(A, x, a, arad=fzero):
    """x * (a +- arad), a a working-precision number, arad >= 0."""
    p = A.prec
    c = mpf_mul(x.c, a, p, round_nearest)
    errs = [A.mul_up(a, x.r), A.err(c)]
    k = {}
    for t, v in x.k.items():
        s = mpf_mul(v, a, p, round_nearest)
        errs.append(A.err(s))
        k[t] = s
    if arad != fzero:
        errs.append(mpf_mul(arad, mpf_add(mpf_abs(x.c), total_radius(A, x), p, round_ceiling), p, round_ceiling))
    return Form(c, k, A.up(*errs))


def mul(A, x, y):
    """Linear part exact up to rounding; nonlinear part bounded by Tx * Ty, |x.c| r_y + |y.c| r_x."""
    p = A.prec
    c = mpf_mul(x.c, y.c, p, round_nearest)
    errs = [A.err(c), A.mul_up(x.c, y.r), A.mul_up(y.c, x.r)]
    tx, ty = total_radius(A, x), total_radius(A, y)
    errs.append(mpf_mul(tx, ty, p, round_ceiling))
    k = {}
    for t in set(x.k) | set(y.k):
        parts = []
        if t in y.k:
            parts.append(mpf_mul(x.c, y.k[t], p, round_nearest))
        if t in x.k:
            parts.append(mpf_mul(y.c, x.k[t], p, round_nearest))
        for q in parts:
            errs.append(A.err(q))
        s = parts[0] if len(parts) == 1 else mpf_add(parts[0], parts[1], p, round_nearest)
        if len(parts) == 2:
            errs.append(A.err(s))
        if s != fzero:
            k[t] = s
    return Form(c, k, A.up(*errs))


def form_range(A, x):
    """Outward [lo, hi] as exact Fractions."""
    T = total_radius(A, x)
    lo = mpf_add(x.c, mpf_neg(T), A.prec, round_floor)
    hi = mpf_add(x.c, T, A.prec, round_ceiling)
    return rq(lo), rq(hi)


def domain(lo: Q, hi: Q):
    """V1 rule on an enclosure [lo, hi] of R^2: R >= r_min is inside."""
    if lo >= K.R_MIN2:
        return K.PROVEN
    if hi < K.R_MIN2:
        return K.VIOLATED
    return K.UNPROVEN


def _iv_point(x):
    return LI.c(rq(x))


def _mid_and_rad(A, lo_raw, hi_raw):
    mid = mpf_shift(mpf_add(lo_raw, hi_raw, A.prec, round_nearest), -1)
    rad = A.up(mpf_add(hi_raw, mpf_neg(mid), A.prec, round_ceiling), A.err(mid))
    rad2 = mpf_add(mid, mpf_neg(lo_raw), A.prec, round_ceiling)
    if mpf_cmp(rad2, rad) > 0:
        rad = A.up(rad2, A.err(mid))
    return mid, rad


class Event:
    """One InteractionEvent: impulse forms (+J on atom j, -J on atom i) sharing the same tags."""
    __slots__ = ("J", "tags", "cells")

    def __init__(self, J, tags, cells):
        self.J, self.tags, self.cells = J, tags, cells


def interact(A, tags, table, qi, qj, step, h=Q(20)):
    d = [add(A, qj[k], qi[k], -1) for k in range(3)]
    r2 = add(A, add(A, mul(A, d[0], d[0]), mul(A, d[1], d[1])), mul(A, d[2], d[2]))
    a, b = form_range(A, r2)
    st = domain(a, b)
    if st != K.PROVEN:
        raise K.DomainStop(st, step)
    gp_lo, gp_hi, cells = table.gprime_hull(a, b)
    s0 = r2.c                                                     # inside [a, b]
    alpha_q = (gp_lo + gp_hi) / 2
    alpha = from_rational(alpha_q.numerator, alpha_q.denominator, A.prec, round_nearest)
    al = rq(alpha)
    s0q = rq(s0)
    e = max(abs(gp_lo - al), abs(gp_hi - al)) * max(b - s0q, s0q - a)  # mean-value remainder, exact
    e_up = from_rational(e.numerator, e.denominator, A.prec, round_ceiling) if e else fzero
    g = LI.G_of_R2(_iv_point(s0))
    g0, grad = _mid_and_rad(A, g._mpi_[0], g._mpi_[1])
    Gk, errs = {}, [grad, e_up, A.mul_up(alpha, r2.r)]
    for t, v in r2.k.items():                                      # alpha * (r2 - s0): center is exactly 0
        s = mpf_mul(alpha, v, A.prec, round_nearest)
        errs.append(A.err(s))
        if s != fzero:
            Gk[t] = s
    new = []
    coef = A.up(*errs)
    if coef != fzero:
        tg = tags.new()
        new.append(tg)
        Gk[tg] = coef
    G = Form(g0, Gk, fzero)
    hq = from_int(int(h))
    J = []
    for k in range(3):
        if d[k].is_zero():
            J.append(Form(fzero))
            continue
        Pk = scale(A, mul(A, G, d[k]), hq)
        if Pk.r != fzero:                                          # all remaining uncertainty of J_k -> its own tag
            tj = tags.new()
            new.append(tj)
            Pk.k[tj] = Pk.r
        J.append(Form(Pk.c, Pk.k, fzero))
    return Event(J, new, cells)


class Lineage:
    """Candidate stream over one precision: KDK in the order of exact_expression_gate_v1/stream.py."""

    def __init__(self, prec, table, tags=None):
        iv.prec = prec
        self.A = Arith(prec)
        self.table = table
        self.tags = tags or Tags()
        self.q = [[const_form(self.A, x) for x in r] for r in Q0]
        self.p = [[const_form(self.A, x) for x in r] for r in P0]
        cdt = K.CDT
        self.cdt = const_form(self.A, cdt)                          # point + radius
        self.steps = 0
        self.F = interact(self.A, self.tags, self.table, self.q[0], self.q[1], 0)

    def _kick(self):
        A, J = self.A, self.F.J
        self.p[1] = [add(A, self.p[1][k], J[k]) for k in range(3)]
        self.p[0] = [add(A, self.p[0][k], J[k], -1) for k in range(3)]

    def step(self):
        A = self.A
        self._kick()
        for a in range(2):
            self.q[a] = [add(A, self.q[a][k], scale(A, self.p[a][k], self.cdt.c, self.cdt.r)) for k in range(3)]
        self.F = interact(A, self.tags, self.table, self.q[0], self.q[1], self.steps + 1)
        self._kick()
        self.steps += 1

    def components(self):
        return [x for r in self.q for x in r], [x for r in self.p for x in r]

    def ranges(self):
        qs, ps = self.components()
        return [form_range(self.A, x) for x in qs], [form_range(self.A, x) for x in ps]


def cell_of(lo: Q, hi: Q, f):
    a, b = K.rhe(lo * (1 << f)), K.rhe(hi * (1 << f))
    if a != b:
        return None
    if not K.RAW_LO <= a < K.RAW_HI:
        raise K.OutOfRange(a)
    return a


def measure(qr, pr):
    """Cells (or None), worst normalized radii for positions (/2^-48) and momenta (/2^-80)."""
    cells = [cell_of(lo, hi, K.POS_F) for lo, hi in qr] + [cell_of(lo, hi, K.MOM_F) for lo, hi in pr]
    wq = max((hi - lo) / 2 * (1 << K.POS_F) for lo, hi in qr)
    wp = max((hi - lo) / 2 * (1 << K.MOM_F) for lo, hi in pr)
    return (None if any(c is None for c in cells) else cells), wq, wp


def run_candidate(prec, last, want, table):
    out = {"read": {}, "stop": None, "stop_step": None, "completed_steps": 0}
    try:
        L = Lineage(prec, table)
        for s in range(1, last + 1):
            L.step()
            out["completed_steps"] = s
            if s in want:
                qr, pr = L.ranges()
                cells, wq, wp = measure(qr, pr)
                qs, ps = L.components()
                out["read"][str(s)] = {
                    "cells": cells, "norm_radius_pos": float(wq), "norm_radius_mom": float(wp),
                    "norm_radius_pos_exact": str(wq), "norm_radius_mom_exact": str(wp),
                    "tags": len(L.tags.issued),
                    "max_remainder": float(max(rq(x.r) for x in qs + ps)),
                    "max_coefficients_per_component": max(len(x.k) for x in qs + ps),
                    "ranges": [[str(lo), str(hi)] for lo, hi in qr + pr]}
    except K.DomainStop as e:
        out["stop"], out["stop_step"] = e.kind, e.where
    except EventDerivativeDomainUnsupported as e:
        out["stop"], out["stop_step"] = "EVENT_DERIVATIVE_DOMAIN_UNSUPPORTED", out["completed_steps"] + 1
        out["stop_detail"] = str(e)
    except LineageTagCap as e:
        out["stop"], out["stop_step"] = "LINEAGE_TAG_CAP", out["completed_steps"] + 1
        out["stop_detail"] = str(e)
    except K.OutOfRange:
        out["stop"], out["stop_step"] = K.OUT_OF_RANGE, out["completed_steps"]
    return out


def _endpoints_from_key(key):
    """Exact endpoints from V1's endpoints_key text (repr of mpi raw tuples)."""
    out = []
    for part in key.split("|"):
        if part.startswith("Q"):
            n, d = part[1:].split("/")
            v = Q(int(n), int(d))
            out.append((v, v))
        else:
            lo, hi = ast.literal_eval(part)
            out.append((rq(lo), rq(hi)))
    return out


def run_baseline(prec, last, want):
    from exact_expression_gate_v1 import stream
    q0 = [list(r) for r in Q0]
    p0 = [list(r) for r in P0]
    t = (time.process_time(), time.perf_counter())
    r = stream.run(q0, p0, prec, last, set(want), exact=False)
    cost = {"cpu_s": time.process_time() - t[0], "wall_s": time.perf_counter() - t[1]}
    read = {}
    for s, (cells, key) in r["read"].items():
        ends = _endpoints_from_key(key)
        qr, pr = ends[:6], ends[6:]
        _, wq, wp = measure(qr, pr)
        read[str(s)] = {"cells": cells, "norm_radius_pos": float(wq), "norm_radius_mom": float(wp),
                        "norm_radius_pos_exact": str(wq), "norm_radius_mom_exact": str(wp),
                        "ranges": [[str(lo), str(hi)] for lo, hi in qr + pr]}
    return {"read": read, "stop": r["stop"], "stop_step": r["stop_step"], "completed_steps": r["completed_steps"]}, cost


def peak_rss():
    import psutil
    mi = psutil.Process().memory_info()
    return getattr(mi, "peak_wset", None) or mi.rss


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--path", required=True, choices=["baseline", "candidate"])
    ap.add_argument("--prec", type=int, required=True)
    ap.add_argument("--last", type=int, required=True)
    ap.add_argument("--want", required=True)
    ap.add_argument("--cert", default=str(DEFAULT_CERT))
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    want = sorted(int(x) for x in a.want.split(","))
    doc = {"path": a.path, "prec": a.prec, "last": a.last, "want": want, "python": sys.version}
    if a.path == "baseline":
        res, cost = run_baseline(a.prec, a.last, want)
    else:
        table = Table(a.cert)
        doc["certificate_sha256"] = table.sha256
        t = (time.process_time(), time.perf_counter())
        res = run_candidate(a.prec, a.last, set(want), table)
        cost = {"cpu_s": time.process_time() - t[0], "wall_s": time.perf_counter() - t[1]}
    doc.update(res)
    doc.update(cost)
    doc["peak_rss"] = peak_rss()
    Path(a.out).write_text(json.dumps(doc, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
