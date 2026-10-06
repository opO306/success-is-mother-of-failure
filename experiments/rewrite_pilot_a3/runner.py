"""REWRITE_PILOT_A3 worker (one fresh process per call).

    python -m experiments.rewrite_pilot_a3.runner refs   OUT
    python -m experiments.rewrite_pilot_a3.runner verify EV REFS OUT        (S1, S2, S3a, S4, S5, S6)
    python -m experiments.rewrite_pilot_a3.runner sympy  EV OUT             (S3b)
    python -m experiments.rewrite_pilot_a3.runner pass   EV SCENARIO T P OUT
    python -m experiments.rewrite_pilot_a3.runner serve  EV SCENARIO T POLICY OUT
"""

from __future__ import annotations

import copy
import json
import os
import random
import sys
import time
from fractions import Fraction as Q
from pathlib import Path

T0 = (time.process_time(), time.perf_counter())

from experiments.precision_pilot_a1 import policies as POL  # noqa: E402

from . import adapter as A  # noqa: E402
from . import rules as RU  # noqa: E402

PARAMS = Path(__file__).resolve().parents[1] / "precision_pilot_a2t" / "frozen_policy_params_a1.json"
MAX_PASSES, CPU_BUDGET = 24, 5400.0
S4_P = (64, 96, 128, 192, 512)
S5_P = (96, 128)
SCEN = ("A2_bound", "A3_low", "A3_high")


def _now():
    return time.process_time(), time.perf_counter()


def _bnd(x):
    from mpmath.libmp import to_rational
    return Q(*to_rational(x._mpi_[0])), Q(*to_rational(x._mpi_[1]))


def _s(pair):
    return [str(pair[0]), str(pair[1])]


def refs():
    """1024-bit ORIGINAL point enclosures for S4, the S4 input set, the algebra PROGRAM, and the original/algebra short
    reference passes for S5."""
    from mpmath import iv
    prep = A.prepare("algebra")
    P = A.A2E._PROBE
    LI = sys.modules["exact_expression_gate_v0.lang_iv"]
    rmin = P.L.R_MIN_BOHR

    def G1024(R2):
        iv.prec = 1024
        return _bnd(LI.G_of_R2(LI.c(R2)))
    lo, hi = Q(6), Q(9)                                 # G > 0 (repulsive) below the potential minimum
    for _ in range(60):
        mid = (lo + hi) / 2
        a, b = G1024(mid * mid)
        if a > 0:
            lo = mid
        elif b < 0:
            hi = mid
        else:
            lo = hi = mid
            break
    rstar = (lo + hi) / 2
    radii = [rmin + (Q(30) - rmin) * Q(i, 47) for i in range(48)] + [rstar]
    inputs = []
    for i in range(12):
        c = rmin + (Q(30) - rmin) * Q(i, 11)
        inputs.append((max(c * c * (1 - Q(1, 10 ** 6)), rmin * rmin), c * c * (1 + Q(1, 10 ** 6))))
    rng = random.Random(3)
    rel = [Q(1, 2 ** 64), Q(1, 2 ** 128), Q(1, 2 ** 256), Q(1, 2 ** 20), Q(1, 2 ** 8), Q(1, 4), Q(1, 2 ** 40),
           Q(1, 2 ** 12), Q(1, 2 ** 192)]
    for w in rel:
        R = rmin + (Q(30) - rmin) * Q(rng.randrange(1, 10 ** 6), 10 ** 6)
        inputs.append((max(R * R * (1 - w), rmin * rmin), R * R * (1 + w)))
    inputs.append((rmin * rmin, Q(900)))                # very wide: the whole [r_min, 30]
    inputs.append(((rstar - Q(1, 1000)) ** 2, (rstar + Q(1, 1000)) ** 2))   # crosses G = 0
    inputs.append((rmin * rmin, (rmin * Q(1001, 1000)) ** 2))              # at the domain edge
    point_refs = [_s(G1024(R * R)) for R in radii]
    interval_refs = [[_s(G1024(x)) for x in (a, b, (a + b) / 2)] for a, b in inputs]
    passes = {}
    for ev in ("original", "algebra"):
        for scen in SCEN:
            for p in S5_P:
                h = A.run_pass(ev, scen, p, 100)
                passes[f"{ev}|{scen}|{p}"] = {k: h[k] for k in ("outcome", "cells", "endpoints_scaled", "completed_steps")}
    groups, tail, num, den, dn, k, c = P.PROGRAM
    enc = lambda D: {str(d): str(v) for d, v in D.items()}  # noqa: E731
    program = {"groups": [[str(a), enc(Pp)] for a, Pp in groups], "tail": enc(tail), "num": enc(num), "den": enc(den),
               "dn": enc(dn), "k": k, "c": str(c)}
    return {"mode": "refs", "r_min": str(rmin), "r_star": str(rstar), "radii": [str(r) for r in radii],
            "inputs": [_s(x) for x in inputs], "point_refs": point_refs, "interval_refs": interval_refs,
            "short_passes": passes, "program": program, **prep}


