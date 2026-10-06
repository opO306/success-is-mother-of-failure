"""Independent checker of SELECTOR_SERVICE_V1. Reads JSON evidence only. It does NOT import the executor, the service,
the selector or precision_pilot_a1.policies: the P2 next-p rule and the Selector V1 table are re-implemented here.
Initial states: MULTIATOM checker generator; cells: A1 checker rounding.

    python -m experiments.selector_service_v1.checker DIR
"""

from __future__ import annotations

import json
import re
import sys
from fractions import Fraction as F
from pathlib import Path

from experiments.multiatom_parallel_v1 import checker as MAC
from experiments.precision_pilot_a1 import checker as A1C

PROTO = json.loads((Path(__file__).with_name("protocol.json")).read_text(encoding="utf-8"))
REQUESTS = [(r["N"], r["T"]) for r in PROTO["evaluation_requests"]["requests"]]
REPS = PROTO["evaluation_requests"]["repetitions"]
LABELS = {"SEL_WALL": ("SELECTOR", "WALL_MIN"), "SEL_CPU": ("SELECTOR", "CPU_MIN"), "FIXED_W6": ("FIXED:W6", None)}
RESULT_KEYS = ("outcome", "completed_steps", "stop", "stop_step", "endpoints_key", "cells", "initial_sha256")
ALLOWED_SELECTOR_KEYS = {"N", "T", "p", "goal", "topology"}
SUSPECT = re.compile(r"python|roblox|codex|node", re.I)
FINAL = ("DECIDED", "DOMAIN_VIOLATED_PROVEN", "OUT_OF_RANGE", "INVALID_EVIDENCE")


# ---- own P2 (re-implementation of the A1 P2 rule) ----
def _rhe(x):
    q, r = divmod(x.numerator, x.denominator)
    return q + 1 if 2 * r > x.denominator or (2 * r == x.denominator and q & 1) else q


def _clog2(x):
    e = 0
    while F(2) ** e < x:
        e += 1
    while F(2) ** (e - 1) >= x:
        e -= 1
    return e


