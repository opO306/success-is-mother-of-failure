"""W5_PLACEMENT_V1 analysis (protocol.json 'analysis_questions' and 'verdict_rules'). Reads run records only; clean
repetitions only; paired comparisons use the same repetition index.

    python -m experiments.w5_placement_v1.analyze DIR
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

PROTO = json.loads((Path(__file__).with_name("protocol.json")).read_text(encoding="utf-8"))
CONFIGS = ["SER_E2", "W4_DEDICATED", "W5_DEDICATED", "W6_SHARED"]
PAR = ["W4_DEDICATED", "W5_DEDICATED", "W6_SHARED"]


def med(xs):
    return statistics.median(xs)


def analyze(d, bit_mismatches=0):
    d = Path(d)
    R = {}
    for f in d.glob("N*.json"):
        r = json.loads(f.read_text(encoding="utf-8"))
        R[r["name"]] = r
    out = {"per_N": {}, "verdicts": {}, "excluded_contaminated": sorted({r["group_snapshot_tag"] for r in R.values()
                                                                         if r["group_contaminated"]})}
    for n in PROTO["scope"]["N"]:
        reps = [k for k in range(PROTO["scope"]["repetitions"])
                if all(f"N{n}__{c}__r{k}" in R for c in CONFIGS) and not R[f"N{n}__SER_E2__r{k}"]["group_contaminated"]]
        g = {c: [R[f"N{n}__{c}__r{k}"] for k in reps] for c in CONFIGS}
        row = {"clean_repetitions": reps}
        ser_loop = med([r["loop_wall_s"] for r in g["SER_E2"]])
        for c in CONFIGS:
            rs = g[c]
            s = {"e2e": med([r["end_to_end_wall_s"] for r in rs]), "loop": med([r["loop_wall_s"] for r in rs]),
                 "cpu": med([r["total_cpu_s"] for r in rs]), "main_cpu": med([r["main_cpu_cycle_s"] for r in rs]),
                 "ready": med([r["ready_wall_s"] for r in rs]),
                 "peak_ram_sum_mb": med([r["main_peak_wset_mb"] + sum(b["peak_wset_mb"] for b in r.get("worker_bye", []))
                                         for r in rs]),
                 "e2e_all": [r["end_to_end_wall_s"] for r in rs], "cpu_all": [r["total_cpu_s"] for r in rs]}
            if c != "SER_E2":
                W = len(rs[0]["worker_bye"])
                s["speedup_loop_vs_SER_E2"] = ser_loop / s["loop"]
                s["efficiency"] = s["speedup_loop_vs_SER_E2"] / W
                s["spawn"] = med([r["spawn_wall_s"] for r in rs])
                for k in ("send_s", "wait_s", "reduce_s", "kdk_and_other_s"):
                    s[k] = med([r["main_breakdown"][k] for r in rs])
                s["worker_busy_median"] = [med([r["worker_bye"][w]["busy_wall_s"] for r in rs]) for w in range(W)]
                s["worker_cpu_median"] = [med([r["worker_cpu_cycle_s"][w] for r in rs]) for w in range(W)]
                spreads = []
                for r in rs:
                    b = [x["busy_wall_s"] for x in r["worker_bye"]]
                    spreads.append((max(b) - min(b)) / med(b))
                s["busy_spread_median"] = med(spreads)
                s["slowest_worker_by_rep"] = [max(range(W), key=lambda w: r["worker_bye"][w]["busy_wall_s"]) for r in rs]
            row[c] = s
        w5, w6 = g["W5_DEDICATED"], g["W6_SHARED"]
        pair_e2e = [a["end_to_end_wall_s"] / b["end_to_end_wall_s"] for a, b in zip(w5, w6)]     # W5 / W6
        pair_cpu = [a["total_cpu_s"] / b["total_cpu_s"] for a, b in zip(w5, w6)]
        pair_loop = [a["loop_wall_s"] / b["loop_wall_s"] for a, b in zip(w5, w6)]
        row["W5_over_W6"] = {"e2e_median": med(pair_e2e), "loop_median": med(pair_loop), "cpu_median": med(pair_cpu),
                             "e2e_per_rep": pair_e2e, "loop_per_rep": pair_loop, "cpu_per_rep": pair_cpu,
                             "W6_faster_reps": sum(x > 1 for x in pair_e2e), "W5_less_cpu_reps": sum(x < 1 for x in pair_cpu)}
        # Q4: in W6, the CPU-0 worker is index 5 (worker_cpus [1,2,3,4,5,0])
        q4 = []
        for r in w6:
            b = [x["busy_wall_s"] for x in r["worker_bye"]]
            q4.append({"slowest_is_cpu0": max(range(6), key=lambda w: b[w]) == 5,
                       "cpu0_excess_over_others_median": b[5] / med(b[:5]) - 1})
        row["Q4_W6_cpu0_worker"] = {"slowest_in_reps": sum(x["slowest_is_cpu0"] for x in q4), "of": len(q4),
                                    "excess_median": med([x["cpu0_excess_over_others_median"] for x in q4]),
                                    "per_rep": q4}
        row["Q7_W6_loop_ge_W5_loop"] = row["W6_SHARED"]["loop"] >= row["W5_DEDICATED"]["loop"]
        loops = [row[c]["loop"] for c in PAR]
        row["Q3_monotone_wall_decrease"] = loops[0] > loops[1] > loops[2]
        nrep = len(reps)
        if bit_mismatches:
            v = "D"
        elif med(pair_e2e) >= 1.03 and row["W5_over_W6"]["W6_faster_reps"] >= nrep - 1:
            v = "B"
        elif med(pair_e2e) <= 1.02 and med(pair_cpu) <= 0.97 and row["W5_over_W6"]["W5_less_cpu_reps"] >= nrep - 1:
            v = "A"
        else:
            v = "C"
        out["verdicts"][f"N{n}"] = v
        out["per_N"][f"N{n}"] = row
    vs = set(out["verdicts"].values())
    out["overall"] = vs.pop() if len(vs) == 1 else "MIXED (reported per N)"
    return out


def main():
    d = Path(sys.argv[1])
    mism = 0
    cv = d / "checker_verdict.json"
    if cv.exists():
        mism = json.loads(cv.read_text(encoding="utf-8"))["bit_mismatches"]
    res = analyze(d, mism)
    (d / "analysis.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print("verdicts", res["verdicts"], "overall", res["overall"], "excluded", res["excluded_contaminated"])


if __name__ == "__main__":
    main()
