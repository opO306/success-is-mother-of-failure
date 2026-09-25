"""EXP (deterministic_exp_v1, VM 0.2) judged by R1 interval arithmetic.

docs/current/A_NUMERIC_EXECUTION_STACK_V1.md 3.9. The VM encloses e^x with its
own integer Taylor/squaring scheme; audit/independent_numeric/exp_judge.py uses
mpmath's interval exp. The judge is checked first (known digits of e,
exp(x) exp(-x) = 1, its range thresholds, rejecting neighbours).
"""
from __future__ import annotations

import math
import struct
from fractions import Fraction

import pytest

import a_numeric.exp as vm_exp
from a_numeric import Binary64Finite, Exact, FixedPoint, Instr, VMHalt, VMRejected, run
from audit.independent_numeric.exp_cases import exp_cases
from audit.independent_numeric.exp_judge import (B64_OVERFLOW_FROM, B64_ZERO_UNTIL, enclose, judge_exp_b64,
                                                 judge_exp_fx, ulp_position)
from audit.independent_numeric.oracle import MAX_MAG, value

F64 = Binary64Finite()
CASES = exp_cases()
ALL = [b for v in CASES.values() for b in v]
# e truncated after 98 decimals: E_LO <= e <= E_LO + 10^-98
E_LO = Fraction("2.71828182845904523536028747135266249775724709369995957496696762772407663035354759457138217852516642")


def vm(profile, raw):
    try:
        return profile.exp(raw)
    except VMHalt as h:
        return h.reason


def _f(b):
    return struct.unpack("<d", struct.pack("<Q", b))[0]


# --- the judge is not sacred ---------------------------------------------------

def test_judge_encloses_known_values() -> None:
    a, b = enclose(Fraction(1), 400)
    assert a <= E_LO + Fraction(1, 10 ** 98) and b >= E_LO and b - a < Fraction(1, 10 ** 100)
    for x in (Fraction(1, 3), Fraction(-7, 2), Fraction(123, 4)):
        (a1, b1), (a2, b2) = enclose(x, 300), enclose(-x, 300)
        assert a1 * a2 <= 1 <= b1 * b2


def test_judge_range_thresholds_are_proven() -> None:
    assert enclose(B64_OVERFLOW_FROM, 200)[0] > Fraction(2) ** 1024        # e^710 > 2^1024
    assert enclose(B64_ZERO_UNTIL, 200)[1] < Fraction(1, 2 ** 1076)        # e^-746 < 2^-1076


def test_judge_rejects_every_neighbour_of_the_answer() -> None:
    checked = 0
    for b in ALL:
        r = vm(F64, b)
        if not isinstance(r, int) or r == 0 or r == 0x3FF0000000000000 and b in (0, 1 << 63):
            continue
        for step in (-1, 1):
            m = r + step
            if 0 < m <= MAX_MAG:
                assert judge_exp_b64(b, m) is not None, (hex(b), hex(m))
                checked += 1
    assert checked > 1500


def test_cases_are_hard() -> None:
    """Near-midpoint cases really are near midpoints, and a merely good exp (the C library) fails many."""
    near = [b for b in CASES["constructed_mid"] + CASES["searched_mid"] if abs(_f(b)) < 700]
    assert sum(abs(ulp_position(b) - Fraction(1, 2)) < Fraction(1, 2 ** 30) for b in near) > 200
    libm_wrong = 0
    for b in CASES["constructed_mid"]:
        try:
            h = struct.unpack("<Q", struct.pack("<d", math.exp(_f(b))))[0]
        except OverflowError:
            continue
        libm_wrong += judge_exp_b64(b, h) is not None
    assert libm_wrong > 50
    outcomes = {vm(F64, b) if isinstance(vm(F64, b), str) or vm(F64, b) in (0, 1) else "finite" for b in CASES["edges"]}
    assert {"overflow", 0, 1, "finite"} <= outcomes


# --- the VM --------------------------------------------------------------------

@pytest.mark.parametrize("family", sorted(CASES))
def test_vm_exp_is_correctly_rounded(family) -> None:
    for b in CASES[family]:
        assert judge_exp_b64(b, vm(F64, b)) is None, hex(b)


@pytest.mark.parametrize("width,frac_bits", [(8, 3), (12, 6), (6, 0)])
def test_vm_exp_fixed_point_exhaustive(width, frac_bits) -> None:
    p = FixedPoint(width, frac_bits)
    for a in range(-(1 << (width - 1)), 1 << (width - 1)):
        assert judge_exp_fx(a, vm(p, a), width, frac_bits) is None, a