def my_next_p(history, T):
    """history: list of (requested_p, outcome, completed_steps, endpoints_scaled). Returns int, 'CAP' or None."""
    if not history:
        return 64
    p, outcome, k, ends = history[-1]
    if outcome in FINAL:
        return None
    if outcome == "UNDECIDED_AT_PRECISION" and ends:
        extra = None
        for lo, hi in ends:
            lo, hi = F(lo), F(hi)
            if _rhe(lo) == _rhe(hi):
                continue
            mid = (lo + hi) / 2
            margin = F(1, 2) - abs(mid - _rhe(mid))
            e = 32 if margin <= 0 else _clog2((hi - lo) / margin)
            extra = e if extra is None else max(extra, e)
        nxt = p + max(extra or 0, 1) + 8
    elif outcome == "DOMAIN_UNPROVEN":
        nxt = 2 * p if k <= 0 else -((-p * T) // k) + 8
    else:
        nxt = 2 * p
    nxt = max(nxt, p + 1)
    if nxt > 1024:
        return "CAP" if max(h[0] for h in history) >= 1024 else 1024
    return nxt


# ---- own Selector V1 table ----
def my_plan(N, T, p, goal):
    if goal == "CPU_MIN":
        w = 0
    elif T == 100:
        w = 0 if N <= 4 else (4 if N < 12 else 6)
    elif T == 1000:
        w = 3 if N == 3 else 6
    else:
        return None
    if w == 0:
        return {"evaluator": "rw:R1+R2", "precision": p, "backend": "CPU_SERIAL", "worker_count": 0, "main_cpu": 1,
                "worker_cpus": []}
    return {"evaluator": "rw:R1+R2", "precision": p, "backend": "CPU_PARALLEL", "worker_count": w, "main_cpu": 0,
            "worker_cpus": list(range(1, w + 1)) if w <= 5 else [1, 2, 3, 4, 5, 0]}


LAPTOP_TOPO = {"logical": 6, "physical": 6, "smt": False, "cores": [[k, [k]] for k in range(6)]}


def my_contaminated(rows):
    return sum(v for _, _, v in rows) >= 100.0 or any(SUSPECT.search(n or "") and v >= 25.0 for n, _, v in rows)


def check(d, requests=None, reps=None):
    d = Path(d)
    requests, reps = requests or REQUESTS, REPS if reps is None else reps
    issues, counts = [], {}

    def ok(name, cond, detail=""):
        counts.setdefault(name, [0, 0])
        counts[name][0 if cond else 1] += 1
        if not cond:
            issues.append(f"{name}: {detail}")

    seal = json.loads((d / "execution_seal.json").read_text(encoding="utf-8"))
    ok("seal_clean", seal["status_porcelain"] == "" and not seal["sealed_sources_dirty"], seal["status_porcelain"][:200])
    rate = json.loads((d / "cycle_rate.json").read_text(encoding="utf-8"))["rate_hz"]
    snaps = {}
    if (d / "load_snapshots.jsonl").exists():
        for ln in (d / "load_snapshots.jsonl").read_text(encoding="utf-8").splitlines():
            s = json.loads(ln)
            snaps[s["tag"]] = s
            ok("contamination_rederived", my_contaminated(s["rows"]) == s["contaminated"], s["tag"])
    by_ntp = {}

    def check_pass(where, N, T, pz, plan_expected=None):
        rec, plan = pz["record"], pz["plan"]
        ok("pass_T_supported", T in (100, 1000), where)
        ok("pass_backend_cpu", plan["backend"] in ("CPU_SERIAL", "CPU_PARALLEL"), where)
        ok("pass_meta", rec["N"] == N and rec["T"] == T and rec["p"] == pz["p"] == plan["precision"] ==
           rec["effective_p"] == rec["requested_p"] and rec["evaluator"] == "rw:R1+R2", where)
        ok("pass_plan_shape", plan["worker_count"] == len(plan["worker_cpus"]) and
           (plan["backend"] == "CPU_SERIAL") == (plan["worker_count"] == 0), where)
        if plan_expected is not None:
            ok("plan_rederived", plan == plan_expected, f"{where}: {plan} vs {plan_expected}")
        if plan["backend"] == "CPU_SERIAL":
            ok("pass_executed_as_planned", rec.get("mode") == "serial" and rec["affinity"] == [plan["main_cpu"]], where)
        else:
            ok("pass_executed_as_planned", rec.get("mode") == "parallel" and rec["W"] == plan["worker_count"] and
               len(rec["worker_bye"]) == plan["worker_count"] and rec["worker_cpus"] == plan["worker_cpus"] and
               rec["main_affinity"] == [plan["main_cpu"]] and
               [h["affinity"] for h in rec["worker_hello"]] == [[c] for c in plan["worker_cpus"]] and
               all(h["evaluator"] == "rw:R1+R2" and h["iv_prec"] == plan["precision"] for h in rec["worker_hello"]) and
               rec["workers_exited"] == [0] * plan["worker_count"], where)
        ok("initial_state", rec["initial_sha256"] == MAC.my_digest(*MAC.my_initial(N)), where)
        wc = [b["cycles"] for b in rec.get("worker_bye", [])]
        ok("cycle_cpu_consistent", rec["main_cycles"] + sum(wc) == rec["total_cycles"] and rec["cycle_rate_hz"] == rate
           and abs(rec["total_cpu_s"] - rec["total_cycles"] / rate) < 1e-9, where)
        if rec["outcome"] == "DECIDED":
            ok("cells_rederived", A1C.my_cells(rec["endpoints_scaled"]) == rec["cells"], where)
        by_ntp.setdefault((N, T, pz["p"]), []).append((where, plan["backend"], tuple(json.dumps(rec[k]) for k in RESULT_KEYS)))

    for N, T in requests:
        for rep in range(reps):
            seqs = {}
            for label, (strategy, goal) in LABELS.items():
                name = f"N{N}_T{T}__{label}__r{rep}"
                f = d / "service" / f"{name}.json"
                ok("service_complete", f.exists(), name)
                if not f.exists():
                    continue
                s = json.loads(f.read_text(encoding="utf-8"))
                ok("service_meta", (s["N"], s["T"], s["strategy"], s["goal"]) == (N, T, strategy, goal), name)
                hist = []
                for i, pz in enumerate(s["passes"]):
                    where = f"{name} pass {i}"
                    ok("pass_index", pz["index"] == i, where)
                    ok("p2_rederived", my_next_p(hist, T) == pz["p"], f"{where}: recorded {pz['p']} own {my_next_p(hist, T)}")
                    si = pz["selector_input"]
                    if strategy == "SELECTOR":
                        ok("selector_input_allowed_keys_only", si is not None and set(si) == ALLOWED_SELECTOR_KEYS,
                           f"{where}: {sorted(si) if si else si}")
                        ok("selector_input_values", si is not None and (si.get("N"), si.get("T"), si.get("p"), si.get("goal"),
                                                                        si.get("topology")) == (N, T, pz["p"], goal, LAPTOP_TOPO), where)
                        exp = my_plan(N, T, pz["p"], goal)
                    else:
                        ok("fixed_has_no_selector_input", si is None, where)
                        exp = {"evaluator": "rw:R1+R2", "precision": pz["p"], "backend": "CPU_PARALLEL", "worker_count": 6,
                               "main_cpu": 0, "worker_cpus": [1, 2, 3, 4, 5, 0]}
                    check_pass(where, N, T, pz, exp)
                    r = pz["record"]
                    hist.append((pz["p"], r["outcome"], r["completed_steps"], r.get("endpoints_scaled")))
                nxt = my_next_p(hist, T)
                if hist and nxt is None:
                    want = "DECIDED" if hist[-1][1] == "DECIDED" else {"DOMAIN_VIOLATED_PROVEN": "STOP_DOMAIN_VIOLATED_PROVEN",
                                                                      "OUT_OF_RANGE": "STOP_OUT_OF_RANGE"}.get(hist[-1][1])
                    ok("final_status", s["status"] == want and s["final_p"] == hist[-1][0], f"{name}: {s['status']}")
                elif nxt == "CAP":
                    ok("final_status", s["status"] == "REFUSED_AT_CAP", f"{name}: {s['status']}")
                else:
                    ok("final_status", s["status"] == "REFUSED_PASS_LIMIT" and len(hist) >= 24,
                       f"{name}: status {s['status']} but P2 still wants p {nxt} (missing pass?)")
                seqs[label] = [pz["p"] for pz in s["passes"]]
                ok("p_sequence_recorded", s["p_sequence"] == seqs[label] and s["n_passes"] == len(seqs[label]), name)
            if len(seqs) == 3:
                ok("same_p_sequence_all_strategies", seqs["SEL_WALL"] == seqs["SEL_CPU"] == seqs["FIXED_W6"],
                   f"N{N} T{T} r{rep}: {seqs}")
            for p in seqs.get("SEL_WALL", []):
                for kind, w in (("W3", 3), ("W4", 4)):
                    name = f"N{N}_T{T}__p{p}__{kind}__r{rep}"
                    f = d / "shadow" / f"{name}.json"
                    ok("shadow_complete", f.exists(), name)
                    if not f.exists():
                        continue
                    rec = json.loads(f.read_text(encoding="utf-8"))
                    plan = {"evaluator": "rw:R1+R2", "precision": p, "backend": "CPU_PARALLEL", "worker_count": w,
                            "main_cpu": 0, "worker_cpus": list(range(1, w + 1))}
                    check_pass(name, N, T, {"p": p, "plan": plan, "record": rec}, plan)
    for f in sorted((d / "probes").glob("*.json")):
        s = json.loads(f.read_text(encoding="utf-8"))
        if s["strategy"] == "FIXED:GPU":
            ok("probe_gpu_refused", s["status"] == "REFUSED_BACKEND_NOT_IMPLEMENTED" and s["n_passes"] == 0 and
               not s["passes"], f.name)
        else:
            ok("probe_unsupported_T_refused", s["T"] not in (100, 1000) and s["status"] == "UNSUPPORTED_SELECTOR_DOMAIN"
               and s["n_passes"] == 0 and not s["passes"], f.name)
    for f in sorted((d / "service").glob("*.json")):
        s = json.loads(f.read_text(encoding="utf-8"))
        ok("no_unsupported_or_gpu_pass_anywhere", s["T"] in (100, 1000) and
           all(pz["plan"]["backend"] in ("CPU_SERIAL", "CPU_PARALLEL") for pz in s["passes"]), f.name)
    for key, rows in by_ntp.items():
        ref = [v for _, b, v in rows if b == "CPU_SERIAL"]
        ok("serial_reference_present", bool(ref), str(key))
        for where, _, view in rows:
            ok("bit_identical_to_serial", bool(ref) and view == ref[0], f"{where}")
    bad = sum(v[1] for v in counts.values())
    return {"verdict": "EVIDENCE OK" if bad == 0 else "NOT_OK", "counts": counts, "issues": issues[:80],
            "bit_mismatches": counts.get("bit_identical_to_serial", [0, 0])[1], "n_tried_ntp": len(by_ntp)}


def main():
    res = check(sys.argv[1])
    Path(sys.argv[1], "checker_verdict.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(res["verdict"], "bit mismatches", res["bit_mismatches"], {k: v for k, v in res["counts"].items() if v[1]},
          res["issues"][:6])


if __name__ == "__main__":
    main()
