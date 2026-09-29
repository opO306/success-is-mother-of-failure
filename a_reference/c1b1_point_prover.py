"""C1-B1 point prover generator V0: finds certificates for checker V2. UNTRUSTED.

Design: docs/active/C1B1_POINT_PROVER_DESIGN_V0.md. The prover is a generator, not a judge. It may use anything to guess
a certificate (mpmath floats, heuristics); only checker V2 decides. **The one and only success is
`check_certificate(certificate) == VALID(raw)`**, and a FOUND result always carries that checker verdict.

WHAT IT MAY NOT DO (designer principles 1-3, 2026-09-29)
  * call the executor evaluator (C._model, C._decide, C.impulse) or touch MAX_PRECISION_BITS: this is a separate
    correctness path, not a program that raises the executor's 16384-bit cap;
  * declare success itself, or return a raw that the checker did not prove;
  * retry an ANOMALY until it becomes FOUND.

RESULTS
  FOUND          certificate + raw, with the checker's VALID Result attached.
  NOT_A_DECISION the executor asks no rounding question here, decided EXACTLY from the input alone: dr_k = 0,
                 dt = 0, R < r_min, position outside the profile. Nothing estimated ever leads here.
  EXHAUSTED      no certificate within the operational limits YET. Either the prover's own budget ran out
                 (prover_budget:*, estimate_budget) or the checker REFUSED (checker_refused:<limit>) or the
                 certificate could not be serialized (serialization_limit) or the UNTRUSTED estimate put the value
                 outside the FX(96,80) output range (estimate_out_of_output_range: no certificate says so, and a real
                 output overflow is the executor's own terminal refusal, never a prover case). This says NOTHING
                 about truth: Lemmas A+B give a finite certificate, not one inside today's limits.
  ANOMALY        the prover's guess and the checker contradict (the checker says raw_mismatch, or any INVALID reason
                 other than not_separated). Recorded and STOPPED: never retried into FOUND, because a silent retry
                 would hide a disagreement between two implementations.

STEPS. (1) classify NOT_A_DECISION; (2) estimate y = J / ulp and its distance d (in ulps) to the nearest half-ulp
boundary with mpmath at a doubling precision until two precisions agree to well within d; (3) raw m = floor(y + 1/2);
(4) sqrt bits N = round64(d_bits + y_bits + n_margin), work bits P = N + guard, exp mode/order per rate from float
estimates; (5) one checker V2 call; on not_separated grow N by 3/2 and retry; anything else ends the run.

The numbers n_margin (40) and guard (96) are heuristics of THIS untrusted generator: N must exceed d_bits + y_bits by
about 87 measured bits (the enclosure width is about |y| 2^-N * 2^7 ulps), plus slack for the rounding growth; P = N + guard
keeps the rounding term below the sqrt term. Checker V2 is sound for every N and P; a bad guess only costs attempts.
The budget values are operational defaults recorded with each result, not physics.

DETERMINISM. No randomness, no clock-dependent branch except the optional seconds budget (which can only cut a run
short: availability). Same input and budget give the same certificate bytes.
"""
import math
import time
from fractions import Fraction

import mpmath as mp

import a_reference.c1b1_exact_impulse_checker_v2 as K2

FOUND, NOT_A_DECISION, EXHAUSTED, ANOMALY = "FOUND", "NOT_A_DECISION", "EXHAUSTED", "ANOMALY"
LN2 = math.log(2)
RAW_MIN, RAW_MAX = -(1 << (K2.OUT_WIDTH - 1)), (1 << (K2.OUT_WIDTH - 1)) - 1


class Budget:
    """The prover's own operational budget. Exceeding it gives EXHAUSTED(prover_budget:*), never a verdict on truth."""

    def __init__(self, max_attempts=16, max_sqrt_bits=65536, estimate_max_bits=1 << 17, seconds_max=None,
                 n_margin=40, guard_bits=96):
        self.max_attempts, self.max_sqrt_bits, self.estimate_max_bits = max_attempts, max_sqrt_bits, estimate_max_bits
        self.seconds_max, self.n_margin, self.guard_bits = seconds_max, n_margin, guard_bits

    def as_dict(self):
        return dict(vars(self))


