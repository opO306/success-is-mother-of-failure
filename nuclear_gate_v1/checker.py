"""Independent verdict checker for Gate V1.

Recomputes every verdict from the raw results and the sealed protocol.
Does not import model / dynamics / campaign (enforced by a test).

    python -m nuclear_gate_v1.checker RESULTS.json [--protocol PROTOCOL.json] [--out VERDICTS.json]
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

PROB_OBS = ("P_exc", "electron_right", "transmission")
METHODS = ("Q", "EH", "BOQ", "BOCL")
STRUCTURAL_ABSENT = {"BOQ": ("P_exc", "branch_separation"), "BOCL": ("P_exc", "branch_separation")}
EDGE_LIMIT = 1e-6


class CheckError(Exception):
    pass


def final_obs(run: dict) -> dict:
    s = run["samples"][-1]
    out = {k: s.get(k) for k in PROB_OBS}
    r0, rx = s.get("R_mean_0"), s.get("R_mean_exc")
    out["branch_separation"] = None if (r0 is None or rx is None) else rx - r0
    return out


def max_edge(run: dict) -> float:
    return max(max(s.get("electron_edge") or 0.0, s.get("nuclear_edge") or 0.0) for s in run["samples"])


def drift(run: dict, key: str) -> float:
    v0 = run["samples"][0][key]
    return max(abs(s[key] - v0) for s in run["samples"])


def close(a, b, obs, abs_tol, rel_tol):
    if a is None or b is None:
        return a is None and b is None
    if obs == "branch_separation":
        return abs(a - b) <= rel_tol * abs(b)
    return abs(a - b) <= abs_tol


def check_cell_scenario(sc: dict) -> dict:
    runs = sc["runs"]
    q = runs["Q"]
    report = {"reference": {}, "verdicts": {}, "ledger": {}, "cost": {}}

    # ---- reference validity
    qf = final_obs(q)
    problems = []
    if max(abs(s["norm"] - 1.0) for s in q["samples"]) > 1e-8:
        problems.append("Q norm drift")
    if drift(q, "energy") > 1e-4:
        problems.append("Q energy drift")
    branch_applicable = (qf.get("P_exc") or 0.0) >= 0.05 and qf.get("branch_separation") is not None
    for alt in ("Q_dt_fine", "Q_grid_fine"):
        af = final_obs(runs[alt])
        for obs in ("P_exc", "electron_right", "transmission", "branch_separation"):
            if qf.get(obs) is None and af.get(obs) is None:
                continue
            if obs == "branch_separation" and not branch_applicable:
                continue  # protocol: branch_separation exists only when applicable
            if not close(qf.get(obs), af.get(obs), obs, 1e-3, 0.01):
                problems.append(f"{alt} {obs}: {qf.get(obs)} vs {af.get(obs)}")
    unsupported_q = any(max_edge(runs[k]) > EDGE_LIMIT for k in ("Q", "Q_dt_fine", "Q_grid_fine"))
    report["reference"] = {"valid": not problems and not unsupported_q, "problems": problems,
                           "unsupported": unsupported_q, "final": qf}

    applicable = {
        "P_exc": True,
        "electron_right": True,
        "transmission": qf.get("transmission") is not None,
        "branch_separation": branch_applicable,
    }

    # ---- method verdicts
    for m in ("EH", "BOQ", "BOCL"):
        run = runs[m]
        mf = final_obs(run) if "domain_stop" not in run else {}
        conv = runs.get(f"{m}_quad_conv")
        v = {}
        for obs, app in applicable.items():
            if not app:
                v[obs] = "NOT_APPLICABLE"
                continue
            if obs in STRUCTURAL_ABSENT.get(m, ()):
                if obs == "P_exc" and mf.get("P_exc") not in (0.0, None):
                    raise CheckError(f"{m} claims structural absence but P_exc={mf.get('P_exc')}")
                v[obs] = "ABSENT_BY_CONSTRUCTION"
                continue
            if unsupported_q or problems:
                v[obs] = "REFUSED"
                continue
            if "domain_stop" in run or max_edge(run) > EDGE_LIMIT:
                v[obs] = "UNSUPPORTED"
                continue
            if conv is not None:
                cf = final_obs(conv) if "domain_stop" not in conv else {}
                if not close(mf.get(obs), cf.get(obs), obs, 1e-3, 0.01):
                    v[obs] = "REFUSED"
                    continue
            a, b = mf.get(obs), qf.get(obs)
            if a is None:
                v[obs] = "DISTORTED"
                continue
            if obs == "branch_separation":
                ok = abs(a - b) <= 0.2 * abs(b)
            else:
                ok = abs(a - b) <= max(0.02, 0.1 * abs(b))
            v[obs] = "REPRESENTED" if ok else "DISTORTED"
        report["verdicts"][m] = {"verdict": v, "final": mf}

    # ---- ledger and cost (reported, not used for selection)
    for m in METHODS:
        run = runs[m]
        led = {"energy_drift": drift(run, "energy"), "max_edge": max_edge(run)}
        if "max_traj_energy_dev" in run["samples"][-1]:
            led["max_traj_energy_dev"] = max(s["max_traj_energy_dev"] for s in run["samples"])
        report["ledger"][m] = led
        report["cost"][m] = {**run["cost"], "state_values": run["state_values"]}
    return report


def check(results: dict, protocol: dict | None = None) -> dict:
    if protocol is not None and not results["seal"]["quick"]:
        if json.dumps(protocol, sort_keys=True) != json.dumps(results["protocol"], sort_keys=True):
            raise CheckError("results were not produced under the sealed protocol")
    out = {"quick": results["seal"]["quick"], "cells": []}
    for cell in results["cells"]:
        c = {"Rf": cell["Rf"], "S2_rule": cell["S2_rule"], "scenarios": {}}
        for name, sc in cell["scenarios"].items():
            c["scenarios"][name] = check_cell_scenario(sc)
        if not cell["S2_rule"]["applicable"]:
            c["scenarios"]["S2_barrier"] = "NOT_APPLICABLE"
        out["cells"].append(c)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("results")
    ap.add_argument("--protocol", default=str(Path(__file__).with_name("protocol.json")))
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    res_bytes = Path(a.results).read_bytes()
    results = json.loads(res_bytes)
    proto = json.loads(Path(a.protocol).read_text(encoding="utf-8"))
    out = check(results, proto)
    out["results_sha256"] = hashlib.sha256(res_bytes).hexdigest()
    text = json.dumps(out, indent=1)
    if a.out:
        Path(a.out).write_text(text, encoding="utf-8")
    print(text[:4000])


if __name__ == "__main__":
    main()
