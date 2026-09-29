"""Checker V2 (outward dyadic rounding): primitive soundness, fault injection, V1/executor cross-check, rehearsal.

Soundness first: every rounding must keep new_lo <= old_lo <= true value <= old_hi <= new_hi. A too-wide enclosure
may fail (not_separated); a wrong VALID must never happen. Fault injection mutates the V2 SOURCE TEXT and requires
every mutant to be caught (by a containment test, a size bound, a cross-check, or a reference comparison).
V1 (the trusted reference) is not modified; these tests only compare against it.
"""
import ast
import copy
import types
from fractions import Fraction as Q
from pathlib import Path

import mpmath as mp
import pytest

import a_reference.ar2_lang2024 as L
import a_reference.c1b1_exact_impulse_checker as K1
import a_reference.c1b1_exact_impulse_checker_v2 as K2
import a_reference.c1b1_exact_impulse_crosscheck as XC
import a_reference.c1b1_exact_impulse_search as S1
import a_reference.c1b1_exact_impulse_search_v2 as S2
import a_reference.c1b1_runtime_local_witness as W
import a_reference.c1b1_stress_survey as X
import a_reference.c1b1_two_atom as C

V2_SRC = Path(K2.__file__).read_text(encoding="utf-8")
DT = Q(20)


def _exe(dr, dt=DT):
    return C.impulse(tuple(Q(v, 1 << 48) for v in dr), dt, X.MOM)


def _mutant(*replacements):
    src = V2_SRC
    for old, new in replacements:
        assert src.count(old) == 1, f"mutation target must occur exactly once: {old!r} ({src.count(old)}x)"
        src = src.replace(old, new)
    mod = types.ModuleType("mutant_v2")
    exec(compile(src, "mutant_v2.py", "exec"), mod.__dict__)
    return mod


def _is_dyadic(f):
    d = Q(f).denominator
    return d & (d - 1) == 0


# --- primitive: directed rounding ---------------------------------------------------------------------------------

VALUES = [Q(1, 3), Q(-1, 3), Q(2, 3), Q(-2, 3), Q(7), Q(-7), Q(1), Q(-1), Q(10 ** 40 + 1, 7), Q(-(10 ** 40 + 1), 7),
          Q(1, 10 ** 50), Q(-1, 10 ** 50), Q(3, 1 << 200), Q(-3, 1 << 200), Q((1 << 300) + 1, 3), Q(-((1 << 300) + 1), 3),
          Q(692639712, 100000000), Q(-692639712, 100000000), Q(5, 2), Q(-5, 2), Q(2 ** 64 - 1), Q(-(2 ** 64 - 1)),
          Q(123456789, 987654321), Q(-123456789, 987654321)]
PRECISIONS = (8, 16, 53, 64, 200)


def _rounding_violations(mod):
    bad = 0
    for P in PRECISIONS:
        for x in VALUES:
            try:
                lo, hi = mod.down(x, P), mod.up(x, P)
            except Exception:
                bad += 1
                continue
            a, b = x.numerator, x.denominator
            e = abs(a).bit_length() - b.bit_length() - P - 1
            ok = (lo <= x <= hi and _is_dyadic(lo) and _is_dyadic(hi)
                  and hi - lo <= Q(2) ** (e + 1)                                   # tight: one mantissa step
                  and abs(Q(lo).numerator).bit_length() <= P + 3 + max(0, e)        # bounded mantissa
                  and abs(x) * Q(1, 1 << (P - 1)) >= hi - lo)                      # relative width 2^(1-P)
            bad += not ok
    for P in PRECISIONS:                                                           # small dyadics are kept exactly
        for x in (Q(3, 8), Q(-3, 8), Q(5), Q(-1, 1 << 20)):
            try:
                bad += not (mod.down(x, P) == x == mod.up(x, P))
            except Exception:
                bad += 1
    try:
        bad += not (mod.down(0, 16) == 0 == mod.up(0, 16))
    except Exception:
        bad += 1
    return bad


def test_directed_rounding_is_outward_dyadic_tight_and_bounded():
    assert _rounding_violations(K2) == 0


