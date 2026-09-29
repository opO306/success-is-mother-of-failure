"""C1-B1 point prover generator V0.2: finds certificates for checker V2. UNTRUSTED.

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
                 (prover_budget:*) or the checker REFUSED (checker_refused:<limit>) or the certificate could not be
                 serialized (serialization_limit). This says NOTHING about truth: Lemmas A+B give a finite certificate,
                 not one inside today's limits.
  UNREPRESENTABLE the exact value is decided but the output profile cannot hold it: checker V2's own enclosure lies
                 strictly inside a cell outside FX(96,80) (reason output_out_of_range). No precision helps. Designer
                 verdict 2026-09-30. For the C1-B1 profile (dt = 40, R >= r_min) the D4 bound |J| <= 1277.3 a.u. shows
                 it cannot happen; the runtime wrapper treats it there as a contract violation. Synthetic inputs and
                 arbitrary dt_kick can return it normally.
  ANOMALY        the certificate is rejected for a reason that is neither not_separated nor a wrong raw HINT (e.g.
                 exp_condition), or the trusted enclosure and the checker disagree on a raw the enclosure chose.
                 Recorded and STOPPED: never retried into FOUND.

V0.1 (designer verdicts D1 and D2, 2026-09-30; completeness audit docs/active/C1B1_POINT_PROVER_COMPLETENESS_AUDIT_V0.md).
The untrusted estimate only gives HINTS: a starting N and a first raw to try. The raw is DECIDED by checker V2's own
enclosure: a raw_mismatch on a hinted raw is not an anomaly but a wrong hint, and the prover then computes the enclosure
J at the same N (K2.enclosure, the checker's own computation) and takes the raw of the cell that strictly contains J, or
grows N if J straddles a boundary. An estimate that fails or lands outside the output range stops nothing: the prover
goes straight to the enclosure. So finding a certificate no longer depends on mpmath being right (audit hole H1), and an
estimate never ends a run (hole H2). The final verdict is still one check_certificate call on the certificate returned.

V0.2 (designer verdict H-B, 2026-09-30). The exp ORDERS are also only hinted by floats. _certified_plan computes the
exact x intervals exactly as checker V2 will (same sqrt interval, same outward products) and certifies every hinted
order with exact rational inequalities; a hint that fails, or exceeds the closed-form fallback order n_fb, is replaced
by n_fb, which is itself certified. So the properties the completeness lemma needs (n + 2 > x_hi, a certified tail,
a certified zero_floor floor, n = O(P + x)) never rest on floating point:
  full       n + 2 > x_hi and U_n(x_hi) = t_(n+1)(x_hi) (n+2)/(n+2-x_hi) <= 2^-(P + FULL_SLACK) S_n(x_hi): a RELATIVE
             tail, both sides bounded by one-sided rounded chains at CERT_BITS (t upward, S_n downward)
  zero_floor 1/S_n(x_lo) <= n!/x_lo^n <= e n (n/(e x_lo))^n <= 2^-(P + ZERO_SLACK)   [n! <= e n^(n+1/2) e^-n, n >= 1]
  fallback   full with n_fb = max(ceil(2 e x_hi), P + FULL_SLACK) + 1  (then e x_hi/(n+1) <= 1/2 and the tail
             bound is below 2^-(n+1) * 1.23 < 2^-(P+FULL_SLACK) <= 2^-(P+FULL_SLACK) S_n); certified like any other.
e is bracketed by the rationals E_LO < e < E_UP. The certifier only chooses orders; checker V2 still decides.

STEPS. (1) classify NOT_A_DECISION; (2) HINT: estimate y = J / ulp and its distance d (in ulps) to the nearest half-ulp
boundary with mpmath at a doubling precision until two precisions agree to well within d; hinted raw m = floor(y + 1/2);
(3) sqrt bits N = round64(d_bits + y_bits + n_margin) (128 without a hint), work bits P = N + guard, exp mode/order per
rate from float estimates; (4) with a hint: one checker V2 call; VALID ends it, not_separated grows N by 3/2,
raw_mismatch drops the hint; (5) without a hint: the enclosure at this N decides the raw (or N grows), then one checker
call; (6) anything else ends the run.

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
UNREPRESENTABLE = "UNREPRESENTABLE"
E_LO, E_UP = Fraction(27182, 10000), Fraction(27183, 10000)        # E_LO < e < E_UP
FULL_SLACK, ZERO_SLACK = 32, 72                                     # certified targets 2^-(P+32), 2^-(P+72)
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
    checker's fingerprint ties to the frozen C1-A source). The generator's own transcription, used for HINTS only: if it
    is wrong the checker answers raw_mismatch and the enclosure decides instead (V0.1); it can cost time, never truth."""
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


