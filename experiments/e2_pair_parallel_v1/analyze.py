"""E2_PAIR_PARALLEL_V1 analysis (protocol.json 'derived'). Reads run records only; medians over clean repetitions
(records of CONTAMINATED groups are excluded and listed).

    python -m experiments.e2_pair_parallel_v1.analyze DIR
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

CONFIGS = ["SER_E1", "SER_E2", "PAR_E1_W3", "PAR_E2_W3", "PAR_E1_W4", "PAR_E2_W4", "PAR_E1_W6", "PAR_E2_W6"]
WS = [3, 4, 6]


def med(xs):
    xs = [x for x in xs if x is not None]
    return statistics.median(xs) if xs else None


def summarize(rows):
    o = {"n": len(rows), "e2e": med(r["end_to_end_wall_s"] for r in rows), "loop": med(r["loop_wall_s"] for r in rows),
         "ready": med(r["ready_wall_s"] for r in rows), "cpu": med(r["total_cpu_s"] for r in rows),
         "cpu_tick": med(r["total_cpu_tick_s"] for r in rows), "steps": rows[0]["completed_steps"],
         "outcome": rows[0]["outcome"],
         "main_cpu": med(r["main_cycles"] / r["cycle_rate_hz"] for r in rows),
         "worker_cpu": med(sum(b["cycles"] for b in r.get("worker_bye", [])) / r["cycle_rate_hz"] for r in rows),
         "peak_ram_sum_mb": med(r["main_peak_wset_mb"] + sum(b["peak_wset_mb"] for b in r.get("worker_bye", []))
                                for r in rows)}
    o["startup_share_e2e"] = (o["e2e"] - o["loop"]) / o["e2e"]
    if rows[0]["mode"] == "parallel":
        for k in ("send_s", "wait_s", "reduce_s", "kdk_and_other_s"):
            o[k] = med(r["main_breakdown"][k] for r in rows)
        o["spawn"] = med(r["spawn_wall_s"] for r in rows)
        o["max_busy"] = med(max(b["busy_wall_s"] for b in r["worker_bye"]) for r in rows)
        o["busy_per_step_ms"] = o["max_busy"] / max(o["steps"], 1) * 1e3
        o["main_serial_share_loop"] = (o["send_s"] + o["reduce_s"] + o["kdk_and_other_s"]) / o["loop"]
        o["idle_share_loop"] = (o["wait_s"] - o["max_busy"]) / o["loop"]
        o["ipc_bytes_step"] = rows[0]["ipc_bytes_out_step"] + rows[0]["ipc_bytes_in_step"]
    return o


def analyze(d):
    d = Path(d)
    recs = [json.loads(f.read_text(encoding="utf-8")) for f in d.glob("H*.json")]
    excluded = sorted({r["group_snapshot_tag"] for r in recs if r["group_contaminated"]})
    clean = [r for r in recs if not r["group_contaminated"]]
    keys = sorted({(r["name"].split("__")[0], r["N"]) for r in recs}, key=lambda x: (x[0], x[1]))
    S = {}
    for h, n in keys:
        for c in CONFIGS:
            rows = [r for r in clean if r["name"].startswith(f"{h}__N{n}__{c}__")]
            if rows:
                S[(h, n, c)] = summarize(rows)
    out = {"excluded_contaminated_groups": excluded, "table": {f"{h}__N{n}__{c}": v for (h, n, c), v in S.items()},
           "derived": {}, "first_N_PAR_E2_wall_min": {}}
    for h, n in keys:
        if not all((h, n, c) in S for c in CONFIGS):
            continue
        g = {c: S[(h, n, c)] for c in CONFIGS}
        s1, s2 = g["SER_E1"], g["SER_E2"]
        dv = {"E2_over_E1": {}, "par_over_ser": {}, "PAR_E2_vs_SER_E2": {}, "combined_vs_product": {}, "overheads": {}}
        dv["E2_over_E1"]["serial"] = {"cpu": s2["cpu"] / s1["cpu"], "loop": s2["loop"] / s1["loop"], "e2e": s2["e2e"] / s1["e2e"]}
        for w in WS:
            a, b = g[f"PAR_E1_W{w}"], g[f"PAR_E2_W{w}"]
            dv["E2_over_E1"][f"W{w}"] = {"cpu": b["cpu"] / a["cpu"], "loop": b["loop"] / a["loop"], "e2e": b["e2e"] / a["e2e"],
                                          "worker_cpu": b["worker_cpu"] / a["worker_cpu"],
                                          "busy_per_step": b["busy_per_step_ms"] / a["busy_per_step_ms"]}
            for e, ser in (("E1", s1), ("E2", s2)):
                p = g[f"PAR_{e}_W{w}"]
                dv["par_over_ser"][f"{e}_W{w}"] = {"speedup_loop": ser["loop"] / p["loop"], "speedup_e2e": ser["e2e"] / p["e2e"],
                                                   "cpu_ratio": p["cpu"] / ser["cpu"]}
            dv["PAR_E2_vs_SER_E2"][f"W{w}"] = dv["par_over_ser"][f"E2_W{w}"]
            for k in ("loop", "e2e"):
                actual = s1[k] / b[k]
                product = (s1[k] / a[k]) * (s1[k] / s2[k])
                dv["combined_vs_product"][f"W{w}_{k}"] = {"actual_speedup_vs_SER_E1": actual, "product": product,
                                                         "actual_over_product": actual / product}
            actual_c = b["cpu"] / s1["cpu"]
            product_c = (a["cpu"] / s1["cpu"]) * (s2["cpu"] / s1["cpu"])
            dv["combined_vs_product"][f"W{w}_cpu"] = {"actual_cpu_ratio_vs_SER_E1": actual_c, "product": product_c,
                                                     "actual_over_product": actual_c / product_c}
            for e in ("E1", "E2"):
                p = g[f"PAR_{e}_W{w}"]
                dv["overheads"][f"{e}_W{w}"] = {k: p[k] for k in ("startup_share_e2e", "main_serial_share_loop",
                                                                  "idle_share_loop", "busy_per_step_ms", "spawn",
                                                                  "send_s", "wait_s", "reduce_s", "kdk_and_other_s",
                                                                  "peak_ram_sum_mb", "ipc_bytes_step")}
        for e in ("E1", "E2"):
            loops = {w: g[f"PAR_{e}_W{w}"]["loop"] for w in WS}
            e2es = {w: g[f"PAR_{e}_W{w}"]["e2e"] for w in WS}
            dv[f"W_opt_loop_{e}"] = min(loops, key=loops.get)
            dv[f"W_opt_e2e_{e}"] = min(e2es, key=e2es.get)
        dv["best"] = {"min_wall": min(g, key=lambda c: g[c]["e2e"]), "min_cpu": min(g, key=lambda c: g[c]["cpu"]),
                      "min_wall_x_cpu": min(g, key=lambda c: g[c]["e2e"] * g[c]["cpu"]),
                      "min_loop": min(g, key=lambda c: g[c]["loop"])}
        out["derived"][f"{h}__N{n}"] = dv
    for h in sorted({k[0] for k in keys}):
        ns = sorted(n for hh, n in keys if hh == h and f"{h}__N{n}" in out["derived"])
        hit = [n for n in ns if out["derived"][f"{h}__N{n}"]["best"]["min_wall"].startswith("PAR_E2")]
        out["first_N_PAR_E2_wall_min"][h] = {"first_N": hit[0] if hit else None, "N_where_true": hit,
                                             "holds_for_all_larger": bool(hit) and all(n in hit for n in ns if n >= hit[0])}
    return out


def main():
    res = analyze(sys.argv[1])
    Path(sys.argv[1], "analysis.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res["first_N_PAR_E2_wall_min"]), "excluded:", res["excluded_contaminated_groups"])


if __name__ == "__main__":
    main()
