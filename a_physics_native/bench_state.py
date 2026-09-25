"""Build and run the C1-B1 state-width benchmark (designer 13th ed. item 10), and check its bits against an exact
Python model of the same operations. Benchmark only -- not a world executor.
"""
from __future__ import annotations

import pathlib
import subprocess
import tempfile
from fractions import Fraction as Q

from a_numeric_native.harness import NVCC_FLAGS, find_nvcc, find_vcvars

HERE = pathlib.Path(__file__).resolve().parent
A, B = 5485799090441, 399623831237000000         # 1/m = A/B (m in electron masses)
DT = 40
TIE_P = 4995297890462500                          # |p| raw: p dt / m exactly half a raw unit


def build(kind: str, out_dir) -> pathlib.Path:
    vcvars = find_vcvars()
    out = pathlib.Path(out_dir) / f"bench_{kind}"
    out.mkdir(parents=True, exist_ok=True)
    files = ["bench_state.hpp", "bench_state_io.hpp", "bench_mom.hpp", "bench_mom_io.hpp", "ar2_core.hpp"]
    files += ["bench_state.cu", "ar2_b2.cu"] if kind == "cuda" else ["bench_state.cpp"]
    for f in files:
        (out / f).write_bytes((HERE / f).read_bytes())
    (out / "anvm_core.hpp").write_bytes((HERE.parent / "a_numeric_native" / "anvm_core.hpp").read_bytes())
    if kind == "cuda":
        cmd = f'@"{find_nvcc()}" {NVCC_FLAGS} -Xcompiler "/fp:strict /EHsc /wd4702" bench_state.cu -o bench.exe'
    else:
        cmd = "@cl /nologo /O2 /fp:strict /EHsc /std:c++17 /W3 /wd4702 bench_state.cpp /Febench.exe"
    (out / "build.bat").write_text(f'@call "{vcvars}" >nul\r\n{cmd}\r\n', encoding="mbcs")
    r = subprocess.run(["cmd", "/c", str(out / "build.bat")], capture_output=True, text=True, cwd=out)
    exe = out / "bench.exe"
    if r.returncode != 0 or not exe.exists():
        raise RuntimeError(r.stdout[-3000:] + r.stderr[-3000:])
    return exe


class Rng:
    def __init__(self):
        self.z = 0x9E3779B97F4A7C15

    def next(self):
        m = (1 << 64) - 1
        self.z ^= (self.z << 13) & m
        self.z ^= self.z >> 7
        self.z ^= (self.z << 17) & m
        return self.z

    def range(self, lim):
        return self.next() % (2 * lim + 1) - lim


def _round_half_even(x: Q) -> int:
    fl = x.numerator // x.denominator
    rem = x - fl
    if rem > Q(1, 2) or (rem == Q(1, 2) and fl % 2):
        fl += 1
    return fl


def _drift(rule: str, r: int, p: int) -> int:
    """The three drift rules in exact integers (r in the rule's storage units)."""
    x = Q(p * DT * A, B)                                   # the displacement in raw 2^-48 units
    if rule == "v1":
        return _round_half_even(r + x)
    if rule == "v2":
        return r + _round_half_even(x)
    return r + p * DT * A                                  # exact: units 2^-48 / B


def expected(limbs: int, n: int, rule: str = "v2") -> list[str]:
    """The same operations in exact Python integers, formatted like the native check lines."""
    g = Rng()
    Rr, Pr, Jr = 1000 << 48, 50 << 48, (1 << 48) // 100
    width = 32 * limbs
    lines = []
    for i in range(n):
        ri, rj, pi, pj, J = [], [], [], [], []
        for k in range(3):
            ri.append(g.range(Rr) * (B if rule == "exact" else 1)); rj.append(g.range(Rr) * (B if rule == "exact" else 1))
            pi.append(g.range(Pr)); pj.append(g.range(Pr))
            J.append(g.range(Jr))
        if i % 8 == 0:                                     # exact drift ties (same as make_pairs)
            pi[0] = (1 if i % 16 == 0 else -1) * TIE_P
            pj[1] = TIE_P
        ok = True
        ri = [_drift(rule, r, p) for r, p in zip(ri, pi)]
        rj = [_drift(rule, r, p) for r, p in zip(rj, pj)]
        ok &= all(-(1 << (width - 1)) <= x < (1 << (width - 1)) for x in ri + rj)
        pj = [p + j for p, j in zip(pj, J)]
        pi = [p - j for p, j in zip(pi, J)]
        dr = [b - a for a, b in zip(ri, rj)]
        R2 = sum(x * x for x in dr)

        def hx(v, bits):
            return format(v & ((1 << bits) - 1), f"0{bits // 4}x")
        parts = ["ok" if ok else "ovf"] + [hx(x, width) for x in ri + rj] + [hx(x, 64) for x in pi + pj]
        parts += [hx(x, width + 32) for x in dr] + [hx(R2, 32 * (2 * limbs + 3))]
        lines.append(" ".join(parts))
    return lines


