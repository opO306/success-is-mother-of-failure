"""EXPERIENCE_START_P_V2 service loop: first p from the start-p decision, every later p from the unchanged P2
(precision_pilot_a1.policies.next_p('P2', ...)); every pass uses the fixed W6 plan (selector_service_v1.selector.fixed_plan),
the Selector is not called."""

from __future__ import annotations

import time

from experiments.precision_pilot_a1 import policies as POL
from experiments.selector_service_v1.selector import fixed_plan
from experiments.selector_service_v1.service import MAX_PASSES, STOP_OUTCOMES, p2_view

PLAN_KIND = "W6"


def plan_record(plan):
    return {"evaluator": plan.evaluator, "precision": plan.precision, "backend": plan.backend,
            "worker_count": plan.worker_count, "main_cpu": plan.main_cpu, "worker_cpus": list(plan.worker_cpus)}


def run_request(N, T, decision, executor):
    t0 = time.perf_counter()
    out = {"N": N, "T": T, "policy": decision["policy"], "plan_kind": PLAN_KIND, "start_p": decision["start_p"],
           "passes": [], "status": None, "final_p": None}
    history = []
    while True:
        p = decision["start_p"] if not history else POL.next_p("P2", None, history, T)
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
        plan = fixed_plan(PLAN_KIND, p)
        rec = executor(plan, N, T)
        rec["requested_p"] = p
        if rec.get("effective_p") != p:
            rec["outcome"] = "INVALID_EVIDENCE"
        out["passes"].append({"index": len(history), "p": p, "p_source": "decision" if not history else "P2",
                              "plan": plan_record(plan), "record": rec})
        history.append(p2_view(rec))
    out["service_wall_s"] = time.perf_counter() - t0
    out["n_passes"] = len(out["passes"])
    out["p_sequence"] = [x["p"] for x in out["passes"]]
    return out