ROUNDING_FAULTS = {
    "lower rounded up (down = ceiling)": [("    return Fraction((a << -e) // b, 1 << -e)",
                                            "    return Fraction(-((-(a << -e)) // b), 1 << -e)")],
    "upper rounded down (up = down)": [("    return -down(-Fraction(x), P)", "    return down(Fraction(x), P)")],
    "negative direction flipped (truncation towards zero)": [
        ("    return Fraction((a << -e) // b, 1 << -e)",
         "    return Fraction((1 if a > 0 else -1) * (abs(a << -e) // b), 1 << -e)")],
    "large-magnitude branch truncates": [("        return Fraction((a // (b << e)) << e)",
                                          "        return Fraction(((1 if a > 0 else -1) * (abs(a) // (b << e))) << e)")],
    "precision off by many bits": [("    e = abs(a).bit_length() - b.bit_length() - P - 1",
                                    "    e = abs(a).bit_length() - b.bit_length() - P // 2")],
}


@pytest.mark.parametrize("name", list(ROUNDING_FAULTS))
def test_fault_injection_directed_rounding(name):
    assert _rounding_violations(_mutant(*ROUNDING_FAULTS[name])) > 0, f"fault survived: {name}"


# --- primitive: interval operations -------------------------------------------------------------------------------

def _pairs():
    vals = [Q(-7, 3), Q(-1), Q(-1, 5), Q(0), Q(1, 7), Q(2), Q(11, 2), Q(10 ** 20, 3)]
    return [(a, b) for a in vals for b in vals if a <= b]


def _op_violations(mod, P=24):
    """Every rounded V2 op must contain the exact interval result (hence every pointwise result)."""
    bad = 0
    for a1, a2 in _pairs():
        A = mod._Iv(a1, a2)
        try:
            r = A.rnd(P)
            bad += not (r.lo <= a1 and a2 <= r.hi)
            r = A.neg()
            bad += not (r.lo == -a2 and r.hi == -a1)
        except Exception:
            bad += 1
        for b1, b2 in _pairs():
            B = mod._Iv(b1, b2)
            exact = {"add": (a1 + b1, a2 + b2), "sub": (a1 - b2, a2 - b1)}
            prods = (a1 * b1, a1 * b2, a2 * b1, a2 * b2)
            exact["mul"] = (min(prods), max(prods))
            if b1 > 0:
                quots = (a1 / b1, a1 / b2, a2 / b1, a2 / b2)
                exact["div"] = (min(quots), max(quots))
            for op, (lo, hi) in exact.items():
                try:
                    r = getattr(A, op)(B, P) if op in ("mul", "div") else getattr(A, op)(B)
                    bad += not (r.lo <= lo and hi <= r.hi)
                except Exception:
                    bad += 1
    return bad


def test_every_interval_operation_contains_the_exact_result():
    assert _op_violations(K2) == 0
    with pytest.raises(K2._Invalid):
        K2._Iv(1).div(K2._Iv(-1, 1), 16)


OP_FAULTS = {
    "mul drops two endpoint products": [("        p = (self.lo * o.lo, self.lo * o.hi, self.hi * o.lo, self.hi * o.hi)\n"
                                         "        return _Iv(down(min(p), P), up(max(p), P))",
                                         "        p = (self.lo * o.lo, self.hi * o.hi)\n"
                                         "        return _Iv(down(min(p), P), up(max(p), P))")],
    "mul lower end rounded up": [("        return _Iv(down(min(p), P), up(max(p), P))", "        return _Iv(up(min(p), P), up(max(p), P))")],
    "mul upper end rounded down": [("        return _Iv(down(min(p), P), up(max(p), P))", "        return _Iv(down(min(p), P), down(max(p), P))")],
    "div lower end rounded up": [("        return _Iv(down(min(q), P), up(max(q), P))", "        return _Iv(up(min(q), P), up(max(q), P))")],
    "div takes one quotient": [("        return _Iv(down(min(q), P), up(max(q), P))", "        return _Iv(down(q[0], P), up(q[0], P))")],
    "sub without crossing the ends": [("        return _Iv(self.lo - o.hi, self.hi - o.lo)", "        return _Iv(self.lo - o.lo, self.hi - o.hi)")],
    "rnd rounds the lower end up": [("        return _Iv(down(self.lo, P), up(self.hi, P))", "        return _Iv(up(self.lo, P), up(self.hi, P))")],
}


@pytest.mark.parametrize("name", list(OP_FAULTS))
def test_fault_injection_interval_operations(name):
    assert _op_violations(_mutant(*OP_FAULTS[name])) > 0, f"fault survived: {name}"


# --- primitive: sqrt and powers -----------------------------------------------------------------------------------

SQRT_CASES = [Q(4), Q(2), Q(1, 3), Q(6, 5) ** 2, Q(10 ** 30 + 7, 3), Q(2 ** 90 + 1, 2 ** 96), Q(7 ** 20, 4 ** 20)]


