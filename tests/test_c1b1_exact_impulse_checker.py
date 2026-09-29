"""Exact impulse certificate checker (c1b1-exact-impulse-certificate-v1): tests T1-T9 of the spec.

The checker (a_reference/c1b1_exact_impulse_checker.py) must not depend on the executor or the C1-A evaluator. Only
these tests bring the two together: the fingerprint / constant tables are compared with the frozen C1-A source, the
checker's verdicts are compared with the executor's RESOLVED raws, and the formula is attacked by fault injection
(mutating the checker's SOURCE TEXT and requiring every mutant to be caught).

A passing suite means: the checker agrees with two other implementations of the frozen formula on the sampled inputs,
and it rejects the injected transcription faults. It does not prove the formula transcription, and it says nothing
about A-EV.
"""
import ast
import copy
import json
import types
from fractions import Fraction as Q
from pathlib import Path

import mpmath as mp
import pytest

import a_reference.ar2_lang2024 as L
import a_reference.c1b1_exact_impulse_checker as K
import a_reference.c1b1_exact_impulse_crosscheck as XC
import a_reference.c1b1_exact_impulse_search as S
import a_reference.c1b1_runtime_local_witness as W
import a_reference.c1b1_stress_survey as X
import a_reference.c1b1_two_atom as C

CHECKER_PATH = Path(K.__file__)
CHECKER_SRC = CHECKER_PATH.read_text(encoding="utf-8")
DT = Q(20)


def _exe(dr, dt=DT):
    return C.impulse(tuple(Q(v, 1 << 48) for v in dr), dt, X.MOM)


def _dr(R, d):
    return XC._dr(R, d)


def _mutant(*replacements):
    """The checker module rebuilt from its source with every (old, new) applied exactly once."""
    src = CHECKER_SRC
    for old, new in replacements:
        assert src.count(old) == 1, f"mutation target must occur exactly once: {old!r} ({src.count(old)}x)"
        src = src.replace(old, new)
    mod = types.ModuleType("mutant_checker")
    exec(compile(src, "mutant_checker.py", "exec"), mod.__dict__)
    return mod


# --- T1: independence ---------------------------------------------------------------------------------------------

ALLOWED_IMPORTS = {"fractions", "hashlib", "json", "math", "time"}
FORBIDDEN_NAMES = {"_model", "_model_R", "_exp_enclosure", "enclosure", "impulse", "_decide", "a_reference", "a_numeric"}


def test_t1_checker_imports_only_the_standard_library_and_calls_no_evaluator():
    tree = ast.parse(CHECKER_SRC)
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0
            imported.add((node.module or "").split(".")[0])
    assert imported == ALLOWED_IMPORTS
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)} | {n.attr for n in ast.walk(tree)
                                                                          if isinstance(n, ast.Attribute)}
    assert not (names & FORBIDDEN_NAMES)


def test_t1_the_static_check_would_catch_a_shared_import():
    """Fault injection of the guard itself: a checker that imports the executor is seen."""
    bad = ast.parse(CHECKER_SRC + "\nimport a_reference.c1b1_two_atom\n")
    seen = {a.name.split(".")[0] for n in ast.walk(bad) if isinstance(n, ast.Import) for a in n.names}
    assert "a_reference" in seen and "a_reference" not in ALLOWED_IMPORTS


# --- T2: constants and fingerprint --------------------------------------------------------------------------------

def test_t2_fingerprint_equals_the_frozen_c1a_fingerprint_and_the_literal():
    assert K.fingerprint() == L.parameter_fingerprint() == K.FROZEN_FINGERPRINT


def test_t2_every_constant_table_equals_the_frozen_source_exactly():
    for name in ("BO", "REL", "QED"):
        short, (eta, cs, kadd) = L.COMPONENTS[name]
        for j, (alpha, coefs) in enumerate(K.SHORT[name], start=1):
            assert Q(alpha) == short[j][0]
            assert {i: Q(c) for i, c in coefs.items()} == short[j][1]
        assert (Q(K.LONG[name][0]), K.LONG[name][1], {k: Q(c) for k, c in K.LONG[name][2].items()}) == (eta, kadd, cs)
    assert tuple(Q(a) for a in K.RET_A) == L.RET_A and tuple(Q(b) for b in K.RET_B) == L.RET_B
    assert tuple((Q(a), Q(s)) for a, s in K.SIGMA_BO) == L.SIGMA_BO
    assert tuple((Q(a), Q(s)) for a, s in K.SIGMA_REL) == L.SIGMA_REL
    assert Q(K.BOHR_ANGSTROM) == L.BOHR_ANGSTROM and Q(K.R_MIN_ANGSTROM) == L.R_MIN_ANGSTROM
    assert K.CONTRACT == L.CONTRACT_VERSION


CONSTANT_FAULTS = [
    ('("2.29848003", {0: "0", 1: "0", 2: "6.921721e-2"})', '("2.29848003", {0: "0", 1: "0", 2: "6.921722e-2"})'),
    ('("6.92639712", {-1: "2.19578828e4"', '("6.92639713", {-1: "2.19578828e4"'),
    ('2: "-4.19874548e-2"', '2: "4.19874548e-2"'),
    ('"BO": ("3.65946625", 1,', '"BO": ("3.65946625", 0,'),
    ('8: "4294913366"', '8: "4294913367"'),
    ('"3.064827731712776e-01", "4.843969950480238e-03"', '"3.064827731712776e-01", "4.843969950480239e-03"'),
]


