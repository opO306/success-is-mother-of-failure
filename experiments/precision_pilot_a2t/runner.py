"""PRECISION_PILOT_A2T worker (one fresh process per call).

    python -m experiments.precision_pilot_a2t.runner serve EVALUATOR SCENARIO T POLICY PARAMS_JSON OUT
    python -m experiments.precision_pilot_a2t.runner pass  EVALUATOR SCENARIO T P OUT
    python -m experiments.precision_pilot_a2t.runner audit OUT
"""

from __future__ import annotations

import json
import os
import sys
import time
from fractions import Fraction as Q
from pathlib import Path

T0 = (time.process_time(), time.perf_counter())

from experiments.precision_pilot_a1 import policies as POL  # noqa: E402

from . import evaluator_adapter as E  # noqa: E402

MAX_PASSES = 24
CPU_BUDGET = 5400.0
AUDIT_P = (65, 97, 129, 137, 193, 300, 458, 777)


def _now():
    return time.process_time(), time.perf_counter()


def serve(evaluator, scenario, T, policy, params):
    t_load = _now()
    prep = E.prepare(evaluator)
    params = dict(params, scenario=scenario)
    history, status, cpu = [], None, 0.0
    while True:
        nxt = POL.next_p(policy, params, history, T)
        if nxt is None:
            status = history[-1]["outcome"]
            break
        if nxt == "CAP" or len(history) >= MAX_PASSES or cpu >= CPU_BUDGET:
            status = "RESOURCE_REFUSED"
            break
        rec = E.run_pass(evaluator, scenario, nxt, T)
        cpu += rec["cpu_s"]
        history.append(rec)
    return {"mode": "serve", "evaluator": evaluator, "scenario": scenario, "T": T, "policy": policy,
            "policy_hash": params.get("policy_hash"), "status": status, "passes": history,
            "tried_p": [h["requested_p"] for h in history], "pass_cpu_total_s": cpu,
            "pass_wall_total_s": sum(h["wall_s"] for h in history), "ledger": POL.ledger(history),
            "load_cpu_s": t_load[0] - T0[0], "load_wall_s": t_load[1] - T0[1], **prep}


def single(evaluator, scenario, T, p):
    t_load = _now()
    prep = E.prepare(evaluator)
    return {"mode": "pass", **E.run_pass(evaluator, scenario, p, T), "load_cpu_s": t_load[0] - T0[0],
            "load_wall_s": t_load[1] - T0[1], **prep}


def audit(out_dir):
    """Algebra p-support at non-grid p (effective p, enclosure meets the 1024-bit ORIGINAL pass, cells equal) and the
    FORMULA_REPRO_B_V0 enclosure sample checks re-run with the repository modules bound."""
    prep = E.prepare("algebra")
    from experiments.formula_repro_b_v0 import transform_checks
    tc_path = Path(out_dir) / "transform_checks.json"
    transform_checks.main(str(tc_path))
    tc = json.loads(tc_path.read_text(encoding="utf-8"))
    ref = E.run_pass("original", "A2_bound", 1024, 20)
    rows = []
    for p in AUDIT_P:
        r = E.run_pass("algebra", "A2_bound", p, 20)
        meet = r["endpoints_scaled"] is not None and all(
            Q(a[0]) <= Q(b[1]) and Q(b[0]) <= Q(a[1]) for a, b in zip(r["endpoints_scaled"], ref["endpoints_scaled"]))
        rows.append({"p": p, "effective_p": r["effective_p"], "outcome": r["outcome"], "meets_original_1024": meet,
                     "cells_agree": r["cells"] is None or r["cells"] == ref["cells"],
                     "force_swap_restored": r.get("force_swap_restored")})
    ok = all(x["effective_p"] == x["p"] and x["meets_original_1024"] and x["cells_agree"] and x["force_swap_restored"]
             for x in rows)
    return {"mode": "audit", "rows": rows, "reference_outcome": ref["outcome"], "transform_checks": tc,
            "PASS": ok and ref["outcome"] == "DECIDED" and tc["PASS"], **prep}


def write(doc, out):
    """Write the record; its own first serialisation-and-write cost is measured and stored on a rewrite."""
    t = _now()
    Path(out).write_text(json.dumps(doc, indent=1), encoding="utf-8")
    t1 = _now()
    doc.update(record_cpu_s=t1[0] - t[0], record_wall_s=t1[1] - t[1], child_cpu_s=t1[0] - T0[0],
               child_wall_s=t1[1] - T0[1])
    Path(out).write_text(json.dumps(doc, indent=1), encoding="utf-8")


def main():
    a = sys.argv[1:]
    if a[0] == "serve":
        params = json.loads(Path(a[5]).read_text(encoding="utf-8"))
        doc, out = serve(a[1], a[2], int(a[3]), a[4], params), a[6]
    elif a[0] == "pass":
        doc, out = single(a[1], a[2], int(a[3]), int(a[4])), a[5]
    elif a[0] == "audit":
        doc, out = audit(Path(a[1]).parent), a[1]
    else:
        raise SystemExit("unknown mode")
    doc.update(pid=os.getpid(), python=sys.version)
    write(doc, out)


if __name__ == "__main__":
    main()
