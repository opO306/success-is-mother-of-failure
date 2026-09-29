"""Point prover V0.1: an UNTRUSTED generator. The only success is checker V2 VALID(raw).

V0.1 (designer verdicts D1, D2, 2026-09-30): the mpmath estimate only HINTS; checker V2's own enclosure decides the raw.
A wrong hint is recovered (not an ANOMALY), a failed or out-of-range estimate ends nothing.

Tests: FOUND agrees with the unchanged executor and always re-verifies; cap-128 rehearsal on real trajectories; near-tie
ladder (the prover finds the raw and the parameters itself, from 2^-10 to 2^-4000 on both sides); the four results and their
meanings (EXHAUSTED never a verdict on truth, ANOMALY never retried into FOUND); static independence; determinism;
fault injection into the prover's SOURCE TEXT (a prover that skips the checker, treats not_separated as success, retries an
ANOMALY, or ignores a REFUSED must be caught). Passing these says the generator and the trusted V2 checker cooperate on the
sampled inputs; it proves nothing about the physics, A-EV, Safety or Liveness.
"""
import ast
import json
import sys
import types
from fractions import Fraction as Q
from pathlib import Path

import mpmath as mp
import pytest

import a_reference.c1b1_exact_impulse_checker_v2 as K2
import a_reference.c1b1_exact_impulse_crosscheck as XC
import a_reference.c1b1_point_prover as P
import a_reference.c1b1_runtime_local_witness as W
import a_reference.c1b1_stress_survey as X
import a_reference.c1b1_two_atom as C

PROVER_SRC = Path(P.__file__).read_text(encoding="utf-8")
DT = Q(20)


def _exe(dr, dt=DT):
    return C.impulse(tuple(Q(v, 1 << 48) for v in dr), dt, X.MOM)


def _mutant(*replacements):
    src = PROVER_SRC
    for old, new in replacements:
        assert src.count(old) == 1, f"mutation target must occur exactly once: {old!r} ({src.count(old)}x)"
        src = src.replace(old, new)
    mod = types.ModuleType("mutant_prover")
    exec(compile(src, "mutant_prover.py", "exec"), mod.__dict__)
    return mod


def _fake_estimate(delta):
    real = P._estimate

    def est(dr, k, dt, budget):
        e = dict(real(dr, k, dt, budget))
        e["m"] += delta
        return e
    return est


class _CountingChecker:
    """Wraps K2.check_certificate to count calls (and remember the verdicts)."""

    def __init__(self, monkeypatch):
        self.calls, self.verdicts = 0, []
        real = K2.check_certificate

        def wrapped(cert, limits=None):
            self.calls += 1
            res = real(cert, limits)
            self.verdicts.append((res.status, res.reason))
            return res
        monkeypatch.setattr(K2, "check_certificate", wrapped)


# --- FOUND agrees with the executor and always re-verifies --------------------------------------------------------

def _sample():
    hard = XC.family_hard(18)[::40][:3] + XC.family_hard(17)[::350][:2] + XC.family_hard(16)[::3000][:2]
    return (XC.family_inner(8) + XC.family_axes(8) + XC.family_outer(6) + XC.family_multi65()[::16] + hard
            + XC.family_shell24_26())


def test_found_raw_equals_the_executors_raw_and_every_found_result_reverifies():
    n = 0
    for family, dr in _sample():
        exe = _exe(dr)
        for k in range(3):
            if dr[k] == 0:
                assert P.prove(dr, k, DT).status == P.NOT_A_DECISION
                continue
            r = P.prove(dr, k, DT)
            assert r.status == P.FOUND and r.raw == exe[k], (family, dr, k, r)
            assert r.checker.valid and r.checker.raw == r.raw and P.verify_found(r)
            assert r.attempts[-1]["verdict"] == "VALID" and r.budget["guard_bits"] == 96
            n += 1
    assert n >= 60


# --- V1: cap-128 rehearsal on real trajectories -------------------------------------------------------------------