@pytest.mark.parametrize("old,new", CONSTANT_FAULTS)
def test_t2_a_mistyped_constant_is_caught_by_the_fingerprint(old, new):
    mod = _mutant((old, new))
    assert mod.fingerprint() != L.parameter_fingerprint()
    cert = S.make_certificate(_dr(4.0, (0.6, 0.7, 0.2)), 0, DT, _exe(_dr(4.0, (0.6, 0.7, 0.2)))[0], 128)
    res = mod.check_certificate(cert)
    assert res.status == "INVALID" and res.reason == "model_binding"


# --- shared honest certificates -----------------------------------------------------------------------------------

def _honest(R, d, comp, start=128):
    dr = _dr(R, d)
    raw = _exe(dr)[comp]
    cert, res = S.find_certificate(dr, comp, DT, raw, start)
    assert res.valid and res.raw == raw
    return cert, raw


@pytest.fixture(scope="module")
def honest_small():
    return _honest(5.0, (0.55, 0.7, 0.3), 0)


# --- T5: exp enclosure --------------------------------------------------------------------------------------------

def _mp_exp_neg(q):
    with mp.workdps(450):
        return mp.exp(-mp.mpf(q.numerator) / q.denominator)


def _mp(q):
    with mp.workdps(450):
        return mp.mpf(q.numerator) / q.denominator


EXP_GRID = [(Q(1, 7), Q(1, 7)), (Q(1), Q(1)), (Q(5, 2), Q(5, 2)), (Q(3), Q(7, 2)), (Q(13), Q(13)),
            (Q(473, 10), Q(474, 10)), (Q(140), Q(141))]


