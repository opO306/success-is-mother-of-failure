"""C1-B1 runtime wrapper V0: a real STOP -> point prover -> verified witness -> the same step re-run from its start.

Contract: docs/active/C1B1_RUNTIME_WRAPPER_V0.md (designer conditions W1-W8, 2026-09-30). No Proof Cache: the witness
table lives for one step only.

W1  The prover is called ONLY when an impulse component's rounding ends in ReferenceUndecided inside the executor's
    impulse. PhysicsDomainExceeded, ExecutorLimitExceeded and VMHalt are TERMINAL and never reach the prover.
W2  A FOUND is not trusted: its certificate (with the runtime binding attached) is serialized, and from those BYTES the
    wrapper checks size, JSON, binding, exact input identity, checker V2 VALID and raw agreement before using it.
W3  The step is re-run from its START (the executor's step changes the run only in its last three lines, so a refused
    attempt leaves the run untouched; asserted on every refusal).
W4  During the re-run a witness raw is returned only where the executor ITSELF raises ReferenceUndecided again on
    exactly that input (dr, component, dt_kick, momentum profile). It never replaces a decision the executor makes.
W5  NOT_A_DECISION / EXHAUSTED / ANOMALY / checker REFUSED: UNPROVED, run unchanged, no progress; an ANOMALY is never
    retried.
W6  The certificate byte size is bounded BEFORE json parsing (availability only).
Profile identity: a witness is proven for the canonical half-even a_numeric.profiles.FixedPoint only, so both run
    profiles must BE that class (type identity, no subclass or look-alike, unchanged methods, tie probe); matching
    name/width/frac_bits is not enough. The binding records profiles.py's LF SHA-256 and the checked rounding.

The executor's source is not modified: C.impulse and C._decide are wrapped for the duration of one step and restored
on every exit path (not thread-safe, like the witness prototype). The wrapper never reads or changes the precision cap.
Proof Cache (optional, Config.cache): at a STOP the cache is asked first; whatever it returns has been re-verified from its
bytes by verify_witness. A miss or any failure falls back to the prover. The wrapper never writes to a cache: admission is
the caller's layer (a_reference/c1b1_proof_cache.py), which is also the only place that may know the precision cap.
"""
import hashlib
import json
from contextlib import contextmanager
from fractions import Fraction as Q
from pathlib import Path

import a_reference.ar2_lang2024 as L
import a_reference.c1b1_exact_impulse_checker_v2 as K2
import a_reference.c1b1_point_prover as P
import a_reference.c1b1_two_atom as C
from a_numeric.profiles import FixedPoint, VMHalt

VERSION = "c1b1-runtime-wrapper-v0"
ROOT = Path(__file__).resolve().parents[1]
RESOLVED, WITNESS_RESOLVED, UNPROVED, TERMINAL = "RESOLVED", "WITNESS_RESOLVED", "UNPROVED", "TERMINAL"
TERMINAL_EXCEPTIONS = (C.PhysicsDomainExceeded, C.ExecutorLimitExceeded, VMHalt)


