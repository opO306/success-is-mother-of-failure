"""G0 analysis (protocol 'decision_rules_sealed'): reads checker_verdict.json and perf.json only.

    python -m experiments.gpu_force_feasibility_v1.analyze DIR
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def analyze(d):
    d = Path(d)
    v = json.loads((d / "checker_verdict.json").read_text(encoding="utf-8"))
    perf = json.loads((d / "perf.json").read_text(encoding="utf-8")) if (d / "perf.json").exists() else None
    main = {k: s for k, s in v["summary"].items() if k.startswith("main")}
    n_main = sum(s["EXACT"] + s["SOUND_TIGHT"] + s["SOUND_WIDE"] + s["UNSOUND"] + s["REFUSED"] + s["DOMAIN_MISMATCH"]
                 for s in main.values())
    tot = {k: sum(s[k] for s in main.values()) for k in ("EXACT", "SOUND_TIGHT", "SOUND_WIDE", "UNSOUND", "REFUSED",
                                                          "DOMAIN_MISMATCH")}
    layout_bad = v["counts"].get("layouts_bit_identical", [0, 0])[1]
    fail_reasons = []
    if tot["UNSOUND"]:
        fail_reasons.append("UNSOUND main samples")
    if tot["DOMAIN_MISMATCH"] or v["counts"].get("domain_decision", [0, 0])[1]:
        fail_reasons.append("domain mismatch")
    if layout_bad:
        fail_reasons.append("layout difference")
    if v["verdict"] != "EVIDENCE OK":
        fail_reasons.append("checker NOT_OK")
    p95 = max((s["width_ratio_p95"] or 1) for s in main.values()) if main else None
    out = {"main_samples": n_main, "main_counts": tot, "exact_fraction": tot["EXACT"] / n_main if n_main else None,
           "sound_wide_fraction": tot["SOUND_WIDE"] / n_main if n_main else None, "width_ratio_p95_max": p95,
           "subsets": v["summary"], "fail_reasons": fail_reasons}
    speed = None
    if perf:
        rows = perf["rows"]
        table = []
        for r in rows:
            g = r["gpu_ms"]["total_ms"]
            table.append({"p": r["p"], "pairs": r["pairs"], "N_equiv": r["N_equiv"], "gpu_total_ms": g,
                          "gpu_kernel_ms": r["gpu_ms"]["kernel_ms"], "gpu_h2d_ms": r["gpu_ms"]["h2d_ms"],
                          "gpu_d2h_ms": r["gpu_ms"]["d2h_ms"], "encode_ms": r["gpu_ms"]["encode_ms"],
                          "decode_ms": r["gpu_ms"]["decode_ms"], "cpu_serial_ms": r["cpu_serial_ms"],
                          "cpu_w6_ms": r["cpu_w6_ms"], "gpu_vs_serial": g / r["cpu_serial_ms"],
                          "gpu_vs_w6": g / r["cpu_w6_ms"], "kernel_vs_w6": r["gpu_ms"]["kernel_ms"] / r["cpu_w6_ms"],
                          "results_equal_gpu_serial": r["results_equal_gpu_serial"],
                          "results_equal_w6_serial": r["results_equal_w6_serial"]})
        out["performance"] = table
        out["cold"] = perf.get("cold")
        out["setup"] = perf.get("setup")
        out["w6_spawn_ms"] = perf.get("w6_spawn_ms")
        big = [t for t in table if t["pairs"] >= 2048]
        speed = bool(big) and all(t["gpu_vs_w6"] <= 0.5 for t in big) and {t["p"] for t in big} == {109, 163}
        out["speed_rule_gpu_total_le_half_w6_for_batches_ge_2048"] = speed
        out["throughput_results_equal"] = all(t["results_equal_gpu_serial"] and t["results_equal_w6_serial"] for t in table)
    if fail_reasons:
        verdict = "G0_FAIL"
    elif perf is None:
        verdict = "CORRECTNESS_ONLY (no official performance run)"
    elif (tot["REFUSED"] == 0 and (out["sound_wide_fraction"] or 0) <= 0.01 and (p95 or 1) <= 2 and speed):
        verdict = "G0_PROMISING"
    else:
        verdict = "G0_SOUND_BUT_NOT_USEFUL"
    out["verdict"] = verdict
    return out


def main():
    res = analyze(sys.argv[1])
    Path(sys.argv[1], "analysis.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print(res["verdict"], res["main_counts"], "p95", res["width_ratio_p95_max"])
    for t in res.get("performance", []):
        print(f"p{t['p']} n{t['pairs']}: gpu {t['gpu_total_ms']:.1f} (kernel {t['gpu_kernel_ms']:.1f}) serial "
              f"{t['cpu_serial_ms']:.0f} w6 {t['cpu_w6_ms']:.0f} -> gpu/w6 {t['gpu_vs_w6']:.3f}")


if __name__ == "__main__":
    main()
