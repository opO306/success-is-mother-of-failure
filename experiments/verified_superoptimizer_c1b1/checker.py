"""Independent endpoint/rounding checker for Pilot 1.

No reference evaluator, candidate, or a_numeric imports. The checker loads only
frozen rational parameters. It evaluates the specified directed grid program
with Fraction arithmetic, not the candidate's sign-specialized integer helpers.
This checks implementation equivalence, not a new independent physics model.
"""
from __future__ import annotations
import json
from dataclasses import dataclass
from fractions import Fraction as Q
from math import ceil, floor, isqrt
from pathlib import Path

CONSTANTS_PATH = Path(__file__).with_name('frozen_constants.json')
DATA = json.loads(CONSTANTS_PATH.read_text())
RMIN = Q(DATA['r_min_bohr'])
COMPONENTS = DATA['components']
RET_A = list(map(Q, DATA['ret_a']))
RET_B = list(map(Q, DATA['ret_b']))


@dataclass(frozen=True)
class Cell:
    lower: Q
    upper: Q
    bits: int

    def __post_init__(self):
        if self.lower > self.upper:
            raise ValueError('reversed checker interval')

    @property
    def grid(self):
        return 2 ** self.bits

    @classmethod
    def cover(cls, lower, upper, bits):
        scale = 2 ** bits
        return cls(Q(floor(Q(lower) * scale), scale), Q(ceil(Q(upper) * scale), scale), bits)

    @classmethod
    def constant(cls, value, bits):
        return cls.cover(Q(value), Q(value), bits)

    @classmethod
    def from_raw(cls, raw, bits):
        return cls(Q(raw[0], 2 ** bits), Q(raw[1], 2 ** bits), bits)

    def raw(self):
        a, b = self.lower * self.grid, self.upper * self.grid
        assert a.denominator == b.denominator == 1
        return int(a), int(b)

    def add(self, other):
        return Cell(self.lower + other.lower, self.upper + other.upper, self.bits)

    def negative(self):
        return Cell(-self.upper, -self.lower, self.bits)

    def subtract(self, other):
        return self.add(other.negative())

    def multiply(self, other):
        products = [x * y for x in (self.lower, self.upper) for y in (other.lower, other.upper)]
        return Cell.cover(min(products), max(products), self.bits)

    def scale(self, exact):
        endpoints = [self.lower * exact, self.upper * exact]
        return Cell.cover(min(endpoints), max(endpoints), self.bits)

    def divide(self, other):
        assert other.lower > 0
        quotients = [x / y for x in (self.lower, self.upper) for y in (other.lower, other.upper)]
        return Cell.cover(min(quotients), max(quotients), self.bits)

    def divide_integer(self, n):
        return Cell.cover(self.lower / n, self.upper / n, self.bits)


def reference_taylor_program(Y, bits):
    """Independent rational implementation of the REF Taylor rounding rules."""
    scale = 2 ** bits
    abs_y = Q(abs(Y), scale)
    terms = [scale, scale]
    sums = [scale, scale]
    index = 0
    while terms[1] > 1 or index == 0:
        index += 1
        terms = [floor(Q(terms[0]) * abs_y / index), ceil(Q(terms[1]) * abs_y / index)]
        if Y < 0 and index % 2 == 1:
            sums = [sums[0] - terms[1], sums[1] - terms[0]]
        else:
            sums = [sums[0] + terms[0], sums[1] + terms[1]]
    allowance = 2 * terms[1] + 2
    return sums[0] - allowance, sums[1] + allowance


def scalar_exp_program(end, bits):
    scale = 2 ** bits
    reduction = max(0, end.bit_length() - bits + 1) + 8
    reduced = -Q(end, 2 ** reduction)
    lower = reference_taylor_program(floor(reduced), bits)[0]
    upper = reference_taylor_program(ceil(reduced), bits)[1]
    lower = max(0, lower)
    for _ in range(reduction):
        lower = floor(Q(lower * lower, scale))
        upper = ceil(Q(upper * upper, scale))
    return lower, upper


def exponential(cell: Cell) -> Cell:
    if cell.lower >= cell.bits * Q(6932, 10000):
        return Cell.from_raw((0, 1), cell.bits)
    a, b = cell.raw()
    return Cell.from_raw((scalar_exp_program(b, cell.bits)[0], scalar_exp_program(a, cell.bits)[1]), cell.bits)


def radius_raw(r_squared: Q, bits: int):
    # A distinct formulation using the integer floor of the exact scaled value.
    scaled = r_squared * 2 ** (2 * bits)
    root = isqrt(floor(scaled))
    if Q(root * root) == scaled:
        return root, root
    return root, root + 1