@pytest.mark.parametrize("e,bf,steps", ((Q(9), Q(1, 2), 1640), (Q(1, 2), Q(1, 2), 5775)), ids=("e9_b0.5Re", "e0.5_b0.5Re"))
def test_cap_128_rehearsal_every_refused_impulse_of_a_real_trajectory_is_settled(e, bf, steps):
    """The executor stepping at cap 128 stops on impulses it cannot decide there; the prover, from the refused input
    alone (no raw from the executor), finds a certificate whose raw equals what the full-cap executor decided."""
    st = X.canonical(e, bf * X.RE)
    run = C.new_run(X.POS, X.DT, st["r_i"], st["p_i"], st["r_j"], st["p_j"], momentum_profile=X.MOM)
    _, witnesses, refusals = W.run_with_local_witnesses(run, steps)
    assert len(witnesses) >= 20
    settled = 0
    for w in witnesses:
        dr = [int(Q(x) * (1 << 48)) for x in w["input"]["dr"]]
        for comp in w["components"]:
            if comp.get("zero_input"):
                continue
            r = P.prove(dr, comp["axis"], DT)
            assert r.status == P.FOUND and r.raw == comp["raw"] and P.verify_found(r), (comp, r)
            settled += 1
    assert settled >= sum(len(x["axes_above_exec_cap"]) for x in refusals) >= 20
    assert C.MAX_PRECISION_BITS == 16384


# --- near-tie ladder: the prover finds the raw and the parameters by itself ---------------------------------------

NEAR = [(2.9, (0.8, 0.5, 0.3), 0), (11.3, (0.2, 1.0, 0.4), 1), (61.0, (0.3, 0.3, -1.0), 2), (7.11, (0.7, 0.7, 0.1), 0)]
NEAR_BITS = (10, 30, 60, 100, 140, 300, 1000)


