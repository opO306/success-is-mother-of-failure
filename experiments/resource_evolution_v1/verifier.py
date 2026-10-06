"""Independent result verifier of RESOURCE_EVOLUTION_PILOT_V1. Imports no executor module (worker, orch, selector,
adapters, policies); only the A1 checker's own half-even rounding. A pass record becomes a VERIFIED_RESULT only if:
evaluator approved; outcome DECIDED; completed_steps == T; effective_p == requested_p; 6 * atoms exact endpoints;
cells re-derived here from the endpoints equal the claimed cells; the force swap was restored (non-original)."""

from __future__ import annotations

import time

from experiments.precision_pilot_a1 import checker as A1C

APPROVED = {"algebra", "rw:R1+R2", "original"}
N_ATOMS = {"A2_bound": 2, "A3_low": 3, "A3_high": 3}


def verify(rec, scenario, T):
    t = time.process_time()
    why = None
    if rec.get("evaluator") not in APPROVED:
        why = "evaluator not approved"
    elif (rec.get("scenario"), rec.get("T")) != (scenario, T):
        why = "request metadata differs"
    elif rec.get("outcome") != "DECIDED":
        why = f"outcome {rec.get('outcome')}"
    elif rec.get("completed_steps") != T:
        why = "horizon not reached"
    elif rec.get("effective_p") != rec.get("requested_p"):
        why = "effective p differs"
    elif len(rec.get("endpoints_scaled") or []) != 6 * N_ATOMS[scenario]:
        why = "endpoint count"
    elif rec.get("evaluator") != "original" and rec.get("force_swap_restored") is not True:
        why = "force swap not restored"
    else:
        cells = A1C.my_cells(rec["endpoints_scaled"])
        if cells is None or cells != rec.get("cells"):
            why = "cells not reproduced from endpoints"
    return {"verified": why is None, "reason": why, "verify_cpu_s": time.process_time() - t}
