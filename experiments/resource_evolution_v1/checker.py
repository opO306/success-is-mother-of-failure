"""Independent checker for RESOURCE_EVOLUTION_PILOT_V1. Imports none of: worker, orch, selector, verifier, vserver,
pairloop, floatcand, campaign, adapters, policies. Own re-implementation of: acceptance re-verification (cells from
exact endpoints), the planned record list, the ADAPTIVE rule, the Rescorla-Wagner learner and CONDITIONED choices,
the line L(s,T). Builds the report tables only when evidence is OK.

    python -m experiments.resource_evolution_v1.checker RUN_DIR --out FILE
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import statistics
from fractions import Fraction as F
from pathlib import Path

from experiments.precision_pilot_a1 import checker as A1C

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SCEN = ("A2_bound", "A3_low", "A3_high")
EVAL = [(s, T) for T in (100, 1000, 3000) for s in SCEN]
TRAIN = [(s, T) for s in SCEN for T in (200, 2000)]
COND = [("A2_bound", 1000), ("A3_low", 1000), ("A3_high", 1000), ("A2_bound", 3000), ("A3_low", 3000),
        ("A3_high", 3000)]
TIERS = {"H0": (6, 50, 4096, 3), "H1": (4, 6, 2048, 3), "H2": (2, 3, 1024, 2), "H3": (1, 1.5, 512, 1),
         "H4": (1, 0.7, 256, 1)}
PHYS = [2, 4, 6, 8, 10, 0]
APPROVED = {"algebra", "rw:R1+R2", "original"}
N_ATOMS = {"A2_bound": 2, "A3_low": 3, "A3_high": 3}
BUNDLES = ["docs/active/precision_pilot_a1/results.json.gz", "docs/active/precision_pilot_a2t/results.json.gz",
           "docs/active/rewrite_pilot_a3/results.json.gz"]
PARAMS = ROOT / "experiments/precision_pilot_a2t/frozen_policy_params_a1.json"


class CheckError(Exception):
    pass


def lf(p):
    return hashlib.sha256(Path(p).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def my_line(s, T):
    a, b = (F(x) for x in json.loads(PARAMS.read_text(encoding="utf-8"))["lines"][s])
    return math.ceil(a + b * T)


def my_verify(rec, s, T):
    if rec.get("evaluator") not in APPROVED or (rec.get("scenario"), rec.get("T")) != (s, T):
        return False
    if rec.get("outcome") != "DECIDED" or rec.get("completed_steps") != T or rec.get("effective_p") != rec.get("requested_p"):
        return False
    if len(rec.get("endpoints_scaled") or []) != 6 * N_ATOMS[s]:
        return False
    if rec["evaluator"] != "original" and rec.get("force_swap_restored") is not True:
        return False
    return A1C.my_cells(rec["endpoints_scaled"]) == rec.get("cells") is not None or \
        (A1C.my_cells(rec["endpoints_scaled"]) is not None and A1C.my_cells(rec["endpoints_scaled"]) == rec.get("cells"))


def my_adaptive(v):
    if v["cores"] >= 3 and v["cpu_u"] >= 4 and v["spec"] >= 3:
        return "AGG3"
    if v["cpu_u"] >= 2:
        return "BASE"
    return "CONS"


def my_schedule(phase):
    A, Ap, B, Bp, N = (["A"], False), (["A"], True), (["B"], False), (["B"], True), ([], False)
    return {"T5": [A, N, A, A, N, A, A, N, A, A, N, A],
            "T6": [Ap, N, Ap, Ap, N, Ap, Ap, N, Ap, Ap, N, Ap, Ap, N, Ap, Ap] + [A, A, A, A],
            "T7A": [A] * 12, "T7B": [Bp, A] * 8}[phase]


def safe(ev):
    return ev.replace(":", "-").replace("+", "_")


def planned():
    names = [f"CAL__{s}_{T}__r{r}" for r in range(3) for s, T in TRAIN]
    for T in (100, 1000):
        for s in SCEN:
            for ev in ["algebra", "rw:R1+R2"] + (["original"] if (s, T) in (("A2_bound", 100), ("A3_high", 100)) else []):
                names += [f"T0__{safe(ev)}__{s}_{T}__cpu{c}" for c in (2, 8)]
    names += [f"T0__{safe(ev)}__A2_bound_3000__cpu{c}" for ev in ("algebra", "rw:R1+R2") for c in (2, 8)]
    names += [f"T0__smt_{a}_{b}__r{r}" for r in range(3) for a, b in ((2, 3), (2, 4))]
    names += [f"T1__{p}__k{k}__r{r}" for r in range(3) for k in (1, 2, 3, 4, 6) for p in ("BASE", "BASE_E2")]
    names += [f"T1__single_A3_high_1000__c{c}__r{r}" for r in range(3) for c in (1, 6)]
    names += [f"T2__{p}__{s}_{T}__r{r}" for r in range(3) for s, T in EVAL for p in ("BASE", "SPEC_P_E1", "SPEC_EVAL")]
    names += [f"T2__S4__{s}_{T}__r{r}" for r in range(3) for s in ("A3_low", "A3_high") for T in (100, 1000)]
    names += [f"T2__S5_{m}__r{r}" for r in range(3) for m in ("inline", "after", "pipeline")]
    names += [f"T34__{t}__{x}__{s}_{T}" for t in TIERS for s, T in EVAL for x in ("FIXED_BASE", "FIXED_AGG3", "ADAPTIVE")]
    for ph in ("T5", "T6", "T7A", "T7B"):
        names += [f"{ph}__{i:02d}__{x}" for i in range(len(my_schedule(ph))) for x in ("COND", "NOLEARN")]
    names += [f"T8__{p}__{s}_{T}__r{r}" for r in range(3) for s, T in EVAL for p in ("BASE", "CONS", "AGG1", "AGG3")]
    names += [f"T9__{k}__{s}_{T}" for s, T in EVAL for k in ("float", "verifier_BASE", "typeA_E2", "decision")]
    names += [f"T10__{t}__{p}__{s}_{T}__r{r}" for r in range(2) for t in ("H1", "H2", "H3") for s, T in EVAL
              for p in ("AGG3", "CONS")]
    return names


def pct(xs, q):
    xs = sorted(xs)
    if not xs:
        return None
    return xs[min(len(xs) - 1, max(0, math.ceil(q * len(xs)) - 1))]


def lat(xs):
    xs = [x for x in xs if x is not None]
    return {"n": len(xs), "mean": statistics.mean(xs) if xs else None, "p50": statistics.median(xs) if xs else None,
            "p95": pct(xs, 0.95) if len(xs) >= 20 else "INSUFFICIENT_SAMPLES",
            "p99": pct(xs, 0.99) if len(xs) >= 100 else "INSUFFICIENT_SAMPLES", "max": max(xs) if xs else None}


def check_run(name, rec, s, T, allowed_cores, invalid, false_accept, seen):
    """Re-verify a run_plan/run_workers record."""
    ws = rec.get("workers", [])
    for w in ws:
        st = w.get("start") or {}
        if st and (st.get("affinity_readback") != w["spec"]["cpus"] or not set(w["spec"]["cpus"]) <= set(allowed_cores)):
            invalid.append(f"{name}: affinity {st.get('affinity_readback')} vs spec {w['spec']['cpus']} / allowed {allowed_cores}")
        if not w.get("exited_confirmed"):
            invalid.append(f"{name}: worker {w['name']} exit not confirmed")
        for p in w["passes"]:
            if p["outcome"] == "DECIDED" and not my_verify(p, s, T):
                if w.get("accepted") and p is w["passes"][-1]:
                    false_accept.append(f"{name}: accepted pass fails re-verification")
    status = rec.get("status")
    if status == "VERIFIED":
        acc = [w for w in ws if w.get("accepted")]
        if len(acc) != 1:
            invalid.append(f"{name}: {len(acc)} accepted workers")
            return
        dec = [p for p in acc[0]["passes"] if p["outcome"] == "DECIDED"]
        if not dec or not my_verify(dec[0], s, T):
            false_accept.append(f"{name}: accepted result not verifiable")
            return
        if rec["result"]["cells"] != dec[0]["cells"] or rec["result"]["endpoints_scaled"] != dec[0]["endpoints_scaled"]:
            invalid.append(f"{name}: result differs from the accepted pass")
        key = (s, T)
        seen.setdefault(key, set()).add(json.dumps(dec[0]["cells"]))
        if abs(rec["waste_cpu_s"] - (rec["total_cpu_s"] - acc[0]["cpu_s"])) > 1e-6:
            invalid.append(f"{name}: waste accounting")
    elif status in ("RESOURCE_REFUSED", "BUDGET_STARVATION"):
        env = rec["env"]
        if rec.get("refusal") == "RAM admission":
            nw = {"AGG3": 3, "SPEC_P_E1": 3, "SPEC_EVAL": 2}.get(rec.get("plan"), 1)
            if ws or nw * 150 <= env["ram_mb"]:
                invalid.append(f"{name}: RAM refusal inconsistent")
        elif rec.get("budget_hit") == "cpu":
            trig = rec.get("cpu_at_trigger", rec["total_cpu_s"])
            if trig < env["cpu_s"] - 1e-9 or rec["total_cpu_s"] < trig - 1e-9:
                invalid.append(f"{name}: cpu refusal below budget (trigger {trig:.3f}, total {rec['total_cpu_s']:.3f}, "
                               f"budget {env['cpu_s']:.3f})")
        elif rec.get("budget_hit") == "wall":
            if rec["wall_all_ended_s"] < env["wall_s"] - 0.2:
                invalid.append(f"{name}: wall refusal below budget")
        else:
            invalid.append(f"{name}: refusal without budget event")
        failed = any(p["outcome"] != "DECIDED" for w in ws for p in w["passes"])
        if (status == "BUDGET_STARVATION") != failed:
            invalid.append(f"{name}: starvation flag inconsistent")
        late = {(x["worker"], x["p"]) for x in rec.get("late_results_discarded", []) if x.get("verified")}
        if any(my_verify(p, s, T) and (w["name"], p["requested_p"]) not in late for w in ws for p in w["passes"]):
            invalid.append(f"{name}: a verifiable DECIDED pass was not accepted")
    elif status == "NO_VERIFIED_RESULT":
        pass
    else:
        invalid.append(f"{name}: unknown status {status}")
    if ws:
        cores_used = {c for w in ws for c in w["spec"]["cpus"]}
        limit = len(cores_used) * rec.get("wall_all_ended_s", rec.get("wall_s", 0)) * 1.10 + 0.5 * len(ws)
        if rec["total_cpu_s"] > limit:
            invalid.append(f"{name}: CPU {rec['total_cpu_s']:.2f} exceeds cores x wall bound {limit:.2f} (hidden cores?)")


def check(run_dir):
    d = Path(run_dir)
    seal = json.loads((d / "execution_seal.json").read_text(encoding="utf-8"))
    bad = [s for s, h in seal["source_sha256_lf"].items() if lf(ROOT / s) != h]
    if bad:
        raise CheckError(f"sources changed: {bad}")
    incomplete, invalid, conflicts, false_accept = [], [], [], []
    if seal.get("sealed_sources_dirty"):
        incomplete.append("campaign started with uncommitted sealed sources")
    R = {}
    for n in planned():
        f = d / f"{n}.json"
        if not f.exists():
            incomplete.append(f"missing: {n}")
        else:
            R[n] = json.loads(f.read_text(encoding="utf-8"))
    extra = [f.stem for f in d.glob("*.json") if f.stem not in R and f.stem not in ("execution_seal", "calibration")]
    if extra:
        invalid.append(f"unplanned records: {extra[:5]}")
    cal = json.loads((d / "calibration.json").read_text(encoding="utf-8"))
    rows = [(s, T, R[f"CAL__{s}_{T}__r{r}"]["workers"][0]) for r in range(3) for s, T in TRAIN
            if f"CAL__{s}_{T}__r{r}" in R]
    if rows:
        o = statistics.median(w["cpu_s"] - sum(p["cpu_s"] for p in w["passes"]) for _, _, w in rows)
        kappa = {s: statistics.median(w["passes"][0]["cpu_s"] / T for s2, T, w in rows if s2 == s) for s in SCEN}
        u = {f"{s}@{T}": o + kappa[s] * T for s in SCEN for T in (100, 1000, 3000)}
        if any(abs(u[k] - cal["u"][k]) > 1e-9 for k in u):
            invalid.append("calibration u not re-derivable from CAL records")
    us = cal["u"]

    # reference cells per request from earlier bundles
    ref = {}
    for b in BUNDLES:
        with gzip.open(ROOT / b, "rb") as fh:
            run = json.loads(fh.read())["run"]
        for name, text in run.items():
            if not name.startswith(("eval__", "inv__", "train__")):
                continue
            doc = json.loads(text)
            for h in (doc.get("passes") or [doc]):
                if h.get("outcome") == "DECIDED":
                    ref.setdefault((h["scenario"], h["T"]), set()).add(json.dumps(h["cells"]))
    for k, v in ref.items():
        if len(v) > 1:
            conflicts.append(f"earlier bundles disagree at {k}")
    seen = {}

    def accept_check(name, rec, s, T, allowed_cores):
        check_run(name, rec, s, T, allowed_cores, invalid, false_accept, seen)

    def batch_check(name, b, k):
        for key, e in b["results"].items():
            s, T = key.split("@")[0], int(key.split("@")[1])
            if e["core"] not in PHYS[:k] or (e["start"] or {}).get("affinity_readback") != [e["core"]]:
                invalid.append(f"{name}: core/affinity {e['core']}")
            if e["decided"] is None or not my_verify(e["decided"], s, T):
                invalid.append(f"{name}: {key} not verified")
                continue
            if e["status"] != "VERIFIED":
                invalid.append(f"{name}: status")
            seen.setdefault((s, T), set()).add(json.dumps(e["decided"]["cells"]))
        if b["total_cpu_s"] > k * b["wall_s"] * 1.10 + 0.5 * len(b["results"]):
            invalid.append(f"{name}: CPU exceeds k x wall")
        if len(b["results"]) != len(EVAL):
            invalid.append(f"{name}: batch incomplete")

    def env_of(tier, s, T):
        c, cu, ram, sp = TIERS[tier]
        return c, cu * us[f"{s}@{T}"], ram, sp

    for n, rec in R.items():
        ph = n.split("__")[0]
        if ph == "CAL":
            s, T = n.split("__")[1].rsplit("_", 1)
            accept_check(n, rec, s, int(T), [2])
        elif ph == "T0" and "smt" not in n:
            s, T = n.split("__")[2].rsplit("_", 1)
            accept_check(n, rec, s, int(T), [int(n[-1])])
        elif ph == "T1" and "single" not in n:
            batch_check(n, rec, int(n.split("__k")[1].split("__")[0]))
        elif ph == "T1":
            if "c1" in n:
                accept_check(n, rec, "A3_high", 1000, [2])
            elif not my_verify(rec["passes"][-1], "A3_high", 1000):
                false_accept.append(f"{n}: not verifiable")
        elif ph == "T2" and "S4" not in n and "S5" not in n:
            plan, req = n.split("__")[1], n.split("__")[2]
            s, T = req.rsplit("_", 1)
            accept_check(n, rec, s, int(T), {"BASE": [2], "SPEC_P_E1": [2, 4, 6], "SPEC_EVAL": [2, 4]}[plan])
        elif ph == "T2" and "S4" in n:
            if not rec["bit_identical"]:
                conflicts.append(f"{n}: pair-parallel result differs from the serial pass")
            if not rec["parallel"]["workers_exited"]:
                invalid.append(f"{n}: pair workers not exited")
        elif ph == "T2":
            batch_check(n, rec, 5)
        elif ph == "T34":
            tier, sel, req = n.split("__")[1:4]
            s, T = req.rsplit("_", 1)
            T = int(T)
            c, cpu, ram, sp = env_of(tier, s, T)
            env = rec["env"]
            if (env["cores"], env["ram_mb"], env["spec"]) != (c, ram, sp) or abs(env["cpu_s"] - cpu) > 1e-9:
                invalid.append(f"{n}: env differs from the tier definition")
            accept_check(n, rec, s, T, PHYS[:c])
            if sel == "ADAPTIVE":
                vis = rec["selector_input"].get("visible_env", {})
                if set(rec["selector_input"]) - {"visible_env"} or abs(vis.get("cpu_u", -1) - TIERS[tier][1]) > 1e-9:
                    invalid.append(f"{n}: selector input outside the allowed keys or wrong")
                if rec["plan"] != my_adaptive(vis):
                    invalid.append(f"{n}: ADAPTIVE plan {rec['plan']} != rule {my_adaptive(vis)}")
            elif rec["plan"] != {"FIXED_BASE": "BASE", "FIXED_AGG3": "AGG3"}[sel]:
                invalid.append(f"{n}: fixed plan differs")
        elif ph in ("T8",):
            plan, req = n.split("__")[1], n.split("__")[2]
            s, T = req.rsplit("_", 1)
            accept_check(n, rec, s, int(T), PHYS)
        elif ph == "T10":
            tier, plan, req = n.split("__")[1:4]
            s, T = req.rsplit("_", 1)
            accept_check(n, rec, s, int(T), PHYS[:TIERS[tier][0]])
        elif ph == "T9" and ("verifier" in n or "typeA" in n):
            s, T = n.split("__")[2].rsplit("_", 1)
            accept_check(n, rec, s, int(T), [2])

    # conditioning: re-derive the learner and every choice
    V, idx = {}, 0
    cond_rows = []
    for ph in ("T5", "T6", "T7A", "T7B"):
        for i, (cues, pressure) in enumerate(my_schedule(ph)):
            s, T = COND[idx % len(COND)]
            idx += 1
            a, b = R.get(f"{ph}__{i:02d}__COND"), R.get(f"{ph}__{i:02d}__NOLEARN")
            if a is None or b is None:
                continue
            u = us[f"{s}@{T}"]
            want = "CONS" if any(V.get(c, 0.0) > 0.5 for c in cues) else my_adaptive(
                {"cores": 6, "cpu_u": 50.0, "spec": 3, "ram_mb": 4096})
            if a["plan"] != want or a["V_before"] != V or a["cues"] != cues or a["hidden_pressure"] != pressure:
                invalid.append(f"{ph} {i}: conditioned choice/V/cue/pressure not re-derivable")
            inp = a["selector_input"]
            if set(inp) - {"visible_env", "cues", "V"} or inp["visible_env"].get("cpu_u") != 50.0:
                invalid.append(f"{ph} {i}: selector input leaks hidden budget or extra keys")
            hid_cpu = 1.5 * u if pressure else 50 * u
            for x in (a, b):
                if abs(x["env"]["cpu_s"] - hid_cpu) > 1e-9 or x["scenario"] != s or x["T"] != T:
                    invalid.append(f"{ph} {i}: trial env/request differs")
                accept_check(f"{ph}__{i:02d}", x, s, T, PHYS)
            if b["plan"] != "AGG3":
                invalid.append(f"{ph} {i}: NO_LEARN plan")
            cond_rows.append({"phase": ph, "i": i, "cues": cues, "pressure": pressure, "V_before": dict(V),
                              "plan": a["plan"], "cond": a, "ctrl": b})
            for c in cues:
                V[c] = V.get(c, 0.0) + 0.3 * ((1.0 if pressure else 0.0) - V.get(c, 0.0))
    # T0 regression and invariance
    t0 = {}
    for n, rec in R.items():
        if n.startswith("T0__") and "smt" not in n and rec.get("status") == "VERIFIED":
            key = n.rsplit("__cpu", 1)[0]
            t0.setdefault(key, []).append(rec["result"]["endpoints_scaled"])
    for key, v in t0.items():
        if len(v) != 2 or v[0] != v[1]:
            conflicts.append(f"{key}: endpoints differ between CPU 2 and CPU 8 (or a run missing/unverified)")
    gates = {}
    gdir = d / "T0_e2_gates"
    if (gdir / "verify.json").exists() and (gdir / "sympy.json").exists():
        gv = json.loads((gdir / "verify.json").read_text(encoding="utf-8"))
        gs = json.loads((gdir / "sympy.json").read_text(encoding="utf-8"))
        gates = {"S1_S6": gv.get("PASS_S1_S6_except_S3b"), "sympy": gs.get("sympy_zero")}
        if gates != {"S1_S6": True, "sympy": True}:
            invalid.append(f"E2 gates did not pass: {gates}")
    else:
        incomplete.append("missing T0 E2 gate records")
    for r in range(3):
        a, b = R.get(f"T1__BASE__k1__r{r}"), R.get(f"T1__BASE__k6__r{r}")
        if a and b:
            for key in a["results"]:
                if a["results"][key]["decided"]["endpoints_scaled"] != b["results"][key]["decided"]["endpoints_scaled"]:
                    conflicts.append(f"T1 r{r} {key}: k=1 and k=6 results differ")
    # T9
    t9 = {}
    for s, T in EVAL:
        fl, ver, dec = R.get(f"T9__float__{s}_{T}"), R.get(f"T9__verifier_BASE__{s}_{T}"), R.get(f"T9__decision__{s}_{T}")
        if fl and ver and dec:
            vc = ver["result"]["cells"] if ver.get("status") == "VERIFIED" else None
            hit = fl["cells"] == vc
            if dec["candidate_cells_equal_verified"] != hit or dec["injected_wrong_accepted"]:
                invalid.append(f"T9 {s}@{T}: decision record inconsistent or injected wrong accepted")
            t9[f"{s}@{T}"] = {"hit": hit, "float_cpu_s": fl["cpu_s"], "verifier_cpu_s": ver["total_cpu_s"],
                              "max_raw_diff": None if vc is None else max(abs(a - b) for a, b in zip(fl["cells"], vc))}
    for key, cells in seen.items():
        if len(cells) > 1:
            conflicts.append(f"{key}: VERIFIED cells disagree across runs")
        if key in ref and not cells <= ref[key]:
            conflicts.append(f"{key}: VERIFIED cells differ from earlier bundles")
    ok = not incomplete and not invalid and not conflicts and not false_accept
    tables = build_tables(R, us, cond_rows, t9, gates) if ok else None
    return {"checker": "RESOURCE_EVOLUTION_PILOT_V1 independent checker", "EVIDENCE": "OK" if ok else "NOT_OK",
            "incomplete": incomplete, "invalid_evidence": invalid, "conflicts": conflicts, "false_accepts": false_accept,
            "verified_requests_with_reference": sorted(f"{s}@{T}" for s, T in seen if (s, T) in ref),
            "calibration": cal, "tables": tables}


def build_tables(R, us, cond_rows, t9, gates):
    med = lambda xs: statistics.median(xs) if xs else None  # noqa: E731
    T = {"T0": {"e2_gates": gates}}
    smt = {}
    for pair in ("2_3", "2_4"):
        smt[pair] = med([statistics.mean(R[f"T0__smt_{pair}__r{r}"]["burn_wall_s"]) for r in range(3)])
    T["T0"]["smt_burn_wall_s"] = smt
    t1 = {}
    for plan in ("BASE", "BASE_E2"):
        base = med([R[f"T1__{plan}__k1__r{r}"]["wall_s"] for r in range(3)])
        for k in (1, 2, 3, 4, 6):
            rs = [R[f"T1__{plan}__k{k}__r{r}"] for r in range(3)]
            w, c = med([x["wall_s"] for x in rs]), med([x["total_cpu_s"] for x in rs])
            t1[f"{plan}@k{k}"] = {"wall_med": w, "cpu_med": c, "orch_cpu_med": med([x["orch_cpu_s"] for x in rs]),
                                  "speedup": base / w, "efficiency": base / w / k,
                                  "peak_mb_med": med([x["peak_mb"] for x in rs])}
    t1["single_c1_wall"] = med([R[f"T1__single_A3_high_1000__c1__r{r}"]["wall_s"] for r in range(3)])
    t1["single_c6_wall"] = med([R[f"T1__single_A3_high_1000__c6__r{r}"]["wall_s"] for r in range(3)])
    T["T1"] = t1
    t2 = {}
    for plan in ("BASE", "SPEC_P_E1", "SPEC_EVAL"):
        rs = [R[f"T2__{plan}__{s}_{T_}__r{r}"] for r in range(3) for s, T_ in EVAL]
        t2[plan] = {"wall": lat([x["wall_s"] for x in rs]), "cpu_med": med([x["total_cpu_s"] for x in rs]),
                    "waste_med": med([x["waste_cpu_s"] for x in rs]),
                    "verified": sum(x["status"] == "VERIFIED" for x in rs), "n": len(rs)}
    per = {}
    for s, T_ in EVAL:
        b = med([R[f"T2__BASE__{s}_{T_}__r{r}"]["wall_s"] for r in range(3)])
        per[f"{s}@{T_}"] = {p: med([R[f"T2__{p}__{s}_{T_}__r{r}"]["wall_s"] for r in range(3)]) / b
                            for p in ("SPEC_P_E1", "SPEC_EVAL")}
        per[f"{s}@{T_}"].update({f"{p}_cpu": med([R[f"T2__{p}__{s}_{T_}__r{r}"]["total_cpu_s"] for r in range(3)]) /
                                 med([R[f"T2__BASE__{s}_{T_}__r{r}"]["total_cpu_s"] for r in range(3)])
                                 for p in ("SPEC_P_E1", "SPEC_EVAL")})
    t2["per_request_vs_BASE"] = per
    s4 = {}
    for s in ("A3_low", "A3_high"):
        for T_ in (100, 1000):
            rs = [R[f"T2__S4__{s}_{T_}__r{r}"] for r in range(3)]
            s4[f"{s}@{T_}"] = {"serial_wall": med([x["serial"]["wall_s"] for x in rs]),
                               "parallel_wall": med([x["parallel"]["wall_s"] for x in rs]),
                               "spawn_wall": med([x["parallel"]["spawn_wall_s"] for x in rs]),
                               "serial_cpu": med([x["serial"]["cpu_s"] for x in rs]),
                               "parallel_cpu": med([x["parallel"]["main_cpu_s"] + sum(x["parallel"]["worker_cpu_s"])
                                                    for x in rs]),
                               "bit_identical": all(x["bit_identical"] for x in rs)}
    t2["S4"] = s4
    t2["S5"] = {m: {"wall_med": med([R[f"T2__S5_{m}__r{r}"]["wall_s"] for r in range(3)]),
                    "verify_cpu_med": med([R[f"T2__S5_{m}__r{r}"]["verify_cpu_s"] for r in range(3)]),
                    "orch_cpu_med": med([R[f"T2__S5_{m}__r{r}"]["orch_cpu_s"] for r in range(3)])}
                for m in ("inline", "after", "pipeline")}
    T["T2"] = t2
    t34 = {}
    for tier in TIERS:
        for sel in ("FIXED_BASE", "FIXED_AGG3", "ADAPTIVE"):
            rs = [R[f"T34__{tier}__{sel}__{s}_{T_}"] for s, T_ in EVAL]
            t34[f"{tier}/{sel}"] = {"verified": sum(x["status"] == "VERIFIED" for x in rs),
                                    "refused": sum(x["status"] == "RESOURCE_REFUSED" for x in rs),
                                    "starvation": sum(x["status"] == "BUDGET_STARVATION" for x in rs),
                                    "plans": sorted({x["plan"] for x in rs}),
                                    "wall_sum_verified": sum(x["wall_s"] for x in rs if x["status"] == "VERIFIED"),
                                    "cpu_sum": sum(x["total_cpu_s"] for x in rs),
                                    "waste_sum": sum(x["waste_cpu_s"] for x in rs)}
    T["T34"] = t34
    cr = {}
    for ph in ("T5", "T6", "T7A", "T7B"):
        rows = [x for x in cond_rows if x["phase"] == ph]
        cr[ph] = [{"i": x["i"], "cues": x["cues"], "pressure": x["pressure"], "V_before": x["V_before"], "plan": x["plan"],
                   "cond_status": x["cond"]["status"], "ctrl_status": x["ctrl"]["status"],
                   "cond_wall": x["cond"]["wall_s"], "ctrl_wall": x["ctrl"]["wall_s"],
                   "cond_cpu": x["cond"]["total_cpu_s"], "ctrl_cpu": x["ctrl"]["total_cpu_s"]} for x in rows]
    T["T567"] = cr
    t8 = {}
    for plan in ("BASE", "CONS", "AGG1", "AGG3"):
        rs = [R[f"T8__{plan}__{s}_{T_}__r{r}"] for r in range(3) for s, T_ in EVAL]
        t8[plan] = {"verified": sum(x["status"] == "VERIFIED" for x in rs), "n": len(rs),
                    "wall": lat([x["wall_s"] for x in rs]), "cpu_sum": sum(x["total_cpu_s"] for x in rs),
                    "waste_sum": sum(x["waste_cpu_s"] for x in rs),
                    "first_try_success": sum(1 for x in rs if x["status"] == "VERIFIED" and
                                             len([p for w in x["workers"] if w["accepted"] for p in w["passes"]]) == 1
                                             and not any(e.get("fallback_start_p") for e in x["events"])),
                    "fallbacks": sum(1 for x in rs if any(e.get("fallback_start_p") for e in x["events"]))}
    rel = {}
    for s, T_ in EVAL:
        b = med([R[f"T8__BASE__{s}_{T_}__r{r}"]["wall_s"] for r in range(3)])
        rel[f"{s}@{T_}"] = {p: med([R[f"T8__{p}__{s}_{T_}__r{r}"]["wall_s"] for r in range(3)]) / b
                           for p in ("CONS", "AGG1", "AGG3")}
    t8["wall_vs_BASE_per_request"] = rel
    T["T8"] = t8
    T["T9"] = t9
    t10 = {}
    for tier in ("H1", "H2", "H3"):
        for plan in ("AGG3", "CONS"):
            rs = [R[f"T10__{tier}__{plan}__{s}_{T_}__r{r}"] for r in range(2) for s, T_ in EVAL]
            t10[f"{tier}/{plan}"] = {"verified": sum(x["status"] == "VERIFIED" for x in rs), "n": len(rs),
                                     "refused": sum(x["status"] == "RESOURCE_REFUSED" for x in rs),
                                     "starvation": sum(x["status"] == "BUDGET_STARVATION" for x in rs),
                                     "wall_verified": lat([x["wall_s"] for x in rs if x["status"] == "VERIFIED"]),
                                     "cpu_sum": sum(x["total_cpu_s"] for x in rs),
                                     "waste_sum": sum(x["waste_cpu_s"] for x in rs)}
    T["T10"] = t10
    return T


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    v = check(a.run_dir)
    Path(a.out).write_text(json.dumps(v, indent=1, default=str), encoding="utf-8")
    print(v["EVIDENCE"], "incomplete", len(v["incomplete"]), "invalid", len(v["invalid_evidence"]),
          "conflicts", len(v["conflicts"]), "false_accepts", len(v["false_accepts"]))


if __name__ == "__main__":
    main()
