"""Run the sealed Multiparticle Residual / Carry Gate V1.

    python -m multiparticle_residual_gate_v1.campaign --out runs/multiparticle_residual_gate_v1_<date> [--quick]
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import itertools
import json
import platform
import subprocess
import time
from fractions import Fraction as Q
from pathlib import Path

from . import ledger as LG

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SOURCES = ["__init__.py", "ledger.py", "campaign.py", "protocol.json"]
S = str


def snap(s: LG.State):
    return {"P": s.P, "r": [S(x) for x in s.r], "p": [S(x) for x in s.p()],
            "ext": {k: S(v) for k, v in s.ext.items()}}


def run_both(n, entries, p0=None, grouping="forward"):
    p0 = p0 or [Q(0)] * n
    u = LG.apply_U(LG.State(p0), entries)
    l = LG.apply_L(LG.State(p0), entries, grouping)
    return u, l


def enc_entries(entries):
    return [[e[0], *[S(x) if isinstance(x, Q) else x for x in e[1:]]] for e in entries]


# ------------------------------------------------------------------ named cases T1-T7
def far_ar_standin():
    """x-components of pair impulse midpoints (512-bit enclosures) for the Gate V0 far-field geometry, in coarse units."""
    import multiparticle_rounding_v0.physics as ph
    v0 = json.loads(gzip.decompress((ROOT / "docs/active/multiparticle_rounding_v0/results.json.gz").read_bytes()))
    pos = [tuple(Q(c) for c in r) for r in v0["far_field"]["positions"]]
    entries = []
    for i in range(len(pos)):
        for j in range(i + 1, len(pos)):
            lo, hi = ph.pair_enclosure(ph.rel(pos[i], pos[j]), 512)[0]
            entries.append(("pair", i, j, (lo + hi) / 2 / ph.UNIT))
    return len(pos), entries, pos


def named_cases():
    c = {}
    c["T1_repeat_0.4x3"] = (4, [("pair", 1, 0, Q(2, 5)), ("pair", 2, 0, Q(2, 5)), ("pair", 3, 0, Q(2, 5))])
    c["T2_cancel"] = (3, [("pair", 1, 0, Q(2, 5)), ("pair", 2, 0, Q(-2, 5))])
    c["T3_partial"] = (3, [("pair", 1, 0, Q(7, 10)), ("pair", 2, 0, Q(-2, 5))])
    c["T4_strong_opposite"] = (3, [("pair", 1, 0, Q(2, 5)), ("pair", 2, 0, Q(-7, 10))])
    c["T5_closed_pair"] = (2, [("pair", 1, 0, Q(2, 5))])
    c["T6_wall_body"] = (3, [("pair", 0, 1, Q(3, 5)), ("pair", 1, 2, Q(3, 5))])
    c["T6_wall_external"] = (2, [("pair", 0, 1, Q(3, 5)), ("ext", 1, Q(-3, 5), "wall")])
    c["T7_split"] = (3, [("pair", 0, 1, Q(2, 5)), ("pair", 0, 2, Q(2, 5))])
    for K in range(1, 21):
        c[f"T7_many_K{K}"] = (K + 1, [("pair", j, 0, Q(1, 10)) for j in range(1, K + 1)])
    n, e, _ = far_ar_standin()
    c["T7_far_Ar_standin"] = (n, e)
    return c


def v0_laws(n, entries):
    """P/T/C of Gate V0 when the case is a pure closed-pair set with one entry per pair."""
    from multiparticle_rounding_v0 import laws as V0
    if any(e[0] != "pair" for e in entries):
        return None
    pairs = {}
    for _, i, j, d in entries:
        if (i, j) in pairs:
            return None
        pairs[(i, j)] = Q(d)
    return {k: (list(f(n, pairs)) if f(n, pairs) != "STOP" else "STOP") for k, f in V0.LAWS.items()}


def orders(entries):
    if len(entries) <= 8:
        return list(itertools.permutations(entries))
    out = []
    for k in range(12):
        rot = entries[k:] + entries[:k]
        out += [rot, rot[::-1]]
    return out


def named_panel():
    res = {}
    for name, (n, entries) in named_cases().items():
        u, l = run_both(n, entries)
        row = {"n": n, "entries": enc_entries(entries), "U": snap(u), "L": snap(l), "V0": v0_laws(n, entries)}
        # T8 order / grouping
        pu, pl = u.p(), l.p()
        bad_u = bad_l = 0
        ords = orders(entries)
        for o in ords:
            uu, ll = run_both(n, list(o))
            bad_u += uu.p() != pu
            bad_l += ll.p() != pl
        bad_g = sum(LG.apply_L(LG.State([Q(0)] * n), entries, g).p() != pl for g in ("reverse", "tree"))
        row["T8"] = {"orders": len(ords), "U_mismatch": bad_u, "L_mismatch": bad_l, "L_grouping_mismatch": bad_g}
        # T9 relabel
        if n <= 4:
            mism = 0
            perms = list(itertools.permutations(range(n)))
            for perm in perms:
                pe = [("pair", perm[e[1]], perm[e[2]], e[3]) if e[0] == "pair" else ("ext", perm[e[1]], e[2], e[3])
                      for e in entries]
                uu, ll = run_both(n, pe)
                mism += any(uu.p()[perm[i]] != pu[i] for i in range(n))
                mism += any(ll.p()[perm[i]] != pl[i] for i in range(n))
            row["T9"] = {"perms": len(perms), "mismatch": mism}
        res[name] = row
    return res


# ------------------------------------------------------------------ T11 drift
def t11():
    s = LG.State([Q(0)])
    s.P, s.r = [1], [Q(1, 5)]
    c = Q(1, 2)
    out = {"P": 1, "r": "1/5", "c": "1/2",
           "grid_U_L": LG.drift_grid([0], s, c)[0],
           "grid_Ponly": LG.drift_grid([0], s, c, P_only=True)[0],
           "exact_U_L": S(LG.drift_exact([Q(0)], s, c)[0]),
           "exact_Ponly": S(LG.drift_exact([Q(0)], s, c, P_only=True)[0])}
    xg, xe, xgp = [0], [Q(0)], [0]
    for _ in range(1000):
        xg = LG.drift_grid(xg, s, c)
        xe = LG.drift_exact(xe, s, c)
        xgp = LG.drift_grid(xgp, s, c, P_only=True)
    out["constant_velocity_1000_steps"] = {"grid_P_plus_r": xg[0], "exact": S(xe[0]), "grid_Ponly": xgp[0],
                                           "reference": S(Q(6, 5) * c * 1000)}
    return out


# ------------------------------------------------------------------ T12 long run
def t12_entries(k):
    return [("pair", 0, 1, Q((7 * k) % 11 - 5, 10)), ("pair", 0, 2, Q((5 * k) % 13 - 6, 20)),
            ("pair", 1, 2, Q((3 * k) % 7 - 3, 3))]


def t12(steps):
    p0 = [Q(1, 3), Q(-1, 7), Q(-4, 21)]
    c = Q(1, 3)
    out = {}
    for name, apply in (("U", LG.apply_U), ("L", LG.apply_L)):
        s = LG.State(p0)
        xg, xe = [0, 0, 0], [Q(0)] * 3
        maxr, maxbits = Q(0), 0
        checkpoints = []
        t0 = time.perf_counter()
        for k in range(steps):
            s = apply(s, t12_entries(k))
            xg = LG.drift_grid(xg, s, c)
            xe = LG.drift_exact(xe, s, c)
            for r in s.r:
                maxr = max(maxr, abs(r))
                maxbits = max(maxbits, r.numerator.bit_length() + r.denominator.bit_length())
            if (k + 1) % 1000 == 0:
                checkpoints.append({"step": k + 1, "p": [S(x) for x in s.p()], "x_grid": xg, "x_exact": [S(x) for x in xe]})
        out[name] = {"final": snap(s), "x_grid": xg, "x_exact": [S(x) for x in xe], "max_abs_r": S(maxr),
                     "max_r_bits": maxbits, "checkpoints": checkpoints, "wall_s": time.perf_counter() - t0}
    out["p0"] = [S(x) for x in p0]
    out["c"] = S(c)
    out["steps"] = steps
    return out


def t12_adversarial(steps):
    out = {}
    for name, apply in (("U", LG.apply_U), ("L", LG.apply_L)):
        s = LG.State([Q(0), Q(0)])
        bits = []
        for k in range(steps):
            s = apply(s, [("pair", 0, 1, Q((-1) ** k, k + 2))])
            if (k + 1) % 250 == 0:
                bits.append({"step": k + 1, "r_bits": max(r.numerator.bit_length() + r.denominator.bit_length() for r in s.r)})
        out[name] = {"final_p": [S(x) for x in s.p()], "bits": bits}
    return out


# ------------------------------------------------------------------ T13/T14 exhaustive + cost
def exhaustive(n, plist, values):
    from multiparticle_rounding_v0 import laws as V0
    stats = {k: {"cases": 0, "nonconserving": 0, "not_exact": 0, "stop": 0} for k in ("U", "L")}
    times = {k: 0.0 for k in ("U", "L", "P", "T", "C")}
    for combo in itertools.product(values, repeat=len(plist)):
        entries = [("pair", i, j, A) for (i, j), A in zip(plist, combo)]
        exact = [Q(0)] * n
        for _, i, j, A in entries:
            exact[j] += A
            exact[i] -= A
        for name, apply in (("U", LG.apply_U), ("L", LG.apply_L)):
            t0 = time.perf_counter()
            s = apply(LG.State([Q(0)] * n), entries)
            times[name] += time.perf_counter() - t0
            p = s.p()
            st = stats[name]
            st["cases"] += 1
            st["nonconserving"] += sum(p) != 0
            st["not_exact"] += p != exact
        pairs = dict(zip(plist, combo))
        for name, f in V0.LAWS.items():
            t0 = time.perf_counter()
            f(n, pairs)
            times[name] += time.perf_counter() - t0
    return stats, times


# ------------------------------------------------------------------ physical realization
def realization(ks):
    import a_reference.c1b1_two_atom as C
    from a_numeric.profiles import FixedPoint
    import multiparticle_rounding_v0.physics as ph
    n, _, pos = far_ar_standin()
    v0 = json.loads(gzip.decompress((ROOT / "docs/active/multiparticle_rounding_v0/results.json.gz").read_bytes()))
    exact_center_x = Q(v0["far_field"]["exact_totals_u"][0][0])
    out = {"exact_center_x_coarse_u_512bit_midpoint": S(exact_center_x), "k": {}}
    for k in ks:
        prof = FixedPoint(96 + k, 80 + k)
        entries, nonzero = [], 0
        Pfine = [0] * n
        for i in range(n):
            for j in range(i + 1, n):
                J = C.impulse(ph.rel(pos[i], pos[j]), ph.KICK, prof)[0]
                nonzero += J != 0
                Pfine[j] += J
                Pfine[i] -= J
                entries.append(("pair", i, j, Q(J, 1 << k)))
        s = LG.apply_U(LG.State([Q(0)] * n), entries)
        equal = all(s.p()[i] == Q(Pfine[i], 1 << k) for i in range(n))
        center = s.p()[0]
        out["k"][str(k)] = {"center_p_coarse_u": S(center), "center_loss_coarse_u": float(exact_center_x - center),
                            "equals_P_on_finer_grid": equal, "pairs_nonzero_fine": nonzero,
                            "pairs_total": n * (n - 1) // 2, "momentum_sum": S(sum(s.p())),
                            "residual_bits_bound": k}
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--quick", action="store_true")
    a = ap.parse_args(argv)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=HERE).stdout.strip()
    seal = {"quick": a.quick, "git_head_at_start": head, "python": platform.python_version(),
            "source_sha256": {s: hashlib.sha256((HERE / s).read_bytes()).hexdigest() for s in SOURCES}}
    (out / "execution_seal.json").write_text(json.dumps(seal, indent=1), encoding="utf-8")
    res = {"seal": seal, "protocol": json.loads((HERE / "protocol.json").read_text(encoding="utf-8"))}
    t0 = time.perf_counter()
    print("named T1-T9", flush=True)
    res["named"] = named_panel()
    print("T11", flush=True)
    res["T11"] = t11()
    print("T12", flush=True)
    res["T12"] = t12(200 if a.quick else 10000)
    res["T12_adversarial"] = t12_adversarial(250 if a.quick else 2000)
    print("T13/T14", flush=True)
    v3 = [Q(k, 10) for k in range(-15, 16)] if not a.quick else [Q(k, 10) for k in range(-2, 3)]
    v4 = [Q(k, 5) for k in range(-4, 5)] if not a.quick else [Q(k, 5) for k in range(-1, 2)]
    s3, t3 = exhaustive(3, [(0, 1), (0, 2), (1, 2)], v3)
    s4, t4 = exhaustive(4, [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)], v4)
    res["T13"] = {"N3": s3, "N4": s4}
    res["T14"] = {"runtime_N3_s": t3, "runtime_N4_s": t4, "state_values_per_atom": 2, "per_pair_state": 0}
    print("realization", flush=True)
    res["realization"] = realization([8] if a.quick else [8, 16, 32])
    res["wall_s"] = time.perf_counter() - t0
    (out / "results.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print("wrote", out / "results.json", round(res["wall_s"], 1), "s", flush=True)


if __name__ == "__main__":
    main()
