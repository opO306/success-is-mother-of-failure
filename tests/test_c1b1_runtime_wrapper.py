"""Runtime wrapper V0 (C1-B1): a real STOP -> point prover -> verified witness -> the same step re-run from its start.

W1 only ReferenceUndecided inside an impulse reaches the prover; terminal refusals never do.
W2 a FOUND is re-verified from its certificate bytes: size, JSON, binding, exact input, checker V2 VALID, raw agreement.
W3 the step is re-run from its start.
W4 a witness raw is used only where the executor itself stops again on exactly that input.
W5 NOT_A_DECISION / EXHAUSTED / ANOMALY / checker REFUSED: no progress, run unchanged, no retry of an ANOMALY.
W6 the certificate byte size is bounded before parsing.
W7 wrapper on/off differential; cap-128 rehearsal equals the plain full-cap run at every step.
W8 fault injection (source-text mutants of the wrapper and planted witnesses) must all be caught.
The executor cap is lowered only by these TESTS (the wrapper never touches it).
"""
import ast
import copy
import json
import types
from collections import Counter
from fractions import Fraction as Q
from pathlib import Path

import pytest

import a_reference.c1b1_exact_impulse_checker_v2 as K2
import a_reference.c1b1_point_prover as P
import a_reference.c1b1_runtime_local_witness as W
import a_reference.c1b1_runtime_wrapper as RW
import a_reference.c1b1_stress_survey as X
import a_reference.c1b1_two_atom as C
from a_numeric.profiles import FixedPoint, VMHalt

WRAPPER_SRC = Path(RW.__file__).read_text(encoding="utf-8")
REAL_PROVE = P.prove                  # RW.P is the same module object: fakes must call this, never P.prove
POS, MOM, DT = X.POS, X.MOM, X.DT
ULP = Q(1, 1 << 48)


def mk(e=Q(9), bf=Q(1, 2)):
    st = X.canonical(Q(e), Q(bf) * X.RE)
    return C.new_run(POS, DT, st["r_i"], st["p_i"], st["r_j"], st["p_j"], momentum_profile=MOM)


def plain(n, e=Q(9), bf=Q(1, 2)):
    run, tel = mk(e, bf), X.Telemetry()
    states = [W._raw(run)]
    with X.instrumented(tel):
        for _ in range(n):
            C.step(run)
            states.append(W._raw(run))
    return states, tel


def wrapped(run, n, config=None, cap=None, module=RW):
    states, outs = [W._raw(run)], []

    def go():
        for _ in range(n):
            o = module.step(run, config)
            outs.append(o)
            if not o.advanced:
                return
            states.append(W._raw(run))
    if cap is None:
        go()
    else:
        with W.precision_cap(cap):
            go()
    return states, outs


def _mutant(*replacements, extra=None):
    src = WRAPPER_SRC
    for old, new in replacements:
        assert src.count(old) == 1, f"mutation target must occur exactly once: {old!r} ({src.count(old)}x)"
        src = src.replace(old, new)
    mod = types.ModuleType("mutant_wrapper")
    mod.__file__ = RW.__file__                  # same repository root: the binding hashes the same sources
    mod.__dict__.update(extra or {})
    exec(compile(src, "mutant_wrapper.py", "exec"), mod.__dict__)
    return mod


class _ProverSpy:
    """Replaces P.prove as seen by the wrapper; counts calls and can return a doctored result."""

    def __init__(self, monkeypatch, fake=None):
        self.calls = []
        real = REAL_PROVE

        def prove(dr_raw, k, dt_kick, budget=None, limits=None):
            self.calls.append((tuple(dr_raw), k, Q(dt_kick)))
            return (fake or real)(dr_raw, k, dt_kick, budget, limits)
        monkeypatch.setattr(RW.P, "prove", prove)
        self.real = real


def _first_refusal_state():
    """A run whose next step is refused at cap 128 in the post-drift impulse (e = 9 De, b = Re/2, after 3 steps)."""
    run = mk()
    for _ in range(3):
        C.step(run)
    return run


# --- W7: on/off differential ---------------------------------------------------------------------------------------

