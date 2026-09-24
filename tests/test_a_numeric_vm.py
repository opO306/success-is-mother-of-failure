"""A-Numeric VM stage 0 (docs/current/A_NUMERIC_EXECUTION_STACK_V1.md, section 3).

Three independent checks of the arithmetic meaning:
  * against hardware IEEE binary64 (Python floats: + - * / and math.sqrt are
    correctly rounded, so the bits must match exactly);
  * against exact rationals with a DIFFERENT rounding method (neighbours via
    math.nextafter / Python's round-half-even on Fractions);
  * hand-worked cases.
Inputs come from a fixed sha256 counter -- deterministic, no random module.
"""
from __future__ import annotations

import functools
import hashlib
import itertools
import math
import operator
import struct
from fractions import Fraction

import pytest

from a_numeric import (OPCODES, Exact, FixedPoint, IEEE64Strict, Instr, VMUnsupported, canonical_sum,
                       run)

F64 = IEEE64Strict()


def bits(x: float) -> int:
    return struct.unpack("<Q", struct.pack("<d", x))[0]


def flt(b: int) -> float:
    return struct.unpack("<d", struct.pack("<Q", b))[0]


def _stream(tag: str, n: int):
    for i in range(n):
        yield int.from_bytes(hashlib.sha256(f"{tag}:{i}".encode()).digest()[:8], "little")


def _finite_patterns(tag: str, n: int):
    """Mixed families: raw patterns, subnormals, near 1, near overflow, small exponents."""
    out = []
    for i, r in enumerate(_stream(tag, n)):
        family = i % 5
        sign = (r >> 63) << 63
        frac = r & ((1 << 52) - 1)
        if family == 0:
            field = (r >> 52) & 0x7FF
        elif family == 1:
            field = 0                                   # subnormal
        elif family == 2:
            field = 1023 + ((r >> 52) & 3) - 1          # around 1
        elif family == 3:
            field = 0x7FE - ((r >> 52) & 3)             # near overflow
        else:
            field = 1 + ((r >> 52) & 3)                 # smallest normals
        if field == 0x7FF:
            field = 0x7FE
        out.append(sign | (field << 52) | frac)
    return out + [0, 1 << 63, bits(1.0), bits(-1.0), 1, bits(5e-324) | (1 << 63), bits(1.7976931348623157e308)]


A = _finite_patterns("a", 1500)
B = _finite_patterns("b", 1500)


def _hardware(op, x, y):
    try:
        r = {"add": x + y, "sub": x - y, "mul": x * y, "div": x / y if y != 0 else None}[op]
    except OverflowError:
        return None
    if r is None or math.isinf(r) or math.isnan(r):
        return None
    return bits(r)


@pytest.mark.parametrize("op", ["add", "sub", "mul", "div"])
def test_ieee_matches_hardware_bit_for_bit(op) -> None:
    halts = 0
    for a, b in zip(A, B):
        want = _hardware(op, flt(a), flt(b))
        try:
            got = getattr(F64, op)(a, b)
        except Exception as e:                  # noqa: BLE001 -- only VMHalt is legal
            assert type(e).__name__ == "VMHalt", e
            assert want is None, (op, hex(a), hex(b))
            halts += 1
            continue
        assert want is not None and got == want, (op, hex(a), hex(b), hex(got), want and hex(want))
    assert halts < len(A)                       # the comparison is not vacuous


def test_ieee_sqrt_matches_hardware_bit_for_bit() -> None:
    for a in A:
        x = flt(a)
        if x < 0:
            with pytest.raises(Exception) as info:
                F64.sqrt(a)
            assert info.value.reason == "sqrt_of_negative"
            continue
        assert F64.sqrt(a) == bits(math.sqrt(x)), hex(a)


def _is_nearest_even(result_bits: int, exact: Fraction) -> bool:
    """Independent of the VM's rounding: the exact value must lie within half the gap
    to each neighbour, and on a tie the result's last mantissa bit must be even."""
    r = flt(result_bits)
    here = Fraction(r)
    for toward in (math.inf, -math.inf):
        nb = math.nextafter(r, toward)
        if math.isinf(nb):
            continue
        mid = (here + Fraction(nb)) / 2
        if toward > 0 and exact > mid or toward < 0 and exact < mid:
            return False
        if exact == mid and result_bits & 1:
            return False
    return True


def test_ieee_rounding_against_exact_rationals() -> None:
    for a, b in list(zip(A, B))[:600]:
        xa, xb = F64.to_exact(a), F64.to_exact(b)
        for op, exact in (("add", xa + xb), ("mul", xa * xb), ("div", xa / xb if xb else None)):
            if exact is None or exact == 0:
                continue
            try:
                r = getattr(F64, op)(a, b)
            except Exception:                   # noqa: BLE001
                continue                        # overflow halts are covered above
            assert _is_nearest_even(r, exact), (op, hex(a), hex(b))


