"""Independent checker for PRECISION_PILOT_A2T. Imports none of: A1 policies/runner/campaign/evaluator_adapter, A2T
evaluator_adapter/runner/campaign, the upstream probe or harness. It reuses only the A1 CHECKER's own rule
implementation (my_next, my_cells; verifier side, frozen at 0e49576).

1. binding: sealed sources unchanged; upstream copy equals its SHA256SUMS; frozen policy params equal the A1 bundle's
   and their hash; A1 bundle hash; run records name the repository modules (never the vendor copies);
2. audit: algebra p-support rows re-checked; transform sample checks PASS; upstream tests passed;
3. completeness of the planned SERVE set and the planned algebra INVESTIGATE set, record consistency, child exit;
4. per pass: effective p, completed steps, endpoint count, cells recomputed from the stored exact endpoints, force swap
   restored (algebra); every next-p choice re-derived with the A1 frozen parameters; final status re-derived;
5. agreement: same (evaluator, request, p) deterministic; new original passes equal A1's at the same (request, p);
   every pair of passes that reached T (both evaluators, A1 included) has intersecting enclosures in every component;
   all decided cells of a request equal (both evaluators, A1 included);
6. tables (only when evidence is OK): per request and combination the tried p, outcomes, costs; minima/brackets per
   evaluator; same-p table; derived effect split; frozen P2/P3 transfer. Verification CPU is reported separately.

    python -m experiments.precision_pilot_a2t.checker RUN_DIR --out FILE
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import re
import statistics
import time
from fractions import Fraction as F
from pathlib import Path

from experiments.precision_pilot_a1 import checker as A1C

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
UP = ROOT / "experiments/formula_repro_b_v0/upstream"
A1_BUNDLE = ROOT / "docs/active/precision_pilot_a1/results.json.gz"
A1_BUNDLE_SHA = "af5c13e6f61b52211c244a282fbd70ac4fb70cbede63d7c9b643d7ec477e357a"
POLICY_HASH = "6d601462f31f5505a2656fe8e2b853fcce617174de279766947dbadda816348e"
SCEN = ("A2_bound", "A3_low", "A3_high")
SHORT_T, LONG_T = (100, 1000), (3000, 5000, 10000)
COMBOS = (("original", "P0"), ("original", "P2"), ("original", "P3"),
          ("algebra", "P0"), ("algebra", "P1"), ("algebra", "P2"), ("algebra", "P3"))
N_ATOMS = {"A2_bound": 2, "A3_low": 3, "A3_high": 3}
AUDIT_P = (65, 97, 129, 137, 193, 300, 458, 777)
MODULE_TAILS = {"exact_expression_gate_v1.stream": "exact_expression_gate_v1/stream.py",
                "exact_expression_gate_v1.common": "exact_expression_gate_v1/common.py",
                "exact_expression_gate_v0.lang_iv": "exact_expression_gate_v0/lang_iv.py",
                "a_reference.ar2_lang2024": "a_reference/ar2_lang2024.py"}


class CheckError(Exception):
    pass


def lf(p):
    return hashlib.sha256(Path(p).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _norm(path):
    return str(path).replace("\\", "/")


def _repo_module(path, tail):
    p = _norm(path)
    return p == _norm(ROOT / tail) and "/upstream/" not in p and "/vendor/" not in p


def _ends(h):
    return [(F(a), F(b)) for a, b in h["endpoints_scaled"]]


def _width(h):
    return max(b - a for a, b in _ends(h))


def _med(xs):
    xs = [x for x in xs if x is not None]
    return statistics.median(xs) if xs else None


def check(run_dir):
    d = Path(run_dir)
    tv0 = time.process_time()
    seal = json.loads((d / "execution_seal.json").read_text(encoding="utf-8"))
    bad = [s for s, h in seal["source_sha256_lf"].items() if lf(ROOT / s) != h]
    if bad:
        raise CheckError(f"sources changed: {bad}")
    incomplete, invalid, conflicts = [], [], []
    if seal.get("sealed_sources_dirty"):
        incomplete.append("campaign started with uncommitted sealed sources")
    vcost = {}

    # 1. binding
    sums = json.loads((UP / "SHA256SUMS.json").read_text(encoding="utf-8"))
    present = [k for k in sums if (UP / k).exists()]
    if not {"probe.py", "test_probe.py"} <= set(present):
        invalid.append("upstream copy incomplete")
    for k in present:
        if hashlib.sha256((UP / k).read_bytes()).hexdigest() != sums[k]:
            invalid.append(f"upstream file differs from SHA256SUMS: {k}")
    if hashlib.sha256(A1_BUNDLE.read_bytes()).hexdigest() != A1_BUNDLE_SHA:
        raise CheckError("A1 bundle differs from the sealed hash")
    with gzip.open(A1_BUNDLE, "rb") as f:
        a1 = json.loads(f.read())["run"]
    prm = json.loads((HERE / "frozen_policy_params_a1.json").read_text(encoding="utf-8"))
    core = {k: v for k, v in prm.items() if k != "policy_hash"}
    if hashlib.sha256(json.dumps(core, sort_keys=True).encode()).hexdigest() != POLICY_HASH \
            or prm.get("policy_hash") != POLICY_HASH or json.loads(a1["policy_params.json"]) != prm:
        invalid.append("frozen policy params differ from A1")

    def load(name):
        if (d / f"{name}.ERROR.txt").exists():
            incomplete.append(f"run failed: {name}")
        f = d / f"{name}.json"
        if not f.exists():
            incomplete.append(f"missing: {name}")
            return None
        doc = json.loads(f.read_text(encoding="utf-8"))
        if doc.get("child_exit_code") != 0 or not doc.get("child_pid_confirmed_exited"):
            invalid.append(f"{name}: child exit not confirmed")
        mods = doc.get("modules") or {}
        if set(mods) != set(MODULE_TAILS) or not all(_repo_module(mods[m], t) for m, t in MODULE_TAILS.items()):
            invalid.append(f"{name}: modules are not the repository modules")
        return doc

    # 2. audit
    up = d / "upstream_pytest.txt"
    if not up.exists():
        incomplete.append("missing: upstream_pytest.txt")
    else:
        t = up.read_text(encoding="utf-8")
        m = re.search(r"(\d+) passed", t)
        if "exit_code=0" not in t or not m or int(m.group(1)) < 27 or re.search(r"\d+ (failed|errors?)\b", t):
            invalid.append("upstream tests did not pass")
    audit = load("audit")
    if audit:
        rows = {r["p"]: r for r in audit["rows"]}
        tc = audit["transform_checks"]
        if sorted(rows) != sorted(AUDIT_P) or not all(
                r["effective_p"] == p and r["meets_original_1024"] and r["cells_agree"] and r["force_swap_restored"]
                for p, r in rows.items()) or audit["reference_outcome"] != "DECIDED":
            invalid.append("algebra p-support audit not passed")
        if not (tc["PASS"] and tc["RET_B_all_positive"] and tc["r_min_positive"] and not tc["point_failures"]
                and not tc["interval_failures"] and tc["point_checks"] == 192 and tc["interval_checks"] == 48):
            invalid.append("transform sample checks not passed")
        if not str(audit.get("probe_file", "")).replace("\\", "/").endswith("formula_repro_b_v0/upstream/probe.py"):
            invalid.append("audit probe file unexpected")

    # 3-4. runs
    passes = {}                                         # (ev, scen, T, p) -> [(name, pass)]

    def take(name, ev, scen, T, plist):
        for h in plist:
            if (h["evaluator"], h["scenario"], h["T"]) != (ev, scen, T):
                invalid.append(f"{name}: pass metadata differs")
            if h.get("effective_p") != h["requested_p"]:
                invalid.append(f"{name}: effective_p {h.get('effective_p')} != requested {h['requested_p']}")
            if ev == "algebra" and h.get("force_swap_restored") is not True:
                invalid.append(f"{name}: force swap not restored")
            if h["outcome"] in ("DECIDED", "UNDECIDED_AT_PRECISION"):
                if h["completed_steps"] != T or not h.get("endpoints_scaled") or \
                        len(h["endpoints_scaled"]) != 6 * N_ATOMS[scen]:
                    invalid.append(f"{name}: p{h['requested_p']} completion/endpoints inconsistent")
                    continue
                mine = A1C.my_cells(h["endpoints_scaled"])
                if (mine is None) != (h["outcome"] == "UNDECIDED_AT_PRECISION") or mine != h["cells"]:
                    invalid.append(f"{name}: p{h['requested_p']} cells not reproduced from endpoints")
            elif h["outcome"] == "DOMAIN_UNPROVEN":
                if not 0 <= h["completed_steps"] < T:
                    invalid.append(f"{name}: domain stop with completed_steps {h['completed_steps']}")
            else:
                invalid.append(f"{name}: unexpected outcome {h['outcome']}")
            passes.setdefault((ev, scen, T, h["requested_p"]), []).append((name, h))

    plan = [(s, T, ev, pol, r) for s in SCEN for T in SHORT_T for ev, pol in COMBOS for r in range(3)] + \
           [(s, T, ev, pol, 0) for s in SCEN for T in LONG_T for ev, pol in COMBOS]
    serve = {}
    for scen, T, ev, pol, rep in plan:
        name = f"eval__{scen}__T{T}__{ev}__{pol}__r{rep}"
        t0 = time.process_time()
        doc = load(name)
        if not doc:
            continue
        if (doc["evaluator"], doc["scenario"], doc["T"], doc["policy"]) != (ev, scen, T, pol) or \
                doc.get("policy_hash") != POLICY_HASH:
            invalid.append(f"{name}: metadata differs")
        if ev == "algebra" and not str(doc.get("probe_file", "")).replace("\\", "/").endswith(
                "formula_repro_b_v0/upstream/probe.py"):
            invalid.append(f"{name}: probe file unexpected")
        hist = doc["passes"]
        take(name, ev, scen, T, hist)
        for i in range(len(hist) + 1):
            n = A1C.my_next(pol, prm, scen, hist[:i], T)
            if i < len(hist):
                if n != hist[i]["requested_p"]:
                    invalid.append(f"{name}: pass {i} p{hist[i]['requested_p']} but the rule gives {n}")
                    break
            else:
                end = hist[-1]["outcome"] if n is None else ("RESOURCE_REFUSED" if n == "CAP" or len(hist) >= 24 or
                                                             sum(h["cpu_s"] for h in hist) >= 5400 else "UNFINISHED")
                if end != doc["status"]:
                    invalid.append(f"{name}: status {doc['status']} but the rule ends with {end}")
        serve[(scen, T, ev, pol, rep)] = doc
        vcost[name] = time.process_time() - t0
    inv = {}
    for scen in SCEN:
        for T in SHORT_T:
            runs = [serve[(scen, T, "algebra", pol, r)] for pol in ("P0", "P1", "P2", "P3") for r in range(3)
                    if (scen, T, "algebra", pol, r) in serve]
            tried = {h["requested_p"] for x in runs for h in x["passes"]}
            low = min((h["requested_p"] for x in runs for h in x["passes"] if h["outcome"] == "DECIDED"), default=None)
            for p in range(64, low or 64):
                if p not in tried and not (d / f"inv__{scen}__T{T}__algebra__p{p}.json").exists():
                    incomplete.append(f"missing investigate pass: {scen}@{T} p{p}")
            for f in sorted(d.glob(f"inv__{scen}__T{T}__algebra__p*.json")):
                t0 = time.process_time()
                doc = load(f.stem)
                if doc:
                    take(f.stem, "algebra", scen, T, [doc])
                    inv.setdefault((scen, T), []).append(doc)
                vcost[f.stem] = time.process_time() - t0
    if [x for x in d.glob("eval__*.json") if not any(x.stem == f"eval__{s}__T{T}__{e}__{p}__r{r}"
                                                     for s, T, e, p, r in plan)]:
        invalid.append("unplanned eval files present")

    # 5. agreement
    ta = time.process_time()
    for key, lst in passes.items():
        if len({(h["outcome"], json.dumps(h.get("endpoints_scaled"))) for _, h in lst}) > 1:
            conflicts.append(f"{key}: same (evaluator, request, p) gave different outcomes/endpoints")
    a1p = {}
    for name, text in a1.items():
        if not name.startswith(("eval__", "inv__", "train__")):
            continue
        doc = json.loads(text)
        for h in (doc.get("passes") or [doc]):
            a1p[(h["scenario"], h["T"], h["requested_p"])] = h
    a1_shared = 0
    for (ev, scen, T, p), lst in passes.items():
        h0 = a1p.get((scen, T, p))
        if ev == "original" and h0 is not None:
            a1_shared += 1
            h = lst[0][1]
            if (h["outcome"], h.get("endpoints_scaled")) != (h0["outcome"], h0.get("endpoints_scaled")):
                conflicts.append(f"original {scen}@{T} p{p}: differs from the A1 pass")
    n_pairs = 0
    for scen in SCEN:
        for T in SHORT_T + LONG_T:
            reached = [(f"{ev}:p{p}", _ends(lst[0][1])) for (ev, s, t, p), lst in passes.items()
                       if (s, t) == (scen, T) and lst[0][1]["outcome"] in ("DECIDED", "UNDECIDED_AT_PRECISION")
                       and lst[0][1]["completed_steps"] == T and lst[0][1].get("endpoints_scaled")]
            reached += [(f"A1:p{p}", _ends(h)) for (s, t, p), h in a1p.items() if (s, t) == (scen, T)
                        and h["outcome"] in ("DECIDED", "UNDECIDED_AT_PRECISION")]
            for i in range(len(reached)):
                for j in range(i + 1, len(reached)):
                    n_pairs += 1
                    if not all(a0 <= b1 and b0 <= a1_ for (a0, a1_), (b0, b1) in zip(reached[i][1], reached[j][1])):
                        conflicts.append(f"{scen}@{T}: enclosures {reached[i][0]} and {reached[j][0]} do not intersect")
            cells = {json.dumps(lst[0][1]["cells"]) for (ev, s, t, p), lst in passes.items()
                     if (s, t) == (scen, T) and lst[0][1]["outcome"] == "DECIDED"}
            cells |= {json.dumps(h["cells"]) for (s, t, p), h in a1p.items() if (s, t) == (scen, T)
                      and h["outcome"] == "DECIDED"}
            if len(cells) > 1:
                conflicts.append(f"{scen}@{T}: decided cells disagree")
    agreement_cpu = time.process_time() - ta
    evidence_ok = not incomplete and not invalid and not conflicts

    # 6. tables
    def states(ev, scen, T, with_a1):
        st = {p: lst[0][1]["outcome"] for (e, s, t, p), lst in passes.items() if (e, s, t) == (ev, scen, T)}
        if with_a1:
            for (s, t, p), h in a1p.items():
                if (s, t) == (scen, T):
                    st.setdefault(p, h["outcome"])
        return st

    def minimum(st):
        low = min((p for p, o in st.items() if o == "DECIDED"), default=None)
        if low is None:
            return {"lowest_success": None}
        below = [p for p, o in st.items() if o != "DECIDED" and p < low]
        full = all(p in st and st[p] != "DECIDED" for p in range(64, low))
        return {"lowest_success": low, "max_nonsuccess_below": max(below, default=None),
                "claim": "MIN_SUCCESS_IN_DECLARED_DOMAIN" if full else "LOWEST_SUCCESS_OBSERVED",
                "untried_below": sum(1 for p in range(64, low) if p not in st),
                "fails_above_lowest": sorted(p for p, o in st.items() if o != "DECIDED" and p > low)}

    tables, totals_v = {}, {}
    for scen in SCEN:
        for T in SHORT_T + LONG_T:
            reps = 3 if T in SHORT_T else 1
            key = f"{scen}@{T}"
            row = {"minimum": {"original": {**minimum(states("original", scen, T, True)),
                                            "source": "this campaign + A1 bundle (A1 INVESTIGATE for short T)"},
                               "algebra": {**minimum(states("algebra", scen, T, False)),
                                           "source": "this campaign (algebra INVESTIGATE for short T)"}},
                   "investigate_algebra": {"passes": len(inv.get((scen, T), [])),
                                           "pass_cpu_s": sum(x["cpu_s"] for x in inv.get((scen, T), [])),
                                           "child_cpu_s": sum(x["child_cpu_s"] for x in inv.get((scen, T), []))},
                   "combos": {}}
            for ev, pol in COMBOS:
                ds = [serve.get((scen, T, ev, pol, r)) for r in range(reps)]
                ds = [x for x in ds if x]
                if not ds:
                    continue
                d0 = ds[0]
                c = {"status": sorted({x["status"] for x in ds}),
                     "tried_p": d0["tried_p"], "tried_p_same_all_reps": all(x["tried_p"] == d0["tried_p"] for x in ds),
                     "outcomes": [h["outcome"] for h in d0["passes"]],
                     "completed_steps": [h["completed_steps"] for h in d0["passes"]],
                     "final_p": d0["passes"][-1]["requested_p"] if d0["status"] == "DECIDED" else None,
                     "retries": len(d0["passes"]) - 1,
                     "decided_cells": d0["passes"][-1]["cells"] if d0["status"] == "DECIDED" else None,
                     "pass_cpu_runs": [x["pass_cpu_total_s"] for x in ds],
                     "pass_cpu_median": _med([x["pass_cpu_total_s"] for x in ds]),
                     "per_pass_cpu_median": [_med([x["passes"][i]["cpu_s"] for x in ds])
                                             for i in range(len(d0["passes"]))],
                     "load_cpu_median": _med([x["load_cpu_s"] for x in ds]),
                     "prepare_cpu_median": _med([x["prepare_cpu_s"] for x in ds]),
                     "record_cpu_median": _med([x["record_cpu_s"] for x in ds]),
                     "child_cpu_median": _med([x["child_cpu_s"] for x in ds]),
                     "parent_wall_median": _med([x["parent_process_wall_s"] for x in ds])}
                row["combos"][f"{ev}+{pol}"] = c
                names = [f"eval__{scen}__T{T}__{ev}__{pol}__r{r}" for r in range(reps)]
                totals_v.setdefault(key, {})[f"{ev}+{pol}"] = {
                    "verify_cpu_median": _med([vcost.get(n) for n in names]),
                    "total_cpu_incl_verification_median": _med([x["child_cpu_s"] + vcost.get(n, 0)
                                                                for x, n in zip(ds, names)])}
            base = row["combos"].get("original+P0", {})
            for c in row["combos"].values():
                c["pass_cpu_vs_original_P0"] = c["pass_cpu_median"] / base["pass_cpu_median"] if base else None
                c["child_cpu_vs_original_P0"] = c["child_cpu_median"] / base["child_cpu_median"] if base else None
            same = []
            ps = sorted({p for (e, s, t, p) in passes if (s, t) == (scen, T)})
            for p in ps:
                o, a = passes.get(("original", scen, T, p)), passes.get(("algebra", scen, T, p))
                if not o or not a:
                    continue
                ho, ha = o[0][1], a[0][1]
                if ho["completed_steps"] != T or ha["completed_steps"] != T:
                    continue
                co, ca = _med([h["cpu_s"] for _, h in o]), _med([h["cpu_s"] for _, h in a])
                same.append({"p": p, "original": ho["outcome"], "algebra": ha["outcome"], "original_cpu": co,
                             "algebra_cpu": ca, "speed_factor": co / ca,
                             "log2_width_original_over_algebra": math.log2(_width(ho) / _width(ha))})
            row["same_p"] = same
            S = _med([x["speed_factor"] for x in same])
            row["same_p_speed_factor_median"] = S
            eff = {}
            for pol in ("P0", "P2", "P3"):
                o, a = row["combos"].get(f"original+{pol}"), row["combos"].get(f"algebra+{pol}")
                if o and a and S:
                    R = o["pass_cpu_median"] / a["pass_cpu_median"]
                    eff[pol] = {"cost_factor": R, "same_p_speed_factor": S, "path_factor_derived": R / S,
                                "original_tried": o["tried_p"], "algebra_tried": a["tried_p"],
                                "original_final": o["final_p"], "algebra_final": a["final_p"]}
            row["effect_split"] = eff
            amin = row["minimum"]["algebra"]
            tr = {}
            for pol in ("P1", "P2", "P3"):
                c = row["combos"].get(f"algebra+{pol}")
                if not c or amin.get("lowest_success") is None:
                    continue
                first = c["tried_p"][0]
                low, mx = amin["lowest_success"], amin.get("max_nonsuccess_below")
                exact = amin.get("claim") == "MIN_SUCCESS_IN_DECLARED_DOMAIN"
                tr[pol] = {"first_p": first, "first_try_success": c["outcomes"][0] == "DECIDED",
                           "final_p": c["final_p"], "passes": len(c["tried_p"]), "status": c["status"],
                           "first_p_minus_lowest_success": first - low,
                           "minimum_known_exactly": exact,
                           "minimum_bracket": [mx, low] if not exact else [low, low]}
            row["algebra_policy_transfer"] = tr
            tables[key] = row
    vcost_total = time.process_time() - tv0
    return {"checker": "PRECISION_PILOT_A2T independent checker", "incomplete": incomplete,
            "invalid_evidence": invalid, "conflicts": conflicts, "EVIDENCE": "OK" if evidence_ok else "NOT_OK",
            "a1_shared_original_passes": a1_shared, "enclosure_pairs_checked": n_pairs,
            "tables": tables if evidence_ok else None, "tables_unverified": None if evidence_ok else tables,
            "verification_cost": {"total_cpu_s": vcost_total, "agreement_checks_cpu_s": agreement_cpu,
                                  "per_run_cpu_s": vcost, "per_combo": totals_v}}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    v = check(a.run_dir)
    Path(a.out).write_text(json.dumps(v, indent=1), encoding="utf-8")
    print(v["EVIDENCE"], "incomplete", len(v["incomplete"]), "invalid", len(v["invalid_evidence"]),
          "conflicts", len(v["conflicts"]), "verify_cpu", round(v["verification_cost"]["total_cpu_s"], 1))


if __name__ == "__main__":
    main()