def _sqrt_violations(mod):
    bad = 0
    for R2 in SQRT_CASES:
        for N in (2, 7, 64, 300):
            try:
                r = mod._sqrt_interval(R2, N)
                # r.lo may be 0 for tiny R2 at small N (the checker rejects that separately as sqrt_enclosure)
                bad += not (r.lo >= 0 and r.lo * r.lo <= R2 <= r.hi * r.hi and r.hi - r.lo == Q(1, 1 << N))
            except Exception:
                bad += 1
    return bad


def test_sqrt_interval_contains_the_root():
    assert _sqrt_violations(K2) == 0


SQRT_FAULTS = {
    "upper end shrunk to the lower end": [("    return _Iv(Fraction(a, 1 << N), Fraction(a + 1, 1 << N))",
                                           "    return _Iv(Fraction(a, 1 << N), Fraction(a, 1 << N))")],
    "root one step too small": [("    a = math.isqrt(F)\n    return _Iv(Fraction(a, 1 << N)",
                                 "    a = math.isqrt(F) - 1\n    return _Iv(Fraction(a, 1 << N)")],
}


@pytest.mark.parametrize("name", list(SQRT_FAULTS))
def test_fault_injection_sqrt(name):
    assert _sqrt_violations(_mutant(*SQRT_FAULTS[name])) > 0, f"fault survived: {name}"


def _power_violations(mod):
    bad = 0
    for R in (mod._Iv(Q(9, 4), Q(19, 8)), mod._Iv(Q(7), Q(7) + Q(1, 1 << 40)), mod._Iv(Q(1000), Q(1001))):
        try:
            pw = mod._powers(R, 40)
        except Exception:
            return 1
        for i in range(-17, 7):
            lo_true, hi_true = (R.lo ** i, R.hi ** i) if i >= 0 else (R.hi ** i, R.lo ** i)
            bad += not (pw[i].lo <= lo_true and hi_true <= pw[i].hi)
    return bad


def test_powers_and_reciprocals_contain_the_exact_ranges():
    assert _power_violations(K2) == 0


POWER_FAULTS = {
    "reciprocal from the wrong end": [("    inv = _Iv(down(1 / R.hi, P), up(1 / R.lo, P))\n    pw[-1] = inv",
                                       "    inv = _Iv(down(1 / R.lo, P), up(1 / R.lo, P))\n    pw[-1] = inv")],
    "reciprocal upper rounded down": [("    inv = _Iv(down(1 / R.hi, P), up(1 / R.lo, P))\n    pw[-1] = inv",
                                       "    inv = _Iv(down(1 / R.hi, P), down(1 / R.lo, P))\n    pw[-1] = inv")],
}


@pytest.mark.parametrize("name", list(POWER_FAULTS))
def test_fault_injection_powers(name):
    assert _power_violations(_mutant(*POWER_FAULTS[name])) > 0, f"fault survived: {name}"


# --- primitive: exp enclosure -------------------------------------------------------------------------------------

def _mp(q):
    with mp.workdps(450):
        return mp.mpf(q.numerator) / q.denominator


def _mp_exp_neg(q):
    with mp.workdps(450):
        return mp.exp(-_mp(q))


EXP_X = [(Q(1, 7), Q(1, 7) + Q(1, 1 << 30)), (Q(1), Q(1)), (Q(5, 2), Q(5, 2) + Q(1, 1 << 60)), (Q(13), Q(13) + Q(1, 1000)),
         (Q(473, 10), Q(474, 10)), (Q(140), Q(140) + Q(1, 1 << 100))]


