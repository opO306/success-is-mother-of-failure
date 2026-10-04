"""Run the sealed Gate V2 panel.

    python -m nuclear_gate_v2.campaign --out runs/nuclear_gate_v2_<date> [--quick] [--processes 6]
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

from nuclear_gate_v1 import dynamics as dyn1
from nuclear_gate_v1.model import Grid, Params, adiabatic_states

from . import bocl_exact, ctmqc, q2
from .table import AdiabaticTable

HERE = Path(__file__).resolve().parent
SOURCES = ["__init__.py", "table.py", "ctmqc.py", "q2.py", "bocl_exact.py", "campaign.py", "protocol.json"]
V1_SOURCES = ["model.py", "dynamics.py"]

GRID = {"R": Grid(-9.0, 9.0, 512), "x": Grid(-32.0, 32.0, 512),
        "R_fine": Grid(-9.0, 9.0, 768), "x_fine": Grid(-32.0, 32.0, 768),
        "R_tab": Grid(-9.0, 9.0, 1024)}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_protocol() -> dict:
    return json.loads((HERE / "protocol.json").read_text(encoding="utf-8"))


def s2r_rule(R: np.ndarray, V0: np.ndarray, M: float, slope_fn):
    left = (R >= -8.0) & (R < 0.0)
    ia = np.flatnonzero(left)[np.argmin(V0[left])]
    span = (R >= R[ia]) & (R <= -R[ia])
    idx = np.flatnonzero(span)
    ib = idx[np.argmax(V0[span])]
    B = float(V0[ib] - V0[ia])
    target = V0[ia] + 0.8 * B
    j = ia
    while j > 0 and V0[j] < target:
        j -= 1
    # V0[j] >= target > V0[j+1] on the outer wall
    Rc = float(R[j] + (target - V0[j]) * (R[j + 1] - R[j]) / (V0[j + 1] - V0[j]))
    slope = float(slope_fn(Rc))
    sigma = float((2.0 / (M * abs(slope))) ** (1.0 / 3.0))
    return {"R_a": float(R[ia]), "R_b": float(R[ib]), "barrier": B, "R_c": Rc,
            "slope_at_R_c": slope, "sigma": sigma}


def gap_min(R, E):
    left = (R >= -8.0) & (R < 0.0)
    gap = E[:, 1] - E[:, 0]
    i = np.flatnonzero(left)[np.argmin(gap[left])]
    return float(R[i])


def job(args):
    kind, proto, Rf, P0, scale, workers = args
    q2.FFT_WORKERS = workers
    m = proto["model"]
    p = Params(m["L"], Rf, m["Rl"], m["Rr"], m["M"])
    G = dict(GRID)
    if scale == "quick":
        G = {"R": Grid(-9.0, 9.0, 128), "x": Grid(-32.0, 32.0, 128), "R_fine": Grid(-9.0, 9.0, 160),
             "x_fine": Grid(-32.0, 32.0, 160), "R_tab": Grid(-9.0, 9.0, 160)}
    gt = proto["grids_time"]
    nq, nq2 = gt["quadrature"]["n_primary"], gt["quadrature"]["n_convergence"]
    if scale == "quick":
        nq, nq2 = 4, 5
    ns = gt["nstates_projection"]
    ad = adiabatic_states(G["R"].points, G["x"], p, ns)
    adf = adiabatic_states(G["R_fine"].points, G["x_fine"], p, ns)
    table = AdiabaticTable(p, G["x"], ns, G["R_tab"])
    tv = table.validate(8 if scale == "quick" else 64)
    S = proto["scenarios"]
    surf = {"R": G["R"].points.tolist(), "E": ad[0].tolist()}

    if kind == "S1":
        sc = dyn1.Scenario("S1", S["S1_branching"]["R0"], S["S1_branching"]["P0"], S["S1_branching"]["sigma"], None)
        tf = S["S1_branching"]["t_final"]
    elif kind == "S2r":
        rule = s2r_rule(G["R"].points, ad[0][:, 0], p.M, lambda r: table.G(np.array([r]))[0, 0])
        sc = dyn1.Scenario("S2r", rule["R_c"], 0.0, rule["sigma"], rule["R_b"])
        tf = S["S2r_tunnelling"]["t_final"]
    else:
        sc = dyn1.Scenario("S3", S["S3_recombination"]["R0"], P0, S["S3_recombination"]["sigma"], None)
        tf = S["S3_recombination"]["t_final"]
    if scale == "quick":
        tf = 40.0
    dt, dtf = (0.5, 0.25) if scale == "quick" else (gt["dt"], gt["dt_fine"])
    ts = dyn1.TimeSpec(dt, tf, gt["sample_every"])
    tsf = dyn1.TimeSpec(dtf, tf, gt["sample_every"])

    runs = {
        "Q": q2.run_q2(p, G["R"], G["x"], ts, sc, ad),
        "Q_dt_fine": q2.run_q2(p, G["R"], G["x"], tsf, sc, ad),
        "Q_grid_fine": q2.run_q2(p, G["R_fine"], G["x_fine"], ts, sc, adf),
        "CT": ctmqc.run(table, p.M, ts, sc, nq, True),
        "CT_quad_conv": ctmqc.run(table, p.M, ts, sc, nq2, True),
        "EHA": ctmqc.run(table, p.M, ts, sc, nq, False),
        "EHA_quad_conv": ctmqc.run(table, p.M, ts, sc, nq2, False),
    }
    extra = {}
    if kind == "S2r":
        extra["rule"] = rule
        runs["BOQ"] = dyn1.run_boq(p, G["R"], G["x"], ts, sc, ad)
        n1, n2 = (21, 31) if scale == "quick" else (201, 301)
        runs["BOCL_exact"] = bocl_exact.run_bocl_exact(table, p.M, ts, sc, n1)
        runs["BOCL_exact_conv"] = bocl_exact.run_bocl_exact(table, p.M, ts, sc, n2)
    if kind == "S3":
        extra["R_g"] = gap_min(G["R"].points, ad[0])
    return {"kind": kind, "Rf": Rf, "P0": P0, "R0": sc.R0, "sigma": sc.sigma, "R_b": sc.R_b,
            "t_final": tf, "table_validation": tv, "surface": surf, **extra, "runs": runs}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--processes", type=int, default=6)
    a = ap.parse_args(argv)
    proto = load_protocol()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    try:
        head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=HERE).stdout.strip()
    except OSError:
        head = None
    v1 = HERE.parent / "nuclear_gate_v1"
    seal = {"quick": a.quick, "git_head_at_start": head,
            "source_sha256": {**{s: sha256(HERE / s) for s in SOURCES},
                              **{"v1/" + s: sha256(v1 / s) for s in V1_SOURCES}},
            "python": platform.python_version(), "numpy": np.__version__, "platform": platform.platform()}
    (out / "execution_seal.json").write_text(json.dumps(seal, indent=1), encoding="utf-8")
    scale = "quick" if a.quick else "full"
    S = proto["scenarios"]
    workers = max(1, 12 // max(1, a.processes))
    jobs = [("S1", proto, Rf, 0.0, scale, workers) for Rf in S["S1_branching"]["Rf_panel"]]
    jobs.append(("S2r", proto, S["S2r_tunnelling"]["Rf"], 0.0, scale, workers))
    jobs += [("S3", proto, S["S3_recombination"]["Rf"], P0, scale, workers) for P0 in S["S3_recombination"]["P0_scan"]]
    if a.quick:
        jobs = [jobs[0], jobs[len(S["S1_branching"]["Rf_panel"])], jobs[-1]]
    if a.processes > 1:
        with mp.get_context("spawn").Pool(a.processes) as pool:
            cells = pool.map(job, jobs, chunksize=1)
    else:
        cells = [job(j) for j in jobs]
    results = {"protocol": proto, "seal": seal, "cells": cells}
    (out / "results.json").write_text(json.dumps(results), encoding="utf-8")
    print("wrote", out / "results.json")


if __name__ == "__main__":
    main()
