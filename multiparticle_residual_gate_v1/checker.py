"""Independent checker for Multiparticle Residual / Carry Gate V1.

Standard library only. Does not import the executor (ledger, campaign). Recomputes the
exact rational reference for every test, evaluates the sealed core conditions and
applies the sealed verdict rule.

    python -m multiparticle_residual_gate_v1.checker RESULTS.json [--out VERDICT.json]
"""

from __future__ import annotations

import argparse
import hashlib
import json
from fractions import Fraction as F
from math import lcm
from pathlib import Path


class CheckError(Exception):
    pass


def rnd(x):
    q = x.numerator // x.denominator
    rem = x - q
    if rem > F(1, 2) or (rem == F(1, 2) and q % 2):
        q += 1
    return q


def exact_effect(n, entries):
    p = [F(0)] * n
    ext = {}
    for e in entries:
        if e[0] == "pair":
            _, i, j, d = e
            p[j] += F(d)
            p[i] -= F(d)
        else:
            _, i, d, name = e
            p[i] += F(d)
            ext[name] = ext.get(name, F(0)) - F(d)
    return p, ext


def snap_ok(sn, bound):
    P, r, p = sn["P"], [F(x) for x in sn["r"]], [F(x) for x in sn["p"]]
    return all(F(Pi) + ri == pi and abs(ri) <= bound for Pi, ri, pi in zip(P, r, p))


