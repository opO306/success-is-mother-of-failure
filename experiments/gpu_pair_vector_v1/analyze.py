"""GPU_PAIR_VECTOR_V1 analysis (protocol 'decision_rules_sealed'); reads checker_verdict.json and perf.json only.

    python -m experiments.gpu_pair_vector_v1.analyze DIR
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def analyze(d):
    d = Path(d)
    v = json.loads((d / "checker_verdict.json").read_text(encoding="utf-8"))
    perf = json.loads((d / "perf.json").read_text(encoding="utf-8")) if (d / "perf.json").exists() else None
    s, c = v["stats"], v["counts"]
    bad = lambda k: c.get(k, [0, 0])[1] > 0                                             # noqa: E731
    a_fail = [k for k in ("pair_J_exact", "domain_status", "pair_count", "pair_id_echo", "first_stop_pair",
                          "positions_echo_equals_bundle", "precision_echo", "r2_equal", "G_equal", "obligations_complete")
              if bad(k)] + (["layouts"] if bad("layouts_bit_identical") else [])
    a_exact = not a_fail and s["PAIR_UNSOUND"] == 0 and s["PAIR_SOUND_ONLY"] == 0 and s["DOMAIN_MISMATCH"] == 0 \
        and s["REFUSED"] == 0
    b_exact = a_exact and not bad("atom_F_exact") and not bad("atom_id_echo") and not bad("atom_status") and s["F_DIFF"] == 0
    out = {"stats": s, "gate_A_failures": a_fail, "gate_A_exact": a_exact, "gate_B_exact": b_exact,
           "checker_verdict": v["verdict"]}
    speed = None
    if perf:
        rows = []
        for r in perf["rows"]:
            A, B = r["gpu_A"], r["gpu_B"]
            rows.append({"N": r["N"], "p": r["p"], "pairs": r["pairs"], "source": r["source"], "cpu_w6_ms": r["cpu_w6_ms"],
                         "A_total_to_pairs_ms": A["total_to_pairs_ms"], "A_total_to_forces_ms": A["total_to_forces_ms"],
                         "A_decode_ms": A["decode_ms"], "A_host_reduce_ms": A["host_reduce_ms"],
                         "A_d2h_ms": A["d2h_compact_ms"], "B_total_ms": B["total_ms"], "B_decode_ms": B["decode_ms"],
                         "B_encode_ms": B["encode_ms"], "B_h2d_ms": B["h2d_ms"], "B_k_dr2_ms": B["k_dr2_ms"],
                         "B_k_G_ms": B["k_G_ms"], "B_k_J_ms": B["k_J_ms"], "B_k_reduce_ms": B["k_reduce_ms"],
                         "B_d2h_ms": B["d2h_atoms_ms"], "A_vs_W6": A["total_to_forces_ms"] / r["cpu_w6_ms"],
                         "B_vs_W6": B["total_ms"] / r["cpu_w6_ms"], "F_equal_A_W6": r["F_equal_A_W6"],
                         "F_equal_B_W6": r["F_equal_B_W6"], "gpu_bytes": r["memory"]["total_bytes"],
                         "returned_values_A": r["pairs"] * 3, "returned_values_B": r["N"] * 3})
        out["performance"] = rows
        out["sweep"] = perf.get("sweep")
        out["memory_table"] = perf.get("memory_table")
        out["cold"] = perf.get("cold")
        tgt = [x for x in rows if x["p"] == 109 and x["N"] in (40, 64)]
        speed = len(tgt) == 2 and all(x["B_vs_W6"] <= 0.5 for x in tgt)
        out["speed_rule_B_le_half_W6_at_N40_N64_p109"] = speed
        out["perf_forces_equal"] = all(x["F_equal_A_W6"] and x["F_equal_B_W6"] for x in rows)
    if not a_exact:
        verdict = "A_FAIL"
    elif not b_exact:
        verdict = "B_FAIL"
    elif perf is None:
        verdict = "A_EXACT_B_EXACT (no official performance run)"
    elif speed and out["perf_forces_equal"]:
        verdict = "GPU_PAIR_PROMISING"
    else:
        verdict = "B_EXACT_NOT_FASTER"
    out["verdict"] = verdict
    return out


def main():
    res = analyze(sys.argv[1])
    Path(sys.argv[1], "analysis.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print(res["verdict"], res["stats"], res["gate_A_failures"])
    for r in res.get("performance", []):
        print(f"N{r['N']} p{r['p']}: W6 {r['cpu_w6_ms']:.0f} | A {r['A_total_to_forces_ms']:.1f} ({r['A_vs_W6']:.3f}) | "
              f"B {r['B_total_ms']:.1f} ({r['B_vs_W6']:.3f}) equal {r['F_equal_A_W6']} {r['F_equal_B_W6']}")


if __name__ == "__main__":
    main()