def _exact_x(dr, N, P):
    """The exp arguments x = r * rate EXACTLY as checker V2's _compute builds them (same R^2, sqrt interval, products)."""
    R2 = Fraction(sum(v * v for v in dr), 1 << (2 * K2.POSITION_FRAC_BITS))
    r = K2._sqrt_interval(R2, N)
    return [r.mul(K2._const(rate, P), P) for rate in K2.rates()]


CERT_BITS = 64                                                      # mantissa bits of the certifier's own bounds


def _full_ok(n, x_hi, P):
    """Exact: n + 2 > x_hi and the RELATIVE Taylor tail U_n(x_hi) <= 2^-(P + FULL_SLACK) * S_n(x_hi), which is what
    makes the enclosure of e^-x narrow relative to e^-x itself. Both sides are bounded by one-sided rounded chains
    (like checker V2's series): t_up >= t_{n+1}(x_hi) = x_hi^(n+1)/(n+1)!, s_lo <= S_n(x_hi); all terms are positive."""
    if n < 1 or not n + 2 > x_hi:
        return False
    y_up, y_lo = K2.up(x_hi, CERT_BITS), K2.down(x_hi, CERT_BITS)
    t_up = t_lo = s_lo = Fraction(1)
    for k in range(1, n + 1):
        t_up = K2.up(t_up * y_up / k, CERT_BITS)
        t_lo = K2.down(t_lo * y_lo / k, CERT_BITS)
        s_lo = K2.down(s_lo + t_lo, CERT_BITS)
    t_up = K2.up(t_up * y_up / (n + 1), CERT_BITS)
    return t_up * Fraction(n + 2) / (n + 2 - x_hi) <= s_lo / (1 << (P + FULL_SLACK))


def _zero_ok(n, x_lo, P):
    """Exact: 1/S_n(v) <= 2^-(P + ZERO_SLACK) for every v >= x_lo."""
    if n < 1 or not x_lo > 0:
        return False
    q = K2.up(Fraction(n) / (E_LO * x_lo), 64)                     # q >= n / (e x_lo)
    if q >= 1:
        return False
    return E_UP * n * q ** n <= Fraction(1, 1 << (P + ZERO_SLACK))


def _fallback_order(x_hi, P):
    return max(math.ceil(2 * E_UP * x_hi), P + FULL_SLACK) + 1


def _certified_plan(dr, N, P, info=None):
    """The exp plan with every order certified exactly (H-B). The float plan is only a hint."""
    R = math.sqrt(sum(float(v) * float(v) for v in dr)) / 2.0 ** K2.POSITION_FRAC_BITS
    hint = _exp_plan(R, N, P)
    out, hinted, fallback = [], 0, 0
    for (mode, n), x in zip(hint, _exact_x(dr, N, P)):
        n_fb = _fallback_order(x.hi, P)
        ok = (type(n) is int and n <= n_fb
              and (_full_ok(n, x.hi, P) if mode == "full" else mode == "zero_floor" and _zero_ok(n, x.lo, P)))
        if ok:
            out.append((mode, n))
            hinted += 1
            continue
        if not _full_ok(n_fb, x.hi, P):                             # the closed form is certified like any order
            raise _Stop(ANOMALY, "order_certification_failed")
        out.append(("full", n_fb))
        fallback += 1
    if info is not None:
        info["orders_hinted"], info["orders_fallback"] = hinted, fallback
    return out


def _certificate(dr, k, dt, raw, N, P, info=None):
    plan = _certified_plan(dr, N, P, info)
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


def _cell(J):
    """The raw m whose OPEN rounding cell ((2m-1)/2, (2m+1)/2) * 2^-80 strictly contains the enclosure J, else None.
    The same strict test as checker V2's _decide_raw (it must never choose a raw the checker would not accept)."""
    ulp = Fraction(1, 1 << K2.OUT_FRAC)
    m = math.floor(J.lo / ulp + Fraction(1, 2))
    if (2 * m - 1) * ulp / 2 < J.lo and J.hi < (2 * m + 1) * ulp / 2:
        return m
    return None


