"""Proof-only 1D PES bounds and point-evaluator endpoint error bounds.

No subdivision, measured trajectory, or changed execution arithmetic.
Mathematical range and numerical endpoint error are different quantities.
"""
from dataclasses import dataclass
from fractions import Fraction as Q
from math import factorial
from hashlib import sha256
from pathlib import Path

import a_numeric.exp as E
from a_numeric.exp import enclosure
from a_reference import ar2_lang2024 as L
from a_reference import c1b1_two_atom as C
from a_reference import c1b1_outer_bound as B
from a_reference import c1b1_outer_bootstrap as O

MATH_BITS = 512
_SOURCE_HASHES = {
    C: 'e5889e8af2901eaa594b9b593a2c47048c61a4b4811bb0af04fb6c5d25c32c0e',
    E: '33522adcb4cc07cac5c65ec26187993d0b43efd214a7b846c2a207605108d58b',
}
_BINDINGS = tuple((module, name, getattr(module, name)) for module, names in (
    (C, ('_model', '_model_R', '_mul', '_add', '_neg', '_const', '_scale',
         '_div_small', '_div_pos', '_exp_neg', '_const_cache', '_exp_enclosure', '_decide')),
    (E, ('enclosure', '_taylor')),
) for name in names)


def proof_guard():
    O._model_guard()
    if (C.START_PRECISION_BITS, C.MAX_PRECISION_BITS, B.H, B.UX, B.UP, C.LN2_UPPER) != (
            128, 16384, Q(40), Q(1, 1 << 48), Q(1, 1 << 80), Q(6932, 10000)):
        raise O.NotCertified('numeric proof assumptions changed')
    if any(getattr(module, name) is not original for module, name, original in _BINDINGS):
        raise O.NotCertified('live evaluator changed')
    for module, expected in _SOURCE_HASHES.items():
        if sha256(Path(module.__file__).read_bytes().replace(b'\r\n', b'\n')).hexdigest() != expected:
            raise O.NotCertified('source-bound endpoint error proof needs re-audit')


def precision_guard(bits):
    if type(bits) is not int or bits not in tuple(128 << k for k in range(8)):
        raise O.NotCertified('live finite precision schedule required')