@pytest.mark.parametrize("R,d,k", NEAR, ids=[f"R{t[0]}" for t in NEAR])
def test_near_tie_ladder_both_sides(R, d, k):
    dr = XC._dr(R, d)
    sqrt_bits = []
    for e in NEAR_BITS:
        for sign in (1, -1):
            _, dr_, dt, expected = XC.near_tie_item(dr, k, e, sign, dps=e // 3 + 200, dt_bits=e + 400)
            assert _exe(dr_, dt)[k] == expected
            r = P.prove(dr_, k, dt)
            assert r.status == P.FOUND and r.raw == expected and P.verify_found(r), (e, sign, r)
            assert r.estimate["dist_bits"] in (e, e + 1), (e, r.estimate)      # it measured the distance itself
        sqrt_bits.append(r.attempts[-1]["sqrt_bits"])
    assert sqrt_bits == sorted(sqrt_bits) and sqrt_bits[-1] > sqrt_bits[0]


def test_deeper_than_the_executors_cheap_range_2_to_the_minus_4000_both_sides():
    dr = XC._dr(4.4, (0.6, 0.6, 0.5))
    for sign in (1, -1):
        _, dr_, dt, expected = XC.near_tie_item(dr, 0, 4000, sign, dps=1540, dt_bits=4400)
        r = P.prove(dr_, 0, dt)
        assert r.status == P.FOUND and r.raw == expected and P.verify_found(r)
        assert r.attempts[-1]["sqrt_bits"] >= 4000


def test_the_estimator_agrees_with_the_third_implementation():
    """The prover's mpmath transcription equals the cross-check driver's (which the fingerprint-tied tables feed)."""
    for R, d in ((2.4, (1, 0.3, 0.2)), (7.1129, (-1, 0, 0)), (33.0, (0.5, 0.5, 1)), (900.0, (1, 0.1, 0.9))):
        dr = XC._dr(R, d)
        for k in range(3):
            if dr[k] == 0:
                continue
            with mp.workdps(120):
                y = P._y_at(dr, k, DT, 400)
                ref = XC.reference_J_unit(dr, k, 120) * 20 * mp.mpf(2) ** 80
                assert abs(y - ref) <= abs(ref) * mp.mpf(10) ** -60 + mp.mpf(10) ** -60


# --- the four results and their meanings --------------------------------------------------------------------------

def test_not_a_decision_cases():
    dr = XC._dr(5.0, (0.6, 0.7, 0.3))
    assert P.prove([0, dr[1], dr[2]], 0, DT).reason == "zero_component"
    assert P.prove(dr, 0, Q(0)).reason == "zero_kick"
    assert P.prove([1 << 48, 0, 0], 0, DT).reason == "below_r_min"
    assert P.prove([1 << 96, 5, 5], 0, DT).reason == "outside_position_profile"
    # an estimate outside the output range decides nothing (D2): the trusted enclosure is consulted, and only when IT lies
    # strictly inside a cell outside FX(96,80) does the run end, as output_out_of_range (never NOT_A_DECISION)
    over = P.prove(dr, 0, Q(10 ** 40))
    assert (over.status, over.reason) == (P.EXHAUSTED, "output_out_of_range") and over.raw is None
    assert over.estimate["estimate_failed"] == "estimate_out_of_output_range"
    assert over.attempts[-1]["verdict"] == "ENCLOSURE" and over.certificate is None
    assert P.NOT_A_DECISION not in {P.prove(dr, 0, Q(10 ** e)).status for e in (35, 40, 60)}
    for r in (P.prove([0, dr[1], dr[2]], 0, DT), P.prove(dr, 0, Q(0))):
        assert r.status == P.NOT_A_DECISION and r.raw is None and r.certificate is None
    with pytest.raises(ValueError):
        P.prove([1.5, 2, 3], 0, DT)
    with pytest.raises(ValueError):
        P.prove(dr, 3, DT)


def _deep_2_17000(sign=1):
    dr = XC._dr(4.4, (0.6, 0.6, 0.5))
    old = sys.get_int_max_str_digits()
    sys.set_int_max_str_digits(0)
    try:
        _, dr_, dt, expected = XC.near_tie_item(dr, 0, 17000, sign, dps=5700, dt_bits=17600)
    finally:
        sys.set_int_max_str_digits(old)
    return dr_, dt, expected


def test_a_stop_beyond_the_executors_cap_is_exhausted_not_false_under_the_default_limits():
    """2^-17000: the prover measures the distance, but a certificate needs a 5,300-digit dt_kick. With Python's own digit
    limit it cannot even be written (serialization_limit); with that lifted, checker V2 refuses (integer_size_limit).
    Neither is a statement about truth: EXHAUSTED, no raw, no FOUND."""
    dr, dt, expected = _deep_2_17000()
    r = P.prove(dr, 0, dt)
    assert (r.status, r.reason) == (P.EXHAUSTED, "serialization_limit") and r.raw is None
    assert r.estimate["dist_bits"] in (17000, 17001)          # dt is quantized: the distance is 2^-17000 to within one bit
    old = sys.get_int_max_str_digits()
    sys.set_int_max_str_digits(0)
    try:
        r2 = P.prove(dr, 0, dt)
    finally:
        sys.set_int_max_str_digits(old)
    assert (r2.status, r2.reason) == (P.EXHAUSTED, "checker_refused:integer_size_limit")
    assert r2.raw is None and r2.checker.status == "REFUSED"


def test_exhausted_distinguishes_the_prover_budget_from_a_checker_refusal_and_never_reports_truth():
    dr = XC._dr(4.4, (0.6, 0.6, 0.5))
    _, dr_, dt, expected = XC.near_tie_item(dr, 0, 1000, 1, dps=540, dt_bits=1400)
    ok = P.prove(dr_, 0, dt)
    assert ok.status == P.FOUND and ok.raw == expected
    budget = P.prove(dr_, 0, dt, budget=P.Budget(max_sqrt_bits=512))
    assert (budget.status, budget.reason) == (P.EXHAUSTED, "prover_budget:sqrt_bits") and budget.attempts == []
    refused = P.prove(dr_, 0, dt, limits=K2.Limits(order_max=1))
    assert (refused.status, refused.reason) == (P.EXHAUSTED, "checker_refused:order_limit")
    attempts = P.prove(dr_, 0, dt, budget=P.Budget(max_attempts=1, n_margin=-500))
    assert (attempts.status, attempts.reason) == (P.EXHAUSTED, "prover_budget:attempts")
    assert attempts.attempts[0]["reason"] == "not_separated"
    timed = P.prove(dr_, 0, dt, budget=P.Budget(seconds_max=-1))
    assert (timed.status, timed.reason) == (P.EXHAUSTED, "prover_budget:time") and timed.attempts == []
    for r in (budget, refused, attempts, timed):
        assert r.raw is None and not P.verify_found(r)
    # a looser budget / limit turns every EXHAUSTED into FOUND with the same raw: availability only
    assert P.prove(dr_, 0, dt, budget=P.Budget(max_sqrt_bits=4096)).raw == expected
    assert P.prove(dr_, 0, dt, limits=K2.Limits(order_max=10 ** 6)).raw == expected
    assert P.prove(dr_, 0, dt, budget=P.Budget(max_attempts=8, n_margin=-500)).raw == expected


def test_a_too_small_first_guess_grows_and_still_ends_in_found():
    dr = XC._dr(3.3, (0.5, 0.8, 0.2))
    _, dr_, dt, expected = XC.near_tie_item(dr, 1, 140, 1)
    r = P.prove(dr_, 1, dt, budget=P.Budget(n_margin=-150))
    assert r.status == P.FOUND and r.raw == expected and P.verify_found(r)
    assert len(r.attempts) >= 2 and r.attempts[0]["reason"] == "not_separated" and r.attempts[-1]["verdict"] == "VALID"
    assert [a["sqrt_bits"] for a in r.attempts] == sorted(a["sqrt_bits"] for a in r.attempts)


# --- D1 / D2: the estimate hints, the trusted enclosure decides ----------------------------------------------------

@pytest.mark.parametrize("delta", (1, -1, 5))
def test_a_wrong_raw_hint_is_recovered_by_the_enclosure_and_ends_in_found(monkeypatch, delta):
    """D1 (audit hole H1): a wrong hint used to end as ANOMALY forever. Now the checker's raw_mismatch drops the hint,
    checker V2's own enclosure at the same N decides the raw, and one more checker call returns VALID with the true raw."""
    dr = XC._dr(5.0, (0.55, 0.7, 0.3))
    monkeypatch.setattr(P, "_estimate", _fake_estimate(delta))
    count = _CountingChecker(monkeypatch)
    r = P.prove(dr, 0, DT)
    assert count.verdicts == [("INVALID", "raw_mismatch"), ("VALID", "strictly_separated")]   # before verify_found
    assert r.status == P.FOUND and r.raw == _exe(dr)[0] and P.verify_found(r)
    assert [(a["verdict"], a["reason"]) for a in r.attempts] == [("INVALID", "raw_mismatch"), ("ENCLOSURE", "cell"),
                                                                 ("VALID", "strictly_separated")]
    assert r.estimate["hint_rejected"] == _exe(dr)[0] + delta
    assert len({a["sqrt_bits"] for a in r.attempts}) == 1, "the enclosure decides at the same N: no precision is wasted"


def test_a_failed_estimate_ends_nothing_the_enclosure_decides_from_n_128():
    """D2 (audit hole H2): the estimate's own budget runs out, yet the run goes on without a hint."""
    dr = XC._dr(3.3, (0.5, 0.8, 0.2))
    _, dr_, dt, expected = XC.near_tie_item(dr, 1, 300, 1, dps=300, dt_bits=700)
    r = P.prove(dr_, 1, dt, budget=P.Budget(estimate_max_bits=256))
    assert r.status == P.FOUND and r.raw == expected and P.verify_found(r)
    assert r.estimate == {"hint": None, "estimate_failed": "estimate_budget"}
    assert r.attempts[0]["sqrt_bits"] == 128 and r.attempts[0]["verdict"] == "ENCLOSURE"
    ns = [a["sqrt_bits"] for a in r.attempts]
    assert ns == sorted(ns) and ns[-1] > 300 and r.attempts[-1]["verdict"] == "VALID"
    assert all(a["reason"] == "not_separated" for a in r.attempts[:-2])   # it grew N until the enclosure separated


def test_the_enclosure_and_the_checker_disagreeing_is_an_anomaly(monkeypatch):
    """If the raw the enclosure chose is rejected by check_certificate the two paths of the checker disagree: stop."""
    dr = XC._dr(5.0, (0.55, 0.7, 0.3))
    real_cell = P._cell
    monkeypatch.setattr(P, "_cell", lambda J: None if real_cell(J) is None else real_cell(J) + 1)
    r = P.prove(dr, 0, DT, budget=P.Budget(estimate_max_bits=256))
    assert (r.status, r.reason) == (P.ANOMALY, "enclosure_checker_disagree:raw_mismatch") and r.raw is None


# --- ANOMALY: stop, record, never retry into FOUND ----------------------------------------------------------------


def test_an_unexpected_invalid_reason_is_an_anomaly_and_is_not_retried(monkeypatch):
    dr = XC._dr(2.6, (1, 0, 0))
    real = P._exp_plan

    def bad_plan(R, N, Pbits):
        plan = real(R, N, Pbits)
        i = next(i for i, (mode, _) in enumerate(plan) if mode == "full")
        plan[i] = ("full", 0)                           # violates n + 2 > x_hi
        return plan
    monkeypatch.setattr(P, "_exp_plan", bad_plan)
    count = _CountingChecker(monkeypatch)
    r = P.prove(dr, 0, DT)
    assert (r.status, r.reason) == (P.ANOMALY, "checker_exp_condition")
    assert count.calls == 1


# --- static independence, determinism ------------------------------------------------------------------------------

def test_the_prover_never_touches_the_executor_evaluator_or_its_cap():
    tree = ast.parse(PROVER_SRC)
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module)
    assert imported == {"math", "time", "fractions", "mpmath", "a_reference.c1b1_exact_impulse_checker_v2"}
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)} | {n.attr for n in ast.walk(tree)
                                                                          if isinstance(n, ast.Attribute)}
    forbidden = {"_model", "_model_R", "_decide", "impulse", "MAX_PRECISION_BITS", "START_PRECISION_BITS",
                 "c1b1_two_atom", "ar2_lang2024", "a_numeric", "_exp_enclosure", "set_int_max_str_digits"}
    assert not (names & forbidden)
    assert "c1b1_exact_impulse_checker " not in PROVER_SRC.replace("c1b1_exact_impulse_checker_v2", "")


