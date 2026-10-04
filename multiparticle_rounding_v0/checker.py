"""Independent checker for Multiparticle Rounding Gate V0 (standard library only;
does not import the producer). Re-implements the three laws for the synthetic panel,
re-derives the exhaustive statistics, and recomputes every physics-panel metric from
the recorded outputs.

    python -m multiparticle_rounding_v0.checker RESULTS.json [--out SUMMARY.json] [--skip-exhaustive]
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from fractions import Fraction as F
from pathlib import Path


class CheckError(Exception):
    pass


def _round(x):
    n, d = x.numerator, x.denominator
    q = n // d
    r = x - q
    if r > F(1, 2) or (r == F(1, 2) and q % 2 == 1):
        q += 1
    return q


def _tot(n, pairs):
    a = [F(0)] * n
    for (i, j), A in pairs.items():
        a[j] += A
        a[i] -= A
    return a


def _P(n, pairs):
    dp = [0] * n
    for (i, j), A in pairs.items():
        J = _round(A)
        dp[j] += J
        dp[i] -= J
    return dp


def _T(n, pairs):
    return [_round(x) for x in _tot(n, pairs)]


def _C(n, pairs):
    a = _tot(n, pairs)
    t = [_round(x) for x in a]
    D = sum(t)
    if D == 0:
        return t
    s = 1 if D > 0 else -1
    e = [s * (ti - ai) for ti, ai in zip(t, a)]
    k = abs(D)
    ranked = sorted(e, reverse=True)
    if k < n and ranked[k] == ranked[k - 1]:
        return "STOP"
    cut = ranked[k - 1]
    return [ti - s if ei >= cut else ti for ti, ei in zip(t, e)]


LAWS = {"P": _P, "T": _T, "C": _C}


def _pairs(rec):
    return {tuple(int(v) for v in k.split(",")): F(A) for k, A in rec["pairs"].items()}


def check_synthetic(res):
    for name, rec in res["synthetic"].items():
        n, pairs = rec["n"], _pairs(rec)
        for law, f in LAWS.items():
            mine = f(n, pairs)
            got = rec[law]["result"]
            if mine != got:
                raise CheckError(f"{name}/{law}: recomputed {mine} != recorded {got}")
        for law, m in rec["perm"]["mismatches"].items():
            if m:
                raise CheckError(f"{name}/{law}: permutation mismatch recorded")


def recompute_exhaustive(n, plist, values):
    stats = {k: {"cases": 0, "stop": 0, "nonconserving": 0, "max_abs_error": F(0), "err_gt_half": 0} for k in LAWS}
    for combo in itertools.product(values, repeat=len(plist)):
        pairs = dict(zip(plist, combo))
        a = _tot(n, pairs)
        for k, f in LAWS.items():
            s = stats[k]
            s["cases"] += 1
            r = f(n, pairs)
            if r == "STOP":
                s["stop"] += 1
                continue
            if sum(r) != 0:
                s["nonconserving"] += 1
            e = max(abs(x - y) for x, y in zip(r, a))
            s["max_abs_error"] = max(s["max_abs_error"], e)
            if e > F(1, 2):
                s["err_gt_half"] += 1
    for s in stats.values():
        s["max_abs_error"] = str(s["max_abs_error"])
    return stats


def physics_metrics(row):
    n = row["n"]
    exact = [[F(c) for c in r] for r in row["exact_totals_u"]]
    out = {}
    for law in ("P", "T", "C"):
        v = row.get(law)
        if isinstance(v, str):
            out[law] = {"status": v}
            continue
        sums = [sum(v[i][k] for i in range(n)) for k in range(3)]
        err = max(abs(v[i][k] - exact[i][k]) for i in range(n) for k in range(3))
        out[law] = {"momentum_sum": sums, "conserving": sums == [0, 0, 0], "max_abs_error_u": float(err)}
    if "permutation" in row:
        out["permutation_mismatches"] = row["permutation"]["mismatches"]
    out["translation_same"] = row["translation_same"]
    if "T_grouping" in row:
        out["T_grouping_same"] = all(g["same"] for g in row["T_grouping"].values())
    # T must be the rounding of the exact total (|T - a| <= 1/2 up to the 512-bit midpoint slack)
    if not isinstance(row.get("T"), str):
        slack = F(1, 10**30)
        for i in range(n):
            for k in range(3):
                if abs(row["T"][i][k] - exact[i][k]) > F(1, 2) + slack:
                    raise CheckError(f"{row['name']}: T is not a rounding of the exact total")
    return out


def check(res, skip_exhaustive=False):
    if res["protocol"]["gate"] != "Multiparticle Rounding Gate V0":
        raise CheckError("wrong protocol")
    check_synthetic(res)
    summary = {"quick": res["seal"]["quick"]}
    if not skip_exhaustive:
        if res["seal"]["quick"]:
            v3, v4 = [F(k, 10) for k in range(-3, 4)], [F(k, 5) for k in range(-1, 2)]
        else:
            v3, v4 = [F(k, 10) for k in range(-15, 16)], [F(k, 5) for k in range(-4, 5)]
        e3 = recompute_exhaustive(3, [(0, 1), (0, 2), (1, 2)], v3)
        e4 = recompute_exhaustive(4, [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)], v4)
        if e3 != res["exhaustive_N3"] or e4 != res["exhaustive_N4"]:
            raise CheckError("exhaustive statistics do not recompute")
    summary["exhaustive_N3"] = res["exhaustive_N3"]
    summary["exhaustive_N4"] = res["exhaustive_N4"]
    n2 = res["physics_N2"]
    summary["N2_equal_to_C1B1"] = {law: all(r[f"{law}_equal"] for r in n2) for law in ("P", "T", "C")}
    summary["clusters"] = {k: physics_metrics(v) for k, v in res["physics_clusters"].items()}
    ff = res["far_field"]
    m = physics_metrics(ff)
    exact_c = [F(c) for c in ff["exact_totals_u"][0]]
    m["d"] = ff["d"]
    m["center_exact_total_u"] = [float(x) for x in exact_c]
    for law in ("P", "T", "C"):
        v = ff.get(law)
        if not isinstance(v, str):
            m[law]["center_dp_u"] = v[0]
            m[law]["center_lost_u"] = [float(exact_c[k] - v[0][k]) for k in range(3)]
    summary["far_field"] = m
    return summary


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("results")
    ap.add_argument("--out")
    ap.add_argument("--skip-exhaustive", action="store_true")
    a = ap.parse_args(argv)
    raw = Path(a.results).read_bytes()
    out = check(json.loads(raw), a.skip_exhaustive)
    out["results_sha256"] = hashlib.sha256(raw).hexdigest()
    text = json.dumps(out, indent=1)
    if a.out:
        Path(a.out).write_text(text, encoding="utf-8")
    print(text[:4000])


if __name__ == "__main__":
    main()
