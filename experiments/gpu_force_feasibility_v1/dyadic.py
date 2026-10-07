"""Exact serialization of mpmath raw mpf tuples (sign, man, exp, bc) - no float, no decimal (protocol 'encoding').

An endpoint is [sign, mantissa as lowercase hex of the odd integer, binary exponent, bitcount]; zero = [0, "0", 0, 0].
Value = (-1)**sign * mantissa * 2**exp."""

from __future__ import annotations

from fractions import Fraction

FZERO = (0, 0, 0, 0)


def encode(x):
    sign, man, exp, bc = x
    if not man:
        if (sign, exp, bc) != (0, 0, 0):
            raise ValueError(f"special value {x!r} is not serializable")
        return [0, "0", 0, 0]
    return [int(sign), format(int(man), "x"), int(exp), int(bc)]


def decode(e):
    sign, hexman, exp, bc = e
    man = int(hexman, 16)
    if man == 0:
        return FZERO
    if man & 1 == 0 or man.bit_length() != bc or sign not in (0, 1):
        raise ValueError(f"non-canonical endpoint {e!r}")
    return (sign, man, exp, bc)


def value(x):
    """Exact rational value of a raw tuple."""
    sign, man, exp, bc = x
    v = Fraction(man) * (Fraction(2) ** exp)
    return -v if sign else v


def encode_iv(t):
    return [encode(t[0]), encode(t[1])]


def decode_iv(e):
    return (decode(e[0]), decode(e[1]))