def test_ieee_ties_and_signed_zero() -> None:
    one = F64.from_exact(1)
    tie = F64.from_exact(Fraction(1) + Fraction(1, 2 ** 53))   # exactly between 1 and 1+2^-52
    assert tie == one                                          # ties go to the even neighbour
    assert F64.from_exact(Fraction(1) + Fraction(3, 2 ** 53)) == bits(1.0 + 2 ** -51)
    neg0 = 1 << 63
    assert F64.add(neg0, neg0) == neg0
    assert F64.add(0, neg0) == 0
    assert F64.sub(one, one) == 0
    assert F64.mul(neg0, one) == neg0
    assert F64.sqrt(neg0) == neg0


@pytest.mark.parametrize("call, reason", [
    (lambda: F64.mul(bits(1e308), bits(10.0)), "overflow"),
    (lambda: F64.div(bits(1.0), 0), "division_by_zero"),
    (lambda: F64.div(0, 0), "division_by_zero"),
    (lambda: F64.sqrt(bits(-2.0)), "sqrt_of_negative"),
    (lambda: F64.add(bits(math.inf), 0), "non_finite_value"),
])
def test_ieee_never_produces_nan_or_infinity(call, reason) -> None:
    with pytest.raises(Exception) as info:
        call()
    assert info.value.reason == reason


# ---------------------------------------------------------------------------
# Fixed point.
# ---------------------------------------------------------------------------

FX = FixedPoint(32, 16)


def _fx_values(tag, n):
    return [((r >> 1) % (1 << 31)) * (-1 if r & 1 else 1) >> ((r >> 40) % 24) for r in _stream(tag, n)]


def test_fixed_point_mul_div_round_half_even_independently() -> None:
    scale = 1 << FX.frac_bits
    for a, b in zip(_fx_values("fa", 800), _fx_values("fb", 800)):
        for op, exact in (("mul", Fraction(a * b, scale)), ("div", Fraction(a * scale, b) if b else None)):
            if exact is None:
                continue
            want = round(exact)                 # Python rounds Fractions half-to-even
            try:
                got = getattr(FX, op)(a, b)
            except Exception as e:              # noqa: BLE001
                assert e.reason == "overflow" and not FX.lo <= want <= FX.hi
                continue
            assert got == want, (op, a, b)


def test_fixed_point_hand_cases() -> None:
    h = FX.from_exact
    assert FX.mul(h("3/2"), h(2)) == h(3)
    assert FX.to_exact(FX.mul(1, 1 << 15)) == 0              # 2^-16 * 1/2 = 2^-17: tie -> even 0
    assert FX.to_exact(FX.mul(3, 1 << 15)) == Fraction(2, 1 << 16)   # 1.5 ulp -> 2 ulp
    r = FX.sqrt(h(2))
    n = h(2) << FX.frac_bits
    assert Fraction(2 * r - 1, 2) ** 2 <= n <= Fraction(2 * r + 1, 2) ** 2


def test_fixed_point_sqrt_is_nearest_independently() -> None:
    for a in _fx_values("fs", 800):
        a = abs(a)
        r = FX.sqrt(a)
        n = a << FX.frac_bits
        assert Fraction(2 * r - 1, 2) ** 2 <= n <= Fraction(2 * r + 1, 2) ** 2, a


@pytest.mark.parametrize("call, reason", [
    (lambda: FX.add(FX.hi, 1), "overflow"),
    (lambda: FX.neg(FX.lo), "overflow"),
    (lambda: FX.mul(FX.from_exact(300), FX.from_exact(300)), "overflow"),
    (lambda: FX.div(1, 0), "division_by_zero"),
    (lambda: FX.sqrt(-1), "sqrt_of_negative"),
])
def test_fixed_point_never_wraps(call, reason) -> None:
    with pytest.raises(Exception) as info:
        call()
    assert info.value.reason == reason


# ---------------------------------------------------------------------------
# Canonical sum: order and names cannot matter.
# ---------------------------------------------------------------------------

NON_ASSOC = [bits(1e16), bits(1.0), bits(-1e16), bits(1.0), bits(3.0), bits(-2.5)]


def test_naive_float_sum_depends_on_order() -> None:
    """Why canonical_sum exists: the same six numbers, folded left in two orders."""
    # functools.reduce, not sum(): since 3.12 sum() compensates float rounding
    results = {bits(functools.reduce(operator.add, (flt(x) for x in perm))) for perm in itertools.permutations(NON_ASSOC)}
    assert len(results) > 1