def _orders(x_hi):
    n0 = max(0, -(-x_hi.numerator // x_hi.denominator) - 1)
    return [n0, n0 + 3, 2 * n0 + 10, 4 * n0 + 60]


def _exp_violations(mod, precisions=(24, 64, 200)):
    bad = 0
    for P in precisions:
        ctx = mod._Ctx(mod.Limits())
        for x_lo, x_hi in EXP_X:
            x = mod._Iv(x_lo, x_hi)
            for n in _orders(x_hi):
                for mode in ("full", "zero_floor"):
                    try:
                        iv = mod._exp_interval(x, mode, n, P, ctx)
                        ok = (_mp(iv.lo) <= _mp_exp_neg(x_hi) and _mp_exp_neg(x_lo) <= _mp(iv.hi) and iv.lo >= 0
                              and _is_dyadic(iv.lo) and _is_dyadic(iv.hi))
                    except Exception:
                        ok = False
                    bad += not ok
    return bad


def test_exp_enclosure_contains_exp_for_every_mode_order_and_precision():
    assert _exp_violations(K2) == 0


def test_exp_enclosure_width_shrinks_with_precision_and_order():
    ctx = K2._Ctx(K2.Limits())
    x = K2._Iv(Q(13), Q(13))
    widths = [(lambda iv: iv.hi - iv.lo)(K2._exp_interval(x, "full", n, P, ctx)) for n, P in ((20, 32), (60, 64), (200, 300))]
    assert widths[0] > widths[1] > widths[2]
    assert widths[2] < _mp_exp_neg_q(Q(13)) * Q(1, 1 << 280)


def _mp_exp_neg_q(q):
    with mp.workdps(450):
        return Q(int(mp.floor(mp.exp(-_mp(q)) * mp.mpf(2) ** 600)) + 1, 1 << 600)


def test_exp_condition_violation_is_invalid():
    ctx = K2._Ctx(K2.Limits())
    with pytest.raises(K2._Invalid):
        K2._exp_interval(K2._Iv(Q(9)), "full", 6, 64, ctx)


EXP_FAULTS = {
    "lower chain rounds its terms up": [("        t = down(t * y / k, P)\n        S = down(S + t, P)",
                                         "        t = up(t * y / k, P)\n        S = down(S + t, P)")],
    "lower chain rounds its sum up": [("        t = down(t * y / k, P)\n        S = down(S + t, P)",
                                       "        t = down(t * y / k, P)\n        S = up(S + t, P)")],
    "upper chain rounds its terms down": [("        t = up(t * y / k, P)\n        S = up(S + t, P)",
                                           "        t = down(t * y / k, P)\n        S = up(S + t, P)")],
    "upper chain rounds its sum down": [("        t = up(t * y / k, P)\n        S = up(S + t, P)",
                                         "        t = up(t * y / k, P)\n        S = down(S + t, P)")],
    "tail bound dropped": [("    U_hi = up(t_hi * (n + 2) / (n + 2 - x_hi), P)", "    U_hi = 0")],
    "upper end from the wrong end of x": [("    S_lo = _series_lower(x.lo, n, P, ctx)", "    S_lo = _series_lower(x.hi, n, P, ctx)")],
    "lower end from the wrong end of x": [("    S_hi, t_hi = _series_upper(x.hi, n, P, ctx)", "    S_hi, t_hi = _series_upper(x.lo, n, P, ctx)")],
}


@pytest.mark.parametrize("name", list(EXP_FAULTS))
def test_fault_injection_exp_enclosure(name):
    assert _exp_violations(_mutant(*EXP_FAULTS[name])) > 0, f"fault survived: {name}"


# Step-wise directions. A single wrong-direction rounding at the END of the exp enclosure is hidden from the pointwise
# containment test above by the slack of the upstream series roundings (it is "only sometimes" unsound). So every
# step is also checked against its EXACT pre-rounding value: exact S_n, t_{n+1}, U_n computed in plain rationals.

def _exact_series(y, n):
    t = S = Q(1)
    for k in range(1, n + 1):
        t = t * y / k
        S += t
    return S, t * y / (n + 1)


SERIES_Y = [Q(1, 3), Q(1), Q(7, 3), Q(13), Q(473, 10), Q(99, 7)]


def _chain_violations(mod):
    bad = 0
    ctx = mod._Ctx(mod.Limits())
    for y in SERIES_Y:
        for n in (int(y) + 1, int(y) + 7, 3 * int(y) + 20):
            for P in (16, 40, 120):
                S, t1 = _exact_series(y, n)
                try:
                    lo = mod._series_lower(y, n, P, ctx)
                    hi, t_hi = mod._series_upper(y, n, P, ctx)
                    bad += not (lo <= S <= hi and t1 <= t_hi)
                except Exception:
                    bad += 1
    return bad


def _combine_violations(mod):
    """_exp_combine with EXACT series inputs: upper >= 1/S_n(x_lo), lower <= 1/(S_n + U_n)(x_hi)."""
    bad = 0
    for x in (Q(1, 3), Q(1), Q(7, 3), Q(13), Q(99, 7)):
        for n in (int(x) + 1, int(x) + 4, 3 * int(x) + 20):
            S, t1 = _exact_series(x, n)
            U = t1 * (n + 2) / (n + 2 - x)
            for P in (16, 40, 120):
                try:
                    iv = mod._exp_combine("full", n, x, S, S, t1, P)
                    zf = mod._exp_combine("zero_floor", n, x, S, None, None, P)
                    bad += not (iv.lo <= 1 / (S + U) and iv.hi >= 1 / S and zf.lo == 0 and zf.hi >= 1 / S)
                except Exception:
                    bad += 1
    return bad


def test_exp_steps_round_in_the_right_direction_against_exact_values():
    assert _chain_violations(K2) == 0
    assert _combine_violations(K2) == 0


STEP_FAULTS = {
    "exp lower end rounded up": [("    lower = down(1 / (S_hi + U_hi), P)", "    lower = up(1 / (S_hi + U_hi), P)")],
    "exp upper end rounded down": [("    upper = up(1 / S_lo, P)", "    upper = down(1 / S_lo, P)")],
    "tail bound rounded down": [("    U_hi = up(t_hi * (n + 2) / (n + 2 - x_hi), P)", "    U_hi = down(t_hi * (n + 2) / (n + 2 - x_hi), P)")],
    "tail geometric factor dropped": [("    U_hi = up(t_hi * (n + 2) / (n + 2 - x_hi), P)", "    U_hi = up(t_hi, P)")],
    "last tail term rounded down": [("    t1 = up(t * y / (n + 1), P)", "    t1 = down(t * y / (n + 1), P)")],
    "lower chain term rounded up": [("        t = down(t * y / k, P)\n        S = down(S + t, P)",
                                     "        t = up(t * y / k, P)\n        S = down(S + t, P)")],
    "upper chain sum rounded down": [("        t = up(t * y / k, P)\n        S = up(S + t, P)",
                                      "        t = up(t * y / k, P)\n        S = down(S + t, P)")],
}


@pytest.mark.parametrize("name", list(STEP_FAULTS))
def test_fault_injection_exp_steps(name):
    mod = _mutant(*STEP_FAULTS[name])
    assert _chain_violations(mod) + _combine_violations(mod) > 0, f"fault survived: {name}"


# --- size bound: numbers stay O(work_bits) (the reason V2 exists) --------------------------------------------------

def test_intermediate_numbers_stay_bounded_by_the_work_precision():
    """Mantissas stay within P+4 bits; whole numbers (mantissa plus the exponent of tiny values) stay O(P)."""
    dr = XC._dr(4.4, (0.6, 0.6, 0.5))
    raw = _exe(dr)[0]
    for N in (128, 512, 1024):
        cert = S2.make_certificate(dr, 0, DT, raw, N)
        P = int(cert["proof"]["work_bits"])
        J, st = K2.enclosure(cert)
        assert st["max_mantissa_bits"] <= P + 4, (N, P, st)
        assert st["max_bits"] <= 3 * P + 200, (N, P, st)


ROUNDING_REMOVED = {
    "series term rounding removed": [("        t = down(t * y / k, P)\n        S = down(S + t, P)",
                                      "        t = t * y / k\n        S = down(S + t, P)")],
    "series sum rounding removed": [("        t = up(t * y / k, P)\n        S = up(S + t, P)",
                                     "        t = up(t * y / k, P)\n        S = S + t")],
}


@pytest.mark.parametrize("name", list(ROUNDING_REMOVED))
def test_fault_injection_a_removed_rounding_step_breaks_the_size_bound_not_soundness(name):
    """Removing a rounding keeps the enclosure sound (exact is inside the rounded) but lets numbers grow like V1."""
    mod = _mutant(*ROUNDING_REMOVED[name])
    assert _exp_violations(mod, precisions=(64,)) == 0                      # still sound
    dr = XC._dr(4.4, (0.6, 0.6, 0.5))
    cert = S2.make_certificate(dr, 0, DT, _exe(dr)[0], 512)
    P = int(cert["proof"]["work_bits"])
    J, st = mod.enclosure(cert)
    assert st["max_mantissa_bits"] > P + 4, "the size bound test must see the missing rounding"


# --- independence and binding -------------------------------------------------------------------------------------

def test_v2_imports_only_the_standard_library_and_nothing_of_v1_or_the_executor():
    tree = ast.parse(V2_SRC)
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0
            imported.add((node.module or "").split(".")[0])
    assert imported == {"fractions", "hashlib", "json", "math", "time"}
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)} | {n.attr for n in ast.walk(tree)
                                                                          if isinstance(n, ast.Attribute)}
    assert not (names & {"_model", "_model_R", "_exp_enclosure", "impulse", "_decide", "a_reference", "a_numeric"})