def test_vm_exp_fixed_point_wide() -> None:
    p = FixedPoint(64, 32)
    xs = [p.from_exact(Fraction(k, 7)) for k in range(-170, 160)] + [0, 1, -1, p.hi, p.lo]
    for a in xs:
        assert judge_exp_fx(a, vm(p, a), 64, 32) is None, a


def test_exp_in_programs_and_capabilities() -> None:
    r = run([Instr("CONST", "x", ("1/2",)), Instr("EXP", "y", ("x",))], F64)
    assert _f(int(r.registers["y"], 16)) == math.exp(0.5) or judge_exp_b64(F64.from_exact("1/2"), int(r.registers["y"], 16)) is None
    assert run([Instr("CONST", "x", (800,)), Instr("EXP", "y", ("x",))], F64).halt == (1, "overflow")
    with pytest.raises(VMRejected) as info:
        run([Instr("CONST", "x", (1,)), Instr("EXP", "y", ("x",))], Exact())
    assert info.value.code == "unsupported_operation"
    assert vm(F64, 0) == vm(F64, 1 << 63) == 0x3FF0000000000000


def test_ln2_bound_used_for_early_ranges() -> None:
    lo, _ = vm_exp.enclosure(vm_exp.LN2_UPPER, 300, 8)
    assert lo > 2 << 300                     # e^0.6932 > 2, so 0.6932 > ln 2


# --- fault injection -------------------------------------------------------------

def _no_refinement(profile, x):
    """Same early ranges, but ONE enclosure at a fixed modest precision, rounded at its midpoint."""
    if x > 1024 * vm_exp.LN2_UPPER:
        raise VMHalt("overflow")
    if x < -1076 * vm_exp.LN2_UPPER:
        return 0
    k = max(0, x.numerator.bit_length() - x.denominator.bit_length() + 1) + 8 if x else 8
    M = 2 * k + 70                                        # about 70 bits for results near 1, fewer for small ones
    lo, hi = vm_exp.enclosure(x, M, k)
    return profile.from_exact(Fraction(lo + hi, 2 << M))


def _one_squaring_too_many(x, M, k):
    lo, hi = _ORIG_ENCLOSURE(x, M, k)
    return (lo * lo) >> M, -((-hi * hi) >> M)


_ORIG_ENCLOSURE = vm_exp.enclosure


def _early_stop_taylor(Y, M):
    a, neg, one = abs(Y), Y < 0, 1 << M
    t, s, i = one, one, 0
    while t > one >> 48:                                  # Taylor accurate to about 48 bits
        i += 1
        t = t * a // (i << M)
        s = s - t if neg and i & 1 else s + t
    return s, s


MUTANTS = {
    "no refinement: one fixed precision, midpoint of the enclosure": ("exp_exact_rounded", _no_refinement),
    "range reduction: one squaring too many": ("enclosure", _one_squaring_too_many),
    "Taylor stopped at ~48 bits, no remainder bound": ("_taylor", _early_stop_taylor),
}


@pytest.mark.parametrize("name", sorted(MUTANTS))
def test_vm_exp_defects_are_caught(name, monkeypatch) -> None:
    attr, fn = MUTANTS[name]
    monkeypatch.setattr(vm_exp, attr, fn)
    if attr == "exp_exact_rounded":
        monkeypatch.setattr(Binary64Finite, "exp", lambda self, a: fn(self, self.to_exact(a)))
    caught = sum(judge_exp_b64(b, vm(F64, b)) is not None for b in ALL)
    assert caught > 0, name


@pytest.mark.parametrize("threshold", ["overflow at 709", "zero below -700"])
def test_early_range_threshold_defects_are_caught(threshold, monkeypatch) -> None:
    orig = vm_exp.exp_exact_rounded

    def wrong(profile, x):
        if threshold == "overflow at 709" and x > 709:
            raise VMHalt("overflow")
        if threshold == "zero below -700" and x < -700:
            return profile.from_exact(0)
        return orig(profile, x)
    monkeypatch.setattr(Binary64Finite, "exp", lambda self, a: wrong(self, self.to_exact(a)))
    assert any(judge_exp_b64(b, vm(F64, b)) is not None for b in CASES["edges"])


def test_platform_exp_is_caught(monkeypatch) -> None:
    """Using the C library's exp instead of the defined meaning."""
    def libm(self, a):
        try:
            return struct.unpack("<Q", struct.pack("<d", math.exp(_f(a))))[0]
        except OverflowError:
            raise VMHalt("overflow") from None
    monkeypatch.setattr(Binary64Finite, "exp", libm)
    assert sum(judge_exp_b64(b, vm(F64, b)) is not None for b in CASES["constructed_mid"]) > 50