def run(exe, *args) -> str:
    return subprocess.run([str(exe), *map(str, args)], capture_output=True, text=True, check=True).stdout


def check(exe, limbs: int, n: int, rule: str = "v2") -> bool:
    with tempfile.TemporaryDirectory() as d:
        out = pathlib.Path(d) / "c.txt"
        subprocess.run([str(exe), "check", rule, str(limbs), str(n), str(out)], check=True)
        return out.read_text().split("\n")[:n] == expected(limbs, n, rule)


# --- momentum-representation comparison (designer 15th ed.) -------------------------------------------------------

MOM_KINDS = {"fx64_48": (64, 48), "fx80_64": (96, 64), "fx96_80": (96, 80), "fx128_112": (128, 112), "carry": None}
HALF_COARSE = 1 << 62


def _rng_range(x: int, lim: int) -> int:
    return x % (2 * lim + 1) - lim


def _wrap(v: int, bits: int) -> int:
    v &= (1 << bits) - 1
    return v - (1 << bits) if v >> (bits - 1) else v


def _carry_split(total: int):
    c = _round_half_even(Q(total, 1 << 63))
    return c, total - (c << 63)


def expected_mom(kind: str, n: int) -> list[str]:
    """Position FX(96,48), drift v2, momentum `kind`: drift, kick, dr, R^2 in exact integers (native storage widths)."""
    g = Rng()
    RR, P, Jr = 1000 << 48, 50 << 48, (1 << 48) // 100
    spec = MOM_KINDS[kind]
    lines = []
    for i in range(n):
        ri, rj, pi, pj, J = [], [], [], [], []
        for k in range(3):
            ri.append(g.range(RR)); rj.append(g.range(RR))
            bi, bj, bJ = g.range(P), g.range(P), g.range(Jr)
            xi, xj, xJ = g.next(), g.next(), g.next()
            ti, tj = i % 8 == 0 and k == 0, i % 8 == 0 and k == 1
            if ti:
                bi = (1 if i % 16 == 0 else -1) * TIE_P
            if tj:
                bj = TIE_P
            if spec is None:
                pi.append((bi, 0 if ti else _rng_range(xi, HALF_COARSE)))
                pj.append((bj, 0 if tj else _rng_range(xj, HALF_COARSE)))
                J.append((bJ << 63) + _rng_range(xJ, HALF_COARSE))
            else:
                bits, F = spec
                S = F - 48
                ext = lambda x: 0 if S == 0 else x if S >= 64 else x & ((1 << S) - 1)
                pi.append(_wrap((bi << S) + (0 if ti else ext(xi)), bits))
                pj.append(_wrap((bj << S) + (0 if tj else ext(xj)), bits))
                J.append(_wrap((bJ << S) + ext(xJ), bits))
        ok = True
        if spec is None:
            dq = lambda p: _round_half_even(Q(p[0] * DT * A, B))
        else:
            dq = lambda p, S=spec[1] - 48: _round_half_even(Q(p * DT * A, B << S))
        ri = [r + dq(p) for r, p in zip(ri, pi)]
        rj = [r + dq(p) for r, p in zip(rj, pj)]
        ok &= all(-(1 << 95) <= x < (1 << 95) for x in ri + rj)
        if spec is None:
            tot_j = [(c << 63) + r + j for (c, r), j in zip(pj, J)]
            tot_i = [(c << 63) + r - j for (c, r), j in zip(pi, J)]
            pj, pi = [_carry_split(t) for t in tot_j], [_carry_split(t) for t in tot_i]
            ok &= all(-(1 << 63) <= c < (1 << 63) for c, _ in pi + pj)
            mhex = lambda v: format(v[0] & ((1 << 64) - 1), "016x") + ":" + format(v[1] & ((1 << 64) - 1), "016x")
        else:
            bits = spec[0]
            nj = [p + j for p, j in zip(pj, J)]
            ni = [p - j for p, j in zip(pi, J)]
            ok &= all(-(1 << (bits - 1)) <= x < (1 << (bits - 1)) for x in ni + nj)
            pj, pi = [_wrap(x, bits) for x in nj], [_wrap(x, bits) for x in ni]
            mhex = lambda v: format(v & ((1 << bits) - 1), f"0{bits // 4}x")
        dr = [b - a for a, b in zip(ri, rj)]
        R2 = sum(x * x for x in dr)

        def hx(v, bits):
            return format(v & ((1 << bits) - 1), f"0{bits // 4}x")
        parts = ["ok" if ok else "ovf"] + [hx(x, 96) for x in ri + rj] + [mhex(x) for x in pi + pj]
        parts += [hx(x, 128) for x in dr] + [hx(R2, 32 * 9)]
        lines.append(" ".join(parts))
    return lines


def check_mom(exe, kind: str, n: int) -> bool:
    with tempfile.TemporaryDirectory() as d:
        out = pathlib.Path(d) / "c.txt"
        subprocess.run([str(exe), "mcheck", kind, str(n), str(out)], check=True)
        return out.read_text().split("\n")[:n] == expected_mom(kind, n)