def test_the_same_input_and_budget_give_the_same_certificate_bytes():
    dr = XC._dr(3.3, (0.5, 0.8, 0.2))
    _, dr_, dt, _ = XC.near_tie_item(dr, 1, 100, 1)
    runs = [P.prove(dr_, 1, dt, budget=P.Budget(n_margin=-120)) for _ in range(2)]
    assert runs[0].status == runs[1].status == P.FOUND and len(runs[0].attempts) >= 2
    assert json.dumps(runs[0].certificate, sort_keys=True) == json.dumps(runs[1].certificate, sort_keys=True)
    assert [(a["sqrt_bits"], a["verdict"]) for a in runs[0].attempts] == [(a["sqrt_bits"], a["verdict"]) for a in runs[1].attempts]


# --- fault injection into the prover ------------------------------------------------------------------------------

CHECK_CALL = "        res = K2.check_certificate(cert, limits)\n"
NOT_SEPARATED = ('        if res.reason == "not_separated":\n            N = _grow(N)\n            continue\n')
REFUSED = ('        if res.status == "REFUSED":\n            return ProverResult(EXHAUSTED, "checker_refused:" + res.reason, certificate=cert, checker=res,\n'
           '                                attempts=attempts, estimate=est, budget=budget)\n')


def _run_mutant(mod, dr, k, dt, **kw):
    return mod.prove(dr, k, dt, **kw)


