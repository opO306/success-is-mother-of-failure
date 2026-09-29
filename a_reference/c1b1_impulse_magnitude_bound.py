"""C1-B1 D4: a rigorous upper bound of |J_k| for every impulse the executor can decide, against the FX(96,80) range.

Designer verdict D4 (2026-09-30, completeness audit docs/active/C1B1_POINT_PROVER_COMPLETENESS_AUDIT_V0.md): prove, do not
assume, that no impulse the executor decides can come near the FX(96,80) output-overflow edge, so that overflow-edge STOPs
are outside the supported domain of the point prover.

CLAIM. For every relative position with R^2 >= r_min^2 (the executor's own guard: impulse() raises PhysicsDomainExceeded
before any rounding otherwise) and R < 2^49 bohr (every FX(96,48) relative position: |dr_raw| < 2^96, so R < sqrt(3) 2^48),
and dt_kick = 20 (the C1-B1 profile dt = 40, c1b1_domain_contract.PROFILE; both kicks of a step use dt/2):
    |J_k| = |V'(R)| * |dr_k| / R * dt_kick <= B * 20,     B = sup_{R in [r_min, 2^49]} |V'(R)|  (|dr_k| <= R exactly).
The script computes an upper bound B_up >= B and checks B_up * 20 < (2^95 - 1/2) * 2^-80, the magnitude where FX(96,80)
rounding would leave the range. The margin is reported.

METHOD. Checker V2's trusted interval evaluation of V' (K2._dv, outward dyadic rounding, retardation ON, the frozen
constants bound by the fingerprint) over a COVER of [r_min, 2^49] by closed intervals R: 1/64 bohr steps up to 32 bohr,
then factor 5/4 steps. Each exponential enclosure is K2._exp_interval over the whole x interval: 'full' (Taylor with the
remainder bound, order n > x_hi) while x_hi <= 600, else 'zero_floor' (e^-x in [0, 1/S_n(x_lo)], sound for any n). The
natural interval extension OVERestimates |V'| on an interval; that is harmless for an upper bound. Every interval's
enclosure contains V'(R) for all R in it (inclusion isotonicity), so max over the cover of max(|lo|, |hi|) >= B.

WHAT THIS DOES NOT CLAIM. Nothing about rounding decisions, liveness, A-EV or the executor's own evaluator (which is not
used). It relies on checker V2's formula transcription, the same trust as every V2 certificate. dt other than 40 is outside.
"""
import json
import sys
import time
from fractions import Fraction as Q

import a_reference.c1b1_exact_impulse_checker_v2 as K2

R_MIN = Q(K2.R_MIN_ANGSTROM) / Q(K2.BOHR_ANGSTROM)
R_TOP = Q(1 << 49)
DT_KICK = Q(20)
EDGE = (Q(1 << 95) - Q(1, 2)) / (1 << K2.OUT_FRAC)     # |J| at or beyond this can round outside FX(96,80)
P_BITS = 96
FULL_X_MAX = 600
ZERO_FLOOR_ORDER = 40


def cover():
    """Closed intervals [a, b] covering [R_MIN, R_TOP] without gaps (consecutive intervals share an end point)."""
    out, a = [], R_MIN
    while a < 32:
        b = min(Q(int(a * 64) + 1, 64), Q(32))
        out.append((a, b))
        a = b
    while a < R_TOP:
        b = min(a * Q(5, 4), R_TOP)
        out.append((a, b))
        a = b
    return out


def _exp(x, ctx):
    if x.hi <= FULL_X_MAX:
        n = int(x.hi) + 80
        return K2._exp_interval(x, "full", n, P_BITS, ctx)
    return K2._exp_interval(x, "zero_floor", ZERO_FLOOR_ORDER, P_BITS, ctx)


def dv_enclosure(a, b, ctx):
    """An interval containing V'(R) for every R in [a, b] (checker V2's own evaluation)."""
    r = K2._Iv(a, b)
    xs = [r.mul(K2._const(rate, P_BITS), P_BITS) for rate in K2.rates()]
    E = [_exp(x, ctx) for x in xs]
    return K2._dv(r, E, P_BITS, ctx)


TARGET = Q(64)                       # split an interval while its |V'| bound exceeds this (true sup |V'| is about 2.93)
MIN_WIDTH = Q(1, 1 << 24)            # never split below this width; a leaf above TARGET then simply stays in the max


def _leaves(a, b, ctx):
    """Adaptive subdivision of [a, b]: the natural interval extension overestimates |V'| in proportion to the interval
    width (large cancelling terms near r_min), so an interval whose bound exceeds TARGET is halved. The leaves are still a
    gap-free cover of [a, b] (the halves share their midpoint), so the maximum over them is still an upper bound."""
    stack, out = [(a, b)], []
    while stack:
        lo, hi = stack.pop()
        dv = dv_enclosure(lo, hi, ctx)
        m = max(abs(dv.lo), abs(dv.hi))
        if m > TARGET and hi - lo > MIN_WIDTH:
            mid = (lo + hi) / 2
            stack += [(mid, hi), (lo, mid)]
            continue
        out.append((lo, hi, m))
    return out


def bound():
    ctx = K2._Ctx(K2.Limits(seconds_max=10 ** 9, bits_max=10 ** 9, order_max=10 ** 6))
    assert K2.fingerprint() == K2.FROZEN_FINGERPRINT
    best, where, n = Q(0), None, 0
    last_b = None
    for a, b in cover():
        assert last_b is None or a == last_b, "the cover has a gap"
        last_b = b
        prev = a
        for lo, hi, m in _leaves(a, b, ctx):
            assert lo == prev, "the subdivision has a gap"
            prev = hi
            n += 1
            if m > best:
                best, where = m, (lo, hi)
        assert prev == b, "the subdivision does not reach the interval end"
    assert cover()[0][0] == R_MIN and last_b == R_TOP
    return best, where, n


def main(out_path=None):
    t0 = time.time()
    B_up, where, n = bound()
    J_up = B_up * DT_KICK
    res = {"kind": "rigorous_bound", "r_min_bohr": str(R_MIN), "r_top_bohr": str(R_TOP), "intervals": n,
           "dt_kick": str(DT_KICK), "work_bits": P_BITS,
           "sup_abs_dV_upper": float(B_up), "sup_abs_dV_upper_exact": str(B_up),
           "attained_on_interval": [float(where[0]), float(where[1])],
           "J_upper": float(J_up), "edge": float(EDGE), "ratio_J_upper_to_edge": float(J_up / EDGE),
           "holds": J_up < EDGE, "seconds": round(time.time() - t0, 1)}
    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(res, f, indent=1)
    print(json.dumps(res, indent=1))
    return 0 if res["holds"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else None))