def _up(x, bits):
    scaled = Q(x)*(1 << bits)
    return Q(-(-scaled.numerator//scaled.denominator), 1 << bits)


@dataclass(frozen=True)
class Iv:
    lo: Q
    hi: Q

    def __post_init__(self):
        object.__setattr__(self, 'lo', B.exact(self.lo))
        object.__setattr__(self, 'hi', B.exact(self.hi))
        if self.lo > self.hi:
            raise ValueError('reversed interval')

    @classmethod
    def of(cls, x):
        return x if isinstance(x, cls) else cls(Q(x), Q(x))

    @classmethod
    def outward(cls, lo, hi):
        return cls(-_up(-lo, MATH_BITS), _up(hi, MATH_BITS))

    def __add__(self, other):
        other = Iv.of(other)
        return Iv.outward(self.lo+other.lo, self.hi+other.hi)

    __radd__ = __add__

    def __neg__(self):
        return Iv(-self.hi, -self.lo)

    def __sub__(self, other):
        return self+-Iv.of(other)

    def __mul__(self, other):
        other = Iv.of(other)
        values = [x*y for x in (self.lo, self.hi) for y in (other.lo, other.hi)]
        return Iv.outward(min(values), max(values))

    __rmul__ = __mul__

    def reciprocal(self):
        if self.lo <= 0 <= self.hi:
            raise O.NotCertified('zero denominator in axis proof')
        return Iv.outward(1/self.hi, 1/self.lo)

    def __pow__(self, n):
        if n < 0:
            return self.reciprocal()**-n
        if self.lo < 0:
            raise O.NotCertified('positive-radius powers required')
        return Iv.outward(self.lo**n, self.hi**n)

    @property
    def magnitude(self):
        return max(abs(self.lo), abs(self.hi))


def exp_range(argument):
    """Mathematical exp(-x), independent of the execution precision."""
    if argument.lo < 0:
        raise O.NotCertified('nonnegative exponential argument required')
    def endpoint(x):
        if x >= MATH_BITS*C.LN2_UPPER:
            return Q(0), Q(1, 1 << MATH_BITS)
        k = max(0, x.numerator.bit_length()-x.denominator.bit_length()+1)+8
        lo, hi = enclosure(-x, MATH_BITS, k)
        return Q(lo, 1 << MATH_BITS), Q(hi, 1 << MATH_BITS)
    return Iv(endpoint(argument.hi)[0], endpoint(argument.lo)[1])


def _padd(a, b):
    out = dict(a)
    for k, v in b.items():
        out[k] = out.get(k, Q(0))+v
    return {k: v for k, v in out.items() if v}


def _pmul(a, b):
    out = {}
    for i, x in a.items():
        for j, y in b.items():
            out[i+j] = out.get(i+j, Q(0))+x*y
    return {k: v for k, v in out.items() if v}


def _pd(a):
    return {k-1: k*v for k, v in a.items() if k and v}


def _pscale(a, value):
    return {k: v*value for k, v in a.items() if v*value}


def _eval(a, radius):
    return sum((v*radius**k for k, v in a.items()), Iv.of(0))


def _representation():
    """Exact identity: rational retardation + inverse powers + exp Laurent terms."""
    numerator = {0: Q(1), **{i+1: v for i, v in enumerate(L.RET_A)}}
    denominator = {0: Q(1), **{i+1: v for i, v in enumerate(L.RET_B)}}
    inverse, exponentials = {}, {}
    leading = None
    for name, (shorts, (eta, cs, kadd)) in L.COMPONENTS.items():
        for alpha, coefficients in shorts.values():
            exponentials[alpha] = _padd(exponentials.get(alpha, {}), coefficients)
        for k, c in cs.items():
            power = 2*k
            if k == min(cs) and name == 'BO':
                if power != 6:
                    raise O.NotCertified('retardation proof requires leading R^-6')
                leading = _pscale(numerator, -c)
            elif not (k == min(cs) and name == 'REL'):
                inverse[-power] = inverse.get(-power, Q(0))-c
            coefficients = {i-power: c*eta**i/factorial(i) for i in range(power+kadd+1)}
            exponentials[eta] = _padd(exponentials.get(eta, {}), coefficients)
    if leading is None or any(v <= 0 for v in denominator.values()):
        raise O.NotCertified('positive retardation denominator required')
    return leading, denominator, inverse, exponentials


def axis_derivatives(a, b):
    """V' and V'' on [a,b], using coefficient signs to remove dependency inflation.

    A rational term with nonnegative derivative numerator is monotone; exact
    endpoint bounds are then valid for its entire interval. No point sampling.
    """
    proof_guard()
    a, b = B.exact(a), B.exact(b)
    if not 20 <= a <= b:
        raise O.NotCertified('finite positive outer radius required')
    r = Iv(a, b)
    pol, den, inverse, exponentials = _representation()
    polynomials = [pol]
    for n in range(3):
        term = _pmul({1: Q(1)}, _pmul(den, _pd(polynomials[-1])))
        weight = _padd(_pscale(den, 6+n), _pmul({1: Q(1)}, _pscale(_pd(den), 1+n)))
        polynomials.append(_padd(term, _pscale(_pmul(weight, polynomials[-1]), -1)))
    def rational(n):
        def at(radius):
            return _eval(polynomials[n], radius)*(radius**(6+n)*_eval(den, radius)**(1+n)).reciprocal()
        next_pol = polynomials[n+1]
        if all(v >= 0 for v in next_pol.values()):
            return Iv(at(Iv.of(a)).lo, at(Iv.of(b)).hi)
        if all(v <= 0 for v in next_pol.values()):
            return Iv(at(Iv.of(b)).lo, at(Iv.of(a)).hi)
        return at(r)
    result = []
    for n in (1, 2):
        total = rational(n)
        inv = dict(inverse)
        for _ in range(n):
            inv = _pd(inv)
        total += _eval(inv, r)
        for lam, coefficients in exponentials.items():
            for _ in range(n):
                coefficients = _padd(_pd(coefficients), _pscale(coefficients, -lam))
            total += exp_range(lam*r)*_eval(coefficients, r)
        result.append(total)
    return tuple(result)


def exp_endpoint_error(argument, input_error, bits):
    """Uniform error of actual _exp_neg endpoints, not the parent range width.

    Taylor: <=ceil(M/8)+1 terms, term enclosure width <=2 ulps,
    remainder <=4 ulps per endpoint, range-reduction input error <=1 ulp.
    Squaring on [0,2] is 4-Lipschitz; the strict error<1 guard closes induction.
    Shortcut [0,1] has <=1 ulp error and is included by this larger bound.
    """
    if argument.lo-input_error < 0:
        raise O.NotCertified('numerical EXP argument can become negative')
    upper_raw = G_ceil((argument.hi+input_error)*(1 << bits))
    kmax = max(0, upper_raw.bit_length()-bits+1)+8
    terms = -(-bits//8)+1
    error = Q(4**kmax*(2*terms+10), 1 << bits)
    if error >= 1:
        raise O.NotCertified('EXP endpoint error induction not closed')
    return input_error+error


def G_ceil(x):
    return -(-x.numerator//x.denominator)


@dataclass(frozen=True)
class Num:
    """At each fixed R, every numerical endpoint is within e of its true value."""
    v: Iv
    e: Q
    bits: int

    @classmethod
    def exact(cls, x, bits):
        return cls(Iv.of(x), Q(0), bits)

    @classmethod
    def const(cls, x, bits):
        return cls(Iv.of(x), Q(1, 1 << bits), bits)

    def _new(self, v, e):
        return Num(v, _up(e, self.bits+128), self.bits)

    def __add__(self, other):
        return self._new(self.v+other.v, self.e+other.e)

    def __neg__(self):
        return Num(-self.v, self.e, self.bits)

    def __mul__(self, other):
        e = self.v.magnitude*other.e+other.v.magnitude*self.e+self.e*other.e+Q(1, 1 << self.bits)
        return self._new(self.v*other.v, e)

    def scale(self, c):
        return self._new(self.v*c, abs(c)*self.e+Q(1, 1 << self.bits))

    def div(self, other):
        lower = other.v.lo
        if lower <= other.e:
            raise O.NotCertified('positive numerical denominator not proved')
        error = self.e/(lower-other.e)+self.v.magnitude*other.e/(lower*(lower-other.e))+Q(1, 1 << self.bits)
        return self._new(self.v*other.v.reciprocal(), error)

    def exp(self):
        return self._new(exp_range(self.v), exp_endpoint_error(self.v, self.e, self.bits))


def evaluator_ratio_error(a, b, bits):
    """Follow the actual _model_R arithmetic for each dyadic R on a 1D axis.

    At M>=48 its sqrt(R^2) input is exact. This does not cover oblique or
    arbitrary 3D inputs. Physical ranges use 512-bit outward arithmetic.
    """
    proof_guard()
    precision_guard(bits)
    a, b = B.exact(a), B.exact(b)
    if not 20 <= a <= b:
        raise O.NotCertified('finite axis interval required')
    r = Num.exact(Iv(a, b), bits)
    one, zero = Num.exact(1, bits), Num.exact(0, bits)
    powers = {0: one, 1: r}
    for k in range(2, 7):
        powers[k] = powers[k-1]*r
    inverse = {k: Num(r.v**-k, Q(1, 1 << bits), bits) for k in range(1, 18)}
    def power(k):
        return powers[k] if k >= 0 else inverse[-k]
    dv = zero
    for name, (shorts, (eta, cs, kadd)) in L.COMPONENTS.items():
        for alpha, coefficients in shorts.values():
            ex = (Num.const(alpha, bits)*r).exp()
            pol = dpol = zero
            for k, c in coefficients.items():
                pol += power(k).scale(c)
                if k:
                    dpol += power(k-1).scale(c*k)
            dv += ex*(dpol+-pol.scale(alpha))
        x = Num.const(eta, bits)*r
        ex = x.exp()
        piece = total = one
        done = 0
        for k, c in sorted(cs.items()):
            n = 2*k+kadd
            for i in range(done+1, n+1):
                piece = (piece*x).scale(Q(1, i))
                total += piece
            done = n
            tail, derivative = ex*total, (ex*piece).scale(eta)
            if k == min(cs) and name == 'BO':
                num = den = one
                dnum = dden = zero
                for m, value in enumerate(L.RET_A):
                    num += powers[m+1].scale(value)
                    dnum += powers[m].scale(value*(m+1))
                for m, value in enumerate(L.RET_B):
                    den += powers[m+1].scale(value)
                    dden += powers[m].scale(value*(m+1))
                g = num.div(den)
                dg = (dnum*den+-(num*dden)).div(den*den)
                damp, derivative = g+-tail, derivative+dg
            elif k == min(cs) and name == 'REL':
                damp = -tail
            else:
                damp = one+-tail
            dv += -(derivative*power(-2*k)).scale(c)
            dv += (damp*power(-2*k-1)).scale(c*2*k)
    return (-dv)*inverse[1]


def axis_impulse_error(a, b, bits):
    ratio = evaluator_ratio_error(a, b, bits)
    # The executor scales the ratio by the EXACT q_k*h/2 without a further
    # dyadic rounding. Absolute endpoint error therefore scales by b*h/2.
    return ratio.e*b*B.H/2