def test_v2_constants_and_fingerprint_equal_the_frozen_source():
    assert K2.fingerprint() == L.parameter_fingerprint() == K2.FROZEN_FINGERPRINT
    for name in ("BO", "REL", "QED"):
        short, (eta, cs, kadd) = L.COMPONENTS[name]
        for j, (alpha, coefs) in enumerate(K2.SHORT[name], start=1):
            assert Q(alpha) == short[j][0] and {i: Q(c) for i, c in coefs.items()} == short[j][1]
        assert (Q(K2.LONG[name][0]), K2.LONG[name][1], {k: Q(c) for k, c in K2.LONG[name][2].items()}) == (eta, kadd, cs)
    assert tuple(Q(a) for a in K2.RET_A) == L.RET_A and tuple(Q(b) for b in K2.RET_B) == L.RET_B


def test_v1_is_untouched_by_this_work():
    """V1 stays the reference: its source hash is pinned to the trusted e9b30eb version."""
    import hashlib
    data = Path(K1.__file__).read_bytes().replace(b"\r\n", b"\n")
    assert hashlib.sha256(data).hexdigest() == V1_SHA256


V1_SHA256 = "52e669e0bdd9e3e85e3e448afb194bd30ea765aebc79a07fc46b897d49b2a116"


# --- honest samples and verdict tests -----------------------------------------------------------------------------

