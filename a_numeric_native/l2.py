"""L2 numerical structure without a potential: given test impulses J on pairs, apply +J / -J.

docs/current/A_NUMERIC_EXECUTION_STACK_V1.md 4.3. No force law is chosen here --
the impulses are INPUTS. What is tested is the structure every C0 step will
have: each pair (a, b) gives a exactly +J and b exactly -J (NEG is exact), and
each particle's new momentum, per axis, is ONE order-free SUM of its old
momentum and all its contributions.

A system is described label-free (particle indices, pair list); `program`
turns it into a VM program under a chosen particle naming and pair order, so the
same physics can be sent under different labels and orders.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from fractions import Fraction

from a_numeric import Instr

from .harness import F64, FX64, moderate_patterns, permutation

AXES = ("x", "y", "z")


@dataclass(frozen=True)
class System:
    profile: object
    p0: tuple          # p0[i][axis] raw values
    pairs: tuple       # ((a, b), ...)
    J: tuple           # J[k][axis] raw values, impulse on pair k: a gets +J, b gets -J


def negate_raw(profile, v):
    return v ^ (1 << 63) if profile is F64 else -v


def program(sys: System, names=None, order=None, swap=frozenset(), chained=False):
    """VM program for `sys`. names[i]: register label of particle i; order: pair order;
    swap: pair indices sent as (b, a) with -J (the same physics). chained=True is a DELIBERATE
    structural defect: accumulate with successive ADDs (one rounding per term) instead of one SUM."""
    P = len(sys.p0)
    names = names or [f"q{i}" for i in range(P)]
    order = order or list(range(len(sys.pairs)))
    inputs, prog = {}, []
    contrib = {i: [] for i in range(P)}
    for i in range(P):
        for ax, a in enumerate(AXES):
            inputs[f"{names[i]}_p{a}"] = sys.p0[i][ax]
    for slot, k in enumerate(order):
        a, b = sys.pairs[k]
        J = sys.J[k]
        if k in swap:
            a, b, J = b, a, tuple(negate_raw(sys.profile, v) for v in J)
        for ax, x in enumerate(AXES):
            jn = f"J{slot}_{x}"
            inputs[jn] = J[ax]
            prog.append(Instr("NEG", f"nJ{slot}_{x}", (jn,)))
            contrib[a].append((ax, jn))
            contrib[b].append((ax, f"nJ{slot}_{x}"))
    for i in range(P):
        for ax, x in enumerate(AXES):
            terms = [f"{names[i]}_p{x}"] + [r for a2, r in contrib[i] if a2 == ax]
            if chained:
                acc = terms[0]
                for n, t in enumerate(terms[1:]):
                    dst = f"{names[i]}_n{x}" if n == len(terms) - 2 else f"{names[i]}_t{x}{n}"
                    prog.append(Instr("ADD", dst, (acc, t)))
                    acc = dst
                if len(terms) == 1:
                    prog.append(Instr("SUM", f"{names[i]}_n{x}", tuple(terms)))
            else:
                prog.append(Instr("SUM", f"{names[i]}_n{x}", tuple(terms)))
    return sys.profile, inputs, prog


def new_momenta(sys: System, result: dict, names=None):
    """Per particle index, the three new-momentum register values (encoded), or None if halted."""
    if result["halt"]:
        return None
    names = names or [f"q{i}" for i in range(len(sys.p0))]
    return [tuple(result["registers"][f"{names[i]}_n{x}"] for x in AXES) for i in range(len(sys.p0))]


# ---------------------------------------------------------------------------
# Systems (deterministic)
# ---------------------------------------------------------------------------

def _ints(tag, n, bits):
    for i in range(n):
        r = int.from_bytes(hashlib.sha256(f"{tag}:{i}".encode()).digest(), "little")
        yield (r & ((1 << bits) - 1)) - (1 << (bits - 1))


def _values(profile, tag, n, p_like):
    if profile is F64:
        return moderate_patterns(tag, n, 1013, 1033) if p_like else moderate_patterns(tag, n, 985, 1030)
    return list(_ints(tag, n, 44 if p_like else 38))


def _system(profile, tag, P, pairs):
    pv = _values(profile, f"{tag}p", 3 * P, True)
    jv = _values(profile, f"{tag}j", 3 * len(pairs), False)
    return System(profile, tuple(tuple(pv[3 * i:3 * i + 3]) for i in range(P)), tuple(pairs),
                  tuple(tuple(jv[3 * k:3 * k + 3]) for k in range(len(pairs))))


def systems():
    out = []
    for profile in (F64, FX64):
        t = profile.name
        out += [_system(profile, f"{t}two{n}", 2, [(0, 1)]) for n in range(60)]
        for P in (3, 5, 8, 16):
            allp = [(a, b) for a in range(P) for b in range(a + 1, P)]
            out += [_system(profile, f"{t}all{P}_{n}", P, allp) for n in range(4)]
        sel = permutation(64 * 63 // 2, f"{t}sel")[:400]
        allp64 = [(a, b) for a in range(64) for b in range(a + 1, 64)]
        out.append(_system(profile, f"{t}sparse64", 64, [allp64[i] for i in sel]))
        # one particle carries 2049 pairs: a long order-free SUM (O6)
        out.append(_system(profile, f"{t}star", 2050, [(0, j) for j in range(1, 2050)]))
    return out


def exact_total(profile, values) -> Fraction:
    return sum((profile.to_exact(v) for v in values), Fraction(0))


def ulp_half(profile, raw) -> Fraction:
    """Half the spacing at a binary64 value (bound on one rounding)."""
    field = (raw >> 52) & 0x7FF
    return Fraction(2) ** (max(field, 1) - 1075 - 1)