def verify(ev, refs_path):
    """S1, S2, S3a, S4, S5, S6 for one candidate (correctness only; no cost score)."""
    from mpmath import iv
    from . import rwforce as RW
    from . import symbolic as SY
    from exact_expression_gate_v1 import common as K
    R = json.loads(Path(refs_path).read_text(encoding="utf-8"))
    out = {"mode": "verify", "evaluator": ev, "stages": {}}
    st = out["stages"]
    try:
        prep = A.prepare(ev)
        plan = A._PLAN
        st["S1"] = {"ok": True, "ops": plan["ops"], "rules": plan["rules"]}
    except Exception as e:                               # noqa: BLE001
        st["S1"] = {"ok": False, "error": repr(e)}
        return out
    out.update(prep)
    out["plan"] = RU.plan_to_json(plan)
    P = A.A2E._PROBE
    LI = sys.modules["exact_expression_gate_v0.lang_iv"]
    # S2 domain duties
    s2 = {}
    iv.prec = 128
    f = RW.RwForce(plan)
    for label, x in (("r2_touches_0", iv.mpf([0, 1])), ("r2_negative_low", iv.mpf(["-1e-30", "1"]))):
        try:
            f(x)
            s2[label] = "NOT_REFUSED"
        except K.DomainStop:
            s2[label] = "REFUSED"
    if plan["recip"]:
        bad = copy.deepcopy(plan)
        bad["den"] = {0: Q(1), 1: Q(-1)}                # den(R) = 1 - R vanishes at R = 1
        try:
            RW.RwForce(bad)(iv.mpf([LI.c(Q(1, 4)).a, LI.c(Q(4)).b]))
            s2["den_crossing_0"] = "NOT_REFUSED"
        except K.DomainStop:
            s2["den_crossing_0"] = "REFUSED"
    st["S2"] = {"ok": all(v == "REFUSED" for v in s2.values()), **s2}
    # S3a
    st["S3a"] = SY.s3a(plan, P.PROGRAM)
    st["S3a"]["ok"] = st["S3a"]["canonical_equal"] and st["S3a"]["dn_identity"]
    # S4 inclusion against the 1024-bit original
    pts, ivs, bad4 = {}, {}, []
    for p in S4_P:
        iv.prec = p
        f = RW.RwForce(plan)
        pr, ir = [], []
        for i, Rs in enumerate(R["radii"]):
            Rq = Q(Rs)
            lo, hi = _bnd(f(LI.c(Rq * Rq)))
            ref = [Q(v) for v in R["point_refs"][i]]
            if not (lo <= ref[0] and ref[1] <= hi):
                bad4.append(f"p{p} R{Rs}")
            pr.append(_s((lo, hi)))
        for j, (a, b) in enumerate(R["inputs"]):
            a, b = Q(a), Q(b)
            x = iv.mpf([LI.c(a).a, LI.c(b).b])
            lo, hi = _bnd(f(x))
            for ref in R["interval_refs"][j]:
                if not (lo <= Q(ref[0]) and Q(ref[1]) <= hi):
                    bad4.append(f"p{p} input{j}")
            ir.append(_s((lo, hi)))
        pts[str(p)], ivs[str(p)] = pr, ir
    st["S4"] = {"ok": not bad4, "failures": bad4, "point_enclosures": pts, "interval_enclosures": ivs}
    # S5/S6 short passes
    s5, bad5, bad6 = {}, [], []
    for scen in SCEN:
        for p in S5_P:
            h = A.run_pass(ev, scen, p, 100)
            s5[f"{scen}|{p}"] = {k: h[k] for k in ("outcome", "cells", "endpoints_scaled", "completed_steps",
                                                   "effective_p", "force_swap_restored")}
            for ref_ev in ("original", "algebra"):
                r = R["short_passes"][f"{ref_ev}|{scen}|{p}"]
                if h["endpoints_scaled"] and r["endpoints_scaled"]:
                    if not all(Q(a0) <= Q(b1) and Q(b0) <= Q(a1) for (a0, a1), (b0, b1)
                               in zip(h["endpoints_scaled"], r["endpoints_scaled"])):
                        bad5.append(f"{scen} p{p} vs {ref_ev}")
                elif h["completed_steps"] == 100 or r["completed_steps"] == 100:
                    bad5.append(f"{scen} p{p} vs {ref_ev}: completion differs")
                if h["outcome"] == "DECIDED" and r["outcome"] == "DECIDED" and h["cells"] != r["cells"]:
                    bad6.append(f"{scen} p{p} vs {ref_ev}")
            if h["effective_p"] != p or h["force_swap_restored"] is not True:
                bad5.append(f"{scen} p{p}: effective p / swap")
    st["S5"] = {"ok": not bad5, "failures": bad5, "passes": s5}
    st["S6"] = {"ok": not bad6, "failures": bad6}
    out["PASS_S1_S6_except_S3b"] = all(st[s]["ok"] for s in ("S1", "S2", "S3a", "S4", "S5", "S6"))
    return out


