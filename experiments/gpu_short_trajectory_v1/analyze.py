"""GPU_SHORT_TRAJECTORY_V1 analysis (protocol 'decision_rules_sealed'); reads the checker verdicts and perf.json only.

    python -m experiments.gpu_short_trajectory_v1.analyze DIR
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

GPU_REGION_N = (64, 128)


def _load(p):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def analyze(d):
    d = Path(d)
    v10, v100 = _load(d / "checker_verdict_s10.json"), _load(d / "checker_verdict_s100.json")
    perf = _load(d / "perf.json")
    s10 = v10 is not None and v10["verdict"] == "EVIDENCE OK"
    s100 = v100 is not None and v100["verdict"] == "EVIDENCE OK"
    last = v100 or v10
    st = last["stats"] if last else {}
    stops_exact = bool(last) and st["stops_mismatch"] == 0 and st["stops_exact"] > 0
    layouts = bool(last) and last["counts"].get("layouts_identical", [0, 1])[1] == 0
    out = {"S10_exact": s10, "S100_exact": s100, "stops_exact": stops_exact, "layout_independent": layouts,
           "stats": st, "first_divergence": (last or {}).get("first_divergence", [])}
    if perf:
        rows = []
        for r in perf["rows"]:
            rows.append({k: r[k] for k in ("N", "p", "pairs", "class", "ratio_warm", "ratio_cold", "gpu_warm_ms",
                                           "w6_warm_ms", "gpu_cold_ms", "w6_cold_ms", "gpu_warm_per_step_ms",
                                           "w6_warm_per_step_ms", "gpu_breakdown", "w6_breakdown", "load",
                                           "final_states_equal_reference", "gpu_warm_all", "w6_warm_all",
                                           "gpu_cold_all", "w6_cold_all")})
        out["performance"] = rows
        p109 = {r["N"]: r for r in rows if r["p"] == 109}
        for p in (109, 163):
            byN = {r["N"]: r["class"] for r in rows if r["p"] == p}
            out[f"regions_p{p}"] = {"CPU_confirmed": sorted(n for n, c in byN.items() if c == "CPU_WIN"),
                                    "TIE": sorted(n for n, c in byN.items() if c == "TIE"),
                                    "GPU_confirmed": sorted(n for n, c in byN.items() if c == "GPU_WIN"),
                                    "UNKNOWN": "every unmeasured N"}
        gpu_win = all(p109.get(n, {}).get("class") == "GPU_WIN" for n in GPU_REGION_N)
        n40_ok = 40 in p109 and p109[40]["ratio_warm"] < 1.03
        any_win = any(p109.get(n, {}).get("class") == "GPU_WIN" for n in (40, 64, 128))
        out["perf_states_equal"] = all(r["final_states_equal_reference"] for r in rows)
        out["contaminated_conditions"] = [(r["N"], r["p"]) for r in rows if r["load"].get("contaminated")]
    if not (s10 and s100 and stops_exact and layouts):
        verdict = "SHORT_TRAJ_FAIL" if (v10 and not s10) or (v100 and not s100) else "INCOMPLETE"
    elif perf is None:
        verdict = "EXACT (no official performance run)"
    elif gpu_win and n40_ok and out["perf_states_equal"]:
        verdict = "SHORT_TRAJ_PROMISING"
    elif not any_win:
        verdict = "SHORT_TRAJ_EXACT_NO_GAIN"
    else:
        verdict = "SHORT_TRAJ_EXACT_MIXED"
    out["verdict"] = verdict
    return out


def main():
    res = analyze(sys.argv[1])
    Path(sys.argv[1], "analysis.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print(res["verdict"], res["stats"], res.get("regions_p109"), res.get("regions_p163"))
    for r in res.get("performance", []):
        print(f"N{r['N']} p{r['p']}: warm GPU {r['gpu_warm_ms']:.0f} W6 {r['w6_warm_ms']:.0f} ms ratio {r['ratio_warm']:.3f} "
              f"{r['class']} | cold GPU {r['gpu_cold_ms']:.0f} W6 {r['w6_cold_ms']:.0f} ratio {r['ratio_cold']:.3f}")


if __name__ == "__main__":
    main()
