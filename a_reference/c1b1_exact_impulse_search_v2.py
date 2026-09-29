"""Certificate PARAMETER SEARCH for checker V2 -- a test-side helper, NOT the point prover, NOT trusted.

Chooses sqrt bits N, work bits P = N + guard and one exp mode/order per exponential with floating-point estimates, then
lets checker V2 decide. A bad guess costs time only: the checker answers not_separated / REFUSED.

guard (the only "guard bits" anywhere): P = N + guard_bits. Default 96 = 64 bits of margin for the absolute width
needed at N bits + about 16 bits for the number of roundings in one evaluation (a few thousand, log2 ~ 12) + 16 bits of
cancellation reserve. It is a heuristic of this untrusted helper; checker V2 is sound for every P (design section 4).
"""
import math
from fractions import Fraction

import a_reference.c1b1_exact_impulse_checker_v2 as K2
import a_reference.c1b1_exact_impulse_search as S1

GUARD_BITS = 96


def make_certificate(dr_raw, component, dt_kick, raw, sqrt_bits, work_bits=None, plan=None):
    R = S1._R_estimate(dr_raw)
    work_bits = work_bits if work_bits is not None else sqrt_bits + GUARD_BITS
    plan = plan or S1.exp_plan(R, work_bits)
    return {
        "format": K2.FORMAT, "method": K2.METHOD,
        "model": {"contract": K2.CONTRACT, "parameter_fingerprint": K2.FROZEN_FINGERPRINT, "retardation": True},
        "input": {"position_frac_bits": K2.POSITION_FRAC_BITS, "dr_raw": [str(int(v)) for v in dr_raw],
                  "component": component, "dt_kick": str(Fraction(dt_kick))},
        "output": {"width": K2.OUT_WIDTH, "frac_bits": K2.OUT_FRAC, "raw": str(int(raw))},
        "proof": {"sqrt_bits": str(sqrt_bits), "work_bits": str(work_bits),
                  "exp": [{"rate": str(rate), "mode": mode, "order": str(order)}
                          for rate, (mode, order) in zip(K2.rates(), plan)]},
    }


def find_certificate(dr_raw, component, dt_kick, raw, start_bits=128, max_bits=2048, limits=None, guard=None):
    """Doubling search over the sqrt bits (work bits follow). Returns (certificate, Result) of the last attempt."""
    bits, last = start_bits, None
    while bits <= max_bits:
        cert = make_certificate(dr_raw, component, dt_kick, raw, bits,
                                None if guard is None else bits + guard)
        res = K2.check_certificate(cert, limits)
        last = (cert, res)
        if res.valid or res.status == "REFUSED" or res.reason not in ("not_separated",):
            return last
        bits *= 2
    return last
