"""ADAPTIVE_EXECUTION_V1 service (protocol 'service').

    p      <- start decision (sealed store chain) for the first pass, then P2 (precision_pilot_a1.policies, unchanged)
    plan   <- selector (ADAPTIVE) or a fixed baseline plan; re-checked by adapters.validate_plan
    pass   <- CPU (fresh process) or GPU (the one worker); every pass from the original state at exactly p
    GPU refusal / device error -> the same p on CPU serial, the event kept; precision mismatch -> INVALID_EVIDENCE
until DECIDED / STOP / CAP / pass limit. The selector never receives a pass record. Faults are for the tests only.
"""

from __future__ import annotations

import time

from experiments.adaptive_execution_v1 import adapters as AD
from experiments.adaptive_execution_v1 import experience as EXP
from experiments.adaptive_execution_v1 import selector as SEL
from experiments.precision_pilot_a1 import policies as POL

MAX_PASSES = 24
STOP_OUTCOMES = {"DOMAIN_VIOLATED_PROVEN": "STOP_DOMAIN_VIOLATED_PROVEN", "OUT_OF_RANGE": "STOP_OUT_OF_RANGE"}
STRATEGIES = ("ADAPTIVE", "FIXED_SERIAL", "FIXED_W6", "FIXED_GPU")
_LAST_GPU_STATE = {}                                            # fault F7 only


def p2_view(pz):
    return {"requested_p": pz["requested_p"], "outcome": pz["outcome"], "completed_steps": pz["completed_steps"],
            "endpoints_scaled": pz.get("endpoints_scaled")}


def _plan(strategy, goal, N, T, p, env, perf, gate100):
    t0 = time.perf_counter()
    if strategy == "ADAPTIVE":
        plan = SEL.select(N, T, p, goal, env, perf, gate100)
    else:
        plan = SEL.fixed(strategy.split("_", 1)[1], N, T, p, env, gate100)
    return plan, (time.perf_counter() - t0) * 1000


def run_request(req, strategy, env, perf, store, gpu=None, goal=None, gate100=False, run_id="", workdir=None,
                keep_gpu_detail=True, faults=()):
    """req: {'id', 'N', 'T', 'start'}. Returns the service ledger."""
    faults = set(faults)
    N, T = req["N"], req["T"]
    t0 = time.perf_counter()
    out = {"run_id": run_id, "request_id": req["id"], "N": N, "T": T, "strategy": strategy, "goal": goal,
           "env_id": env["env_id"], "perf_profile_sha256": perf.sha256 if perf else None, "gate100_passed": gate100,
           "passes": [], "events": [], "status": None, "final_p": None}
    try:
        SEL.check_request(N, T, env)
    except SEL.Refusal as e:
        out.update(status=e.code, refusal=e.reason, service_wall_s=time.perf_counter() - t0, p_sequence=[],
                   n_passes=0, service_cpu_s=0.0)
        return out
    dec = EXP.start_decision(N, T, req["start"], store, env)
    out["start_decision"] = dec
    history = []
    while True:
        p = dec["start_p"] if not history else POL.next_p("P2", None, history, T)
        if "F5" in faults and history and p not in (None, "CAP"):
            p += 1                                              # forged next p
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
        idx = len(history)
        try:
            plan, sel_ms = _plan(strategy, goal, N, T, p, env, perf, gate100)
        except SEL.Refusal as e:
            out.update(status=e.code, refusal=e.reason)
            break
        attempts = []
        if "F3" in faults and gpu is not None and plan.backend != "GPU_HYBRID" and \
                p not in SEL.CORRECTNESS["GPU_V1"]["support_p"]:
            plan = SEL.AdaptivePlan(plan.evaluator, p, "GPU_HYBRID", 0, None, (), SEL.gpu_placement_id(env), "GPU_V1",
                                    32, goal, ("F3",), (), env["env_id"], strategy)   # unsupported p sent to the GPU
        bad = [] if "F3" in faults else AD.validate_plan(plan, N, T, env, gate100)
        if bad and plan.backend == "GPU_HYBRID":
            out["events"].append({"pass": idx, "event": "GPU_PLAN_REFUSED_BY_ADAPTER", "violations": bad})
            attempts.append({"plan": plan.record(), "result": None, "event": "GPU_PLAN_REFUSED_BY_ADAPTER"})
            plan = SEL.fixed("SERIAL", N, T, p, env, gate100)
            bad = AD.validate_plan(plan, N, T, env, gate100)
        if bad:
            out.update(status="REFUSED_INVALID_PLAN", refusal=",".join(bad))
            break
        res = _execute(plan, N, T, gpu, run_id or req["id"], workdir, keep_gpu_detail, faults, idx)
        attempts.append({"plan": plan.record(), "result": res})
        if plan.backend == "GPU_HYBRID" and res["status_class"] in ("DEVICE_REFUSAL", "DEVICE_ERROR"):
            out["events"].append({"pass": idx, "event": res["status_class"], "gpu_status": res["gpu"]["status"],
                                  "error": res["gpu"].get("error")})
            plan = SEL.fixed("SERIAL", N, T, p, env, gate100)
            res = _execute(plan, N, T, gpu, run_id or req["id"], workdir, keep_gpu_detail, faults, idx)
            attempts.append({"plan": plan.record(), "result": res, "fallback_reason": out["events"][-1]["event"]})
        if res["status_class"] == "CPU_RUNNER_ERROR":
            out.update(status="CPU_RUNNER_ERROR", refusal=res.get("error"))
            out["passes"].append(_pass_entry(idx, p, dec, history, attempts, res, sel_ms))
            break
        if res.get("effective_p") != p and res["outcome"] != "INVALID_EVIDENCE" and "F3" not in faults:
            res["outcome"] = "INVALID_EVIDENCE"
        if plan.backend != "GPU_HYBRID" and not res.get("executed_placement_ok") and "F13" not in faults:
            res["outcome"] = "INVALID_EVIDENCE"
        out["passes"].append(_pass_entry(idx, p, dec, history, attempts, res, sel_ms))
        history.append(p2_view(out["passes"][-1]))
    if "F6" in faults and len(out["passes"]) > 1:
        out["passes"] = out["passes"][1:]                       # a failed pass deleted
    if "F12" in faults:
        out["events"] = [e for e in out["events"] if e["event"] != "DEVICE_ERROR"]
    backends = [a["plan"]["backend"] for pz in out["passes"] for a in pz["attempts"] if a.get("result")]
    gpu_used = "GPU_HYBRID" in backends
    out["execution_label"] = ("CPU_ONLY" if not gpu_used else
                              "GPU_FULL_RETRY" if all(b == "GPU_HYBRID" for b in backends) and not out["events"]
                              else "GPU_WITH_CPU_FALLBACK")
    out["service_wall_s"] = time.perf_counter() - t0
    out["service_cpu_s"] = sum((a["result"] or {}).get("cpu_s") or 0.0 for pz in out["passes"] for a in pz["attempts"]
                               if a.get("result"))
    out["n_passes"] = len(out["passes"])
    out["p_sequence"] = [pz["requested_p"] for pz in out["passes"]]
    return out


