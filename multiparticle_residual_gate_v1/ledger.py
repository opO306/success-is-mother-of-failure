"""Residual / carry candidates U and L (executor side). Exact rational arithmetic.

A step is a list of entries:
  ("pair", i, j, delta)   j += delta, i -= delta (same exact delta)
  ("ext", i, delta, name) i += delta, external ledger[name] -= delta
State: P (list of int, coarse units), r (list of Fraction), ext (dict name -> Fraction).
Authoritative momentum p_i = P_i + r_i.
"""

from __future__ import annotations

from fractions import Fraction as Q


def rhe(x) -> int:
    x = Q(x)
    n, d = x.numerator, x.denominator
    sign = -1 if n < 0 else 1
    q, rem = divmod(abs(n), d)
    if 2 * rem > d or (2 * rem == d and q & 1):
        q += 1
    return sign * q


class State:
    def __init__(self, p0):
        self.P = [rhe(x) for x in p0]
        self.r = [Q(x) - P for x, P in zip(p0, self.P)]
        self.ext = {}

    def p(self):
        return [Q(P) + r for P, r in zip(self.P, self.r)]

    def copy(self):
        s = State.__new__(State)
        s.P, s.r, s.ext = list(self.P), list(self.r), dict(self.ext)
        return s


def _carry(s: State, i: int):
    while s.r[i] >= 1:
        s.P[i] += 1
        s.r[i] -= 1
    while s.r[i] <= -1:
        s.P[i] -= 1
        s.r[i] += 1


def _deltas(entries):
    for e in entries:
        if e[0] == "pair":
            _, i, j, d = e
            yield j, Q(d)
            yield i, -Q(d)
        else:
            _, i, d, _name = e
            yield i, Q(d)


def apply_U(s: State, entries) -> State:
    """Designer: each contribution goes into r immediately, carry whole units to P."""
    for e in entries:
        if e[0] == "pair":
            _, i, j, d = e
            for k, v in ((j, Q(d)), (i, -Q(d))):
                s.r[k] += v
                _carry(s, k)
        else:
            _, i, d, name = e
            s.r[i] += Q(d)
            _carry(s, i)
            s.ext[name] = s.ext.get(name, Q(0)) - Q(d)
    return s


def apply_L(s: State, entries, grouping: str = "forward") -> State:
    """Reviewer: exact net per atom first, then normalize once (nearest)."""
    n = len(s.P)
    contrib = [[] for _ in range(n)]
    for k, v in _deltas(entries):
        contrib[k].append(v)
    for e in entries:
        if e[0] == "ext":
            _, i, d, name = e
            s.ext[name] = s.ext.get(name, Q(0)) - Q(d)
    for k in range(n):
        c = contrib[k]
        if grouping == "reverse":
            c = c[::-1]
        if grouping == "tree":
            while len(c) > 1:
                c = [c[a] + c[a + 1] if a + 1 < len(c) else c[a] for a in range(0, len(c), 2)]
            net = c[0] if c else Q(0)
        else:
            net = sum(c, Q(0))
        p = Q(s.P[k]) + s.r[k] + net
        s.P[k] = rhe(p)
        s.r[k] = p - s.P[k]
    return s


def drift_grid(x, s: State, c, P_only=False):
    """C1-B1 v2 meaning: x += round(p c); x on the integer position grid."""
    return [xi + rhe((Q(P) if P_only else Q(P) + r) * c) for xi, P, r in zip(x, s.P, s.r)]


def drift_exact(x, s: State, c, P_only=False):
    return [xi + (Q(P) if P_only else Q(P) + r) * c for xi, P, r in zip(x, s.P, s.r)]
