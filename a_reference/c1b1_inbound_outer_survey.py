"""survey_only: where does the inbound V1 mirror induction close? NOT evidence for any state it did not certify, and a
certified state is certified by c1b1_inbound_outer, never by this survey. Writes JSON to the path given.

Grid (fixed before running, not fitted): E/De in {1e-8, 1e-4, 1e-2, 0.1, 1, 2, 5, 10}, b in {0, 7, 14} bohr,
R0 in {25, 200, 20000} bohr; relative state q = (sqrt(R0^2 - b^2), b, 0), P = (-p, 0, 0), p from E = p^2/(2 mu) + V(R0)
(the D_valid L / H energy ranges and b <= 2 Re; D_valid membership itself is not asked). Momentum budget: the caller's search budget, never a premise (the induction checks it). A fixed ladder, tried in
order until one certifies: P_cap = sqrt(|P0|^2 + 2 mu |V(20)|) (1 + rho), rho in RHO_LADDER (V(20) the diagnostic
potential: what the attraction adds before R = 20). Every rung's result is recorded.
History, kept in runs/c1b1_inbound_v1_survey_20260930/: (1) survey_first_run_bad_cap.* used the global force-envelope
integral I_F(20), ~1.9e7 hartree at R = 20 (valid but useless there): P_cap and the handoff width g became absurd and
R0 = 25, 200 "certified" as zero-step handoffs -- the certificate now refuses P_cap < |P|, and those rows are void.
(2) survey_second_run_tight_cap.* used one rung, rho ~ 0 (4 mu |V(20)|): every state failed, mostly on the momentum
induction, because the kick-accumulated bound p + 2 n K with each shell's MAXIMUM force needs more slack than that.
"""
import json
import math
import sys
import time
from fractions import Fraction as Q

from a_numeric import FixedPoint
from a_reference import c1b1_inbound_outer as IB
from a_reference import c1b1_outer_bootstrap as O
from a_reference import c1b1_outer_bound as B
from a_reference import c1b1_two_atom as C

POS, MOM = FixedPoint(96, 48), FixedPoint(96, 80)
ENERGIES = ("1e-8", "1e-4", "1e-2", "0.1", "1", "2", "5", "10")
IMPACT = (0, 7, 14)
RADII = (25, 200, 20000)


def state(e, b, R0):
    mu = float(B.MU)
    V = float(C.potential_high(Q(R0) ** 2))
    p = math.sqrt(2 * mu * (float(e) * float(C.DE_CONTRACT) - V))
    q = (Q(math.sqrt(R0 * R0 - b * b)), Q(b), Q(0))
    P = (Q(-p), Q(0), Q(0))
    return C.new_run(POS, B.H, tuple(-x / 2 for x in q), tuple(-x for x in P), tuple(x / 2 for x in q), P,
                     momentum_profile=MOM, validated_only=False)


RHO_LADDER = (Q(1, 1024), Q(1, 128), Q(1, 16), Q(1, 4), Q(1), Q(4))


def p_cap(run, rho):
    _, p, _ = O._state(run)
    return B.sqrt_up(O._norm2(p) + 2 * B.MU * abs(C.potential_high(Q(400)))) * (1 + rho)


def one(args):
    e, b, R0 = args
    run = state(e, b, R0)
    rungs, t = [], time.monotonic()
    for rho in RHO_LADDER:
        try:
            c = IB.certify_inbound_outer(run, p_cap(run, rho))
            rungs.append({"rho": str(rho), "status": "certified", "shells": len(c["shells"]),
                          "max_shell_steps": c["max_shell_steps"],
                          "zero_leg_steps": c["zero_impulse_leg"] and c["zero_impulse_leg"]["steps_exact"],
                          "handoff_w_upper": float(c["handoff_packet"]["q_dot_p_upper"])})
            break
        except IB.NotCertified as err:
            rungs.append({"rho": str(rho), "status": "NotCertified", "reason": str(err)})
    return {"E_De": e, "b": b, "R0": R0, "result": rungs[-1]["status"], "rungs": rungs,
            "seconds": round(time.monotonic() - t, 2)}


def main(out):
    from multiprocessing import Pool
    grid = [(e, b, R0) for e in ENERGIES for b in IMPACT for R0 in RADII]
    with Pool(6) as pool:
        rows = pool.map(one, grid)
    for r in rows:
        print(r, flush=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"kind": "survey_only", "version": IB.VERSION, "rho_ladder": [str(x) for x in RHO_LADDER],
                   "rows": rows}, f, indent=1)


if __name__ == "__main__":
    main(sys.argv[1])
