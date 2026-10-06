"""Independent checker for REWRITE_PILOT_A3. Imports none of: rules, rwforce, symbolic, adapter, runner, campaign of
this package; no executor module of A1/A2T; no probe/harness. Reuses only the A1 CHECKER's rule implementation.

Screening: every candidate's verify record present; S3a re-derived here from the STORED plan and the stored algebra
PROGRAM with this file's own canonicalisation; S4 containment, S5 intersection, S6 cells re-checked from stored exact
endpoints; rw:R0 control equals algebra bit for bit; screening/width runs complete; selection re-derived.
Serve: completeness (runs and rewrite INVESTIGATE), per-pass consistency, every policy choice re-derived, determinism,
enclosure intersection across all evaluators (A1 and A2T bundles included), decided-cell agreement. Tables only when
evidence is OK. Verification CPU reported separately.

    python -m experiments.rewrite_pilot_a3.checker RUN_DIR --out FILE
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import itertools
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
BUNDLES = {"A1": (ROOT / "docs/active/precision_pilot_a1/results.json.gz",
                  "af5c13e6f61b52211c244a282fbd70ac4fb70cbede63d7c9b643d7ec477e357a")}
A2T_BUNDLE = ROOT / "docs/active/precision_pilot_a2t/results.json.gz"
A2T_SHA = "6b67243d9d7c55a56d7f77df7a8ce61d55fce2ee6540d9f4559bb31ffe697c5b"
POLICY_HASH = "6d601462f31f5505a2656fe8e2b853fcce617174de279766947dbadda816348e"
PARAMS = ROOT / "experiments/precision_pilot_a2t/frozen_policy_params_a1.json"
SCEN = ("A2_bound", "A3_low", "A3_high")
SHORT_T, LONG_T = (100, 1000), (3000, 5000, 10000)
N_ATOMS = {"A2_bound": 2, "A3_low": 3, "A3_high": 3}
RULE_IDS = ("R1", "R2", "R3", "R4", "R5")
S4_P = (64, 96, 128, 192, 512)
MODULE_TAILS = {"exact_expression_gate_v1.stream": "exact_expression_gate_v1/stream.py",
                "exact_expression_gate_v1.common": "exact_expression_gate_v1/common.py",
                "exact_expression_gate_v0.lang_iv": "exact_expression_gate_v0/lang_iv.py",
                "a_reference.ar2_lang2024": "a_reference/ar2_lang2024.py"}


class CheckError(Exception):
    pass


def lf(p):
    return hashlib.sha256(Path(p).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def my_candidates():
    out = []
    for n in range(5):
        for s in itertools.combinations(RULE_IDS, n):
            if "R3" in s and "R1" not in s:
                continue
            out.append("rw:" + ("+".join(s) if s else "R0"))
    return out


def safe(ev):
    return ev.replace(":", "-").replace("+", "_")


def _norm(p):
    return str(p).replace("\\", "/")


def _repo_module(path, tail):
    p = _norm(path)
    return p == _norm(ROOT / tail) and "/upstream/" not in p and "/vendor/" not in p


def _med(xs):
    xs = [x for x in xs if x is not None]
    return statistics.median(xs) if xs else None


# --- own canonicalisation (independent of symbolic.py) ---------------------------------------------------------------

def _d(D):
    return {int(k): F(v) for k, v in D.items() if F(v) != 0}


def my_canon_program(prog):
    terms = {}
    for a, P in prog["groups"]:
        for d, v in _d(P).items():
            terms[(F(a), d - 1)] = -v
    for d, v in _d(prog["tail"]).items():
        terms[(F(0), d - 1)] = -v
    return terms, (_d(prog["num"]), _d(prog["den"]), _d(prog["dn"]), int(prog["k"]), -F(prog["c"]), 1)


def my_canon_plan(plan):
    ff = plan["final_fold"]
    sh, sg = (0, 1) if ff else (-1, -1)
    terms = {}
    alphas = [F(a) for a in plan["alphas"]]

    def put(a, d, v):
        v = F(v)
        if v != 0:
            key = (a, int(d) + sh)
            if key in terms:
                raise CheckError(f"duplicate term {key}")
            terms[key] = sg * v
    if plan["collect"]:
        for d, v in plan["collected"].items():
            put(F(0), d, v["tail"])
            for i, cv in v["exp"]:
                put(alphas[int(i)], d, cv)
    else:
        for a, P in zip(alphas, plan["blocks"]):
            for d, v in P.items():
                put(a, d, v)
        for d, v in plan["tail"].items():
            put(F(0), d, v)
    s_tot = int(plan["rat_shift"]) + (0 if ff else 1)
    c_tot = F(plan["c"]) * int(plan["rat_sign"]) * (1 if ff else -1)
    return terms, (_d(plan["num"]), _d(plan["den"]), _d(plan["dn"]), int(plan["k"]), c_tot, s_tot)


def my_dn_ok(num, den, dn):
    out = {}
    for i, a in num.items():
        for j, b in den.items():
            if i:
                out[i - 1 + j] = out.get(i - 1 + j, F(0)) + i * a * b
            if j:
                out[i + j - 1] = out.get(i + j - 1, F(0)) - j * a * b
    return {k: v for k, v in out.items() if v != 0} == dn


def _ends(h):
    return [(F(a), F(b)) for a, b in h["endpoints_scaled"]]


def _meet(x, y):
    return all(a0 <= b1 and b0 <= a1 for (a0, a1), (b0, b1) in zip(x, y))


def check(run_dir):
    d = Path(run_dir)
    tv0 = time.process_time()
    seal = json.loads((d / "execution_seal.json").read_text(encoding="utf-8"))
    bad = [s for s, h in seal["source_sha256_lf"].items() if lf(ROOT / s) != h]
    if bad:
        raise CheckError(f"sources changed: {bad}")
    incomplete, invalid, conflicts, refused = [], [], [], []
    if seal.get("sealed_sources_dirty"):
        incomplete.append("campaign started with uncommitted sealed sources")
    vcost = {}
    sums = json.loads((UP / "SHA256SUMS.json").read_text(encoding="utf-8"))
    for k in [k for k in sums if (UP / k).exists()]:
        if hashlib.sha256((UP / k).read_bytes()).hexdigest() != sums[k]:
            invalid.append(f"upstream file differs: {k}")
    prm = json.loads(PARAMS.read_text(encoding="utf-8"))
    core = {k: v for k, v in prm.items() if k != "policy_hash"}
    if hashlib.sha256(json.dumps(core, sort_keys=True).encode()).hexdigest() != POLICY_HASH:
        invalid.append("frozen policy params changed")
    up = d / "upstream_pytest.txt"
    if not up.exists():
        incomplete.append("missing: upstream_pytest.txt")
    else:
        t = up.read_text(encoding="utf-8")
        m = re.search(r"(\d+) passed", t)
        if "exit_code=0" not in t or not m or int(m.group(1)) < 27 or re.search(r"\d+ (failed|errors?)\b", t):
            invalid.append("upstream tests did not pass")

    def load(name, modules=True):
        if (d / f"{name}.ERROR.txt").exists():
            incomplete.append(f"run failed: {name}")
        f = d / f"{name}.json"
        if not f.exists():
            incomplete.append(f"missing: {name}")
            return None
        doc = json.loads(f.read_text(encoding="utf-8"))
        if doc.get("status") == "REFUSED_TIMEOUT":
            refused.append(name)
            return doc
        if doc.get("child_exit_code") != 0 or not doc.get("child_pid_confirmed_exited"):
            invalid.append(f"{name}: child exit not confirmed")
        if modules:
            mods = doc.get("modules") or {}
            if set(mods) != set(MODULE_TAILS) or not all(_repo_module(mods[m], t) for m, t in MODULE_TAILS.items()):
                invalid.append(f"{name}: modules are not the repository modules")
        return doc

    # ---------------- screening ----------------
    refs = load("refs")
    screen = {}
    if refs:
        prog_canon = my_canon_program(refs["program"])
        if not my_dn_ok(*prog_canon[1][:3]):
            invalid.append("refs program: dn != num' den - num den'")
        cands = my_candidates()
        passing = []
        for ev in cands:
            t0 = time.process_time()
            v, s = load(f"verify__{safe(ev)}", modules=False), load(f"sympy__{safe(ev)}")
            if v is not None and v["stages"]["S1"]["ok"]:
                mods = v.get("modules") or {}
                if set(mods) != set(MODULE_TAILS) or not all(_repo_module(mods[m], t) for m, t in MODULE_TAILS.items()):
                    invalid.append(f"verify {ev}: modules are not the repository modules")
            row = {"verify_present": v is not None, "sympy": None}
            if s is not None:
                row["sympy"] = "REFUSED_TIMEOUT" if s.get("status") == "REFUSED_TIMEOUT" else s.get("sympy_zero")
                row["sympy_cpu_s"] = s.get("sympy_cpu_s")
            if v is None:
                screen[ev] = row
                continue
            st = v["stages"]
            row["claimed"] = {k: x.get("ok") for k, x in st.items()}
            mine = {}
            if not st["S1"]["ok"]:
                mine["S1"] = False
            else:
                plan = v["plan"]
                if sorted(plan["rules"]) != sorted([] if ev == "rw:R0" else ev[3:].split("+")):
                    invalid.append(f"{ev}: plan rules differ from its id")
                mine["S1"] = plan["ops"] <= 400 and len(plan["rules"]) <= 4
                row["ops"] = plan["ops"]
                mine["S2"] = all(x == "REFUSED" for k, x in st["S2"].items() if k != "ok") and \
                    (("den_crossing_0" in st["S2"]) == plan["recip"])
                pc = my_canon_plan(plan)
                mine["S3a"] = pc == prog_canon and my_dn_ok(*pc[1][:3])
                bad4 = []
                for p in S4_P:
                    for i, e in enumerate(st["S4"]["point_enclosures"][str(p)]):
                        lo, hi = F(e[0]), F(e[1])
                        r0, r1 = (F(x) for x in refs["point_refs"][i])
                        if not (lo <= r0 and r1 <= hi):
                            bad4.append(f"p{p} R{i}")
                    for j, e in enumerate(st["S4"]["interval_enclosures"][str(p)]):
                        lo, hi = F(e[0]), F(e[1])
                        for r in refs["interval_refs"][j]:
                            if not (lo <= F(r[0]) and F(r[1]) <= hi):
                                bad4.append(f"p{p} I{j}")
                    if len(st["S4"]["point_enclosures"][str(p)]) != len(refs["radii"]) or \
                            len(st["S4"]["interval_enclosures"][str(p)]) != len(refs["inputs"]):
                        bad4.append(f"p{p} incomplete")
                mine["S4"] = not bad4
                bad5, bad6 = [], []
                for key, h in st["S5"]["passes"].items():
                    scen, p = key.split("|")
                    if h["effective_p"] != int(p) or h["force_swap_restored"] is not True:
                        bad5.append(key)
                    if h["endpoints_scaled"] and A1C.my_cells(h["endpoints_scaled"]) != h["cells"]:
                        bad5.append(f"{key} cells")
                    for rev in ("original", "algebra"):
                        r = refs["short_passes"][f"{rev}|{key}"]
                        if bool(h["endpoints_scaled"]) != bool(r["endpoints_scaled"]):
                            bad5.append(f"{key} {rev} completion")
                        elif h["endpoints_scaled"] and not _meet(_ends(h), _ends(r)):
                            bad5.append(f"{key} {rev}")
                        if h["outcome"] == r["outcome"] == "DECIDED" and h["cells"] != r["cells"]:
                            bad6.append(f"{key} {rev}")
                    if ev == "rw:R0" and (h["outcome"], h["endpoints_scaled"]) != (
                            refs["short_passes"][f"algebra|{key}"]["outcome"],
                            refs["short_passes"][f"algebra|{key}"]["endpoints_scaled"]):
                        bad5.append(f"{key} R0 control not bit-identical to algebra")
                if len(st["S5"]["passes"]) != 6:
                    bad5.append("S5 incomplete")
                mine["S5"], mine["S6"] = not bad5, not bad6
                row["S4_failures"], row["S5_failures"] = bad4[:5], bad5[:5]
            row["rechecked"] = mine
            for k, x in mine.items():
                if x != row["claimed"].get(k):
                    invalid.append(f"{ev}: {k} claimed {row['claimed'].get(k)} but re-check gives {x}")
            row["pass_S1_S6"] = all(mine.get(k) for k in ("S1", "S2", "S3a", "S4", "S5", "S6")) and row["sympy"] is True
            if row["pass_S1_S6"]:
                passing.append(ev)
            screen[ev] = row
            vcost[ev] = time.process_time() - t0
        # screening costs and widths
        scr = {}
        for ev in ["algebra"] + passing:
            for s in SCEN:
                for rep in range(3):
                    doc = load(f"scr__{safe(ev)}__{s}__r{rep}")
                    if doc:
                        scr[(ev, s, rep)] = doc
                doc = load(f"wid__{safe(ev)}__{s}")
                if doc:
                    scr[(ev, s, "w")] = doc
        for s in SCEN:
            doc = load(f"scr__original__{s}__r0")
            if doc:
                scr[("original", s, 0)] = doc
        for (ev, s, rep), doc in scr.items():
            T, p = (3000, 192) if rep == "w" else (1000, 128)
            if (doc["evaluator"], doc["scenario"], doc["T"], doc["requested_p"], doc["effective_p"]) != (ev, s, T, p, p):
                invalid.append(f"screen {ev} {s} {rep}: metadata")
            if doc.get("endpoints_scaled") and A1C.my_cells(doc["endpoints_scaled"]) != doc["cells"]:
                invalid.append(f"screen {ev} {s} {rep}: cells")
        sel_mine = None
        needed = [(e, s, r) for e in ["algebra"] + passing for s in SCEN for r in (0, 1, 2, "w")]
        if passing and all(k in scr for k in needed):
            elig = [e for e in passing if e != "rw:R0"]
            cost = {e: statistics.median(sum(scr[(e, s, r)]["cpu_s"] for s in SCEN) for r in range(3))
                    for e in elig + ["algebra"]}

            def wd(e, s):
                h = scr[(e, s, "w")]
                return max(b - a for a, b in _ends(h)) if h.get("endpoints_scaled") else None
            width = {}
            for e in elig:
                vals = [math.log2(wd("algebra", s) / wd(e, s)) if wd(e, s) else -math.inf for s in SCEN]
                width[e] = statistics.median(vals)
            fast = min(elig, key=lambda e: (cost[e], e))
            narrow = max(elig, key=lambda e: (width[e], e))
            sel_mine = {"FAST": fast, "NARROW": narrow if narrow != fast and width[narrow] > 0.5 else None}
            selj = json.loads((d / "selection.json").read_text(encoding="utf-8"))
            if (selj["FAST"], selj["NARROW"]) != (sel_mine["FAST"], sel_mine["NARROW"]):
                invalid.append(f"selection {selj['FAST']}/{selj['NARROW']} != re-derived {sel_mine}")
            for e in elig:
                screen[e]["screen_cost_median_sum_s"] = cost[e]
                screen[e]["screen_cost_vs_algebra"] = cost[e] / cost["algebra"]
                screen[e]["width_gain_log2_median"] = width[e]
                screen[e]["width_gain_log2_per_scenario"] = [
                    math.log2(wd("algebra", s) / wd(e, s)) if wd(e, s) else None for s in SCEN]
            screen["algebra"] = {"screen_cost_median_sum_s": cost["algebra"]}
            if all(("original", s, 0) in scr for s in SCEN):
                screen["original"] = {"screen_cost_rep0_sum_s": sum(scr[("original", s, 0)]["cpu_s"] for s in SCEN)}
        search_cpu = sum(json.loads(f.read_text(encoding="utf-8")).get("child_cpu_s", 0) for f in d.glob("*.json")
                         if f.name.startswith(("refs", "verify__", "sympy__", "scr__", "wid__")))
    else:
        passing, sel_mine, search_cpu = [], None, None

    # ---------------- serve ----------------
    rws = [x for x in ((sel_mine or {}).get("FAST"), (sel_mine or {}).get("NARROW")) if x]
    evs = ["original", "algebra"] + rws
    short = [(ev, pol) for ev in evs for pol in ("P0", "P2", "P3")]
    long = [("original", "P3")] + [(ev, pol) for ev in evs[1:] for pol in ("P0", "P2", "P3")]
    plan_runs = [(s, T, ev, pol, r) for s in SCEN for T in SHORT_T for ev, pol in short for r in range(3)] + \
                [(s, T, ev, pol, 0) for s in SCEN for T in LONG_T for ev, pol in long]
    passes, serve = {}, {}

    def take(name, ev, scen, T, plist):
        for h in plist:
            if (h["evaluator"], h["scenario"], h["T"]) != (ev, scen, T):
                invalid.append(f"{name}: pass metadata")
            if h.get("effective_p") != h["requested_p"]:
                invalid.append(f"{name}: effective p")
            if ev != "original" and h.get("force_swap_restored") is not True:
                invalid.append(f"{name}: force swap not restored")
            if h["outcome"] in ("DECIDED", "UNDECIDED_AT_PRECISION"):
                if h["completed_steps"] != T or len(h.get("endpoints_scaled") or []) != 6 * N_ATOMS[scen]:
                    invalid.append(f"{name}: completion/endpoints")
                    continue
                mine = A1C.my_cells(h["endpoints_scaled"])
                if (mine is None) != (h["outcome"] == "UNDECIDED_AT_PRECISION") or mine != h["cells"]:
                    invalid.append(f"{name}: cells not reproduced")
            elif h["outcome"] == "DOMAIN_UNPROVEN":
                if not 0 <= h["completed_steps"] < T:
                    invalid.append(f"{name}: domain stop steps")
            else:
                invalid.append(f"{name}: unexpected outcome {h['outcome']}")
            passes.setdefault((ev, scen, T, h["requested_p"]), []).append((name, h))

    if sel_mine:
        for scen, T, ev, pol, rep in plan_runs:
            name = f"eval__{scen}__T{T}__{safe(ev)}__{pol}__r{rep}"
            t0 = time.process_time()
            doc = load(name)
            if not doc:
                continue
            if (doc["evaluator"], doc["scenario"], doc["T"], doc["policy"]) != (ev, scen, T, pol) or \
                    doc.get("policy_hash") != POLICY_HASH:
                invalid.append(f"{name}: metadata")
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
        for ev in rws:
            for scen in SCEN:
                for T in SHORT_T:
                    runs = [serve[(scen, T, ev, pol, r)] for pol in ("P0", "P2", "P3") for r in range(3)
                            if (scen, T, ev, pol, r) in serve]
                    tried = {h["requested_p"] for x in runs for h in x["passes"]}
                    low = min((h["requested_p"] for x in runs for h in x["passes"] if h["outcome"] == "DECIDED"),
                              default=None)
                    for p in range(64, low or 64):
                        if p not in tried and not (d / f"inv__{scen}__T{T}__{safe(ev)}__p{p}.json").exists():
                            incomplete.append(f"missing investigate pass: {ev} {scen}@{T} p{p}")
                    for f in sorted(d.glob(f"inv__{scen}__T{T}__{safe(ev)}__p*.json")):
                        doc = load(f.stem)
                        if doc:
                            take(f.stem, ev, scen, T, [doc])
                            inv.setdefault((ev, scen, T), []).append(doc)
    else:
        inv = {}
    # agreement
    ta = time.process_time()
    for key, lst in passes.items():
        if len({(h["outcome"], json.dumps(h.get("endpoints_scaled"))) for _, h in lst}) > 1:
            conflicts.append(f"{key}: not deterministic")
    ext = {}
    for label, (path, sha) in BUNDLES.items():
        if hashlib.sha256(path.read_bytes()).hexdigest() != sha:
            raise CheckError(f"{label} bundle hash differs")
    a2t_sha = hashlib.sha256(A2T_BUNDLE.read_bytes()).hexdigest()
    if a2t_sha != A2T_SHA:
        raise CheckError("A2T bundle hash differs")
    for label, path in (("A1", BUNDLES["A1"][0]), ("A2T", A2T_BUNDLE)):
        with gzip.open(path, "rb") as f:
            run = json.loads(f.read())["run"]
        for name, text in run.items():
            if not name.startswith(("eval__", "inv__", "train__")):
                continue
            doc = json.loads(text)
            for h in (doc.get("passes") or [doc]):
                ev = h.get("evaluator", "original")
                ext.setdefault((label, ev, h["scenario"], h["T"], h["requested_p"]), h)
    shared = 0
    for (lab, ev, s, T, p), h0 in ext.items():
        lst = passes.get((ev, s, T, p))
        if lst:
            shared += 1
            h = lst[0][1]
            if (h["outcome"], h.get("endpoints_scaled")) != (h0["outcome"], h0.get("endpoints_scaled")):
                conflicts.append(f"{ev} {s}@{T} p{p}: differs from the {lab} pass")
    n_pairs = 0
    for scen in SCEN:
        for T in SHORT_T + LONG_T:
            reached = {}
            for (ev, s, t, p), lst in passes.items():
                h = lst[0][1]
                if (s, t) == (scen, T) and h.get("endpoints_scaled") and h["completed_steps"] == T:
                    reached[f"{ev}:p{p}"] = _ends(h)
            for (lab, ev, s, t, p), h in ext.items():
                if (s, t) == (scen, T) and h.get("endpoints_scaled") and h["completed_steps"] == T:
                    reached.setdefault(f"{ev}:p{p}", _ends(h))
            items = list(reached.items())
            for i in range(len(items)):
                for j in range(i + 1, len(items)):
                    n_pairs += 1
                    if not _meet(items[i][1], items[j][1]):
                        conflicts.append(f"{scen}@{T}: {items[i][0]} and {items[j][0]} do not intersect")
            cells = {json.dumps(lst[0][1]["cells"]) for (ev, s, t, p), lst in passes.items()
                     if (s, t) == (scen, T) and lst[0][1]["outcome"] == "DECIDED"}
            cells |= {json.dumps(h["cells"]) for (lab, ev, s, t, p), h in ext.items()
                      if (s, t) == (scen, T) and h["outcome"] == "DECIDED"}
            if len(cells) > 1:
                conflicts.append(f"{scen}@{T}: decided cells disagree")
    agreement_cpu = time.process_time() - ta
    evidence_ok = not incomplete and not invalid and not conflicts

    # tables
    def states(ev, scen, T):
        st = {p: lst[0][1]["outcome"] for (e, s, t, p), lst in passes.items() if (e, s, t) == (ev, scen, T)}
        for (lab, e, s, t, p), h in ext.items():
            if (e, s, t) == (ev, scen, T):
                st.setdefault(p, h["outcome"])
        return st

    def minimum(st):
        low = min((p for p, o in st.items() if o == "DECIDED"), default=None)
        if low is None:
            return {"lowest_success": None}
        full = all(p in st and st[p] != "DECIDED" for p in range(64, low))
        return {"lowest_success": low, "max_nonsuccess_below": max([p for p, o in st.items() if o != "DECIDED" and p < low],
                                                                   default=None),
                "claim": "MIN_SUCCESS_IN_DECLARED_DOMAIN" if full else "LOWEST_SUCCESS_OBSERVED",
                "fails_above_lowest": sorted(p for p, o in st.items() if o != "DECIDED" and p > low)}

    tables, totals_v = {}, {}
    if sel_mine:
        for scen in SCEN:
            for T in SHORT_T + LONG_T:
                reps = 3 if T in SHORT_T else 1
                key = f"{scen}@{T}"
                row = {"minimum": {ev: minimum(states(ev, scen, T)) for ev in evs}, "combos": {},
                       "investigate": {ev: {"passes": len(inv.get((ev, scen, T), [])),
                                            "child_cpu_s": sum(x["child_cpu_s"] for x in inv.get((ev, scen, T), []))}
                                       for ev in rws}}
                for ev, pol in (short if T in SHORT_T else long):
                    ds = [serve.get((scen, T, ev, pol, r)) for r in range(reps)]
                    ds = [x for x in ds if x]
                    if not ds:
                        continue
                    d0 = ds[0]
                    names = [f"eval__{scen}__T{T}__{safe(ev)}__{pol}__r{r}" for r in range(reps)]
                    row["combos"][f"{ev}+{pol}"] = {
                        "status": sorted({x["status"] for x in ds}), "tried_p": d0["tried_p"],
                        "tried_p_same_all_reps": all(x["tried_p"] == d0["tried_p"] for x in ds),
                        "outcomes": [h["outcome"] for h in d0["passes"]],
                        "completed_steps": [h["completed_steps"] for h in d0["passes"]],
                        "final_p": d0["passes"][-1]["requested_p"] if d0["status"] == "DECIDED" else None,
                        "retries": len(d0["passes"]) - 1,
                        "pass_cpu_median": _med([x["pass_cpu_total_s"] for x in ds]),
                        "prepare_cpu_median": _med([x["prepare_cpu_s"] for x in ds]),
                        "record_wall_median": _med([x["record_wall_s"] for x in ds]),
                        "child_cpu_median": _med([x["child_cpu_s"] for x in ds]),
                        "parent_wall_median": _med([x["parent_process_wall_s"] for x in ds])}
                    totals_v.setdefault(key, {})[f"{ev}+{pol}"] = _med([x["child_cpu_s"] + vcost.get(n, 0)
                                                                        for x, n in zip(ds, names)])
                same = []
                for p in sorted({p for (e, s, t, p) in passes if (s, t) == (scen, T)}):
                    rec = {}
                    for ev in evs:
                        lst = passes.get((ev, scen, T, p))
                        if lst and lst[0][1]["completed_steps"] == T and lst[0][1].get("endpoints_scaled"):
                            rec[ev] = (_med([h["cpu_s"] for _, h in lst]), max(b - a for a, b in _ends(lst[0][1])),
                                       lst[0][1]["outcome"])
                    if "algebra" in rec and len(rec) > 1:
                        same.append({"p": p, **{ev: {"cpu": v[0], "outcome": v[2],
                                                     "log2_width_algebra_over_this": math.log2(rec["algebra"][1] / v[1])}
                                                for ev, v in rec.items()}})
                row["same_p"] = same
                for ev in rws + ["original"]:
                    xs = [x[ev]["cpu"] / x["algebra"]["cpu"] for x in same if ev in x]
                    row[f"same_p_cost_{ev}_over_algebra_median"] = _med(xs)
                tables[key] = row
    return {"checker": "REWRITE_PILOT_A3 independent checker", "incomplete": incomplete, "invalid_evidence": invalid,
            "conflicts": conflicts, "refused_timeouts": refused, "EVIDENCE": "OK" if evidence_ok else "NOT_OK",
            "passing_candidates": passing, "selection_rederived": sel_mine, "screening": screen,
            "search_cpu_s": search_cpu, "external_shared_passes": shared, "a2t_bundle_sha256": a2t_sha,
            "enclosure_pairs_checked": n_pairs,
            "tables": tables if evidence_ok else None, "tables_unverified": None if evidence_ok else tables,
            "verification_cost": {"total_cpu_s": time.process_time() - tv0, "agreement_cpu_s": agreement_cpu,
                                  "per_run_cpu_s": vcost, "totals_incl_verification": totals_v}}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    v = check(a.run_dir)
    Path(a.out).write_text(json.dumps(v, indent=1, default=str), encoding="utf-8")
    print(v["EVIDENCE"], "incomplete", len(v["incomplete"]), "invalid", len(v["invalid_evidence"]),
          "conflicts", len(v["conflicts"]), "refused", len(v["refused_timeouts"]),
          "verify_cpu", round(v["verification_cost"]["total_cpu_s"], 1))


if __name__ == "__main__":
    main()
