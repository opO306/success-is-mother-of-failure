"""Run the sealed Multiparticle Rounding Gate V0 panels.

    python -m multiparticle_rounding_v0.campaign --out runs/multiparticle_rounding_v0_<date> [--quick]
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import platform
import subprocess
import time
from fractions import Fraction as Q
from pathlib import Path

from . import laws, physics as ph

HERE = Path(__file__).resolve().parent
SOURCES = ["__init__.py", "laws.py", "physics.py", "campaign.py", "protocol.json"]


def fr(x):
    return str(x)


# ------------------------------------------------------------------ synthetic panel
def synthetic_cases():
    c = {}
    c["S_collective"] = (4, {(1, 0): Q(2, 5), (2, 0): Q(2, 5), (3, 0): Q(2, 5)})
    c["S_split"] = (3, {(0, 1): Q(2, 5), (0, 2): Q(2, 5)})
    c["S_pair"] = (2, {(0, 1): Q(3, 5)})
    c["S_ties_half"] = (2, {(0, 1): Q(1, 2)})
    c["S_ties_three_halves"] = (3, {(0, 1): Q(3, 2), (0, 2): Q(-1, 2)})
    for K in range(1, 21):
        c[f"S_many_K{K}"] = (K + 1, {(j, 0): Q(1, 10) for j in range(1, K + 1)})
    return c


def eval_case(n, pairs):
    a = laws.totals(n, pairs)
    row = {"n": n, "pairs": {f"{i},{j}": fr(A) for (i, j), A in pairs.items()},
           "exact_totals": [fr(x) for x in a]}
    for name, f in laws.LAWS.items():
        r = f(n, pairs)
        if r == "STOP":
            row[name] = {"result": "STOP"}
        else:
            row[name] = {"result": list(r), "sum": sum(r),
                         "max_abs_error": fr(max(abs(ri - ai) for ri, ai in zip(r, a)))}
    return row


def perm_check(n, pairs):
    """Relabel atoms with every permutation (n <= 4) and check outputs permute with labels."""
    base = {name: f(n, pairs) for name, f in laws.LAWS.items()}
    bad = {name: 0 for name in laws.LAWS}
    perms = list(itertools.permutations(range(n))) if n <= 4 else [tuple(range(1, n)) + (0,)]
    for p in perms:
        q = {(p[i], p[j]): A for (i, j), A in pairs.items()}
        for name, f in laws.LAWS.items():
            r = f(n, q)
            b = base[name]
            if (r == "STOP") != (b == "STOP"):
                bad[name] += 1
            elif r != "STOP" and any(r[p[i]] != b[i] for i in range(n)):
                bad[name] += 1
    return {"permutations": len(perms), "mismatches": bad}


def exhaustive(n, pair_list, values):
    stats = {name: {"cases": 0, "stop": 0, "nonconserving": 0, "max_abs_error": Q(0),
                    "err_gt_half": 0} for name in laws.LAWS}
    pairs_template = pair_list
    for combo in itertools.product(values, repeat=len(pair_list)):
        pairs = dict(zip(pairs_template, combo))
        a = laws.totals(n, pairs)
        for name, f in laws.LAWS.items():
            s = stats[name]
            s["cases"] += 1
            r = f(n, pairs)
            if r == "STOP":
                s["stop"] += 1
                continue
            if sum(r) != 0:
                s["nonconserving"] += 1
            e = max(abs(ri - ai) for ri, ai in zip(r, a))
            if e > s["max_abs_error"]:
                s["max_abs_error"] = e
            if e > Q(1, 2):
                s["err_gt_half"] += 1
    for s in stats.values():
        s["max_abs_error"] = fr(s["max_abs_error"])
    return stats


# ------------------------------------------------------------------ physics panel
def configs():
    g = ph.on_grid
    s3, s23 = Q(1732050807568877, 10**15), Q(816496580927726, 10**15)  # only to place points; then grid-rounded
    cfg = {}
    cfg["triangle_7.0"] = [(Q(0), Q(0), Q(0)), (Q(7), Q(0), Q(0)), (g(Q(7, 2)), g(Q(7, 2) * s3), Q(0))]
    cfg["chain_7.5"] = [(Q(0), Q(0), Q(0)), (Q(15, 2), Q(0), Q(0)), (Q(15), Q(0), Q(0))]
    cfg["square_7.2"] = [(Q(0), Q(0), Q(0)), (Q(36, 5), Q(0), Q(0)), (Q(36, 5), Q(36, 5), Q(0)), (Q(0), Q(36, 5), Q(0))]
    a = Q(7)
    cfg["tetrahedron_7.0"] = [(Q(0), Q(0), Q(0)), (a, Q(0), Q(0)), (g(a / 2), g(a / 2 * s3), Q(0)),
                              (g(a / 2), g(a / 2 / s3), g(a * s23))]
    return cfg


N2_R = [Q(13, 2), Q(71, 10), Q(8), Q(10), Q(20), Q(50)]
N2_DIRS = [(3, 1, 2), (1, -2, 2), (2, 2, -1), (-1, 3, 1), (4, -1, -1), (1, 1, 1)]
CAP_DIRS = [(1, 0, 0), (1, 1, 0), (1, -1, 0), (1, 0, 1), (1, 0, -1), (2, 1, 1), (2, -1, 1), (2, 1, -1)]


def far_field_distance(max_d=200000):
    d = 100
    while d <= max_d:
        ok = True
        for v in CAP_DIRS:
            enc = ph.pair_enclosure(ph.unit_scaled(v, d), 256)
            if any(max(abs(lo), abs(hi)) / ph.UNIT >= Q(1, 2) for lo, hi in enc):
                ok = False
                break
        if ok:
            return d
        d += 100
    raise RuntimeError("no far-field distance found")


def physics_row(name, pos, perms=True):
    t0 = time.perf_counter()
    n = len(pos)
    out = {"name": name, "n": n, "positions": [[fr(c) for c in r] for r in pos]}
    P = ph.law_P(pos)
    out["P"] = [list(x) for x in P]
    try:
        T, MT, _ = ph.law_T(pos)
        out["T"], out["T_bits"] = [list(x) for x in T], MT
        groupings = {}
        for gname in ("reverse", "tree"):
            Tg, Mg, _ = ph.law_T(pos, gname)
            groupings[gname] = {"same": Tg == T, "bits": Mg}
        out["T_grouping"] = groupings
    except ph.Refused as e:
        out["T"] = "REFUSED"
        out["T_reason"] = str(e)
    Cr, MC = ph.law_C(pos)
    out["C"] = Cr if isinstance(Cr, str) else [list(x) for x in Cr]
    out["exact_totals_u"] = [[fr(c) for c in r] for r in ph.high_precision_totals(pos)]
    # translation
    shift = (Q(3), Q(-2), Q(5))
    pos_t = [tuple(a + b for a, b in zip(r, shift)) for r in pos]
    out["translation_same"] = {"P": ph.law_P(pos_t) == P}
    if out["T"] != "REFUSED":
        out["translation_same"]["T"] = ph.law_T(pos_t)[0] == T
    # permutations
    if perms:
        plist = list(itertools.permutations(range(n))) if n <= 4 else \
            [tuple((i + s) % n for i in range(n)) for s in range(n)] + [tuple(range(n))[::-1]]
        mism = {"P": 0, "T": 0, "C": 0}
        for p in plist:
            q = [None] * n
            for i in range(n):
                q[p[i]] = pos[i]
            Pq = ph.law_P(q)
            if any(Pq[p[i]] != P[i] for i in range(n)):
                mism["P"] += 1
            if out["T"] != "REFUSED":
                Tq = ph.law_T(q)[0]
                if any(Tq[p[i]] != T[i] for i in range(n)):
                    mism["T"] += 1
            Cq = ph.law_C(q)[0]
            if isinstance(Cq, str) or isinstance(Cr, str):
                if isinstance(Cq, str) != isinstance(Cr, str):
                    mism["C"] += 1
            elif any(Cq[p[i]] != Cr[i] for i in range(n)):
                mism["C"] += 1
        out["permutation"] = {"count": len(plist), "mismatches": mism}
    out["wall_s"] = time.perf_counter() - t0
    return out


def n2_rows():
    rows = []
    for R, v in zip(N2_R, N2_DIRS):
        r1 = ph.unit_scaled(v, R)
        pos = [(Q(0), Q(0), Q(0)), r1]
        J = ph.C.impulse(ph.rel(pos[0], pos[1]), ph.KICK, ph.MOM)
        P = ph.law_P(pos)
        T, _, _ = ph.law_T(pos)
        Cr, _ = ph.law_C(pos)
        ref = [tuple(-x for x in J), tuple(J)]
        rows.append({"R": fr(R), "dir": v, "c1b1_J": list(J), "P_equal": list(P) == ref,
                     "T_equal": list(T) == ref, "C_equal": (not isinstance(Cr, str)) and list(Cr) == ref})
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--quick", action="store_true")
    a = ap.parse_args(argv)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=HERE).stdout.strip()
    seal = {"quick": a.quick, "git_head_at_start": head,
            "source_sha256": {s: hashlib.sha256((HERE / s).read_bytes()).hexdigest() for s in SOURCES},
            "python": platform.python_version()}
    (out / "execution_seal.json").write_text(json.dumps(seal, indent=1), encoding="utf-8")
    res = {"seal": seal, "protocol": json.loads((HERE / "protocol.json").read_text(encoding="utf-8"))}
    print("synthetic named cases", flush=True)
    res["synthetic"] = {k: {**eval_case(*v), "perm": perm_check(*v)} for k, v in synthetic_cases().items()}
    vals3 = [Q(k, 10) for k in range(-15, 16)]
    vals4 = [Q(k, 5) for k in range(-4, 5)]
    if a.quick:
        vals3, vals4 = [Q(k, 10) for k in range(-3, 4)], [Q(k, 5) for k in range(-1, 2)]
    print("exhaustive N3", flush=True)
    res["exhaustive_N3"] = exhaustive(3, [(0, 1), (0, 2), (1, 2)], vals3)
    print("exhaustive N4", flush=True)
    res["exhaustive_N4"] = exhaustive(4, [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)], vals4)
    print("physics N2", flush=True)
    res["physics_N2"] = n2_rows()
    res["physics_clusters"] = {}
    for name, pos in configs().items():
        print("physics", name, flush=True)
        res["physics_clusters"][name] = physics_row(name, pos)
    print("far field distance", flush=True)
    d = 2000 if a.quick else far_field_distance()
    cap = [(Q(0), Q(0), Q(0))] + [ph.unit_scaled(v, d) for v in CAP_DIRS]
    print("far field", d, flush=True)
    row = physics_row(f"far_field_d{d}", cap, perms=not a.quick)
    row["d"] = d
    res["far_field"] = row
    (out / "results.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print("wrote", out / "results.json", flush=True)


if __name__ == "__main__":
    main()
