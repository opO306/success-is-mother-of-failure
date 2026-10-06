"""MULTIATOM_PARALLEL_V1 analysis (protocol.json 'boundaries'). Reads run records only; medians over repetitions.

    python -m experiments.multiatom_parallel_v1.analyze DIR
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

PROTO = json.loads((Path(__file__).with_name("protocol.json")).read_text(encoding="utf-8"))
N_LIST = PROTO["scenario_family"]["N_list"]
HORIZONS = {"H100": N_LIST, "H1000": [2, 3, 4, 6, 8, 12]}
WS = [1, 2, 3, 4, 6]
CONFIGS = ["SER_E1", "SER_E2"] + [f"PAR_{w}" for w in WS]


def med(xs):
    xs = [x for x in xs if x is not None]
    return statistics.median(xs) if xs else None


def summarize(rows):
    out = {"n": len(rows),
           "e2e_wall_s": med(r["end_to_end_wall_s"] for r in rows),
           "loop_wall_s": med(r["loop_wall_s"] for r in rows),
           "ready_wall_s": med(r["ready_wall_s"] for r in rows),
           "total_cpu_s": med(r["total_cpu_s"] for r in rows),
           "steps": rows[0]["completed_steps"], "outcome": rows[0]["outcome"],
           "peak_ram_sum_mb": med(r["main_peak_wset_mb"] + sum(b["peak_wset_mb"] for b in r.get("worker_bye", []))
                                  for r in rows)}
    out["per_step_wall_s"] = out["loop_wall_s"] / max(out["steps"], 1)
    if rows[0]["mode"] == "parallel":
        out["spawn_wall_s"] = med(r["spawn_wall_s"] for r in rows)
        for k in ("send_s", "wait_s", "reduce_s", "kdk_and_other_s"):
            out[k] = med(r["main_breakdown"][k] for r in rows)
        out["max_worker_busy_wall_s"] = med(max(b["busy_wall_s"] for b in r["worker_bye"]) for r in rows)
        out["ipc_bytes_step"] = rows[0]["ipc_bytes_out_step"] + rows[0]["ipc_bytes_in_step"]
        out["main_serial_frac"] = (out["send_s"] + out["reduce_s"] + out["kdk_and_other_s"]) / out["loop_wall_s"]
        out["ipc_wait_frac"] = (out["loop_wall_s"] - out["max_worker_busy_wall_s"]) / out["loop_wall_s"]
    return out


def first(ns, pred):
    hit = [n for n in ns if pred(n)]
    return {"first_N": hit[0] if hit else None, "holds_for_all_larger": bool(hit) and
            all(pred(n) for n in ns if n >= hit[0]), "N_where_true": hit}


def analyze(d):
    d = Path(d)
    recs = [json.loads(f.read_text(encoding="utf-8")) for f in d.glob("H*.json")]
    S = {}
    for h, ns in HORIZONS.items():
        for n in ns:
            for c in CONFIGS:
                rows = [r for r in recs if r["name"].startswith(f"{h}__N{n}__{c}__")]
                if rows:
                    S[(h, n, c)] = summarize(rows)
    res = {"table": {f"{h}__N{n}__{c}": v for (h, n, c), v in S.items()}, "boundaries": {}, "derived": {}}
    for h, ns in HORIZONS.items():
        ns = [n for n in ns if all((h, n, c) in S for c in CONFIGS)]
        der = {}
        for n in ns:
            s = S[(h, n, "SER_E1")]
            rows = {}
            for w in WS:
                p = S[(h, n, f"PAR_{w}")]
                sp_loop = s["loop_wall_s"] / p["loop_wall_s"]
                sp_e2e = s["e2e_wall_s"] / p["e2e_wall_s"]
                cr = p["total_cpu_s"] / s["total_cpu_s"]
                dstep = s["per_step_wall_s"] - p["per_step_wall_s"]
                over = p["ready_wall_s"] - s["ready_wall_s"]
                rows[w] = {"speedup_loop": sp_loop, "speedup_e2e": sp_e2e, "cpu_ratio": cr, "efficiency": sp_loop / w,
                           "wallcpu_ratio": (p["e2e_wall_s"] * p["total_cpu_s"]) / (s["e2e_wall_s"] * s["total_cpu_s"]),
                           "spawn_overhead_s": over, "break_even_T": over / dstep if dstep > 0 else None}
            loops = {w: S[(h, n, f"PAR_{w}")]["loop_wall_s"] for w in WS}
            w_opt = min(loops, key=loops.get)
            w_sat = next((w for w, nxt in zip(WS, WS[1:]) if loops[nxt] > loops[w] * 0.95), WS[-1])
            e2 = S[(h, n, "SER_E2")]
            allc = {c: S[(h, n, c)] for c in CONFIGS}
            best = {"min_wall": min(allc, key=lambda c: allc[c]["e2e_wall_s"]),
                    "min_cpu": min(allc, key=lambda c: allc[c]["total_cpu_s"]),
                    "min_wall_x_cpu": min(allc, key=lambda c: allc[c]["e2e_wall_s"] * allc[c]["total_cpu_s"]),
                    "min_loop_wall": min(allc, key=lambda c: allc[c]["loop_wall_s"])}
            der[n] = {"pairs": n * (n - 1) // 2, "W": rows, "W_opt_loop": w_opt, "W_sat_5pct": w_sat,
                      "W6_vs_W4_loop_gain": 1 - loops[6] / loops[4],
                      "E2_cpu_ratio": e2["total_cpu_s"] / s["total_cpu_s"],
                      "E2_loop_ratio": e2["loop_wall_s"] / s["loop_wall_s"], "best": best,
                      "W6_main_serial_frac": S[(h, n, "PAR_6")]["main_serial_frac"],
                      "W6_ipc_wait_frac": S[(h, n, "PAR_6")]["ipc_wait_frac"],
                      "W6_peak_ram_sum_mb": S[(h, n, "PAR_6")]["peak_ram_sum_mb"]}
        res["derived"][h] = der
        res["boundaries"][h] = {
            "B1_first_loop_win": first(ns, lambda n: min(S[(h, n, f"PAR_{w}")]["loop_wall_s"] for w in WS)
                                       < S[(h, n, "SER_E1")]["loop_wall_s"]),
            "B2_first_e2e_win": first(ns, lambda n: min(S[(h, n, f"PAR_{w}")]["e2e_wall_s"] for w in WS)
                                      < S[(h, n, "SER_E1")]["e2e_wall_s"]),
            "B3_wall_beats_cpu": first(ns, lambda n: any(der[n]["W"][w]["speedup_e2e"] >= der[n]["W"][w]["cpu_ratio"]
                                                         for w in WS)),
            "B4_W6_still_gains_5pct_over_W4": first(ns, lambda n: der[n]["W6_vs_W4_loop_gain"] >= 0.05),
            "B5_main_serial_frac_ge_20pct": first(ns, lambda n: der[n]["W6_main_serial_frac"] >= 0.20),
            "B5_ipc_wait_frac_ge_20pct": first(ns, lambda n: der[n]["W6_ipc_wait_frac"] >= 0.20),
            "B5_ram_ge_2048mb": first(ns, lambda n: der[n]["W6_peak_ram_sum_mb"] >= 2048),
            "missing_N": [n for n in HORIZONS[h] if n not in ns]}
    return res


def main():
    res = analyze(sys.argv[1])
    Path(sys.argv[1], "analysis.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    for h, b in res["boundaries"].items():
        print(h, json.dumps(b))


if __name__ == "__main__":
    main()