def test_fault_injection_a_prover_that_skips_the_checker_is_caught_by_verification():
    """A generator that declares success itself. The harness re-decides every FOUND with the trusted checker."""
    mod = _mutant((CHECK_CALL, '        res = K2.Result("VALID", m, "skipped", {"seconds": 0.0})\n'))
    dr = XC._dr(5.0, (0.55, 0.7, 0.3))
    mod._estimate = _fake_estimate(1)                 # a wrong guess that only an honest checker would reject
    r = _run_mutant(mod, dr, 0, DT)
    assert r.status == "FOUND" and r.raw == _exe(dr)[0] + 1
    assert not P.verify_found(r), "verification must expose a FOUND the checker never proved"
    honest = P.prove(dr, 0, DT)
    assert honest.found and P.verify_found(honest)


def test_fault_injection_treating_not_separated_as_success_is_caught_by_verification():
    mod = _mutant((NOT_SEPARATED, '        if res.reason == "not_separated":\n            return ProverResult(FOUND, "checker_valid", raw=m, '
                                  'certificate=cert, checker=res, attempts=attempts, estimate=est, budget=budget)\n'))
    dr = XC._dr(3.3, (0.5, 0.8, 0.2))
    _, dr_, dt, expected = XC.near_tie_item(dr, 1, 140, 1)
    bad = _run_mutant(mod, dr_, 1, dt, budget=mod.Budget(n_margin=-150))
    assert bad.status == "FOUND" and bad.attempts[0]["reason"] == "not_separated"
    assert not P.verify_found(bad)
    good = P.prove(dr_, 1, dt, budget=P.Budget(n_margin=-150))
    assert good.found and good.raw == expected and P.verify_found(good)


