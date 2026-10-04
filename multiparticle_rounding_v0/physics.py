"""Physics panel: Ar clusters with the frozen C1-B1 pair impulse evaluator.

P uses c1b1_two_atom.impulse (authoritative two-atom contract) for every pair.
T and C use enclosures of the same pair impulses, summed per atom, and decide one
rounding (or REFUSED within MAX_BITS). Read-only use of a_reference.
"""

from __future__ import annotations

from fractions import Fraction as Q
from math import isqrt

import a_reference.ar2_lang2024 as L
import a_reference.c1b1_two_atom as C
from a_numeric.profiles import FixedPoint

POS, MOM = FixedPoint(96, 48), FixedPoint(96, 80)
KICK = Q(20)
START_BITS, MAX_BITS = 128, 4096
UNIT = Q(1, 1 << 80)


class Refused(Exception):
    pass


def on_grid(x: Q) -> Q:
    return POS.to_exact(POS.from_exact(x))


def unit_scaled(v, d) -> tuple:
    """Grid point d * v / |v| (integer vector v): exact rational approximation via isqrt, then one grid rounding."""
    n2 = sum(c * c for c in v)
    root = Q(isqrt(n2 << 400), 1 << 200)          # sqrt(n2) to 200 bits
    return tuple(on_grid(Q(d) * c / root) for c in v)


def rel(ri, rj):
    return tuple(b - a for a, b in zip(ri, rj))


def pair_enclosure(dr, M):
    """[lo, hi] of the exact impulse components on j, in momentum units."""
    R2 = sum((x * x for x in dr), Q(0))
    if R2 < C.R_MIN2:
        raise C.PhysicsDomainExceeded("R < r_min")
    _, dV, inv1 = C._model(R2, M, L.WORLD_RETARDATION)
    lo, hi = C._mul(C._neg(dV), inv1, M)
    out = []
    for x in dr:
        c = x * KICK
        a, b = Q(lo, 1 << M) * c, Q(hi, 1 << M) * c
        out.append((min(a, b), max(a, b)))
    return out


def law_P(pos):
    n = len(pos)
    dp = [[0, 0, 0] for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            J = C.impulse(rel(pos[i], pos[j]), KICK, MOM)
            for k in range(3):
                dp[j][k] += J[k]
                dp[i][k] -= J[k]
    return [tuple(x) for x in dp]


def atom_enclosures(pos, M, grouping="forward"):
    """Per atom, per component enclosure of the exact total impulse. grouping changes only the summation order."""
    n = len(pos)
    terms = [[[] for _ in range(3)] for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            enc = pair_enclosure(rel(pos[i], pos[j]), M)
            for k, (lo, hi) in enumerate(enc):
                terms[j][k].append((lo, hi))
                terms[i][k].append((-hi, -lo))
    out = []
    for i in range(n):
        row = []
        for k in range(3):
            t = terms[i][k]
            if grouping == "reverse":
                t = t[::-1]
            if grouping == "tree":
                while len(t) > 1:
                    t = [(t[a][0] + t[a + 1][0], t[a][1] + t[a + 1][1]) if a + 1 < len(t) else t[a]
                         for a in range(0, len(t), 2)]
                row.append(t[0] if t else (Q(0), Q(0)))
            else:
                lo = sum((x[0] for x in t), Q(0))
                hi = sum((x[1] for x in t), Q(0))
                row.append((lo, hi))
        out.append(row)
    return out


def law_T(pos, grouping="forward"):
    M = START_BITS
    while M <= MAX_BITS:
        enc = atom_enclosures(pos, M, grouping)
        vals = []
        ok = True
        for row in enc:
            r = []
            for lo, hi in row:
                a, b = MOM.from_exact(lo), MOM.from_exact(hi)
                if a != b:
                    ok = False
                r.append(a)
            vals.append(tuple(r))
        if ok:
            return vals, M, enc
        M *= 2
    raise Refused("T rounding not decided within MAX_BITS")


def law_C(pos):
    """T then label-free largest-remainder correction; rank decided on enclosures."""
    t, M, enc = law_T(pos)
    n = len(pos)
    out = [list(x) for x in t]
    for k in range(3):
        D = sum(t[i][k] for i in range(n))
        if D == 0:
            continue
        s = 1 if D > 0 else -1
        need = abs(D)
        Mk = M
        while True:
            encM = atom_enclosures(pos, Mk) if Mk != M else enc
            # e_i = t_i - a_i in units; s*e_i interval
            iv = []
            for i in range(n):
                lo, hi = encM[i][k]
                elo = t[i][k] - hi / UNIT
                ehi = t[i][k] - lo / UNIT
                iv.append((s * elo, s * ehi) if s > 0 else (s * ehi, s * elo))
            order = sorted(range(n), key=lambda i: (iv[i][0] + iv[i][1]) / 2, reverse=True)
            chosen, rest = order[:need], order[need:]
            if not rest or min(iv[i][0] for i in chosen) > max(iv[i][1] for i in rest):
                for i in chosen:
                    out[i][k] -= s
                break
            Mk *= 2
            if Mk > MAX_BITS:
                return "STOP_OR_UNDECIDED", M
    return [tuple(x) for x in out], M


def high_precision_totals(pos, M=512):
    """Midpoints of tight enclosures of the exact per-atom totals, in units u (diagnostic)."""
    enc = atom_enclosures(pos, M)
    return [tuple((lo + hi) / 2 / UNIT for lo, hi in row) for row in enc]
