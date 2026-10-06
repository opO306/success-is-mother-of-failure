"""Evaluator adapter for PRECISION_PILOT_A2T. One pass = one call of A1's unchanged adapter function `_original`
(repository exact_expression_gate_v1.stream.run at integer working precision p, exact initial state to step T).

'original': exactly that call.
'algebra' : exactly that call with only the pair-force function swapped (stream.LI -> {c: lang_iv.c, G_of_R2: probe
            Force(compiled=True) at p}) for the duration of the pass, then restored. Same loop, domain check, readout.

The upstream probe is loaded after the repository modules, so it binds to the repository lang_iv / ar2_lang2024.
"""

from __future__ import annotations

import sys
import time
import types

from experiments.precision_pilot_a1 import evaluator_adapter as A1E

P_MIN, P_MAX = A1E.P_MIN, A1E.P_MAX
MODULES = ("exact_expression_gate_v1.stream", "exact_expression_gate_v1.common", "exact_expression_gate_v0.lang_iv",
           "a_reference.ar2_lang2024")
_PROBE = None


def _now():
    return time.process_time(), time.perf_counter()


def prepare(evaluator):
    """Evaluator preparation, timed. original: repository module imports. algebra: the same imports, then the
    unchanged upstream probe (eager PROGRAM deferred) and exact_program()."""
    global _PROBE
    t0 = _now()
    import a_reference.ar2_lang2024  # noqa: F401
    import exact_expression_gate_v0.lang_iv  # noqa: F401
    from exact_expression_gate_v1 import common, stream  # noqa: F401
    info = {}
    if evaluator == "algebra":
        from experiments.formula_repro_b_v0.harness import UPSTREAM, load_probe
        vendor = str(UPSTREAM.parent / "vendor")
        P = load_probe()
        while vendor in sys.path:                     # the probe prepends its vendor dir; nothing else may load from it
            sys.path.remove(vendor)
        P.PROGRAM = P.exact_program()
        LI = sys.modules["exact_expression_gate_v0.lang_iv"]
        if P.LI is not LI or P.L is not sys.modules["a_reference.ar2_lang2024"] or P.L is not LI.L:
            raise RuntimeError("probe is not bound to the repository modules")
        if not (all(b > 0 for b in P.L.RET_B) and P.L.R_MIN_BOHR > 0):
            raise RuntimeError("rearrangement applicability condition fails")
        _PROBE = P
        info["probe_file"] = P.__file__
    elif evaluator != "original":
        raise ValueError(evaluator)
    t1 = _now()
    info.update(prepare_cpu_s=t1[0] - t0[0], prepare_wall_s=t1[1] - t0[1],
                modules={m: sys.modules[m].__file__ for m in MODULES})
    return info


def _algebra(name, p, T):
    if _PROBE is None:
        raise RuntimeError("algebra evaluator not prepared")
    from exact_expression_gate_v1 import stream
    LI = sys.modules["exact_expression_gate_v0.lang_iv"]
    force = _PROBE.Force(_PROBE.Backend("mp", p), True)
    saved = stream.LI
    stream.LI = types.SimpleNamespace(c=LI.c, G_of_R2=force)
    try:
        rec = A1E._original(name, p, T)
    finally:
        stream.LI = saved
    rec["force_swap_restored"] = stream.LI is LI
    return rec


EVALUATORS = {"original": A1E._original, "algebra": _algebra}


def run_pass(evaluator, name, p, T):
    if not (isinstance(p, int) and P_MIN <= p <= P_MAX):
        raise ValueError(f"p {p!r} outside the audited domain [{P_MIN}, {P_MAX}]")
    t = _now()
    rec = EVALUATORS[evaluator](name, p, T)
    t1 = _now()
    rec.update(requested_p=p, evaluator=evaluator, scenario=name, T=T, cpu_s=t1[0] - t[0], wall_s=t1[1] - t[1])
    if rec["effective_p"] != p or rec.get("force_swap_restored") is False:
        rec["outcome"] = "INVALID_EVIDENCE"
    return rec
