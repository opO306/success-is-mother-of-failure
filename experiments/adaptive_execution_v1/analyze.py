"""ADAPTIVE_EXECUTION_V1 analysis (protocol 'decision_rules_sealed').

    python -m experiments.adaptive_execution_v1.analyze OUT [--profile FILE]

Reads the services, cases, checker verdict(s), replay timings and the performance profile; writes analysis.json.
Only services of the run's env_id enter the performance tables, and only when the checker verdict is EVIDENCE OK.
"""

from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path

SEEN = ("R1", "R2", "R3", "R4", "R5", "R6", "R8")
UNSEEN = ("R7",)
LABELS = ("ADAPTIVE_WALL", "FIXED_SERIAL", "FIXED_W6", "FIXED_GPU")


def load(p):
    raw = Path(p).read_bytes()
    return json.loads(gzip.decompress(raw) if str(p).endswith(".gz") else raw)


def med(xs):
    s = sorted(xs)
    n = len(s)
    return None if not n else s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def analyze(out, profile=None):
    out = Path(out)
    env = load(out / "env.json")["env"]
    verdicts = {f.stem: load(f) for f in out.glob("checker_verdict_*.json")}
    final_ok = verdicts.get("checker_verdict_final", {}).get("verdict") == "EVIDENCE OK"
    svc = {}
    for f in sorted((out / "services").glob("r*/*.json.gz")):
        s = load(f)
        if s["env_id"] != env["env_id"]:
            continue
        svc.setdefault((s["request_id"], s["label"]), []).append(s)
    table = {}
    for (rid, lab), lst in sorted(svc.items()):
        table.setdefault(rid, {})[lab] = {
            "n": len(lst), "wall_med_s": med([s["service_wall_s"] for s in lst]),
            "wall_all_s": [round(s["service_wall_s"], 3) for s in sorted(lst, key=lambda x: x["repeat"])],
            "cpu_med_s": med([s["service_cpu_s"] for s in lst]), "p_sequence": lst[0]["p_sequence"],
            "backends": [pz["attempts"][-1]["plan"]["backend"] + (f"/W{pz['attempts'][-1]['plan']['worker_count']}"
                                                                     if pz["attempts"][-1]["plan"]["worker_count"] else "")
                         for pz in lst[0]["passes"]],
            "status": lst[0]["status"], "label": lst[0]["execution_label"],
            "selector_ms": [round(pz["selector_ms"], 3) for s in lst for pz in s["passes"]]}
    per = {}
    for rid, t in table.items():
        if "ADAPTIVE_WALL" not in t:
            continue
        oracle = min(v["wall_med_s"] for v in t.values())
        per[rid] = {"oracle_s": oracle, "oracle_label": min(t, key=lambda k: t[k]["wall_med_s"]),
                    "adaptive_s": t["ADAPTIVE_WALL"]["wall_med_s"], "ratio": t["ADAPTIVE_WALL"]["wall_med_s"] / oracle}
    seen = [r for r in SEEN if r in per]
    sa = sum(table[r]["ADAPTIVE_WALL"]["wall_med_s"] for r in seen)
    sw6 = sum(table[r]["FIXED_W6"]["wall_med_s"] for r in seen if "FIXED_W6" in table[r])
    sser = sum(table[r]["FIXED_SERIAL"]["wall_med_s"] for r in seen)
    best_uniform = min(sser, sw6) if sw6 else sser
    soracle = sum(per[r]["oracle_s"] for r in seen)
    npass = sum(len(svc[(r, "ADAPTIVE_WALL")][0]["passes"]) for r in seen)
    g_w6 = sa / sw6 if sw6 else None
    g_best = sa / best_uniform if best_uniform else None
    bound = 1.10 * soracle + 0.5 * npass
    cpu = {r: {lab: table[r][lab]["cpu_med_s"] for lab in table[r]} for r in table}
    counter = [{"request": r, **per[r]} for r in per if per[r]["ratio"] > 1.10]
    # environment cases
    cases = {}
    for f in sorted((out / "cases").glob("*.json.gz")):
        s = load(f)
        cases[f.name.replace(".json.gz", "")] = {
            "status": s["status"], "p_sequence": s["p_sequence"], "wall_s": s.get("service_wall_s"),
            "cpu_s": s.get("service_cpu_s"),
            "plans": [(a["plan"]["backend"], a["plan"]["worker_count"], a["plan"]["reasons"]) for pz in s["passes"]
                      for a in pz["attempts"]]}
    forced = load(out / "cases" / "forced_gpu.json") if (out / "cases" / "forced_gpu.json").exists() else []
    u = cases
    env_ok = ("U1" in u and all(b == "CPU_SERIAL" for b, _, _ in u["U1"]["plans"]) and
              "U2" in u and all(b != "GPU_HYBRID" for b, _, _ in u["U2"]["plans"]) and
              "U3" in u and u["U3"]["status"] == "REFUSED_UNVERIFIED_ENVIRONMENT" and not u["U3"]["p_sequence"])
    forced_ok = bool(forced) and all(c["adapter_violations"] and not c["executed"] for c in forced)
    acpu_ok = all(all(b == "CPU_SERIAL" for b, _, _ in v["plans"]) for k, v in cases.items()
                  if k.endswith("ADAPTIVE_CPU"))
    # p assumption: per (N, T) the order of fixed strategies' pass walls at each p
    order = {}
    for (rid, lab), lst in svc.items():
        if lab not in ("FIXED_SERIAL", "FIXED_W6", "FIXED_GPU"):
            continue
        for s in lst:
            for pz in s["passes"]:
                order.setdefault(f"N{s['N']}_T{s['T']}_p{pz['requested_p']}", {}).setdefault(lab, []).append(
                    pz["wall_s"])
    p_order = {k: sorted(((med(v), lab) for lab, v in d.items()), key=lambda x: x[0]) for k, d in order.items()}
    p_order = {k: [lab for _, lab in v] for k, v in p_order.items()}
    replay = [load(f) for f in (out / "replay").glob("*.json")] if (out / "replay").exists() else []
    gate100 = load(out / "gate100.json")["passed"] if (out / "gate100.json").exists() else None
    fail = not final_ok
    if fail:
        verdict = "ADAPTIVE_FAIL"
    elif env_ok and forced_ok and acpu_ok and g_best is not None and g_best <= 0.85 and sa <= bound:
        verdict = "ADAPTIVE_V1_READY"
    else:
        verdict = "ADAPTIVE_EXACT_NOT_USEFUL"
    res = {"env_id": env["env_id"], "cpu_model": env["cpu_model"], "gpu": env.get("gpu"), "checker": verdicts,
           "gate100_passed": gate100, "table": table, "per_request": per, "cpu_med": cpu,
           "seen": seen, "unseen": [r for r in UNSEEN if r in per],
           "sums": {"adaptive": sa, "fixed_w6": sw6, "fixed_serial": sser, "best_uniform_cpu": best_uniform,
                    "oracle": soracle, "adaptive_passes": npass, "deterioration_bound": bound},
           "G_W6": g_w6, "G_best": g_best, "counterexamples": counter, "cases": cases, "forced_gpu": forced,
           "env_cases_ok": env_ok, "forced_gpu_refused": forced_ok, "adaptive_cpu_all_serial": acpu_ok,
           "p_assumption_order": p_order,
           "replay": {"n": len(replay), "total_s": sum(r.get("replay_wall_s", 0) for r in replay)},
           "verdict": verdict}
    (out / "analysis.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--profile")
    a = ap.parse_args()
    r = analyze(a.out, a.profile)
    print(r["verdict"], "G_best", r["G_best"], "G_W6", r["G_W6"], "counterexamples", len(r["counterexamples"]))


if __name__ == "__main__":
    main()