def _bad_plan_for(mod):
    real = mod._exp_plan

    def bad_plan(R, N, Pbits):
        plan = real(R, N, Pbits)
        i = next(i for i, (mode, _) in enumerate(plan) if mode == "full")
        plan[i] = ("full", 0)                           # violates n + 2 > x_hi: a structural rejection, not a wrong raw
        return plan
    return bad_plan


def test_fault_injection_retrying_an_anomaly_hides_it(monkeypatch):
    """A structural rejection (here exp_condition) must stop. A prover that keeps growing N on it never reports the
    defect. (Since V0.1 a raw_mismatch on a HINT is recovered by design; this is the case that must still stop.)"""
    tail = ('        return ProverResult(ANOMALY, "checker_" + res.reason, certificate=cert, checker=res, attempts=attempts,\n'
            '                            estimate=est, budget=budget)\n')
    mod = _mutant((tail, "        N = _grow(N)\n        continue\n"))
    dr = XC._dr(2.6, (1, 0, 0))
    mod._exp_plan = _bad_plan_for(mod)
    count = _CountingChecker(monkeypatch)
    r = _run_mutant(mod, dr, 0, DT, budget=mod.Budget(max_attempts=4))    # few attempts: N grows 3/2 per retry
    assert r.status != "ANOMALY" and count.calls == 4 and not P.verify_found(r)
    honest_count = count.calls
    monkeypatch.setattr(P, "_exp_plan", _bad_plan_for(P))
    r2 = P.prove(dr, 0, DT)
    assert (r2.status, r2.reason) == (P.ANOMALY, "checker_exp_condition") and count.calls == honest_count + 1


def test_fault_injection_the_v0_rule_a_wrong_hint_is_an_anomaly_is_caught():
    """Mutant restoring V0: raw_mismatch on a hint ends the run. The D1 test must see it."""
    mod = _mutant(('        if res.reason == "raw_mismatch" and not decided:                # a wrong HINT: let the enclosure decide (D1)\n'
                   '            est["hint_rejected"] = m\n            m = None\n            continue\n', ""))
    mod._estimate = _fake_estimate(1)
    dr = XC._dr(5.0, (0.55, 0.7, 0.3))
    r = _run_mutant(mod, dr, 0, DT)
    assert (r.status, r.reason) == ("ANOMALY", "checker_raw_mismatch"), "the V0 behaviour must be visible to the test"


