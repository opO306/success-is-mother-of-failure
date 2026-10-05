"""FORMULA_REPRO_B_V0 worker. One fresh process per measurement. The upstream probe is imported unchanged; only its
eager `PROGRAM = exact_program()` assignment is deferred in memory (the method of the upstream startup comparison), so
the 'original' and 'cache' paths never pay the preparation and 'algebra' pays it inside the timed 'prepare' phase.

    python -m experiments.formula_repro_b_v0.harness policy SCENARIO STEPS EVALUATOR OUT
    python -m experiments.formula_repro_b_v0.harness fixed  SCENARIO PREC EVALUATOR OUT
    python -m experiments.formula_repro_b_v0.harness reference OUT        (repository V1 stream, no vendor path)
"""

from __future__ import annotations

import ast
import json
import os
import sys
import time
import types
from pathlib import Path

T0 = (time.process_time(), time.perf_counter())
HERE = Path(__file__).resolve().parent
UPSTREAM = HERE / "upstream" / "probe.py"
COMPILED = {"original": False, "cache": "cache", "algebra": True}
REF_STEPS = (1, 10, 100, 1000)
REF_BITS = 384
SCENARIOS = ("A2_bound", "A3_low", "A3_high")


def load_probe():
    tree = ast.parse(UPSTREAM.read_text(encoding="utf-8"), filename=str(UPSTREAM))
    changed = 0
    for node in tree.body:
        if (isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)
                and node.targets[0].id == "PROGRAM"):
            assert isinstance(node.value, ast.Call) and node.value.func.id == "exact_program"
            node.value = ast.Constant(value=None)
            changed += 1
    assert changed == 1, "upstream probe is not the expected source"
    ast.fix_missing_locations(tree)
    mod = types.ModuleType("repro_probe")
    mod.__file__ = str(UPSTREAM)
    exec(compile(tree, str(UPSTREAM), "exec"), mod.__dict__)
    return mod


def _spans(spans):
    return None if spans is None else [[str(lo), str(hi)] for lo, hi in spans]


def _now():
    return time.process_time(), time.perf_counter()


def _phases(t_start, t_load, t_prep, t_end):
    return {"load_cpu_s": t_load[0] - t_start[0], "load_wall_s": t_load[1] - t_start[1],
            "prepare_cpu_s": t_prep[0] - t_load[0], "prepare_wall_s": t_prep[1] - t_load[1],
            "compute_cpu_s": t_end[0] - t_prep[0], "compute_wall_s": t_end[1] - t_prep[1],
            "child_total_cpu_s": t_end[0] - t_start[0], "child_total_wall_s": t_end[1] - t_start[1]}


def policy(scenario, steps, evaluator):
    P = load_probe()
    t_load = _now()
    if evaluator == "algebra":
        P.PROGRAM = P.exact_program()
    t_prep = _now()
    q, p = P.scenario(scenario)
    attempts, cells, spans, status = [], None, None, "UNDECIDED_AT_CAP"
    for bits in P.GRID:                                  # upstream default grid, cap 512, restart from exact state
        a = time.process_time()
        try:
            cells, spans = P.evolve(q, p, steps, P.Backend("mp", bits), COMPILED[evaluator])[steps]
            status = "DECIDED" if cells is not None else "UNDECIDED"
        except P.DomainStop as e:
            cells, spans, status = None, None, e.kind
        except OverflowError:
            cells, spans, status = None, None, "OUT_OF_RANGE"
        attempts.append({"bits": bits, "status": status, "cpu_s": time.process_time() - a,
                         "spans_scaled": _spans(spans)})
        if status == "DECIDED" or status in ("VIOLATED", "OUT_OF_RANGE"):
            break
    t_end = _now()
    return {"mode": "policy", "scenario": scenario, "steps": steps, "evaluator": evaluator, "status": status,
            "decided_bits": attempts[-1]["bits"] if status == "DECIDED" else None, "cells": cells,
            "attempts": attempts, **_phases(T0, t_load, t_prep, t_end)}


def fixed(scenario, prec, evaluator):
    P = load_probe()
    t_load = _now()
    if evaluator == "algebra":
        P.PROGRAM = P.exact_program()
    t_prep = _now()
    q, p = P.scenario(scenario)
    status, out = "COMPLETED", {}
    try:
        out = P.evolve(q, p, 1000, P.Backend("mp", prec), COMPILED[evaluator], checkpoints=[100, 1000])
    except P.DomainStop as e:
        status = e.kind
    except OverflowError:
        status = "OUT_OF_RANGE"
    t_end = _now()
    reads = {str(s): {"cells": c, "spans_scaled": _spans(sp)} for s, (c, sp) in out.items()}
    return {"mode": "fixed", "scenario": scenario, "prec": prec, "evaluator": evaluator, "status": status,
            "reads": reads, **_phases(T0, t_load, t_prep, t_end)}


def reference():
    """Repository (not vendor) V1 C_stream at 384 bits: cells and exact endpoints for every scenario and step."""
    from fractions import Fraction as Q
    from exact_expression_gate_v1 import stream
    init = {"A2_bound": ([("-71/20", 0, 0), ("71/20", 0, 0)], [(1, -3, 0), (-1, 3, 0)]),
            "A3_low": ([(0, 0, 0), (25, 0, 0), (0, 25, 0)], [(2, 1, 0), (-1, 2, 0), (-1, -3, 0)]),
            "A3_high": ([(0, 0, 0), ("71/10", 0, 0), ("71/20", "6149/1000", 0)],
                        [(3, 0, "1/2"), ("-3/2", "13/5", 0), ("-3/2", "-13/5", "-1/2")])}
    res = {}
    for name in SCENARIOS:
        q0, p0 = ([[Q(x) for x in r] for r in v] for v in init[name])
        r = stream.run(q0, p0, REF_BITS, max(REF_STEPS), set(REF_STEPS), exact=False)
        if r["stop"] is not None:
            raise RuntimeError(f"reference stopped: {name} {r['stop']}")
        res[name] = {str(s): {"cells": c, "endpoints_key": k} for s, (c, k) in r["read"].items()}
    return {"mode": "reference", "bits": REF_BITS, "source": "repository exact_expression_gate_v1.stream",
            "results": res, "modules": {m: getattr(sys.modules[m], "__file__", None)
                                        for m in ("exact_expression_gate_v1.stream", "exact_expression_gate_v0.lang_iv",
                                                  "a_reference.ar2_lang2024")}}


def peak_rss():
    try:
        import psutil
        mi = psutil.Process().memory_info()
        return getattr(mi, "peak_wset", None) or mi.rss
    except Exception:
        return None


def main(argv=None):
    a = sys.argv[1:] if argv is None else argv
    if a[0] == "policy":
        doc, out = policy(a[1], int(a[2]), a[3]), a[4]
    elif a[0] == "fixed":
        doc, out = fixed(a[1], int(a[2]), a[3]), a[4]
    elif a[0] == "reference":
        doc, out = reference(), a[1]
    else:
        raise SystemExit("unknown mode")
    doc.update(pid=os.getpid(), python=sys.version, peak_rss=peak_rss())
    Path(out).write_text(json.dumps(doc, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