def _execute(plan, N, T, gpu, rid, workdir, keep, faults, idx):
    if plan.backend == "GPU_HYBRID":
        if gpu is None or not gpu.ready:
            return {"backend": "GPU_HYBRID", "status_class": "DEVICE_ERROR", "requested_p": plan.p, "wall_s": 0.0,
                    "cpu_s": 0.0, "gpu": {"status": "DEVICE_ERROR", "error": "no GPU worker"}}
        f = {}
        if "F3" in faults and idx == 0 and plan.p not in SEL.CORRECTNESS["GPU_V1"]["support_p"]:
            f["fault_run_p"] = min(x for x in SEL.CORRECTNESS["GPU_V1"]["support_p"] if x > plan.p)
            f["fault_hide_mismatch"] = True
        if "F4" in faults and idx == 0:
            f["fault_upload_p"] = min(x for x in SEL.CORRECTNESS["GPU_V1"]["support_p"] if x > plan.p)
            f["fault_hide_mismatch"] = True
        if "DEVICE_ERROR" in faults and idx == 0:
            f["fault_device_error"] = True
        if "F7" in faults and idx > 0 and _LAST_GPU_STATE.get(rid):
            f["fault_start"] = _LAST_GPU_STATE[rid]                 # retry from the previous pass's last state
        res = AD.gpu_pass(gpu, plan, N, T, rid, keep_detail=keep or "F7" in faults, **f)
        if f.get("fault_hide_mismatch") and res["status_class"] == "GPU_PRECISION_MISMATCH":
            res["status_class"] = "OK"
        if "F7" in faults:
            full = (res.get("gpu_detail") or {}).get("full") or {}
            if full:
                _LAST_GPU_STATE[rid] = full[max(full, key=int)]
        return res
    executed = None
    if "F13" in faults and plan.backend == "CPU_PARALLEL" and plan.worker_count == 6:
        executed = SEL.AdaptivePlan(plan.evaluator, plan.p, "CPU_PARALLEL", 4, plan.main_cpu,
                                    tuple(plan.worker_cpus[:4]), "F13", None, None, plan.goal, plan.reasons,
                                    plan.evidence_ids, plan.env_id, plan.strategy)      # W4 run, W6 recorded
    return AD.cpu_pass(plan, N, T, workdir, executed_plan=executed)


def _pass_entry(idx, p, dec, history, attempts, res, sel_ms):
    pz = {"index": idx, "requested_p": p, "p_source": "start:" + dec["start_source"] if not history else "P2",
          "start": "ORIGINAL_STATE", "selector_ms": sel_ms, "attempts": attempts,
          "backend": res.get("backend"), "effective_p": res.get("effective_p"), "wall_s": sum(
              (a["result"] or {}).get("wall_s") or 0.0 for a in attempts if a.get("result")),
          "cpu_s": sum((a["result"] or {}).get("cpu_s") or 0.0 for a in attempts if a.get("result"))}
    pz.update({k: res.get(k) for k in AD.OUTCOME_KEYS})
    return pz
