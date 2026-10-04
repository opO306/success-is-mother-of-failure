"""Run the sealed Exact Expression State Gate V0.

    python -m exact_expression_gate_v0.campaign --out runs/exact_expression_gate_v0_<date> [--quick] [--only NAME]

Writes one JSON per scenario as soon as it finishes (partial results survive) and prints progress lines.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import time
import tracemalloc
from fractions import Fraction as Q
from pathlib import Path

from mpmath import iv
from mpmath.libmp import to_rational

import a_reference.c1b1_two_atom as C

from . import lang_iv as LI
from .dag import DAG, build_kdk

HERE = Path(__file__).resolve().parent
SOURCES = ["__init__.py", "lang_iv.py", "dag.py", "campaign.py", "protocol.json"]
MASS = C.AR40_MASS_ME
DT = Q(40)
POS_F, MOM_F = 48, 80


def q3(*xs):
    return tuple(Q(x) for x in xs)


SCENARIOS = {
    "F_free": ([q3(0, 0, 0)], [q3(14, 3, -2)]),
    "A2_bound": ([q3("-71/20", 0, 0), q3("71/20", 0, 0)], [q3(1, -3, 0), q3(-1, 3, 0)]),
    "A3_low": ([q3(0, 0, 0), q3(25, 0, 0), q3(0, 25, 0)], [q3(2, 1, 0), q3(-1, 2, 0), q3(-1, -3, 0)]),
    "A3_high": ([q3(0, 0, 0), q3("71/10", 0, 0), q3("71/20", "6149/1000", 0)],
                [q3(3, 0, "1/2"), q3("-3/2", "13/5", 0), q3("-3/2", "-13/5", "-1/2")]),
}


def rhe(x: Q) -> int:
    n, d = x.numerator, x.denominator
    sign = -1 if n < 0 else 1
    q, r = divmod(abs(n), d)
    if 2 * r > d or (2 * r == d and q & 1):
        q += 1
    return sign * q


def cell(v, frac_bits):
    """Grid cell of an interval if both endpoints round to the same raw value, else None."""
    lo = Q(*to_rational(v._mpi_[0]))
    hi = Q(*to_rational(v._mpi_[1]))
    a, b = rhe(lo * (1 << frac_bits)), rhe(hi * (1 << frac_bits))
    return a if a == b else None


def decide(qv, pv):
    out = [cell(v, POS_F) for v in qv] + [cell(v, MOM_F) for v in pv]
    return None if any(x is None for x in out) else out


def replay(q0, p0, steps, prec, checkpoints):
    """Path C: interval KDK recomputed from the initial state. Returns {cp: cells or None}."""
    iv.prec = prec
    n = len(q0)
    h, cdt = LI.c(DT / 2), LI.c(DT / MASS)
    q = [[LI.c(x) for x in r] for r in q0]
    p = [[LI.c(x) for x in r] for r in p0]
    pairs = [(i, j) for i in range(n) for j in range(i + 1, n)]
    r2min = LI.c(LI.L.R_MIN_BOHR ** 2)

    def forces(q):
        F = [[iv.mpf(0)] * 3 for _ in range(n)]
        for i, j in pairs:
            d = [q[j][k] - q[i][k] for k in range(3)]
            r2 = d[0] * d[0] + d[1] * d[1] + d[2] * d[2]
            if not (r2.a > r2min):
                raise ValueError("R^2 below r_min^2")
            g = LI.G_of_R2(r2)
            for k in range(3):
                F[j][k] = F[j][k] + h * g * d[k]
                F[i][k] = F[i][k] - h * g * d[k]
        return F

    out = {}
    try:
        F = forces(q)
        for s in range(1, steps + 1):
            p = [[p[a][k] + F[a][k] for k in range(3)] for a in range(n)]
            q = [[q[a][k] + p[a][k] * cdt for k in range(3)] for a in range(n)]
            F = forces(q)
            p = [[p[a][k] + F[a][k] for k in range(3)] for a in range(n)]
            if s in checkpoints:
                out[s] = decide([x for r in q for x in r], [x for r in p for x in r])
    except ValueError:
        pass
    for c in checkpoints:
        out.setdefault(c, None)
    return out, (q, p)


def sweep(dag, snaps, checkpoints, grid):
    """Smallest grid precision deciding each checkpoint (path evaluation with memo)."""
    found = {}
    timing = {}
    for prec in grid:
        if all(c in found for c in checkpoints):
            break
        memo = {}
        t0 = time.perf_counter()
        for cp in checkpoints:
            if cp in found:
                continue
            qi, pi = snaps[cp]
            try:
                vals = dag.evaluate(qi + pi, prec, memo)
            except ValueError:
                break
            d = decide(vals[:len(qi)], vals[len(qi):])
            if d is not None:
                found[cp] = (prec, d)
        timing[prec] = time.perf_counter() - t0
    return found, timing


def eval_once(dag, snaps, cp, prec):
    t0 = time.perf_counter()
    qi, pi = snaps[cp]
    try:
        vals = dag.evaluate(qi + pi, prec, {})
        d = decide(vals[:len(qi)], vals[len(qi):])
    except ValueError:
        d = None
    return d, time.perf_counter() - t0


def tree_size_estimate(dag, roots):
    """Fully expanded tree size by dynamic programming over the DAG (never materialised)."""
    size = {}
    for i in sorted(dag._collect(roots)):
        n = dag.nodes[i]
        if n[0] == "lin":
            size[i] = 1 + sum(size[a] for a, _ in n[1])
        elif n[0] == "mul":
            size[i] = 1 + size[n[1]] + size[n[2]]
        elif n[0] == "G":
            size[i] = 1 + size[n[1]]
        else:
            size[i] = 1
    return sum(size[r] for r in roots)


def run_scenario(name, q0, p0, checkpoints, grid, log):
    res = {"name": name, "checkpoints": checkpoints}
    for path in ("A", "B"):
        tracemalloc.start()
        t0 = time.perf_counter()
        dag = DAG(optimize=(path == "B"))
        snaps = build_kdk(dag, q0, p0, MASS, DT, max(checkpoints), set(checkpoints))
        build_s = time.perf_counter() - t0
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        sizes = {cp: dag.reachable(snaps[cp][0] + snaps[cp][1]) for cp in checkpoints}
        created_edges = sum(len(n[1]) if n[0] == "lin" else (2 if n[0] == "mul" else (1 if n[0] == "G" else 0))
                            for n in dag.nodes)
        created_size = len(dag.nodes) + created_edges
        rec = {"build_s": build_s, "build_peak_bytes": peak, "created_nodes": len(dag.nodes),
               "created_size": created_size, "constructor_calls": dag.created_calls,
               "reachable": {str(cp): {"nodes": s[0], "edges": s[1], "size": s[0] + s[1]} for cp, s in sizes.items()},
               "bytes_per_size_unit": peak / max(1, created_size)}
        if path == "A":
            rec["tree_size_log2"] = {str(cp): tree_size_estimate(dag, snaps[cp][0] + snaps[cp][1]).bit_length()
                                     for cp in checkpoints}
            log(f"{name}: A built {len(dag.nodes)} nodes in {build_s:.1f}s; sweeping precision")
            t0 = time.perf_counter()
            found, timing = sweep(dag, snaps, checkpoints, grid)
            rec["sweep_s"] = time.perf_counter() - t0
            rec["sweep_timing"] = {str(k): v for k, v in timing.items()}
            rec["required_bits"] = {str(cp): (found[cp][0] if cp in found else "UNDECIDED_AT_CAP") for cp in checkpoints}
            res["cells"] = {str(cp): found[cp][1] for cp in found}
            res["dagA"] = (dag, snaps)
        else:
            rec["eval"] = {}
            for cp in checkpoints:
                need = res["A"]["required_bits"][str(cp)]
                if need == "UNDECIDED_AT_CAP":
                    rec["eval"][str(cp)] = {"status": "skipped (A undecided)"}
                    continue
                d, t = eval_once(dag, snaps, cp, need)
                prec = need
                while d is None and grid.index(prec) + 1 < len(grid):
                    prec = grid[grid.index(prec) + 1]
                    d, t = eval_once(dag, snaps, cp, prec)
                rec["eval"][str(cp)] = {"bits": prec, "wall_s": t, "agrees_with_A": d == res["cells"].get(str(cp))}
        res[path] = rec
    dagA, snapsA = res.pop("dagA")
    res["A"]["eval"] = {}
    res["C"] = {}
    for cp in checkpoints:
        need = res["A"]["required_bits"][str(cp)]
        if need == "UNDECIDED_AT_CAP":
            continue
        d, t = eval_once(dagA, snapsA, cp, need)
        res["A"]["eval"][str(cp)] = {"bits": need, "wall_s": t}
        t0 = time.perf_counter()
        out, _ = replay(q0, p0, cp, need, {cp})
        res["C"][str(cp)] = {"bits": need, "wall_s": time.perf_counter() - t0, "agrees_with_A": out[cp] == res["cells"][str(cp)]}
    # intrinsic sensitivity (diagnostic)
    log(f"{name}: sensitivity")
    t0 = time.perf_counter()
    qa = [list(r) for r in q0]
    qb = [list(r) for r in q0]
    qb[0][0] += Q(1, 1 << 100)
    sens = {}
    for cp in checkpoints:
        _, (q1, p1) = replay([tuple(r) for r in qa], p0, cp, 400, set())
        _, (q2, p2) = replay([tuple(r) for r in qb], p0, cp, 400, set())
        diff = 0.0
        for A, B in ((q1, q2), (p1, p2)):
            for ra, rb in zip(A, B):
                for x, y in zip(ra, rb):
                    diff = max(diff, abs(float((x - y).mid)))
        import math
        sens[str(cp)] = (math.log2(diff) + 100) if diff > 0 else None
    res["intrinsic_amplification_log2"] = sens
    res["sensitivity_s"] = time.perf_counter() - t0
    return res


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--only")
    a = ap.parse_args(argv)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    proto = json.loads((HERE / "protocol.json").read_text(encoding="utf-8"))
    head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=HERE).stdout.strip()
    seal = {"quick": a.quick, "git_head_at_start": head, "python": platform.python_version(),
            "source_sha256": {s: hashlib.sha256((HERE / s).read_bytes()).hexdigest() for s in SOURCES}}
    (out / "execution_seal.json").write_text(json.dumps(seal, indent=1), encoding="utf-8")
    grid = proto["precision_grid"]
    cps = [10, 20] if a.quick else proto["checkpoints"]
    names = [n for n in SCENARIOS if not a.only or n == a.only]
    jobs = [(n, cps, grid, a.quick, str(out), seal, proto) for n in names]
    if len(jobs) > 1 and not a.quick:
        import multiprocessing as mp
        with mp.get_context("spawn").Pool(len(jobs)) as pool:
            pool.map(scenario_job, jobs, chunksize=1)
    else:
        for j in jobs:
            scenario_job(j)


def scenario_job(args):
    name, cps, grid, quick, out, seal, proto = args
    q0, p0 = SCENARIOS[name]

    def log(msg):
        print(time.strftime("%H:%M:%S"), msg, flush=True)

    log(f"start {name}")
    try:
        r = run_scenario(name, q0, p0, cps, grid, log)
        Path(out, f"{name}.base.json").write_text(json.dumps({"seal": seal, "protocol": proto, "result": r}, indent=1),
                                                  encoding="utf-8")
        if not quick and r["A"]["sweep_s"] < 300:
            log(f"{name}: extended 10000-step checkpoint")
            r["extended"] = run_scenario(name, q0, p0, [10000], grid, log)
        elif not quick:
            r["extended"] = "NOT_RUN(time)"
        Path(out, f"{name}.json").write_text(json.dumps({"seal": seal, "protocol": proto, "result": r}, indent=1),
                                             encoding="utf-8")
        log(f"done {name}")
    except Exception as e:  # recorded, never hidden; other scenarios keep running
        import traceback
        Path(out, f"{name}.ERROR.txt").write_text(traceback.format_exc(), encoding="utf-8")
        log(f"FAILED {name}: {e!r}")


if __name__ == "__main__":
    main()