def _honest(R, d, comp, dt=DT):
    dr = XC._dr(R, d)
    raw = _exe(dr, dt)[comp]
    cert, res = S2.find_certificate(dr, comp, dt, raw)
    assert res.valid and res.raw == raw, res
    return cert, raw


@pytest.fixture(scope="module")
def honest_small():
    return _honest(5.0, (0.55, 0.7, 0.3), 0)


def _set(cert, path, value):
    c = copy.deepcopy(cert)
    node = c
    for p in path[:-1]:
        node = node[p]
    node[path[-1]] = value
    return c


NEGATIVES = [
    (("output", "raw"), lambda c: str(int(c["output"]["raw"]) + 1), "raw_mismatch"),
    (("output", "raw"), lambda c: str(int(c["output"]["raw"]) - 1), "raw_mismatch"),
    (("proof", "work_bits"), lambda c: "7", "work_bits"),
    (("proof", "work_bits"), lambda c: "01", "bad_integer:work_bits"),
    (("format",), lambda c: K1.FORMAT, "format"),
    (("method",), lambda c: K1.METHOD, "format"),
    (("model", "parameter_fingerprint"), lambda c: "0" * 64, "model_binding"),
    (("input", "dr_raw"), lambda c: ["0"] + c["input"]["dr_raw"][1:], "not_a_decision"),
    (("input", "dr_raw"), lambda c: [str(1 << 48), "0", "0"], "physics_domain"),
    (("proof", "exp", 3, "rate"), lambda c: "3/1", "exp_rate"),
]


@pytest.mark.parametrize("path,make,reason", NEGATIVES)
def test_negative_certificates_are_invalid(honest_small, path, make, reason):
    cert, _ = honest_small
    res = K2.check_certificate(_set(cert, path, make(cert)))
    assert (res.status, res.reason) == ("INVALID", reason)


def test_a_v1_certificate_is_not_a_v2_certificate_and_the_reverse(honest_small):
    cert, raw = honest_small
    v1 = S1.make_certificate([int(x) for x in cert["input"]["dr_raw"]], 0, DT, raw, 128)
    assert K2.check_certificate(v1).status == "INVALID"
    assert K1.check_certificate(cert).status == "INVALID"


def test_limits_give_refused_and_never_change_the_truth(honest_small):
    cert, raw = honest_small
    P = int(cert["proof"]["work_bits"])
    for lim, reason in ((K2.Limits(work_bits_max=P - 1), "work_limit"), (K2.Limits(sqrt_bits_max=1), "sqrt_limit"),
                        (K2.Limits(order_max=1), "order_limit"), (K2.Limits(seconds_max=-1), "time_limit"),
                        (K2.Limits(bits_max=10), "size_limit")):
        res = K2.check_certificate(cert, lim)
        assert (res.status, res.reason) == ("REFUSED", reason)
    assert K2.check_certificate(cert, K2.Limits(work_bits_max=P)).raw == raw


def test_small_work_precision_fails_safely_and_never_gives_a_wrong_valid():
    """'Guard bits removed' (work_bits = sqrt_bits or far less): only not_separated or the right raw, never another."""
    for R, d, k in ((2.4, (1, 0.3, 0.2), 0), (7.11, (0.6, 0.7, 0.4), 1), (40.0, (0.2, 0.3, 1), 2), (900.0, (1, 0.1, 0.4), 0)):
        dr = XC._dr(R, d)
        raw = _exe(dr)[k]
        for N, P in ((128, 128), (128, 64), (128, 32), (128, 16), (64, 8)):
            for claim in (raw, raw + 1, raw - 1):
                res = K2.check_certificate(S2.make_certificate(dr, k, DT, claim, N, P))
                assert res.status in ("VALID", "INVALID")
                if res.status == "VALID":
                    assert res.raw == raw == claim, (R, N, P, claim)


