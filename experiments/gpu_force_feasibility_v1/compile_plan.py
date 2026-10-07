"""G0 program compiler (GPU host side; protocol 'gpu_design.program').

Records the per-call operation sequence of the frozen RwForce.__call__ (rw:R1+R2) by running it once with symbolic
values. rwforce.iv and rwforce._pos are replaced in memory during the trace only and restored afterwards; no file is
changed. Every interval constant the frozen object lifted at construction (iv.prec = p) is taken over exactly.

The result is a straight-line program over interval values:
    op = (code, dst, a, b)   operands >= 0 are registers, operands < 0 are constants (-1 - index)
    codes: ADD SUB MUL DIV NEG SQRT EXP REQPOS(obligation number in b) OUT
register 0 holds the input R^2. A liveness pass re-uses registers.
`replay` evaluates a program with mpmath interval operations (host check that the trace equals RwForce).
"""

from __future__ import annotations

import math

from mpmath import iv
from mpmath.libmp import mpi_add, mpi_div, mpi_exp, mpi_mul, mpi_neg, mpi_sqrt, mpi_sub, mpf_sign

OPS = {"ADD": 0, "SUB": 1, "MUL": 2, "DIV": 3, "NEG": 4, "SQRT": 5, "EXP": 6, "REQPOS": 7, "OUT": 8}
EV = "rw:R1+R2"


class _Trace:
    def __init__(self):
        self.ops, self.consts, self.cidx, self.nvals, self.nobl = [], [], {}, 1, 0

    def const(self, raw):
        k = self.cidx.get(raw)
        if k is None:
            k = self.cidx[raw] = len(self.consts)
            self.consts.append(raw)
        return _Node(self, -1 - k)

    def emit(self, code, a, b=0):
        v = self.nvals
        self.nvals += 1
        self.ops.append([code, v, a, b])
        return _Node(self, v)


class _Node:
    __slots__ = ("tr", "v")

    def __init__(self, tr, v):
        self.tr, self.v = tr, v

    def _o(self, x):
        if isinstance(x, _Node):
            return x.v
        if isinstance(x, int):
            return self.tr.const(iv.mpf(x)._mpi_).v            # mpmath converts a Python int at iv.prec
        raise TypeError(f"untraced operand {type(x)}")

    def __add__(self, x): return self.tr.emit("ADD", self.v, self._o(x))
    def __radd__(self, x): return self.tr.emit("ADD", self._o(x), self.v)
    def __sub__(self, x): return self.tr.emit("SUB", self.v, self._o(x))
    def __rsub__(self, x): return self.tr.emit("SUB", self._o(x), self.v)
    def __mul__(self, x): return self.tr.emit("MUL", self.v, self._o(x))
    def __rmul__(self, x): return self.tr.emit("MUL", self._o(x), self.v)
    def __truediv__(self, x): return self.tr.emit("DIV", self.v, self._o(x))
    def __rtruediv__(self, x): return self.tr.emit("DIV", self._o(x), self.v)
    def __neg__(self): return self.tr.emit("NEG", self.v)


def _wrap(tr, x):
    """Replace every lifted ivmpf constant inside the frozen object's specs by a traced constant."""
    if isinstance(x, iv.mpf):
        return tr.const(x._mpi_)
    if isinstance(x, tuple):
        return tuple(_wrap(tr, y) for y in x)
    if isinstance(x, list):
        return [_wrap(tr, y) for y in x]
    if isinstance(x, dict):
        return {k: _wrap(tr, y) for k, y in x.items()}
    return x


def trace(p):
    from experiments.rewrite_pilot_a3 import adapter as AD
    from experiments.rewrite_pilot_a3 import rwforce as RW
    AD.prepare(EV)
    iv.prec = p
    force = RW.RwForce(AD._PLAN)                       # a fresh in-memory object, constructed as the E2 worker does
    tr = _Trace()
    for name in ("zero", "alphas", "blocks", "tail", "num", "den", "dn", "c"):
        if hasattr(force, name):
            setattr(force, name, _wrap(tr, getattr(force, name)))
    if force.collect:
        raise NotImplementedError("collect plans are not part of rw:R1+R2")

    def pos(x):
        tr.ops.append(["REQPOS", -1, x.v, tr.nobl])
        tr.nobl += 1
        return True

    class _IV:
        @staticmethod
        def sqrt(x): return tr.emit("SQRT", x.v)

        @staticmethod
        def exp(x): return tr.emit("EXP", x.v)

    saved = (RW.iv, RW._pos)
    RW.iv, RW._pos = _IV, pos
    try:
        out = force(_Node(tr, 0))
    finally:
        RW.iv, RW._pos = saved
    tr.ops.append(["OUT", -1, out.v, 0])
    return {"p": p, "ops": tr.ops, "consts": tr.consts, "n_values": tr.nvals, "n_obligations": tr.nobl}


def allocate(prog):
    """Liveness-based register re-use (values -> registers). Value 0 (input) is register 0."""
    ops = prog["ops"]
    last = {}
    for i, (code, dst, a, b) in enumerate(ops):
        for x in ((a, b) if code in ("ADD", "SUB", "MUL", "DIV") else (a,)):
            if x >= 0:
                last[x] = i
    reg, free, nreg = {0: 0}, [], 1
    out = []
    for i, (code, dst, a, b) in enumerate(ops):
        ra = reg[a] if a >= 0 else a
        rb = (reg[b] if b >= 0 else b) if code in ("ADD", "SUB", "MUL", "DIV") else b
        for x in ((a, b) if code in ("ADD", "SUB", "MUL", "DIV") else (a,)):
            if x >= 0 and last.get(x) == i and x in reg:
                free.append(reg.pop(x))
        rd = -1
        if dst >= 0:
            if free:
                rd = free.pop()
            else:
                rd, nreg = nreg, nreg + 1
            reg[dst] = rd
        out.append([OPS[code], rd, ra, rb])
    return {**prog, "code": out, "n_regs": nreg}


def replay(prog, r2_raw):
    """Evaluate a traced program with mpmath interval operations at prog['p'] (host check)."""
    p, consts = prog["p"], prog["consts"]
    vals = {0: r2_raw}
    get = lambda x: vals[x] if x >= 0 else consts[-1 - x]          # noqa: E731
    for code, dst, a, b in prog["ops"]:
        if code == "REQPOS":
            if not mpf_sign(get(a)[0]) > 0:
                return "DOMAIN_UNPROVEN", b
            continue
        if code == "OUT":
            return "OK", get(a)
        f = {"ADD": mpi_add, "SUB": mpi_sub, "MUL": mpi_mul, "DIV": mpi_div}.get(code)
        if f:
            vals[dst] = f(get(a), get(b), p)
        else:
            vals[dst] = {"NEG": mpi_neg, "SQRT": mpi_sqrt, "EXP": mpi_exp}[code](get(a), p)
    raise RuntimeError("program without OUT")


def exp_tables(p, mags=range(2, 25)):
    """Host constants of mpf_exp at precision p: wp, r = int(wp ** 0.5) and ln2_fixed(wp + mag)."""
    from mpmath.libmp.libelefun import ln2_fixed
    wp = p + 14
    return {"wp": wp, "r": int(wp ** 0.5), "isqrt_check": math.isqrt(wp),
            "ln2": {m: int(ln2_fixed(wp + m)) for m in mags}}
