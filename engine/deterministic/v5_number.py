"""causal v5: the one way exact numbers enter the world (plan section 2).

Every physical quantity in v5 is an exact rational (`fractions.Fraction`):
always reduced, denominator positive, 0 == 0/1. So one physical value has
exactly one serialised form and one hash -- 2/4 and 1/2 cannot disagree.

Floats never enter. `q()` accepts an `int` or an "n/d" / "n" string only;
a float (or a bool, which Python treats as an int) is refused. Arithmetic
elsewhere must stay `int | Fraction` -- `Fraction(1, 3) * 0.5` silently
becomes a float in Python, which is why the physics modules are also
checked by AST (`tests/test_v5_reference.py`).

The fraction is the reference executor's exact representation, not a law
of the world (designer decision K2): another executor may use another
number system if it reproduces these results exactly.
"""
from __future__ import annotations

from fractions import Fraction
from typing import Iterable

Vec = tuple[Fraction, Fraction]
ZERO = Fraction(0)


def q(value: object) -> Fraction:
    """The only constructor: int, Fraction, or an "n/d" / "n" string."""
    if isinstance(value, bool):
        raise TypeError("a bool is not a number here")
    if isinstance(value, Fraction):
        return value
    if isinstance(value, int):
        return Fraction(value)
    if isinstance(value, str):
        text = value.strip()
        if any(mark in text for mark in (".", "e", "E")):
            raise TypeError(f"decimal or exponent notation is refused: {value!r}")
        return Fraction(text)
    raise TypeError(f"exact numbers only (int, Fraction, 'n/d'); got {type(value).__name__}")


def vec(pair: Iterable[object]) -> Vec:
    x, y = pair
    return (q(x), q(y))


def ser(value: Fraction) -> list[int]:
    value = q(value)
    return [value.numerator, value.denominator]


def deser(pair: list[int]) -> Fraction:
    numerator, denominator = pair
    if not isinstance(numerator, int) or not isinstance(denominator, int) or isinstance(numerator, bool):
        raise TypeError("a serialised number is two ints")
    if denominator <= 0:
        raise ValueError("denominator must be positive")
    value = Fraction(numerator, denominator)
    if (value.numerator, value.denominator) != (numerator, denominator):
        raise ValueError("serialised numbers must be reduced")
    return value


def ser_vec(v: Vec) -> list[list[int]]:
    return [ser(v[0]), ser(v[1])]


def add(a: Vec, b: Vec) -> Vec:
    return (a[0] + b[0], a[1] + b[1])


def sub(a: Vec, b: Vec) -> Vec:
    return (a[0] - b[0], a[1] - b[1])


def scale(a: Vec, k: Fraction) -> Vec:
    return (a[0] * k, a[1] * k)


def dot(a: Vec, b: Vec) -> Fraction:
    return a[0] * b[0] + a[1] * b[1]


def cross(a: Vec, b: Vec) -> Fraction:
    """z component of a x b."""
    return a[0] * b[1] - a[1] * b[0]


def exact(value: object) -> Fraction:
    """Assert a computed value stayed exact (int | Fraction, never float)."""
    if isinstance(value, bool) or not isinstance(value, (int, Fraction)):
        raise TypeError(f"a physical value became {type(value).__name__}")
    return Fraction(value)