def _lf_sha256(rel):
    return hashlib.sha256((ROOT / rel).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


_FX_METHODS = {n: FixedPoint.__dict__[n] for n in ("from_exact", "to_exact", "_check")}   # what the executor calls
_FX_ATTRS = {"width", "frac_bits", "lo", "hi", "name"}
_HALF = Q(1, 2)


def _canonical_fx(p, width, frac_bits):
    """True only for the real a_numeric.profiles.FixedPoint(width, frac_bits) with half-even rounding: the exact class
    (no subclass, no look-alike), no instance attribute beyond the constructor's, the class methods the executor calls
    unchanged since import, and a known-answer tie probe. Matching name/width/frac_bits alone is never enough."""
    if type(p) is not FixedPoint or set(vars(p)) != _FX_ATTRS:
        return False
    if (p.width, p.frac_bits, p.name) != (width, frac_bits, f"FX({width},{frac_bits})"):
        return False
    if (p.lo, p.hi) != (-(1 << (width - 1)), (1 << (width - 1)) - 1):
        return False
    if any(FixedPoint.__dict__.get(n) is not f for n, f in _FX_METHODS.items()):
        return False
    u = Q(1, 1 << frac_bits)
    try:                                                                # ties go to even, both signs; exact inverse
        probe = [p.from_exact(s * t * u) for s in (1, -1) for t in (_HALF, 3 * _HALF, 5 * _HALF)]
        inverse = p.to_exact(3) == 3 * u and p.to_exact(-5) == -5 * u
    except Exception:
        return False
    return probe == [0, 2, 2, 0, -2, -2] and inverse


def _profile_id(p):
    """The binding's profile record. 'rounding' says half_even only when _canonical_fx checked it, never by default."""
    width, frac_bits = getattr(p, "width", None), getattr(p, "frac_bits", None)
    canonical = isinstance(width, int) and isinstance(frac_bits, int) and _canonical_fx(p, width, frac_bits)
    return {"impl": f"{type(p).__module__}.{type(p).__qualname__}", "name": getattr(p, "name", None),
            "width": width, "frac_bits": frac_bits, "rounding": "half_even" if canonical else "unverified"}


def binding(run):
    """Everything a witness depends on besides the mathematical claim. Any difference makes a witness stale."""
    return {"wrapper": VERSION,
            "checker": {"format": K2.FORMAT, "method": K2.METHOD,
                        "source_sha256": _lf_sha256("a_reference/c1b1_exact_impulse_checker_v2.py")},
            "executor_sha256": _lf_sha256("a_reference/c1b1_two_atom.py"),
            "model_sha256": _lf_sha256("a_reference/ar2_lang2024.py"),
            "model_fingerprint": L.parameter_fingerprint(),
            "profiles_sha256": _lf_sha256("a_numeric/profiles.py"),
            "position_profile": _profile_id(run.pos), "momentum_profile": _profile_id(run.mom),
            "dt": str(Q(run.dt)), "dt_kick": str(Q(run.dt) / 2), "drift": run.drift,
            "retardation": L.WORLD_RETARDATION}


def _key(dr, k, dt_kick, profile):
    return (tuple(Q(x) for x in dr), int(k), Q(dt_kick), profile.name, getattr(profile, "width", None),
            getattr(profile, "frac_bits", None))


def _supported(run):
    """The certificate format covers only the canonical half-even FX(96,48) position / FX(96,80) momentum."""
    return _canonical_fx(run.pos, 96, K2.POSITION_FRAC_BITS) and _canonical_fx(run.mom, 96, 80)


def _dr_raw(dr):
    """The FX(96,48) raws of an exact relative position, or None if it is not on the 2^-48 grid."""
    out = []
    for x in dr:
        v = Q(x) * (1 << K2.POSITION_FRAC_BITS)
        if v.denominator != 1:
            return None
        out.append(int(v))
    return out


class Config:
    def __init__(self, budget=None, limits=None, max_certificate_bytes=262144, max_attempts_per_step=8, cache=None):
        self.budget, self.limits, self.cache = budget, limits, cache
        self.max_certificate_bytes, self.max_attempts_per_step = max_certificate_bytes, max_attempts_per_step


class StepOutcome:
    def __init__(self, status, reason, witnesses=None, stops=None, prover=None, exception=None, new_certificates=None):
        self.status, self.reason = status, reason
        self.witnesses, self.stops = witnesses or [], stops or []
        self.prover, self.exception = prover, exception
        self.new_certificates = new_certificates or []    # [(stop key, bytes)] the prover made; for an admission layer

    def __repr__(self):
        return f"StepOutcome({self.status}, {self.reason}, witnesses={len(self.witnesses)})"

    @property
    def advanced(self):
        return self.status in (RESOLVED, WITNESS_RESOLVED)


class _Reject(Exception):
    """A witness that may not be used (reason) and, when the prover was the cause, its result summary."""

    def __init__(self, reason, prover=None):
        super().__init__(reason)
        self.reason, self.prover = reason, prover


def witness_bytes(certificate, run):
    """The canonical bytes a witness is verified from (runtime binding attached)."""
    doc = dict(certificate)
    doc["runtime_binding"] = binding(run)
    return json.dumps(doc, sort_keys=True, separators=(",", ":")).encode("utf-8")


def verify_witness(data, key, run, claimed_raw, config):
    """W2: from BYTES. Returns the raw or raises _Reject(reason). Nothing in the bytes is trusted but what is checked."""
    if not _supported(run):                                             # a look-alike profile is never bound
        raise _Reject("unsupported_profile")
    if not isinstance(data, (bytes, bytearray)):
        raise _Reject("not_bytes")
    if len(data) > config.max_certificate_bytes:                         # W6: before any parsing
        raise _Reject("certificate_too_large")
    try:
        cert = json.loads(data)
    except (ValueError, RecursionError):
        raise _Reject("bad_json")
    if not isinstance(cert, dict) or cert.get("runtime_binding") != binding(run):
        raise _Reject("stale_binding")
    dr, k, dt_kick = key[0], key[1], key[2]
    inp = cert.get("input")
    expected_dr = _dr_raw(dr)
    if not (isinstance(inp, dict) and expected_dr is not None
            and inp.get("dr_raw") == [str(v) for v in expected_dr] and inp.get("component") == k
            and isinstance(inp.get("dt_kick"), str) and _same_rational(inp.get("dt_kick"), dt_kick)):
        raise _Reject("input_mismatch")
    res = K2.check_certificate(cert, config.limits)
    if res.status == "REFUSED":
        raise _Reject("checker_refused:" + res.reason)
    if not res.valid:
        raise _Reject("checker_invalid:" + res.reason)
    if claimed_raw is not None and res.raw != claimed_raw:            # None: no outside claim (a cached witness)
        raise _Reject("raw_disagrees")
    return res.raw


def _same_rational(s, value):
    try:
        return Q(s) == Q(value)
    except (ValueError, ZeroDivisionError):
        return False


@contextmanager
def _hooks(table, stops, used):
    """Wrap C.impulse and C._decide for one step (W1, W4). Restored on every exit path."""
    orig_impulse, orig_decide = C.impulse, C._decide
    state = {"active": None}

    def impulse(dr, dt_kick, profile):
        ks = [k for k, x in enumerate(dr) if x * dt_kick != 0]           # the components impulse decides, in order
        state["active"] = (tuple(dr), dt_kick, profile, iter(ks))
        try:
            return orig_impulse(dr, dt_kick, profile)
        finally:
            state["active"] = None

    def decide(profile, value_at):
        active = state["active"]
        if active is None:                                              # not inside a step's impulse: untouched
            return orig_decide(profile, value_at)
        dr, dt_kick, prof, ks = active
        k = next(ks)
        try:
            return orig_decide(profile, value_at)
        except C.ReferenceUndecided:
            key = _key(dr, k, dt_kick, prof)
            if key in table:                                            # the executor itself stopped here again
                used.append(key)
                return table[key]
            stops.append(key)
            raise

    C.impulse, C._decide = impulse, decide
    try:
        yield
    finally:
        C.impulse, C._decide = orig_impulse, orig_decide


def _prove_and_verify(key, run, config):
    """Returns (raw, witness record) or raises _Reject(reason) / returns the prover result in the reason."""
    dr, k, dt_kick = key[0], key[1], key[2]
    dr_raw = _dr_raw(dr)
    if dr_raw is None:
        raise _Reject("unsupported_profile")
    result = P.prove(dr_raw, k, dt_kick, config.budget, config.limits)
    summary = {"status": result.status, "reason": result.reason,
               "attempts": [(a["sqrt_bits"], a["verdict"]) for a in result.attempts]}
    if result.status != P.FOUND:                                        # W5: no progress, no retry of an ANOMALY
        raise _Reject(result.status.lower() + ":" + result.reason, summary)
    data = witness_bytes(result.certificate, run)
    raw = verify_witness(data, key, run, result.raw, config)
    return raw, witness_record(key, raw, data, "prover", prover=summary), data


def witness_record(key, raw, data, source, prover=None, **extra):
    """What a WITNESS_RESOLVED step records per witness: the content address of the exact bytes it was verified from."""
    rec = {"key": [[str(x) for x in key[0]], key[1], str(key[2])], "raw": raw, "source": source,
           "certificate_sha256": hashlib.sha256(data).hexdigest(), "certificate_bytes": len(data), "prover": prover}
    rec.update(extra)
    return rec


def _run_step(run, table, stops, used):
    """One attempt of the executor's step, from its start."""
    with _hooks(table, stops, used):
        C.step(run)


def step(run, config=None):
    """Advance run by one step under the wrapper. Returns a StepOutcome; the run changes only if it advanced."""
    config = config or Config()
    table, records, stop_log, new = {}, [], [], []
    for _ in range(config.max_attempts_per_step):
        before = dict(vars(run))
        stops, used = [], []
        try:
            _run_step(run, table, stops, used)
        except C.ReferenceUndecided:
            if dict(vars(run)) != before:
                raise AssertionError("fail-closed violated: a refused step changed the run")
            if not stops:
                return StepOutcome(UNPROVED, "undecided_outside_impulse", records, stop_log)
            key = stops[-1]
            stop_log.append([[str(x) for x in key[0]], key[1], str(key[2])])
            if key in table:
                return StepOutcome(UNPROVED, "witness_not_applied", records, stop_log)
            if not _supported(run):
                return StepOutcome(UNPROVED, "unsupported_profile", records, stop_log)
            hit = config.cache.lookup(key, run, config) if config.cache is not None else None
            if hit is not None:                                         # re-verified from its bytes by the cache
                raw, record = hit
            else:
                try:
                    raw, record, data = _prove_and_verify(key, run, config)
                except _Reject as r:
                    return StepOutcome(UNPROVED, r.reason, records, stop_log, prover=r.prover)
                new.append((key, data))
            table[key] = raw
            records.append(record)
            continue                                                    # W3: the same step again, from its start
        except TERMINAL_EXCEPTIONS as exc:
            if dict(vars(run)) != before:
                raise AssertionError("fail-closed violated: a refused step changed the run")
            return StepOutcome(TERMINAL, type(exc).__name__, records, stop_log, exception=str(exc))
        if len(used) < len(table):                                      # a verified witness that was not needed
            return _unused(run, before, records, stop_log)
        return StepOutcome(WITNESS_RESOLVED if used else RESOLVED, "advanced", records, stop_log, new_certificates=new)
    return StepOutcome(UNPROVED, "attempt_limit", records, stop_log)


def _unused(run, before, records, stop_log):
    """Should not happen: a witness was proven for a stop that did not recur. Roll back and refuse (fail closed)."""
    for name, value in before.items():
        setattr(run, name, value)
    return StepOutcome(UNPROVED, "witness_not_used_on_rerun", records, stop_log)


def run_steps(run, n, config=None):
    """Up to n steps; stops at the first UNPROVED or TERMINAL. Returns the list of StepOutcome."""
    out = []
    for _ in range(n):
        o = step(run, config)
        out.append(o)
        if not o.advanced:
            break
    return out
