"""GPU_LONG_TRAJECTORY_V1 analysis (protocol 'decision_rules_sealed'); reads the checker verdicts and perf.json only.

    python -m experiments.gpu_long_trajectory_v1.analyze DIR
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def _load(p):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def analyze(d):
    d = Path(d)
    vp, vf, vs = (_load(d / f"checker_verdict_{x}.json") for x in ("gateP", "fixed", "service"))
    perf = _load(d / "perf.json")
    ok = lambda v: v is not None and v["verdict"] == "EVIDENCE OK"        # noqa: E731
    sup = (vp or {}).get("support", {})
    out = {"gateP_ok": ok(vp), "fixed_ok": ok(vf), "service_ok": ok(vs), "support": sup,
           "stats": (vs or vf or {}).get("stats"), "first_divergence": (vs or vf or {}).get("first_divergence", []),
           "final_cells_across_policies_equal": (vs or {}).get("final_cells_across_policies_equal")}
    limited = bool(sup.get("GPU_UNSUPPORTED_P"))
    if perf:
        rows = perf["fixed"]
        out["fixed_perf"] = rows
        n16 = next((r for r in rows if r["N"] == 16), None)
        out["services_perf"] = perf.get("services")
        out["cold"] = perf.get("cold")
        out["perf_outcomes_equal"] = perf.get("outcomes_equal_correctness")
    exact = ok(vp) and ok(vf) and ok(vs)
    if not exact:
        verdict = "LONG_FAIL" if any(v is not None and not ok(v) for v in (vp, vf, vs)) else "INCOMPLETE"
    elif limited:
        verdict = "LONG_EXACT_GPU_PRECISION_LIMITED"
    elif perf is None:
        verdict = "EXACT (no official performance run)"
    elif not (n16 and n16["class"] == "GPU_WIN") or not out["perf_outcomes_equal"]:
        verdict = "LONG_EXACT_NO_PERF_VALUE" if out.get("perf_outcomes_equal") else "LONG_FAIL"
    else:
        verdict = "GPU_V1_READY"
    out["verdict"] = verdict
    return out


def main():
    res = analyze(sys.argv[1])
    Path(sys.argv[1], "analysis.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print(res["verdict"], res["stats"], res["support"].get("GPU_SUPPORTED_P"), res["support"].get("GPU_UNSUPPORTED_P"))
    for r in res.get("fixed_perf", []):
        print(f"fixed N{r['N']} p{r['p']} T1000: GPU {r['gpu_ms']:.0f} W6 {r['w6_ms']:.0f} ms ratio {r['ratio']:.3f} {r['class']}")
    for s in res.get("services_perf") or []:
        print(f"service N{s['N']} {s['policy']}: GPU {s['gpu_total_ms']:.0f} CPU_W6 {s['cpu_total_ms']:.0f} ms "
              f"seq {s['p_sequence']}")


if __name__ == "__main__":
    main()
