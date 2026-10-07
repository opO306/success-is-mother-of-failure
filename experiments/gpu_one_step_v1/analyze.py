"""GPU_ONE_STEP_V1 analysis (protocol 'decision_rules_sealed'); reads checker_verdict.json and perf.json only.

    python -m experiments.gpu_one_step_v1.analyze DIR
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

GPU_REGION_N = (64, 128)


def analyze(d):
    d = Path(d)
    v = json.loads((d / "checker_verdict.json").read_text(encoding="utf-8"))
    perf = json.loads((d / "perf.json").read_text(encoding="utf-8")) if (d / "perf.json").exists() else None
    exact = v["verdict"] == "EVIDENCE OK" and v["stats"]["steps_mismatch"] == 0 and v["stats"]["stops_mismatch"] == 0
    out = {"checker_verdict": v["verdict"], "stats": v["stats"], "exact": exact}
    if perf:
        rows = [{"N": r["N"], "p": r["p"], "pairs": r["pairs"], "class": r["class"], "ratio": r["ratio_gpu_over_w6"],
                 "gpu_steady_ms": r["gpu_steady"]["total_ms"], "w6_steady_ms": r["w6_steady"]["total_ms"],
                 "gpu_force_ms": r["gpu_steady"]["force_total_ms"], "w6_force_ms": r["w6_steady"]["force_total_ms"],
                 "gpu_breakdown": r["gpu_steady"], "w6_breakdown": r["w6_steady"], "gpu_init_ms": r["gpu_init"]["init_total_ms"],
                 "w6_init_ms": r["w6_init"]["init_total_ms"], "gpu_init": r["gpu_init"], "w6_init": r["w6_init"],
                 "load": r["load"], "states_equal": r["states_equal_gpu_w6_every_rep"]} for r in perf["rows"]]
        out["performance"] = rows
        p109 = {r["N"]: r for r in rows if r["p"] == 109}
        out["regions_p109"] = {
            "CPU_confirmed": sorted(n for n, r in p109.items() if r["class"] == "CPU_WIN"),
            "TIE": sorted(n for n, r in p109.items() if r["class"] == "TIE"),
            "GPU_confirmed": sorted(n for n, r in p109.items() if r["class"] == "GPU_WIN"),
            "UNKNOWN": "every unmeasured N"}
        out["regions_p163"] = {r["N"]: r["class"] for r in rows if r["p"] == 163}
        gpu_win = all(p109.get(n, {}).get("class") == "GPU_WIN" for n in GPU_REGION_N)
        n40_ok = 40 in p109 and p109[40]["ratio"] < 1.03
        any_win = any(p109.get(n, {}).get("class") == "GPU_WIN" for n in (40, 64, 128))
        out["perf_states_equal"] = all(r["states_equal"] for r in rows)
        out["contaminated_conditions"] = [(r["N"], r["p"]) for r in rows if r["load"].get("contaminated")]
    if not exact:
        verdict = "ONE_STEP_FAIL"
    elif perf is None:
        verdict = "EXACT (no official performance run)"
    elif gpu_win and n40_ok and out["perf_states_equal"]:
        verdict = "ONE_STEP_PROMISING"
    elif not any_win:
        verdict = "ONE_STEP_EXACT_BUT_NO_GAIN"
    else:
        verdict = "ONE_STEP_EXACT_MIXED"
    out["verdict"] = verdict
    return out


def main():
    res = analyze(sys.argv[1])
    Path(sys.argv[1], "analysis.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print(res["verdict"], res["stats"], res.get("regions_p109"), res.get("regions_p163"))
    for r in res.get("performance", []):
        print(f"N{r['N']} p{r['p']}: GPU {r['gpu_steady_ms']:.1f} W6 {r['w6_steady_ms']:.1f} ratio {r['ratio']:.3f} "
              f"{r['class']} | init GPU {r['gpu_init_ms']:.0f} W6 {r['w6_init_ms']:.0f}")


if __name__ == "__main__":
    main()