def model_r(raw_radius: tuple[int, int], bits: int, ret: bool = True, *, exp_function=None):
    exp_function = exponential if exp_function is None else exp_function
    r = Cell.from_raw(raw_radius, bits)
    zero, one = Cell.constant(0, bits), Cell.constant(1, bits)
    powers = {0: one, 1: r}
    for n in range(2, 7):
        powers[n] = powers[n - 1].multiply(r)
    for n in range(1, 18):
        powers[-n] = Cell.cover(1 / r.upper ** n, 1 / r.lower ** n, bits)
    contributions = []
    for component in COMPONENTS:
        for alpha_text, coeffs in component['short']:
            alpha = Q(alpha_text)
            damping = exp_function(Cell.constant(alpha, bits).multiply(r))
            polynomial, derivative = zero, zero
            for i, ctext in coeffs:
                c = Q(ctext)
                if c == 0:
                    continue
                polynomial = polynomial.add(powers[i].scale(c))
                if i:
                    derivative = derivative.add(powers[i - 1].scale(i * c))
            term = damping.multiply(derivative.subtract(polynomial.scale(alpha)))
            contributions.append(term)
        eta = Q(component['eta'])
        x = Cell.constant(eta, bits).multiply(r)
        e = exp_function(x)
        term, partial_sum = one, one
        completed = 0
        for position, (k, coefficient_text) in enumerate(component['long']):
            coefficient = Q(coefficient_text)
            degree = 2 * k + component['kadd']
            for index in range(completed + 1, degree + 1):
                term = term.multiply(x).divide_integer(index)
                partial_sum = partial_sum.add(term)
            completed = degree
            tail = e.multiply(partial_sum)
            derivative = e.multiply(term).scale(eta)
            if ret and position == 0 and component['name'] == 'BO':
                numerator, denominator = one, one
                d_numerator, d_denominator = zero, zero
                for power, a in enumerate(RET_A, 1):
                    numerator = numerator.add(powers[power].scale(a))
                    d_numerator = d_numerator.add(powers[power - 1].scale(power * a))
                for power, b in enumerate(RET_B, 1):
                    denominator = denominator.add(powers[power].scale(b))
                    d_denominator = d_denominator.add(powers[power - 1].scale(power * b))
                correction = numerator.divide(denominator)
                correction_derivative = d_numerator.multiply(denominator).subtract(
                    numerator.multiply(d_denominator)).divide(denominator.multiply(denominator))
                D = correction.subtract(tail)
                derivative = derivative.add(correction_derivative)
            elif ret and position == 0 and component['name'] == 'REL':
                D = tail.negative()
            else:
                D = one.subtract(tail)
            contributions.append(derivative.multiply(powers[-2 * k]).scale(coefficient).negative())
            contributions.append(D.multiply(powers[-2 * k - 1]).scale(coefficient * 2 * k))
    total = zero
    for part in contributions:
        total = total.add(part)
    return total.raw(), powers[-1].raw()


def model(r_squared, bits, ret=True):
    return model_r(radius_raw(Q(r_squared), bits), bits, ret)


def nearest_integer(exact: Q) -> int:
    low = floor(exact)
    distance = exact - low
    if distance < Q(1, 2):
        return low
    if distance > Q(1, 2):
        return low + 1
    return low if low % 2 == 0 else low + 1


def round_raw(exact: Q, spec: dict):
    """Independent nearest-even profile conversion, returning a tagged outcome."""
    exact = Q(exact)
    kind = spec['kind']
    if kind == 'FX':
        result = nearest_integer(exact * 2 ** spec['frac'])
        limit = 2 ** (spec['width'] - 1)
        return ('value', result) if -limit <= result < limit else ('halt', 'overflow')
    if kind == 'CARRY':
        fine = spec['fine']
        result = nearest_integer(exact * 2 ** fine)
        unit = 2 ** (fine - 48)
        coarse = nearest_integer(Q(result, unit))
        limit = 2 ** (spec['width'] - 1)
        return ('value', (coarse, result - coarse * unit)) if -limit <= coarse < limit else ('halt', 'overflow')
    if kind != 'B64':
        raise ValueError(spec)
    if exact == 0:
        return 'value', 0
    sign = int(exact < 0)
    magnitude = abs(exact)
    # Find a binary exponent using exact comparisons, without host floats.
    exponent = magnitude.numerator.bit_length() - magnitude.denominator.bit_length()
    while magnitude < Q(2) ** exponent:
        exponent -= 1
    while magnitude >= Q(2) ** (exponent + 1):
        exponent += 1
    unit_exponent = max(exponent - 52, -1074)
    significand = nearest_integer(magnitude / (Q(2) ** unit_exponent))
    if significand >= 2 ** 53:
        significand //= 2
        unit_exponent += 1
    if significand >= 2 ** 52:
        field = unit_exponent + 1075
        if field >= 2047:
            return 'halt', 'overflow'
        raw = sign * 2 ** 63 + field * 2 ** 52 + significand - 2 ** 52
    else:
        raw = sign * 2 ** 63 + significand
    return 'value', raw


def g_and_j(dv_raw, inverse_raw, bits, coefficient):
    dv = Cell.from_raw(dv_raw, bits)
    inverse = Cell.from_raw(inverse_raw, bits)
    g = dv.negative().multiply(inverse)
    endpoints = [g.lower * coefficient, g.upper * coefficient]
    return g.raw(), (min(endpoints), max(endpoints))


def impulse(dr, dt_kick, spec, *, model_function=model, cap=16384):
    squared = sum((x * x for x in dr), Q(0))
    if squared < RMIN * RMIN:
        return {'outcome': ('error', 'physics_domain_exceeded'), 'model_bits': [], 'decisions': []}
    cache, model_bits, decisions, raw_results = {}, [], [], []
    for x in dr:
        coefficient = x * dt_kick
        if coefficient == 0:
            raw_results.append(round_raw(Q(0), spec)[1])
            continue
        bits = 128
        axis_steps = []
        decisions.append(axis_steps)
        while bits <= cap:
            if bits not in cache:
                cache[bits] = model_function(squared, bits, True)
                model_bits.append(bits)
            g, (lower, upper) = g_and_j(*cache[bits], bits, coefficient)
            a, b = round_raw(lower, spec), round_raw(upper, spec)
            axis_steps.append({'M': bits, 'lo': str(lower), 'hi': str(upper)})
            if a == b and not (a[0] == 'halt' and lower < 0 < upper):
                if a[0] == 'halt':
                    return {'outcome': a, 'model_bits': model_bits, 'decisions': decisions}
                raw_results.append(a[1])
                break
            bits *= 2
        else:
            return {'outcome': ('error', 'executor_limit_exceeded'), 'model_bits': model_bits, 'decisions': decisions}
    return {'outcome': ('value', tuple(raw_results)), 'model_bits': model_bits, 'decisions': decisions}
