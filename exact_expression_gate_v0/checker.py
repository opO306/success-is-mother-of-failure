"""Independent checker for Exact Expression State Gate V0.

Does not import dag or campaign. Uses lang_iv only as the shared force specification (validated against
a_reference/ar2_lang2024 by the tests). Re-runs its own interval KDK at the reported precision for the
10- and 100-step checkpoints (and 1000 unless --fast), confirms the recorded grid cells, and applies the
sealed verdict rule.

    python -m exact_expression_gate_v0.checker RUN_DIR [--out VERDICT.json] [--fast]
"""

from __future__ import annotations

import argparse
import hashlib
import json
from fractions import Fraction as F
from pathlib import Path

from mpmath import iv
from mpmath.libmp import to_rational

from . import lang_iv as LI

NAMES = ["F_free", "A2_bound", "A3_low", "A3_high"]
INIT = {
    "F_free": ([("0", "0", "0")], [("14", "3", "-2")]),
    "A2_bound": ([("-71/20", "0", "0"), ("71/20", "0", "0")], [("1", "-3", "0"), ("-1", "3", "0")]),
    "A3_low": ([("0", "0", "0"), ("25", "0", "0"), ("0", "25", "0")], [("2", "1", "0"), ("-1", "2", "0"), ("-1", "-3", "0")]),
    "A3_high": ([("0", "0", "0"), ("71/10", "0", "0"), ("71/20", "6149/1000", "0")],
                [("3", "0", "1/2"), ("-3/2", "13/5", "0"), ("-3/2", "-13/5", "-1/2")]),
}
MASS = F("39.9623831237") / F("5.485799090441e-4")


class CheckError(Exception):
    pass


def _r(x):
    n, d = x.numerator, x.denominator
    q = n // d
    rem = x - q
    if rem > F(1, 2) or (rem == F(1, 2) and q % 2):
        q += 1
    return q


def _cell(v, fb):
    a = _r(F(*to_rational(v._mpi_[0])) * (1 << fb))
    b = _r(F(*to_rational(v._mpi_[1])) * (1 << fb))
    return a if a == b else None


def my_replay(name, steps, prec):
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
                g = LI.G_of_R2(d[0] * d[0] + d[1] * d[1] + d[2] * d[2])
                for k in range(3):
                    out[j][k] += h * g * d[k]
                    out[i][k] -= h * g * d[k]
        return out

    A = acc(q)
    for _ in range(steps):
        p = [[p[a][k] + A[a][k] for k in range(3)] for a in range(n)]
        q = [[q[a][k] + p[a][k] * cdt for k in range(3)] for a in range(n)]
        A = acc(q)
        p = [[p[a][k] + A[a][k] for k in range(3)] for a in range(n)]
    cells = [_cell(v, 48) for r in q for v in r] + [_cell(v, 80) for r in p for v in r]
    return None if None in cells else cells


def slope(a, b, ta, tb):
    return (b - a) / (tb - ta)


def scenario_flags(r, name):
    cps = r["checkpoints"]
    ext = r.get("extended")
    have_ext = isinstance(ext, dict) and "10000" in ext["A"]["required_bits"]
    sizeA = {int(k): v["size"] for k, v in r["A"]["reachable"].items()}
    sizeB = {int(k): v["size"] for k, v in r["B"]["reachable"].items()}
    bits = {int(k): v for k, v in r["A"]["required_bits"].items()}
    bpu = r["B"]["bytes_per_size_unit"]
    rep_last = max(cps)
    beval = r["B"]["eval"].get(str(rep_last), {})
    ctime = r["C"].get(str(rep_last), {}).get("wall_s")
    btime = r["B"]["build_s"] + beval.get("wall_s", float("inf"))
    if have_ext:
        sizeA[10000] = ext["A"]["reachable"]["10000"]["size"]
        sizeB[10000] = ext["B"]["reachable"]["10000"]["size"]
        bits[10000] = ext["A"]["required_bits"]["10000"]
        bpu = ext["B"]["bytes_per_size_unit"]
        be = ext["B"]["eval"].get("10000", {})
        btime = ext["B"]["build_s"] + be.get("wall_s", float("inf"))
        ctime = ext["C"].get("10000", {}).get("wall_s")
    last = max(sizeA)
    base = 100 if 100 in sizeA else min(sizeA)
    sA, sB = slope(sizeA[base], sizeA[last], base, last), slope(sizeB[base], sizeB[last], base, last)
    undecided = any(v == "UNDECIDED_AT_CAP" for v in bits.values())
    bslope = None if undecided else slope(bits[base], bits[last], base, last)
    flags = {
        "last_checkpoint": last,
        "size_slope_A": sA, "size_slope_B": sB,
        "optimizer_meaningful": sA > 0 and sB <= 0.5 * sA,
        "bits": bits, "bits_slope": bslope,
        "precision_wall": undecided or (bslope is not None and bslope > 0.05),
        "bytes_slope_B": bpu * sB,
        "expression_wall": bpu * sB * 1e6 > 1e9,
        "B_query_s": btime, "C_query_s": ctime,
        "replay_dominates": ctime is not None and btime >= ctime,
    }
    if name == "F_free":
        flags["free_passes"] = sizeB[last] == sizeB[min(sizeB)] and not undecided and bits[last] == bits[min(bits)]
    return flags


