"""Build native executors and judge them against the A-Numeric VM.

docs/current/A_NUMERIC_EXECUTION_STACK_V1.md section 4. The VM is the judge:
this module sends the SAME straight-line programs to a native executor and to
`a_numeric.run`, and compares registers, branch records and halts. The
native executor never receives an expected value -- only programs and inputs.
"""
from __future__ import annotations

import hashlib
import os
import pathlib
import subprocess
import tempfile
from fractions import Fraction

from a_numeric import Binary64Finite, FixedPoint, Instr, run as vm_run

HERE = pathlib.Path(__file__).resolve().parent
B0_SOURCE = HERE / "b0_serial.cpp"


# ---------------------------------------------------------------------------
# Toolchain
# ---------------------------------------------------------------------------

def find_vcvars() -> pathlib.Path | None:
    root = pathlib.Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"))
    vswhere = root / "Microsoft Visual Studio" / "Installer" / "vswhere.exe"
    if not vswhere.exists():
        return None
    found = subprocess.run([str(vswhere), "-latest", "-products", "*", "-requires",
                            "Microsoft.VisualStudio.Component.VC.Tools.x86.x64", "-property", "installationPath"],
                           capture_output=True, text=True).stdout.strip()
    bat = pathlib.Path(found) / "VC" / "Auxiliary" / "Build" / "vcvars64.bat" if found else None
    return bat if bat and bat.exists() else None


SOURCES = {"b0": B0_SOURCE, "b1": HERE / "b1_parallel.cpp"}


def build_native(kind: str, out_dir, inject: int = 0) -> pathlib.Path:
    """Compile an executor with MSVC /fp:strict. inject > 0 compiles a deliberate defect."""
    vcvars = find_vcvars()
    if vcvars is None:
        raise RuntimeError("MSVC not found (vswhere/vcvars64.bat)")
    out_dir = pathlib.Path(out_dir) / f"{kind}_inject{inject}"
    out_dir.mkdir(parents=True, exist_ok=True)
    # the repository path is not ASCII; compile copies with relative names inside out_dir
    for f in (SOURCES[kind], HERE / "anvm_core.hpp"):
        (out_dir / f.name).write_bytes(f.read_bytes())
    exe = out_dir / f"{kind}.exe"
    bat = out_dir / "build.bat"
    bat.write_text(f'@call "{vcvars}" >nul\r\n'
                   f'@cl /nologo /O2 /fp:strict /EHsc /std:c++17 /W3 /wd4702 /DINJECT={inject} '
                   f'{SOURCES[kind].name} /Fe{exe.name}\r\n', encoding="mbcs")
    r = subprocess.run(["cmd", "/c", str(bat)], capture_output=True, text=True, cwd=out_dir)
    if r.returncode != 0 or not exe.exists():
        raise RuntimeError(f"{kind} build failed:\n{r.stdout}\n{r.stderr}")
    return exe


def build_b0(out_dir, inject: int = 0) -> pathlib.Path:
    return build_native("b0", out_dir, inject)


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------

def _profile_line(profile) -> str:
    if isinstance(profile, FixedPoint):
        return f"P FX {profile.width} {profile.frac_bits}"
    if isinstance(profile, Binary64Finite):
        return "P B64"
    raise ValueError(f"native executors implement FX and A-Binary64-Finite only, not {profile.name}")


def encode(programs) -> str:
    lines = []
    for profile, inputs, program in programs:
        lines.append(_profile_line(profile))
        lines += [f"I {name} {profile.encode(raw)}" for name, raw in inputs.items()]
        for ins in program:
            if ins.op == "CONST":
                x = Fraction(ins.args[0])
                lines.append(f"X CONST {ins.dst} {x.numerator} {x.denominator}")
            elif ins.op == "DOT":
                xs, ys = ins.args
                lines.append(f"X DOT {ins.dst} {len(xs)} {' '.join(xs + ys)}")
            elif ins.op == "SUM":
                lines.append(f"X SUM {ins.dst} {len(ins.args)} {' '.join(ins.args)}")
            elif ins.op == "CMP":
                lines.append(f"X CMP - {' '.join(ins.args)}")
            else:
                lines.append(f"X {ins.op} {ins.dst} {' '.join(ins.args)}")
        lines.append("E")
    return "\n".join(lines) + "\n"