class ProverResult:
    def __init__(self, status, reason, raw=None, certificate=None, checker=None, attempts=None, estimate=None,
                 budget=None):
        self.status, self.reason, self.raw, self.certificate = status, reason, raw, certificate
        self.checker, self.attempts, self.estimate = checker, attempts or [], estimate
        self.budget = None if budget is None else budget.as_dict()

    def __repr__(self):
        return f"ProverResult({self.status}, {self.reason}, raw={self.raw}, attempts={len(self.attempts)})"

    @property
    def found(self):
        return self.status == FOUND


class _Stop(Exception):
    def __init__(self, status, reason):
        self.status, self.reason = status, reason


# --- step 2: the mpmath estimate (untrusted) ---------------------------------------------------------------------

def _mpf(q):
    q = Fraction(q)
    return mp.mpf(q.numerator) / q.denominator


def _dv_mp(R2):
    """dV/dR (retardation ON) at R = sqrt(R2) with mpmath, from the constant tables of checker V2 (which the
    checker's fingerprint ties to the frozen C1-A source). The generator's own transcription: if it is wrong the checker
    answers raw_mismatch and the run ends as ANOMALY."""
    R = mp.sqrt(_mpf(R2))
    Nr = 1 + sum(_mpf(a) * R ** (m + 1) for m, a in enumerate(K2.RET_A))
    Dn = 1 + sum(_mpf(b) * R ** (m + 1) for m, b in enumerate(K2.RET_B))
    dNr = sum(_mpf(a) * (m + 1) * R ** m for m, a in enumerate(K2.RET_A))
    dDn = sum(_mpf(b) * (m + 1) * R ** m for m, b in enumerate(K2.RET_B))
    g, dg = Nr / Dn, (dNr * Dn - Nr * dDn) / (Dn * Dn)
    total = mp.mpf(0)
    for name in ("BO", "REL", "QED"):
        for alpha, coefs in K2.SHORT[name]:
            al = _mpf(alpha)
            P = sum(_mpf(c) * R ** i for i, c in coefs.items())
            dP = sum(_mpf(c) * i * R ** (i - 1) for i, c in coefs.items() if i)
            total += mp.exp(-al * R) * (dP - al * P)
        eta, kadd, cs = K2.LONG[name]
        eta = _mpf(eta)
        x, ex = eta * R, mp.exp(-eta * R)
        kmin = min(cs)
        for k, c in cs.items():
            n = 2 * k + kadd
            T = ex * sum(x ** i / mp.factorial(i) for i in range(n + 1))
            base = eta * ex * x ** n / mp.factorial(n)
            if name == "BO" and k == kmin:
                D, dD = g - T, base + dg
            elif name == "REL" and k == kmin:
                D, dD = -T, base
            else:
                D, dD = 1 - T, base
            total += -_mpf(c) * (dD * R ** (-2 * k) - 2 * k * D * R ** (-2 * k - 1))
    return total, R


def _y_at(dr, k, dt, p_bits):
    """y = J_k / ulp at p_bits of working precision (mpmath), J = -dV/dR * dr_k * dt / R."""
    with mp.workdps(int(p_bits * 0.30103) + 20):
        R2 = Fraction(sum(v * v for v in dr), 1 << (2 * K2.POSITION_FRAC_BITS))
        dv, R = _dv_mp(R2)
        J = -dv * _mpf(Fraction(dr[k], 1 << K2.POSITION_FRAC_BITS) * dt) / R
        return J * mp.mpf(2) ** K2.OUT_FRAC


def _split(y):
    """(m, dist) with m = floor(y + 1/2) the nearest raw and dist the distance (in ulps) of y to the nearest half-ulp
    boundary. Boundaries are the integers of t = y + 1/2."""
    t = y + mp.mpf(1) / 2
    m = int(mp.floor(t))
    f = t - m
    return m, min(f, 1 - f)