def check(run_dir, fast=False):
    run_dir = Path(run_dir)
    out = {"scenarios": {}, "replay_confirmations": []}
    proto = None
    for name in NAMES:
        doc = json.loads((run_dir / f"{name}.json").read_text(encoding="utf-8"))
        if proto is None:
            proto = doc["protocol"]
        elif doc["protocol"] != proto:
            raise CheckError("scenario files disagree on protocol")
        r = doc["result"]
        for path in ("B",):
            for cp, e in r[path]["eval"].items():
                if "agrees_with_A" in e and not e["agrees_with_A"]:
                    raise CheckError(f"{name}: B disagrees with A at {cp}")
        for cp, e in r["C"].items():
            if not e["agrees_with_A"]:
                raise CheckError(f"{name}: replay disagrees with A at {cp}")
        for cp in (10, 100) + (() if fast else (1000,)):
            need = r["A"]["required_bits"].get(str(cp))
            if need in (None, "UNDECIDED_AT_CAP"):
                continue
            mine = my_replay(name, cp, need)
            ok = mine is not None and mine == r["cells"][str(cp)]
            if not ok:
                # the independent replay may need one more grid step (different operation order)
                grid = proto["precision_grid"]
                nxt = grid[grid.index(need) + 1] if grid.index(need) + 1 < len(grid) else None
                mine2 = my_replay(name, cp, nxt) if nxt else None
                ok = mine2 is not None and mine2 == r["cells"][str(cp)]
                if mine2 is not None and mine2 != r["cells"][str(cp)]:
                    raise CheckError(f"{name}: independent replay decides different cells at {cp}")
            out["replay_confirmations"].append({"scenario": name, "checkpoint": cp, "bits": need, "confirmed": ok})
        out["scenarios"][name] = {"flags": scenario_flags(r, name),
                                  "intrinsic_amplification_log2": r["intrinsic_amplification_log2"],
                                  "tree_size_log2": r["A"].get("tree_size_log2"),
                                  "extended": "RUN" if isinstance(r.get("extended"), dict) else r.get("extended")}
    inter = ["A2_bound", "A3_low", "A3_high"]
    fl = {n: out["scenarios"][n]["flags"] for n in inter}
    free_ok = out["scenarios"]["F_free"]["flags"]["free_passes"]
    good = {n: f["optimizer_meaningful"] and not f["precision_wall"] and not f["expression_wall"]
            and not f["replay_dominates"] for n, f in fl.items()}
    if all(good.values()):
        verdict = "PROMISING"
    elif free_ok and not all(good.values()):
        verdict = "CONDITIONAL"
    else:
        counts = {"PRECISION_WALL": sum(f["precision_wall"] for f in fl.values()),
                  "EXPRESSION_WALL": sum(f["expression_wall"] for f in fl.values()),
                  "REPLAY_DOMINATES": sum(f["replay_dominates"] for f in fl.values())}
        verdict = max(counts, key=counts.get)
    out["verdict"] = verdict
    out["failing_flags"] = {n: [k for k in ("precision_wall", "expression_wall", "replay_dominates") if f[k]]
                            + ([] if f["optimizer_meaningful"] else ["optimizer_not_meaningful"]) for n, f in fl.items()}
    if not all(c["confirmed"] for c in out["replay_confirmations"]):
        out["verdict"] += " (WITH UNCONFIRMED CHECKPOINTS)"
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    ap.add_argument("--out")
    ap.add_argument("--fast", action="store_true")
    a = ap.parse_args(argv)
    out = check(a.run_dir, a.fast)
    out["file_sha256"] = {n: hashlib.sha256((Path(a.run_dir) / f"{n}.json").read_bytes()).hexdigest() for n in NAMES}
    text = json.dumps(out, indent=1, ensure_ascii=True)
    if a.out:
        Path(a.out).write_text(text, encoding="utf-8")
    print(json.dumps({"verdict": out["verdict"], "failing_flags": out["failing_flags"]}, ensure_ascii=True, indent=1))


if __name__ == "__main__":
    main()
