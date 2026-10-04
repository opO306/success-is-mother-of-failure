"""Forward KDK from the exact initial state: paths C / C_stream (interval) and C_stream_x (exact-rational carry).

One run = one precision, steps 1..last, reading the requested steps on the way. Path C and C_stream use this same
run; they differ only in the query policy (paths.py): C restarts from step 0 for every query, C_stream reads all
requested steps in one pass. Operation order is V0's replay, so at equal precision C and C_stream give bit-identical
enclosures.

exact=True (C_stream_x, the local-algebra candidate of the 2026-10-05 handover): a value stays an exact Fraction
while every input is exact (constants, initial state, sums and products of exact values). Anything touching the
transcendental force becomes an interval, except that an exact 0 times a finite force is exactly 0. The force's
domain obligation is always checked before that product (exactly when R^2 is exact). No other algebra.

A run never returns a partial state as the target state: it reports completed_steps and why it stopped.
"""

from __future__ import annotations

from fractions import Fraction as Q

from mpmath import iv

from . import common as K
from exact_expression_gate_v0 import lang_iv as LI


def _ops(exact):
    if not exact:
        return (lambda a, b: a + b), (lambda a, b: a - b), (lambda a, b: a * b), LI.c

    def to_iv(x):
        return LI.c(x) if isinstance(x, Q) else x

    def add(a, b):
        if isinstance(a, Q) and isinstance(b, Q):
            return a + b
        return to_iv(a) + to_iv(b)

    def sub(a, b):
        if isinstance(a, Q) and isinstance(b, Q):
            return a - b
        return to_iv(a) - to_iv(b)

    def mul(a, b):
        if (isinstance(a, Q) and a == 0) or (isinstance(b, Q) and b == 0):
            return Q(0)                       # finite x * 0 = 0 exactly; finiteness is the checked domain duty
        if isinstance(a, Q) and isinstance(b, Q):
            return a * b
        return to_iv(a) * to_iv(b)

    return add, sub, mul, (lambda x: Q(x))


def run(q0, p0, prec, last, want, exact=False):
    """KDK at one precision up to step `last`. want: set of steps to read.

    Returns {"completed_steps", "stop": None | VIOLATED | UNPROVEN | OUT_OF_RANGE, "stop_step",
             "read": {s: (cells or None, endpoints key)}, "exact_bits": max bit length of exact values (exact only)}.
    """
    iv.prec = prec
    add, sub, mul, lift = _ops(exact)
    n = len(q0)
    h, cdt = lift(K.H), lift(K.CDT)
    q = [[lift(x) for x in r] for r in q0]
    p = [[lift(x) for x in r] for r in p0]
    zero = lift(Q(0))
    pairs = [(i, j) for i in range(n) for j in range(i + 1, n)]
    exact_bits = 0

    def forces(q, step):
        F = [[zero] * 3 for _ in range(n)]
        for i, j in pairs:
            d = [sub(q[j][k], q[i][k]) for k in range(3)]
            r2 = add(add(mul(d[0], d[0]), mul(d[1], d[1])), mul(d[2], d[2]))
            st = K.domain(r2)
            if st != K.PROVEN:
                raise K.DomainStop(st, step)
            g = LI.G_of_R2(LI.c(r2) if isinstance(r2, Q) else r2)
            for k in range(3):
                t = mul(mul(h, g), d[k])
                F[j][k] = add(F[j][k], t)
                F[i][k] = sub(F[i][k], t)
        return F

    out = {"completed_steps": 0, "stop": None, "stop_step": None, "read": {}}
    try:
        F = forces(q, 0)
        for s in range(1, last + 1):
            p = [[add(p[a][k], F[a][k]) for k in range(3)] for a in range(n)]
            q = [[add(q[a][k], mul(p[a][k], cdt)) for k in range(3)] for a in range(n)]
            F = forces(q, s)
            p = [[add(p[a][k], F[a][k]) for k in range(3)] for a in range(n)]
            out["completed_steps"] = s
            if exact:
                for v in (x for r in q + p for x in r):
                    if isinstance(v, Q):
                        exact_bits = max(exact_bits, v.numerator.bit_length(), v.denominator.bit_length())
            if s in want:
                qv, pv = [x for r in q for x in r], [x for r in p for x in r]
                out["read"][s] = (K.decide(qv, pv), K.endpoints_key(qv + pv))
    except K.DomainStop as e:
        out["stop"], out["stop_step"] = e.kind, e.where
    except K.OutOfRange:                       # raised while reading step completed_steps
        out["stop"], out["stop_step"] = K.OUT_OF_RANGE, out["completed_steps"]
    if exact:
        out["exact_bits"] = exact_bits
    return out
