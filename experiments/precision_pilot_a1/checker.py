"""Independent checker for PRECISION_PILOT_A1. Imports none of policies, runner, campaign, evaluator_adapter.

1. binding (sources, protocol) and completeness of every planned run; record consistency (metadata, effective_p,
   child exit) BEFORE any summary;
2. cells recomputed from stored exact endpoints (own half-even); decided cells of one request must agree across all
   runs and passes; same (request, p) passes must agree in outcome and endpoints (determinism);
3. every next-p choice of P0-P3 re-derived from the recorded outcomes with this file's own implementation of the
   sealed rules, and P1/P3 parameters re-derived from the training runs;
4. ledger claims (MIN_SUCCESS_IN_DECLARED_DOMAIN only if every lower integer in [64, low) is a recorded non-success);
5. cost tables from raw pass CPU (INVESTIGATE never added to SERVE).

    python -m experiments.precision_pilot_a1.checker RUN_DIR --out FILE
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
from fractions import Fraction as F
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
GRID = [64, 96, 128, 192, 256, 384, 512, 768, 1024]
SCEN = ("A2_bound", "A3_low", "A3_high")
TRAIN_T, SHORT_T, LONG_T = (200, 2000), (100, 1000), (3000, 5000, 10000)
POLICIES = ("P0", "P1", "P2", "P3")
N_ATOMS = {"A2_bound": 2, "A3_low": 3, "A3_high": 3}
FINAL = {"DECIDED", "DOMAIN_VIOLATED_PROVEN", "OUT_OF_RANGE", "INVALID_EVIDENCE"}


class CheckError(Exception):
    pass


def lf(p):
    return hashlib.sha256(Path(p).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def he(x):
    q = x.numerator // x.denominator
    r = x - q
    if r > F(1, 2) or (r == F(1, 2) and q % 2):
        q += 1
    return q


def my_cells(ends):
    out = []
    for lo, hi in ends:
        a, b = he(F(lo)), he(F(hi))
        if a != b:
            return None
        out.append(a)
    return out


def my_clog2(x):
    e = 0
    while F(2) ** e < x:
        e += 1
    while F(2) ** (e - 1) >= x:
        e -= 1
    return e


def my_extra(ends):
    best = None
    for lo, hi in ends:
        lo, hi = F(lo), F(hi)
        if he(lo) == he(hi):
            continue
        mid = (lo + hi) / 2
        margin = F(1, 2) - abs(mid - he(mid))
        e = 32 if margin <= 0 else my_clog2((hi - lo) / margin)
        best = e if best is None else max(best, e)
    return 0 if best is None else best


def my_p2(last, T):
    p = last["requested_p"]
    if last["outcome"] == "UNDECIDED_AT_PRECISION" and last.get("endpoints_scaled"):
        n = p + max(my_extra(last["endpoints_scaled"]), 1) + 8
    elif last["outcome"] == "DOMAIN_UNPROVEN":
        k = last["completed_steps"]
        n = 2 * p if k <= 0 else math.ceil(F(p * T, k)) + 8
    else:
        n = 2 * p
    return max(n, p + 1)


def my_next(pol, prm, scen, hist, T):
    if hist and hist[-1]["outcome"] in FINAL:
        return None
    tried = [h["requested_p"] for h in hist]
    if pol == "P0":
        c = [g for g in GRID if not tried or g > max(tried)]
        n = c[0] if c else None
    elif pol == "P1":
        if not hist:
            n = prm["s1"]
        else:
            c = [g for g in GRID if g > max(tried)]
            n = c[0] if c else None
    elif pol == "P2":
        n = 64 if not hist else my_p2(hist[-1], T)
    else:
        if not hist:
            ln = prm["lines"].get(scen)
            n = 64 if ln is None else max(64, math.ceil(F(ln[0]) + F(ln[1]) * T) + 8)
        else:
            n = my_p2(hist[-1], T)
    if n is None:
        return None
    if n > 1024:
        return "CAP" if max(tried, default=0) >= 1024 else 1024
    return n


def my_train(train):
    lows = {}
    for k, hist in train.items():
        s = [h["requested_p"] for h in hist if h["outcome"] == "DECIDED"]
        lows[k] = min(s) if s else None
    vals = sorted(v for v in lows.values() if v is not None)
    n = len(vals)
    s1 = None if not n else (vals[n // 2] if n % 2 else math.ceil(F(vals[n // 2 - 1] + vals[n // 2], 2)))
    lines = {}
    for scen in SCEN:
        pts = sorted((T, lows[(scen, T)]) for T in TRAIN_T if lows.get((scen, T)) is not None)
        if len(pts) >= 2:
            (t1, p1), (t2, p2) = pts[0], pts[-1]
            b = F(p2 - p1, t2 - t1)
            lines[scen] = [str(p1 - b * t1), str(b)]
    return s1, lines


def check(run_dir):
    d = Path(run_dir)
    seal = json.loads((d / "execution_seal.json").read_text(encoding="utf-8"))
    bad = [s for s, h in seal["source_sha256_lf"].items() if lf(ROOT / s) != h]
    if bad:
        raise CheckError(f"sources changed: {bad}")
    incomplete, invalid, conflicts = [], [], []
    if seal.get("sealed_sources_dirty"):
        incomplete.append("campaign started with uncommitted sealed sources")

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
        return doc

    audit = load("audit")
    if audit and not (audit["PASS"] and all(r["effective_p"] == r["p"] for r in audit["rows"])):
        invalid.append("p-support audit not passed")
    passes = {}                                         # (scen, T, p) -> list of (name, pass)

    def take(name, scen, T, p_list):
        for h in p_list:
            if (h["scenario"], h["T"]) != (scen, T):
                invalid.append(f"{name}: pass metadata {h['scenario']}/{h['T']} != {scen}/{T}")
            if h.get("effective_p") != h["requested_p"]:
                invalid.append(f"{name}: effective_p {h.get('effective_p')} != requested {h['requested_p']}")
            if h["outcome"] in ("DECIDED", "UNDECIDED_AT_PRECISION"):
                if h["completed_steps"] != T or not h.get("endpoints_scaled") or \
                        len(h["endpoints_scaled"]) != 6 * N_ATOMS[scen]:
                    invalid.append(f"{name}: p{h['requested_p']} completion/endpoints inconsistent")
                    continue
                mine = my_cells(h["endpoints_scaled"])
                if (mine is None) != (h["outcome"] == "UNDECIDED_AT_PRECISION") or mine != h["cells"]:
                    invalid.append(f"{name}: p{h['requested_p']} cells not reproduced from endpoints")
            elif h["outcome"] == "DOMAIN_UNPROVEN":
                if not 0 <= h["completed_steps"] < T:
                    invalid.append(f"{name}: domain stop with completed_steps {h['completed_steps']}")
            passes.setdefault((scen, T, h["requested_p"]), []).append((name, h))

    train = {}
    for scen in SCEN:
        for T in TRAIN_T:
            doc = load(f"train__{scen}__T{T}__P2")
            if doc:
                take(f"train__{scen}__T{T}", scen, T, doc["passes"])
                train[(scen, T)] = doc["passes"]
    prm = json.loads((d / "policy_params.json").read_text(encoding="utf-8"))
    s1, lines = my_train(train)
    if (s1, lines) != (prm["s1"], prm["lines"]):
        invalid.append(f"frozen params {prm['s1']}/{prm['lines']} != re-derived {s1}/{lines}")
    serve = {}
    plan = [(s, T, pol, r) for s in SCEN for T in SHORT_T for pol in POLICIES for r in range(3)] + \
           [(s, T, pol, 0) for s in SCEN for T in LONG_T for pol in POLICIES]
    for scen, T, pol, rep in plan:
        name = f"eval__{scen}__T{T}__{pol}__r{rep}"
        doc = load(name)
        if not doc:
            continue
        if (doc["scenario"], doc["T"], doc["policy"]) != (scen, T, pol):
            invalid.append(f"{name}: metadata differs")
        hist = doc["passes"]
        take(name, scen, T, hist)
        for i in range(len(hist) + 1):                   # every choice re-derived
            n = my_next(pol, prm, scen, hist[:i], T)
            if i < len(hist):
                if n != hist[i]["requested_p"]:
                    invalid.append(f"{name}: pass {i} p{hist[i]['requested_p']} but the rule gives {n}")
                    break
            else:
                end = hist[-1]["outcome"] if n is None else ("RESOURCE_REFUSED" if n == "CAP" or len(hist) >= 24 or
                                                             sum(h["cpu_s"] for h in hist) >= 5400 else "UNFINISHED")
                if end != doc["status"]:
                    invalid.append(f"{name}: status {doc['status']} but the rule ends with {end}")
        serve[(scen, T, pol, rep)] = doc
    inv = {}
    for scen in SCEN:
        for T in SHORT_T:
            for f in sorted(d.glob(f"inv__{scen}__T{T}__p*.json")):
                doc = load(f.stem)
                if doc:
                    take(f.stem, scen, T, [doc])
                    inv.setdefault((scen, T), []).append(doc)
    # determinism and agreement
    for key, lst in passes.items():
        outs = {(h["outcome"], json.dumps(h.get("endpoints_scaled"))) for _, h in lst}
        if len(outs) > 1:
            conflicts.append(f"{key}: same (request, p) gave different outcomes/endpoints")
    for scen in SCEN:
        for T in TRAIN_T + SHORT_T + LONG_T:
            cells = {json.dumps(h["cells"]) for (s, t, p), lst in passes.items() if (s, t) == (scen, T)
                     for _, h in lst if h["outcome"] == "DECIDED"}
            if len(cells) > 1:
                conflicts.append(f"{scen}@{T}: decided cells disagree")
    # ledgers and tables
    tables = {}
    for scen in SCEN:
        for T in SHORT_T + LONG_T:
            reps = 3 if T in SHORT_T else 1
            states = {}
            for (s, t, p), lst in passes.items():
                if (s, t) == (scen, T):
                    states[p] = lst[0][1]["outcome"]
            low = min((p for p, o in states.items() if o == "DECIDED"), default=None)
            claim = None
            if low is not None:
                claim = "MIN_SUCCESS_IN_DECLARED_DOMAIN" if all(
                    p in states and states[p] != "DECIDED" for p in range(64, low)) else "LOWEST_SUCCESS_OBSERVED"
            row = {"lowest_success": low, "claim": claim,
                   "untried_below": None if low is None else sum(1 for p in range(64, low) if p not in states),
                   "investigate_passes": len(inv.get((scen, T), [])),
                   "investigate_cpu_s": sum(x["cpu_s"] for x in inv.get((scen, T), [])), "policies": {}}
            for pol in POLICIES:
                ds = [serve.get((scen, T, pol, r)) for r in range(reps)]
                ds = [x for x in ds if x]
                if not ds:
                    continue
                cpus = [sum(h["cpu_s"] for h in x["passes"]) for x in ds]
                row["policies"][pol] = {"status": sorted({x["status"] for x in ds}),
                                        "tried_p": [x["tried_p"] for x in ds][0],
                                        "passes": len(ds[0]["passes"]),
                                        "decided_p": ds[0]["passes"][-1]["requested_p"] if ds[0]["status"] == "DECIDED" else None,
                                        "cpu_runs": cpus, "cpu_median": statistics.median(cpus),
                                        "process_wall_median": statistics.median(x.get("parent_process_wall_s", 0) for x in ds)}
            base = row["policies"].get("P0", {}).get("cpu_median")
            for pol, r in row["policies"].items():
                r["cpu_vs_P0"] = (r["cpu_median"] / base) if base else None
            tables[f"{scen}@{T}"] = row
    evidence_ok = not incomplete and not invalid and not conflicts
    return {"checker": "PRECISION_PILOT_A1 independent checker", "incomplete": incomplete, "invalid_evidence": invalid,
            "conflicts": conflicts, "EVIDENCE": "OK" if evidence_ok else "NOT_OK",
            "frozen_params_rederived": {"s1": s1, "lines": lines}, "tables": tables if evidence_ok else None,
            "tables_unverified": None if evidence_ok else tables}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    v = check(a.run_dir)
    Path(a.out).write_text(json.dumps(v, indent=1), encoding="utf-8")
    print(v["EVIDENCE"], "incomplete", len(v["incomplete"]), "invalid", len(v["invalid_evidence"]),
          "conflicts", len(v["conflicts"]))


if __name__ == "__main__":
    main()
