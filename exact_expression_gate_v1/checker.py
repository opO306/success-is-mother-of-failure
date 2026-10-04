"""Independent checker for Exact Expression Gate V1.

Imports none of dag, stream, paths, common, campaign (a test enforces it). Own interval KDK replay, own rounding,
own domain rule, own exact computation of the controls. Shared TCB: exact_expression_gate_v0/lang_iv.py (force).

V0 checker holes closed here: no positive label from empty or missing evidence (all 70 jobs, every requested step,
every cost field must be there, and the replay confirmations must actually happen); stored agreement flags are not
read, cells are compared directly; sources and protocol are bound by hash; no 'dominant failure' choice.

    python -m exact_expression_gate_v1.checker RUN_DIR [--out VERDICT.json] [--fast]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import time
from fractions import Fraction as F
from pathlib import Path

from mpmath import iv
from mpmath.libmp import finf, fnan, fninf, to_rational

from exact_expression_gate_v0 import lang_iv as LI

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SEALED = ["exact_expression_gate_v1/" + f for f in
          ("__init__.py", "common.py", "dag.py", "stream.py", "paths.py", "campaign.py", "checker.py", "protocol.json")] + \
         ["exact_expression_gate_v0/lang_iv.py", "a_reference/ar2_lang2024.py"]
PHYSICAL = ["F_free", "A2_bound", "A3_low", "A3_high"]
INTERACTING = ["A2_bound", "A3_low", "A3_high"]
CONTROL = ["H_halfway", "D_zero"]
PATHS = ["A", "B", "C", "CS", "CX"]
STATUSES = {"DECIDED", "UNDECIDED_AT_CAP", "REFUSED_DOMAIN", "OUT_OF_RANGE"}
FINAL = {"DECIDED", "REFUSED_DOMAIN", "OUT_OF_RANGE"}
MASS = F("39.9623831237") / F("5.485799090441e-4")
RMIN2 = F(LI.L.R_MIN_BOHR) ** 2
MARGIN = 0.8
INIT = {
    "F_free": ([("0", "0", "0")], [("14", "3", "-2")]),
    "A2_bound": ([("-71/20", "0", "0"), ("71/20", "0", "0")], [("1", "-3", "0"), ("-1", "3", "0")]),
    "A3_low": ([("0", "0", "0"), ("25", "0", "0"), ("0", "25", "0")], [("2", "1", "0"), ("-1", "2", "0"), ("-1", "-3", "0")]),
    "A3_high": ([("0", "0", "0"), ("71/10", "0", "0"), ("71/20", "6149/1000", "0")],
                [("3", "0", "1/2"), ("-3/2", "13/5", "0"), ("-3/2", "-13/5", "-1/2")]),
}
N_ATOMS = {"F_free": 1, "A2_bound": 2, "A3_low": 3, "A3_high": 3, "H_halfway": 1, "D_zero": 2}


class CheckError(Exception):
    pass


def lf(path):
    return hashlib.sha256(Path(path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _half_even(x):
    q = x.numerator // x.denominator
    rem = x - q
    if rem > F(1, 2) or (rem == F(1, 2) and q % 2):
        q += 1
    return q


def _end(t):
    return None if t in (finf, fninf, fnan) else F(*to_rational(t))


def _cell(v, fb):
    lo, hi = _end(v._mpi_[0]), _end(v._mpi_[1])
    if lo is None or hi is None:
        return None
    a, b = _half_even(lo * 2 ** fb), _half_even(hi * 2 ** fb)
    return a if a == b else None


def my_replay(name, steps, prec):
    """Own interval KDK. Cells, or None when not decided or the force domain is not proven."""
    iv.prec = prec
    q0, p0 = INIT[name]
    q = [[LI.c(F(x)) for x in r] for r in q0]
    p = [[LI.c(F(x)) for x in r] for r in p0]
    n = len(q)
    h, cdt = LI.c(F(20)), LI.c(F(40) / MASS)

    def acc(q):
        out = [[iv.mpf(0)] * 3 for _ in range(n)]
        for i in range(n):
            for j in range(i + 1, n):
                d = [q[j][k] - q[i][k] for k in range(3)]
                r2 = d[0] * d[0] + d[1] * d[1] + d[2] * d[2]
                lo = _end(r2._mpi_[0])
                if lo is None or lo < RMIN2:
                    return None
                g = LI.G_of_R2(r2)
                for k in range(3):
                    out[j][k] += h * g * d[k]
                    out[i][k] -= h * g * d[k]
        return out

    A = acc(q)
    for _ in range(steps):
        if A is None:
            return None
        p = [[p[a][k] + A[a][k] for k in range(3)] for a in range(n)]
        q = [[q[a][k] + p[a][k] * cdt for k in range(3)] for a in range(n)]
        A = acc(q)
        if A is None:
            return None
        p = [[p[a][k] + A[a][k] for k in range(3)] for a in range(n)]
    cells = [_cell(v, 48) for r in q for v in r] + [_cell(v, 80) for r in p for v in r]
    return None if None in cells else cells


def halfway_expected():
    q0 = F(1, 2 ** 49) - F(40) / MASS
    q1 = q0 + F(1) * (F(40) / MASS)                      # no force: half kicks are zero
    assert q1 == F(1, 2 ** 49)
    return [_half_even(q1 * 2 ** 48), 0, 0, _half_even(F(1) * 2 ** 80), 0, 0]


def expected_sets(proto, quick):
    if quick:
        return {"cold": [[3], [5]], "warm": [[3, 5]], "every": [[1, 2, 3, 4, 5]], "control": [[1]]}
    out = {}
    for w, spec in proto["workloads"].items():
        if "steps" in spec:
            a, b = spec["steps"]
            out[w] = [list(range(a, b + 1))]
        else:
            out[w] = spec["query_sets"]
    return out


def jobs():
    return [(s, p, w) for s in PHYSICAL for p in PATHS for w in ("cold", "warm", "every")] + \
           [(s, p, "control") for s in CONTROL for p in PATHS]


def _finite(x):
    return isinstance(x, (int, float)) and math.isfinite(x) and x >= 0


def _cpu(rec):
    """CPU recomputed from the build and every attempt of every query (stored totals are not read)."""
    total = 0.0
    for q in rec["queries"]:
        parts = [q["build"]] + q["attempts"]
        for part in parts:
            if not (_finite(part.get("cpu_s")) and _finite(part.get("wall_s"))):
                return None
            total += part["cpu_s"]
    return total


def check(run_dir, fast=False):
    run_dir = Path(run_dir)
    proto = json.loads((HERE / "protocol.json").read_text(encoding="utf-8"))
    proto_hash = lf(HERE / "protocol.json")
    seal_path = run_dir / "execution_seal.json"
    if not seal_path.exists():
        raise CheckError("no execution_seal.json")
    seal_hash = lf(seal_path)
    seal = json.loads(seal_path.read_text(encoding="utf-8"))
    incomplete = []
    if sorted(seal.get("source_sha256_lf", {})) != sorted(SEALED):
        raise CheckError("seal does not list the sealed sources")
    for src, h in seal["source_sha256_lf"].items():
        if lf(ROOT / src) != h:
            raise CheckError(f"source changed since the run: {src}")
    if seal.get("quick"):
        incomplete.append("quick run (not the sealed workloads)")
    if seal.get("sealed_sources_dirty"):
        incomplete.append("run started with uncommitted sealed sources")
    sets = expected_sets(proto, bool(seal.get("quick")))
    if seal.get("query_sets") != sets:
        raise CheckError("run used other query sets than the protocol")
    grid = proto["precision_grid"]

    recs = {}
    for s, p, w in jobs():
        stem = f"{s}__{p}__{w}"
        if (run_dir / f"{stem}.ERROR.txt").exists():
            incomplete.append(f"job failed: {stem}")
        f = run_dir / f"{stem}.json"
        if not f.exists():
            incomplete.append(f"job missing: {stem}")
            continue
        doc = json.loads(f.read_text(encoding="utf-8"))
        if doc.get("protocol_sha256") != proto_hash or doc.get("seal_sha256") != seal_hash:
            raise CheckError(f"{stem}: not bound to this protocol / seal")
        if (doc.get("scenario"), doc.get("path"), doc.get("workload")) != (s, p, w):
            raise CheckError(f"{stem}: file content names another job")
        rec = doc["record"]
        want = sorted({x for qs in sets[w] for x in qs})
        res = rec.get("results", {})
        if sorted(int(k) for k in res) != want or len(rec.get("queries", [])) == 0:
            incomplete.append(f"{stem}: requested steps missing")
            continue
        for k, r in res.items():
            st = r.get("status")
            if st not in STATUSES:
                raise CheckError(f"{stem} step {k}: unknown status {st}")
            if st == "DECIDED":
                c = r.get("cells")
                if r.get("bits") not in grid or not isinstance(c, list) or len(c) != 6 * N_ATOMS[s] \
                        or not all(isinstance(x, int) and -(2 ** 95) <= x < 2 ** 95 for x in c):
                    raise CheckError(f"{stem} step {k}: malformed DECIDED result")
        cpu = _cpu(rec)
        if cpu is None:
            incomplete.append(f"{stem}: cost fields missing or not finite")
        mem = doc.get("memory", {})
        if not isinstance(mem.get("peak_rss"), int):
            incomplete.append(f"{stem}: peak RSS missing")
        recs[(s, p, w)] = {"rec": rec, "cpu": cpu, "mem": mem}

    # agreement: every DECIDED cell of a scenario and step, over all paths and workloads, must be identical
    cells = {}
    for (s, p, w), d in recs.items():
        for k, r in d["rec"]["results"].items():
            if r["status"] == "DECIDED":
                key = (s, int(k))
                if key in cells and cells[key][0] != r["cells"]:
                    raise CheckError(f"{s} step {k}: {p}/{w} cells differ from {cells[key][1]}")
                cells.setdefault(key, (r["cells"], f"{p}/{w}"))

    def res(s, p, w, step):
        d = recs.get((s, p, w))
        return None if d is None else d["rec"]["results"].get(str(step))

    # controls
    hw = halfway_expected()
    for p in PATHS:
        r = res("H_halfway", p, "control", 1)
        if r and r["status"] == "DECIDED" and r["cells"] != hw:
            raise CheckError(f"H_halfway {p}: decided cells differ from the exact answer")
    if not F(0) < RMIN2:
        raise CheckError("r_min")

    # independent replay confirmation
    confirmations = []
    cold_steps = [qs[0] for qs in sets["cold"]]
    for s in PHYSICAL:
        for step in cold_steps:
            if fast and step == max(cold_steps):
                incomplete.append(f"--fast: step {step} not confirmed")
                continue
            starts = [r["bits"] for p in PATHS for r in [res(s, p, "cold", step)] if r and r["status"] == "DECIDED"]
            if not starts:
                confirmations.append({"scenario": s, "step": step, "confirmed": False, "why": "no decided result"})
                continue
            c = res(s, "C", "cold", step)
            b0 = c["bits"] if c and c["status"] == "DECIDED" else min(starts)
            i0, ok, used = grid.index(b0), False, None
            for b in grid[i0:i0 + 3]:
                mine = my_replay(s, step, b)
                if mine is not None:
                    if mine != cells[(s, step)][0]:
                        raise CheckError(f"{s} step {step}: independent replay decides other cells")
                    ok, used = True, b
                    break
            confirmations.append({"scenario": s, "step": step, "start_bits": b0, "confirmed": ok, "bits": used})
    if not confirmations or not all(c["confirmed"] for c in confirmations):
        incomplete.append("replay confirmations missing or unconfirmed")

    def complete(s, p, w):
        d = recs.get((s, p, w))
        return d is not None and d["cpu"] is not None and all(r["status"] in FINAL for r in d["rec"]["results"].values())

    def cpu(s, p, w):
        return recs[(s, p, w)]["cpu"] if complete(s, p, w) else None

    def faster(s, w, x, y):
        a, b = cpu(s, x, w), cpu(s, y, w)
        return None if a is None or b is None else a < MARGIN * b

    def lcs(s, w):
        c = {p: cpu(s, p, w) for p in PATHS if cpu(s, p, w) is not None}
        if not c:
            return []
        m = min(c.values())
        return sorted(p for p, v in c.items() if v <= m / MARGIN)

    def outcome(values):
        if any(v is None for v in values):
            return "UNDETERMINED"
        return "HOLDS" if all(values) else "FAILS"

    claims = {}
    def got(s, p, w, step, test):
        r = res(s, p, w, step)
        return None if r is None else bool(test(r))
    claims["K1_DOMAIN"] = outcome([got("D_zero", p, "control", 1, lambda r: r["status"] == "REFUSED_DOMAIN"
                                       and r.get("completed_steps") == 0) for p in PATHS])
    k2 = [got("H_halfway", p, "control", 1, lambda r: r["status"] == "DECIDED" and r.get("bits") == 64
              and r.get("cells") == hw) for p in ("B", "CX")]
    k2 += [got("H_halfway", p, "control", 1, lambda r: r["status"] == "UNDECIDED_AT_CAP") for p in ("A", "C", "CS")]
    claims["K2_HALFWAY"] = outcome(k2)

    def sig(r):
        return None if r is None else (r["status"], r.get("bits"), r.get("key"))
    k3 = []
    for s in PHYSICAL:
        for step in cold_steps:
            a = sig(res(s, "C", "cold", step))
            k3 += [a is not None and a[0] == "DECIDED" and a == sig(res(s, "CS", "cold", step)) == sig(res(s, "CS", "warm", step))]
        every = set(sets["every"][0])
        for step in sets["warm"][0]:
            if step in every:
                a = sig(res(s, "CS", "warm", step))
                k3 += [a is not None and a[0] == "DECIDED" and a == sig(res(s, "CS", "every", step))]
    claims["K3_STREAM_IDENTITY"] = outcome(k3)
    claims["K4_AGREEMENT"] = "HOLDS"
    k5 = []
    bw = recs.get(("F_free", "B", "warm"))
    if bw:
        sizes = [v["size"] for v in bw["rec"]["queries"][0]["dag"]["reachable"].values()]
        k5.append(len(set(sizes)) == 1)
    else:
        k5.append(None)
    bc = recs.get(("F_free", "B", "cold"))
    created = [q["dag"]["created_nodes"] for q in bc["rec"]["queries"]] if bc else None
    k5.append(None if created is None else all(x < y for x, y in zip(created, created[1:])))
    for w in ("cold", "warm", "every"):
        d = recs.get(("F_free", "CX", w))
        k5.append(None if d is None else all(r["status"] == "DECIDED" and r["bits"] == 64
                                             for r in d["rec"]["results"].values()))
    claims["K5_FREE"] = outcome(k5)

    W = ("cold", "warm", "every")
    preds = {}
    preds["P1"] = outcome([v for s in INTERACTING for v in
                           ([("CS" in lcs(s, "warm")) if lcs(s, "warm") else None,
                             ("CS" in lcs(s, "every")) if lcs(s, "every") else None,
                             (("C" not in lcs(s, "every")) if complete(s, "C", "every") else None)])])
    p2 = []
    for s in INTERACTING:
        f1, f2 = faster(s, "cold", "C", "CS"), faster(s, "cold", "CS", "C")
        p2.append(None if f1 is None else (not f1 and not f2))
    preds["P2"] = outcome(p2)
    p3 = []
    for s in INTERACTING:
        for w in W:
            for x in ("A", "B"):
                f = faster(s, w, x, "CS")
                p3.append(None if f is None else not f)
    preds["P3"] = outcome(p3)
    p4 = []
    for s in INTERACTING:
        for step in cold_steps:
            a, b = res(s, "A", "cold", step), res(s, "B", "cold", step)
            if a is None or b is None:
                p4.append(None)
            elif b["status"] == "DECIDED" and a["status"] == "DECIDED":
                p4.append(b["bits"] <= a["bits"])
            elif b["status"] == "DECIDED":
                p4.append(True)
            elif a["status"] == "DECIDED":
                p4.append(False)
            else:
                p4.append(None)
    preds["P4"] = outcome(p4)
    p5 = []
    for s in INTERACTING:
        for w in W:
            f1, f2 = faster(s, w, "CX", "CS"), faster(s, w, "CS", "CX")
            p5.append(None if f1 is None else (not f1 and not f2))
    preds["P5"] = outcome(p5)

    table = {}
    for s in PHYSICAL:
        table[s] = {}
        for w in W:
            table[s][w] = {"least_cost_set": lcs(s, w), "cpu_s": {p: recs[(s, p, w)]["cpu"] for p in PATHS
                                                                   if (s, p, w) in recs},
                           "complete": {p: complete(s, p, w) for p in PATHS},
                           "peak_rss": {p: recs[(s, p, w)]["mem"].get("peak_rss") for p in PATHS if (s, p, w) in recs}}
        table[s]["bits_cold"] = {p: {str(st): (res(s, p, "cold", st) or {}).get("bits") or
                                     (res(s, p, "cold", st) or {}).get("status") for st in cold_steps} for p in PATHS}
    controls = {s: {p: res(s, p, "control", 1) for p in PATHS} for s in CONTROL}
    verdict = "INCOMPLETE" if incomplete else "COMPARISON_COMPLETE"
    return {"verdict": verdict, "incomplete_reasons": incomplete, "claims": claims, "predictions": preds,
            "replay_confirmations": confirmations, "comparison": table, "controls": controls,
            "note": "No PROMISING/PASS label exists in V1; no path is promoted. Timings are EXECUTED measurements "
                    "under the disclosed concurrency, not verified performance."}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    ap.add_argument("--out")
    ap.add_argument("--fast", action="store_true")
    a = ap.parse_args(argv)
    t0, c0 = time.perf_counter(), time.process_time()
    out = check(a.run_dir, a.fast)
    out["checker_cost"] = {"wall_s": time.perf_counter() - t0, "cpu_s": time.process_time() - c0}
    text = json.dumps(out, indent=1, ensure_ascii=True)
    if a.out:
        Path(a.out).write_text(text, encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("verdict", "incomplete_reasons", "claims", "predictions", "checker_cost")},
                     indent=1, ensure_ascii=True))


if __name__ == "__main__":
    main()
