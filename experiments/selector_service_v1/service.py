"""SELECTOR_SERVICE_V1 service loop (protocol 'pipeline'): one request from start to a final status.

    p      <- P2 (precision_pilot_a1.policies.next_p('P2', ...), unchanged)
    plan   <- Selector V1 (goal) or a fixed baseline plan, from (N, T, p, goal, topology) only
    record <- executor(plan, N, T): one fresh pass from step 0 (the unchanged W5_PLACEMENT_V1 runner)
until DECIDED / STOP / CAP / pass limit. The selector never receives a pass record.
"""

from __future__ import annotations

import time

from experiments.precision_pilot_a1 import policies as POL
from experiments.selector_service_v1 import selector as SEL
from experiments.w5_placement_v1.plan import IMPLEMENTED

MAX_PASSES = 24
STOP_OUTCOMES = {"DOMAIN_VIOLATED_PROVEN": "STOP_DOMAIN_VIOLATED_PROVEN", "OUT_OF_RANGE": "STOP_OUT_OF_RANGE"}


def p2_view(rec):
    """The fields of a pass that P2 reads."""
    return {"requested_p": rec["requested_p"], "outcome": rec["outcome"], "completed_steps": rec["completed_steps"],
            "endpoints_scaled": rec.get("endpoints_scaled")}


def run_request(N, T, strategy, topology_summary, executor, goal=None):
    """strategy: 'SELECTOR' (needs goal) | 'FIXED:<SERIAL|W3|W4|W6>'. executor(plan, N, T) -> pass record."""
    t0 = time.perf_counter()
    topo = SEL.topology_input(topology_summary)
    out = {"N": N, "T": T, "strategy": strategy, "goal": goal, "passes": [], "status": None, "final_p": None}
    history = []
    while True:
        p = POL.next_p("P2", None, history, T)
        if p is None:
            last = history[-1]["outcome"]
            out["status"] = "DECIDED" if last == "DECIDED" else STOP_OUTCOMES.get(last, f"FINAL_{last}")
            out["final_p"] = history[-1]["requested_p"]
            break
        if p == "CAP":
            out["status"] = "REFUSED_AT_CAP"
            break
        if len(history) >= MAX_PASSES:
            out["status"] = "REFUSED_PASS_LIMIT"
            break
        sel_in = None
        try:
            if strategy == "SELECTOR":
                inp = SEL.SelectorInput(N=N, T=T, p=p, goal=goal, topology=topo)
                sel_in = inp.as_record()
                plan = SEL.select(inp)
            elif strategy.startswith("FIXED:"):
                if T not in (100, 1000):
                    raise SEL.UnsupportedSelectorDomain(f"T {T}")
                plan = SEL.fixed_plan(strategy[6:], p)
            else:
                raise ValueError(strategy)
        except SEL.UnsupportedSelectorDomain as e:
            out["status"], out["refusal"] = SEL.UnsupportedSelectorDomain.code, str(e)
            break
        if plan.backend not in IMPLEMENTED:
            out["status"], out["refusal"] = "REFUSED_BACKEND_NOT_IMPLEMENTED", plan.backend
            break
        rec = executor(plan, N, T)
        rec["requested_p"] = p
        if rec.get("effective_p") != p:
            rec["outcome"] = "INVALID_EVIDENCE"
        out["passes"].append({"index": len(history), "p": p, "selector_input": sel_in,
                              "plan": {"evaluator": plan.evaluator, "precision": plan.precision,
                                       "backend": plan.backend, "worker_count": plan.worker_count,
                                       "main_cpu": plan.main_cpu, "worker_cpus": list(plan.worker_cpus)},
                              "record": rec})
        history.append(p2_view(rec))
    out["service_wall_s"] = time.perf_counter() - t0
    out["n_passes"] = len(out["passes"])
    out["p_sequence"] = [x["p"] for x in out["passes"]]
    return out