def test_fault_injection_the_v0_rule_a_failed_estimate_ends_the_run_is_caught():
    """Mutant restoring V0: an estimate failure ends the run as EXHAUSTED. The D2 test must see it."""
    mod = _mutant(('    except _Stop as s:                                                  # D2: a failed estimate ends nothing\n'
                   '        est, m, N = {"hint": None, "estimate_failed": s.reason}, None, 128\n',
                   '    except _Stop as s:\n        return ProverResult(s.status, s.reason, attempts=attempts, budget=budget)\n'))
    dr = XC._dr(3.3, (0.5, 0.8, 0.2))
    _, dr_, dt, _ = XC.near_tie_item(dr, 1, 300, 1, dps=300, dt_bits=700)
    r = _run_mutant(mod, dr_, 1, dt, budget=mod.Budget(estimate_max_bits=256))
    assert (r.status, r.reason) == ("EXHAUSTED", "estimate_budget"), "the V0 behaviour must be visible to the test"


def test_fault_injection_an_enclosure_that_ignores_strictness_is_caught_by_the_checker():
    """Mutant: the cell is taken as round(J.lo) without the strict containment test. It picks a raw for a J that still
    straddles a boundary; the checker then does not accept it and the enclosure-checker disagreement stops the run."""
    mod = _mutant(('    if (2 * m - 1) * ulp / 2 < J.lo and J.hi < (2 * m + 1) * ulp / 2:\n        return m\n    return None\n',
                   '    return m\n'))
    dr = XC._dr(3.3, (0.5, 0.8, 0.2))
    _, dr_, dt, expected = XC.near_tie_item(dr, 1, 300, 1, dps=300, dt_bits=700)
    bad = _run_mutant(mod, dr_, 1, dt, budget=mod.Budget(estimate_max_bits=256))
    assert bad.status == "ANOMALY" and bad.reason.startswith("enclosure_checker_disagree")
    good = P.prove(dr_, 1, dt, budget=P.Budget(estimate_max_bits=256))
    assert good.found and good.raw == expected


def test_fault_injection_ignoring_a_checker_refusal_is_caught():
    mod = _mutant((REFUSED, ""))
    dr = XC._dr(4.4, (0.6, 0.6, 0.5))
    _, dr_, dt, _ = XC.near_tie_item(dr, 0, 1000, 1, dps=540, dt_bits=1400)
    lim = K2.Limits(order_max=1)
    honest = P.prove(dr_, 0, dt, limits=lim)
    assert (honest.status, honest.reason) == (P.EXHAUSTED, "checker_refused:order_limit")
    bad = _run_mutant(mod, dr_, 0, dt, limits=lim, budget=mod.Budget(max_attempts=3))
    assert (bad.status, bad.reason) != (P.EXHAUSTED, "checker_refused:order_limit")


def test_fault_injection_an_estimate_that_loses_the_boundary_distance_is_caught_by_the_ladder():
    """If the distance were ignored the first guess would be too small for a deep near-tie; the honest ladder measures it."""
    dr = XC._dr(4.4, (0.6, 0.6, 0.5))
    _, dr_, dt, expected = XC.near_tie_item(dr, 0, 300, 1, dps=300, dt_bits=700)
    r = P.prove(dr_, 0, dt)
    assert r.found and r.estimate["dist_bits"] >= 300 and r.attempts[0]["sqrt_bits"] >= 300 and len(r.attempts) == 1
    blind = P.prove(dr_, 0, dt, budget=P.Budget(n_margin=-r.estimate["dist_bits"] - 10, max_attempts=1))
    assert blind.status == P.EXHAUSTED and blind.attempts[0]["reason"] == "not_separated"
