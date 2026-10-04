"""Run the sealed Gate V1 panel. Writes raw results (Git-external run dir) and a
compact results.json. Usage:

    python -m nuclear_gate_v1.campaign --out runs/nuclear_gate_v1_<date> [--quick]

--quick shrinks grids/time for smoke tests only; quick output is never evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import multiprocessing as mp
import platform
import subprocess
from pathlib import Path

import numpy as np

from . import dynamics as dyn
from .model import Grid, Params, adiabatic_states

HERE = Path(__file__).resolve().parent
SOURCES = ["__init__.py", "model.py", "dynamics.py", "campaign.py", "protocol.json"]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_protocol() -> dict:
    return json.loads((HERE / "protocol.json").read_text(encoding="utf-8"))


def grid(d) -> Grid:
    return Grid(float(d["lo"]), float(d["hi"]), int(d["n"]))


def quickify(proto: dict) -> dict:
    proto = json.loads(json.dumps(proto))
    g = proto["grids"]
    g["R"]["n"], g["x"]["n"], g["R_fine"]["n"], g["x_fine"]["n"] = 128, 128, 160, 160
    proto["time"].update({"dt": 0.5, "dt_fine": 0.25, "t_final": 40.0, "sample_every": 10.0})
    proto["classical_ensemble"].update({"n_primary": 4, "n_convergence": 5})
    proto["model"]["Rf_panel"] = proto["model"]["Rf_panel"][:1]
    return proto


def s2_rule(Rg: Grid, V0: np.ndarray):
    """Sealed S2 rule (protocol.scenarios.S2_barrier.rule)."""
    R = Rg.points
    left = (R >= -8.0) & (R < 0.0)
    ia = np.flatnonzero(left)[np.argmin(V0[left])]
    Ra = R[ia]
    span = (R >= Ra) & (R <= -Ra)
    idx = np.flatnonzero(span)
    ib = idx[np.argmax(V0[span])]
    Rb = R[ib]
    B = float(V0[ib] - V0[ia])
    endpoint = ib in (idx[0], idx[-1])
    return {"R_a": float(Ra), "R_b": float(Rb), "barrier": B,
            "applicable": bool(B >= 1e-3 and not endpoint)}


def run_cell(args):
    proto, Rf, workers = args
    dyn.FFT_WORKERS = workers
    m = proto["model"]
    p = Params(m["L"], Rf, m["Rl"], m["Rr"], m["M"])
    G = proto["grids"]
    Rg, xg, Rgf, xgf = grid(G["R"]), grid(G["x"]), grid(G["R_fine"]), grid(G["x_fine"])
    ns = int(G["nstates"])
    T = proto["time"]
    ts = dyn.TimeSpec(T["dt"], T["t_final"], T["sample_every"])
    tsf = dyn.TimeSpec(T["dt_fine"], T["t_final"], T["sample_every"])
    ce = proto["classical_ensemble"]

    ad = adiabatic_states(Rg.points, xg, p, ns)
    adf = adiabatic_states(Rgf.points, xgf, p, ns)
    V0 = ad[0][:, 0]
    s2 = s2_rule(Rg, V0)
    surfaces = {"R": Rg.points.tolist(), "E": ad[0].tolist()}

    S = proto["scenarios"]
    scenarios = [dyn.Scenario("S1_slide", S["S1_slide"]["R0"], S["S1_slide"]["P0"], S["S1_slide"]["sigma"], None)]
    if s2["applicable"]:
        Ek = 0.5 * s2["barrier"]
        scenarios.append(dyn.Scenario("S2_barrier", s2["R_a"], float(np.sqrt(2 * p.M * Ek)),
                                      S["S1_slide"]["sigma"], s2["R_b"]))
    out = {"Rf": Rf, "S2_rule": s2, "scenarios": {}}
    for sc in scenarios:
        runs = {
            "Q": dyn.run_q(p, Rg, xg, ts, sc, ns, ad),
            "Q_dt_fine": dyn.run_q(p, Rg, xg, tsf, sc, ns, ad),
            "Q_grid_fine": dyn.run_q(p, Rgf, xgf, ts, sc, ns, adf),
            "BOQ": dyn.run_boq(p, Rg, xg, ts, sc, ad),
            "EH": dyn.run_eh(p, xg, ts, sc, ce["n_primary"], ns),
            "EH_quad_conv": dyn.run_eh(p, xg, ts, sc, ce["n_convergence"], ns),
            "BOCL": dyn.run_bocl(p, Rg, xg, ts, sc, ce["n_primary"], ns, ad),
            "BOCL_quad_conv": dyn.run_bocl(p, Rg, xg, ts, sc, ce["n_convergence"], ns, ad),
        }
        out["scenarios"][sc.name] = {"R0": sc.R0, "P0": sc.P0, "sigma": sc.sigma, "R_b": sc.R_b, "runs": runs}
    return out, surfaces


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--processes", type=int, default=3)
    a = ap.parse_args(argv)
    proto = load_protocol()
    if a.quick:
        proto = quickify(proto)
    outdir = Path(a.out)
    outdir.mkdir(parents=True, exist_ok=True)
    try:
        head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=HERE).stdout.strip()
    except OSError:
        head = None
    seal = {
        "quick": a.quick,
        "git_head_at_start": head,
        "source_sha256": {s: sha256(HERE / s) for s in SOURCES},
        "python": platform.python_version(),
        "numpy": np.__version__,
        "platform": platform.platform(),
    }
    (outdir / "execution_seal.json").write_text(json.dumps(seal, indent=1), encoding="utf-8")
    panel = proto["model"]["Rf_panel"]
    workers = max(1, 12 // max(1, a.processes))
    jobs = [(proto, Rf, workers) for Rf in panel]
    if a.processes > 1 and len(jobs) > 1:
        with mp.get_context("spawn").Pool(min(a.processes, len(jobs))) as pool:
            cells = pool.map(run_cell, jobs)
    else:
        cells = [run_cell(j) for j in jobs]
    results = {"protocol": proto, "seal": seal, "cells": [c for c, _ in cells]}
    (outdir / "results.json").write_text(json.dumps(results, indent=1), encoding="utf-8")
    (outdir / "surfaces.json").write_text(json.dumps({str(c["Rf"]): s for c, s in cells}), encoding="utf-8")
    print("wrote", outdir / "results.json")


if __name__ == "__main__":
    main()