def _orders(x_hi):
    n0 = max(0, -(-x_hi.numerator // x_hi.denominator) - 1)          # smallest n with n + 2 > x_hi
    return [n0, n0 + 3, 2 * n0 + 10]


def test_t5_full_mode_contains_exp_and_the_width_shrinks_with_the_order():
    ctx = K._Ctx(K.Limits())
    for x_lo, x_hi in EXP_GRID:
        widths = []
        for n in _orders(x_hi):
            iv = K._exp_interval(Q(1), K._Iv(x_lo, x_hi), "full", n, ctx)
            assert 0 < iv.lo <= iv.hi
            for x in (x_lo, x_hi, (x_lo + x_hi) / 2):
                assert _mp(iv.lo) <= _mp_exp_neg(x) <= _mp(iv.hi)
            widths.append(iv.hi - iv.lo)
        assert widths[0] >= widths[1] >= widths[2]
        big = K._exp_interval(Q(1), K._Iv(x_lo, x_hi), "full", 6 * _orders(x_hi)[0] + 60, ctx)
        assert big.hi - big.lo <= (x_hi - x_lo) * _mp_to_q(_mp_exp_neg(x_lo)) + Q(1, 10 ** 30)


def _mp_to_q(v):
    with mp.workdps(450):
        return Q(int(mp.floor(v * mp.mpf(2) ** 300)) + 1, 1 << 300)


def test_t5_zero_floor_is_sound_and_positive():
    ctx = K._Ctx(K.Limits())
    for x_lo, x_hi in EXP_GRID:
        for n in (3, 12, 60):
            iv = K._exp_interval(Q(1), K._Iv(x_lo, x_hi), "zero_floor", n, ctx)
            assert iv.lo == 0
            assert _mp_exp_neg(x_hi) > 0 and _mp(iv.hi) >= _mp_exp_neg(x_lo)


def test_t5_a_full_mode_condition_violation_is_invalid_not_refused():
    ctx = K._Ctx(K.Limits())
    with pytest.raises(K._Invalid):
        K._exp_interval(Q(1), K._Iv(Q(9), Q(9)), "full", 6, ctx)          # n + 2 = 8 <= 9


def _exp_violations(mod):
    """Number of grid cases where the module's exp interval misses exp(-x) (any exception counts as a violation)."""
    ctx = mod._Ctx(mod.Limits())
    bad = 0
    for x_lo, x_hi in EXP_GRID:
        for n in _orders(x_hi):
            try:
                iv = mod._exp_interval(Q(1), mod._Iv(x_lo, x_hi), "full", n, ctx)
                ok = _mp(iv.lo) <= _mp_exp_neg(x_hi) and _mp_exp_neg(x_lo) <= _mp(iv.hi)
            except Exception:
                ok = False
            bad += not ok
    return bad


EXP_FAULTS = {
    "tail dropped": [("U_hi = t_hi * (n + 2) / (n + 2 - x_hi)", "U_hi = t_hi * 0")],
    "geometric factor dropped": [("U_hi = t_hi * (n + 2) / (n + 2 - x_hi)", "U_hi = t_hi")],
    "upper end from the wrong end": [("S_lo, _ = _series(x_lo, n, ctx)", "S_lo, _ = _series(x_hi, n, ctx)")],
    "lower end from the wrong end": [("S_hi, t_hi = _series(x_hi, n, ctx)", "S_hi, t_hi = _series(x_lo, n, ctx)")],
    "series stops one term early": [("    for j in range(n, 0, -1):", "    for j in range(n - 1, 0, -1):")],
    "condition weakened (no n+2 > x)": [("    if mode == \"full\" and not Fraction(n + 2) > x_hi:", "    if False:")],
}


def test_t5_the_honest_exp_enclosure_has_no_violations():
    assert _exp_violations(K) == 0


@pytest.mark.parametrize("name", [n for n in EXP_FAULTS if n != "condition weakened (no n+2 > x)"])
def test_t5_fault_injection_exp_enclosure(name):
    assert _exp_violations(_mutant(*EXP_FAULTS[name])) > 0, f"fault survived: {name}"


def test_t5_fault_injection_the_exp_condition_check_is_needed():
    """Without the condition the checker would accept an unsound geometric bound. Both places must fail closed."""
    cert, _ = _honest(2.6, (1, 0, 0), 0)
    full_slots = [i for i, e in enumerate(cert["proof"]["exp"]) if e["mode"] == "full"]
    assert full_slots
    bad = copy.deepcopy(cert)
    bad["proof"]["exp"][full_slots[0]]["order"] = "0"
    honest = K.check_certificate(bad)
    assert (honest.status, honest.reason) == ("INVALID", "exp_condition")
    weak = _mutant(EXP_FAULTS["condition weakened (no n+2 > x)"][0],
                   ('        if mode == "full" and not Fraction(order + 2) > rate * r.hi:\n'
                    '            raise _Invalid("exp_condition")', "        pass"))
    res = None
    try:
        res = weak.check_certificate(bad)
    except Exception:
        pass
    assert res is None or (res.status, res.reason) != ("INVALID", "exp_condition")


# --- T6: sqrt and interval arithmetic ------------------------------------------------------------------------------

SQRT_CASES = [Q(4), Q(2), Q(1, 3), Q(6, 5) ** 2, Q(10 ** 30 + 7, 3), Q(2 ** 90 + 1, 2 ** 96), Q(1 << 40),
              Q(7 ** 20, 4 ** 20)]


def _sqrt_ok(mod, R2, N):
    r = mod._sqrt_interval(R2, N)
    return r.lo > 0 and r.lo * r.lo <= R2 <= r.hi * r.hi and r.hi - r.lo == Q(1, 1 << N)


def test_t6_sqrt_interval_contains_the_root_with_width_two_to_minus_n():
    for R2 in SQRT_CASES:
        for N in (1, 2, 7, 64, 130):
            if K._sqrt_interval(R2, N).lo > 0:
                assert _sqrt_ok(K, R2, N)


SQRT_FAULTS = {
    "upper end equals the lower end": ("Fraction(a + 1, 1 << N))", "Fraction(a, 1 << N))"),
    "root rounded down once more": ("    a = math.isqrt(F)\n    return _Iv", "    a = math.isqrt(F) - 1\n    return _Iv"),
    "one bit too few": ("F = (R2.numerator << (2 * N)) // R2.denominator\n    a = math.isqrt(F)\n    return",
                        "F = (R2.numerator << (2 * N - 1)) // R2.denominator\n    a = math.isqrt(F)\n    return"),
}


@pytest.mark.parametrize("name", list(SQRT_FAULTS))
def test_t6_fault_injection_sqrt(name):
    mod = _mutant(SQRT_FAULTS[name])
    bad = 0
    for R2 in SQRT_CASES:
        for N in (2, 7, 64):
            try:
                bad += not _sqrt_ok(mod, R2, N)
            except Exception:
                bad += 1
    assert bad > 0, f"fault survived: {name}"


def _interval_cases():
    vals = [Q(-7, 3), Q(-1), Q(-1, 5), Q(0), Q(1, 7), Q(2), Q(11, 2)]
    return [(a, b) for a in vals for b in vals if a <= b]


def _iv_violations(mod):
    ops = {"add": lambda x, y: x + y, "sub": lambda x, y: x - y, "mul": lambda x, y: x * y}
    bad = 0
    pairs = _interval_cases()
    for a1, a2 in pairs:
        for b1, b2 in pairs:
            A, B = mod._Iv(a1, a2), mod._Iv(b1, b2)
            for name, fn in ops.items():
                try:
                    r = getattr(A, name)(B)
                except Exception:
                    bad += 1
                    continue
                for x in {a1, a2, (a1 + a2) / 2}:
                    for y in {b1, b2, (b1 + b2) / 2}:
                        bad += not (r.lo <= fn(x, y) <= r.hi)
            if b1 > 0:
                try:
                    r = A.div(B)
                    for x in {a1, a2}:
                        for y in {b1, b2, (b1 + b2) / 2}:
                            bad += not (r.lo <= x / y <= r.hi)
                except Exception:
                    bad += 1
        for c in (Q(-3, 2), Q(0), Q(5, 3)):
            try:
                r = mod._Iv(a1, a2).scale(c)
                bad += not (r.lo <= a1 * c <= r.hi and r.lo <= a2 * c <= r.hi)
            except Exception:                    # a broken operation that trips the interval-order guard is a catch
                bad += 1
    return bad


def test_t6_interval_operations_contain_all_sampled_results():
    assert _iv_violations(K) == 0


INTERVAL_FAULTS = {
    "mul uses only two products": ("return _Iv(min(p), max(p))\n\n    def scale", "return _Iv(min(p[:2]), max(p[:2]))\n\n    def scale"),
    "sub does not swap the ends": ("return _Iv(self.lo - o.hi, self.hi - o.lo)", "return _Iv(self.lo - o.lo, self.hi - o.hi)"),
    "div takes only one quotient": ("return _Iv(min(q), max(q))", "return _Iv(q[0], q[0])"),
    "scale forgets the sign": ("return _Iv(min(a, b), max(a, b))\n\n    def div", "return _Iv(a, b)\n\n    def div"),
}


@pytest.mark.parametrize("name", list(INTERVAL_FAULTS))
def test_t6_fault_injection_interval_arithmetic(name):
    assert _iv_violations(_mutant(INTERVAL_FAULTS[name])) > 0, f"fault survived: {name}"


def test_t6_touching_a_rounding_boundary_is_never_valid():
    """Strict separation: an interval that touches or crosses a half-ulp boundary of the claimed raw is not proof."""
    ulp = Q(1, 1 << 80)
    m = 12345
    lo_b, hi_b = (m - Q(1, 2)) * ulp, (m + Q(1, 2)) * ulp
    K._decide_raw(K._Iv(lo_b + ulp / 10, hi_b - ulp / 10), m)
    for J in (K._Iv(lo_b, m * ulp), K._Iv(m * ulp, hi_b), K._Iv(lo_b, hi_b), K._Iv(lo_b - ulp, m * ulp)):
        with pytest.raises(K._Invalid) as e:
            K._decide_raw(J, m)
        assert str(e.value) == "not_separated"
    with pytest.raises(K._Invalid) as e:
        K._decide_raw(K._Iv((m + 1) * ulp, (m + 1) * ulp + ulp / 4), m)
    assert str(e.value) == "raw_mismatch"


def test_t6_fault_injection_a_non_strict_separation_test_is_seen():
    mod = _mutant(("if cell_lo < J.lo and J.hi < cell_hi:", "if cell_lo <= J.lo and J.hi <= cell_hi:"))
    ulp = Q(1, 1 << 80)
    lo_b = (12345 - Q(1, 2)) * ulp
    accepted = True
    try:
        mod._decide_raw(mod._Iv(lo_b, 12345 * ulp), 12345)
    except mod._Invalid:
        accepted = False
    assert accepted, "the non-strict mutant must accept a touching interval (so the strict test above catches it)"


# --- T7: negatives -------------------------------------------------------------------------------------------------

def _variant(cert, path, value):
    c = copy.deepcopy(cert)
    node = c
    for p in path[:-1]:
        node = node[p]
    if value is KeyError:
        del node[path[-1]]
    else:
        node[path[-1]] = value
    return c


def test_t7_the_honest_certificate_is_valid_with_and_without_a_runtime_binding(honest_small):
    cert, raw = honest_small
    res = K.check_certificate(cert)
    assert (res.status, res.raw, res.reason) == ("VALID", raw, "strictly_separated")
    with_binding = dict(cert, runtime_binding={"anything": "is not read by the checker"})
    assert K.check_certificate(with_binding).valid
    assert K.check_certificate(dict(cert, runtime_binding=[1])).reason.startswith("not_an_object")


NEGATIVES = [
    ("raw plus one", ("output", "raw"), lambda c: str(int(c["output"]["raw"]) + 1), "raw_mismatch"),
    ("raw minus one", ("output", "raw"), lambda c: str(int(c["output"]["raw"]) - 1), "raw_mismatch"),
    ("raw out of range", ("output", "raw"), lambda c: str(1 << 95), "out_of_range"),
    ("raw with a leading zero", ("output", "raw"), lambda c: "0" + c["output"]["raw"].lstrip("-"), "bad_integer:raw"),
    ("raw with a space", ("output", "raw"), lambda c: " " + c["output"]["raw"], "bad_integer:raw"),
    ("raw as a number", ("output", "raw"), lambda c: int(c["output"]["raw"]), "bad_integer:raw"),
    ("width", ("output", "width"), lambda c: 64, "output_profile"),
    ("frac bits", ("output", "frac_bits"), lambda c: 79, "output_profile"),
    ("component zero position", ("input", "dr_raw"), lambda c: ["0"] + c["input"]["dr_raw"][1:], "not_a_decision"),
    ("below r_min", ("input", "dr_raw"), lambda c: [str(1 << 48), "0", "0"], "physics_domain"),
    ("position range", ("input", "dr_raw"), lambda c: [str(1 << 96), "5", "5"], "input_range"),
    ("dr_raw length", ("input", "dr_raw"), lambda c: c["input"]["dr_raw"][:2], "input"),
    ("position bits", ("input", "position_frac_bits"), lambda c: 47, "input"),
    ("component index", ("input", "component"), lambda c: 3, "input"),
    ("component bool", ("input", "component"), lambda c: True, "bad_integer:component"),
    ("dt zero", ("input", "dt_kick"), lambda c: "0", "input"),
    ("dt zero denominator", ("input", "dt_kick"), lambda c: "1/0", "bad_rational:dt_kick"),
    ("fingerprint", ("model", "parameter_fingerprint"), lambda c: "0" * 64, "model_binding"),
    ("retardation off", ("model", "retardation"), lambda c: False, "model_binding"),
    ("contract name", ("model", "contract"), lambda c: "c1a-ar2-lang2024-v2", "model_binding"),
    ("format", ("format",), lambda c: "c1b1-exact-impulse-certificate-v2", "format"),
    ("method", ("method",), lambda c: "other", "format"),
    ("sqrt bits zero", ("proof", "sqrt_bits"), lambda c: "0", "sqrt_bits"),
    ("exp list too short", ("proof", "exp"), lambda c: c["proof"]["exp"][:8], "exp_list"),
    ("exp mode", ("proof", "exp", 0, "mode"), lambda c: "guess", "exp_mode"),
    ("exp rate", ("proof", "exp", 3, "rate"), lambda c: "3/1", "exp_rate"),
    ("exp order negative", ("proof", "exp", 3, "order"), lambda c: "-1", "exp_order"),
]


@pytest.mark.parametrize("label,path,make,reason", NEGATIVES, ids=[n[0] for n in NEGATIVES])
def test_t7_negative_certificates_are_invalid_for_the_intended_reason(honest_small, label, path, make, reason):
    cert, _ = honest_small
    res = K.check_certificate(_variant(cert, path, make(cert)))
    assert (res.status, res.reason) == ("INVALID", reason)


def test_t7_unknown_keys_and_missing_keys_are_invalid(honest_small):
    cert, _ = honest_small
    for path in (("extra",), ("model", "extra"), ("input", "extra"), ("output", "extra"), ("proof", "extra"),
                 ("proof", "exp", 0, "extra")):
        c = copy.deepcopy(cert)
        node = c
        for p in path[:-1]:
            node = node[p]
        node[path[-1]] = 1
        assert K.check_certificate(c).reason.startswith("keys:"), path
    for path in (("model",), ("proof", "sqrt_bits"), ("output", "raw"), ("input", "dt_kick")):
        assert K.check_certificate(_variant(cert, path, KeyError)).reason.startswith("keys:"), path
    assert K.check_certificate("not a dict").reason.startswith("not_an_object")


def test_t7_swapped_exp_slots_are_caught_by_the_rate_check(honest_small):
    cert, _ = honest_small
    c = copy.deepcopy(cert)
    c["proof"]["exp"][0], c["proof"]["exp"][1] = c["proof"]["exp"][1], c["proof"]["exp"][0]
    assert K.check_certificate(c).reason == "exp_rate"


def test_t7_too_coarse_a_certificate_is_invalid_not_refused_and_never_valid(honest_small):
    cert, _ = honest_small
    for bits in ("1", "8", "24"):
        res = K.check_certificate(_variant(cert, ("proof", "sqrt_bits"), bits))
        assert res.status == "INVALID" and res.reason in ("not_separated", "exp_condition", "division_by_nonpositive")


def test_t7_a_wrong_exp_order_still_cannot_make_a_wrong_raw_valid(honest_small):
    cert, raw = honest_small
    for i in range(9):
        for order in ("40", "300"):
            c = _variant(cert, ("proof", "exp", i, "order"), order)
            res = K.check_certificate(c)
            assert res.status != "VALID" or res.raw == raw


# --- T3: cross-check against the executor -------------------------------------------------------------------------

def _sample_items():
    hard = XC.family_hard(18)[::37][:3] + XC.family_hard(17)[::300][:2] + XC.family_hard(16)[::2500][:2]
    return (XC.family_inner(8) + XC.family_axes(8) + XC.family_outer(6) + XC.family_multi65()[::16]
            + hard + XC.family_shell24_26())


def test_t3_the_checker_proves_the_same_raw_as_the_executor_on_a_deterministic_sample():
    items = _sample_items()
    assert len(items) >= 35
    records = [XC.run_one(it) for it in items]
    summary = XC.summarize(records)
    assert summary["disagreements"] == [], summary["disagreements"][:3]
    assert summary["by_status"] == {"VALID": summary["decisions"]} and summary["decisions"] >= 60
    assert set(summary["by_family"]) >= {"inner", "axes", "outer", "far", "multi65", "hard18", "hard17", "hard16",
                                          "shell24", "shell25", "shell26"} - {"shell25"}


def test_t3_the_mpmath_reference_agrees_with_the_executor():
    """A third implementation of the same formula: the exact J (times 20) is within half an ulp of the executor's raw."""
    for R, d in ((2.4, (1, 0.3, 0.2)), (7.7, (0.3, 1, 0.5)), (33.0, (0.5, 0.5, 1)), (450.0, (1, 0.1, 0.9))):
        dr = _dr(R, d)
        exe = _exe(dr)
        for k in range(3):
            ref = XC.reference_J_unit(dr, k) * 20 * mp.mpf(2) ** 80
            assert abs(ref - exe[k]) <= mp.mpf(1) / 2 + mp.mpf(10) ** -30


NEAR_TIE = [(2.9, (0.8, 0.5, 0.3), 0), (11.3, (0.2, 1.0, 0.4), 1), (61.0, (0.3, 0.3, 1.0), 2), (700.0, (1.0, 0.0, 0.0), 0)]
NEAR_BITS = (10, 40, 80, 130)


@pytest.mark.parametrize("R,d,k", NEAR_TIE, ids=[f"R{t[0]}" for t in NEAR_TIE])
def test_t3_near_tie_inputs_executor_and_checker_agree_on_both_sides_of_a_boundary(R, d, k):
    """The exact impulse sits 2^-e ulps above / below a half-ulp boundary (e up to 130): both must pick the right side."""
    dr = _dr(R, d)
    for e in NEAR_BITS:
        for sign in (1, -1):
            _, dr_, dt, expected = XC.near_tie_item(dr, k, e, sign)
            assert _exe(dr_, dt)[k] == expected
            cert, res = S.find_certificate(dr_, k, dt, expected, 128, 1024)
            assert res.valid and res.raw == expected, (e, sign, res)
            wrong = _variant(cert, ("output", "raw"), str(expected + (-1 if sign > 0 else 1) if sign > 0 else expected + 1))
            assert K.check_certificate(wrong).status == "INVALID"


# --- T4: fault injection into the formula -------------------------------------------------------------------------

@pytest.fixture(scope="module")
def formula_samples():
    """Honest (certificate, raw) pairs; cheap ones first. Every formula mutant must be rejected by at least one."""
    specs = [(2.5, (1, 0, 0), 0), (3.7, (0.5, 0.8, 0.3), 2), (6.5, (0.2, 1, 0.1), 1), (12.0, (0.6, 0.4, 0.9), 0),
             (30.0, (0.7, 0.2, 0.5), 2), (90.0, (0.4, 0.9, 0.3), 1), (450.0, (0.9, 0.3, 0.2), 0),
             (2400.0, (0.5, 0.5, 0.7), 2), (6000.0, (1, 0.2, 0.1), 0)]
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


def test_t4_the_honest_checker_accepts_every_sample(formula_samples):
    assert not _caught(K, formula_samples)


FORMULA_FAULTS = {
    "short term P' + alpha P": [(".sub(_poly(R, coefs).scale(alpha)))", ".add(_poly(R, coefs).scale(alpha)))")],
    "short term alpha doubled": [(".sub(_poly(R, coefs).scale(alpha)))", ".sub(_poly(R, coefs).scale(alpha * 2)))")],
    "short term wrong slot": [('E[RATE_ORDER.index((name, "short", idx))]', 'E[RATE_ORDER.index((name, "short", 0))]')],
    "long term wrong slot": [('E[RATE_ORDER.index((name, "long", 0))]', 'E[RATE_ORDER.index((name, "short", 0))]')],
    "kadd forgotten": [("n = 2 * k + kadd", "n = 2 * k")],
    "kadd swapped": [("n = 2 * k + kadd", "n = 2 * k + (1 - kadd)")],
    "series one term short": [("for i in range(done + 1, n + 1):", "for i in range(done + 1, n):")],
    "BO retardation g dropped": [("D, dD = g.sub(T), base.add(dg)", "D, dD = _Iv(1).sub(T), base.add(dg)")],
    "BO g' dropped": [("D, dD = g.sub(T), base.add(dg)", "D, dD = g.sub(T), base")],
    "BO g plus T": [("D, dD = g.sub(T), base.add(dg)", "D, dD = g.add(T), base.add(dg)")],
    "REL branch like the default": [("D, dD = T.neg(), base", "D, dD = _Iv(1).sub(T), base")],
    "default branch without the 1": [("D, dD = _Iv(1).sub(T), base\n            c = Fraction", "D, dD = T.neg(), base\n            c = Fraction")],
    "kmin of BO wrong": [('if name == "BO" and k == kmin:', 'if name == "BO" and k == kmin + 1:')],
    "kmin of REL wrong": [('elif name == "REL" and k == kmin:', 'elif name == "REL" and k == kmin + 1:')],
    "base eta forgotten": [("base = e.mul(_Iv(term_lo, term_hi)).scale(eta)", "base = e.mul(_Iv(term_lo, term_hi))")],
    "power -2k replaced by -k": [("_rpow(R, -2 * k)", "_rpow(R, -k)")],
    "power -2k-1 replaced by -2k": [("_rpow(R, -2 * k - 1)", "_rpow(R, -2 * k)")],
    "2k factor replaced by k": [(".scale(c * 2 * k)", ".scale(c * k)")],
    "long term sign": [("total = total.sub(dD.mul(_rpow(R, -2 * k)).scale(c))", "total = total.add(dD.mul(_rpow(R, -2 * k)).scale(c))")],
    "polynomial derivative power": [("_rpow(R, i - 1).scale(c * i)", "_rpow(R, i).scale(c * i)")],
    "polynomial derivative factor": [("_rpow(R, i - 1).scale(c * i)", "_rpow(R, i - 1).scale(c)")],
    "polynomial power": [("out = out.add(_rpow(R, i).scale(c))", "out = out.add(_rpow(R, i + 1).scale(c))")],
    "retardation g' numerator sign": [("dg = dNr.mul(Dn).sub(Nr.mul(dDn)).div(Dn.mul(Dn))", "dg = dNr.mul(Dn).add(Nr.mul(dDn)).div(Dn.mul(Dn))")],
    "retardation g' denominator": [("dg = dNr.mul(Dn).sub(Nr.mul(dDn)).div(Dn.mul(Dn))", "dg = dNr.mul(Dn).sub(Nr.mul(dDn)).div(Dn)")],
    "retardation dNr factor": [("dNr = dNr.add(_rpow(R, m).scale(Fraction(a) * (m + 1)))", "dNr = dNr.add(_rpow(R, m).scale(Fraction(a)))")],
    "retardation dDn factor": [("dDn = dDn.add(_rpow(R, m).scale(Fraction(b) * (m + 1)))", "dDn = dDn.add(_rpow(R, m).scale(Fraction(b)))")],
    "retardation Nr start": [("Nr, dNr, Dn, dDn = _Iv(1), _Iv(0), _Iv(1), _Iv(0)", "Nr, dNr, Dn, dDn = _Iv(0), _Iv(0), _Iv(1), _Iv(0)")],
    "retardation Dn start": [("Nr, dNr, Dn, dDn = _Iv(1), _Iv(0), _Iv(1), _Iv(0)", "Nr, dNr, Dn, dDn = _Iv(1), _Iv(0), _Iv(2), _Iv(0)")],
    "force sign": [("G = dv.neg().mul(_Iv(1 / r.hi, 1 / r.lo))", "G = dv.mul(_Iv(1 / r.hi, 1 / r.lo))")],
    "one over R forgotten": [("G = dv.neg().mul(_Iv(1 / r.hi, 1 / r.lo))", "G = dv.neg().mul(_Iv(1, 1))")],
    "kick interval forgotten": [("J = G.scale(Fraction(dr[comp], 1 << POSITION_FRAC_BITS) * dt)", "J = G.scale(Fraction(dr[comp], 1 << POSITION_FRAC_BITS))")],
    "wrong component": [("J = G.scale(Fraction(dr[comp], 1 << POSITION_FRAC_BITS) * dt)", "J = G.scale(Fraction(dr[0], 1 << POSITION_FRAC_BITS) * dt)")],
    "position unit": [("J = G.scale(Fraction(dr[comp], 1 << POSITION_FRAC_BITS) * dt)", "J = G.scale(Fraction(dr[comp], 1 << 47) * dt)")],
    "R squared unit": [("R2 = Fraction(sum(v * v for v in dr), 1 << (2 * POSITION_FRAC_BITS))", "R2 = Fraction(sum(v * v for v in dr), 1 << POSITION_FRAC_BITS)")],
    "output scale": [("ulp = Fraction(1, 1 << OUT_FRAC)", "ulp = Fraction(1, 1 << (OUT_FRAC + 1))")],
    # localized faults: they touch only one high-order term, yet the 2^-80 output grid makes every term visible
    "local: retardation dDn factor only for m == 5": [("dDn = dDn.add(_rpow(R, m).scale(Fraction(b) * (m + 1)))", "dDn = dDn.add(_rpow(R, m).scale(Fraction(b) * ((m + 1) if m < 5 else 1)))")],
    "local: retardation dNr factor only for m == 4": [("dNr = dNr.add(_rpow(R, m).scale(Fraction(a) * (m + 1)))", "dNr = dNr.add(_rpow(R, m).scale(Fraction(a) * ((m + 1) if m < 4 else 1)))")],
    "local: 2k factor wrong only for k == 8": [(".scale(c * 2 * k)", ".scale(c * (2 * k if k < 8 else k))")],
    "local: REL C4 second term dropped": [("            total = total.add(D.mul(_rpow(R, -2 * k - 1)).scale(c * 2 * k))", "            total = total.add(D.mul(_rpow(R, -2 * k - 1)).scale(c * 2 * k)) if not (name == 'REL' and k == 2) else total")],
    "local: QED k == 4 term omitted": [("            total = total.sub(dD.mul(_rpow(R, -2 * k)).scale(c))", "            total = total.sub(dD.mul(_rpow(R, -2 * k)).scale(c)) if not (name == 'QED' and k == 4) else total")],
}


@pytest.mark.parametrize("name", list(FORMULA_FAULTS))
def test_t4_fault_injection_formula(name, formula_samples):
    mod = _mutant(*FORMULA_FAULTS[name])
    assert _caught(mod, formula_samples), f"fault survived: {name}"


BYPASS_FINGERPRINT = (
    "    computed = fingerprint()" + chr(10)
    + '    if not (computed == FROZEN_FINGERPRINT == model["parameter_fingerprint"]):' + chr(10)
    + '        raise _Invalid("model_binding")',
    "    pass")
# last-digit errors in constants, with the fingerprint check switched off: what the cross-check alone would see
SEEN_BY_CROSSCHECK = [
    ('"2.19578828e4"', '"2.19578829e4"'), ('"9.53252754e4"', '"9.53252755e4"'), ('"-3.55673715e0"', '"-3.55673716e0"'),
    ('"6.921721e-2"', '"6.921722e-2"'), ('"64.2295222"', '"64.2295223"'), ('"4294913366"', '"4294913367"'),
    ('"-9.43594504e-4"', '"-9.43594505e-4"'), ('"-1.949525e-2"', '"-1.949526e-2"'),
    ('"4.843969950480238e-03"', '"4.843969950480239e-03"'), ('"1.156839432134599e-05"', '"1.156839432134600e-05"'),
]


@pytest.mark.parametrize("old,new", SEEN_BY_CROSSCHECK)
def test_t2_a_last_digit_constant_error_is_also_seen_by_the_cross_check_without_the_fingerprint(old, new, formula_samples):
    assert _caught(_mutant((old, new), BYPASS_FINGERPRINT), formula_samples)


def test_t2_the_r6_retardation_coefficient_is_protected_by_the_fingerprint_alone(formula_samples):
    """Documented limit of the cross-check: the last digit of RET_B[5] (8.77e-15, the R^6 term of the retardation
    denominator) moves no sampled raw. Only the fingerprint (and the table-equality test) stops such an error."""
    old, new = '"8.769598859882065e-15"', '"8.769598859882066e-15"'
    assert not _caught(_mutant((old, new), BYPASS_FINGERPRINT), formula_samples)
    assert _mutant((old, new)).check_certificate(formula_samples[0][0]).reason == "model_binding"


# --- T8: rehearsal at a lowered executor cap ----------------------------------------------------------------------

def test_t8_rehearsal_a_refused_executor_decision_is_settled_by_a_certificate_equal_to_the_full_cap_result():
    """The executor at cap 128 cannot decide a near-tie impulse; the checker's certificate settles it with a raw that
    equals what the full-cap executor decides; the parameters needed grow as the boundary gets closer."""
    dr = _dr(4.4, (0.6, 0.6, 0.5))
    needed = []
    for e in (20, 70, 120, 160):
        _, dr_, dt, expected = XC.near_tie_item(dr, 0, e, 1)
        with W.precision_cap(128):
            with pytest.raises(C.ReferenceUndecided):
                C.impulse(tuple(Q(v, 1 << 48) for v in dr_), dt, X.MOM)
        assert _exe(dr_, dt)[0] == expected
        cert, res = S.find_certificate(dr_, 0, dt, expected, 64, 2048)
        assert res.valid and res.raw == expected
        needed.append(int(cert["proof"]["sqrt_bits"]))
        too_small = _variant(cert, ("proof", "sqrt_bits"), str(int(cert["proof"]["sqrt_bits"]) // 4))
        assert K.check_certificate(too_small).status == "INVALID"
    assert needed == sorted(needed) and needed[-1] > needed[0]
    assert C.MAX_PRECISION_BITS == 16384


def test_t8_real_trajectory_refusals_at_cap_128_are_settled_by_certificates_with_the_full_cap_raw():
    """Real refusals: the executor stepping a real trajectory at cap 128 stops on impulses it cannot decide there; the
    witness prototype records the refused inputs and the raws the full-cap executor decides. The independent checker
    must prove exactly those raws (components that needed more than 128 bits included)."""
    st = X.canonical(Q(9), Q(1, 2) * X.RE)
    run = C.new_run(X.POS, X.DT, st["r_i"], st["p_i"], st["r_j"], st["p_j"], momentum_profile=X.MOM)
    _, witnesses, refusals = W.run_with_local_witnesses(run, 200)
    assert len(witnesses) >= 3 and sum(len(r["axes_above_exec_cap"]) for r in refusals) >= 3
    checked = 0
    for w in witnesses:
        dr_exact = [Q(x) for x in w["input"]["dr"]]
        dr_raw = [int(x * (1 << 48)) for x in dr_exact]
        assert all(Q(v, 1 << 48) == x for v, x in zip(dr_raw, dr_exact))
        for comp in w["components"]:
            if comp.get("zero_input"):
                continue
            cert, res = S.find_certificate(dr_raw, comp["axis"], DT, comp["raw"])
            assert res.valid and res.raw == comp["raw"], (comp["axis"], res)
            checked += 1
    assert checked >= 3


# --- T9: operational limits ---------------------------------------------------------------------------------------

def test_t9_limits_give_refused_and_never_change_the_truth(honest_small):
    cert, raw = honest_small
    n_bits = int(cert["proof"]["sqrt_bits"])
    orders = [int(e["order"]) for e in cert["proof"]["exp"]]
    limits = {
        "sqrt bits": (K.Limits(sqrt_bits_max=n_bits - 1), "sqrt_limit"),
        "order": (K.Limits(order_max=max(orders) - 1), "order_limit"),
        "size": (K.Limits(bits_max=1000), "size_limit"),
        "time": (K.Limits(seconds_max=-1.0), "time_limit"),
    }
    for label, (lim, reason) in limits.items():
        res = K.check_certificate(cert, lim)
        assert (res.status, res.raw, res.reason) == ("REFUSED", None, reason), label
    # the same limit one step looser -> the mathematical verdict
    assert K.check_certificate(cert, K.Limits(sqrt_bits_max=n_bits)).raw == raw
    assert K.check_certificate(cert, K.Limits(order_max=max(orders))).raw == raw


def test_t9_a_ladder_of_limits_never_turns_valid_into_invalid_or_the_reverse(honest_small):
    cert, raw = honest_small
    coarse = _variant(cert, ("proof", "sqrt_bits"), "12")
    for lim in (K.Limits(sqrt_bits_max=16), K.Limits(sqrt_bits_max=64), K.Limits(sqrt_bits_max=128), K.Limits(order_max=10),
                K.Limits(order_max=100), K.Limits(order_max=10 ** 5), K.Limits(bits_max=10 ** 3), K.Limits(bits_max=10 ** 6),
                K.Limits(seconds_max=-1), K.Limits()):
        good, bad = K.check_certificate(cert, lim), K.check_certificate(coarse, lim)
        assert good.status in ("VALID", "REFUSED") and (good.status != "VALID" or good.raw == raw)
        assert bad.status in ("INVALID", "REFUSED")
        wrong = K.check_certificate(_variant(cert, ("output", "raw"), str(raw + 1)), lim)
        assert wrong.status in ("INVALID", "REFUSED")


def test_t9_refused_is_not_a_verdict_about_a_malformed_certificate(honest_small):
    """A malformed certificate is INVALID whatever the limits are (structure is checked before any limit applies)."""
    cert, _ = honest_small
    bad = _variant(cert, ("model", "parameter_fingerprint"), "0" * 64)
    for lim in (K.Limits(seconds_max=-1.0), K.Limits(sqrt_bits_max=1), K.Limits()):
        assert K.check_certificate(bad, lim).reason == "model_binding"


def test_t9_the_default_limits_and_the_measured_cost_are_recorded(honest_small):
    cert, _ = honest_small
    res = K.check_certificate(cert)
    assert res.stats["limits"] == K.Limits().as_dict()
    assert res.stats["max_bits"] > 0 and res.stats["seconds"] >= 0 and len(res.stats["orders"]) == 9
