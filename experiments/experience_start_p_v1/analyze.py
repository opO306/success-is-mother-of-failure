"""EXPERIENCE_START_P_V1 analysis (protocol 'cost_metrics_per_service_run', 'decision_rules_sealed'). Reads evidence only;
clean repetitions only (a (part, request, repetition) group is excluded when its load snapshot is CONTAMINATED).

    python -m experiments.experience_start_p_v1.analyze DIR
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

PROTO = json.loads((Path(__file__).with_name("protocol.json")).read_text(encoding="utf-8"))
REPS = PROTO["part_A_exact_replay"]["repetitions"]
BUNDLE = Path(__file__).resolve().parents[2] / "docs/active/experience_start_p_v1/training_bundle.json"


def med(xs):
    return statistics.median(xs) if xs else None


def metrics(s, train_low=None):
    ps = s["passes"]
    rec = [pz["record"] for pz in ps]
    fails = [r for r in rec if r["outcome"] != "DECIDED"]
    w = sum(r["end_to_end_wall_s"] for r in rec)
    c = sum(r["total_cpu_s"] for r in rec)
    final = rec[-1] if rec else None
    return {"service_wall_s": s["service_wall_s"], "cpu_s": c, "passes": len(rec), "failed_passes": len(fails),
            "first_pass_success": bool(rec) and rec[0]["outcome"] == "DECIDED",
            "first_wall_s": rec[0]["end_to_end_wall_s"], "first_cpu_s": rec[0]["total_cpu_s"],
            "failed_wall_s": sum(r["end_to_end_wall_s"] for r in fails), "failed_cpu_s": sum(r["total_cpu_s"] for r in fails),
            "final_wall_s": final["end_to_end_wall_s"], "final_cpu_s": final["total_cpu_s"],
            "retry_wall_fraction": sum(r["end_to_end_wall_s"] for r in fails) / w,
            "retry_cpu_fraction": sum(r["total_cpu_s"] for r in fails) / c,
            "starting_p": s["start_p"], "final_success_p": s["final_p"], "status": s["status"],
            "p_sequence": s["p_sequence"],
            "overshoot": (s["start_p"] - train_low) if train_low is not None else None}


def analyze(d, part_a=None, part_b=None, reps=None):
    d = Path(d)
    part_a = part_a or [(r["N"], r["T"]) for r in PROTO["part_A_exact_replay"]["requests"]]
    part_b = part_b or [(r["N"], r["T"]) for r in PROTO["part_B_unseen_N"]["requests"]]
    reps = REPS if reps is None else reps
    snaps = {}
    if (d / "load_snapshots.jsonl").exists():
        for ln in (d / "load_snapshots.jsonl").read_text(encoding="utf-8").splitlines():
            s = json.loads(ln)
            snaps[s["tag"]] = s["contaminated"]
    bundle = json.loads(BUNDLE.read_text(encoding="utf-8"))
    low_by_NT = {(e["N"], e["T"]): e["lowest_observed_success_p"] for e in bundle["exact"].values()}
    out = {"A": {}, "B": {}, "excluded": [], "rules": {}}
    for label, reqs, pols in (("A", part_a, PROTO["part_A_exact_replay"]["policies"]),
                              ("B", part_b, PROTO["part_B_unseen_N"]["policies"])):
        for N, T in reqs:
            key = f"N{N}_T{T}"
            clean = [r for r in range(reps) if not snaps.get(f"{label}_{key}__r{r}", False)]
            out["excluded"] += [f"{label}_{key}__r{r}" for r in range(reps) if r not in clean]
            row = {"clean_reps": clean}
            for pol in pols:
                ms = [metrics(json.loads((d / "service" / f"{label}_{key}__{pol}__r{r}.json").read_text(encoding="utf-8")),
                              low_by_NT.get((N, T)) if label == "A" else None) for r in clean]
                if not ms:
                    continue
                agg = {k: med([m[k] for m in ms]) for k in ms[0] if isinstance(ms[0][k], (int, float)) and
                       not isinstance(ms[0][k], bool) and ms[0][k] is not None}
                agg["first_pass_success_reps"] = sum(m["first_pass_success"] for m in ms)
                agg["statuses"] = sorted({m["status"] for m in ms})
                agg["p_sequences"] = sorted({tuple(m["p_sequence"]) for m in ms})
                agg["walls"] = [m["service_wall_s"] for m in ms]
                agg["cpus"] = [m["cpu_s"] for m in ms]
                agg["overshoot"] = ms[0]["overshoot"]
                row[pol] = agg
            base = row.get("P2_BASE")
            for pol in pols:
                if pol != "P2_BASE" and base and pol in row:
                    row[pol]["wall_vs_base"] = row[pol]["service_wall_s"] / base["service_wall_s"]
                    row[pol]["cpu_vs_base"] = row[pol]["cpu_s"] / base["cpu_s"]
            out[label][key] = row
    A = [r for r in out["A"].values() if "EXACT_MEMORY" in r]
    B = [r for r in out["B"].values() if "FAMILY_MIN" in r]
    nrep = lambda r: len(r["clean_reps"])                                         # noqa: E731
    out["rules"]["EXACT_MEMORY_useful_candidate"] = bool(A) and \
        sum(r["EXACT_MEMORY"]["first_pass_success_reps"] == nrep(r) for r in A) >= 5 and \
        sum(r["EXACT_MEMORY"]["wall_vs_base"] <= 0.80 for r in A) >= 5
    out["rules"]["FAMILY_MIN_generalization_candidate"] = bool(B) and \
        sum(r["FAMILY_MIN"]["first_pass_success_reps"] == nrep(r) for r in B) >= 4 and \
        sum(r["FAMILY_MIN"]["wall_vs_base"] < 1 and r["FAMILY_MIN"]["cpu_vs_base"] < 1 for r in B) >= 4
    out["rules"]["FAMILY_MAX_service_candidate"] = bool(B) and \
        sum(r["FAMILY_MAX"]["wall_vs_base"] < 1 and r["FAMILY_MAX"]["cpu_vs_base"] < 1 for r in B) >= 4 and \
        sum(r["FAMILY_MAX"]["service_wall_s"] < r["FAMILY_MIN"]["service_wall_s"] and
            r["FAMILY_MAX"]["cpu_s"] < r["FAMILY_MIN"]["cpu_s"] for r in B) >= 3
    out["rules"]["both_family_unstable"] = not (out["rules"]["FAMILY_MIN_generalization_candidate"] or
                                                out["rules"]["FAMILY_MAX_service_candidate"])
    return out


def main():
    res = analyze(sys.argv[1])
    Path(sys.argv[1], "analysis.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res["rules"]), "excluded", res["excluded"])


if __name__ == "__main__":
    main()
