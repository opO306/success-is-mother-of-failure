"""EXPERIENCE_START_P_V2 analysis (protocol 'metrics', 'decision_rules_sealed'). Reads evidence only; a (request,
repetition) group is excluded when its load snapshot is CONTAMINATED.

    python -m experiments.experience_start_p_v2.analyze DIR
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

PROTO = json.loads((Path(__file__).with_name("protocol.json")).read_text(encoding="utf-8"))
REQUESTS = [(r["N"], r["T"]) for r in PROTO["evaluation_requests"]["requests"]]
REPS = PROTO["evaluation_requests"]["repetitions"]
POLICIES = ("BASE64", "FAMILY_MIN", "FAMILY_MAX")


def med(xs):
    return statistics.median(xs) if xs else None


def metrics(s):
    rec = [pz["record"] for pz in s["passes"]]
    fails = [r for r in rec if r["outcome"] != "DECIDED"]
    w = sum(r["end_to_end_wall_s"] for r in rec)
    c = sum(r["total_cpu_s"] for r in rec)
    return {"service_wall_s": s["service_wall_s"], "cpu_s": c, "pass_wall_s": w, "passes": len(rec),
            "failed_passes": len(fails), "first_pass_success": bool(rec) and rec[0]["outcome"] == "DECIDED",
            "first_wall_s": rec[0]["end_to_end_wall_s"], "first_cpu_s": rec[0]["total_cpu_s"],
            "failed_wall_s": sum(r["end_to_end_wall_s"] for r in fails), "failed_cpu_s": sum(r["total_cpu_s"] for r in fails),
            "final_wall_s": rec[-1]["end_to_end_wall_s"], "final_cpu_s": rec[-1]["total_cpu_s"],
            "retry_wall_fraction": sum(r["end_to_end_wall_s"] for r in fails) / w,
            "retry_cpu_fraction": sum(r["total_cpu_s"] for r in fails) / c,
            "starting_p": s["start_p"], "final_success_p": s["final_p"], "status": s["status"],
            "p_sequence": s["p_sequence"]}


def min_vs_max(totals, per_req):
    """Sealed MIN vs MAX classification from the totals and the equal-weight per-request ratios."""
    Sw = totals["FAMILY_MAX"]["wall"] / totals["FAMILY_MIN"]["wall"]
    Sc = totals["FAMILY_MAX"]["cpu"] / totals["FAMILY_MIN"]["cpu"]
    Ew = statistics.mean(r["FAMILY_MAX"]["service_wall_s"] / r["FAMILY_MIN"]["service_wall_s"] for r in per_req)
    Ec = statistics.mean(r["FAMILY_MAX"]["cpu_s"] / r["FAMILY_MIN"]["cpu_s"] for r in per_req)
    Fw = statistics.mean(r["FAMILY_MIN"]["service_wall_s"] / r["FAMILY_MAX"]["service_wall_s"] for r in per_req)
    Fc = statistics.mean(r["FAMILY_MIN"]["cpu_s"] / r["FAMILY_MAX"]["cpu_s"] for r in per_req)
    nums = {"Sw_MAX_over_MIN": Sw, "Sc_MAX_over_MIN": Sc, "Ew_mean_MAX_over_MIN": Ew, "Ec_mean_MAX_over_MIN": Ec,
            "mean_MIN_over_MAX_wall": Fw, "mean_MIN_over_MAX_cpu": Fc}
    if Sw <= 0.95 and Sc <= 0.95 and Ew <= 1.02 and Ec <= 1.02:
        v = "MAX_WIN"
    elif 1 / Sw <= 0.95 and 1 / Sc <= 0.95 and Fw <= 1.02 and Fc <= 1.02:
        v = "MIN_WIN"
    elif (Sw <= 0.95 and Ew > 1.02) or (Sc <= 0.95 and Ec > 1.02) or \
            (1 / Sw <= 0.95 and Fw > 1.02) or (1 / Sc <= 0.95 and Fc > 1.02):
        v = "DISTRIBUTION_SENSITIVE"
    elif all(abs(x - 1) < 0.05 for x in (Sw, Sc, Ew, Ec)):
        v = "TIE"
    else:
        v = "MIXED"
    return v, nums


def analyze(d, requests=None, reps=None):
    d = Path(d)
    requests = requests or REQUESTS
    reps = REPS if reps is None else reps
    snaps = {}
    if (d / "load_snapshots.jsonl").exists():
        for ln in (d / "load_snapshots.jsonl").read_text(encoding="utf-8").splitlines():
            s = json.loads(ln)
            snaps[s["tag"]] = s["contaminated"]
    out = {"requests": {}, "excluded": [], "policies": {}, "totals": {}, "equal_weight_vs_BASE64": {}, "rules": {}}
    runs = {p: [] for p in POLICIES}
    for N, T in requests:
        key = f"N{N}_T{T}"
        clean = [r for r in range(reps) if not snaps.get(f"{key}__r{r}", False)]
        out["excluded"] += [f"{key}__r{r}" for r in range(reps) if r not in clean]
        row = {"clean_reps": clean}
        for pol in POLICIES:
            ms = [metrics(json.loads((d / "service" / f"{key}__{pol}__r{r}.json").read_text(encoding="utf-8")))
                  for r in clean]
            if not ms:
                continue
            runs[pol] += ms
            agg = {k: med([m[k] for m in ms]) for k in ms[0]
                   if isinstance(ms[0][k], (int, float)) and not isinstance(ms[0][k], bool)}
            agg["first_pass_success_reps"] = sum(m["first_pass_success"] for m in ms)
            agg["statuses"] = sorted({m["status"] for m in ms})
            agg["p_sequences"] = sorted({tuple(m["p_sequence"]) for m in ms})
            agg["walls"] = [m["service_wall_s"] for m in ms]
            agg["cpus"] = [m["cpu_s"] for m in ms]
            row[pol] = agg
        for pol in ("FAMILY_MIN", "FAMILY_MAX"):
            if pol in row and "BASE64" in row:
                row[pol]["wall_vs_BASE64"] = row[pol]["service_wall_s"] / row["BASE64"]["service_wall_s"]
                row[pol]["cpu_vs_BASE64"] = row[pol]["cpu_s"] / row["BASE64"]["cpu_s"]
        out["requests"][key] = row
    full = [r for r in out["requests"].values() if all(p in r for p in POLICIES)]
    complete = len(full) == len(requests)
    for pol in POLICIES:
        ms = runs[pol]
        out["policies"][pol] = {
            "first_try_success_requests": sum(r[pol]["first_pass_success_reps"] == len(r["clean_reps"]) for r in full),
            "first_try_success_runs": sum(m["first_pass_success"] for m in ms), "runs": len(ms),
            "retry_count": sum(m["failed_passes"] for m in ms),
            "retry_cpu_fraction": (sum(m["failed_cpu_s"] for m in ms) / sum(m["cpu_s"] for m in ms)) if ms else None,
            "retry_wall_fraction": (sum(m["failed_wall_s"] for m in ms) / sum(m["pass_wall_s"] for m in ms)) if ms else None}
        out["totals"][pol] = {"wall": sum(r[pol]["service_wall_s"] for r in full), "cpu": sum(r[pol]["cpu_s"] for r in full)}
    for pol in ("FAMILY_MIN", "FAMILY_MAX"):
        out["equal_weight_vs_BASE64"][pol] = {
            "wall": statistics.mean(r[pol]["wall_vs_BASE64"] for r in full) if full else None,
            "cpu": statistics.mean(r[pol]["cpu_vs_BASE64"] for r in full) if full else None}
        t, b = out["totals"][pol], out["totals"]["BASE64"]
        out["totals"][pol]["wall_vs_BASE64"] = t["wall"] / b["wall"] if b["wall"] else None
        out["totals"][pol]["cpu_vs_BASE64"] = t["cpu"] / b["cpu"] if b["cpu"] else None
        out["rules"][f"{pol}_cost_policy"] = ("USEFUL_COST_POLICY_CANDIDATE" if complete and
                                              t["wall"] <= 0.80 * b["wall"] and t["cpu"] <= 0.80 * b["cpu"]
                                              else "INFO_ONLY")
    if complete:
        out["rules"]["MIN_vs_MAX"], out["min_vs_max_numbers"] = min_vs_max(out["totals"], full)
    else:
        out["rules"]["MIN_vs_MAX"], out["min_vs_max_numbers"] = "INCOMPLETE", {}
    stable = {pol: out["policies"][pol]["first_try_success_requests"] >= 3 for pol in ("FAMILY_MIN", "FAMILY_MAX")}
    a = [pol for pol in ("FAMILY_MIN", "FAMILY_MAX")
         if stable[pol] and out["rules"][f"{pol}_cost_policy"] == "USEFUL_COST_POLICY_CANDIDATE"]
    both_fail = sum(1 for r in full if r["FAMILY_MIN"]["first_pass_success_reps"] < len(r["clean_reps"]) and
                    r["FAMILY_MAX"]["first_pass_success_reps"] < len(r["clean_reps"]))
    neither_useful = all(out["rules"][f"{p}_cost_policy"] != "USEFUL_COST_POLICY_CANDIDATE" for p in ("FAMILY_MIN", "FAMILY_MAX"))
    out["rules"]["stop_candidate"] = ("A_keep_simple_policy" if a else
                                      "B_table_range_limit" if (both_fail >= 2 or neither_useful) else "otherwise")
    out["rules"]["stop_candidate_A_policies"] = a
    out["rules"]["requests_where_both_first_pass_failed"] = both_fail
    out["complete"] = complete
    return out


def main():
    res = analyze(sys.argv[1])
    Path(sys.argv[1], "analysis.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res["rules"]), "excluded", res["excluded"], "totals",
          {p: (round(v["wall"], 2), round(v["cpu"], 2)) for p, v in res["totals"].items()})


if __name__ == "__main__":
    main()