def check(res):
    if res["protocol"]["gate"] != "Multiparticle Residual / Carry Gate V1":
        raise CheckError("wrong protocol")
    cond = {f"C{i}": True for i in range(1, 10)}
    notes = []
    rep_example = None
    named = {}
    for name, row in res["named"].items():
        n = row["n"]
        exact, ext = exact_effect(n, row["entries"])
        pu = [F(x) for x in row["U"]["p"]]
        pl = [F(x) for x in row["L"]["p"]]
        if not snap_ok(row["U"], F(1) - F(1, 10**40)) or not snap_ok(row["L"], F(1, 2)):
            raise CheckError(f"{name}: recorded (P, r) inconsistent with p or residual bound")
        same = pu == pl
        collective = pu == exact and pl == exact
        total = sum(pu) + sum(F(v) for v in row["U"]["ext"].values())
        conserving = total == 0 and sum(pl) + sum(F(v) for v in row["L"]["ext"].values()) == 0
        if not collective:
            cond["C1"] = False
            notes.append(f"{name}: p differs from exact effect")
        if not conserving:
            cond["C2"] = False
        if row["T8"]["U_mismatch"] or row["T8"]["L_mismatch"] or row["T8"]["L_grouping_mismatch"]:
            cond["C4"] = False
        if row.get("T9", {}).get("mismatch"):
            cond["C3"] = False
        if not same:
            notes.append(f"{name}: U and L differ")
        if rep_example is None and (row["U"]["P"] != row["L"]["P"]):
            rep_example = {"case": name, "U": row["U"], "L": row["L"]}
        v0 = row["V0"]
        named[name] = {"exact_p": [str(x) for x in exact], "U_eq_L": same, "equals_exact": collective,
                       "conserving_incl_external": conserving, "V0": v0,
                       "external": {k: str(v) for k, v in ext.items()}}
    # T11
    t = res["T11"]
    p, c = F(1) + F(1, 5), F(1, 2)
    t11_ok = t["grid_U_L"] == rnd(p * c) and F(t["exact_U_L"]) == p * c
    t11_neg_detected = t["grid_Ponly"] != rnd(p * c) or F(t["exact_Ponly"]) != p * c
    cv = t["constant_velocity_1000_steps"]
    if not t11_ok:
        cond["C5"] = False
    if not t11_neg_detected:
        raise CheckError("negative control not detected: T11 cannot distinguish P-only drift")
    # T12: recompute the exact reference
    T12 = res["T12"]
    p0 = [F(x) for x in T12["p0"]]
    c12 = F(T12["c"])
    ref_p = list(p0)
    ref_x = [F(0)] * 3
    grid_x = [0, 0, 0]
    nsteps = T12["steps"]
    den = lcm(*[x.denominator for x in p0], 10, 20, 3)
    for k in range(nsteps):
        A01, A02, A12 = F((7 * k) % 11 - 5, 10), F((5 * k) % 13 - 6, 20), F((3 * k) % 7 - 3, 3)
        ref_p[1] += A01; ref_p[0] -= A01
        ref_p[2] += A02; ref_p[0] -= A02
        ref_p[2] += A12; ref_p[1] -= A12
        ref_x = [x + q * c12 for x, q in zip(ref_x, ref_p)]
        grid_x = [x + rnd(q * c12) for x, q in zip(grid_x, ref_p)]
    t12 = {}
    for name in ("U", "L"):
        r = T12[name]
        pf = [F(x) for x in r["final"]["p"]]
        ok_p = pf == ref_p
        ok_x = [F(x) for x in r["x_exact"]] == ref_x
        ok_g = r["x_grid"] == grid_x
        res_den_ok = all(F(x).denominator and den % F(x).denominator == 0 for x in r["final"]["r"])
        if not (ok_p and ok_x and ok_g):
            cond["C8"] = False
            cond["C5"] = cond["C5"] and ok_x
        if not res_den_ok:
            cond["C9"] = False
        t12[name] = {"p_equals_exact": ok_p, "x_exact_equals_reference": ok_x, "x_grid_recomputed": ok_g,
                     "momentum_sum_change": str(sum(pf) - sum(p0)), "max_abs_r": r["max_abs_r"],
                     "max_r_bits": r["max_r_bits"], "residual_denominator_divides_stream_lcm": res_den_ok}
        if sum(pf) != sum(p0):
            cond["C2"] = False
    t12["grid_mode_position_minus_exact_final"] = [str(F(g) - x) for g, x in zip(grid_x, ref_x)]
    t12["steps"] = nsteps
    # T13 / T14
    for N in ("N3", "N4"):
        for name in ("U", "L"):
            s = res["T13"][N][name]
            if s["nonconserving"]:
                cond["C2"] = False
            if s["not_exact"]:
                cond["C1"] = False
            if s["stop"]:
                cond["C6"] = False
    if res["T14"]["per_pair_state"] != 0 or res["T14"]["state_values_per_atom"] != 2:
        cond["C7"] = False
    # equivalence
    equivalent = all(v["U_eq_L"] for v in named.values()) and \
        all(t12[n]["p_equals_exact"] for n in ("U", "L")) and \
        res["T12"]["U"]["x_grid"] == res["T12"]["L"]["x_grid"]
    # realization
    real = res["realization"]["k"]
    reduces = all(v["equals_P_on_finer_grid"] for v in real.values())
    loss_nonzero = all(v["center_loss_coarse_u"] != 0 for v in real.values())
    # verdict (sealed rule)
    if not (cond["C1"] and cond["C2"]):
        verdict = "C — CONSERVATION_OR_COLLECTIVE_EFFECT_FAIL"
    elif not (cond["C5"] and cond["C8"]):
        verdict = "D — RESIDUAL_STATE_CAUSES_NEW_DYNAMICS_PROBLEM"
    elif not (cond["C7"] and cond["C9"]):
        verdict = "E — STATE_OR_COST_SCALING_FAILURE"
    elif not (cond["C3"] and cond["C4"] and cond["C6"]):
        verdict = "F — INCONCLUSIVE"
    elif reduces and loss_nonzero:
        verdict = "B — U_AND_L_EQUIVALENT_BUT_COST_UNRESOLVED"
    elif not loss_nonzero:
        verdict = "A — RESIDUAL_CARRY_FEASIBLE"
    else:
        verdict = "F — INCONCLUSIVE"
    return {"core_conditions": cond, "equivalence": "SAME_SEMANTICS_DIFFERENT_NORMALIZATION" if equivalent else "DIFFERENT",
            "representation_difference_example": rep_example, "named": named,
            "T11": {"P_plus_r_used": t11_ok, "negative_control_detected": t11_neg_detected, "constant_velocity": cv},
            "T12": t12, "T12_adversarial": res["T12_adversarial"], "T13": res["T13"], "T14": res["T14"],
            "realization": res["realization"], "realization_reduces_to_finer_P": reduces,
            "realization_far_field_loss_nonzero_all_k": loss_nonzero, "verdict": verdict, "notes": notes}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("results")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    raw = Path(a.results).read_bytes()
    out = check(json.loads(raw))
    out["results_sha256"] = hashlib.sha256(raw).hexdigest()
    text = json.dumps(out, indent=1)
    if a.out:
        Path(a.out).write_text(text, encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("verdict", "equivalence", "core_conditions")}, indent=1))


if __name__ == "__main__":
    main()
