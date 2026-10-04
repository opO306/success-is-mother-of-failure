"""Independent verdict checker for Gate V2 (standard library only; does not
import the producer). Recomputes all verdicts from raw results + sealed protocol.

    python -m nuclear_gate_v2.checker RESULTS.json [--out VERDICTS.json]
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
V1_EVIDENCE = HERE.parent / "docs" / "active" / "nuclear_gate_v1" / "results.json.gz"
EDGE = 1e-6
PROBS = ("P_exc", "electron_right", "transmission", "coherence_indicator")


class CheckError(Exception):
    pass


def fin(run):
    s = run["samples"][-1]
    out = {k: s.get(k) for k in PROBS}
    r0, rx = s.get("R_mean_0"), s.get("R_mean_exc")
    out["branch_separation"] = None if r0 is None or rx is None else rx - r0
    return out


def drift(run, key):
    v0 = run["samples"][0][key]
    return max(abs(s[key] - v0) for s in run["samples"])


def edge(run):
    return max(max(s.get("electron_edge") or 0.0, s.get("nuclear_edge") or 0.0) for s in run["samples"])


def same(a, b, obs):
    if a is None or b is None:
        return a is None and b is None
    if obs == "branch_separation":
        return abs(a - b) <= 0.01 * abs(b)
    return abs(a - b) <= 1e-3


def band(m, q, obs):
    if obs == "branch_separation":
        return abs(m - q) <= 0.2 * abs(q)
    if obs == "coherence_indicator":
        return abs(m - q) <= max(0.02, 0.2 * abs(q))
    return abs(m - q) <= max(0.02, 0.1 * abs(q))


def q_validity(runs):
    q = fin(runs["Q"])
    problems = []
    if max(abs(s["norm"] - 1) for s in runs["Q"]["samples"]) > 1e-8:
        problems.append("norm")
    if drift(runs["Q"], "energy") > 1e-4:
        problems.append("energy")
    applicable_branch = (q["P_exc"] or 0) >= 0.05 and q["branch_separation"] is not None
    for alt in ("Q_dt_fine", "Q_grid_fine"):
        a = fin(runs[alt])
        for obs in PROBS + ("branch_separation",):
            if obs == "branch_separation" and not applicable_branch:
                continue
            if q.get(obs) is None and a.get(obs) is None:
                continue
            if not same(q.get(obs), a.get(obs), obs):
                problems.append(f"{alt}:{obs} {q.get(obs)} vs {a.get(obs)}")
    unsupported = any(edge(runs[k]) > EDGE for k in ("Q", "Q_dt_fine", "Q_grid_fine"))
    return q, problems, unsupported, applicable_branch


def method_verdicts(runs, m, q, observables, ref_ok, machinery_ok):
    run, conv = runs[m], runs.get(f"{m}_quad_conv")
    mf = fin(run) if "domain_stop" not in run else {}
    cf = fin(conv) if conv and "domain_stop" not in conv else {}
    v = {}
    for obs in observables:
        if not ref_ok:
            v[obs] = "REFUSED"
        elif not machinery_ok:
            v[obs] = "REFUSED"
        elif "domain_stop" in run or edge(run) > EDGE:
            v[obs] = "UNSUPPORTED"
        elif not same(mf.get(obs), cf.get(obs), obs):
            v[obs] = "REFUSED"
        elif mf.get(obs) is None:
            v[obs] = "DISTORTED"
        else:
            v[obs] = "REPRESENTED" if band(mf[obs], q[obs], obs) else "DISTORTED"
    return {"verdict": v, "final": mf, "quad_conv_final": cf}


def ledger(runs):
    out = {}
    for k, r in runs.items():
        if "samples" not in r:
            out[k] = {"cost": r["cost"], "state_values": r["state_values"]}
            continue
        led = {"energy_drift": drift(r, "energy"), "max_edge": edge(r), "cost": r["cost"],
               "state_values": r["state_values"]}
        if "max_traj_energy_dev" in r["samples"][-1]:
            led["max_traj_energy_dev"] = max(s["max_traj_energy_dev"] for s in r["samples"])
        if "direct_Q_pair_fallbacks" in r:
            led["direct_Q_pair_fallbacks"] = r["direct_Q_pair_fallbacks"]
        out[k] = led
    return out


def v1_eh_reference():
    if not V1_EVIDENCE.exists():
        return None
    v1 = json.loads(gzip.decompress(V1_EVIDENCE.read_bytes()))
    ref = {}
    for c in v1["cells"]:
        s = c["scenarios"]["S1_slide"]["runs"]["EH"]["samples"][-1]
        ref[c["Rf"]] = (s["P_exc"], s["electron_right"])
    return ref


def recheck_s2r_rule(cell, M):
    R, E = cell["surface"]["R"], cell["surface"]["E"]
    V0 = [e[0] for e in E]
    left = [i for i, r in enumerate(R) if -8.0 <= r < 0.0]
    ia = min(left, key=lambda i: V0[i])
    span = [i for i, r in enumerate(R) if R[ia] <= r <= -R[ia]]
    ib = max(span, key=lambda i: V0[i])
    B = V0[ib] - V0[ia]
    target = V0[ia] + 0.8 * B
    j = ia
    while j > 0 and V0[j] < target:
        j -= 1
    Rc = R[j] + (target - V0[j]) * (R[j + 1] - R[j]) / (V0[j + 1] - V0[j])
    rule = cell["rule"]
    sigma = (2.0 / (M * abs(rule["slope_at_R_c"]))) ** (1.0 / 3.0)
    ok = (abs(R[ia] - rule["R_a"]) < 1e-12 and abs(R[ib] - rule["R_b"]) < 1e-12 and abs(B - rule["barrier"]) < 1e-12
          and abs(Rc - rule["R_c"]) < 1e-9 and abs(sigma - rule["sigma"]) < 1e-12
          and abs(cell["R0"] - Rc) < 1e-9 and abs(cell["sigma"] - sigma) < 1e-12)
    if not ok:
        raise CheckError("S2r initial condition does not follow the sealed rule")


def check(results, protocol=None):
    quick = results["seal"]["quick"]
    if protocol is not None and not quick:
        if json.dumps(protocol, sort_keys=True) != json.dumps(results["protocol"], sort_keys=True):
            raise CheckError("results were not produced under the sealed protocol")
    M = results["protocol"]["model"]["M"]
    v1ref = None if quick else v1_eh_reference()
    out = {"quick": quick, "S1": [], "S2r": None, "S3": None}

    # ---- machinery check (EHA vs V1 grid Ehrenfest)
    mach = {}
    for cell in results["cells"]:
        if cell["kind"] != "S1":
            continue
        e = fin(cell["runs"]["EHA"])
        if v1ref is None:
            mach[cell["Rf"]] = None
        else:
            P1, r1 = v1ref[cell["Rf"]]
            mach[cell["Rf"]] = {"dP_exc": e["P_exc"] - P1, "d_electron_right": e["electron_right"] - r1,
                                "pass": abs(e["P_exc"] - P1) <= 0.01 and abs(e["electron_right"] - r1) <= 0.01}
    s1_machinery_ok = all(x is None or x["pass"] for x in mach.values())

    s3_cells = []
    for cell in results["cells"]:
        runs = cell["runs"]
        tv_ok = cell["table_validation"]["pass"]
        q, problems, unsup, appl_branch = q_validity(runs)
        ref_ok = not problems and not unsup
        rec = {"Rf": cell["Rf"], "P0": cell["P0"], "reference": {"valid": ref_ok, "problems": problems,
               "unsupported": unsup, "final": q}, "table_validation": cell["table_validation"],
               "ledger": ledger(runs)}
        if cell["kind"] == "S1":
            obs = ["P_exc", "electron_right", "coherence_indicator"] + (["branch_separation"] if appl_branch else [])
            rec["machinery_check"] = mach.get(cell["Rf"])
            rec["methods"] = {m: method_verdicts(runs, m, q, obs, ref_ok, tv_ok and s1_machinery_ok)
                              for m in ("CT", "EHA")}
            if not appl_branch:
                for m in rec["methods"]:
                    rec["methods"][m]["verdict"]["branch_separation"] = "NOT_APPLICABLE"
            out["S1"].append(rec)
        elif cell["kind"] == "S2r":
            recheck_s2r_rule(cell, M)
            rec["rule"] = cell["rule"]
            obs = ["transmission", "P_exc"]
            rec["methods"] = {m: method_verdicts(runs, m, q, obs, ref_ok, tv_ok) for m in ("CT", "EHA")}
            # BOQ (no quadrature) and BOCL exact
            boq = fin(runs["BOQ"])
            b1, b2 = runs["BOCL_exact"], runs["BOCL_exact_conv"]
            tq = q["transmission"]
            if not ref_ok:
                tun = "REFUSED"
            elif tq < 1e-6:
                tun = "INCONCLUSIVE"
            else:
                tun = None
            rec["BOQ"] = {"transmission": boq["transmission"],
                          "verdict": tun or ("REPRESENTED" if band(boq["transmission"], tq, "transmission") else "DISTORTED")}
            conv_ok = abs(b1["transmission"] - b2["transmission"]) <= max(1e-4, 0.05 * b2["transmission"])
            lost_ok = max(b1["weight_left_table"], b2["weight_left_table"]) <= EDGE
            bv = tun or ("REFUSED" if not conv_ok else "UNSUPPORTED" if not lost_ok else
                         ("REPRESENTED" if band(b1["transmission"], tq, "transmission") else "DISTORTED"))
            rec["BOCL_exact"] = {"transmission": b1["transmission"], "transmission_conv": b2["transmission"],
                                 "wigner_mass_above_barrier": b1["wigner_mass_above_barrier"], "verdict": bv,
                                 "quantum_minus_classical": tq - b1["transmission"]}
            out["S2r"] = rec
        else:
            Rg = cell["R_g"]
            xs = [s["R_mean"] - Rg for s in runs["Q"]["samples"]]
            crossings = sum(1 for a, b in zip(xs, xs[1:]) if (a < 0) != (b < 0))
            rec["R_g"], rec["crossings"] = Rg, crossings
            rec["applicable"] = crossings >= 2
            obs = ["P_exc", "coherence_indicator"]
            rec["methods"] = {m: method_verdicts(runs, m, q, obs, ref_ok, tv_ok) for m in ("CT", "EHA")}
            s3_cells.append(rec)

    if s3_cells:
        appl = [c for c in s3_cells if c["applicable"]]
        s3 = {"cells": s3_cells, "n_applicable": len(appl)}
        if any(not c["reference"]["valid"] for c in appl):
            s3["phase_test"] = "REFUSED"
        elif len(appl) < 2:
            s3["phase_test"] = "NOT_APPLICABLE"
        else:
            qv = [c["reference"]["final"]["P_exc"] for c in appl]
            s3["Q_contrast"] = max(qv) - min(qv)
            if s3["Q_contrast"] < 0.05:
                s3["phase_test"] = "NOT_DEMONSTRATED"
            else:
                s3["phase_test"] = "TESTED"
                s3["phase_verdict"] = {}
                for m in ("CT", "EHA"):
                    vs = [c["methods"][m]["verdict"]["P_exc"] for c in appl]
                    mv = [c["methods"][m]["final"].get("P_exc") for c in appl]
                    if "REFUSED" in vs or "UNSUPPORTED" in vs or None in mv:
                        verdict = "REFUSED"
                        contrast = None
                    else:
                        contrast = max(mv) - min(mv)
                        ok = all(v == "REPRESENTED" for v in vs) and \
                            abs(contrast - s3["Q_contrast"]) <= max(0.02, 0.2 * s3["Q_contrast"])
                        verdict = "REPRESENTED" if ok else "DISTORTED"
                    s3["phase_verdict"][m] = {"verdict": verdict, "contrast": contrast, "per_P0": vs}
        out["S3"] = s3
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("results")
    ap.add_argument("--protocol", default=str(HERE / "protocol.json"))
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    raw = Path(a.results).read_bytes()
    res = json.loads(raw)
    proto = json.loads(Path(a.protocol).read_text(encoding="utf-8"))
    out = check(res, proto)
    out["results_sha256"] = hashlib.sha256(raw).hexdigest()
    text = json.dumps(out, indent=1)
    if a.out:
        Path(a.out).write_text(text, encoding="utf-8")
    print(text[:3000])


if __name__ == "__main__":
    main()
