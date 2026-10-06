"""EXPERIENCE_START_P_V1 service loop: identical to SELECTOR_SERVICE_V1's loop except the first p, which comes from a
start-p decision. Every later p is the unchanged P2 (precision_pilot_a1.policies.next_p('P2', ...))."""

from __future__ import annotations

import time

from experiments.precision_pilot_a1 import policies as POL
from experiments.selector_service_v1 import selector as SEL
from experiments.selector_service_v1.service import MAX_PASSES, STOP_OUTCOMES, p2_view
from experiments.w5_placement_v1.plan import IMPLEMENTED


def run_request(N, T, decision, topology_summary, executor, goal="WALL_MIN"):
    t0 = time.perf_counter()
    topo = SEL.topology_input(topology_summary)
    out = {"N": N, "T": T, "policy": decision["policy"], "goal": goal, "start_p": decision["start_p"], "passes": [],
           "status": None, "final_p": None}
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
        try:
            inp = SEL.SelectorInput(N=N, T=T, p=p, goal=goal, topology=topo)
            plan = SEL.select(inp)
        except SEL.UnsupportedSelectorDomain as e:
            out["status"], out["refusal"] = SEL.UnsupportedSelectorDomain.code, str(e)
            break
        if plan.backend not in IMPLEMENTED:
            out["status"] = "REFUSED_BACKEND_NOT_IMPLEMENTED"
            break
        rec = executor(plan, N, T)
        rec["requested_p"] = p
        if rec.get("effective_p") != p:
            rec["outcome"] = "INVALID_EVIDENCE"
        out["passes"].append({"index": len(history), "p": p, "selector_input": inp.as_record(),
                              "plan": {"evaluator": plan.evaluator, "precision": plan.precision, "backend": plan.backend,
                                       "worker_count": plan.worker_count, "main_cpu": plan.main_cpu,
                                       "worker_cpus": list(plan.worker_cpus)}, "record": rec})
        history.append(p2_view(rec))
    out["service_wall_s"] = time.perf_counter() - t0
    out["n_passes"] = len(out["passes"])
    out["p_sequence"] = [x["p"] for x in out["passes"]]
    return out