def _enclosure(dr, k, dt, N, P, limits):
    """Checker V2's own enclosure J of the exact impulse at (N, P). The raw written into the throw-away certificate is
    irrelevant to J (0). Raises _Stop for a refusal (EXHAUSTED) or a structural rejection (ANOMALY)."""
    cert = _certificate(dr, k, dt, 0, N, P)
    try:
        return K2.enclosure(cert, limits)
    except K2._Refused as e:
        raise _Stop(EXHAUSTED, "checker_refused:" + str(e))
    except MemoryError:
        raise _Stop(EXHAUSTED, "checker_refused:memory_limit")
    except K2._Invalid as e:
        raise _Stop(ANOMALY, "enclosure_" + str(e))


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
        m = est["m"]                                                    # a HINT, never a decision (D1)
        N = _round_up(max(128, est["dist_bits"] + est["y_bits"] + budget.n_margin))
    except _Stop as s:                                                  # D2: a failed estimate ends nothing
        est, m, N = {"hint": None, "estimate_failed": s.reason}, None, 128
    decided = False                                                     # True once the enclosure chose m
    for _ in range(budget.max_attempts):
        if out_of_time():
            return ProverResult(EXHAUSTED, "prover_budget:time", attempts=attempts, estimate=est, budget=budget)
        if N > budget.max_sqrt_bits:
            return ProverResult(EXHAUSTED, "prover_budget:sqrt_bits", attempts=attempts, estimate=est, budget=budget)
        P = N + budget.guard_bits
        try:
            if m is None:                                               # the trusted enclosure decides the raw
                J, stats = _enclosure(dr, component, dt, N, P, limits)
                m = _cell(J)
                attempts.append({"sqrt_bits": N, "work_bits": P, "verdict": "ENCLOSURE",
                                 "reason": "not_separated" if m is None else "cell", "seconds": stats["seconds"]})
                if m is None:
                    N = _grow(N)
                    continue
                if not RAW_MIN <= m <= RAW_MAX:
                    return ProverResult(UNREPRESENTABLE, "output_out_of_range", attempts=attempts, estimate=est,
                                        budget=budget)
                decided = True
            info = {}
            cert = _certificate(dr, component, dt, m, N, P, info)
        except ValueError:                        # a number too long for Python's int/str conversion limit
            return ProverResult(EXHAUSTED, "serialization_limit", attempts=attempts, estimate=est, budget=budget)
        except _Stop as s:
            return ProverResult(s.status, s.reason, attempts=attempts, estimate=est, budget=budget)
        res = K2.check_certificate(cert, limits)
        attempts.append({"sqrt_bits": N, "work_bits": P, "verdict": res.status, "reason": res.reason,
                         "seconds": res.stats["seconds"], **info})
        if res.valid:
            return ProverResult(FOUND, "checker_valid", raw=res.raw, certificate=cert, checker=res, attempts=attempts,
                                estimate=est, budget=budget)
        if res.status == "REFUSED":
            return ProverResult(EXHAUSTED, "checker_refused:" + res.reason, certificate=cert, checker=res,
                                attempts=attempts, estimate=est, budget=budget)
        if res.reason == "not_separated":
            N = _grow(N)
            continue
        if res.reason == "raw_mismatch" and not decided:                # a wrong HINT: let the enclosure decide (D1)
            est["hint_rejected"] = m
            m = None
            continue
        if decided:
            return ProverResult(ANOMALY, "enclosure_checker_disagree:" + res.reason, certificate=cert, checker=res,
                                attempts=attempts, estimate=est, budget=budget)
        return ProverResult(ANOMALY, "checker_" + res.reason, certificate=cert, checker=res, attempts=attempts,
                            estimate=est, budget=budget)
    return ProverResult(EXHAUSTED, "prover_budget:attempts", attempts=attempts, estimate=est, budget=budget)


def verify_found(result, limits=None):
    """Re-decide a FOUND result's certificate with checker V2: True only if it is VALID with the reported raw."""
    if not result.found or result.certificate is None:
        return False
    res = K2.check_certificate(result.certificate, limits)
    return res.valid and res.raw == result.raw