@pytest.mark.parametrize("e,bf,n", ((Q(9), Q(1, 2), 300), (Q(1, 2), Q(1, 2), 300)), ids=("e9", "e0.5"))
def test_wrapper_on_off_is_bit_identical_at_the_full_cap_and_never_calls_the_prover(monkeypatch, e, bf, n):
    spy = _ProverSpy(monkeypatch)
    ref, _ = plain(n, e, bf)
    got, outs = wrapped(mk(e, bf), n)
    assert got == ref
    assert Counter(o.status for o in outs) == {RW.RESOLVED: n} and spy.calls == []


@pytest.mark.parametrize("e,bf,n", ((Q(9), Q(1, 2), 1640), (Q(1, 2), Q(1, 2), 5775)), ids=("e9_1640", "e0.5_5775"))
def test_cap_128_rehearsal_equals_the_full_cap_run_at_every_step(e, bf, n):
    ref, tel = plain(n, e, bf)
    got, outs = wrapped(mk(e, bf), n, cap=128)
    assert got == ref, "every raw state, not only the last"
    uses = sum(len(o.witnesses) for o in outs)
    assert uses == tel.decisions[256] >= 20                     # one witness per decision the executor stopped on
    _, _, refusals = W.run_with_local_witnesses(mk(e, bf), n)
    assert Counter(o.status for o in outs)[RW.WITNESS_RESOLVED] == len(refusals)
    assert all(w["prover"]["status"] == P.FOUND for o in outs for w in o.witnesses)
    assert C.MAX_PRECISION_BITS == 16384


def test_a_refusal_in_the_first_impulse_is_resolved_too():
    st = X.canonical(Q(1, 2), Q(0))
    rj = (st["r_j"][0] + 46 * ULP, Q(0), Q(0))                  # needs 256 bits at the very first impulse
    ref = C.new_run(POS, DT, st["r_i"], st["p_i"], rj, st["p_j"], momentum_profile=MOM)
    run = C.new_run(POS, DT, st["r_i"], st["p_i"], rj, st["p_j"], momentum_profile=MOM)
    C.step(ref)
    got, outs = wrapped(run, 1, cap=128)
    assert outs[0].status == RW.WITNESS_RESOLVED and got[-1] == W._raw(ref)


# --- W1: only ReferenceUndecided inside an impulse reaches the prover ----------------------------------------------