@pytest.mark.parametrize("profile, values", [
    (F64, NON_ASSOC),
    (FX, [FX.from_exact(x) for x in ("1/3", "-7/5", "100", "1/65536", "-100")]),
    (Exact(), [Fraction(1, 3), Fraction(-7, 5), Fraction(2)]),
])
def test_canonical_sum_is_independent_of_order(profile, values) -> None:
    results = {canonical_sum(profile, list(p)) for p in itertools.permutations(values)}
    assert len(results) == 1


def test_register_names_cannot_change_results() -> None:
    def program(names):
        ins = [Instr("CONST", n, (v,)) for n, v in zip(names, ["1/3", "2", "-5/7", "9"])]
        return ins + [Instr("SUM", "s", tuple(names)), Instr("MUL", "p", (names[0], names[3])),
                      Instr("CMP", None, ("s", "p"))]
    a = run(program(["a", "b", "c", "d"]), F64)
    b = run(program(["zz", "q", "a0", "m"]), F64)
    assert (a.registers["s"], a.registers["p"], a.branches) == (b.registers["s"], b.registers["p"], b.branches)


# ---------------------------------------------------------------------------
# The VM itself.
# ---------------------------------------------------------------------------

def test_opcode_set_is_frozen_and_has_no_forbidden_primitives() -> None:
    """Forbid by absence: nothing reads labels, randomness, clocks or threads."""
    assert OPCODES == {"CONST", "ADD", "SUB", "MUL", "DIV", "NEG", "ABS", "SQRT", "CMP", "SUM", "DOT"}


def test_unsupported_operations_are_rejected_before_running() -> None:
    program = [Instr("CONST", "x", (2,)), Instr("SQRT", "y", ("x",))]
    with pytest.raises(VMUnsupported):
        run(program, Exact())
    with pytest.raises(VMUnsupported):
        run([Instr("RANDOM", "x", ())], F64)


def test_float_literals_are_refused() -> None:
    with pytest.raises(TypeError):
        run([Instr("CONST", "x", (0.1,))], F64)


def test_halt_is_a_recorded_result() -> None:
    program = [Instr("CONST", "big", ("1e308",)), Instr("CONST", "ten", (10,)),
               Instr("MUL", "x", ("big", "ten")), Instr("CONST", "never", (1,))]
    result = run(program, F64)
    assert result.halt == (2, "overflow") and "never" not in result.registers


def test_branch_margin_is_recorded_exactly() -> None:
    program = [Instr("CONST", "r2", ("1/3",)), Instr("CONST", "rc2", ("1/3",)), Instr("CMP", None, ("r2", "rc2"))]
    (b,) = run(program, F64).branches
    assert b.result == 0 and b.margin == 0                   # both round to the same double
    (e,) = run(program, Exact()).branches
    assert e.result == 0 and e.margin == 0


def test_dot_and_distance_squared() -> None:
    program = [Instr("CONST", n, (v,)) for n, v in [("x0", 3), ("x1", 4), ("y0", 3), ("y1", 4)]]
    program.append(Instr("DOT", "r2", (("x0", "x1"), ("y0", "y1"))))
    for profile in (F64, FX, Exact()):
        result = run(program, profile)
        assert profile.to_exact(profile.from_exact(25)) == Fraction(25)
        assert result.registers["r2"] == profile.encode(profile.from_exact(25))


def test_same_program_same_digest() -> None:
    program = [Instr("CONST", "a", ("1/7",)), Instr("CONST", "b", ("22/7",)), Instr("DIV", "c", ("b", "a")),
               Instr("SQRT", "d", ("c",))]
    assert run(program, F64).digest() == run(program, F64).digest()
    assert run(program, F64).digest() != run(program, FX).digest()


def test_dot_order_is_the_fixed_axis_fold() -> None:
    """DOT is (((x0*y0 + x1*y1) + x2*y2) + x3*y3): pinned with values where the order shows
    (left to right gives 0, right to left gives 2)."""
    big = float(2 ** 53)
    xs = [big, 1.0, 1.0, -big]
    inputs = {f"x{i}": bits(x) for i, x in enumerate(xs)} | {f"y{i}": bits(1.0) for i in range(4)}
    result = run([Instr("DOT", "d", (("x0", "x1", "x2", "x3"), ("y0", "y1", "y2", "y3")))], F64, inputs=inputs)
    assert result.registers["d"] == f"{bits(((big + 1.0) + 1.0) + -big):016x}" == f"{bits(0.0):016x}"
    assert ((-big + 1.0) + 1.0) + big == 2.0