# --- cross-check: V2 = V1 = executor ------------------------------------------------------------------------------

CROSS = [(2.3, (1, 0.2, 0.1)), (2.6, (-0.5, 0.8, -0.3)), (4.4, (0.6, 0.6, 0.5)), (7.1, (0.6, 0.7, 0.4)),
         (7.1129, (-1, 0, 0)), (9.3, (0.1, -1, 0.2)), (20.0, (0.3, -0.9, 0.2)), (61.0, (-0.3, -0.3, 1)),
         (450.0, (0.9, 0.3, -0.2)), (2400.0, (0.5, -0.5, 0.7)), (9000.0, (1, 0.2, 0.1)), (2.0 ** 30, (0.3, 0.3, 0.9))]


@pytest.mark.parametrize("R,d", CROSS, ids=[f"R{c[0]:g}" for c in CROSS])
def test_v2_v1_and_the_executor_agree_on_every_component(R, d):
    dr = XC._dr(R, d)
    exe = _exe(dr)
    for k in range(3):
        if dr[k] == 0:
            continue
        _, r2 = S2.find_certificate(dr, k, DT, exe[k])
        _, r1 = S1.find_certificate(dr, k, DT, exe[k])
        assert r2.valid and r1.valid and r2.raw == r1.raw == exe[k], (k, r2, r1)


NEAR = [(2.9, (0.8, 0.5, 0.3), 0), (11.3, (0.2, 1.0, 0.4), 1), (61.0, (0.3, 0.3, -1.0), 2), (7.11, (0.7, 0.7, 0.1), 0)]
NEAR_BITS = (10, 30, 60, 100, 140, 300, 1000)


