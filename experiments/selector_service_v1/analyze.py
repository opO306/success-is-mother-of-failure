"""SELECTOR_SERVICE_V1 analysis (protocol 'analysis_questions', 'noise_rule'). Reads evidence only; clean repetitions
only (a (request, repetition) group is excluded when its load snapshot is CONTAMINATED).

    python -m experiments.selector_service_v1.analyze DIR
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

PROTO = json.loads((Path(__file__).with_name("protocol.json")).read_text(encoding="utf-8"))
REQUESTS = [(r["N"], r["T"]) for r in PROTO["evaluation_requests"]["requests"]]
REPS = PROTO["evaluation_requests"]["repetitions"]
LABELS = ("SEL_WALL", "SEL_CPU", "FIXED_W6")
TIE = 0.03


def med(xs):
    return statistics.median(xs)


def rule_choice(N, T):
    if T == 100:
        return "SERIAL" if N <= 4 else ("W4" if N < 12 else "W6")
    return "W3" if N == 3 else "W6"


def analyze(d, requests=None, reps=None, ignore_load=False):
    """ignore_load is for dry runs only (the campaign analysis always honours the load rule)."""
    d = Path(d)
    requests, reps = requests or REQUESTS, REPS if reps is None else reps
    snaps = {}
    if (d / "load_snapshots.jsonl").exists():
        for ln in (d / "load_snapshots.jsonl").read_text(encoding="utf-8").splitlines():
            s = json.loads(ln)
            snaps[s["tag"]] = s["contaminated"] and not ignore_load
    out = {"requests": {}, "excluded": []}
    for N, T in requests:
        key = f"N{N}_T{T}"
        clean = [r for r in range(reps) if not snaps.get(f"{key}__r{r}", False)]
        out["excluded"] += [f"{key}__r{r}" for r in range(reps) if r not in clean]
        if not clean:
            out["requests"][key] = {"clean_reps": [], "no_clean_repetition": True}
            continue
        S = {lab: [json.loads((d / "service" / f"{key}__{lab}__r{r}.json").read_text(encoding="utf-8")) for r in clean]
             for lab in LABELS}
        row = {"clean_reps": clean, "status": {lab: sorted({s["status"] for s in S[lab]}) for lab in LABELS},
               "p_sequence": S["SEL_WALL"][0]["p_sequence"] if clean else None,
               "n_passes": S["SEL_WALL"][0]["n_passes"] if clean else None}
        tot = {}
        for lab in LABELS:
            walls = [s["service_wall_s"] for s in S[lab]]
            cpus = [sum(p["record"]["total_cpu_s"] for p in s["passes"]) for s in S[lab]]
            tot[lab] = {"wall": med(walls), "cpu": med(cpus), "walls": walls, "cpus": cpus}
        row["totals"] = tot
        row["Q3_SEL_WALL_faster_than_SERIAL"] = {
            "per_rep": [a < b for a, b in zip(tot["SEL_WALL"]["walls"], tot["SEL_CPU"]["walls"])],
            "speedup_median": tot["SEL_CPU"]["wall"] / tot["SEL_WALL"]["wall"]}
        row["Q4_SEL_WALL_vs_FIXED_W6"] = {
            "wall_ratio": tot["SEL_WALL"]["wall"] / tot["FIXED_W6"]["wall"],
            "cpu_ratio": tot["SEL_WALL"]["cpu"] / tot["FIXED_W6"]["cpu"],
            "wallxcpu_ratio": (tot["SEL_WALL"]["wall"] * tot["SEL_WALL"]["cpu"]) / (tot["FIXED_W6"]["wall"] * tot["FIXED_W6"]["cpu"]),
            "wall_per_rep": [a / b for a, b in zip(tot["SEL_WALL"]["walls"], tot["FIXED_W6"]["walls"])]}
        row["Q2_cpu_min_is_serial"] = min(LABELS, key=lambda lab: tot[lab]["cpu"]) == "SEL_CPU"
        # per tried p: SERIAL (SEL_CPU), W6 (FIXED_W6), W3/W4 (shadow); SEL_WALL is the selector's own sample
        per_p = {}
        for i, p in enumerate(row["p_sequence"] or []):
            m = {"SERIAL": [S["SEL_CPU"][j]["passes"][i]["record"] for j in range(len(clean))],
                 "W6": [S["FIXED_W6"][j]["passes"][i]["record"] for j in range(len(clean))]}
            for kind in ("W3", "W4"):
                m[kind] = [json.loads((d / "shadow" / f"{key}__p{p}__{kind}__r{r}.json").read_text(encoding="utf-8"))
                           for r in clean]
            stats = {k: {"e2e": med([x["end_to_end_wall_s"] for x in v]), "loop": med([x["loop_wall_s"] for x in v]),
                         "cpu": med([x["total_cpu_s"] for x in v])} for k, v in m.items()}
            best = min(stats, key=lambda k: stats[k]["e2e"])
            ties = sorted(k for k in stats if stats[k]["e2e"] <= stats[best]["e2e"] * (1 + TIE))
            chosen = rule_choice(N, T)
            sel = [S["SEL_WALL"][j]["passes"][i]["record"]["end_to_end_wall_s"] for j in range(len(clean))]
            per_p[str(p)] = {"stats": stats, "best_wall": best, "within_3pct_of_best": ties,
                             "rule_choice": chosen, "rule_choice_ok": chosen in ties,
                             "selector_pass_e2e_median": med(sel),
                             "regret_ratio": stats[chosen]["e2e"] / stats[best]["e2e"],
                             "best_cpu": min(stats, key=lambda k: stats[k]["cpu"]),
                             "outcome": m["SERIAL"][0]["outcome"]}
        row["per_p"] = per_p
        bests = [(p, v["best_wall"], tuple(v["within_3pct_of_best"])) for p, v in per_p.items()]
        row["Q5_best_changes_with_p"] = len({b for _, b, _ in bests}) > 1 and \
            not set.intersection(*[set(t) for _, _, t in bests]) if bests else None
        row["Q6_rule_ok_at_every_p"] = all(v["rule_choice_ok"] for v in per_p.values())
        cw = sum(v["stats"][v["rule_choice"]]["e2e"] for v in per_p.values())
        bw = sum(v["stats"][v["best_wall"]]["e2e"] for v in per_p.values())
        row["Q7_regret_sum_ratio"] = cw / bw if bw else None
        # Q9 cost split per strategy: share of non-final passes; parallel overhead vs serial CPU at the same p
        split = {}
        for lab in LABELS:
            shares_w, shares_c, ovh, start = [], [], [], []
            for j, s in enumerate(S[lab]):
                ps = s["passes"]
                w_all = sum(p["record"]["end_to_end_wall_s"] for p in ps)
                c_all = sum(p["record"]["total_cpu_s"] for p in ps)
                shares_w.append(sum(p["record"]["end_to_end_wall_s"] for p in ps[:-1]) / w_all)
                shares_c.append(sum(p["record"]["total_cpu_s"] for p in ps[:-1]) / c_all)
                ser_c = sum(S["SEL_CPU"][j]["passes"][i]["record"]["total_cpu_s"] for i in range(len(ps)))
                ovh.append((c_all - ser_c) / c_all)
                start.append(sum(p["record"]["end_to_end_wall_s"] - p["record"]["loop_wall_s"] for p in ps) / w_all)
            split[lab] = {"retry_share_wall": med(shares_w), "retry_share_cpu": med(shares_c),
                          "parallel_overhead_share_cpu": med(ovh), "startup_share_wall": med(start)}
        row["Q9_cost_split"] = split
        out["requests"][key] = row
    rs = [r for r in out["requests"].values() if r["clean_reps"]]
    out["summary"] = {
        "Q1_all_final_ok": all(all(st in ("DECIDED", "STOP_DOMAIN_VIOLATED_PROVEN", "STOP_OUT_OF_RANGE", "REFUSED_AT_CAP")
                                   for sts in r["status"].values() for st in sts) for r in rs),
        "Q2_serial_cheapest_everywhere": all(r["Q2_cpu_min_is_serial"] for r in rs),
        "Q3_sel_wall_faster_than_serial_every_request_median": all(r["Q3_SEL_WALL_faster_than_SERIAL"]["speedup_median"] > 1 for r in rs),
        "Q6_rule_ok_everywhere": all(r["Q6_rule_ok_at_every_p"] for r in rs),
        "Q5_any_request_best_changes_with_p": any(r["Q5_best_changes_with_p"] for r in rs)}
    return out


def main():
    res = analyze(sys.argv[1])
    Path(sys.argv[1], "analysis.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res["summary"]), "excluded", res["excluded"])


if __name__ == "__main__":
    main()
