"""A-Numeric VM 0.1 (docs/current/A_NUMERIC_EXECUTION_STACK_V1.md, section 3).

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

from a_numeric import (ANVM_VERSION, OPCODES, SPEC_HASH, Binary64Finite, Exact, FixedPoint, Instr, VMRejected,
                       program_digest, run)

F64 = Binary64Finite()


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
# SUM and DOT: exact accumulation, ONE rounding -- order of terms and of axes
# cannot matter (VM 0.1; 0 had pairwise rounding and an axis-order-dependent DOT).
# ---------------------------------------------------------------------------

NON_ASSOC = [bits(1e16), bits(1.0), bits(-1e16), bits(1.0), bits(3.0), bits(-2.5)]


def test_naive_float_sum_depends_on_order() -> None:
    """Why SUM must be exact: the same six numbers, folded left in different orders."""
    # functools.reduce, not sum(): since 3.12 sum() compensates float rounding
    results = {bits(functools.reduce(operator.add, (flt(x) for x in perm))) for perm in itertools.permutations(NON_ASSOC)}
    assert len(results) > 1


@pytest.mark.parametrize("profile, values", [
    (F64, NON_ASSOC),
    (FX, [FX.from_exact(x) for x in ("1/3", "-7/5", "100", "1/65536", "-100")]),
    (Exact(), [Fraction(1, 3), Fraction(-7, 5), Fraction(2)]),
])
def test_sum_is_independent_of_order(profile, values) -> None:
    assert len({profile.sum(list(p)) for p in itertools.permutations(values)}) == 1


def test_binary64_sum_is_the_correctly_rounded_exact_sum() -> None:
    """Independent check: math.fsum returns the correctly rounded exact sum of floats."""
    groups = [A[i:i + 7] for i in range(0, 700, 7)] + [NON_ASSOC]
    checked = 0
    for g in groups:
        try:
            want = math.fsum(flt(x) for x in g)
        except OverflowError:                               # fsum's own limit, not A's
            continue
        if math.isinf(want):
            continue
        checked += 1
        try:
            got = F64.sum(g)
        except Exception as e:                              # noqa: BLE001
            assert e.reason == "overflow"
            continue
        assert got == bits(want), [hex(x) for x in g]
    assert checked > 50                                     # not vacuous
    assert F64.sum(NON_ASSOC) == bits(2.5)                  # exact: 1 + 1 + 3 - 2.5


def test_fixed_point_sum_checks_range_once() -> None:
    """The exact total is in range, so no order can make it halt."""
    for p in itertools.permutations([FX.hi, FX.from_exact(1), FX.from_exact(-1)]):
        assert FX.sum(list(p)) == FX.hi


def test_binary64_sum_zero_sign_is_order_free() -> None:
    neg0 = 1 << 63
    assert F64.sum([neg0, neg0, neg0]) == neg0
    for p in itertools.permutations([neg0, 0, neg0]):
        assert F64.sum(list(p)) == 0
    assert F64.sum([bits(1.0), bits(-1.0)]) == 0


def test_dot_is_exact_and_independent_of_axis_order() -> None:
    """VM 0 pinned a left fold that gave 0 one way and 2 the other; the exact DOT gives 2
    (= 2**53 + 1 + 1 - 2**53) whatever the axis order."""
    big = float(2 ** 53)
    xs = [bits(big), bits(1.0), bits(1.0), bits(-big)]
    ones = [bits(1.0)] * 4
    assert {F64.dot([xs[i] for i in p], ones) for p in itertools.permutations(range(4))} == {bits(2.0)}
    fx_x = [FX.from_exact(v) for v in ("1/3", "-5/7", "9/2")]
    fx_y = [FX.from_exact(v) for v in ("7/3", "1/65536", "-2")]
    assert len({FX.dot([fx_x[i] for i in p], [fx_y[i] for i in p]) for p in itertools.permutations(range(3))}) == 1


def test_dot_rounds_once() -> None:
    """Independent: the exact dot of represented values, rounded by a DIFFERENT method."""
    for i in range(0, 600, 3):
        xs, ys = A[i:i + 3], B[i:i + 3]
        exact = sum((F64.to_exact(x) * F64.to_exact(y) for x, y in zip(xs, ys)), Fraction(0))
        try:
            got = F64.dot(xs, ys)
        except Exception:                                   # noqa: BLE001
            continue
        if exact != 0:
            assert _is_nearest_even(got, exact)
    scale = 1 << FX.frac_bits
    for a, b in zip(_fx_values("da", 300), _fx_values("db", 300)):
        xs, ys = [a, b >> 3], [b >> 5, a >> 7]
        want = round(Fraction(sum(x * y for x, y in zip(xs, ys)), scale))
        try:
            assert FX.dot(xs, ys) == want
        except Exception as e:                              # noqa: BLE001
            assert e.reason == "overflow" and not FX.lo <= want <= FX.hi


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


def test_spec_version_and_hash_are_frozen() -> None:
    """Changing the meaning must be a conscious act: update this hash AND the version."""
    assert ANVM_VERSION == "0.1"
    assert SPEC_HASH == "aaf88d9f5d641c0935436f884b00f7e823be5c0280b4126817377f98237a0b97"


def test_results_carry_provenance() -> None:
    program = [Instr("CONST", "a", ("1/7",))]
    doc = run(program, FX).canonical()
    assert doc["vm_version"] == "0.1" and doc["spec_hash"] == SPEC_HASH and doc["profile"] == "FX(32,16)"
    assert doc["program_digest"] == program_digest(program)
    assert run(program, FixedPoint(64, 32)).canonical()["profile"] == "FX(64,32)"


C1 = Instr("CONST", "one", (1,))


@pytest.mark.parametrize("program, profile, inputs, code", [
    ([C1, Instr("SQRT", "y", ("one",))], Exact(), None, "unsupported_operation"),
    ([Instr("RANDOM", "x", ())], F64, None, "unknown_instruction"),
    (["ADD one one"], F64, None, "unknown_instruction"),
    ([C1, Instr("ADD", "x", ("one",))], F64, None, "bad_arity"),
    ([C1, Instr("ADD", "x", ["one", "one"])], F64, None, "unknown_instruction"),
    ([C1, Instr("ADD", "x", ("one", "ghost"))], F64, None, "undefined_register"),
    ([Instr("ADD", "x", ("x", "x"))], F64, None, "undefined_register"),
    ([C1, Instr("CMP", "flag", ("one", "one"))], F64, None, "bad_destination"),
    ([C1, Instr("NEG", None, ("one",))], F64, None, "bad_destination"),
    ([C1, Instr("SUM", "s", ())], F64, None, "bad_arity"),
    ([C1, Instr("DOT", "d", (("one",), ("one", "one")))], F64, None, "bad_arity"),
    ([C1, Instr("DOT", "d", ("one", "one"))], F64, None, "bad_arity"),
    ([Instr("CONST", "x", (0.1,))], F64, None, "bad_literal"),
    ([Instr("CONST", "x", (True,))], F64, None, "bad_literal"),
    ([Instr("CONST", "x", ("1/0",))], F64, None, "bad_literal"),
    ([], F64, {"x": bits(math.inf)}, "bad_input_value"),
    ([], F64, {"x": bits(math.nan)}, "bad_input_value"),
    ([], F64, {"x": 1 << 64}, "bad_input_value"),
    ([], FX, {"x": FX.hi + 1}, "bad_input_value"),
    ([], FX, {"x": True}, "bad_input_value"),
    ([], Exact(), {"x": 0.5}, "bad_input_value"),
    ([], F64, {3: 0}, "bad_register"),
])
def test_bad_programs_and_inputs_end_in_one_canonical_rejection(program, profile, inputs, code) -> None:
    with pytest.raises(VMRejected) as info:
        run(program, profile, inputs)
    assert info.value.code == code


def test_halt_is_a_recorded_result() -> None:
    program = [Instr("CONST", "big", ("1e308",)), Instr("CONST", "ten", (10,)),
               Instr("MUL", "x", ("big", "ten")), Instr("CONST", "never", (1,))]
    result = run(program, F64)
    assert result.halt == (2, "overflow") and "never" not in result.registers


def test_branch_records_the_represented_margin() -> None:
    """The margin is between REPRESENTED values: 1/3 and 1/3 + 1e-30 round to the same
    double, so the represented margin is 0 while the mathematical one is not."""
    program = [Instr("CONST", "a", ("1/3",)), Instr("CONST", "b", (Fraction(1, 3) + Fraction(1, 10 ** 30),)),
               Instr("CMP", None, ("a", "b"))]
    (b,) = run(program, F64).branches
    assert b.result == 0 and b.represented_margin == 0
    (e,) = run(program, Exact()).branches
    assert e.result == -1 and e.represented_margin == Fraction(1, 10 ** 30)


def test_distance_squared() -> None:
    program = [Instr("CONST", n, (v,)) for n, v in [("x0", 3), ("x1", 4)]]
    program.append(Instr("DOT", "r2", (("x0", "x1"), ("x0", "x1"))))
    for profile in (F64, FX, Exact()):
        assert run(program, profile).registers["r2"] == profile.encode(profile.from_exact(25))


def test_same_program_same_digest() -> None:
    program = [Instr("CONST", "a", ("1/7",)), Instr("CONST", "b", ("22/7",)), Instr("DIV", "c", ("b", "a")),
               Instr("SQRT", "d", ("c",))]
    assert run(program, F64).digest() == run(program, F64).digest()
    assert run(program, F64).digest() != run(program, FX).digest()
