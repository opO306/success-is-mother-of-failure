"""Evaluator adapter for REWRITE_PILOT_A3: 'original' and 'algebra' through the sealed A2T adapter; 'rw:<rules>' =
the same A1 adapter call (repository stream.run loop) with stream.LI swapped to the fixed interpreter running the
candidate plan, for one pass, then restored."""

from __future__ import annotations

import sys
import time
import types

from mpmath import iv

from experiments.precision_pilot_a1 import evaluator_adapter as A1E
from experiments.precision_pilot_a2t import evaluator_adapter as A2E

from . import rules as RU
from . import rwforce as RW

_PLAN = None


def _now():
    return time.process_time(), time.perf_counter()


def prepare(ev):
    """Timed preparation. rw: probe load + exact_program (as algebra) + plan build."""
    global _PLAN
    if ev in ("original", "algebra"):
        return A2E.prepare(ev)
    rules = RU.parse_ev(ev)
    t0 = _now()
    info = A2E.prepare("algebra")
    _PLAN = RU.build_plan(A2E._PROBE.PROGRAM, rules)
    t1 = _now()
    info.update(prepare_cpu_s=t1[0] - t0[0], prepare_wall_s=t1[1] - t0[1], plan_ops=_PLAN["ops"],
                plan_rules=list(rules))
    return info


def _rw(name, p, T):
    if _PLAN is None:
        raise RuntimeError("rewrite evaluator not prepared")
    from exact_expression_gate_v1 import stream
    LI = sys.modules["exact_expression_gate_v0.lang_iv"]
    iv.prec = p
    force = RW.RwForce(_PLAN)
    saved = stream.LI
    stream.LI = types.SimpleNamespace(c=LI.c, G_of_R2=force)
    try:
        rec = A1E._original(name, p, T)
    finally:
        stream.LI = saved
    rec["force_swap_restored"] = stream.LI is LI
    return rec


def run_pass(ev, name, p, T):
    if ev in ("original", "algebra"):
        return A2E.run_pass(ev, name, p, T)
    if not (isinstance(p, int) and A1E.P_MIN <= p <= A1E.P_MAX):
        raise ValueError(f"p {p!r} outside the audited domain")
    t = _now()
    rec = _rw(name, p, T)
    t1 = _now()
    rec.update(requested_p=p, evaluator=ev, scenario=name, T=T, cpu_s=t1[0] - t[0], wall_s=t1[1] - t[1])
    if rec["effective_p"] != p or rec.get("force_swap_restored") is False:
        rec["outcome"] = "INVALID_EVIDENCE"
    return rec
