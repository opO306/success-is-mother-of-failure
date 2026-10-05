"""Independent checker for STATE_OBJECT_EVENT_PILOT_V0.

Imports none of world_retention, object_port, pair_state, event_lineage, derivative_certificate, campaign,
campaign_b (a test enforces it). It recomputes from the raw run files; stored summaries and PASS flags are not read.

PART A: source/protocol binding, completeness, identity of every run against an own replay of the canonical REF
        executor (own record format and own stream hash), memory and cost classes.
PART B certificate: coverage/gap/overlap/order/domain, recomputation of every cell with radial_derivatives (fresh
        processes), own G' interval code, and an independent necessary V'' check from c1b1_two_atom._model_R.
PART B runs: own 512-bit interval replay of A2_bound (lang_iv is the declared shared TCB); every candidate and
        baseline range must intersect it, decided cells must equal its cells; tag bounds; extension rule re-derived.

    python -m experiments.state_object_event_pilot_v0.checker --part-a DIR --part-b DIR --cert FILE --out FILE
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import statistics
import time
from fractions import Fraction as F
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CHECKPOINTS = (1, 10, 100, 1000, 10000)
CASES_A = ("e0.5_rho-0.005", "e1_b10", "e10_b0", "A2_sym")
REPS = 3
MLO, MHI, SC = 7065, 7679, 1024


class CheckError(Exception):
    pass


def lf(path):
    return hashlib.sha256(Path(path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _binding(seal):
    bad = [s for s, h in seal["source_sha256_lf"].items() if lf(ROOT / s) != h]
    if bad:
        raise CheckError(f"sources changed since the run: {bad}")
    if seal["protocol_sha256_lf"] != lf(HERE / "protocol.json"):
        raise CheckError("protocol changed since the run")


# ------------------------------------------------------------------------------------------- PART A ---------------

def _own_case(case):
    from a_numeric import FixedPoint
    from a_reference import c1b1_two_atom as C
    pos, mom = FixedPoint(96, 48), FixedPoint(96, 80)
    if case == "A2_sym":
        return C.new_run(pos, F(40), (F(-71, 20), 0, 0), (1, -3, 0), (F(71, 20), 0, 0), (-1, 3, 0),
                         momentum_profile=mom, validated_only=True)
    doc = json.loads((ROOT / f"docs/active/c1b1_trusted_test_origins_v1/{case}.json").read_text(encoding="utf-8"))
    raw = [int(x) for x in doc["initial_raw"]]
    run = C.new_run(pos, F(40), tuple(F(v, 1 << 48) for v in raw[0:3]), tuple(F(v, 1 << 80) for v in raw[3:6]),
                    tuple(F(v, 1 << 48) for v in raw[6:9]), tuple(F(v, 1 << 80) for v in raw[9:12]),
                    momentum_profile=mom, validated_only=False)
    a, b = run.atoms
    if list(a.r) + list(a.p) + list(b.r) + list(b.p) != raw:
        raise CheckError(f"{case}: own rebuild differs from initial_raw")
    return run


def _own_record(run, t, status):
    a, b = run.atoms
    j = "None" if run.J_cache is None else ",".join(map(str, run.J_cache))
    s = lambda x: ",".join(map(str, x))  # noqa: E731
    return f"v1|{t}|{a.species}|{s(a.r)}|{s(a.p)}|{b.species}|{s(b.r)}|{s(b.p)}|{j}|{status}"


def own_replay_a(case, max_steps=10000):
    from a_numeric.profiles import VMHalt
    from a_reference import c1b1_two_atom as C
    stops = (C.PhysicsDomainExceeded, C.IntegratorDomainExceeded, C.ExecutorLimitExceeded, C.ContractViolation,
             VMHalt)
    run = _own_case(case)
    h = hashlib.sha256((_own_record(run, 0, "OK") + "\n").encode())
    cps, status = {}, "OK"
    for _ in range(max_steps):
        try:
            C.step(run)
        except stops as e:
            status = type(e).__name__
            break
        rec = _own_record(run, run.t_steps, "OK")
        h.update((rec + "\n").encode())
        if run.t_steps in CHECKPOINTS:
            cps[str(run.t_steps)] = rec
    final = _own_record(run, run.t_steps, status)
    h.update(("END|" + final).encode())
    return {"completed_steps": run.t_steps, "status": status, "final_record": final, "checkpoint_records": cps,
            "stream_sha256": h.hexdigest()}


IDENTITY = ("completed_steps", "status", "final_record", "checkpoint_records", "stream_sha256")


def _ident(doc):
    return {k: doc[k] for k in IDENTITY}


def _cost_class(ratios):
    if all(r < 0.90 for r in ratios):
        return "LOWER"
    if any(r > 1.10 for r in ratios):
        return "WORSE"
    return "TIE"


def check_part_a(d):
    d = Path(d)
    seal = json.loads((d / "execution_seal.json").read_text(encoding="utf-8"))
    _binding(seal)
    incomplete = []
    if seal.get("sealed_sources_dirty"):
        incomplete.append("PART A started with uncommitted sealed sources")
    modes = {c: ["WORLD_ONLY", "OBSERVER_HISTORY", "PORT"] + (["PAIR"] if c == "A2_sym" else []) for c in CASES_A}
    runs = {}
    for c in CASES_A:
        for m in modes[c]:
            for tag in [f"t{i}" for i in range(REPS)] + ["mem"]:
                stem = f"A__{c}__{m}__{tag}"
                if (d / f"{stem}.ERROR.txt").exists():
                    incomplete.append(f"run failed: {stem}")
                f = d / f"{stem}.json"
                if not f.exists():
                    incomplete.append(f"missing: {stem}")
                    continue
                runs[(c, m, tag)] = json.loads(f.read_text(encoding="utf-8"))
    per_case, iso, port_ok, pair = {}, True, True, None
    for c in CASES_A:
        ref = own_replay_a(c)
        got = {k: v for k, v in runs.items() if k[0] == c}
        mism = sorted(f"{m}/{t}" for (_, m, t), v in got.items() if _ident(v) != ref)
        if any(m in ("WORLD_ONLY", "OBSERVER_HISTORY") for m in (x.split("/")[0] for x in mism)):
            iso = False
        if any(x.startswith("PORT/") for x in mism):
            port_ok = False
        for (_, m, t), v in got.items():
            if m == "PORT":
                e = v.get("extra", {})
                if e.get("event_invariant_checks") != 2 * v["completed_steps"] or e.get("events") != v["completed_steps"]:
                    port_ok = False
        if c == "A2_sym":
            pv = [v for (_, m, _), v in got.items() if m == "PAIR"]
            if any(x.split("/")[0] == "PAIR" for x in mism):
                pair = "FAIL"
            elif any(v.get("extra", {}).get("refused_at") is not None or v["status"] == "PairStateRefused" for v in pv):
                pair = "REFUSED"
            elif len(pv) == REPS + 1:
                pair = "LOSSLESS"
        mem = got.get((c, "WORLD_ONLY", "mem"))
        wl = "UNRESOLVED"
        if mem and mem["completed_steps"] >= 1000 and mem.get("live_state_bytes") and mem.get("tracemalloc"):
            lb = list(mem["live_state_bytes"].values())
            cps = sorted(mem["tracemalloc"], key=int)
            growth = mem["tracemalloc"][cps[-1]][0] - mem["tracemalloc"][cps[-2]][0]
            wl = "FLAT" if (max(lb) / min(lb) <= 1.25 and growth <= 65536) else "GROWS"
            wl_detail = {"live_state_bytes": mem["live_state_bytes"], "tracemalloc_current": {k: v[0] for k, v in mem["tracemalloc"].items()},
                         "last_interval_traced_growth": growth}
        else:
            wl_detail = None
        cpu = {m: statistics.median(got[(c, m, f"t{i}")]["cpu_s"] for i in range(REPS) if (c, m, f"t{i}") in got)
               for m in modes[c] if all((c, m, f"t{i}") in got for i in range(REPS))}
        omem = got.get((c, "OBSERVER_HISTORY", "mem"))
        per_case[c] = {"own_replay": ref, "mismatches": mism, "world_live_memory": wl, "world_live_detail": wl_detail,
                       "cpu_median": cpu,
                       "peak_rss": {m: got[(c, m, "t0")]["peak_rss"] for m in modes[c] if (c, m, "t0") in got},
                       "observer_history_bytes": omem.get("history_bytes") if omem else None,
                       "observer_tracemalloc_current": {k: v[0] for k, v in omem["tracemalloc"].items()} if omem else None,
                       "live_state_bytes": {m: got[(c, m, "mem")].get("live_state_bytes") for m in modes[c] if (c, m, "mem") in got}}
    wls = [per_case[c]["world_live_memory"] for c in CASES_A]
    world_live = "GROWS" if "GROWS" in wls else ("UNRESOLVED" if "UNRESOLVED" in wls else "FLAT")
    port_ratios = [per_case[c]["cpu_median"]["PORT"] / per_case[c]["cpu_median"]["WORLD_ONLY"] for c in CASES_A]
    obs_ratios = [per_case[c]["cpu_median"]["OBSERVER_HISTORY"] / per_case[c]["cpu_median"]["WORLD_ONLY"] for c in CASES_A]
    pair_ratio = per_case["A2_sym"]["cpu_median"]["PAIR"] / per_case["A2_sym"]["cpu_median"]["WORLD_ONLY"]
    port_cost = _cost_class(port_ratios)
    port_live_lower = all((per_case[c]["live_state_bytes"]["PORT"] or {}).get("1", 1e18) <
                          (per_case[c]["live_state_bytes"]["WORLD_ONLY"] or {}).get("1", 0) for c in CASES_A)
    port_model = "BIT_IDENTICAL" if port_ok else "FAIL"
    return {"incomplete": incomplete,
            "OBSERVER_ISOLATION": "PASS" if iso and not incomplete else "FAIL",
            "WORLD_LIVE_MEMORY": world_live,
            "PORT_MODEL": port_model,
            "PORT_COST": port_cost,
            "PORT_STRUCTURE_ONLY": port_model == "BIT_IDENTICAL" and port_cost in ("TIE", "WORSE") and not port_live_lower,
            "PAIR_CURRENT_STATE": pair or "FAIL",
            "PAIR_COST": _cost_class([pair_ratio]),
            "ratios": {"PORT/WORLD_ONLY": dict(zip(CASES_A, port_ratios)),
                       "OBSERVER_HISTORY/WORLD_ONLY": dict(zip(CASES_A, obs_ratios)), "PAIR/WORLD_ONLY": pair_ratio},
            "per_case": per_case}


# ------------------------------------------------------------------------------- PART B certificate ----------------

def _imul(x, y):
    p = (x[0] * y[0], x[0] * y[1], x[1] * y[0], x[1] * y[1])
    return min(p), max(p)


def own_gprime(V1, V2, a, b):
    RV2 = _imul((a, b), V2)
    num = (V1[0] - RV2[1], V1[1] - RV2[0])
    den = (2 * a * a * a, 2 * b * b * b)
    q = [num[i] / den[j] for i in (0, 1) for j in (0, 1)]
    return min(q), max(q)


def _recompute(m):
    from a_reference.c1b1_energy_bound import radial_derivatives
    d = radial_derivatives(F(m, SC), F(m + 1, SC))
    return m, (str(d[1].lo), str(d[1].hi)), (str(d[2].lo), str(d[2].hi))


def _model_dV(R, M=128):
    from a_reference import c1b1_two_atom as C
    lo, hi = (R.numerator << M) // R.denominator, -((-(R.numerator << M)) // R.denominator)
    dV = C._model_R((lo, hi), M, True)[1]
    return F(dV[0], 1 << M), F(dV[1], 1 << M)


def check_certificate(path, recompute=None, workers=6):
    with gzip.open(path, "rb") as f:
        body = json.loads(f.read())
    problems = []
    for s, h in body["generator_source_sha256_lf"].items():
        if lf(ROOT / s) != h:
            problems.append(f"generator source changed: {s}")
    if body["protocol_sha256_lf"] != lf(HERE / "protocol.json"):
        problems.append("protocol changed")
    cells = body["cells"]
    ms = [c["m"] for c in cells]
    if ms != list(range(MLO, MHI + 1)):
        problems.append("coverage: cells are not exactly m = 7065..7679 in order (gap, overlap or duplicate)")
    if body["domain_R_bohr"] != [f"{MLO}/{SC}", f"{MHI + 1}/{SC}"] or F(MLO, SC) > F(69, 10) or F(MHI + 1, SC) < F(75, 10):
        problems.append("declared domain does not cover [6.9, 7.5]")
    from a_reference.ar2_lang2024 import R_MIN_BOHR
    if F(MLO, SC) < R_MIN_BOHR:
        problems.append("domain below r_min")
    vals = {}
    for c in cells:
        try:
            V1 = (F(c["V1"][0]), F(c["V1"][1]))
            V2 = (F(c["V2"][0]), F(c["V2"][1]))
            Gp = (F(c["Gp"][0]), F(c["Gp"][1]))
        except (ValueError, ZeroDivisionError):
            problems.append(f"cell {c['m']}: non-finite or malformed value")
            continue
        if not (V1[0] <= V1[1] and V2[0] <= V2[1] and Gp[0] <= Gp[1]):
            problems.append(f"cell {c['m']}: endpoint order")
        a, b = F(c["m"], SC), F(c["m"] + 1, SC)
        g = own_gprime(V1, V2, a, b)
        if not (Gp[0] <= g[0] and g[1] <= Gp[1]):
            problems.append(f"cell {c['m']}: stored G' does not contain the own recomputation from V', V''")
        vals[c["m"]] = (V1, V2)
    todo = sorted(vals) if recompute is None else sorted(m for m in recompute if m in vals)
    t0 = time.perf_counter()
    if workers > 1 and len(todo) > 1:
        import multiprocessing as mp
        with mp.get_context("spawn").Pool(workers) as pool:
            rec = pool.map(_recompute, todo, chunksize=8)
    else:
        rec = [_recompute(m) for m in todo]
    for m, V1s, V2s in rec:
        V1, V2 = vals[m]
        if (str(V1[0]), str(V1[1])) != V1s or (str(V2[0]), str(V2[1])) != V2s:
            problems.append(f"cell {m}: recomputed radial_derivatives differ from stored")
    indep = 0
    for m in todo:
        V1, V2 = vals[m]
        a, b = F(m, SC), F(m + 1, SC)
        da, db = _model_dV(a), _model_dV(b)
        if not (da[0] <= V1[1] and V1[0] <= da[1] and db[0] <= V1[1] and V1[0] <= db[1]):
            problems.append(f"cell {m}: _model_R V' at the cell ends does not meet V'(cell)")
        slope = ((db[0] - da[1]) / (b - a), (db[1] - da[0]) / (b - a))
        if not (slope[0] <= V2[1] and V2[0] <= slope[1]):
            problems.append(f"cell {m}: mean-value slope of V' does not meet V''(cell)")
        indep += 1
    return {"problems": problems, "cells": len(cells), "recomputed": len(rec), "independent_checks": indep,
            "recompute_wall_s": time.perf_counter() - t0,
            "content_sha256": hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()}


# ----------------------------------------------------------------------------------- PART B runs -------------------

def own_reference_b(steps, want, prec=512):
    from mpmath import iv
    import exact_expression_gate_v0.lang_iv as LI
    from mpmath.libmp import finf, fnan, fninf, to_rational
    iv.prec = prec
    mass = F("39.9623831237") / F("5.485799090441e-4")
    q = [[LI.c(F(x)) for x in r] for r in (("-71/20", 0, 0), ("71/20", 0, 0))]
    p = [[LI.c(F(x)) for x in r] for r in ((1, -3, 0), (-1, 3, 0))]
    h, cdt = LI.c(F(20)), LI.c(F(40) / mass)
    rmin2 = F(LI.L.R_MIN_BOHR) ** 2

    def end(t):
        return None if t in (finf, fninf, fnan) else F(*to_rational(t))

    def forces(q):
        d = [q[1][k] - q[0][k] for k in range(3)]
        r2 = d[0] * d[0] + d[1] * d[1] + d[2] * d[2]
        if end(r2._mpi_[0]) < rmin2:
            raise CheckError("reference: domain not proven")
        g = LI.G_of_R2(r2)
        t = [h * g * d[k] for k in range(3)]
        return [[iv.mpf(0) - x for x in t], t]
    out = {}
    Fq = forces(q)
    for s in range(1, steps + 1):
        p = [[p[a][k] + Fq[a][k] for k in range(3)] for a in range(2)]
        q = [[q[a][k] + p[a][k] * cdt for k in range(3)] for a in range(2)]
        Fq = forces(q)
        p = [[p[a][k] + Fq[a][k] for k in range(3)] for a in range(2)]
        if s in want:
            vals = [v for r in q for v in r] + [v for r in p for v in r]
            out[s] = [(end(v._mpi_[0]), end(v._mpi_[1])) for v in vals]
    return out


def _half_even(x):
    q = x.numerator // x.denominator
    rem = x - q
    if rem > F(1, 2) or (rem == F(1, 2) and q % 2):
        q += 1
    return q


def own_cells(ranges):
    out = []
    for i, (lo, hi) in enumerate(ranges):
        fb = 48 if i < 6 else 80
        a, b = _half_even(lo * 2 ** fb), _half_even(hi * 2 ** fb)
        if a != b:
            return None
        out.append(a)
    return out


def check_part_b(d, cert_path):
    d = Path(d)
    seal = json.loads((d / "execution_seal.json").read_text(encoding="utf-8"))
    _binding(seal)
    proto = json.loads((HERE / "protocol.json").read_text(encoding="utf-8"))["part_B"]
    with gzip.open(cert_path, "rb") as f:
        cert_sha = hashlib.sha256(json.dumps(json.loads(f.read()), sort_keys=True).encode()).hexdigest()
    plans = [(96, 100, [10, 100])]
    dec_doc = json.loads((d / "decision.json").read_text(encoding="utf-8"))
    if (d / "execution_seal_stage2.json").exists():
        s2 = json.loads((d / "execution_seal_stage2.json").read_text(encoding="utf-8"))
        bad = [s for s, h in s2["source_sha256_lf"].items() if lf(ROOT / s) != h]
        if bad:
            raise CheckError(f"stage-2 sources changed: {bad}")
        plans += [(96, 1000, [10, 100, 1000]), (128, 1000, [10, 100, 1000])]
    incomplete, sound, tag_ok, rows = [], [], True, {}
    refs = {}
    for prec, last, want in plans:
        if last not in refs:
            refs[last] = own_reference_b(last, set(want))
        ref = refs[last]
        for path in ("baseline", "candidate"):
            docs = []
            for rep in range(REPS):
                stem = f"B__{path}__p{prec}__s{last}__t{rep}"
                if (d / f"{stem}.ERROR.txt").exists():
                    incomplete.append(f"run failed: {stem}")
                f = d / f"{stem}.json"
                if not f.exists():
                    incomplete.append(f"missing: {stem}")
                    continue
                docs.append(json.loads(f.read_text(encoding="utf-8")))
            for doc in docs:
                if path == "candidate" and doc.get("certificate_sha256") != cert_sha:
                    raise CheckError("candidate ran with another certificate")
                if doc.get("stop") is not None:
                    sound.append(("stop", path, prec, last, doc["stop"]))
                for s in want:
                    r = doc["read"].get(str(s))
                    if r is None:
                        incomplete.append(f"{path} p{prec} s{last}: step {s} missing")
                        continue
                    rng = [(F(a), F(b)) for a, b in r["ranges"]]
                    if not all(lo <= rhi and rlo <= hi for (lo, hi), (rlo, rhi) in zip(rng, ref[s])):
                        sound.append(("disjoint_from_reference", path, prec, s))
                    mine = own_cells(rng)
                    if (mine is None) != (r["cells"] is None) or (mine is not None and mine != r["cells"]):
                        sound.append(("cells_not_reproduced", path, prec, s))
                    refc = own_cells(ref[s])
                    if r["cells"] is not None and refc is not None and r["cells"] != refc:
                        sound.append(("cells_differ_from_reference", path, prec, s))
                    if path == "candidate" and (r["tags"] > 3 * (s + 1) or r["tags"] > proto["MAX_TAGS"]):
                        tag_ok = False
            if docs:
                rows[f"{path}_p{prec}_s{last}"] = {
                    "cpu_median": statistics.median(x["cpu_s"] for x in docs),
                    "cpu_runs": [x["cpu_s"] for x in docs], "wall_median": statistics.median(x["wall_s"] for x in docs),
                    "peak_rss_max": max(x["peak_rss"] for x in docs),
                    "read": {s: {k: v for k, v in docs[0]["read"][str(s)].items() if k != "ranges"}
                             for s in want if str(s) in docs[0]["read"]}}
    soundness_pass = not sound and not incomplete
    st1b, st1c = rows.get("baseline_p96_s100"), rows.get("candidate_p96_s100")
    corr, cost, ext = "UNRESOLVED", None, None
    if st1b and st1c:
        rb, rc = st1b["read"][100], st1c["read"][100]
        wb = max(F(rb["norm_radius_pos_exact"]), F(rb["norm_radius_mom_exact"]))
        wc = max(F(rc["norm_radius_pos_exact"]), F(rc["norm_radius_mom_exact"]))
        signal = (rc["cells"] is not None and rb["cells"] is None) or wb >= 2 * wc
        ratio = st1c["cpu_median"] / st1b["cpu_median"]
        cost = "FASTER" if ratio < 0.8 else "TIE" if ratio <= 1.25 else "WORSE" if ratio <= 10 else "COST_WALL"
        if soundness_pass:
            corr = "YES" if signal else "NO"
        ext = ("EVENT_LINEAGE_SOUNDNESS_FAIL" if not soundness_pass else "EVENT_LINEAGE_COST_WALL" if ratio > 10
               else "EVENT_LINEAGE_NO_SIGNAL" if not signal else "EXTEND")
        if ext != dec_doc.get("decision"):
            raise CheckError(f"campaign extension decision {dec_doc.get('decision')} != re-derived {ext}")
        if ext == "EXTEND" and len(plans) == 1:
            incomplete.append("extension required by the rule but stage 2 missing")
        if ext != "EXTEND" and len(plans) > 1:
            raise CheckError("stage 2 ran although the rule did not allow it")
        rows["stage1_summary"] = {"worst_norm_baseline": float(wb), "worst_norm_candidate": float(wc),
                                  "radius_ratio": float(wb / wc) if wc else None, "cpu_ratio": ratio}
    return {"incomplete": incomplete, "soundness_findings": sound,
            "LINEAGE_SOUNDNESS": "PASS" if soundness_pass else ("UNRESOLVED" if incomplete and not sound else "FAIL"),
            "LINEAGE_CORRELATION": corr, "LINEAGE_COST": cost, "TAG_GROWTH": "CONTROLLED" if tag_ok else "WALL",
            "extension_rederived": ext, "rows": rows,
            "reference": "own 512-bit interval replay, lang_iv shared TCB"}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--part-a")
    ap.add_argument("--part-b")
    ap.add_argument("--cert")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    t0, c0 = time.perf_counter(), time.process_time()
    out = {"gate": "STATE_OBJECT_EVENT_PILOT_V0", "note": "PART A and PART B verdicts are separate and never combined."}
    if a.part_a:
        out["part_A"] = check_part_a(a.part_a)
    if a.cert:
        out["certificate"] = check_certificate(a.cert, workers=a.workers)
    if a.part_b:
        out["part_B"] = check_part_b(a.part_b, a.cert)
    out["checker_cost"] = {"wall_s": time.perf_counter() - t0, "cpu_s": time.process_time() - c0}
    Path(a.out).write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    brief = {k: (v if k in ("checker_cost",) else {kk: vv for kk, vv in v.items() if kk.isupper() or kk in ("incomplete", "problems", "soundness_findings")})
             for k, v in out.items() if isinstance(v, dict)}
    print(json.dumps(brief, indent=1, default=str))


if __name__ == "__main__":
    main()