@pytest.mark.parametrize("R,d,k", NEAR, ids=[f"R{t[0]}" for t in NEAR])
def test_near_tie_ladder_both_sides_v2_agrees_with_the_executor(R, d, k):
    dr = XC._dr(R, d)
    for e in NEAR_BITS:
        for sign in (1, -1):
            _, dr_, dt, expected = XC.near_tie_item(dr, k, e, sign, dps=e // 3 + 200, dt_bits=e + 400)
            assert _exe(dr_, dt)[k] == expected
            cert, res = S2.find_certificate(dr_, k, dt, expected, 128, 4096)
            assert res.valid and res.raw == expected, (e, sign, res)
            for wrong in (expected + 1, expected - 1):
                assert K2.check_certificate(_set(cert, ("output", "raw"), str(wrong))).status == "INVALID"


def test_near_tie_v1_and_v2_agree_where_both_are_affordable():
    dr = XC._dr(3.3, (0.5, 0.8, 0.2))
    for e in (20, 60, 140):
        for sign in (1, -1):
            _, dr_, dt, expected = XC.near_tie_item(dr, 1, e, sign)
            _, r1 = S1.find_certificate(dr_, 1, dt, expected, 128, 512)
            _, r2 = S2.find_certificate(dr_, 1, dt, expected, 128, 512)
            assert r1.valid and r2.valid and r1.raw == r2.raw == expected


# --- formula fault injection (V2 has its own transcription of the frozen formula) ---------------------------------

@pytest.fixture(scope="module")
def formula_samples():
    specs = [(2.5, (1, 0, 0), 0), (3.7, (0.5, 0.8, 0.3), 2), (6.5, (0.2, 1, 0.1), 1), (12.0, (0.6, 0.4, 0.9), 0),
             (30.0, (0.7, 0.2, 0.5), 2), (450.0, (0.9, 0.3, 0.2), 0), (6000.0, (1, 0.2, 0.1), 0)]
    return [_honest(R, d, k) for R, d, k in specs]


def _caught(mod, samples):
    for cert, raw in samples:
        try:
            res = mod.check_certificate(cert)
        except Exception:
            return True
        if not (res.status == "VALID" and res.raw == raw):
            return True
    return False


def test_honest_v2_accepts_every_formula_sample(formula_samples):
    assert not _caught(K2, formula_samples)


FORMULA_FAULTS = {
    "short term P' + alpha P": [(".sub(_poly(pw, coefs, P).mul(_const(alpha, P), P)).rnd(P)", ".add(_poly(pw, coefs, P).mul(_const(alpha, P), P)).rnd(P)")],
    "short term wrong slot": [('e = E[RATE_ORDER.index((name, "short", idx))]', 'e = E[RATE_ORDER.index((name, "short", 0))]')],
    "long term wrong slot": [('e = E[RATE_ORDER.index((name, "long", 0))]', 'e = E[RATE_ORDER.index((name, "short", 0))]')],
    "kadd forgotten": [("n = 2 * k + kadd", "n = 2 * k")],
    "BO retardation g dropped": [("D, dD = g.sub(T), base.add(dg)", "D, dD = _Iv(1).sub(T), base.add(dg)")],
    "BO g' dropped": [("D, dD = g.sub(T), base.add(dg)", "D, dD = g.sub(T), base")],
    "REL branch like the default": [("D, dD = T.neg(), base", "D, dD = _Iv(1).sub(T), base")],
    "base eta forgotten": [("base = e.mul(_Iv(term_lo, term_hi), P).mul(eta_iv, P)", "base = e.mul(_Iv(term_lo, term_hi), P)")],
    "power -2k replaced by -k": [("term = dD.mul(pw[-2 * k], P)", "term = dD.mul(pw[-k], P)")],
    "2k factor replaced by k": [(".mul(_const(2 * k, P), P))", ".mul(_const(k, P), P))")],
    "long term sign": [("term = dD.mul(pw[-2 * k], P).mul(c, P).neg()", "term = dD.mul(pw[-2 * k], P).mul(c, P)")],
    "polynomial derivative factor": [("out = out.add(pw[i - 1].mul(_const(c * i, P), P))", "out = out.add(pw[i - 1].mul(_const(c, P), P))")],
    "retardation g' numerator sign": [("dg = dNr.mul(Dn, P).sub(Nr.mul(dDn, P))", "dg = dNr.mul(Dn, P).add(Nr.mul(dDn, P))")],
    "retardation dDn factor": [("dDn = dDn.add(pw[m].mul(_const(Fraction(b) * (m + 1), P), P))", "dDn = dDn.add(pw[m].mul(_const(Fraction(b), P), P))")],
    "force sign": [("G = dv.neg().mul(inv, P)", "G = dv.mul(inv, P)")],
    "one over R forgotten": [("G = dv.neg().mul(inv, P)", "G = dv.neg()")],
    "kick interval forgotten": [("c = Fraction(dr[comp], 1 << POSITION_FRAC_BITS) * dt ", "c = Fraction(dr[comp], 1 << POSITION_FRAC_BITS) ")],
    "wrong component": [("c = Fraction(dr[comp], 1 << POSITION_FRAC_BITS) * dt ", "c = Fraction(dr[0], 1 << POSITION_FRAC_BITS) * dt ")],
}


@pytest.mark.parametrize("name", list(FORMULA_FAULTS))
def test_fault_injection_formula(name, formula_samples):
    assert _caught(_mutant(*FORMULA_FAULTS[name]), formula_samples), f"fault survived: {name}"


# --- lowered-cap rehearsal ----------------------------------------------------------------------------------------

def test_rehearsal_real_trajectory_refusals_at_cap_128_are_settled_by_v2():
    st = X.canonical(Q(9), Q(1, 2) * X.RE)
    run = C.new_run(X.POS, X.DT, st["r_i"], st["p_i"], st["r_j"], st["p_j"], momentum_profile=X.MOM)
    _, witnesses, refusals = W.run_with_local_witnesses(run, 200)
    checked = 0
    for w in witnesses:
        dr = [int(Q(x) * (1 << 48)) for x in w["input"]["dr"]]
        for comp in w["components"]:
            if comp.get("zero_input"):
                continue
            _, res = S2.find_certificate(dr, comp["axis"], DT, comp["raw"])
            assert res.valid and res.raw == comp["raw"]
            checked += 1
    assert checked >= 3


def test_rehearsal_near_tie_stops_at_cap_128_and_v2_settles_it():
    dr = XC._dr(4.4, (0.6, 0.6, 0.5))
    for e in (20, 120, 400):
        _, dr_, dt, expected = XC.near_tie_item(dr, 0, e, 1, dps=e // 3 + 200, dt_bits=e + 400)
        with W.precision_cap(128):
            with pytest.raises(C.ReferenceUndecided):
                C.impulse(tuple(Q(v, 1 << 48) for v in dr_), dt, X.MOM)
        assert _exe(dr_, dt)[0] == expected
        _, res = S2.find_certificate(dr_, 0, dt, expected, 128, 2048)
        assert res.valid and res.raw == expected
    assert C.MAX_PRECISION_BITS == 16384