def _never_prove(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("the prover must not be called for a terminal refusal")
    monkeypatch.setattr(RW.P, "prove", boom)


def test_terminal_refusals_never_reach_the_prover_and_leave_the_run_unchanged(monkeypatch):
    _never_prove(monkeypatch)
    cases = []
    ri, rj = (Q(0), Q(-1), Q(0)), (Q(-3), Q(1), Q(0))
    pj = (Q(6000), Q(0), Q(0))
    cases.append((C.new_run(POS, 40, ri, tuple(-x for x in pj), rj, pj, momentum_profile=MOM, validated_only=False),
                  "PhysicsDomainExceeded"))
    z = (Q(0),) * 3
    cases.append((C.new_run(POS, DT, z, z, (Q(3), Q(0), Q(0)), z, momentum_profile=FixedPoint(8, 4),
                            validated_only=False), "VMHalt"))
    p, mom = Q(12799, 100), FixedPoint(24, 16)
    cases.append((C.new_run(POS, DT, z, (-p, Q(0), Q(0)), (Q(5), Q(0), Q(0)), (p, Q(0), Q(0)), momentum_profile=mom,
                            validated_only=False), "ExecutorLimitExceeded"))
    for run, name in cases:
        before = dict(vars(run))
        o = RW.step(run)
        assert (o.status, o.reason) == (RW.TERMINAL, name) and dict(vars(run)) == before
    small = FixedPoint(40, 32)
    st = X.canonical(Q(9), Q(0))
    q = -st["p_j"][0]
    run = C.new_run(small, DT, (Q(10799, 100), Q(0), Q(0)), (-q, Q(0), Q(0)), (Q(12799, 100), Q(0), Q(0)),
                    (q, Q(0), Q(0)), momentum_profile=MOM)
    outs = RW.run_steps(run, 200)
    assert (outs[-1].status, outs[-1].reason) == (RW.TERMINAL, "ExecutorLimitExceeded")
    assert all(o.status == RW.RESOLVED for o in outs[:-1])


def test_an_unsupported_profile_stop_is_unproved_not_proved(monkeypatch):
    """A ReferenceUndecided on a momentum profile the certificate format does not cover: no prover, no progress."""
    spy = _ProverSpy(monkeypatch)
    st = X.canonical(Q(9), Q(1, 2) * X.RE)
    mom = FixedPoint(96, 79)
    run = C.new_run(POS, DT, st["r_i"], st["p_i"], st["r_j"], st["p_j"], momentum_profile=mom)
    outs = wrapped(run, 400, cap=128)[1]
    assert (outs[-1].status, outs[-1].reason) == (RW.UNPROVED, "unsupported_profile") and spy.calls == []


# --- W5: prover results that must not advance ----------------------------------------------------------------------

@pytest.mark.parametrize("status,reason", ((P.NOT_A_DECISION, "zero_component"), (P.EXHAUSTED, "prover_budget:attempts"),
                                           (P.EXHAUSTED, "checker_refused:order_limit"), (P.ANOMALY, "checker_raw_mismatch")))
def test_non_found_prover_results_stop_without_progress_and_anomaly_is_not_retried(monkeypatch, status, reason):
    spy = _ProverSpy(monkeypatch, fake=lambda *a: P.ProverResult(status, reason))
    run = _first_refusal_state()
    before = dict(vars(run))
    with W.precision_cap(128):
        o = RW.step(run)
    assert (o.status, o.reason) == (RW.UNPROVED, status.lower() + ":" + reason)
    assert dict(vars(run)) == before and len(spy.calls) == 1 and o.prover["status"] == status


# --- W2 / W4 / W8: planted witnesses ---------------------------------------------------------------------------------

def _doctored(transform):
    """A fake prover: the real FOUND, then `transform(result, dr_raw, k, dt)` returns the doctored result."""
    def fake(dr_raw, k, dt_kick, budget=None, limits=None):
        r = REAL_PROVE(dr_raw, k, dt_kick, budget, limits)
        assert r.found
        return transform(r, list(dr_raw), k, Q(dt_kick))
    return fake


def _with_cert(r, cert, raw=None):
    return P.ProverResult(P.FOUND, "checker_valid", raw=r.raw if raw is None else raw, certificate=cert, checker=r.checker,
                          attempts=r.attempts, estimate=r.estimate)


def _raw_plus_one(r, dr, k, dt):
    cert = copy.deepcopy(r.certificate)
    cert["output"]["raw"] = str(r.raw + 1)
    return _with_cert(r, cert, r.raw + 1)


def _claim_only_wrong(r, dr, k, dt):
    return _with_cert(r, r.certificate, r.raw + 1)


def _consistent_forgery(other):
    """A certificate for ANOTHER input together with ITS raw: internally consistent, so only the input check can stop
    it (the raw-agreement check alone would not)."""
    return _with_cert(other, other.certificate, other.raw)


def _other_dr(r, dr, k, dt):
    other = list(dr)
    other[0] += 1
    return _consistent_forgery(REAL_PROVE(other, k, dt))


def _other_component(r, dr, k, dt):
    j = next(j for j in range(3) if j != k and dr[j] != 0)
    return _consistent_forgery(REAL_PROVE(dr, j, dt))


def _other_dt(r, dr, k, dt):
    return _consistent_forgery(REAL_PROVE(dr, k, dt + Q(1, 1000)))


PLANTED = [("wrong raw in the certificate", _raw_plus_one, "checker_invalid:raw_mismatch"),
           ("wrong raw claimed", _claim_only_wrong, "raw_disagrees"),
           ("certificate for another dr", _other_dr, "input_mismatch"),
           ("certificate for another component", _other_component, "input_mismatch"),
           ("certificate for another dt", _other_dt, "input_mismatch")]


@pytest.mark.parametrize("label,transform,reason", PLANTED, ids=[p[0] for p in PLANTED])
def test_planted_witnesses_are_rejected_and_the_run_does_not_move(monkeypatch, label, transform, reason):
    _ProverSpy(monkeypatch, fake=_doctored(transform))
    run = _first_refusal_state()
    before = dict(vars(run))
    with W.precision_cap(128):
        o = RW.step(run)
    assert (o.status, o.reason) == (RW.UNPROVED, reason) and dict(vars(run)) == before


def test_a_stale_binding_is_rejected(monkeypatch):
    real = RW.witness_bytes

    def stale(cert, run):
        doc = json.loads(real(cert, run))
        doc["runtime_binding"]["executor_sha256"] = "0" * 64
        return json.dumps(doc, sort_keys=True, separators=(",", ":")).encode()
    monkeypatch.setattr(RW, "witness_bytes", stale)
    run = _first_refusal_state()
    before = dict(vars(run))
    with W.precision_cap(128):
        o = RW.step(run)
    assert (o.status, o.reason) == (RW.UNPROVED, "stale_binding") and dict(vars(run)) == before


def test_a_checker_refusal_on_reverification_does_not_advance(monkeypatch):
    _ProverSpy(monkeypatch, fake=lambda dr, k, dt, b=None, l=None: REAL_PROVE(dr, k, dt))   # prover under default limits
    run = _first_refusal_state()
    before = dict(vars(run))
    with W.precision_cap(128):
        o = RW.step(run, RW.Config(limits=K2.Limits(order_max=1)))
    assert (o.status, o.reason) == (RW.UNPROVED, "checker_refused:order_limit") and dict(vars(run)) == before


# --- W6: byte size before parsing ------------------------------------------------------------------------------------

def test_the_byte_limit_applies_before_parsing_and_only_limits_availability(monkeypatch):
    calls = []
    real_loads = json.loads

    def counting(data, *a, **k):
        calls.append(len(data))
        return real_loads(data, *a, **k)
    monkeypatch.setattr(RW.json, "loads", counting)
    run = _first_refusal_state()
    before = dict(vars(run))
    with W.precision_cap(128):
        o = RW.step(run, RW.Config(max_certificate_bytes=100))
    assert (o.status, o.reason) == (RW.UNPROVED, "certificate_too_large") and dict(vars(run)) == before
    assert calls == [], "json.loads must not run on an oversized certificate"
    key = RW._key(tuple(Q(1) for _ in range(3)), 0, Q(20), MOM)
    with pytest.raises(RW._Reject) as e:
        RW.verify_witness(b"x" * 5_000_000, key, run, 0, RW.Config())
    assert e.value.reason == "certificate_too_large" and calls == []
    with pytest.raises(RW._Reject) as e:
        RW.verify_witness(b"{", key, run, 0, RW.Config())
    assert e.value.reason == "bad_json"
    ref = _first_refusal_state()
    C.step(ref)
    with W.precision_cap(128):
        o2 = RW.step(run, RW.Config(max_certificate_bytes=1 << 20))
    assert o2.status == RW.WITNESS_RESOLVED and W._raw(run) == W._raw(ref)


# --- W4: a witness never overrides a decision the executor makes ----------------------------------------------------

def test_a_witness_for_an_input_the_executor_decides_is_ignored():
    dr = (Q(7) + 3 * ULP, Q(2), Q(0))
    honest = C.impulse(dr, DT / 2, MOM)
    table = {RW._key(dr, 0, DT / 2, MOM): honest[0] + 12345}
    stops, used = [], []
    with RW._hooks(table, stops, used):
        got = C.impulse(dr, DT / 2, MOM)
    assert got == honest and used == [] and stops == []
    assert C.impulse is not None and C.impulse.__module__ == "a_reference.c1b1_two_atom"
    assert C._decide.__module__ == "a_reference.c1b1_two_atom"


def test_the_hooks_are_restored_on_every_exit_path(monkeypatch):
    _ProverSpy(monkeypatch, fake=lambda *a: P.ProverResult(P.ANOMALY, "x"))
    run = _first_refusal_state()
    with W.precision_cap(128):
        RW.step(run)
    assert C.impulse.__module__ == "a_reference.c1b1_two_atom" and C._decide.__module__ == "a_reference.c1b1_two_atom"
    ri, rj = (Q(0), Q(-1), Q(0)), (Q(-3), Q(1), Q(0))
    pj = (Q(6000), Q(0), Q(0))
    bad = C.new_run(POS, 40, ri, tuple(-x for x in pj), rj, pj, momentum_profile=MOM, validated_only=False)
    RW.step(bad)
    assert C.impulse.__module__ == "a_reference.c1b1_two_atom" and C._decide.__module__ == "a_reference.c1b1_two_atom"


# --- static independence --------------------------------------------------------------------------------------------

def test_the_wrapper_never_touches_the_precision_cap_or_the_evaluator_or_v1():
    tree = ast.parse(WRAPPER_SRC)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AugAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for t in targets:
                for n in ast.walk(t):
                    assert not (isinstance(n, ast.Attribute) and n.attr in ("MAX_PRECISION_BITS", "START_PRECISION_BITS"))
    names = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    assert not (names & {"_model", "_model_R", "_exp_enclosure", "MAX_PRECISION_BITS"})
    imported = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    assert "a_reference.c1b1_exact_impulse_checker" not in imported


# --- W8: mutants of the wrapper ---------------------------------------------------------------------------------------

CHECK = "    res = K2.check_certificate(cert, config.limits)\n"
INPUT_CHECK = '        raise _Reject("input_mismatch")\n'
BINDING_CHECK = '        raise _Reject("stale_binding")\n'
STORE = "            table[key] = raw\n"
RERUN = "            continue                                                    # W3: the same step again, from its start\n"


def _state_after_one_wrapped_step(module, monkeypatch, fake=None, config=None):
    if fake is not None:
        monkeypatch.setattr(module.P, "prove", fake)
    run = _first_refusal_state()
    with W.precision_cap(128):
        o = module.step(run, config)
    return o, W._raw(run)


def _reference_after_one_step():
    ref = _first_refusal_state()
    C.step(ref)
    return W._raw(ref)


def test_mutant_without_the_checker_accepts_a_wrong_raw_and_the_differential_catches_it(monkeypatch):
    honest, _ = _state_after_one_wrapped_step(RW, monkeypatch, _doctored(_raw_plus_one))
    assert honest.status == RW.UNPROVED
    mod = _mutant((CHECK, '    res = K2.Result("VALID", claimed_raw, "skipped", {})\n'))
    o, state = _state_after_one_wrapped_step(mod, monkeypatch, _doctored(_raw_plus_one))
    assert o.status == "WITNESS_RESOLVED" and state != _reference_after_one_step()


@pytest.mark.parametrize("forgery", (_other_dr, _other_component, _other_dt), ids=("dr", "component", "dt"))
def test_mutant_without_the_input_check_accepts_a_consistent_forgery(monkeypatch, forgery):
    honest, _ = _state_after_one_wrapped_step(RW, monkeypatch, _doctored(forgery))
    assert (honest.status, honest.reason) == (RW.UNPROVED, "input_mismatch")
    mod = _mutant((INPUT_CHECK, "        pass\n"))
    o, state = _state_after_one_wrapped_step(mod, monkeypatch, _doctored(forgery))
    assert o.status == "WITNESS_RESOLVED", "only the input check stops a consistent forgery"
    if forgery is not _other_dt:                  # a nearby dt can round to the same raw: then the state may agree
        assert state != _reference_after_one_step()


def test_mutant_without_the_binding_check_accepts_a_stale_witness(monkeypatch):
    real = RW.witness_bytes

    def stale(cert, run):
        doc = json.loads(real(cert, run))
        doc["runtime_binding"]["dt"] = "41"
        return json.dumps(doc, sort_keys=True, separators=(",", ":")).encode()
    monkeypatch.setattr(RW, "witness_bytes", stale)
    honest, _ = _state_after_one_wrapped_step(RW, monkeypatch)
    assert (honest.status, honest.reason) == (RW.UNPROVED, "stale_binding")
    mod = _mutant((BINDING_CHECK, "        pass\n"))
    monkeypatch.setattr(mod, "witness_bytes", stale)
    o, _ = _state_after_one_wrapped_step(mod, monkeypatch)
    assert o.status == "WITNESS_RESOLVED", "the binding test must see a mutant that ignores the binding"


def test_mutant_that_resumes_without_the_witness_never_progresses(monkeypatch):
    mod = _mutant((STORE, "            pass\n"))
    o, _ = _state_after_one_wrapped_step(mod, monkeypatch)
    assert o.status == "UNPROVED" and o.reason == "attempt_limit"
    honest, state = _state_after_one_wrapped_step(RW, monkeypatch)
    assert honest.status == RW.WITNESS_RESOLVED and state == _reference_after_one_step()


def _resume_mid_step(run, key, raw):
    """DEFECT FOR THE TEST: continue from the failed impulse with the witness instead of re-running the step."""
    J = [0, 0, 0]
    J[key[1]] = raw
    run.atoms = C._kick(run.mom, run.atoms, tuple(J))
    run.J_cache = tuple(J)
    run.t_steps += 1


def test_mutant_that_resumes_in_the_middle_of_the_step_is_caught_by_the_differential(monkeypatch):
    mod = _mutant((RERUN, "            _resume_mid_step(run, key, raw)\n"
                          "            return StepOutcome(WITNESS_RESOLVED, 'advanced', records, stop_log)\n"),
                  extra={"_resume_mid_step": _resume_mid_step})
    o, state = _state_after_one_wrapped_step(mod, monkeypatch)
    assert o.status == "WITNESS_RESOLVED" and state != _reference_after_one_step()


def test_mutant_whose_hook_prefers_the_witness_overrides_an_executor_decision():
    mod = _mutant(("        try:\n            return orig_decide(profile, value_at)\n        except C.ReferenceUndecided:\n"
                   "            key = _key(dr, k, dt_kick, prof)\n",
                   "        key = _key(dr, k, dt_kick, prof)\n        if key in table:\n            used.append(key)\n"
                   "            return table[key]\n        try:\n            return orig_decide(profile, value_at)\n"
                   "        except C.ReferenceUndecided:\n"))
    dr = (Q(7) + 3 * ULP, Q(2), Q(0))
    honest = C.impulse(dr, DT / 2, MOM)
    table = {RW._key(dr, 0, DT / 2, MOM): honest[0] + 12345}
    with mod._hooks(table, [], []):
        got = C.impulse(dr, DT / 2, MOM)
    assert got != honest, "the W4 test must see a hook that overrides a decision the executor makes"


# --- profile identity: a look-alike of the canonical half-even FX must never receive a witness --------------------------

import a_numeric.profiles as PR                 # noqa: E402


def _half_up(p, value):
    """Ties away from zero: a different rounding rule behind the same name/width/frac_bits."""
    x = Q(value) * (1 << p.frac_bits)
    q = (2 * abs(x.numerator) + x.denominator) // (2 * x.denominator)
    return p._check(q if x >= 0 else -q)


class _HalfUpFX(FixedPoint):
    """FORGERY FOR THE TEST: a FixedPoint subclass whose from_exact rounds ties away from zero."""

    def from_exact(self, value):
        return _half_up(self, value)


class _OtherToExactFX(FixedPoint):
    """FORGERY FOR THE TEST: a FixedPoint subclass whose to_exact differs at one raw."""

    def to_exact(self, v):
        return Q(v, 1 << self.frac_bits) + (Q(1, 1 << 200) if v == 12345 else 0)


class _LookAlikeFX:
    """FORGERY FOR THE TEST: not a FixedPoint at all; same name/width/frac_bits/lo/hi, half-up from_exact."""

    def __init__(self, width, frac_bits):
        self._real = FixedPoint(width, frac_bits)
        self.name, self.width, self.frac_bits = self._real.name, width, frac_bits
        self.lo, self.hi = self._real.lo, self._real.hi

    def from_exact(self, value):
        return _half_up(self._real, value)

    def __getattr__(self, name):
        return getattr(self._real, name)


def _instance_override(width, frac_bits):
    p = FixedPoint(width, frac_bits)
    p.from_exact = types.MethodType(_half_up, p)          # the real class, a forged bound method on the instance
    return p


def _half_up_div_round(num, den):
    q, r = divmod(abs(num), abs(den))
    q += 2 * r >= abs(den)
    return q if (num < 0) == (den < 0) else -q


FORGED = {
    "subclass_from_exact": lambda mp: ("mom", _HalfUpFX(96, 80)),
    "subclass_to_exact": lambda mp: ("mom", _OtherToExactFX(96, 80)),
    "look_alike": lambda mp: ("mom", _LookAlikeFX(96, 80)),
    "instance_override": lambda mp: ("mom", _instance_override(96, 80)),
    "position_subclass": lambda mp: ("pos", _HalfUpFX(96, 48)),
    "class_method_patched": lambda mp: (mp.setattr(FixedPoint, "from_exact", lambda self, v: _half_up(self, v)),
                                        ("mom", FixedPoint(96, 80)))[1],
    "module_rounding_patched": lambda mp: (mp.setattr(PR, "_div_round", _half_up_div_round),
                                           ("mom", FixedPoint(96, 80)))[1],
}


def _refusal_state_with(which, profile):
    """_first_refusal_state with one profile replaced: the forgeries agree with half-even off exact ties, so the
    trajectory and the cap-128 stop in the 4th step are the same."""
    st = X.canonical(Q(9), Q(1, 2) * X.RE)
    pos, mom = (profile, MOM) if which == "pos" else (POS, profile)
    run = C.new_run(pos, DT, st["r_i"], st["p_i"], st["r_j"], st["p_j"], momentum_profile=mom)
    for _ in range(3):
        C.step(run)
    return run


def test_the_canonical_profiles_pass_the_identity_check_and_are_bound_with_their_source():
    run = _first_refusal_state()
    assert RW._supported(run)
    b = RW.binding(run)
    assert b["profiles_sha256"] == RW._lf_sha256("a_numeric/profiles.py")
    for key, frac in (("position_profile", 48), ("momentum_profile", 80)):
        assert b[key] == {"impl": "a_numeric.profiles.FixedPoint", "name": f"FX(96,{frac})", "width": 96,
                          "frac_bits": frac, "rounding": "half_even"}
    assert "rounding" not in b, "no free-standing rounding declaration: it comes from the checked profile"


@pytest.mark.parametrize("forgery", sorted(FORGED))
def test_a_forged_profile_with_the_same_metadata_never_reaches_the_prover(monkeypatch, forgery):
    which, profile = FORGED[forgery](monkeypatch)
    assert (profile.name, profile.width, profile.frac_bits) == ((MOM if which == "mom" else POS).name, 96,
                                                               80 if which == "mom" else 48)
    spy = _ProverSpy(monkeypatch)
    run = _refusal_state_with(which, profile)
    before = dict(vars(run))
    with W.precision_cap(128):
        o = RW.step(run)
    assert (o.status, o.reason) == (RW.UNPROVED, "unsupported_profile")
    assert spy.calls == [] and o.stops and dict(vars(run)) == before
    assert RW.binding(run)[f"{'momentum' if which == 'mom' else 'position'}_profile"]["rounding"] == "unverified"
    with pytest.raises(RW._Reject, match="unsupported_profile"):   # the byte path refuses before reading the bytes
        RW.verify_witness(b"{}", None, run, 0, RW.Config())


OLD_GATE = "    return _canonical_fx(run.pos, 96, K2.POSITION_FRAC_BITS) and _canonical_fx(run.mom, 96, 80)\n"


def test_mutant_with_the_metadata_only_gate_gives_a_forged_profile_a_half_even_witness(monkeypatch):
    """The V0 defect: name/width/frac_bits alone let a half-up FX(96,80) receive a raw proven for half-even."""
    mod = _mutant((OLD_GATE, "    return ((run.pos.name, run.pos.width, run.pos.frac_bits) == ('FX(96,48)', 96, 48)\n"
                             "            and (run.mom.name, run.mom.width, run.mom.frac_bits) == ('FX(96,80)', 96, 80))\n"))
    run = _refusal_state_with("mom", _HalfUpFX(96, 80))
    with W.precision_cap(128):
        o = mod.step(run)
    assert o.status == "WITNESS_RESOLVED", "the identity test must see a gate that trusts the metadata"
    honest = _refusal_state_with("mom", _HalfUpFX(96, 80))
    with W.precision_cap(128):
        assert RW.step(honest).reason == "unsupported_profile"


def test_a_binding_with_another_profiles_source_is_stale(monkeypatch):
    real = RW.witness_bytes

    def stale(cert, run):
        doc = json.loads(real(cert, run))
        doc["runtime_binding"]["profiles_sha256"] = "0" * 64
        return json.dumps(doc, sort_keys=True, separators=(",", ":")).encode()
    monkeypatch.setattr(RW, "witness_bytes", stale)
    run = _first_refusal_state()
    before = dict(vars(run))
    with W.precision_cap(128):
        o = RW.step(run)
    assert (o.status, o.reason) == (RW.UNPROVED, "stale_binding") and dict(vars(run)) == before


@pytest.mark.parametrize("target,replacement,forgery", (
    ("    if type(p) is not FixedPoint or set(vars(p)) != _FX_ATTRS:\n",
     "    if not isinstance(p, FixedPoint) or set(vars(p)) != _FX_ATTRS:\n", "subclass_to_exact"),
    ("    return probe == [0, 2, 2, 0, -2, -2] and inverse\n", "    return True\n", "module_rounding_patched"),
), ids=("isinstance_instead_of_type_identity", "no_tie_probe"))
def test_mutants_of_the_identity_check_let_a_forgery_reach_the_prover(monkeypatch, target, replacement, forgery):
    """Each layer is load-bearing: isinstance admits a subclass whose to_exact differs (it passes the probe), and
    without the probe a module-level rounding patch passes every identity check."""
    mod = _mutant((target, replacement))
    which, profile = FORGED[forgery](monkeypatch)
    spy = _ProverSpy(monkeypatch)
    run = _refusal_state_with(which, profile)
    with W.precision_cap(128):
        o = mod.step(run)
    assert spy.calls, "the identity test must see this mutant send a forged profile to the prover"
    assert o.reason != "unsupported_profile"


# --- UNREPRESENTABLE: a contract violation at the canonical dt, a plain UNPROVED elsewhere (designer verdict 2026-09-30) -

def test_the_canonical_dt_is_the_domain_contract_dt():
    import a_reference.c1b1_domain_contract as DC
    assert RW.CANONICAL_DT == DC.PROFILE["dt"] == Q(40)


def test_unrepresentable_at_the_canonical_dt_is_a_runtime_contract_violation_and_the_run_is_untouched(monkeypatch):
    """D4 proves |J| <= 1277.3 a.u. at dt = 40, so UNREPRESENTABLE there is not a world event: the wrapper fails loudly
    (not TERMINAL, not UNPROVED), with the run unchanged and the executor hooks restored."""
    _ProverSpy(monkeypatch, fake=lambda *a: P.ProverResult(P.UNREPRESENTABLE, "output_out_of_range"))
    run = _first_refusal_state()
    before = dict(vars(run))
    orig = (C.impulse, C._decide)
    with W.precision_cap(128):
        with pytest.raises(RW.RuntimeContractViolation, match="UNREPRESENTABLE at dt = 40"):
            RW.step(run)
    assert dict(vars(run)) == before and (C.impulse, C._decide) == orig


def test_unrepresentable_elsewhere_is_an_ordinary_unproved_reason(monkeypatch):
    _ProverSpy(monkeypatch, fake=lambda *a: P.ProverResult(P.UNREPRESENTABLE, "output_out_of_range"))
    st = X.canonical(Q(9), Q(1, 2) * X.RE)
    run = C.new_run(POS, Q(41), st["r_i"], st["p_i"], st["r_j"], st["p_j"], momentum_profile=MOM)
    key = (tuple(Q(v, 1 << 48) for v in (5 << 48, 3 << 48, 0)), 0, Q(41, 2), MOM.name, 96, 80)
    with pytest.raises(RW._Reject) as e:
        RW._prove_and_verify(key, run, RW.Config())
    assert e.value.reason == "unrepresentable:output_out_of_range"
