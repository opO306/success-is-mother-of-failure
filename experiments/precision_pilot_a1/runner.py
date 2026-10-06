"""PRECISION_PILOT_A1 worker (one fresh process per call).

    python -m experiments.precision_pilot_a1.runner serve   SCENARIO T POLICY PARAMS_JSON OUT
    python -m experiments.precision_pilot_a1.runner pass    SCENARIO T P OUT
    python -m experiments.precision_pilot_a1.runner audit   OUT
"""

from __future__ import annotations

import json
import os
import sys
import time
from fractions import Fraction as Q
from pathlib import Path

T0 = (time.process_time(), time.perf_counter())

from . import evaluator_adapter as E  # noqa: E402
from . import policies as POL  # noqa: E402

MAX_PASSES = 24
CPU_BUDGET = 5400.0


def serve(scenario, T, policy, params):
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
        rec = E.run_pass("original", scenario, nxt, T)
        cpu += rec["cpu_s"]
        history.append(rec)
    return {"mode": "serve", "scenario": scenario, "T": T, "policy": policy, "status": status,
            "passes": history, "pass_cpu_total_s": cpu, "pass_wall_total_s": sum(h["wall_s"] for h in history),
            "tried_p": [h["requested_p"] for h in history], "ledger": POL.ledger(history)}


def audit():
    """D_evaluator audit at non-grid p: effective p equals requested p; enclosure meets a 1024-bit pass; decided
    cells agree with the 1024-bit cells."""
    rows = []
    ref = E.run_pass("original", "A2_bound", 1024, 20)
    for p in (65, 97, 129, 137, 193, 300, 777):
        r = E.run_pass("original", "A2_bound", p, 20)
        meet = all(Q(a[0]) <= Q(b[1]) and Q(b[0]) <= Q(a[1])
                   for a, b in zip(r["endpoints_scaled"], ref["endpoints_scaled"]))
        rows.append({"p": p, "effective_p": r["effective_p"], "outcome": r["outcome"], "meets_1024": meet,
                     "cells_agree": r["cells"] is None or r["cells"] == ref["cells"]})
    ok = all(x["effective_p"] == x["p"] and x["meets_1024"] and x["cells_agree"] for x in rows)
    return {"mode": "audit", "rows": rows, "reference_outcome": ref["outcome"], "PASS": ok and ref["outcome"] == "DECIDED"}


def main():
    a = sys.argv[1:]
    if a[0] == "serve":
        params = json.loads(Path(a[4]).read_text(encoding="utf-8")) if a[4] != "-" else {}
        doc, out = serve(a[1], int(a[2]), a[3], params), a[5]
    elif a[0] == "pass":
        doc, out = {"mode": "pass", **E.run_pass("original", a[1], int(a[3]), int(a[2]))}, a[4]
    elif a[0] == "audit":
        doc, out = audit(), a[1]
    else:
        raise SystemExit("unknown mode")
    doc.update(pid=os.getpid(), python=sys.version, child_cpu_s=time.process_time() - T0[0],
               child_wall_s=time.perf_counter() - T0[1])
    Path(out).write_text(json.dumps(doc, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