def _estimate(dr, k, dt, budget):
    """Doubling-precision estimate. Accepts when two successive precisions agree to well within the distance to the
    nearest boundary. Returns dict(m, dist_bits, y_bits, precision). Raises _Stop(EXHAUSTED, ...) when the estimate
    runs out of budget or lands outside the output range (an estimate is not evidence of an overflow)."""
    p_bits, prev = 512, None
    while True:
        y = _y_at(dr, k, dt, p_bits)
        with mp.workdps(int(p_bits * 0.30103) + 20):
            if abs(y) > mp.mpf(2) ** (K2.OUT_WIDTH + 1):
                raise _Stop(EXHAUSTED, "estimate_out_of_output_range")
            if prev is not None:
                m, dist = _split(y)
                err = max(abs(y - prev), abs(y) * mp.mpf(2) ** (-(p_bits // 2 - 8)))
                if dist > 8 * err and dist > 0:
                    if not RAW_MIN <= m <= RAW_MAX:
                        raise _Stop(EXHAUSTED, "estimate_out_of_output_range")
                    dist_bits = max(1, int(mp.ceil(-mp.log(dist, 2))))
                    y_bits = max(0, int(mp.ceil(mp.log(abs(y), 2)))) if abs(y) > 1 else 0
                    return {"m": m, "dist_bits": dist_bits, "y_bits": y_bits, "precision_bits": p_bits}
            prev = y
        p_bits *= 2
        if p_bits > budget.estimate_max_bits:
            raise _Stop(EXHAUSTED, "estimate_budget")


# --- step 4: certificate parameters ------------------------------------------------------------------------------

def _zero_floor_order(x_lo, bits):
    need = bits * LN2 + 1.0
    n, limit = 1, int(x_lo) + 2
    while n <= limit:
        if n * math.log(x_lo) - math.lgamma(n + 1) >= need:
            return n
        n += 1
    return None


def _full_order(x_lo, x_hi, bits):
    n = max(0, math.ceil(x_hi) - 1)
    need = bits * LN2
    while True:
        gap = n + 2 - x_hi
        if gap > 0:
            log_tail = (n + 1) * math.log(x_hi) - math.lgamma(n + 2) + math.log((n + 2) / gap) - x_lo
            if log_tail <= -need:
                return n
        n += 1 if n < 64 else max(1, n // 200)


def _exp_plan(R, N, P):
    """One (mode, order) per exponential. zero_floor where exp(-x) is far below the working precision, else full."""
    bits = P + 48
    width = R * 2.0 ** -N
    plan = []
    for rate in K2.rates():
        lam = float(rate)
        x_lo, x_hi = lam * R, lam * (R + width)
        n = _zero_floor_order(x_lo, bits + 40) if x_lo > 8 else None
        plan.append(("zero_floor", n) if n is not None else ("full", _full_order(x_lo, x_hi, bits)))
    return plan


def _certificate(dr, k, dt, raw, N, P):
    R = math.sqrt(sum(float(v) * float(v) for v in dr)) / 2.0 ** K2.POSITION_FRAC_BITS
    plan = _exp_plan(R, N, P)
    return {
        "format": K2.FORMAT, "method": K2.METHOD,
        "model": {"contract": K2.CONTRACT, "parameter_fingerprint": K2.FROZEN_FINGERPRINT, "retardation": True},
        "input": {"position_frac_bits": K2.POSITION_FRAC_BITS, "dr_raw": [str(int(v)) for v in dr],
                  "component": k, "dt_kick": str(Fraction(dt))},
        "output": {"width": K2.OUT_WIDTH, "frac_bits": K2.OUT_FRAC, "raw": str(int(raw))},
        "proof": {"sqrt_bits": str(N), "work_bits": str(P),
                  "exp": [{"rate": str(rate), "mode": mode, "order": str(order)}
                          for rate, (mode, order) in zip(K2.rates(), plan)]},
    }


def _round_up(n, step=64):
    return -(-n // step) * step


def _grow(N):
    return _round_up(N * 3 // 2 + 1)


# --- step 1 and the driver ---------------------------------------------------------------------------------------

def _classify(dr, k, dt):
    if not (isinstance(dr, (list, tuple)) and len(dr) == 3 and all(type(v) is int for v in dr)):
        raise ValueError("dr_raw must be three Python integers")
    if k not in (0, 1, 2):
        raise ValueError("component must be 0, 1 or 2")
    if any(abs(v) >= 1 << K2.OUT_WIDTH for v in dr):            # |dr_raw| < 2^96 for FX(96,48) positions
        return "outside_position_profile"
    if dr[k] == 0:
        return "zero_component"
    if Fraction(dt) == 0:
        return "zero_kick"
    R2 = Fraction(sum(v * v for v in dr), 1 << (2 * K2.POSITION_FRAC_BITS))
    bohr = Fraction(K2.BOHR_ANGSTROM)
    if R2 * bohr * bohr < Fraction(K2.R_MIN_ANGSTROM) ** 2:
        return "below_r_min"
    return None


def prove(dr_raw, component, dt_kick, budget=None, limits=None):
    """Find a checker-V2 certificate for J_component of the relative position dr_raw (FX(96,48) raws) and kick interval
    dt_kick. Returns a ProverResult; FOUND only with the checker's VALID verdict attached."""
    budget = budget or Budget()
    t0 = time.monotonic()
    dr, dt = tuple(dr_raw), Fraction(dt_kick)
    why = _classify(dr, component, dt)
    if why:
        return ProverResult(NOT_A_DECISION, why, budget=budget)
    attempts = []

    def out_of_time():
        return budget.seconds_max is not None and time.monotonic() - t0 > budget.seconds_max
    try:
        est = _estimate(dr, component, dt, budget)
    except _Stop as s:
        return ProverResult(s.status, s.reason, attempts=attempts, budget=budget)
    m = est["m"]
    N = _round_up(max(128, est["dist_bits"] + est["y_bits"] + budget.n_margin))
    for _ in range(budget.max_attempts):
        if out_of_time():
            return ProverResult(EXHAUSTED, "prover_budget:time", attempts=attempts, estimate=est, budget=budget)
        if N > budget.max_sqrt_bits:
            return ProverResult(EXHAUSTED, "prover_budget:sqrt_bits", attempts=attempts, estimate=est, budget=budget)
        P = N + budget.guard_bits
        try:
            cert = _certificate(dr, component, dt, m, N, P)
        except ValueError:                        # a number too long for Python's int/str conversion limit
            return ProverResult(EXHAUSTED, "serialization_limit", attempts=attempts, estimate=est, budget=budget)
        res = K2.check_certificate(cert, limits)
        attempts.append({"sqrt_bits": N, "work_bits": P, "verdict": res.status, "reason": res.reason,
                         "seconds": res.stats["seconds"]})
        if res.valid:
            return ProverResult(FOUND, "checker_valid", raw=res.raw, certificate=cert, checker=res, attempts=attempts,
                                estimate=est, budget=budget)
        if res.status == "REFUSED":
            return ProverResult(EXHAUSTED, "checker_refused:" + res.reason, certificate=cert, checker=res,
                                attempts=attempts, estimate=est, budget=budget)
        if res.reason == "not_separated":
            N = _grow(N)
            continue
        return ProverResult(ANOMALY, "checker_" + res.reason, certificate=cert, checker=res, attempts=attempts,
                            estimate=est, budget=budget)
    return ProverResult(EXHAUSTED, "prover_budget:attempts", attempts=attempts, estimate=est, budget=budget)


def verify_found(result, limits=None):
    """Re-decide a FOUND result's certificate with checker V2: True only if it is VALID with the reported raw."""
    if not result.found or result.certificate is None:
        return False
    res = K2.check_certificate(result.certificate, limits)
    return res.valid and res.raw == result.raw
