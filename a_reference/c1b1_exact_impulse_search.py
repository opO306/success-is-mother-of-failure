"""Certificate PARAMETER SEARCH for the exact impulse checker -- a test-side helper, NOT the point prover.

The checker (c1b1_exact_impulse_checker) is the only thing trusted. This module guesses parameters (sqrt bits and one
mode/order per exponential) with floating-point estimates, builds a certificate and lets the checker decide. A bad
guess only costs time: the checker answers INVALID/REFUSED and the search doubles the sqrt bits.

It may import the checker's constants (rates); the checker never imports it. The real point prover generator
(step 8 of the plan) is a separate, later piece of work.
"""
import math
from fractions import Fraction

import a_reference.c1b1_exact_impulse_checker as K

_FP = K.FROZEN_FINGERPRINT
LN2 = math.log(2)


def _R_estimate(dr_raw):
    return math.sqrt(sum(float(v) * float(v) for v in dr_raw)) / 2.0 ** K.POSITION_FRAC_BITS


def _zero_floor_order(x_lo, bits):
    """Smallest n with x^n/n! >= 2^bits (so 1/S_n <= 2^-bits), or None if x is too small to ever reach it."""
    need = bits * LN2 + 1.0
    n = 1
    limit = int(x_lo) + 2
    while n <= limit:
        if n * math.log(x_lo) - math.lgamma(n + 1) >= need:
            return n
        n += 1
    return None


def _full_order(x_lo, x_hi, bits):
    """Smallest n >= x_hi-1 whose geometric tail bound is below 2^-bits relative to e^{x_lo}."""
    n = max(0, math.ceil(x_hi) - 1)
    need = bits * LN2
    while True:
        gap = n + 2 - x_hi
        if gap > 0:
            log_tail = (n + 1) * math.log(x_hi) - math.lgamma(n + 2) + math.log((n + 2) / gap) - x_lo
            if log_tail <= -need:
                return n
        n += 1 if n < 64 else max(1, n // 200)


def exp_plan(R, sqrt_bits, extra=48):
    """One (mode, order) per exponential for a given R and sqrt precision."""
    bits = sqrt_bits + extra
    width = R * 2.0 ** -sqrt_bits
    plan = []
    for rate in K.rates():
        lam = float(rate)
        x_lo, x_hi = lam * R, lam * (R + width)
        n = _zero_floor_order(x_lo, bits + 40) if x_lo > 8 else None
        if n is not None:
            plan.append(("zero_floor", n))
        else:
            plan.append(("full", _full_order(x_lo, x_hi, bits)))
    return plan


def make_certificate(dr_raw, component, dt_kick, raw, sqrt_bits, plan=None):
    R = _R_estimate(dr_raw)
    plan = plan or exp_plan(R, sqrt_bits)
    return {
        "format": K.FORMAT, "method": K.METHOD,
        "model": {"contract": K.CONTRACT, "parameter_fingerprint": _FP, "retardation": True},
        "input": {"position_frac_bits": K.POSITION_FRAC_BITS, "dr_raw": [str(int(v)) for v in dr_raw],
                  "component": component, "dt_kick": str(Fraction(dt_kick))},
        "output": {"width": K.OUT_WIDTH, "frac_bits": K.OUT_FRAC, "raw": str(int(raw))},
        "proof": {"sqrt_bits": str(sqrt_bits),
                  "exp": [{"rate": str(rate), "mode": mode, "order": str(order)}
                          for rate, (mode, order) in zip(K.rates(), plan)]},
    }


def find_certificate(dr_raw, component, dt_kick, raw, start_bits=128, max_bits=2048, limits=None):
    """Doubling search over the sqrt bits. Returns (certificate, Result) for the first VALID one, else the last try."""
    bits, last = start_bits, None
    while bits <= max_bits:
        cert = make_certificate(dr_raw, component, dt_kick, raw, bits)
        res = K.check_certificate(cert, limits)
        last = (cert, res)
        if res.valid or res.status == "REFUSED" or res.reason in ("raw_mismatch", "model_binding", "physics_domain",
                                                                   "not_a_decision"):
            return last
        bits *= 2
    return last