def decode(text: str) -> list[dict]:
    results, cur = [], None
    for line in text.splitlines():
        w = line.split()
        if not w:
            continue
        if w[0] == "R":
            cur = {"registers": {}, "branches": [], "halt": None}
        elif w[0] == "G":
            cur["registers"][w[1]] = w[2]
        elif w[0] == "B":
            m = Fraction(int(w[3], 16)) * Fraction(2) ** int(w[4])
            cur["branches"].append([int(w[1]), int(w[2]), f"{m.numerator}/{m.denominator}"])
        elif w[0] == "H":
            cur["halt"] = None if w[1] == "-" else [int(w[1]), w[2]]
        elif w[0] == "E":
            results.append(cur)
    return results


def run_native(exe, programs, args=()) -> list[dict]:
    with tempfile.TemporaryDirectory() as d:
        src, dst = pathlib.Path(d) / "programs.txt", pathlib.Path(d) / "results.txt"
        src.write_text(encode(programs), encoding="ascii")
        r = subprocess.run([str(exe), *map(str, args), str(src), str(dst)], capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(f"{exe} exited {r.returncode}: {r.stderr}")
        return decode(dst.read_text(encoding="ascii"))


def vm_expected(programs) -> list[dict]:
    out = []
    for profile, inputs, program in programs:
        c = vm_run(program, profile, inputs).canonical()
        out.append({"registers": c["registers"], "branches": c["branches"], "halt": c["halt"]})
    return out


def mismatches(expected, got) -> list[int]:
    if len(expected) != len(got):
        return list(range(max(len(expected), len(got))))
    return [i for i, (e, g) in enumerate(zip(expected, got)) if e != g]


# ---------------------------------------------------------------------------
# Case families (deterministic: sha256 counters, R1-0 boundary cases)
# ---------------------------------------------------------------------------

F64 = Binary64Finite()


def _stream(tag: str, n: int):
    for i in range(n):
        yield int.from_bytes(hashlib.sha256(f"{tag}:{i}".encode()).digest(), "little")


def finite_patterns(tag: str, n: int) -> list[int]:
    """Raw patterns, subnormals, near 1, near overflow, smallest normals."""
    out = []
    for i, r in enumerate(_stream(tag, n)):
        family = i % 5
        sign, frac = ((r >> 63) & 1) << 63, r & ((1 << 52) - 1)
        field = [(r >> 52) & 0x7FF, 0, 1022 + ((r >> 52) & 3), 0x7FE - ((r >> 52) & 3), 1 + ((r >> 52) & 3)][family]
        out.append(sign | (min(field, 0x7FE) << 52) | frac)
    return out


def moderate_patterns(tag: str, n: int, lo: int = 1013, hi: int = 1033) -> list[int]:
    """Values with exponents in a narrow band -- physical coordinates, not edge cases."""
    return [((r >> 63) & 1) << 63 | (lo + (r >> 52) % (hi - lo)) << 52 | (r & ((1 << 52) - 1))
            for r in _stream(tag, n)]


def _binary(profile, op, a, b):
    return profile, {"a": a, "b": b}, [Instr(op, None if op == "CMP" else "r", ("a", "b"))]


def _unary(profile, op, a):
    return profile, {"a": a}, [Instr(op, "r", ("a",))]


def _sum(profile, terms):
    names = tuple(f"t{i}" for i in range(len(terms)))
    return profile, dict(zip(names, terms)), [Instr("SUM", "r", names)]


def _dot(profile, xs, ys):
    xn, yn = tuple(f"x{i}" for i in range(len(xs))), tuple(f"y{i}" for i in range(len(ys)))
    return profile, {**dict(zip(xn, xs)), **dict(zip(yn, ys))}, [Instr("DOT", "r", (xn, yn))]


def _const(profile, value):
    return profile, {}, [Instr("CONST", "r", (value,))]


def family_b64_hard():
    """R1-0 boundary cases (ties, near-midpoints, underflow/overflow edges, SUM/DOT)."""
    from audit.independent_numeric import binary64_cases
    out = []
    for c in binary64_cases():
        if c.op == "sum":
            out.append(_sum(F64, list(c.args)))
        elif c.op == "dot":
            out.append(_dot(F64, list(c.args[0]), list(c.args[1])))
        elif c.op == "sqrt":
            out.append(_unary(F64, "SQRT", c.args[0]))
        else:
            out.append(_binary(F64, c.op.upper(), *c.args))
    return out


def family_b64_stream():
    a, b = finite_patterns("b0a", 1500), finite_patterns("b0b", 1500)
    out = []
    for x, y in zip(a, b):
        out += [_binary(F64, op, x, y) for op in ("ADD", "SUB", "MUL", "DIV", "CMP")]
        out += [_unary(F64, op, x) for op in ("SQRT", "NEG", "ABS")]
    zeros = [0, 1 << 63]
    out += [_binary(F64, op, x, y) for op in ("ADD", "SUB", "MUL", "DIV", "CMP") for x in zeros for y in zeros + a[:5]]
    return out


def family_b64_sum_dot():
    pool = finite_patterns("b0s", 4000) + moderate_patterns("b0m", 2000)
    out, i = [], 0
    for n in list(range(1, 17)) * 40:
        terms = pool[i:i + n]
        i = (i + n) % (len(pool) - 40)
        out.append(_sum(F64, terms))
        out.append(_sum(F64, terms[::-1]))                       # order must not matter
        out.append(_dot(F64, terms, pool[i:i + n]))
    # exact ties and near-ties of the single final rounding: a + half an ulp of a (+- a far smaller term)
    for a in moderate_patterns("b0t", 300, 900, 1100):
        e = ((a >> 52) & 0x7FF) - 1075 - 1                       # half an ulp of a
        half = F64.from_exact(Fraction(2) ** e)
        tiny = F64.from_exact(Fraction(2) ** (e - 70))
        out += [_sum(F64, [a, half]), _sum(F64, [half, a, tiny]), _sum(F64, [a, half, tiny ^ (1 << 63)]),
                _dot(F64, [a, half], [F64.from_exact(1), F64.from_exact(1)])]
    # signed zero of an exact-zero SUM / DOT (the A rule: -0 only if every term is -0)
    nz, pz, one = 1 << 63, 0, F64.from_exact(1)
    for terms in ([nz], [pz], [nz, nz], [nz, pz], [pz, nz], [nz, nz, nz], [one, one ^ nz], [one ^ nz, one, nz]):
        out.append(_sum(F64, terms))
    for xs, ys in (([nz], [one]), ([pz], [one ^ nz]), ([nz, pz], [one, one]), ([nz, nz], [one, one]),
                   ([one, one], [one, one ^ nz]), ([nz], [pz])):
        out.append(_dot(F64, xs, ys))
    return out


def family_b64_const():
    lits = [0, 1, -1, Fraction(1, 3), Fraction(-1, 3), Fraction(2 ** 53 + 1, 2 ** 53), Fraction(2 ** 53 + 3, 2 ** 53),
            2 ** 1024 - 2 ** 970, 2 ** 1024 - 2 ** 970 - 1, 2 ** 1024, Fraction(1, 2 ** 1075), Fraction(3, 2 ** 1076),
            Fraction(1, 2 ** 1076), 10 ** 400, Fraction(1, 10 ** 400), Fraction(-7, 10 ** 320), Fraction(10 ** 30 + 1, 3)]
    for r in _stream("b0c", 1500):
        num = (r & ((1 << 200) - 1)) >> ((r >> 200) % 190)
        den = ((r >> 210) & ((1 << 40) - 1)) + 1 << ((r >> 250) % 60)
        lits.append(Fraction(-num if r >> 255 else num, den))
    return [_const(F64, x) for x in lits]


FX64 = FixedPoint(64, 32)


def family_fx_exhaustive():
    """FX(6,2) every pair for every binary op, every value for unary ops; FX(7,3) MUL/DIV/SQRT."""
    out = []
    p = FixedPoint(6, 2)
    vals = range(-32, 32)
    for a in vals:
        out += [_unary(p, op, a) for op in ("SQRT", "NEG", "ABS")]
        for b in vals:
            out += [_binary(p, op, a, b) for op in ("ADD", "SUB", "MUL", "DIV", "CMP")]
    q = FixedPoint(7, 3)
    for a in range(-64, 64):
        out.append(_unary(q, "SQRT", a))
        for b in range(-64, 64):
            out += [_binary(q, "MUL", a, b), _binary(q, "DIV", a, b)]
    return out


def family_fx_wide():
    from audit.independent_numeric.hard_cases import fx_wide_ties
    out = [_binary(FX64, op.upper(), a, b) for op, a, b in fx_wide_ties(64, 32)]
    hi, lo = FX64.hi, FX64.lo
    edges = [hi, hi - 1, lo, lo + 1, 0, 1, -1, 1 << 32, -(1 << 32), 1 << 31, 3 << 31]
    raw = [(r & ((1 << 64) - 1)) - (1 << 63) >> ((r >> 64) % 48) for r in _stream("b0fx", 1500)]
    for a, b in zip(edges + raw, raw + edges):
        out += [_binary(FX64, op, a, b) for op in ("ADD", "SUB", "MUL", "DIV", "CMP")]
        out += [_unary(FX64, op, a) for op in ("SQRT", "NEG", "ABS")]
    for n in list(range(1, 13)) * 20:
        out.append(_sum(FX64, raw[n:2 * n]))
        out.append(_dot(FX64, raw[n:2 * n], raw[3 * n:4 * n]))
    out += [_sum(FX64, [hi, 1, -1]), _sum(FX64, [hi, hi, -hi]), _dot(FX64, [hi, 1 << 32], [1 << 32, 1 << 32])]
    out += [_const(FX64, x) for x in (Fraction(1, 3), Fraction(-1, 3), Fraction(1, 2 ** 33), Fraction(3, 2 ** 33),
                                      Fraction(-3, 2 ** 33), 2 ** 31, -2 ** 31, 2 ** 31 - Fraction(1, 2 ** 32))]
    return out


def _points(tag, n, pattern):
    vals = pattern(tag, 6 * n)
    return [vals[6 * i:6 * i + 6] for i in range(n)]


def distance_program(profile, xi, xj):
    names = ("xi", "yi", "zi", "xj", "yj", "zj")
    prog = [Instr("SUB", "dx", ("xj", "xi")), Instr("SUB", "dy", ("yj", "yi")), Instr("SUB", "dz", ("zj", "zi")),
            Instr("DOT", "r2", (("dx", "dy", "dz"), ("dx", "dy", "dz")))]
    return profile, dict(zip(names, list(xi) + list(xj))), prog


def family_distance():
    out = []
    for pt in _points("b0d", 600, moderate_patterns):
        out.append(distance_program(F64, pt[:3], pt[3:]))
    for pt in _points("b0dw", 300, finite_patterns):
        out.append(distance_program(F64, pt[:3], pt[3:]))
    fx_raw = lambda tag, n: [(r & ((1 << 40) - 1)) - (1 << 39) for r in _stream(tag, n)]  # noqa: E731
    for pt in _points("b0dfx", 600, fx_raw):
        out.append(distance_program(FX64, pt[:3], pt[3:]))
    return out


# --- potential capability probes (NOT a choice of C0 potential) --------------

def p_a_program():
    """P-a: polynomial in r^2 with a smooth cutoff, U = A (rc^2 - r^2)^4. Needs only SUB MUL CMP."""
    return [Instr("CONST", "rc2", (4,)), Instr("CONST", "A", ("1/2",)), Instr("CONST", "four", (4,)),
            Instr("CMP", None, ("r2", "rc2")), Instr("SUB", "s", ("rc2", "r2")), Instr("MUL", "s2", ("s", "s")),
            Instr("MUL", "s4", ("s2", "s2")), Instr("MUL", "U", ("A", "s4")), Instr("MUL", "s3", ("s2", "s")),
            Instr("MUL", "t", ("four", "s3")), Instr("MUL", "f", ("A", "t"))]


def p_b_program():
    """P-b: WCA-shaped power law in sigma^2 / r^2 (sigma = eps = 1). Needs DIV, no SQRT."""
    return [Instr("CONST", "one", (1,)), Instr("CONST", "two", (2,)), Instr("CONST", "four", (4,)),
            Instr("CONST", "c24", (24,)), Instr("CONST", "rc2", ("126/100",)), Instr("CMP", None, ("r2", "rc2")),
            Instr("DIV", "inv", ("one", "r2")), Instr("MUL", "i2", ("inv", "inv")), Instr("MUL", "i3", ("i2", "inv")),
            Instr("MUL", "i6", ("i3", "i3")), Instr("SUB", "d", ("i6", "i3")), Instr("MUL", "U0", ("four", "d")),
            Instr("ADD", "U", ("U0", "one")), Instr("MUL", "t", ("two", "i6")), Instr("SUB", "t2", ("t", "i3")),
            Instr("MUL", "f1", ("c24", "t2")), Instr("MUL", "f", ("f1", "inv"))]


def p_c_program():
    """P-c: Born-Mayer A exp(-r / rho). VM 0.1 has SQRT but NO EXP -- only the part up to
    the exponent's argument is expressible. EXP needs a defined deterministic_exp first."""
    return [Instr("CONST", "rho", ("3/10",)), Instr("SQRT", "r", ("r2",)), Instr("DIV", "x", ("r", "rho")),
            Instr("NEG", "arg", ("x",))]


POTENTIALS = {"P-a": p_a_program, "P-b": p_b_program, "P-c(no exp)": p_c_program}


def family_potentials():
    out = []
    b64_r2 = [F64.from_exact(Fraction(k, 64)) for k in range(1, 400, 3)] + moderate_patterns("b0p", 200, 1015, 1025)
    b64_r2 = [v & ~(1 << 63) for v in b64_r2]
    fx_r2 = [FX64.from_exact(Fraction(k, 64)) for k in range(0, 400, 3)] + [1, 2, 1 << 20, 1 << 28]
    for make in POTENTIALS.values():
        out += [(F64, {"r2": v}, make()) for v in b64_r2]
        out += [(FX64, {"r2": v}, make()) for v in fx_r2]
    return out


def family_long_reduction():
    """Long SUM / DOT (the many-forces-on-one-particle case, O6): lengths that do and do not
    divide evenly by 2, 4, 8, 12 threads or 32..256-wide blocks."""
    out = []
    lengths = (2, 3, 7, 12, 13, 64, 100, 257, 1000, 2049)
    mixed, calm = finite_patterns("b0L", 4200), moderate_patterns("b0Lm", 4200, 1000, 1050)
    for n in lengths:
        for pool in (mixed, calm):
            out.append(_sum(F64, pool[:n]))
            out.append(_dot(F64, pool[:n], pool[2100:2100 + n]))
        # large cancellation: +x ... then -x ... with a tiny survivor that must not be lost
        big = calm[:n]
        out.append(_sum(F64, big + [v ^ (1 << 63) for v in big] + [F64.from_exact(Fraction(1, 2 ** 80))]))
        fx = [(r & ((1 << 36) - 1)) - (1 << 35) for r in _stream(f"b0Lfx{n}", 2 * n)]
        out.append(_sum(FX64, fx[:n]))
        out.append(_dot(FX64, fx[:n], fx[n:]))
    return out


FAMILIES = {
    "b64_hard": family_b64_hard,
    "b64_stream": family_b64_stream,
    "b64_sum_dot": family_b64_sum_dot,
    "b64_const": family_b64_const,
    "fx_exhaustive": family_fx_exhaustive,
    "fx_wide": family_fx_wide,
    "distance": family_distance,
    "potentials": family_potentials,
    "long_reduction": family_long_reduction,
}