def sympy_check(ev):
    from . import symbolic as SY
    prep = A.prepare(ev)
    t = _now()
    r = SY.s3b(A._PLAN, A.A2E._PROBE.PROGRAM)
    return {"mode": "sympy", "evaluator": ev, **r, "sympy_cpu_s": _now()[0] - t[0], **prep}


def serve(ev, scenario, T, policy, params):
    t_load = _now()
    prep = A.prepare(ev)
    params = dict(params, scenario=scenario)
    history, status, cpu = [], None, 0.0
    while True:
        nxt = POL.next_p(policy, params, history, T)
        if nxt is None:
            status = history[-1]["outcome"]
            break
        if nxt == "CAP" or len(history) >= MAX_PASSES or cpu >= CPU_BUDGET:
            status = "RESOURCE_REFUSED"
            break
        rec = A.run_pass(ev, scenario, nxt, T)
        cpu += rec["cpu_s"]
        history.append(rec)
    return {"mode": "serve", "evaluator": ev, "scenario": scenario, "T": T, "policy": policy,
            "policy_hash": params.get("policy_hash"), "status": status, "passes": history,
            "tried_p": [h["requested_p"] for h in history], "pass_cpu_total_s": cpu,
            "pass_wall_total_s": sum(h["wall_s"] for h in history), "ledger": POL.ledger(history),
            "load_cpu_s": t_load[0] - T0[0], "load_wall_s": t_load[1] - T0[1], **prep}


def single(ev, scenario, T, p):
    t_load = _now()
    prep = A.prepare(ev)
    return {"mode": "pass", **A.run_pass(ev, scenario, p, T), "load_cpu_s": t_load[0] - T0[0],
            "load_wall_s": t_load[1] - T0[1], **prep}


def write(doc, out):
    t = _now()
    Path(out).write_text(json.dumps(doc, indent=1), encoding="utf-8")
    t1 = _now()
    doc.update(record_cpu_s=t1[0] - t[0], record_wall_s=t1[1] - t[1], child_cpu_s=t1[0] - T0[0],
               child_wall_s=t1[1] - T0[1])
    Path(out).write_text(json.dumps(doc, indent=1), encoding="utf-8")


def main():
    a = sys.argv[1:]
    if a[0] == "refs":
        doc, out = refs(), a[1]
    elif a[0] == "verify":
        doc, out = verify(a[1], a[2]), a[3]
    elif a[0] == "sympy":
        doc, out = sympy_check(a[1]), a[2]
    elif a[0] == "pass":
        doc, out = single(a[1], a[2], int(a[3]), int(a[4])), a[5]
    elif a[0] == "serve":
        params = json.loads(PARAMS.read_text(encoding="utf-8"))
        doc, out = serve(a[1], a[2], int(a[3]), a[4], params), a[5]
    else:
        raise SystemExit("unknown mode")
    doc.update(pid=os.getpid(), python=sys.version)
    write(doc, out)


if __name__ == "__main__":
    main()
